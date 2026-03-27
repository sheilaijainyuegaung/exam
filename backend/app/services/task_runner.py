from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.enums import DetectedSecondLevelMode, TaskStatus
from app.models.recognition import RecognitionDetail, RecognitionResult, RecognitionTask, RuleHitLog
from app.services.document_processor import DocumentProcessor
from app.services.rule_profile_service import get_rule_profile_or_default
from app.utils.cache import clear_cache


def _upsert_result(db: Session, task_id: int, payload: Dict) -> None:
    entity = db.query(RecognitionResult).filter(RecognitionResult.task_id == task_id).first()
    if entity is None:
        entity = RecognitionResult(
            task_id=task_id,
            answerPages=payload.get("answerPages", []),
            mainPages=payload.get("mainPages", []),
            questionType=payload.get("questionType", 1),
            scores=payload.get("scores", {"score": 0, "childScores": []}),
        )
        db.add(entity)
    else:
        entity.answerPages = payload.get("answerPages", [])
        entity.mainPages = payload.get("mainPages", [])
        entity.questionType = payload.get("questionType", 1)
        entity.scores = payload.get("scores", {"score": 0, "childScores": []})


def _upsert_detail(db: Session, task_id: int, payload: Dict) -> None:
    mode = payload.get("secondLevelModeDetected", "unknown")
    if mode not in {"restart", "continuous"}:
        mode = "unknown"

    entity = db.query(RecognitionDetail).filter(RecognitionDetail.task_id == task_id).first()
    if entity is None:
        entity = RecognitionDetail(
            task_id=task_id,
            outline_items=payload.get("outlineItems", []),
            header_footer_items=payload.get("headerFooterItems", []),
            symbol_texts=payload.get("symbolTexts", []),
            detected_max_level=payload.get("detectedMaxLevel", 0),
            second_level_mode_detected=DetectedSecondLevelMode(mode),
        )
        db.add(entity)
    else:
        entity.outline_items = payload.get("outlineItems", [])
        entity.header_footer_items = payload.get("headerFooterItems", [])
        entity.symbol_texts = payload.get("symbolTexts", [])
        entity.detected_max_level = payload.get("detectedMaxLevel", 0)
        entity.second_level_mode_detected = DetectedSecondLevelMode(mode)


def _write_rule_hit_log(db: Session, task: RecognitionTask, hits: Dict[str, int]) -> None:
    db.query(RuleHitLog).filter(RuleHitLog.task_id == task.id).delete()
    for key, value in hits.items():
        log = RuleHitLog(
            task_id=task.id,
            rule_profile_id=task.rule_profile_id,
            rule_key=str(key),
            hit_count=int(value),
        )
        db.add(log)


def run_recognition_task(task_id: int, layout_adjustments: Optional[Dict] = None) -> None:
    db = SessionLocal()
    try:
        task = db.query(RecognitionTask).filter(RecognitionTask.id == task_id).first()
        if not task:
            return

        task.status = TaskStatus.processing
        task.progress = 10
        task.error_message = None
        db.commit()

        profile = get_rule_profile_or_default(db, task.rule_profile_id)
        task.rule_profile_id = profile.id
        db.commit()

        processor = DocumentProcessor()
        output = processor.process(
            task_id=task.id,
            file_path=task.file_path,
            file_ext=task.file_ext,
            max_level=profile.max_level,
            second_level_mode=profile.second_level_mode.value,
            answer_section_patterns=profile.answer_section_patterns,
            score_patterns=profile.score_patterns,
            layout_adjustments=layout_adjustments,
        )

        task.progress = 70
        db.commit()

        _upsert_result(db, task.id, output["result"])
        _upsert_detail(db, task.id, output["details"])
        _write_rule_hit_log(db, task, output.get("ruleHits", {}))

        task.status = TaskStatus.succeeded
        task.progress = 100
        task.finished_at = datetime.utcnow()
        task.error_message = None
        db.commit()
        # 清除缓存，确保前端立即获取到最新状态
        clear_cache(task_id)
    except Exception as exc:  # pylint: disable=broad-except
        task = db.query(RecognitionTask).filter(RecognitionTask.id == task_id).first()
        if task:
            task.status = TaskStatus.failed
            task.progress = 100
            task.error_message = str(exc)
            task.finished_at = datetime.utcnow()
            db.commit()
            # 清除缓存，确保前端立即获取到最新状态
            clear_cache(task_id)
    finally:
        db.close()
