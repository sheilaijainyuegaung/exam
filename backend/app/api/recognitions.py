import copy
import os
import uuid
import json
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.utils.cache import get_cached_or_fetch

from app.db.database import get_db
from app.models.enums import TaskStatus
from app.models.recognition import RecognitionDetail, RecognitionResult, RecognitionTask
from app.schemas.recognition import (
    RecognitionDetailsResponse,
    RecognitionResultResponse,
    TaskListItemResponse,
    TaskListResponse,
    TaskStatusResponse,
    UploadResponse,
)
from app.services.task_runner import run_recognition_task
from app.services.rule_engine import (
    _distribute_outline_parent_remaining_score_to_unscored_children,
    _distribute_outline_parent_score_gap_to_slot_leaves,
    _distribute_outline_parent_score_to_numbered_zero_children,
    _distribute_outline_parent_score_to_slot_children,
    _fill_scored_empty_bracket_leaf_blank_text,
    _fill_scored_question_mark_placeholder_blank_text,
    _fill_scored_underline_leaf_blank_text,
    _force_fill_zero_child_scores_under_scored_parent,
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
    r"_{2,}\s*(?:[（(]\s*([0-9]+(?:\.[0-9]+)?)\s*分?\s*[）)])?"
)
CHOICE_TEXT_HINT_RE = re.compile(
    r"(?:[A-D][\.．、]\s*.+[B-D][\.．、]|下列|选择|选出|正确的是|不正确的是|符合题意|不符合题意)"
)


def _normalize_score_value(score: float) -> float:
    rounded = round(float(score), 4)
    if abs(rounded - round(rounded)) < 1e-8:
        return int(round(rounded))
    return rounded


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

        # 仅对“单叶子包含多个独立空位”展开子节点，避免影响已有层级结构；
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
    normalize_outline_blank_scores(normalized)
    return normalized


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

    # 如果被限流，在响应头中添加提示
    if is_rate_limited:
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
    detail = db.query(RecognitionDetail).filter(RecognitionDetail.task_id == task_id).first()
    if detail and detail.outline_items:
        outline_items = _normalize_outline_for_response(detail.outline_items or [])
        scores_payload = _build_scores_payload_from_outline(outline_items)

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
    outline_items = detail.outline_items or []
    if outline_items:
        outline_items = _normalize_outline_for_response(outline_items)

    return RecognitionDetailsResponse(
        outlineItems=outline_items,
        headerFooterItems=detail.header_footer_items or [],
        symbolTexts=detail.symbol_texts or [],
        detectedMaxLevel=int(detail.detected_max_level),
        secondLevelModeDetected=mode,
    )
