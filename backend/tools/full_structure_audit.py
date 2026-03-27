import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from app.services.document_processor import DocumentProcessor


DOC_EXTS = {".doc", ".docx"}
OPTION_STUB_RE = re.compile(
    r"^\s*(?:[\uFF08(]\s*[\uFF09)]\s*)?\d{1,3}\s*[、\.\uFF0E]\s*[A-DＡ-Ｄa-dａ-ｄ]\s*[、\.\uFF0E]"
)
ANSWER_KEY_LIKE_RE = re.compile(
    r"^\s*(?:\d{1,3}\s*[、\.\uFF0E]?\s*[A-DＡ-Ｄ]|[A-DＡ-Ｄ]\s*[、\.\uFF0E]?\s*\d{1,3}|[√×])(?:\s|$)"
)
LEADING_INDEX_RE = re.compile(r"^\s*\d{1,3}\s*[、\.\uFF0E]?\s*")
LEADING_OPTION_RE = re.compile(r"^\s*[A-DＡ-Ｄa-dａ-ｄ]\s*[、\.\uFF0E]?\s*")
BRACKET_SUBQUESTION_RE = re.compile(r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]")
SECTION_TITLE_HINT_RE = re.compile(
    r"(?:选择|单选|多选|选一选|填空|填一填|阅读|完形|写作|书面表达|任务型|语法|词汇|判断|判一判|实验|计算|算一算|解答|按要求|综合)"
)


@dataclass
class EntryResult:
    file: str
    status: str
    issues: List[Dict]


def cleanup_test_pdfs(test_root: Path) -> Tuple[int, List[str]]:
    deleted = 0
    failed: List[str] = []
    for pdf_path in test_root.rglob("*.pdf"):
        try:
            pdf_path.unlink()
            deleted += 1
        except Exception as exc:  # pragma: no cover - best effort cleanup
            failed.append(f"{pdf_path}: {exc}")
    return deleted, failed


def natural_key(path: Path) -> Tuple[int, str]:
    nums = re.findall(r"\d+", path.stem)
    if nums:
        return int(nums[0]), path.stem.lower()
    return 10**9, path.stem.lower()


def detect_subject_dirs(test_root: Path) -> List[Path]:
    dirs: List[Path] = []
    for item in sorted(test_root.iterdir(), key=lambda p: p.name):
        if not item.is_dir():
            continue
        if item.name.startswith("batch_validation_") or item.name.startswith("_"):
            continue
        dirs.append(item)
    return dirs


def collect_files(subject_dir: Path) -> List[Path]:
    files = [p for p in subject_dir.iterdir() if p.is_file() and p.suffix.lower() in DOC_EXTS]
    files.sort(key=natural_key)
    return files


def iter_nodes(nodes: List[Dict], path: str = "root") -> Iterable[Tuple[Dict, str]]:
    for idx, node in enumerate(nodes, start=1):
        numbering = str(node.get("numbering") or "").strip()
        token = numbering if numbering else f"idx{idx}"
        node_path = f"{path}/{token}" if path != "root" else token
        yield node, node_path
        children = node.get("children", []) or []
        if children:
            yield from iter_nodes(children, node_path)


def _is_segment_separator_node(node: Dict) -> bool:
    numbering = str(node.get("numbering") or "").strip()
    title = str(node.get("title") or "").strip()
    raw = str(node.get("rawText") or "").strip()
    text = re.sub(r"\s+", "", f"{numbering}{title}{raw}")
    if not text:
        return False
    if "部分" in text:
        return True
    if re.fullmatch(r"第[一二三四五六七八九十百0-9]+部分.*", text):
        return True
    if re.fullmatch(r"第[一二三四五六七八九十百0-9]+节.*", text):
        return True
    return text.lower().startswith("part")


def _is_acceptable_duplicate_numbering(nodes: List[Dict], numbering: str, positions: List[int]) -> bool:
    if len(positions) != 2:
        return False
    left_node = nodes[positions[0] - 1]
    right_node = nodes[positions[1] - 1]

    left_raw = str(left_node.get("rawText") or "").strip()
    right_raw = str(right_node.get("rawText") or "").strip()
    if not left_raw or not right_raw:
        return False

    # 多材料场景中常见“(1)(2)...”重复编号，允许出现，不视为结构错误。
    if BRACKET_SUBQUESTION_RE.match(left_raw) and BRACKET_SUBQUESTION_RE.match(right_raw):
        if len(left_raw) >= 8 and len(right_raw) >= 8:
            return True

    left_text = re.sub(r"\s+", "", f"{left_node.get('title') or ''}{left_raw}")
    right_text = re.sub(r"\s+", "", f"{right_node.get('title') or ''}{right_raw}")
    left_score = float(left_node.get("score") or 0.0)
    right_score = float(right_node.get("score") or 0.0)
    left_is_section = left_score > 0 and bool(SECTION_TITLE_HINT_RE.search(left_text))
    right_is_section = right_score > 0 and bool(SECTION_TITLE_HINT_RE.search(right_text))
    left_is_score_placeholder = _is_score_placeholder_line(left_raw, left_score)
    right_is_score_placeholder = _is_score_placeholder_line(right_raw, right_score)

    # “编号题型标题 + 同编号具体题目”属于常见试卷结构，不视为重复错误。
    if left_is_section and not right_is_section:
        return True
    if right_is_section and not left_is_section:
        return True
    # 两个都是题型标题（如文档中手工重复编号）时不作为提取错误。
    if left_is_section and right_is_section:
        return True
    if (left_is_score_placeholder and not right_is_score_placeholder) or (
        right_is_score_placeholder and not left_is_score_placeholder
    ):
        return True

    # 多材料/多任务场景下常见同号并列描述，若双方都为完整长句，默认接受。
    if len(left_raw) >= 12 and len(right_raw) >= 12:
        return True
    return False


def _is_score_placeholder_line(raw: str, score: float) -> bool:
    if score <= 0:
        return False
    text = re.sub(r"\s+", "", raw or "")
    if not text:
        return False
    text = re.sub(r"[\uFF08(]\s*(?:共|总计|总分)?\s*\d+(?:\.\d+)?\s*分\s*[\uFF09)]", "", text)
    text = re.sub(r"^[\d一二三四五六七八九十]+[、\.\uFF0E]?", "", text)
    text = re.sub(r"[：:，,。．；;!?？！\-_—\u3000]+", "", text)
    return text == ""


def collect_duplicate_sibling_issues(nodes: List[Dict], path: str = "root") -> List[Dict]:
    issues: List[Dict] = []
    number_positions: Dict[Tuple[int, str], List[int]] = defaultdict(list)

    segment_id = 0
    for idx, node in enumerate(nodes, start=1):
        if _is_segment_separator_node(node):
            segment_id += 1
            continue
        numbering = str(node.get("numbering") or "").strip()
        if numbering:
            number_positions[(segment_id, numbering)].append(idx)

    for (_, numbering), positions in number_positions.items():
        if len(positions) > 1:
            if _is_acceptable_duplicate_numbering(nodes, numbering, positions):
                continue
            issues.append(
                {
                    "type": "duplicate_sibling_numbering",
                    "path": path,
                    "numbering": numbering,
                    "positions": positions,
                }
            )

    for idx, node in enumerate(nodes, start=1):
        numbering = str(node.get("numbering") or "").strip()
        token = numbering if numbering else f"idx{idx}"
        child_path = f"{path}/{token}" if path != "root" else token
        children = node.get("children", []) or []
        if children:
            issues.extend(collect_duplicate_sibling_issues(children, child_path))
    return issues


def collect_stub_issues(nodes: List[Dict]) -> List[Dict]:
    issues: List[Dict] = []
    for node, node_path in iter_nodes(nodes):
        raw = str(node.get("rawText") or "").strip()
        if not raw:
            continue
        if OPTION_STUB_RE.match(raw):
            issues.append(
                {
                    "type": "numeric_option_stub_node",
                    "path": node_path,
                    "rawText": raw,
                }
            )
    return issues


def collect_empty_placeholder_issues(nodes: List[Dict]) -> List[Dict]:
    issues: List[Dict] = []
    for node, node_path in iter_nodes(nodes):
        children = node.get("children", []) or []
        if children:
            continue
        numbering = str(node.get("numbering") or "").strip()
        raw = str(node.get("rawText") or "").strip()
        title = str(node.get("title") or "").strip()
        blank = str(node.get("blankText") or "").strip()
        score = float(node.get("score") or 0.0)
        if numbering or raw or title or blank:
            continue
        if score > 0:
            continue
        issues.append({"type": "empty_leaf_placeholder", "path": node_path})
    return issues


def _is_likely_question_sentence(raw: str) -> bool:
    text = re.sub(r"\s+", " ", raw or "").strip()
    if not text:
        return False
    without_index = LEADING_INDEX_RE.sub("", text, count=1)
    without_option = LEADING_OPTION_RE.sub("", without_index, count=1)
    words = re.findall(r"[A-Za-z]+", without_option)
    if len(words) >= 3 and len(without_option) >= 18:
        return True
    return False


def collect_answer_like_intrusion_issues(nodes: List[Dict]) -> List[Dict]:
    issues: List[Dict] = []
    for node, node_path in iter_nodes(nodes):
        raw = str(node.get("rawText") or "").strip()
        if not raw:
            continue
        if ANSWER_KEY_LIKE_RE.match(raw) and not _is_likely_question_sentence(raw):
            issues.append(
                {
                    "type": "answer_like_intrusion",
                    "path": node_path,
                    "rawText": raw,
                }
            )
    return issues


def audit_file(processor: DocumentProcessor, file_path: Path, task_id: int) -> EntryResult:
    try:
        output = processor.process(
            task_id=task_id,
            file_path=str(file_path),
            file_ext=file_path.suffix.lower(),
            max_level=8,
            second_level_mode="auto",
            answer_section_patterns=None,
            score_patterns=None,
        )
        outline = output.get("details", {}).get("outlineItems", []) or []

        issues: List[Dict] = []
        issues.extend(collect_duplicate_sibling_issues(outline))
        issues.extend(collect_stub_issues(outline))
        issues.extend(collect_empty_placeholder_issues(outline))
        issues.extend(collect_answer_like_intrusion_issues(outline))

        status = "ok" if not issues else "mismatch"
        return EntryResult(file=file_path.name, status=status, issues=issues)
    except Exception as exc:
        return EntryResult(
            file=file_path.name,
            status="failed",
            issues=[{"type": "exception", "message": f"{type(exc).__name__}: {exc}"}],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full structure audit on local test documents.")
    parser.add_argument(
        "--task-id-start",
        type=int,
        default=930000,
        help="Base task id for processor runs.",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default="",
        help="Optional subject directory name filter.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    test_root = root / "test"
    out_root = root / "tmp_case_results"
    out_root.mkdir(parents=True, exist_ok=True)

    processor = DocumentProcessor()
    subjects = detect_subject_dirs(test_root)
    if args.subject:
        subjects = [item for item in subjects if item.name == args.subject]
        if not subjects:
            raise RuntimeError(f"subject not found: {args.subject}")

    payload: Dict[str, object] = {
        "generated_at": datetime.now().isoformat(),
        "subjects": {},
    }

    task_id = int(args.task_id_start)
    for subject_dir in subjects:
        files = collect_files(subject_dir)
        entries: List[Dict] = []
        ok_count = 0
        mismatch_count = 0
        failed_count = 0

        for file_path in files:
            task_id += 1
            result = audit_file(processor, file_path, task_id)
            entries.append({"file": result.file, "status": result.status, "issues": result.issues})
            if result.status == "ok":
                ok_count += 1
            elif result.status == "mismatch":
                mismatch_count += 1
            else:
                failed_count += 1

        payload["subjects"][subject_dir.name] = {
            "summary": {
                "total": len(files),
                "ok": ok_count,
                "mismatch": mismatch_count,
                "failed": failed_count,
            },
            "entries": entries,
        }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_root / f"full_structure_audit_{stamp}.json"
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    deleted, failed = cleanup_test_pdfs(test_root)
    print(f"pdf_cleanup_deleted={deleted}")
    if failed:
        print(f"pdf_cleanup_failed={len(failed)}")
        for item in failed[:20]:
            print(item)

    print(out_file)


if __name__ == "__main__":
    main()
