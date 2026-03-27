import pytest
from fastapi import HTTPException
import re

from app.api.recognitions import (
    _build_scores_payload_from_outline,
    _extract_blank_segment_scores,
    _parse_layout_adjustments,
)
from app.models.enums import DetectedSecondLevelMode, TaskStatus
from app.models.recognition import RecognitionDetail, RecognitionResult, RecognitionTask


def test_rule_profile_crud(client):
    list_resp = client.get("/api/v1/rule-profiles")
    assert list_resp.status_code == 200

    create_resp = client.post(
        "/api/v1/rule-profiles",
        json={
            "name": "unit-profile",
            "isActive": True,
            "maxLevel": 8,
            "secondLevelMode": "auto",
            "answerSectionPatterns": ["答案"],
            "scorePatterns": [r"[（(](\\d+)分[）)]"],
        },
    )
    assert create_resp.status_code == 200
    profile_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/v1/rule-profiles/{profile_id}",
        json={"secondLevelMode": "restart", "maxLevel": 6},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["secondLevelMode"] == "restart"
    assert update_resp.json()["maxLevel"] == 6


def test_result_and_details_endpoints(client, db_session):
    task = RecognitionTask(
        batch_id="batch-test",
        file_name="mock.docx",
        file_ext=".docx",
        file_size=123,
        file_path="C:/tmp/mock.docx",
        status=TaskStatus.succeeded,
        progress=100,
    )
    db_session.add(task)
    db_session.flush()

    result = RecognitionResult(
        task_id=task.id,
        answerPages=["/storage/pages/a1.png"],
        mainPages=["/storage/pages/m1.png"],
        questionType=3,
        scores={"score": 10, "childScores": [{"score": 5, "childScores": []}]},
    )
    detail = RecognitionDetail(
        task_id=task.id,
        outline_items=[{"level": 1, "numbering": "一"}],
        header_footer_items=[{"page": 1, "header": "H", "footer": "F"}],
        symbol_texts=["（10分）", "____"],
        detected_max_level=3,
        second_level_mode_detected=DetectedSecondLevelMode.restart,
    )
    db_session.add(result)
    db_session.add(detail)
    db_session.commit()

    status_resp = client.get(f"/api/v1/recognitions/tasks/{task.id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "succeeded"

    result_resp = client.get(f"/api/v1/recognitions/tasks/{task.id}/result")
    assert result_resp.status_code == 200
    payload = result_resp.json()
    assert set(payload.keys()) == {"answerPages", "mainPages", "questionType", "scores"}
    assert payload["questionType"] == 3

    detail_resp = client.get(f"/api/v1/recognitions/tasks/{task.id}/details")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["secondLevelModeDetected"] == "restart"


def test_list_tasks_endpoint(client, db_session):
    older = RecognitionTask(
        batch_id="batch-history",
        file_name="older.docx",
        file_ext=".docx",
        file_size=111,
        file_path="C:/tmp/older.docx",
        status=TaskStatus.succeeded,
        progress=100,
    )
    newer = RecognitionTask(
        batch_id="batch-history",
        file_name="newer.pdf",
        file_ext=".pdf",
        file_size=222,
        file_path="C:/tmp/newer.pdf",
        status=TaskStatus.failed,
        progress=100,
        error_message="parse failed",
    )
    db_session.add(older)
    db_session.flush()
    older_id = int(older.id)
    db_session.add(newer)
    db_session.flush()
    newer_id = int(newer.id)
    db_session.commit()

    resp = client.get("/api/v1/recognitions/tasks?limit=20")
    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload and "total" in payload
    assert payload["total"] >= 2

    ids = [item["taskId"] for item in payload["items"]]
    assert newer_id in ids
    assert older_id in ids

    newer_item = next(item for item in payload["items"] if item["taskId"] == newer_id)
    assert newer_item["fileName"] == "newer.pdf"
    assert newer_item["status"] == "failed"
    assert newer_item["errorMessage"] == "parse failed"


def test_details_endpoint_should_normalize_legacy_zero_blank_segments(client, db_session):
    task = RecognitionTask(
        batch_id="batch-legacy",
        file_name="legacy.doc",
        file_ext=".doc",
        file_size=321,
        file_path="C:/tmp/legacy.doc",
        status=TaskStatus.succeeded,
        progress=100,
    )
    db_session.add(task)
    db_session.flush()

    db_session.add(
        RecognitionResult(
            task_id=task.id,
            answerPages=[],
            mainPages=["/storage/pages/m1.pdf"],
            questionType=3,
            scores={"score": 60, "childScores": [{"score": 60, "childScores": []}]},
        )
    )
    db_session.add(
        RecognitionDetail(
            task_id=task.id,
            outline_items=[
                {
                    "lineNumber": 1,
                    "level": 1,
                    "numbering": "二",
                    "score": 60,
                    "blankText": "",
                    "children": [
                        {
                            "lineNumber": 10,
                            "level": 2,
                            "numbering": "10",
                            "score": 10,
                            "blankText": "",
                            "children": [
                                {
                                    "lineNumber": 12,
                                    "level": 3,
                                    "numbering": "2",
                                    "score": 6,
                                    "rawText": "（2）expr ______ ______",
                                    "blankText": "______（0分） ______（0分）",
                                    "children": [],
                                }
                            ],
                        }
                    ],
                }
            ],
            header_footer_items=[],
            symbol_texts=[],
            detected_max_level=3,
            second_level_mode_detected=DetectedSecondLevelMode.restart,
        )
    )
    db_session.commit()

    resp = client.get(f"/api/v1/recognitions/tasks/{task.id}/details")
    assert resp.status_code == 200
    part = resp.json()["outlineItems"][0]["children"][0]["children"][0]
    values = [
        float(item)
        for item in re.findall(
            r"[\uff08(]\s*(\d+(?:\.\d+)?)\s*\u5206\s*[\uff09)]",
            str(part.get("blankText") or ""),
        )
    ]
    assert values
    assert abs(sum(values) - 6.0) < 1e-6


def test_parse_layout_adjustments_accepts_valid_payload():
    parsed = _parse_layout_adjustments(
        '{"marginTopCm": 1.5, "marginLeftCm": 2, "paragraphSpaceAfterPt": 8}'
    )
    assert parsed == {"marginTopCm": 1.5, "marginLeftCm": 2.0, "paragraphSpaceAfterPt": 8.0}


def test_parse_layout_adjustments_rejects_invalid_payload():
    with pytest.raises(HTTPException):
        _parse_layout_adjustments('{"marginTopCm": "abc"}')


def test_extract_blank_segment_scores_should_treat_single_long_underline_as_one_slot():
    assert _extract_blank_segment_scores("_________________________________________________________________________（3分）", 3) == [3]


def test_build_scores_payload_should_not_expand_single_long_underline_leaf():
    outline_items = [
        {
            "numbering": "三",
            "rawText": "三、古诗文阅读（19分）",
            "blankText": "",
            "score": 19,
            "type": 1,
            "children": [
                {
                    "numbering": "12",
                    "rawText": "12.诗歌三、四两句可见小儿是什么心态？结合具体字词简要分析。（3分）_________________________________________________________________________",
                    "blankText": "_________________________________________________________________________（3分）",
                    "score": 3,
                    "type": 1,
                    "children": [],
                }
            ],
        }
    ]
    payload = _build_scores_payload_from_outline(outline_items)
    leaf = payload["childScores"][0]["childScores"][0]
    assert leaf["blankText"] == "_________________________________________________________________________（3分）"
    assert leaf["childScores"] == []
