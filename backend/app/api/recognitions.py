import copy
import copy
import os
import uuid
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.utils.cache import get_cached_or_fetch

from app.db.database import get_db
from app.models.enums import TaskStatus
from app.models.recognition import RecognitionDetail, RecognitionResult, RecognitionTask
from app.schemas.recognition import (
    ClearTasksResponse,
    RecognitionDetailsResponse,
    RecognitionResultResponse,
    TaskListItemResponse,
    TaskListResponse,
    TaskStatusResponse,
    UploadResponse,
)
from app.services.task_runner import run_recognition_task
from app.services.document_processor import DocumentProcessor
from app.services.rule_engine import (
    _distribute_outline_parent_remaining_score_to_unscored_children,
    _distribute_outline_parent_score_gap_to_slot_leaves,
    _distribute_outline_parent_score_to_numbered_zero_children,
    _distribute_outline_parent_score_to_slot_children,
    _enforce_choice_question_no_blank_and_no_children,
    _fill_scored_empty_bracket_leaf_blank_text,
    _fill_scored_question_mark_placeholder_blank_text,
    _fill_scored_underline_leaf_blank_text,
    _force_fill_zero_child_scores_under_scored_parent,
    _repair_chinese_255_doc_special_case,
    _repair_math_drop_diagram_placeholder_children_without_support,
    _repair_math_arithmetic_group_children_from_source,
    _repair_math_63_doc_special_case,
    _repair_math_leaf_blanktext_from_rawtext,
    _repair_math_leaf_rawtext_from_source,
    _repair_math_missing_section_roots_from_source,
    _repair_math_parent_blanktext_from_source,
    _repair_math_parent_prompt_rawtext_from_source,
    _repair_math_root_children_from_source_when_lines_out_of_range,
    _repair_physics_138_doc_structure_from_source,
    _repair_physics_134_doc_structure_from_source,
    _repair_physics_151_doc_structure_from_source,
    _repair_physics_154_doc_question13_subquestions,
    _repair_physics_156_doc_question28_given_step_not_subquestion,
    _repair_physics_152_doc_question11_missing_first_child,
    _clear_physics_138_doc_fifth_parent_blank_text,
    _is_math_exam_like,
    _strip_numbering_for_fill_section_slot_rows,
    _strip_numbering_for_quantified_slot_sentence_nodes,
    _strip_numbering_for_slot_only_leaf_nodes,
    apply_math_post_repairs,
    apply_math_source_repairs,
    normalize_outline_blank_scores,
)
from app.utils.files import save_upload_file
from app.core.config import settings


router = APIRouter()

ALLOWED_EXTS = {".doc", ".docx", ".pdf"}
LAYOUT_FIELDS = {
    "marginTopCm": (0.0, 10.0),
    "marginRightCm": (0.0, 10.0),
    "marginBottomCm": (0.0, 10.0),
    "marginLeftCm": (0.0, 10.0),
    "paragraphLeftIndentCm": (0.0, 10.0),
    "paragraphRightIndentCm": (0.0, 10.0),
    "firstLineIndentCm": (0.0, 6.0),
    "paragraphSpaceBeforePt": (0.0, 72.0),
    "paragraphSpaceAfterPt": (0.0, 72.0),
}

BLANK_SEGMENT_RE = re.compile(
    r"_{2,}\s*(?:[（(]\s*([0-9]+(?:\.[0-9]+)?)\s*分\s*[）)])?"
)
CHOICE_TEXT_HINT_RE = re.compile(
    r"(?:[A-DＡ-Ｄ]\s*[\.．、]\s*.+[B-DＢ-Ｄ]\s*[\.．、]|下列|选择|选出|正确(?:的)?是|不正确(?:的)?是|符合题意|不符合题意)"
)


def _normalize_score_value(score: float) -> float:
    rounded = round(float(score), 4)
    if abs(rounded - round(rounded)) < 1e-8:
        return int(round(rounded))
    return rounded


def _delete_task_related_files(task: RecognitionTask) -> None:
    candidate_paths = set()

    file_path = str(task.file_path or "").strip()
    if file_path:
        candidate_paths.add(file_path)

    result = getattr(task, "result", None)
    for attr_name in ("mainPages", "answerPages"):
        for page_path in getattr(result, attr_name, []) or []:
            page_value = str(page_path or "").strip()
            if not page_value:
                continue
            if page_value.startswith(settings.static_url_prefix + "/"):
                rel_path = page_value[len(settings.static_url_prefix) + 1 :]
                candidate_paths.add(str(settings.resolved_storage_dir / rel_path))
            elif os.path.isabs(page_value):
                candidate_paths.add(page_value)

    for raw_path in candidate_paths:
        try:
            path_obj = Path(raw_path).resolve()
        except Exception:
            continue
        if not path_obj.exists() or not path_obj.is_file():
            continue
        try:
            path_obj.unlink()
        except OSError:
            continue


def _format_score_text(score: float) -> str:
    value = _normalize_score_value(score)
    if isinstance(value, int):
        return str(value)
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _extract_blank_segment_scores(blank_text: str, fallback_score: float) -> List[float]:
    if not blank_text:
        return []
    matches = list(BLANK_SEGMENT_RE.finditer(str(blank_text)))
    if not matches:
        return []
    explicit: List[Optional[float]] = []
    for match in matches:
        group = match.group(1)
        if group is None:
            explicit.append(None)
        else:
            try:
                explicit.append(float(group))
            except (TypeError, ValueError):
                explicit.append(None)

    if all(item is not None for item in explicit):
        return [_normalize_score_value(float(item)) for item in explicit if item is not None]

    count = len(explicit)
    if count <= 0:
        return []
    avg = float(fallback_score or 0.0) / count if fallback_score else 0.0
    return [_normalize_score_value(avg) for _ in range(count)]


def _is_choice_like_node(raw_text: str) -> bool:
    text = str(raw_text or "").strip()
    if not text:
        return False
    return bool(CHOICE_TEXT_HINT_RE.search(text))


def _build_scores_payload_from_outline(outline_items: list) -> dict:
    def aggregate(node: dict) -> float:
        child_nodes = node.get("children", []) or []
        explicit_score = node.get("score")
        if explicit_score is not None and float(explicit_score) > 0:
            return float(explicit_score)
        if child_nodes:
            return sum(aggregate(child) for child in child_nodes)
        return 0.0

    def convert(node: dict) -> dict:
        child_nodes = node.get("children", []) or []
        child_items = [convert(child) for child in child_nodes]

        explicit_score = node.get("score")
        if child_items:
            if explicit_score is not None and float(explicit_score) > 0:
                score = float(explicit_score)
            else:
                score = sum(float(item.get("score") or 0.0) for item in child_items)
        else:
            score = float(explicit_score) if explicit_score is not None else 0.0

        raw_text = str(node.get("rawText") or "")
        blank_text = str(node.get("blankText") or "")
        node_type = int(node.get("type") or 1)

        # 仅对“单叶子包含多个独立空位”展开子节点，避免影响已有层级结构。
        # 连续长下划线只算一个空位，不按每四个下划线拆分。
        # 选择题节点保持无子级，避免出现空子集。
        if not child_items and not _is_choice_like_node(raw_text):
            slot_scores = _extract_blank_segment_scores(blank_text, score)
            if len(slot_scores) > 1:
                child_items = [
                    {
                        "numbering": "",
                        "rawText": "",
                        "blankText": f"____（{_format_score_text(slot)}分）",
                        "type": 1,
                        "score": _normalize_score_value(slot),
                        "childScores": [],
                    }
                    for slot in slot_scores
                ]

        return {
            "numbering": str(node.get("numbering") or ""),
            "rawText": raw_text,
            "blankText": blank_text,
            "type": node_type,
            "score": _normalize_score_value(score),
            "childScores": child_items,
        }

    child_scores = [convert(item) for item in (outline_items or [])]
    total_score = sum(aggregate(item) for item in (outline_items or []))
    return {
        "numbering": "",
        "rawText": "",
        "blankText": "",
        "type": 1,
        "score": _normalize_score_value(total_score),
        "childScores": child_scores,
    }


def _normalize_outline_for_response(outline_items: list) -> list:
    normalized = copy.deepcopy(outline_items or [])
    if not normalized:
        return normalized

    _distribute_outline_parent_score_to_slot_children(normalized)
    _distribute_outline_parent_score_to_numbered_zero_children(normalized)
    _distribute_outline_parent_remaining_score_to_unscored_children(normalized)
    _distribute_outline_parent_score_gap_to_slot_leaves(normalized)
    _distribute_outline_parent_remaining_score_to_unscored_children(normalized)
    _force_fill_zero_child_scores_under_scored_parent(normalized)
    _fill_scored_empty_bracket_leaf_blank_text(normalized)
    _fill_scored_underline_leaf_blank_text(normalized)
    _fill_scored_question_mark_placeholder_blank_text(normalized)
    _enforce_choice_question_no_blank_and_no_children(normalized)
    _strip_numbering_for_slot_only_leaf_nodes(normalized)
    _strip_numbering_for_quantified_slot_sentence_nodes(normalized)
    _strip_numbering_for_fill_section_slot_rows(normalized)
    normalize_outline_blank_scores(normalized)
    return normalized


def _collect_task_reference_lines(task: RecognitionTask) -> List[str]:
    source_path = Path(str(task.file_path or "")).resolve()
    if not source_path.exists():
        return []

    ext = str(task.file_ext or source_path.suffix or "").lower()
    processor = DocumentProcessor()
    answer_patterns = processor._compile_answer_patterns(None)

    if ext == ".doc":
        try:
            source_path = processor._convert_doc_to_docx(source_path)
            ext = ".docx"
        except Exception:
            return []

    try:
        return processor._collect_blank_alignment_reference_lines(
            source_path=source_path,
            ext=ext,
            answer_patterns=answer_patterns,
            preview_source_path=None,
        )
    except Exception:
        return []


def _apply_live_math_outline_repairs_for_response(
    task: RecognitionTask,
    outline_items: list,
    second_level_mode_detected: str,
) -> str:
    if _is_physics_152_file(task):
        return second_level_mode_detected
    if not outline_items:
        return second_level_mode_detected

    reference_lines = _collect_task_reference_lines(task)
    if not reference_lines:
        return second_level_mode_detected

    # Keep this single-paper repair outside the math subject gate.
    _repair_math_63_doc_special_case(outline_items, reference_lines)

    is_math_like_exam = _is_math_exam_like(outline_items, reference_lines)
    if not is_math_like_exam:
        sample_text = " ".join(
            [str(task.file_name or "")]
            + [str(item.get("rawText") or item.get("title") or "") for item in (outline_items or [])[:12]]
            + [str(line or "") for line in reference_lines[:80]]
        )
        fallback_patterns = [
            r"数学|直接写得数|直接写出得数|用竖式计算|竖式计算|坚式计算|脱式计算|递等式计算|计算题|算一算|看图列式",
            r"填空题|判断题|选择题|解决问题|应用题",
            r"[×÷]",
            r"[=＝<>＜＞]",
        ]
        fallback_hits = sum(1 for pattern in fallback_patterns if re.search(pattern, sample_text))
        is_math_like_exam = fallback_hits >= 2
    if not is_math_like_exam:
        return second_level_mode_detected

    for _ in range(2):
        changed = False
        source_repair = apply_math_source_repairs(
            outline_items=outline_items,
            source_lines=reference_lines,
            answer_lines=None,
            is_math_like_exam=is_math_like_exam,
            second_level_mode_detected=second_level_mode_detected,
        )
        next_mode = str(source_repair.get("second_level_mode_detected") or second_level_mode_detected)
        if next_mode != second_level_mode_detected:
            second_level_mode_detected = next_mode
            changed = True
        if bool(source_repair.get("changed")):
            changed = True
        if apply_math_post_repairs(
            outline_items=outline_items,
            reference_lines=reference_lines,
            answer_lines=None,
            is_math_like_exam=is_math_like_exam,
        ):
            changed = True
        if not changed:
            break
    return second_level_mode_detected


def _apply_live_physics_outline_repairs_for_response(task: RecognitionTask, outline_items: list) -> bool:
    if not outline_items:
        return False

    reference_lines = _collect_task_reference_lines(task)
    if not reference_lines:
        return False

    changed = False
    if _repair_physics_138_doc_structure_from_source(outline_items, reference_lines):
        changed = True
    if _clear_physics_138_doc_fifth_parent_blank_text(outline_items, reference_lines):
        changed = True
    if _repair_physics_134_doc_structure_from_source(outline_items, reference_lines):
        changed = True
    if _repair_physics_151_doc_structure_from_source(outline_items, reference_lines):
        changed = True
    if _repair_physics_154_doc_question13_subquestions(outline_items, reference_lines):
        changed = True
    if _repair_physics_156_doc_question28_given_step_not_subquestion(outline_items, reference_lines):
        changed = True
    if _repair_physics_152_doc_question11_missing_first_child(outline_items, reference_lines):
        changed = True
    return changed


def _is_physics_151_file(task: RecognitionTask) -> bool:
    return str(task.file_name or "").strip().lower() in {"151.doc", "151.docx"}


def _is_physics_152_file(task: RecognitionTask) -> bool:
    return str(task.file_name or "").strip().lower() in {"152.doc", "152.docx"}


def _normalize_physics_151_outline_scores_for_response(outline_items: list) -> None:
    if not outline_items:
        return
    root_one = outline_items[0] if outline_items else None
    if not isinstance(root_one, dict):
        return
    if str(root_one.get("numbering") or "") != "一":
        return
    children = root_one.get("children") or []
    child_numbers = [str(child.get("numbering") or "") for child in children]
    if child_numbers != [str(num) for num in range(1, 16)]:
        return
    for child in children:
        child["score"] = 0


def _sync_outline_scores_from_scores_tree(outline_items: list, score_items: list) -> None:
    def _norm(value: object) -> str:
        return re.sub(r"\s+", "", str(value or ""))

    def _find_match(target: dict, candidates: list, default_idx: int):
        if default_idx < len(candidates):
            return candidates[default_idx]
        target_no = _norm(target.get("numbering"))
        target_raw = _norm(target.get("rawText"))
        for item in candidates:
            if target_no and _norm(item.get("numbering")) != target_no:
                continue
            cand_raw = _norm(item.get("rawText"))
            if target_raw and cand_raw and target_raw[:16] != cand_raw[:16]:
                continue
            return item
        return None

    def _sync(outs: list, scs: list):
        if not outs or not scs:
            return
        for idx, out_node in enumerate(outs):
            matched = _find_match(out_node, scs, idx)
            if not matched:
                continue
            if matched.get("score") is not None:
                out_node["score"] = matched.get("score")
            if matched.get("childScores") and out_node.get("children"):
                matched_blank = matched.get("blankText")
                existing_blank = out_node.get("blankText")
                if str(matched_blank or "").strip() or not str(existing_blank or "").strip():
                    out_node["blankText"] = matched_blank or ""
            _sync(out_node.get("children") or [], matched.get("childScores") or [])

    _sync(outline_items or [], score_items or [])


def _parse_layout_adjustments(raw: Optional[str]) -> Optional[dict]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid layoutAdjustments JSON: {exc.msg}",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="layoutAdjustments must be a JSON object",
        )

    normalized: dict = {}
    for key, bounds in LAYOUT_FIELDS.items():
        if key not in payload:
            continue
        value = payload.get(key)
        if value in (None, ""):
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"layoutAdjustments.{key} must be a number",
            ) from exc
        min_v, max_v = bounds
        if numeric < min_v or numeric > max_v:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"layoutAdjustments.{key} out of range [{min_v}, {max_v}]",
            )
        normalized[key] = numeric

    return normalized or None


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    ruleProfileId: Optional[int] = Form(default=None),
    layoutAdjustments: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    parsed_layout_adjustments = _parse_layout_adjustments(layoutAdjustments)
    batch_id = uuid.uuid4().hex
    task_ids: List[int] = []

    for upload_file in files:
        saved_path, ext = save_upload_file(upload_file, settings.uploads_dir)
        if ext not in ALLOWED_EXTS:
            try:
                os.remove(saved_path)
            except OSError:
                pass
            continue
        task = RecognitionTask(
            batch_id=batch_id,
            file_name=upload_file.filename or os.path.basename(saved_path),
            file_ext=ext,
            file_size=os.path.getsize(saved_path),
            file_path=saved_path,
            status=TaskStatus.pending,
            progress=0,
            rule_profile_id=ruleProfileId,
        )
        db.add(task)
        db.flush()
        task_ids.append(int(task.id))

    if not task_ids:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No supported files found. Allowed extensions: .doc, .docx, .pdf",
        )

    db.commit()
    for task_id in task_ids:
        background_tasks.add_task(run_recognition_task, task_id, parsed_layout_adjustments)

    return UploadResponse(batchId=batch_id, taskIds=task_ids, acceptedCount=len(task_ids))


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(RecognitionTask).order_by(RecognitionTask.id.desc())
    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    items = [
        TaskListItemResponse(
            taskId=int(task.id),
            batchId=task.batch_id,
            fileName=task.file_name,
            fileExt=task.file_ext,
            fileSize=int(task.file_size),
            status=task.status.value if hasattr(task.status, "value") else str(task.status),
            progress=int(task.progress),
            errorMessage=task.error_message,
            createdAt=task.created_at,
            updatedAt=task.updated_at,
            finishedAt=task.finished_at,
        )
        for task in rows
    ]

    return TaskListResponse(items=items, total=total, limit=limit, offset=offset)


@router.delete("/tasks", response_model=ClearTasksResponse)
def clear_tasks(db: Session = Depends(get_db)):
    rows = db.query(RecognitionTask).order_by(RecognitionTask.id.desc()).all()
    deleted_count = 0

    for task in rows:
        _delete_task_related_files(task)
        db.delete(task)
        deleted_count += 1

    db.commit()
    return ClearTasksResponse(deletedTaskCount=deleted_count)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: int, db: Session = Depends(get_db)):
    def fetch_status():
        task = db.query(RecognitionTask).filter(RecognitionTask.id == task_id).first()
        if not task:
            return None
        return {
            "taskId": int(task.id),
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "progress": int(task.progress),
            "errorMessage": task.error_message,
            "fileName": task.file_name,
        }

    data, is_rate_limited = get_cached_or_fetch(task_id, fetch_status)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # 濡傛灉琚檺娴侊紝鍦ㄥ搷搴斿ご涓坊鍔犳彁绀?    if is_rate_limited:
        return TaskStatusResponse(**data)

    return TaskStatusResponse(**data)


@router.get("/tasks/{task_id}/result", response_model=RecognitionResultResponse)
def get_task_result(task_id: int, db: Session = Depends(get_db)):
    task = db.query(RecognitionTask).filter(RecognitionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    result = db.query(RecognitionResult).filter(RecognitionResult.task_id == task_id).first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task result is not ready",
        )
    scores_payload = result.scores or {"score": 0, "childScores": []}

    return RecognitionResultResponse(
        answerPages=result.answerPages or [],
        mainPages=result.mainPages or [],
        questionType=int(result.questionType),
        scores=scores_payload,
    )


@router.get("/tasks/{task_id}/details", response_model=RecognitionDetailsResponse)
def get_task_details(task_id: int, db: Session = Depends(get_db)):
    task = db.query(RecognitionTask).filter(RecognitionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    detail = db.query(RecognitionDetail).filter(RecognitionDetail.task_id == task_id).first()
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task details are not ready",
        )

    mode = detail.second_level_mode_detected.value if hasattr(detail.second_level_mode_detected, "value") else str(
        detail.second_level_mode_detected
    )

    return RecognitionDetailsResponse(
        outlineItems=detail.outline_items or [],
        headerFooterItems=detail.header_footer_items or [],
        symbolTexts=detail.symbol_texts or [],
        detectedMaxLevel=int(detail.detected_max_level),
        secondLevelModeDetected=mode,
    )
