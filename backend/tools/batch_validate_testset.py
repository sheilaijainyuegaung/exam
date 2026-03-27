import argparse
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from docx import Document

from app.core.config import settings
from app.services.document_processor import DocumentProcessor
from app.services.rule_engine import (
    QUESTION_DIRECTIVE_HINT_RE,
    QUOTED_UNDERLINE_INSTRUCTION_HINT_RE,
    QUOTED_UNDERLINE_RE,
    SCORE_TEXT_RE,
    UNDERLINE_RE,
    _collect_blank_segments,
    _expand_lines_for_parsing,
    normalize_line,
)


SUPPORTED_EXTS = {".doc", ".docx"}
BLANK_SEGMENT_RE = re.compile(
    r"([_\uFF3F\uFE4D\uFE4E\u2014]{2,})\s*[\uFF08(]\s*(\d+(?:\.\d+)?)\s*\u5206\s*[\uFF09)]"
)
NUMERIC_RE = re.compile(r"\d+")
SUBQUESTION_HEAD_RE = re.compile(r"^\s*[\uFF08(]\d{1,3}[\uFF09)]")
HEADING_HINT_RE = re.compile(
    r"^\s*(?:\d{1,4}[\u3001\.\uFF0E]|[\u4e00-\u9fa5]{1,5}[\u3001\.\uFF0E]|[\uFF08(]\d{1,3}[\uFF09)])"
)
SOURCE_TAG_RE = re.compile(r"\[\s*(?:来源[:：].*?|Z\.X\.X\.K.*?)\s*\]")
LEADING_HEADING_TOKEN_RE = re.compile(r"^\s*(?:[一二三四五六七八九十百千]+[\u3001\.\uFF0E])")
LEADING_PAREN_NUM_RE = re.compile(r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]")


@dataclass
class FileReport:
    subject: str
    source_file: str
    sampled_rank: int
    status: str
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    main_pages: int = 0
    answer_pages: int = 0
    outline_nodes: int = 0
    pdf_outputs: List[str] = field(default_factory=list)


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
    numbers = NUMERIC_RE.findall(path.stem)
    if numbers:
        return int(numbers[0]), path.stem.lower()
    return 10**9, path.stem.lower()


def flatten_outline(nodes: List[Dict]) -> List[Dict]:
    flat: List[Dict] = []
    stack: List[Dict] = list(nodes)
    while stack:
        node = stack.pop(0)
        flat.append(node)
        children = node.get("children", [])
        if children:
            stack = list(children) + stack
    return flat


def iter_outline(nodes: List[Dict], parent_path: str = ""):
    for idx, node in enumerate(nodes, start=1):
        num = str(node.get("numbering") or "")
        path_token = num if num else f"idx{idx}"
        node_path = f"{parent_path}/{path_token}" if parent_path else path_token
        yield node, node_path
        children = node.get("children", [])
        if children:
            yield from iter_outline(children, node_path)


def collect_main_lines(processor: DocumentProcessor, file_path: Path) -> List[str]:
    ext = file_path.suffix.lower()
    answer_patterns = processor._compile_answer_patterns(None)

    if ext == ".doc":
        try:
            converted = processor._convert_doc_to_docx(file_path)
        except Exception:
            preview_pdf = processor._convert_office_to_pdf(file_path)
            page_lines = processor._extract_pdf_page_lines(preview_pdf)
            all_lines = [line for page in page_lines for line in page]
            main_lines, _ = processor._split_lines_by_answer(all_lines, answer_patterns)
            return main_lines
        try:
            doc = Document(str(converted))
            all_lines = processor._collect_docx_lines(doc)
            if not all_lines:
                preview_pdf = processor._convert_office_to_pdf(converted)
                page_lines = processor._extract_pdf_page_lines(preview_pdf)
                all_lines = [line for page in page_lines for line in page]
        except Exception:
            preview_pdf = processor._convert_office_to_pdf(converted)
            page_lines = processor._extract_pdf_page_lines(preview_pdf)
            all_lines = [line for page in page_lines for line in page]
        main_lines, _ = processor._split_lines_by_answer(all_lines, answer_patterns)
        return main_lines

    if ext == ".docx":
        try:
            doc = Document(str(file_path))
            all_lines = processor._collect_docx_lines(doc)
            if not all_lines:
                preview_pdf = processor._convert_office_to_pdf(file_path)
                page_lines = processor._extract_pdf_page_lines(preview_pdf)
                all_lines = [line for page in page_lines for line in page]
        except Exception:
            try:
                preview_pdf = processor._convert_office_to_pdf(file_path)
                page_lines = processor._extract_pdf_page_lines(preview_pdf)
                all_lines = [line for page in page_lines for line in page]
            except Exception:
                all_lines = processor._read_fallback_text_lines(file_path)
        main_lines, _ = processor._split_lines_by_answer(all_lines, answer_patterns)
        return main_lines

    if ext == ".pdf":
        page_lines = processor._extract_pdf_page_lines(file_path)
        answer_start_page = None
        for idx, lines in enumerate(page_lines):
            if processor._matches_answer("\n".join(lines), answer_patterns):
                answer_start_page = idx
                break
        if answer_start_page is None:
            return [line for page in page_lines for line in page]
        return [line for page in page_lines[:answer_start_page] for line in page]

    return []


def find_duplicate_numbering(nodes: List[Dict], node_path: str, warnings: List[str]) -> None:
    nums = [str(item.get("numbering") or "").strip() for item in nodes]
    nums = [item for item in nums if item]
    duplicates = sorted({item for item in nums if nums.count(item) > 1})
    if duplicates:
        warnings.append(f"{node_path or 'root'} has duplicate numbering: {','.join(duplicates)}")

    for idx, node in enumerate(nodes, start=1):
        num = str(node.get("numbering") or "")
        path_token = num if num else f"idx{idx}"
        child_path = f"{node_path}/{path_token}" if node_path else path_token
        children = node.get("children", [])
        if children:
            find_duplicate_numbering(children, child_path, warnings)


def validate_against_source(main_lines: List[str], details: Dict) -> Tuple[List[str], List[str]]:
    issues: List[str] = []
    warnings: List[str] = []
    expanded_lines = [
        normalize_line(line) for line in _expand_lines_for_parsing(main_lines) if normalize_line(line)
    ]

    outline_items = details.get("outlineItems", [])
    find_duplicate_numbering(outline_items, "", warnings)

    for node, node_path in iter_outline(outline_items):
        raw = normalize_line(str(node.get("rawText") or ""))
        line_number = int(node.get("lineNumber") or 0)

        if line_number <= 0 or line_number > len(expanded_lines):
            issues.append(f"{node_path}: lineNumber {line_number} out of range (1-{len(expanded_lines)})")
        else:
            source_line = expanded_lines[line_number - 1]
            if not _is_source_line_compatible_with_extracted_raw(source_line, raw, node_path):
                issues.append(
                    f"{node_path}: rawText mismatch at line {line_number}; "
                    f"source='{source_line[:80]}', extracted='{raw[:80]}'"
                )

        numbering = str(node.get("numbering") or "").strip()
        if numbering:
            prefix_pattern = rf"^\s*(?:[\uFF08(])?{re.escape(numbering)}(?:[\uFF09)])?(?:[\u3001\.\uFF0E])?"
            if not re.match(prefix_pattern, raw):
                warnings.append(f"{node_path}: numbering '{numbering}' does not align with raw prefix.")

        raw_source_for_slots = raw
        if QUOTED_UNDERLINE_RE.search(raw_source_for_slots) and (
            QUESTION_DIRECTIVE_HINT_RE.search(raw_source_for_slots)
            or QUOTED_UNDERLINE_INSTRUCTION_HINT_RE.search(raw_source_for_slots)
        ):
            raw_source_for_slots = normalize_line(QUOTED_UNDERLINE_RE.sub("", raw_source_for_slots))

        raw_underlines = [segment for segment, _ in _collect_blank_segments(raw_source_for_slots)]
        blank_text = str(node.get("blankText") or "")
        blank_segments = [(m.group(1), float(m.group(2))) for m in BLANK_SEGMENT_RE.finditer(blank_text)]

        if raw_underlines:
            if len(blank_segments) != len(raw_underlines):
                issues.append(
                    f"{node_path}: underline count mismatch raw={len(raw_underlines)} blank={len(blank_segments)}"
                )

            raw_score_hits = list(SCORE_TEXT_RE.finditer(raw))
            explicit_score = node.get("score")
            is_subquestion = bool(SUBQUESTION_HEAD_RE.match(raw))

            if is_subquestion and explicit_score is not None and float(explicit_score) > 0 and len(raw_underlines) > 1:
                total_blank_score = round(sum(score for _, score in blank_segments), 2)
                explicit_score_value = round(float(explicit_score), 2)
                if abs(total_blank_score - explicit_score_value) > 1e-6:
                    issues.append(
                        f"{node_path}: multi-blank subquestion score mismatch blankSum={total_blank_score} explicit={explicit_score_value}"
                    )

            explicit_score_value = float(explicit_score or 0.0) if explicit_score is not None else 0.0
            if (
                not raw_score_hits
                and explicit_score_value <= 0
                and any(abs(score) > 1e-9 for _, score in blank_segments)
            ):
                issues.append(f"{node_path}: no score in raw text but blank segment contains non-zero score.")

    if not outline_items:
        has_heading_hint = any(HEADING_HINT_RE.match(line) for line in expanded_lines)
        if has_heading_hint:
            issues.append("outlineItems is empty")
        else:
            warnings.append("outlineItems is empty (no heading-like tokens in source)")

    return issues, warnings


def _normalize_validation_compare_text(text: str) -> str:
    normalized = normalize_line(text or "")
    if not normalized:
        return ""
    normalized = SOURCE_TAG_RE.sub("", normalized)
    normalized = LEADING_HEADING_TOKEN_RE.sub("", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def _is_source_line_compatible_with_extracted_raw(source_line: str, raw: str, node_path: str) -> bool:
    if source_line == raw:
        return True

    normalized_source = _normalize_validation_compare_text(source_line)
    normalized_raw = _normalize_validation_compare_text(raw)
    if "Z.X.X.K" in normalized_source and "Z.X.X.K" in normalized_raw:
        source_probe = LEADING_PAREN_NUM_RE.sub("", normalized_source)
        raw_probe = LEADING_PAREN_NUM_RE.sub("", normalized_raw)
        if source_probe == raw_probe:
            return True
    if normalized_source and normalized_source == normalized_raw:
        return True

    # 父题号与子问在同一物理行时，抽取后的 rawText 只保留子问正文，允许按后缀匹配。
    if "/" in node_path and normalized_source.endswith(normalized_raw):
        return True

    return False


def copy_generated_pdfs(
    result_payload: Dict,
    subject_dir: Path,
    source_name: str,
    output_pdf_root: Path,
) -> List[str]:
    copied: List[str] = []
    safe_name = re.sub(r"[^A-Za-z0-9\u4e00-\u9fa5._-]+", "_", source_name)
    subject_pdf_dir = output_pdf_root / subject_dir.name / safe_name
    subject_pdf_dir.mkdir(parents=True, exist_ok=True)

    def copy_urls(urls: List[str], prefix: str) -> None:
        for idx, url in enumerate(urls, start=1):
            if not str(url).lower().endswith(".pdf"):
                continue
            if not str(url).startswith(settings.static_url_prefix + "/"):
                continue
            rel = str(url)[len(settings.static_url_prefix) + 1 :]
            src = settings.resolved_storage_dir / rel
            if not src.exists():
                continue
            dst = subject_pdf_dir / f"{prefix}_{idx}.pdf"
            shutil.copyfile(src, dst)
            copied.append(str(dst))

    copy_urls(result_payload.get("mainPages", []), "main")
    copy_urls(result_payload.get("answerPages", []), "answer")
    return copied


def process_subject(
    processor: DocumentProcessor,
    subject_dir: Path,
    sample_size: int,
    output_pdf_root: Path,
    temp_input_root: Path,
    task_counter_start: int,
) -> Tuple[List[FileReport], int]:
    files = [p for p in subject_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    files = sorted(files, key=natural_key)
    sampled = files[:sample_size]

    reports: List[FileReport] = []
    task_counter = task_counter_start

    if len(files) < sample_size:
        reports.append(
            FileReport(
                subject=subject_dir.name,
                source_file="",
                sampled_rank=0,
                status="subject_warning",
                warnings=[f"only {len(files)} files available, sampled all"],
            )
        )

    for rank, source in enumerate(sampled, start=1):
        task_counter += 1
        report = _process_one_file(
            processor=processor,
            subject_dir=subject_dir,
            source=source,
            rank=rank,
            output_pdf_root=output_pdf_root,
            temp_input_root=temp_input_root,
            task_id=task_counter,
        )
        reports.append(report)

    return reports, task_counter


def _process_one_file(
    processor: DocumentProcessor,
    subject_dir: Path,
    source: Path,
    rank: int,
    output_pdf_root: Path,
    temp_input_root: Path,
    task_id: int,
) -> FileReport:
    temp_subject = temp_input_root / subject_dir.name
    temp_subject.mkdir(parents=True, exist_ok=True)
    copied_file = temp_subject / source.name
    shutil.copyfile(source, copied_file)

    report = FileReport(
        subject=subject_dir.name,
        source_file=str(source),
        sampled_rank=rank,
        status="pending",
    )

    try:
        output = processor.process(
            task_id=task_id,
            file_path=str(copied_file),
            file_ext=copied_file.suffix.lower(),
            max_level=8,
            second_level_mode="auto",
            answer_section_patterns=None,
            score_patterns=None,
        )

        main_lines = collect_main_lines(processor, copied_file)
        issues, warnings = validate_against_source(main_lines, output.get("details", {}))
        report.issues.extend(issues)
        report.warnings.extend(warnings)

        result_payload = output.get("result", {})
        report.main_pages = len(result_payload.get("mainPages", []))
        report.answer_pages = len(result_payload.get("answerPages", []))
        report.outline_nodes = len(flatten_outline(output.get("details", {}).get("outlineItems", [])))
        report.pdf_outputs = copy_generated_pdfs(
            result_payload=result_payload,
            subject_dir=subject_dir,
            source_name=source.name,
            output_pdf_root=output_pdf_root,
        )

        report.status = "ok" if not report.issues else "mismatch"
    except Exception as exc:  # pragma: no cover - integration path
        report.status = "failed"
        report.issues.append(f"{type(exc).__name__}: {exc}")

    return report


def collect_subject_files(subject_dirs: List[Path]) -> Dict[str, List[Path]]:
    subject_files: Dict[str, List[Path]] = {}
    for subject_dir in subject_dirs:
        files = [p for p in subject_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
        subject_files[subject_dir.name] = sorted(files, key=natural_key)
    return subject_files


def build_round_robin_selection(
    subject_dirs: List[Path],
    subject_files: Dict[str, List[Path]],
    total_samples: int,
) -> List[Tuple[Path, Path, int]]:
    indexes = {subject_dir.name: 0 for subject_dir in subject_dirs}
    ranks = {subject_dir.name: 0 for subject_dir in subject_dirs}
    selected: List[Tuple[Path, Path, int]] = []

    while len(selected) < total_samples:
        progressed = False
        for subject_dir in subject_dirs:
            name = subject_dir.name
            files = subject_files.get(name, [])
            idx = indexes[name]
            if idx >= len(files):
                continue
            source = files[idx]
            indexes[name] = idx + 1
            ranks[name] += 1
            selected.append((subject_dir, source, ranks[name]))
            progressed = True
            if len(selected) >= total_samples:
                break
        if not progressed:
            break

    return selected


def process_selected_files(
    processor: DocumentProcessor,
    selected: List[Tuple[Path, Path, int]],
    output_pdf_root: Path,
    temp_input_root: Path,
    task_counter_start: int,
) -> Tuple[List[FileReport], int]:
    reports: List[FileReport] = []
    task_counter = task_counter_start

    for subject_dir, source, rank in selected:
        task_counter += 1
        report = _process_one_file(
            processor=processor,
            subject_dir=subject_dir,
            source=source,
            rank=rank,
            output_pdf_root=output_pdf_root,
            temp_input_root=temp_input_root,
            task_id=task_counter,
        )
        reports.append(report)

    return reports, task_counter


def summarize(reports: List[FileReport]) -> Dict:
    summary = {
        "total_entries": len(reports),
        "tested_files": len([r for r in reports if r.sampled_rank > 0]),
        "ok_files": len([r for r in reports if r.status == "ok"]),
        "mismatch_files": len([r for r in reports if r.status == "mismatch"]),
        "failed_files": len([r for r in reports if r.status == "failed"]),
        "subject_warnings": len([r for r in reports if r.status == "subject_warning"]),
    }
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Batch validate exam extraction against source documents.")
    parser.add_argument("--sample-size-per-subject", type=int, default=6, help="Sample size per subject.")
    parser.add_argument(
        "--total-samples",
        type=int,
        default=0,
        help="Total samples across all subjects using round-robin selection. 0 means disabled.",
    )
    parser.add_argument("--task-counter-start", type=int, default=880000, help="Initial task id counter.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    test_root = root / "test"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_root = test_root / f"batch_validation_{timestamp}"
    pdf_root = result_root / "generated_pdfs"
    temp_input_root = result_root / "_temp_inputs"
    pdf_root.mkdir(parents=True, exist_ok=True)
    temp_input_root.mkdir(parents=True, exist_ok=True)

    subject_dirs = [
        item
        for item in sorted(test_root.iterdir(), key=lambda p: p.name)
        if item.is_dir() and not item.name.startswith("batch_validation_") and not item.name.startswith("_")
    ]

    processor = DocumentProcessor()
    all_reports: List[FileReport] = []
    task_counter = args.task_counter_start

    print(f"subjects={len(subject_dirs)}")
    subject_files = collect_subject_files(subject_dirs)

    if args.total_samples > 0:
        selected = build_round_robin_selection(
            subject_dirs=subject_dirs,
            subject_files=subject_files,
            total_samples=args.total_samples,
        )
        selected_by_subject: Dict[str, int] = {}
        for subject_dir, _, _ in selected:
            selected_by_subject[subject_dir.name] = selected_by_subject.get(subject_dir.name, 0) + 1

        available_total = sum(len(files) for files in subject_files.values())
        if len(selected) < args.total_samples:
            all_reports.append(
                FileReport(
                    subject="",
                    source_file="",
                    sampled_rank=0,
                    status="subject_warning",
                    warnings=[
                        f"requested total {args.total_samples}, but only {len(selected)} selected from available {available_total} files",
                    ],
                )
            )

        print(f"selection_mode=round_robin total_requested={args.total_samples} total_selected={len(selected)}")
        for subject_dir in subject_dirs:
            print(f"subject={subject_dir.name} selected={selected_by_subject.get(subject_dir.name, 0)}")

        reports, task_counter = process_selected_files(
            processor=processor,
            selected=selected,
            output_pdf_root=pdf_root,
            temp_input_root=temp_input_root,
            task_counter_start=task_counter,
        )
        all_reports.extend(reports)

        for subject_dir in subject_dirs:
            tested = [r for r in reports if r.subject == subject_dir.name and r.sampled_rank > 0]
            mismatches = [r for r in tested if r.status == "mismatch"]
            failures = [r for r in tested if r.status == "failed"]
            print(
                f"subject={subject_dir.name} tested={len(tested)} "
                f"ok={len([r for r in tested if r.status == 'ok'])} "
                f"mismatch={len(mismatches)} failed={len(failures)}"
            )
    else:
        for subject_dir in subject_dirs:
            print(f"processing subject={subject_dir.name}")
            reports, task_counter = process_subject(
                processor=processor,
                subject_dir=subject_dir,
                sample_size=args.sample_size_per_subject,
                output_pdf_root=pdf_root,
                temp_input_root=temp_input_root,
                task_counter_start=task_counter,
            )
            all_reports.extend(reports)
            tested = [r for r in reports if r.sampled_rank > 0]
            mismatches = [r for r in tested if r.status == "mismatch"]
            failures = [r for r in tested if r.status == "failed"]
            print(
                f"subject={subject_dir.name} tested={len(tested)} "
                f"ok={len([r for r in tested if r.status == 'ok'])} "
                f"mismatch={len(mismatches)} failed={len(failures)}"
            )

    summary = summarize(all_reports)
    report_payload = {
        "generated_at": datetime.now().isoformat(),
        "result_root": str(result_root),
        "summary": summary,
        "reports": [r.__dict__ for r in all_reports],
    }

    report_json = result_root / "report.json"
    report_txt = result_root / "summary.txt"
    report_json.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "Batch Validation Summary",
        f"Generated: {report_payload['generated_at']}",
        f"Result Root: {result_root}",
        f"Subjects: {len(subject_dirs)}",
        f"Tested Files: {summary['tested_files']}",
        f"OK: {summary['ok_files']}",
        f"Mismatch: {summary['mismatch_files']}",
        f"Failed: {summary['failed_files']}",
        f"Subject Warnings: {summary['subject_warnings']}",
        "",
    ]
    report_txt.write_text("\n".join(lines), encoding="utf-8")

    deleted, failed = cleanup_test_pdfs(test_root)
    print(f"pdf_cleanup_deleted={deleted}")
    if failed:
        print(f"pdf_cleanup_failed={len(failed)}")
        for item in failed[:20]:
            print(item)

    print("done")
    print(f"report_json={report_json}")
    print(f"summary_txt={report_txt}")


if __name__ == "__main__":
    main()
