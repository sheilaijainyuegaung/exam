import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.services.rule_engine import (
    _collect_blank_segments,
    _collapse_choice_question_multi_blanks,
    _collapse_choice_semantic_leaf_multi_blanks,
    _distribute_outline_parent_remaining_score_to_unscored_children,
    _distribute_outline_parent_score_gap_to_slot_leaves,
    _distribute_outline_parent_score_to_numbered_zero_children,
    _distribute_outline_parent_score_to_slot_children,
    _enforce_choice_question_no_blank_and_no_children,
    _fill_scored_empty_bracket_leaf_blank_text,
    _fill_scored_question_mark_placeholder_blank_text,
    _fill_scored_underline_leaf_blank_text,
    _force_fill_zero_child_scores_under_scored_parent,
    _format_blank_segments_from_line,
    _parse_merged_blank_segment_score,
    _prune_conflicting_duplicate_numbered_children,
    _prune_empty_leaf_placeholder_nodes,
    _prune_number_only_placeholder_nodes,
    _strip_instruction_quoted_underlines_from_blank_text,
    analyze_document_lines,
    build_scores_tree,
    detect_pdf_header_footer,
    extract_symbol_texts,
    normalize_line,
    normalize_outline_blank_scores,
)

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None


DEFAULT_ANSWER_PATTERNS = [
    r"^\s*[【\[]?\s*(?:\u53C2\u8003\s*)?\u7B54\s*\u6848(?:\u4E0E\u89E3\u6790|\u89E3\u6790|\u90E8\u5206|\u9875)?\s*[】\]]?\s*$",
    r"^\s*[\u4e00-\u9fa5A-Za-z0-9\uff08\uff09()\u300a\u300b\-\s]{0,30}\u7B54\s*\u6848\s*$",
    r"\u89E3\u6790\u90E8\u5206",
]
ANSWER_HEADING_KEYWORD_RE = re.compile(r"(?:\u7B54\u6848|\u89E3\u6790)")
QUESTION_LINE_PREFIX_RE = re.compile(
    r"^\s*(?:\d{1,4}\s*[\u3001\.\uFF0E]|[\uFF08(]\d{1,3}[\uFF09)]|\u7b2c\s*\d+\s*\u9898)"
)
ANSWER_INSTRUCTION_HINT_RE = re.compile(
    r"(?:\u8bf7\u5c06|\u586b\u5199|\u586b\u6d82|\u5199\u5728|\u4f5c\u7b54|\u5bf9\u5e94|\u7b54\u9898\u5361|\u6ce8\u610f|\u987b\u77e5|\u8bf4\u660e)"
)
ANSWER_INSTRUCTION_VERB_RE = re.compile(
    r"(?:\u8bf7\u5c06|\u586b\u5199|\u586b\u6d82|\u5199\u5728|\u4f5c\u7b54|\u5bf9\u5e94|\u6ce8\u610f|\u987b\u77e5|\u8bf4\u660e)"
)
ANSWER_HEADING_NEGATIVE_RE = re.compile(
    r"(?:\u7b54\u6848\u65e0\u6548|\u7b54\u6848\u4e0d\u80fd\u7b54\u5728\u8bd5\u5377\u4e0a|\u4e0d\u6309\u4ee5\u4e0a\u8981\u6c42\u4f5c\u7b54|\u6ce8\u610f\u4e8b\u9879)"
)
ANSWER_SHEET_HEADING_RE = re.compile(r"(?:\u7b54\u9898\u5361|\u7b54\u9898\u5377|\u7b54\u5377|\u7b54\u9898\u7eb8)")
ANSWER_SPLIT_HINT_RE = re.compile(
    r"(?:\u53cb\u60c5\u63d0\u9192[:\uff1a]?\s*)?\u8bf7\u5c06\u7b54\u6848(?:\u586b\u5199|\u586b\u5728|\u5199\u5728).{0,20}\u7b54\u9898(?:\u5361|\u7eb8|\u5378)"
)
SECTION_HEADING_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"[IVXLCM\u2160-\u2169]+[\u3001\.\uFF0E]|"
    r"[\u4e00-\u9fa5\d]+[\u3001\.\uFF0E]|"
    r"\u7b2c\s*[一二三四五六七八九十\u4e00-\u9fa5\d]+\s*\u90e8\u5206"
    r")"
)
QUESTION_HEADING_WITH_ANSWER_WORD_RE = re.compile(
    r"(?:正确答案|最佳答案|最佳选项|选择.*答案)"
)
QUESTION_SECTION_HINT_RE = re.compile(
    r"(?:听|读|阅读|完形|填空|单选|选择|对话|短文|词汇|语法|书面|任务|判断|解析|材料)"
)
TAIL_ANSWER_MATERIAL_HEADING_RE = re.compile(
    r"^\s*(?:[IVXLCM\u2160-\u2169\u4e00-\u9fa5\d]+[\u3001\.\uFF0E]\s*)?"
    r"(?:\u542c\u529b\u6750\u6599|\u542c\u529b\u539f\u6587|\u542c\u529b\u6587\u672c|"
    r"(?:\u53c2\u8003\s*)?\u7b54\u6848(?:\u4e0e\u89e3\u6790|\u89e3\u6790)?|\u89e3\u6790\u90e8\u5206)\s*$",
    flags=re.IGNORECASE,
)
TAIL_ANSWER_FOLLOW_LINE_RE = re.compile(
    r"^\s*(?:\u7b2c[一二三四五六七八九十\d]+\u90e8\u5206|"
    r"Text\s*\d+|"
    r"\d+\s*[\.\uFF0E]|"
    r"[A-D\uFF21-\uFF24]\s*[\.\uFF0E\u3001]|"
    r"[MW\u7537\u5973]\s*[:\uFF1A])",
    flags=re.IGNORECASE,
)
ARABIC_QUESTION_LINE_RE = re.compile(r"^\s*(\d{1,4})[\u3001\.\uFF0E]\s*(.*)$")
QUESTION_HINT_RE = re.compile(
    r"(?:\u4e0b\u5217|\u5982\u56fe|\u8bf7|\u6c42|\u8bf4\u660e|\u6b63\u786e|\u9519\u8bef|\u4f55\u4ee5|"
    r"\u4e3a\u4ec0\u4e48|\u662f\u5426|\u6709\u5173|\u73b0\u8c61|\u5b9e\u9a8c)"
)
QUESTION_DIRECTIVE_TEXT_RE = re.compile(
    r"(?:\u8d4f\u6790|\u6982\u62ec|\u89e3\u91ca|\u7ffb\u8bd1|\u5224\u65ad|\u9009\u62e9|\u5199\u51fa|"
    r"\u8bf7|\u56de\u7b54|\u5b8c\u6210|\u4f5c\u7b54|\u7ed3\u5408|\u6839\u636e|\u4f9d\u636e|"
    r"\u6309\u8981\u6c42|\u5185\u5bb9\u5177\u4f53|\u8bed\u53e5\u901a\u987a|\u4e0d\u5f97|"
    r"\u5b57\u6570|\u4f5c\u6587|\u5199\u4f5c|\u6807\u8bed)"
)
SECTION_LIKE_TITLE_RE = re.compile(
    r"(?:积累|运用|阅读|文言文|现代文|综合|写作|作文|表达|名著|语段|诗歌|文言|课外|古诗|古文|材料)"
)
ANSWER_KEY_TOKEN_RE = re.compile(
    r"(?:[A-D]\b|[\uFF08(]\d+[\uFF09)]|[=]|(?:\d+(?:\.\d+)?\s*(?:m/s|cm|mm|kg|N|J|V|A|W|s|Hz|Pa|%)))",
    flags=re.IGNORECASE,
)
ANSWER_EXPLANATION_HINT_RE = re.compile(
    r"(?:\u672c\u9898\u8003\u67e5|\u89e3\u6790|\u6545\u9009|\u7b26\u5408\u9898\u610f|\u4e0d\u5408\u9898\u610f|"
    r"\u8bf4\u6cd5\u6b63\u786e|\u8bf4\u6cd5\u9519\u8bef|\u4f9d\u636e\u6240\u5b66|\u6839\u636e(?:\u6750\u6599|\u9898\u610f|\u6240\u5b66)|"
    r"\u53c2\u8003\u7b54\u6848|\u7b54\u6848(?:\u4e3a|\u662f)|\u6b63\u786e\u9009\u9879|\u9009\u9879\u6b63\u786e)"
)
INLINE_ANSWER_MARKER_RE = re.compile(r"(?:\u53C2\u8003\s*)?\u7B54\u6848\s*[:\uFF1A]")
TAIL_COMPACT_ANSWER_LINE_RE = re.compile(
    r"^\s*(?:[IVXLCM\u2160-\u2169\u4e00-\u9fa5]{1,8}\s*[\u3001\.\uFF0E]\s*)?\d{1,3}\s*[\u3001\.\uFF0E]"
)
TAIL_COMPACT_ANSWER_HEADING_RE = re.compile(
    r"(?:\u7efc\u5408\u7d20\u8d28\u8bc4\u4ef7|\u9636\u6bb5\u6d4b\u8bd5|\u5355\u5143\u6d4b\u8bd5|\u5355\u5143\u68c0\u6d4b|\u6d4b\u8bc4)"
)
TAIL_COMPACT_EXPLICIT_KEY_RE = re.compile(
    r"(?:"
    r"[A-D\uFF21-\uFF24]\s*[\.\uFF0E\u3001](?=(?:\s|$))|"
    r"[√×](?=(?:\s|$|[,，;；]))|"
    r"[\uFF08(]\s*\d+\s*[\uFF09)]\s*[A-D\uFF21-\uFF24√×](?=(?:\s|$|[,，;；]))"
    r")",
    flags=re.IGNORECASE,
)
DOCX_FIELD_CODE_RE = re.compile(
    r"INCLUDEPICTURE\s+\"[^\"]*\"(?:\s+\\\*\s+[A-Z]+)*",
    flags=re.IGNORECASE,
)
DOCX_FIELD_SWITCH_RE = re.compile(
    r"\\\*\s*MERGEFORMAT(?:INET)?",
    flags=re.IGNORECASE,
)
DOCX_LAYOUT_ARTIFACT_RE = re.compile(r"x§k§b\s*\d*", flags=re.IGNORECASE)
TAIL_INLINE_ANSWER_SECTION_WITH_KEYS_RE = re.compile(
    r"^\s*(?:[IVXLCM\u2160-\u2169]+|[一二三四五六七八九十百千万\d]{1,6})\s*[\u3001\.\uFF0E:：]\s*"
    r"(?:\u9009\u62e9\u9898|\u5355\u9009\u9898|\u591a\u9009\u9898|\u586b\u7a7a\u9898|\u5224\u65ad\u9898|"
    r"\u5b9e\u9a8c\u9898|\u8ba1\u7b97\u9898|\u7b80\u7b54\u9898|\u7efc\u5408\u9898|\u89e3\u7b54\u9898|"
    r"\u4f5c\u56fe\u9898|\u975e\u9009\u62e9\u9898|\u542c\u529b|\u9605\u8bfb|\u4f5c\u6587|\u5199\u4f5c)\s*"
    r"(?:[:：]\s*(.*))?$",
    flags=re.IGNORECASE,
)
TAIL_SECTION_INLINE_ANSWER_RE = re.compile(
    r"^\s*(?:[IVXLCM\u2160-\u2169]+|[一二三四五六七八九十百千万]{1,6})\s*[\u3001\.\uFF0E:：]\s*(.+)$",
    flags=re.IGNORECASE,
)
TAIL_OPTION_LINE_RE = re.compile(
    r"^\s*[A-D\uFF21-\uFF24a-d\uFF41-\uFF44]\s*[\u3001\.\uFF0E]\s*"
)
INLINE_NUMBERED_ITEM_RE = re.compile(r"\d{1,3}\s*[\.\uFF0E\u3001]")
ANSWER_SECTION_HEADING_RE = re.compile(
    r"^\s*([一二三四五六七八九十百千万]+|[0-9\uff10-\uff19]{1,3})\s*[\u3001\.\uff0e]"
)
ANSWER_SECTION_SCORE_RE = re.compile(
    r"[\uFF08(]\s*(?:\u5171|\u603b\u8ba1|\u603b\u5206)?\s*(\d+(?:\.\d+)?)\s*\u5206\s*[\uFF09)]"
)


class DocumentProcessor:
    def __init__(self):
        settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        settings.pages_dir.mkdir(parents=True, exist_ok=True)
        self._font_path = self._resolve_font_path()
        self._font_body = self._load_font(34)
        self._font_footer = self._load_font(24)

    def _decode_process_output(self, payload: bytes) -> str:
        if not payload:
            return ""
        for encoding in ("utf-8", "gbk", "utf-16le", "latin1"):
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                continue
        return payload.decode("utf-8", errors="ignore")

    def _read_fallback_text_lines(self, file_path: Path) -> List[str]:
        try:
            raw = file_path.read_bytes()
        except OSError:
            return [str(file_path.name)]

        decoded = self._decode_process_output(raw)
        cleaned = re.sub(r"[\x00-\x08\x0b-\x1f]+", " ", decoded)
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if lines:
            return lines
        return [str(file_path.name)]

    def _create_fallback_pdf(self, task_id: int, lines: List[str], tag: str = "fallback_preview") -> Path:
        filename = f"{task_id}_{tag}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = settings.pages_dir / filename
        text = "\n".join(lines[:200]) if lines else "Unsupported document content."

        if fitz is not None:
            document = fitz.open()
            try:
                page = document.new_page(width=595, height=842)
                rect = fitz.Rect(40, 40, 555, 802)
                page.insert_textbox(rect, text, fontsize=11, fontname="helv")
                document.save(str(output_path))
            finally:
                document.close()
            return output_path

        image = self._build_text_page_image(lines[:80], 1, "fallback")
        try:
            image.save(output_path, format="PDF")
        finally:
            image.close()
        return output_path

    def process(
        self,
        task_id: int,
        file_path: str,
        file_ext: str,
        max_level: int,
        second_level_mode: str,
        answer_section_patterns: Optional[List[str]],
        score_patterns: Optional[List[str]],
        layout_adjustments: Optional[Dict[str, float]] = None,
    ) -> Dict:
        ext = file_ext.lower()
        source_path = Path(file_path)
        preview_source_path = source_path
        if ext == ".doc":
            try:
                source_path = self._convert_doc_to_docx(source_path)
                ext = ".docx"
                preview_source_path = source_path
            except Exception:
                # Some legacy .doc files cannot be converted to .docx reliably.
                # Fallback to direct PDF conversion and process as PDF text.
                source_path = self._convert_office_to_pdf(source_path)
                ext = ".pdf"
                preview_source_path = source_path

        answer_patterns = self._compile_answer_patterns(answer_section_patterns)

        if ext == ".docx":
            preview_docx_path = preview_source_path
            if layout_adjustments:
                try:
                    preview_docx_path = self._create_adjusted_docx_for_preview(
                        source_docx=source_path,
                        task_id=task_id,
                        layout_adjustments=layout_adjustments,
                    )
                except Exception:
                    preview_docx_path = preview_source_path
            (
                all_lines,
                main_lines,
                answer_lines,
                main_page_urls,
                answer_page_urls,
                header_footer_items,
            ) = self._process_docx(task_id, source_path, answer_patterns, preview_source_path=preview_docx_path)
        elif ext == ".pdf":
            (
                all_lines,
                main_lines,
                answer_lines,
                main_page_urls,
                answer_page_urls,
                header_footer_items,
            ) = self._process_pdf(task_id, source_path, answer_patterns)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        analysis = analyze_document_lines(
            main_lines,
            max_level=max_level,
            second_level_mode=second_level_mode,
            score_patterns=score_patterns,
        )
        if self._repair_missing_root_heading_from_child_restart(analysis["outlineItems"]):
            analysis["scores"] = self._recalculate_outline_scores_after_backfill(analysis["outlineItems"])
        if answer_lines:
            if self._backfill_outline_root_scores_from_answer_lines(analysis["outlineItems"], answer_lines):
                analysis["scores"] = self._recalculate_outline_scores_after_backfill(analysis["outlineItems"])
        if self._repair_outline_extraction_artifacts(analysis["outlineItems"]):
            analysis["scores"] = self._recalculate_outline_scores_after_backfill(analysis["outlineItems"])
        if self._repair_misnested_arabic_section_roots(analysis["outlineItems"]):
            analysis["scores"] = self._recalculate_outline_scores_after_backfill(analysis["outlineItems"])
        if self._repair_overflow_arabic_children_to_root_siblings(analysis["outlineItems"]):
            analysis["scores"] = self._recalculate_outline_scores_after_backfill(analysis["outlineItems"])
        symbols = extract_symbol_texts(all_lines)
        analysis["ruleHits"]["symbols"] = len(symbols)
        analysis["ruleHits"]["pages_main"] = len(main_page_urls)
        analysis["ruleHits"]["pages_answer"] = len(answer_page_urls)
        analysis["ruleHits"]["answer_lines"] = len(answer_lines)

        return {
            "result": {
                "answerPages": answer_page_urls,
                "mainPages": main_page_urls,
                "questionType": int(analysis["questionType"]),
                "scores": analysis["scores"],
            },
            "details": {
                "outlineItems": analysis["outlineItems"],
                "headerFooterItems": header_footer_items,
                "symbolTexts": symbols,
                "detectedMaxLevel": int(analysis["detectedMaxLevel"]),
                "secondLevelModeDetected": analysis["secondLevelModeDetected"],
            },
            "ruleHits": analysis["ruleHits"],
        }

    def _normalize_numbering_key(self, value: object) -> str:
        text = re.sub(r"\s+", "", str(value or "").strip())
        if not text:
            return ""
        text = text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        if text.isdigit():
            try:
                return str(int(text))
            except ValueError:
                return text
        return text

    def _extract_answer_heading_score_map(self, answer_lines: List[str]) -> Dict[str, float]:
        score_map: Dict[str, float] = {}
        for raw in answer_lines:
            line = re.sub(r"\s+", " ", (raw or "")).strip()
            if not line:
                continue
            heading_match = ANSWER_SECTION_HEADING_RE.match(line)
            if heading_match is None:
                continue
            score_match = ANSWER_SECTION_SCORE_RE.search(line)
            if score_match is None:
                continue
            try:
                score_value = float(score_match.group(1))
            except (TypeError, ValueError):
                continue
            if score_value <= 0:
                continue
            numbering_key = self._normalize_numbering_key(heading_match.group(1))
            if not numbering_key:
                continue
            score_map[numbering_key] = score_value
        return score_map

    def _parse_arabic_numbering(self, value: object) -> Optional[int]:
        text = self._normalize_numbering_key(value)
        if not text or not text.isdigit():
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def _aggregate_outline_node_score(self, node: Dict) -> float:
        children = node.get("children") or []
        if children:
            child_total = sum(self._aggregate_outline_node_score(child) for child in children)
            if child_total > 0:
                return round(float(child_total), 2)
        try:
            score = float(node.get("score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        return round(score, 2)

    def _find_child_restart_split_index(self, children: List[Dict]) -> Optional[int]:
        if len(children) < 4:
            return None
        numbers: List[int] = []
        for child in children:
            parsed = self._parse_arabic_numbering(child.get("numbering"))
            if parsed is None:
                return None
            numbers.append(parsed)
        if not numbers or numbers[0] != 1:
            return None
        for idx in range(1, len(numbers)):
            current = numbers[idx]
            previous = numbers[idx - 1]
            if current <= previous:
                if current == 1 and idx >= 2 and len(numbers) - idx >= 2:
                    return idx
                return None
        return None

    def _repair_missing_root_heading_from_child_restart(self, outline_items: List[Dict]) -> bool:
        changed = False
        idx = 0
        while idx < len(outline_items) - 1:
            current = outline_items[idx]
            following = outline_items[idx + 1]
            current_number = self._parse_arabic_numbering(current.get("numbering"))
            next_number = self._parse_arabic_numbering(following.get("numbering"))
            if current_number is None or next_number is None or next_number <= current_number + 1:
                idx += 1
                continue

            children = list(current.get("children") or [])
            split_index = self._find_child_restart_split_index(children)
            if split_index is None:
                idx += 1
                continue

            retained_children = children[:split_index]
            moved_children = children[split_index:]
            if len(retained_children) < 2 or len(moved_children) < 2:
                idx += 1
                continue

            missing_number = str(current_number + 1)
            current["children"] = retained_children
            current["score"] = build_scores_tree(retained_children)["score"]

            new_root = {
                "lineNumber": moved_children[0].get("lineNumber"),
                "level": current.get("level", 1),
                "numbering": missing_number,
                "title": "",
                "rawText": f"{missing_number}、",
                "blankText": "",
                "score": build_scores_tree(moved_children)["score"],
                "children": moved_children,
            }
            outline_items.insert(idx + 1, new_root)
            changed = True
            idx += 2
        return changed

    def _is_reading_root_node(self, node: Dict) -> bool:
        title = re.sub(r"\s+", "", str(node.get("title") or node.get("rawText") or ""))
        return "阅读" in title

    def _is_reading_title_blank_node(self, node: Dict) -> bool:
        if str(node.get("numbering") or "").strip():
            return False
        if node.get("children"):
            return False
        raw = str(node.get("rawText") or "").strip()
        if not raw:
            return False
        if not re.match(r"^[_\uFF3F\uFE4D\uFE4E\u2014]{2,}\s*[\u00b7\u2022·\s\u4e00-\u9fa5]{1,16}$", raw):
            return False
        return bool(re.search(r"[\u4e00-\u9fa5]", raw))

    def _is_reading_scored_article_title_leaf(self, node: Dict) -> bool:
        if str(node.get("numbering") or "").strip():
            return False
        if node.get("children"):
            return False
        try:
            score_value = float(node.get("score") or 0)
        except (TypeError, ValueError):
            score_value = 0.0
        if score_value <= 0:
            return False

        raw = re.sub(r"\s+", "", str(node.get("rawText") or node.get("title") or ""))
        if not raw:
            return False
        if QUESTION_DIRECTIVE_TEXT_RE.search(raw):
            return False
        if re.search(r"[？?]", raw):
            return False
        if re.search(r"[_\uFF3F\uFE4D\uFE4E\u2014]{2,}", raw):
            return False
        if re.search(r"[，,。；;：:]", raw):
            return False
        if re.search(r"(?:阅读|回答|完成)\s*\d{1,3}\s*[-~\uFF5E\u2014至到]\s*\d{1,3}\s*题", raw):
            return False
        return bool(re.search(r"[\u4e00-\u9fa5]", raw)) and len(raw) <= 24

    def _is_reading_paragraph_marker_leaf(self, node: Dict) -> bool:
        if node.get("children"):
            return False
        try:
            score_value = float(node.get("score") or 0)
        except (TypeError, ValueError):
            score_value = 0.0
        if score_value > 0:
            return False

        raw = str(node.get("rawText") or "").strip()
        if not raw:
            return False
        if not re.match(r"^[\uFF08(]\s*\d{1,3}\s*[\uFF09)]", raw):
            return False
        if re.search(r"[_\uFF3F\uFE4D\uFE4E\u2014]{2,}", raw):
            return False
        if re.search(r"[？?]", raw):
            return False
        if QUESTION_DIRECTIVE_TEXT_RE.search(raw):
            return False
        punct_count = len(re.findall(r"[，,。；;：:]", raw))
        return len(raw) >= 24 and punct_count >= 2

    def _extract_score_only_line_value(self, text: object) -> Optional[float]:
        match = re.fullmatch(
            r"\s*(?:[\uFF08(]\s*(\d+(?:\.\d+)?)\s*分\s*[\uFF09)]|[\uFF08(]\s*(\d+(?:\.\d+)?)\s*[\uFF09)]\s*分)\s*",
            str(text or ""),
        )
        if match is None:
            return None
        try:
            value = match.group(1) or match.group(2)
            return float(value)
        except (TypeError, ValueError):
            return None

    def _extract_inline_heading_score_value(self, text: object) -> Optional[float]:
        match = re.search(
            r"[\uFF08(]\s*(?:共|总计|总分)?\s*(\d+(?:\.\d+)?)\s*分\s*[\uFF09)]",
            str(text or ""),
        )
        if match is None:
            return None
        try:
            return float(match.group(1))
        except (TypeError, ValueError):
            return None

    def _merge_blank_text(self, target: Dict, blank_text: object) -> None:
        incoming = str(blank_text or "").strip()
        if not incoming:
            return
        current = str(target.get("blankText") or "").strip()
        if not current:
            target["blankText"] = incoming
            return
        if incoming in current.split():
            return
        target["blankText"] = f"{current} {incoming}".strip()

    def _merge_reference_child_into_parent(self, parent: Dict, child: Dict) -> None:
        child_raw = str(child.get("rawText") or "").strip()
        parent_raw = str(parent.get("rawText") or "").strip()
        if child_raw and child_raw not in parent_raw:
            parent["rawText"] = f"{parent_raw} {child_raw}".strip() if parent_raw else child_raw

        child_title = str(child.get("title") or "").strip()
        parent_title = str(parent.get("title") or "").strip()
        if child_title and child_title not in parent_title:
            parent["title"] = f"{parent_title} {child_title}".strip() if parent_title else child_title

        self._merge_blank_text(parent, child.get("blankText"))

    def _has_parent_reference_to_number(self, node: Dict, number_text: object) -> bool:
        number = self._normalize_numbering_key(number_text)
        if not number:
            return False
        raw = str(node.get("rawText") or "")
        if not raw:
            return False
        return bool(
            re.search(
                rf"第\s*[\uFF08(]?\s*{re.escape(number)}\s*[\uFF09)]?\s*(?:自然段|段|小节|节|句|行|幅图|图|空)",
                raw,
            )
        )

    def _is_reference_continuation_node(self, node: Dict) -> bool:
        raw = str(node.get("rawText") or "").strip()
        if not raw:
            return False
        if self._extract_score_only_line_value(raw) is not None:
            return True
        head = re.match(r"^[\uFF08(]\s*\d{1,3}\s*[\uFF09)]", raw)
        if head is None:
            return False

        tail = normalize_line(raw[head.end() :])
        if not tail:
            return True
        if self._extract_score_only_line_value(tail) is not None:
            return True
        if _collect_blank_segments(tail):
            return False
        if re.search(r"[？?\u3002!！;；:：]", tail):
            return False

        # 仅把短碎片当作“引用编号续行”；长句（尤其带中文正文）不参与并入。
        compact_tail = re.sub(r"[\s\u3000,\uFF0C\.\u3002、\-—:：;；()（）\[\]【】]", "", tail)
        cjk_count = len(re.findall(r"[\u4e00-\u9fa5]", compact_tail))
        if cjk_count >= 8:
            return False
        if len(compact_tail) > 16:
            return False
        return True

    def _find_misnested_restart_split_index(self, children: List[Dict]) -> Optional[int]:
        if len(children) < 3:
            return None
        numbers: List[int] = []
        for child in children:
            parsed = self._parse_arabic_numbering(child.get("numbering"))
            if parsed is None:
                return None
            numbers.append(parsed)

        for idx in range(1, len(numbers) - 1):
            if numbers[idx] != 1:
                continue
            tail = numbers[idx:]
            if tail[0] != 1:
                continue
            is_non_decreasing = all(curr >= prev for prev, curr in zip(tail, tail[1:]))
            if not is_non_decreasing:
                continue
            if tail != list(range(1, len(tail) + 1)):
                continue
            return idx
        return None

    def _repair_outline_extraction_artifacts(self, outline_items: List[Dict]) -> bool:
        changed = False

        def _restore_statement_option_parent(node: Dict) -> bool:
            children = list(node.get("children") or [])
            if len(children) < 2:
                return False
            title = str(node.get("title") or "").strip()
            raw = str(node.get("rawText") or "").strip()
            if not title or not raw:
                return False
            if "填序号" not in title and "填入序号" not in title:
                return False
            if any((child.get("children") or []) for child in children):
                return False
            if not all(str(child.get("numbering") or "").strip().isdigit() for child in children):
                return False
            if not all(float(child.get("score") or 0.0) > 0 for child in children):
                return False
            child_raws = [str(child.get("rawText") or "").strip() for child in children]
            if not all(child_raw and child_raw in raw for child_raw in child_raws):
                return False

            numbering = str(node.get("numbering") or "").strip()
            if not numbering:
                return False
            delimiter_match = re.match(rf"^\s*{re.escape(numbering)}\s*([、\.\uFF0E])", raw)
            delimiter = delimiter_match.group(1) if delimiter_match is not None else "."
            rebuilt_raw = f"{numbering}{delimiter}{title}"
            if raw == rebuilt_raw and not str(node.get("blankText") or "").strip():
                return False
            node["rawText"] = rebuilt_raw
            node["blankText"] = ""
            return True

        def _restore_leaf_blank_from_title(node: Dict) -> bool:
            if node.get("children"):
                return False
            if float(node.get("score") or 0.0) <= 0:
                return False
            if str(node.get("blankText") or "").strip():
                return False
            raw = str(node.get("rawText") or "")
            title = str(node.get("title") or "")
            if not title:
                return False
            if _collect_blank_segments(raw):
                return False
            if not _collect_blank_segments(title):
                return False
            filled = _format_blank_segments_from_line(title, float(node.get("score") or 0.0))
            if not filled:
                return False
            node["blankText"] = filled
            if raw.strip() != title.strip():
                prefix_match = re.match(
                    r"^\s*((?:[\uFF08(]\s*\d{1,3}\s*[\uFF09)]|\d{1,4}\s*[、\.\uFF0E]))\s*",
                    raw,
                )
                if prefix_match is not None and not re.match(
                    r"^\s*(?:[\uFF08(]\s*\d{1,3}\s*[\uFF09)]|\d{1,4}\s*[、\.\uFF0E])",
                    title,
                ):
                    node["rawText"] = f"{prefix_match.group(1)}{title}".strip()
                else:
                    node["rawText"] = title
            return True

        def _restore_leaf_raw_from_title(node: Dict) -> bool:
            if node.get("children"):
                return False
            raw = str(node.get("rawText") or "")
            title = str(node.get("title") or "")
            if not raw or not title or raw.strip() == title.strip():
                return False
            raw_blank_count = len(_collect_blank_segments(raw))
            title_blank_count = len(_collect_blank_segments(title))
            if title_blank_count <= raw_blank_count:
                return False
            prefix_match = re.match(
                r"^\s*((?:[\uFF08(]\s*\d{1,3}\s*[\uFF09)]|\d{1,4}\s*[、\.\uFF0E]))\s*",
                raw,
            )
            if prefix_match is not None and not re.match(
                r"^\s*(?:[\uFF08(]\s*\d{1,3}\s*[\uFF09)]|\d{1,4}\s*[、\.\uFF0E])",
                title,
            ):
                node["rawText"] = f"{prefix_match.group(1)}{title}".strip()
            else:
                node["rawText"] = title
            return True

        def _raise_leaf_score_to_explicit_blank_total(node: Dict) -> bool:
            if node.get("children"):
                return False
            blank_text = str(node.get("blankText") or "").strip()
            if not blank_text:
                return False
            parsed_scores = []
            for token in blank_text.split():
                score = _parse_merged_blank_segment_score(token)
                if score is None:
                    return False
                parsed_scores.append(float(score))
            if not parsed_scores:
                return False
            explicit_total = round(sum(parsed_scores), 2)
            current_score = round(float(node.get("score") or 0.0), 2)
            if explicit_total <= current_score:
                return False
            node["score"] = explicit_total
            return True

        def _promote_misnested_restart_children(nodes: List[Dict]) -> bool:
            local_changed = False
            idx = 0
            while idx < len(nodes):
                node = nodes[idx]
                children = list(node.get("children") or [])
                split_idx = self._find_misnested_restart_split_index(children)
                if split_idx is None:
                    idx += 1
                    continue
                retained_children = children[:split_idx]
                moved_children = children[split_idx:]
                if not retained_children or len(moved_children) < 2:
                    idx += 1
                    continue
                node_score = float(node.get("score") or 0.0)
                moved_total = sum(self._aggregate_outline_node_score(child) for child in moved_children)
                if moved_total <= node_score:
                    idx += 1
                    continue
                node["children"] = retained_children
                target_level = int(node.get("level", 1) or 1)
                for moved in moved_children:
                    moved_level = int(moved.get("level", target_level + 1) or (target_level + 1))
                    if moved_level != target_level:
                        self._shift_outline_level(moved, target_level - moved_level)
                nodes[idx + 1 : idx + 1] = moved_children
                local_changed = True
                idx += len(moved_children) + 1
            return local_changed

        def walk(nodes: List[Dict], parent: Optional[Dict] = None, in_reading_context: bool = False) -> bool:
            nonlocal changed
            if not nodes:
                return False

            local_changed = False
            cleaned: List[Dict] = []
            for node in nodes:
                current_reading_context = in_reading_context or self._is_reading_root_node(node)
                if walk(node.get("children") or [], node, current_reading_context):
                    local_changed = True

                if parent is not None:
                    score_only_value = self._extract_score_only_line_value(node.get("rawText"))
                    if score_only_value is not None:
                        parent["score"] = float(score_only_value)
                        local_changed = True
                        continue

                if parent is not None and in_reading_context and self._is_reading_title_blank_node(node):
                    local_changed = True
                    continue

                if parent is not None and in_reading_context and self._is_reading_scored_article_title_leaf(node):
                    local_changed = True
                    continue

                if parent is not None and in_reading_context and self._is_reading_paragraph_marker_leaf(node):
                    local_changed = True
                    continue

                if _restore_statement_option_parent(node):
                    local_changed = True

                if _restore_leaf_blank_from_title(node):
                    local_changed = True

                if _restore_leaf_raw_from_title(node):
                    local_changed = True

                if _raise_leaf_score_to_explicit_blank_total(node):
                    local_changed = True

                node_number = self._normalize_numbering_key(node.get("numbering"))
                if node_number and self._is_reference_continuation_node(node):
                    reference_anchor = next(
                        (
                            candidate
                            for candidate in cleaned + nodes
                            if candidate is not node and self._has_parent_reference_to_number(candidate, node_number)
                        ),
                        None,
                    )
                    if reference_anchor is not None:
                        self._merge_reference_child_into_parent(reference_anchor, node)
                        local_changed = True
                        continue
                    if parent is not None and self._has_parent_reference_to_number(parent, node_number):
                        self._merge_reference_child_into_parent(parent, node)
                        local_changed = True
                        continue

                cleaned.append(node)

            if _promote_misnested_restart_children(cleaned):
                local_changed = True

            if len(cleaned) != len(nodes):
                nodes[:] = cleaned
            changed = changed or local_changed
            return local_changed

        walk(outline_items, None, False)
        return changed

    def _shift_outline_level(self, node: Dict, delta: int) -> None:
        if not isinstance(node, dict) or delta == 0:
            return
        current_level = int(node.get("level", 1) or 1)
        node["level"] = max(1, current_level + delta)
        for child in node.get("children") or []:
            self._shift_outline_level(child, delta)

    def _is_section_like_node(self, node: Dict, min_score: float = 0.0) -> bool:
        score_value = float(node.get("score") or 0.0)
        if score_value < float(min_score):
            return False
        text = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        if not text:
            return False
        if QUESTION_DIRECTIVE_TEXT_RE.search(text) or re.search(r"[？?]", text):
            return False
        return bool(SECTION_LIKE_TITLE_RE.search(text))

    def _find_overflow_arabic_child_split_index(self, parent: Dict, children: List[Dict]) -> Optional[int]:
        parent_num = self._parse_arabic_numbering(parent.get("numbering"))
        if parent_num is None or len(children) < 2:
            return None

        def _is_arabic_question_raw(node: Dict) -> bool:
            raw_text = str(node.get("rawText") or "").strip()
            return bool(re.match(r"^\s*\d{1,4}\s*[\u3001\.\uFF0E]", raw_text))

        split_index: Optional[int] = None
        expected_number = parent_num + 1
        for idx, child in enumerate(children):
            child_num = self._parse_arabic_numbering(child.get("numbering"))
            if child_num is None or not _is_arabic_question_raw(child):
                continue
            if child_num >= expected_number and float(child.get("score") or 0.0) > 0:
                split_index = idx
                break

        if split_index is None:
            return None

        overflow = children[split_index:]
        if not overflow:
            return None
        for child in overflow:
            child_num = self._parse_arabic_numbering(child.get("numbering"))
            if child_num is None or not _is_arabic_question_raw(child):
                return None
            if float(child.get("score") or 0.0) <= 0:
                return None
        return split_index

    def _repair_overflow_arabic_children_to_root_siblings(self, outline_items: List[Dict]) -> bool:
        if not outline_items:
            return False

        changed = False
        idx = 0
        while idx < len(outline_items):
            node = outline_items[idx]
            children = list(node.get("children") or [])
            split_index = self._find_overflow_arabic_child_split_index(node, children)
            if split_index is None:
                idx += 1
                continue

            kept_children = children[:split_index]
            overflow_children = children[split_index:]
            if not overflow_children:
                idx += 1
                continue

            node["children"] = kept_children
            explicit_score = self._extract_inline_heading_score_value(node.get("rawText"))
            if explicit_score is not None and explicit_score > 0:
                node["score"] = explicit_score
            for child in overflow_children:
                child_level = int(child.get("level", 1) or 1)
                if child_level != 1:
                    self._shift_outline_level(child, 1 - child_level)

            outline_items[idx + 1 : idx + 1] = overflow_children
            changed = True
            idx += 1

        return changed

    def _repair_misnested_arabic_section_roots(self, outline_items: List[Dict]) -> bool:
        if len(outline_items) < 2:
            return False

        changed = False
        idx = 1
        while idx < len(outline_items):
            prev = outline_items[idx - 1]
            curr = outline_items[idx]
            prev_num = self._parse_arabic_numbering(prev.get("numbering"))
            curr_num = self._parse_arabic_numbering(curr.get("numbering"))
            if prev_num is None or curr_num is None:
                idx += 1
                continue
            if not self._is_section_like_node(prev, min_score=8):
                idx += 1
                continue

            curr_children = list(curr.get("children") or [])
            if not curr_children:
                idx += 1
                continue

            promoted_sections: List[Dict] = []
            remain_children: List[Dict] = []
            sibling_questions: List[Dict] = []
            for child in curr_children:
                child_num = self._parse_arabic_numbering(child.get("numbering"))
                if (
                    child_num is not None
                    and child_num < curr_num
                    and self._is_section_like_node(child, min_score=8)
                ):
                    promoted_sections.append(child)
                    continue
                if (
                    child_num is not None
                    and child_num >= curr_num + 1
                    and float(child.get("score") or 0.0) > 0
                ):
                    sibling_questions.append(child)
                    continue
                remain_children.append(child)

            if not promoted_sections:
                idx += 1
                continue

            curr["children"] = remain_children
            target_level = int(prev.get("level", 1) or 1) + 1
            curr["level"] = target_level
            for child in curr.get("children") or []:
                child_level = int(child.get("level", target_level) or target_level)
                expected_level = target_level + 1
                if child_level <= target_level:
                    self._shift_outline_level(child, expected_level - child_level)

            prev_children = list(prev.get("children") or [])
            prev_children.append(curr)
            for sibling in sibling_questions:
                sibling_level = int(sibling.get("level", target_level) or target_level)
                if sibling_level != target_level:
                    self._shift_outline_level(sibling, target_level - sibling_level)
                prev_children.append(sibling)
            prev["children"] = prev_children

            for section in promoted_sections:
                section_level = int(section.get("level", 2) or 2)
                if section_level != 1:
                    self._shift_outline_level(section, 1 - section_level)

            outline_items[idx : idx + 1] = promoted_sections
            changed = True
            idx += len(promoted_sections)
        return changed

    def _backfill_outline_root_scores_from_answer_lines(self, outline_items: List[Dict], answer_lines: List[str]) -> bool:
        if not outline_items or not answer_lines:
            return False
        answer_score_map = self._extract_answer_heading_score_map(answer_lines)
        if not answer_score_map:
            return False

        changed = False
        for node in outline_items:
            numbering_key = self._normalize_numbering_key(node.get("numbering"))
            if not numbering_key:
                continue
            current_score = node.get("score")
            if current_score is not None and float(current_score) > 0:
                continue
            matched_score = answer_score_map.get(numbering_key)
            if matched_score is None or float(matched_score) <= 0:
                continue
            node["score"] = float(matched_score)
            changed = True
        return changed

    def _recalculate_outline_scores_after_backfill(self, outline_items: List[Dict]) -> Dict:
        _distribute_outline_parent_score_to_slot_children(outline_items)
        _distribute_outline_parent_score_to_numbered_zero_children(outline_items)
        _distribute_outline_parent_remaining_score_to_unscored_children(outline_items)
        _distribute_outline_parent_score_gap_to_slot_leaves(outline_items)
        _distribute_outline_parent_remaining_score_to_unscored_children(outline_items)
        # 保证“父级有分，子级不为 0 分”在修复回填路径同样生效。
        _force_fill_zero_child_scores_under_scored_parent(outline_items)
        _fill_scored_empty_bracket_leaf_blank_text(outline_items)
        _fill_scored_underline_leaf_blank_text(outline_items)
        _fill_scored_question_mark_placeholder_blank_text(outline_items)
        _strip_instruction_quoted_underlines_from_blank_text(outline_items)
        _collapse_choice_question_multi_blanks(outline_items)
        _collapse_choice_semantic_leaf_multi_blanks(outline_items)
        _enforce_choice_question_no_blank_and_no_children(outline_items)
        _prune_conflicting_duplicate_numbered_children(outline_items)
        _prune_number_only_placeholder_nodes(outline_items)
        _prune_empty_leaf_placeholder_nodes(outline_items)
        normalize_outline_blank_scores(outline_items)
        return build_scores_tree(outline_items)

    def _compile_answer_patterns(self, answer_section_patterns: Optional[List[str]]) -> List[re.Pattern]:
        patterns = answer_section_patterns if answer_section_patterns else DEFAULT_ANSWER_PATTERNS
        compiled: List[re.Pattern] = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern))
            except re.error:
                continue
        if not compiled:
            compiled = [re.compile(pattern) for pattern in DEFAULT_ANSWER_PATTERNS]
        return compiled

    def _matches_answer(self, text: str, patterns: List[re.Pattern]) -> bool:
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return False
        if ANSWER_HEADING_NEGATIVE_RE.search(normalized):
            return False
        compact = re.sub(r"\s+", "", normalized)
        if re.fullmatch(r"[【\[]?(?:参考)?答案(?:与解析|解析|部分|页)?[】\]]?", compact):
            return True
        if self._looks_like_answer_sheet_heading(normalized):
            return True
        # Accept practical headings like "高二物理参考答案（选修...）" even when
        # custom/default regex patterns are too strict on the suffix.
        if self._looks_like_answer_heading(normalized):
            return True
        if not any(pattern.search(normalized) or pattern.search(compact) for pattern in patterns):
            return False
        return self._looks_like_answer_heading(normalized)

    def _looks_like_answer_sheet_heading(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return False
        if not ANSWER_SHEET_HEADING_RE.search(normalized):
            return False
        if QUESTION_LINE_PREFIX_RE.match(normalized):
            return False
        if ANSWER_INSTRUCTION_VERB_RE.search(normalized):
            return False
        if len(normalized) > 96:
            return False
        if any(mark in normalized for mark in ("。", "；", ";")) and len(normalized) > 24:
            return False
        return True

    def _looks_like_answer_heading(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return False
        if ANSWER_HEADING_NEGATIVE_RE.search(normalized):
            return False
        # 防止把“材料解析题”等题型标题误判为答案区
        if (
            SECTION_HEADING_PREFIX_RE.match(normalized)
            and QUESTION_SECTION_HINT_RE.search(normalized)
            and not re.search(r"(?:参考)?答案", normalized)
        ):
            return False
        compact = re.sub(r"\s+", "", normalized)
        if not ANSWER_HEADING_KEYWORD_RE.search(normalized) and not ANSWER_HEADING_KEYWORD_RE.search(compact):
            return False
        if re.fullmatch(r"[【\[]?(?:参考)?答案(?:与解析|解析|部分|页)?[】\]]?", compact):
            return True
        if (
            QUESTION_HEADING_WITH_ANSWER_WORD_RE.search(normalized)
            and QUESTION_SECTION_HINT_RE.search(normalized)
            and not re.search(r"(?:参考\s*答案|答案(?:与解析|解析))", normalized)
        ):
            return False
        if (
            QUESTION_HEADING_WITH_ANSWER_WORD_RE.search(normalized)
            and SECTION_HEADING_PREFIX_RE.match(normalized)
            and re.search(r"[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]", normalized)
        ):
            return False
        if QUESTION_LINE_PREFIX_RE.match(normalized):
            return False
        if ANSWER_INSTRUCTION_HINT_RE.search(normalized):
            return False
        if len(normalized) > 64:
            return False
        if any(mark in normalized for mark in ("。", "；", ";")) and len(normalized) > 20:
            return False
        return True

    def _looks_like_answer_split_hint(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return False
        if QUESTION_LINE_PREFIX_RE.match(normalized):
            return False
        return bool(ANSWER_SPLIT_HINT_RE.search(normalized))

    def _looks_like_tail_answer_material_start(self, lines: List[str], start_idx: int) -> bool:
        window = lines[start_idx + 1 : start_idx + 4]
        if not window:
            return False
        marker_re = re.compile(
            r"^\s*(?:\u7b2c[一二三四五六七八九十\d]+\u90e8\u5206|"
            r"(?:\u53c2\u8003\s*)?\u7b54\u6848|"
            r"\u542c\u529b\u6750\u6599|"
            r"Text\s*\d+|"
            r"[MW\u7537\u5973]\s*[:\uFF1A]|"
            r"\d+\s*[\.\uFF0E]\s*[A-Za-z])",
            flags=re.IGNORECASE,
        )
        for line in window:
            normalized = re.sub(r"\s+", " ", (line or "")).strip()
            if not normalized:
                continue
            if marker_re.search(normalized):
                return True
        return False

    def _looks_like_tail_answer_material_heading(self, lines: List[str], start_idx: int) -> bool:
        if start_idx < int(len(lines) * 0.55):
            return False
        normalized = re.sub(r"\s+", " ", (lines[start_idx] or "")).strip()
        if not normalized:
            return False
        if not TAIL_ANSWER_MATERIAL_HEADING_RE.match(normalized):
            return False
        window = lines[start_idx + 1 : start_idx + 7]
        if not window:
            return False
        signal_count = 0
        for line in window:
            probe = re.sub(r"\s+", " ", (line or "")).strip()
            if not probe:
                continue
            if TAIL_ANSWER_FOLLOW_LINE_RE.match(probe):
                signal_count += 1
                continue
            if self._looks_like_answer_key_line(probe):
                signal_count += 1
        return signal_count >= 1

    def _looks_like_answer_key_line(self, line: str) -> bool:
        normalized = re.sub(r"\s+", " ", (line or "")).strip()
        if not normalized:
            return False
        if "分" in normalized:
            return False
        if "?" in normalized or "？" in normalized:
            return False
        if QUESTION_HINT_RE.search(normalized):
            return False
        if QUESTION_DIRECTIVE_TEXT_RE.search(normalized):
            return False
        if ANSWER_KEY_TOKEN_RE.search(normalized):
            return True
        if re.fullmatch(
            r"(?:[A-D\uFF21-\uFF24√×]|\d+(?:\.\d+)?|[\u4e00-\u9fa5]{1,3})(?:\s*[,，;；、/]\s*"
            r"(?:[A-D\uFF21-\uFF24√×]|\d+(?:\.\d+)?|[\u4e00-\u9fa5]{1,3})){1,12}",
            normalized,
        ):
            return True
        return False

    def _looks_like_tail_compact_answer_start(self, lines: List[str], start_idx: int) -> bool:
        if start_idx < int(len(lines) * 0.6):
            return False
        if self._has_scored_question_section_ahead(lines, start_idx):
            return False

        # 新增：检查前面是否有有效的section heading（如"四、词汇运用"）
        # 如果有，说明当前位置的题目属于该section，不应视为答案分割点
        has_section_heading_before = False
        for i in range(start_idx - 1, max(0, start_idx - 20), -1):
            line = lines[i]
            if not line:
                continue
            # 检查是否是section heading（如"四、xxx"、"五、xxx"）
            if re.match(r'^\s*[\u4e00-\u9fa5\u96d9\u5341\u767e\u5343\u4e00]\s*[\u3001\.\uFF0E]\s*[\u4e00-\u9fa5]', line):
                # 检查标题后面是否有分数（如"（10分）"）- 包含"分"字
                if '分' in line or '\u5206' in line:
                    has_section_heading_before = True
                    break
        if has_section_heading_before:
            return False

        normalized = re.sub(r"\s+", " ", (lines[start_idx] or "")).strip()
        if not normalized:
            return False
        if "分" in normalized:
            return False
        if "?" in normalized or "？" in normalized:
            return False
        if re.search(r"(?:\u8bfb|\u9605\u8bfb|\u56de\u7b54|\u5b8c\u6210|\u4e0b\u5217|\u6750\u6599|\u7531\u56fe|\u6839\u636e)", normalized):
            return False
        if not TAIL_COMPACT_ANSWER_LINE_RE.match(normalized):
            return False
        lead_match = ARABIC_QUESTION_LINE_RE.match(normalized)
        line_tail = (lead_match.group(2) if lead_match else normalized).strip()
        # 尾部紧凑答案块：首行本身必须像“答案内容”，避免把题干/作文要求误切为答案区。
        if not line_tail:
            return False
        if QUESTION_DIRECTIVE_TEXT_RE.search(line_tail):
            return False
        if not (
            self._looks_like_answer_key_line(line_tail)
            or bool(TAIL_COMPACT_EXPLICIT_KEY_RE.search(line_tail))
        ):
            return False

        window = lines[start_idx : start_idx + 8]
        if len(window) < 3:
            return False
        answer_like_count = 0
        compact_count = 0
        no_score_count = 0
        explicit_key_count = 0
        for line in window:
            probe = re.sub(r"\s+", " ", (line or "")).strip()
            if not probe:
                continue
            if "分" not in probe:
                no_score_count += 1
            if TAIL_COMPACT_ANSWER_LINE_RE.match(probe):
                compact_count += 1
            if TAIL_COMPACT_EXPLICIT_KEY_RE.search(probe):
                explicit_key_count += 1
            if self._looks_like_answer_key_line(probe):
                answer_like_count += 1
        return answer_like_count >= 3 and compact_count >= 2 and no_score_count >= 2 and explicit_key_count >= 1

    def _looks_like_tail_compact_answer_heading(self, lines: List[str], start_idx: int) -> bool:
        if start_idx < int(len(lines) * 0.55):
            return False
        normalized = re.sub(r"\s+", " ", (lines[start_idx] or "")).strip()
        if not normalized:
            return False
        if len(normalized) > 48:
            return False
        if not TAIL_COMPACT_ANSWER_HEADING_RE.search(normalized):
            return False
        next_idx = start_idx + 1
        if next_idx >= len(lines):
            return False
        return self._looks_like_tail_compact_answer_start(lines, next_idx)

    def _looks_like_tail_inline_answer_section_heading(self, lines: List[str], start_idx: int) -> bool:
        if start_idx < int(len(lines) * 0.55):
            return False
        if self._has_scored_question_section_ahead(lines, start_idx):
            return False
        normalized = re.sub(r"\s+", " ", (lines[start_idx] or "")).strip()
        if not normalized:
            return False
        if TAIL_OPTION_LINE_RE.match(normalized):
            return False
        if "分" in normalized:
            return False
        match = TAIL_INLINE_ANSWER_SECTION_WITH_KEYS_RE.match(normalized)
        if not match:
            return False

        inline_tail = re.sub(r"\s+", " ", (match.group(1) or "")).strip()
        if inline_tail:
            if self._looks_like_answer_key_line(inline_tail):
                return True
            if re.search(r"(?:[A-D\uFF21-\uFF24]{3,}|\d+\s*[-~]\s*\d+)", inline_tail):
                return True

        window = lines[start_idx + 1 : start_idx + 6]
        if not window:
            return False
        signal_count = 0
        for line in window:
            probe = re.sub(r"\s+", " ", (line or "")).strip()
            if not probe:
                continue
            if self._looks_like_answer_key_line(probe):
                signal_count += 1
                continue
            if re.search(r"(?:[A-D\uFF21-\uFF24]{3,}|\d+\s*[-~]\s*\d+)", probe):
                signal_count += 1
        return signal_count >= 1

    def _looks_like_tail_section_inline_answer_start(self, lines: List[str], start_idx: int) -> bool:
        if start_idx < int(len(lines) * 0.55):
            return False
        if self._has_scored_question_section_ahead(lines, start_idx):
            return False
        normalized = re.sub(r"\s+", " ", (lines[start_idx] or "")).strip()
        if not normalized:
            return False
        if TAIL_OPTION_LINE_RE.match(normalized):
            return False
        if "分" in normalized:
            return False
        if "?" in normalized or "？" in normalized:
            return False
        match = TAIL_SECTION_INLINE_ANSWER_RE.match(normalized)
        if not match:
            return False

        line_tail = match.group(1)
        numbered_item_count = len(INLINE_NUMBERED_ITEM_RE.findall(line_tail))
        explicit_key_count = len(TAIL_COMPACT_EXPLICIT_KEY_RE.findall(line_tail))
        tail_answer_like = self._looks_like_answer_key_line(line_tail)
        if numbered_item_count < 2 and explicit_key_count < 1 and not tail_answer_like:
            return False

        window = lines[start_idx : start_idx + 4]
        if len(window) < 2:
            return False
        bundle_count = 0
        continuation_count = 0
        for line in window:
            probe = re.sub(r"\s+", " ", (line or "")).strip()
            if not probe or "分" in probe:
                continue
            m = TAIL_SECTION_INLINE_ANSWER_RE.match(probe)
            if not m:
                if re.match(r"^\s*\d{1,3}\s*[\.\uFF0E\u3001]\s*", probe) and self._looks_like_answer_key_line(probe):
                    continuation_count += 1
                continue
            tail = m.group(1)
            has_number_bundle = len(INLINE_NUMBERED_ITEM_RE.findall(tail)) >= 1
            has_answer_key = bool(
                TAIL_COMPACT_EXPLICIT_KEY_RE.search(tail)
                or re.search(r"(?:\b[A-D]\b|[√×])", tail, flags=re.IGNORECASE)
            )
            has_answer_like = self._looks_like_answer_key_line(tail)
            if has_number_bundle or has_answer_key or has_answer_like:
                bundle_count += 1
        return bundle_count >= 2 or (bundle_count >= 1 and continuation_count >= 2)

    def _guess_answer_split_by_repeated_numbering(self, lines: List[str]) -> Optional[int]:
        numbered: List[Tuple[int, int, str]] = []
        for idx, line in enumerate(lines):
            normalized = re.sub(r"\s+", " ", (line or "")).strip()
            if not normalized:
                continue
            match = ARABIC_QUESTION_LINE_RE.match(normalized)
            if not match:
                continue
            try:
                number_value = int(match.group(1))
            except ValueError:
                continue
            numbered.append((idx, number_value, normalized))

        if len(numbered) < 6:
            return None

        first_seen_line: Dict[int, int] = {}
        total_lines = len(lines)

        for pos, (line_idx, number_value, _) in enumerate(numbered):
            first_line = first_seen_line.get(number_value)
            if first_line is None:
                first_seen_line[number_value] = line_idx
                continue

            if line_idx < int(total_lines * 0.55):
                continue
            if self._has_scored_question_section_ahead(lines, line_idx):
                continue

            block = numbered[pos : pos + 4]
            if len(block) < 3:
                continue

            repeated_count = 0
            answer_like_count = 0
            no_score_count = 0
            explanation_hint_count = 0
            plain_tail_answer_count = 0
            prev_num = None
            monotonic_non_decreasing = True

            for block_line_idx, block_num, block_raw in block:
                if block_num in first_seen_line and first_seen_line[block_num] < block_line_idx:
                    repeated_count += 1
                if self._looks_like_answer_key_line(block_raw):
                    answer_like_count += 1
                if self._looks_like_answer_explanation_line(block_raw):
                    explanation_hint_count += 1
                if "分" not in (block_raw or ""):
                    no_score_count += 1
                compact_text = re.sub(r"\s+", " ", (block_raw or "")).strip()
                if (
                    compact_text
                    and len(compact_text) <= 48
                    and "分" not in compact_text
                    and "?" not in compact_text
                    and "？" not in compact_text
                    and not QUESTION_HINT_RE.search(compact_text)
                    and not QUESTION_DIRECTIVE_TEXT_RE.search(compact_text)
                ):
                    plain_tail_answer_count += 1
                if prev_num is not None and block_num < prev_num:
                    monotonic_non_decreasing = False
                prev_num = block_num

            fallback_restart_pattern = (
                block[0][1] == 1
                and line_idx >= int(total_lines * 0.6)
                and repeated_count >= 3
                and no_score_count >= 2
                and explanation_hint_count >= 1
                and len(first_seen_line) >= 8
                and not self._has_recent_scored_question_section(lines, line_idx)
            )
            plain_compact_restart_pattern = (
                block[0][1] == 1
                and line_idx >= int(total_lines * 0.65)
                and repeated_count >= 3
                and no_score_count >= 3
                and plain_tail_answer_count >= 3
                and len(first_seen_line) >= 10
                and not self._has_recent_scored_question_section(lines, line_idx)
            )
            if (
                monotonic_non_decreasing
                and (
                    (
                        repeated_count >= 3
                        and answer_like_count >= 2
                        and no_score_count >= 2
                    )
                    or fallback_restart_pattern
                    or plain_compact_restart_pattern
                )
            ):
                return line_idx

        return None

    def _has_scored_question_section_ahead(self, lines: List[str], start_idx: int, lookahead: int = 18) -> bool:
        end_idx = min(len(lines), start_idx + lookahead)
        for idx in range(start_idx, end_idx):
            normalized = re.sub(r"\s+", " ", (lines[idx] or "")).strip()
            if not normalized:
                continue
            if not SECTION_HEADING_PREFIX_RE.match(normalized):
                continue
            if not re.search(r"[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]", normalized):
                continue
            return True
        return False

    def _has_recent_scored_question_section(
        self,
        lines: List[str],
        start_idx: int,
        lookback: int = 3,
    ) -> bool:
        begin = max(0, start_idx - lookback)
        for idx in range(begin, start_idx):
            normalized = re.sub(r"\s+", " ", (lines[idx] or "")).strip()
            if not normalized:
                continue
            if not SECTION_HEADING_PREFIX_RE.match(normalized):
                continue
            if not re.search(r"[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]", normalized):
                continue
            return True
        return False

    def _looks_like_answer_explanation_line(self, line: str) -> bool:
        normalized = re.sub(r"\s+", " ", (line or "")).strip()
        if not normalized:
            return False
        return bool(ANSWER_EXPLANATION_HINT_RE.search(normalized))

    def _looks_like_tail_repeated_title_answer_start(self, lines: List[str], start_idx: int) -> bool:
        if start_idx < int(len(lines) * 0.6):
            return False
        current = re.sub(r"\s+", " ", (lines[start_idx] or "")).strip()
        if not current:
            return False

        head_candidates: List[str] = []
        for line in lines[:3]:
            normalized = re.sub(r"\s+", " ", (line or "")).strip()
            if normalized:
                head_candidates.append(normalized)
        if not head_candidates or current not in head_candidates:
            return False

        window = lines[start_idx + 1 : start_idx + 6]
        if len(window) < 2:
            return False

        answer_like_count = 0
        section_answer_count = 0
        numbered_line_count = 0
        for line in window:
            probe = re.sub(r"\s+", " ", (line or "")).strip()
            if not probe:
                continue
            if self._looks_like_answer_key_line(probe):
                answer_like_count += 1
            if re.match(r"^[一二三四五六七八九十]+[、\.．]\s*\d+", probe):
                section_answer_count += 1
                answer_like_count += 1
                numbered_line_count += 1
                continue
            match = ARABIC_QUESTION_LINE_RE.match(probe)
            if match is not None:
                numbered_line_count += 1
                if self._looks_like_answer_key_line(match.group(2).strip()):
                    answer_like_count += 1

        return section_answer_count >= 1 and numbered_line_count >= 3

    def _detect_answer_split(
        self,
        lines: List[str],
        answer_patterns: List[re.Pattern],
    ) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        split_idx = None
        split_reason: Optional[str] = None
        inline_main_prefix: Optional[str] = None
        inline_answer_first_line: Optional[str] = None
        for idx, line in enumerate(lines):
            # Some papers append answer-sheet/listening material block near tail
            # with hints like "请将答案填在答题卡上". Treat it as split marker only
            # in the latter half to avoid false split in front-page instructions.
            if (
                idx >= int(len(lines) * 0.6)
                and self._looks_like_answer_split_hint(line)
                and self._looks_like_tail_answer_material_start(lines, idx)
            ):
                split_idx = idx
                split_reason = "tail_answer_split_hint"
                break
            if self._looks_like_tail_compact_answer_heading(lines, idx):
                split_idx = idx
                split_reason = "tail_compact_heading"
                break
            if self._looks_like_tail_inline_answer_section_heading(lines, idx):
                split_idx = idx
                split_reason = "tail_inline_section_heading"
                break
            if self._looks_like_tail_section_inline_answer_start(lines, idx):
                split_idx = idx
                split_reason = "tail_section_inline_start"
                break
            if self._looks_like_tail_compact_answer_start(lines, idx):
                split_idx = idx
                split_reason = "tail_compact_start"
                break
            if self._looks_like_tail_answer_material_heading(lines, idx):
                split_idx = idx
                split_reason = "tail_answer_material_heading"
                break
            if self._looks_like_tail_repeated_title_answer_start(lines, idx):
                split_idx = idx
                split_reason = "tail_repeated_title_answer_start"
                break
            if self._matches_answer(line, answer_patterns):
                if idx == 0:
                    # 首行可能是“试题与答案”标题，不作为切分点，继续向后查找真正答案区。
                    continue
                split_idx = idx
                split_reason = "explicit_answer_heading"
                break
            marker = INLINE_ANSWER_MARKER_RE.search(line or "")
            if marker is None:
                continue
            if idx < int(len(lines) * 0.45):
                continue
            before = (line[: marker.start()] if line else "").strip()
            after = (line[marker.start() :] if line else "").strip()
            if not after:
                continue
            if not self._looks_like_answer_key_line(after) and not re.search(
                r"(?:\d+\s*[-~]\s*\d+|[A-D]\b|[;；、,，])",
                after,
            ):
                continue
            split_idx = idx
            inline_main_prefix = before
            inline_answer_first_line = after
            split_reason = "inline_answer_marker"
            break
        guessed_split_idx = self._guess_answer_split_by_repeated_numbering(lines)
        if split_idx is None:
            split_idx = guessed_split_idx
            if split_idx is None:
                return None, None, None
            split_reason = "repeated_numbering_guess"
        elif (
            guessed_split_idx is not None
            and guessed_split_idx < split_idx
            and guessed_split_idx >= int(len(lines) * 0.5)
            and split_reason
            in {
                "tail_compact_heading",
                "tail_inline_section_heading",
                "tail_section_inline_start",
                "tail_compact_start",
                "tail_answer_material_heading",
            }
            and not self._has_scored_question_section_ahead(lines, guessed_split_idx)
        ):
            # 部分试卷尾部会先出现“紧凑答案块”提示，后面才出现明显答案行。
            # 若“重复编号重启”能给出更早且可靠的切分点，优先使用更早点，避免答案混入主文。
            split_idx = guessed_split_idx
            split_reason = "repeated_numbering_guess_earlier"
            inline_main_prefix = None
            inline_answer_first_line = None
        if split_idx == 0:
            # Avoid treating title lines containing "xx试题与答案" as answer section split.
            return None, None, None
        return split_idx, inline_main_prefix, inline_answer_first_line

    def _apply_answer_split(
        self,
        lines: List[str],
        split_idx: Optional[int],
        inline_main_prefix: Optional[str],
        inline_answer_first_line: Optional[str],
    ) -> Tuple[List[str], List[str]]:
        if split_idx is None:
            return lines, []
        if inline_answer_first_line is not None:
            main_lines = lines[:split_idx]
            if inline_main_prefix:
                main_lines.append(inline_main_prefix)
            answer_lines = [inline_answer_first_line] + lines[split_idx + 1 :]
            return main_lines, answer_lines
        return lines[:split_idx], lines[split_idx:]

    def _split_lines_by_answer(self, lines: List[str], answer_patterns: List[re.Pattern]) -> Tuple[List[str], List[str]]:
        split_idx, inline_main_prefix, inline_answer_first_line = self._detect_answer_split(lines, answer_patterns)
        return self._apply_answer_split(lines, split_idx, inline_main_prefix, inline_answer_first_line)

    def _infer_answer_start_page(
        self,
        page_lines: List[List[str]],
        split_idx: Optional[int],
        answer_lines: List[str],
    ) -> Optional[int]:
        if not page_lines:
            return None

        if split_idx is not None:
            offset = 0
            for page_idx, lines in enumerate(page_lines):
                next_offset = offset + len(lines)
                if split_idx < next_offset:
                    return page_idx
                offset = next_offset

        compact_candidates = [re.sub(r"\s+", "", line or "") for line in answer_lines if (line or "").strip()]
        if not compact_candidates:
            return None

        for page_idx, lines in enumerate(page_lines):
            compact_page = re.sub(r"\s+", "", "".join(lines))
            if not compact_page:
                continue
            for candidate in compact_candidates[:8]:
                probe = candidate[:80]
                if probe and probe in compact_page:
                    return page_idx
        return None

    def _find_answer_heading_page(
        self,
        page_lines: List[List[str]],
        answer_patterns: List[re.Pattern],
    ) -> Optional[int]:
        if not page_lines:
            return None

        for page_idx, lines in enumerate(page_lines):
            head_lines: List[str] = []
            for line in lines:
                cleaned = (line or "").strip()
                if not cleaned:
                    continue
                head_lines.append(cleaned)
                if len(head_lines) >= 14:
                    break

            if not head_lines:
                continue

            for line in head_lines:
                if self._matches_answer(line, answer_patterns):
                    return page_idx

            # Keep a tiny page-level fallback for sparse pages where heading and
            # marker text may be split into short fragments.
            if len(head_lines) <= 2 and self._matches_answer("\n".join(head_lines), answer_patterns):
                return page_idx

        return None

    def _chunk_lines(self, lines: List[str], chunk_size: int = 20) -> List[List[str]]:
        if not lines:
            return []
        return [lines[i : i + chunk_size] for i in range(0, len(lines), chunk_size)]

    def _resolve_font_path(self) -> Optional[Path]:
        candidates: List[str] = []
        if os.name == "nt":
            candidates.extend(
                [
                    r"C:\Windows\Fonts\msyh.ttc",
                    r"C:\Windows\Fonts\simsun.ttc",
                    r"C:\Windows\Fonts\simhei.ttf",
                    r"C:\Windows\Fonts\Deng.ttf",
                ]
            )
        else:
            candidates.extend(
                [
                    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                ]
            )
        for item in candidates:
            path = Path(item)
            if path.exists():
                return path
        return None

    def _load_font(self, size: int):
        if self._font_path:
            try:
                return ImageFont.truetype(str(self._font_path), size=size)
            except OSError:
                pass
        return ImageFont.load_default()

    def _wrap_line(self, draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
        if not text:
            return [""]
        result: List[str] = []
        current = ""
        for ch in text:
            probe = current + ch
            bbox = draw.textbbox((0, 0), probe, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current = probe
            else:
                if current:
                    result.append(current)
                current = ch
        if current:
            result.append(current)
        return result if result else [text]

    def _build_text_page_image(self, page_lines: List[str], page_no: int, page_type: str) -> Image.Image:
        width, height = 1654, 2339
        margin = 72
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        sample_bbox = draw.textbbox((0, 0), "A", font=self._font_body)
        line_height = (sample_bbox[3] - sample_bbox[1]) + 14
        y = margin
        max_width = width - margin * 2
        max_y = height - margin - 60

        for line in page_lines:
            wrapped = self._wrap_line(draw, line, self._font_body, max_width)
            for piece in wrapped:
                if y > max_y:
                    break
                draw.text((margin, y), piece, fill=(20, 20, 20), font=self._font_body)
                y += line_height
            if y > max_y:
                break

        # Keep fallback rendering clean: do not inject synthetic footer/header text.
        return image

    def _render_text_page(self, task_id: int, page_lines: List[str], page_no: int, page_type: str) -> str:
        image = self._build_text_page_image(page_lines, page_no, page_type)
        filename = f"{task_id}_{page_type}_{page_no}_{uuid.uuid4().hex[:8]}.png"
        output_path = settings.pages_dir / filename
        image.save(output_path, format="PNG")
        image.close()
        return f"{settings.static_url_prefix}/pages/{filename}"

    def _copy_pdf_to_preview_storage(self, task_id: int, source_pdf: Path, tag: str = "main_preview") -> str:
        filename = f"{task_id}_{tag}_{uuid.uuid4().hex[:8]}.pdf"
        target_path = settings.pages_dir / filename
        shutil.copyfile(source_pdf, target_path)
        return f"{settings.static_url_prefix}/pages/{filename}"

    def _extract_pdf_page_lines(self, file_path: Path) -> List[List[str]]:
        page_lines: List[List[str]] = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                page_lines.append(lines)
        return page_lines

    def _export_pdf_page_range(self, task_id: int, source_pdf: Path, start_page: int, end_page: int, tag: str) -> str:
        if fitz is None:
            # Fallback: no PyMuPDF available, return full source preview.
            return self._copy_pdf_to_preview_storage(task_id, source_pdf, f"{tag}_full")

        document = fitz.open(str(source_pdf))
        try:
            max_page = document.page_count
            start = max(0, min(start_page, max_page))
            end = max(0, min(end_page, max_page))
            if start >= end:
                raise ValueError(f"Invalid page range [{start}, {end}) for {max_page} pages.")

            out_doc = fitz.open()
            try:
                out_doc.insert_pdf(document, from_page=start, to_page=end - 1)
                filename = f"{task_id}_{tag}_{uuid.uuid4().hex[:8]}.pdf"
                output_path = settings.pages_dir / filename
                out_doc.save(str(output_path))
            finally:
                out_doc.close()
        finally:
            document.close()

        return f"{settings.static_url_prefix}/pages/{filename}"

    def _split_pdf_preview(
        self,
        task_id: int,
        source_pdf: Path,
        answer_start_page: Optional[int],
    ) -> Tuple[List[str], List[str]]:
        if fitz is None:
            return [self._copy_pdf_to_preview_storage(task_id, source_pdf, "preview")], []

        document = fitz.open(str(source_pdf))
        try:
            page_count = document.page_count
        finally:
            document.close()

        if page_count <= 0:
            return [self._copy_pdf_to_preview_storage(task_id, source_pdf, "preview")], []

        # Preview should stay as a full paper PDF in "试卷预览".
        # Do not split preview pages into one-file-per-page and do not expose
        # separate answer preview pages for now.
        main_pdf = self._export_pdf_page_range(task_id, source_pdf, 0, page_count, "main_preview")
        return [main_pdf], []

    def _convert_office_to_pdf(self, office_path: Path) -> Path:
        output_pdf = office_path.parent / f"{office_path.stem}_{uuid.uuid4().hex[:8]}.pdf"
        if os.name == "nt" and self._convert_with_word_com(office_path, output_pdf):
            return output_pdf

        soffice_cmd = self._resolve_libreoffice_cmd()
        if not soffice_cmd:
            raise RuntimeError(
                "No Office-to-PDF converter found. Install Microsoft Word or LibreOffice, "
                "or set LIBREOFFICE_CMD to full soffice path."
            )
        out_dir = office_path.parent
        cmd = [
            soffice_cmd,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(office_path),
        ]
        proc = subprocess.run(cmd, capture_output=True)
        stdout = self._decode_process_output(proc.stdout)
        stderr = self._decode_process_output(proc.stderr)
        libreoffice_pdf = out_dir / f"{office_path.stem}.pdf"
        if proc.returncode != 0 or not libreoffice_pdf.exists():
            raise RuntimeError(
                f"Failed to convert office file to PDF. command={soffice_cmd}, "
                f"stdout={stdout}, stderr={stderr}"
            )
        shutil.copyfile(libreoffice_pdf, output_pdf)
        return output_pdf

    def _convert_with_word_com(self, office_path: Path, output_pdf: Path) -> bool:
        source = str(office_path.resolve()).replace("'", "''")
        target = str(output_pdf.resolve()).replace("'", "''")
        script = (
            "$ErrorActionPreference='Stop';"
            "$word=New-Object -ComObject Word.Application;"
            "$word.Visible=$false;"
            "$word.DisplayAlerts=0;"
            "try{"
            f"$doc=$word.Documents.Open('{source}',$false,$true);"
            "try{"
            f"$doc.ExportAsFixedFormat('{target}',17);"
            "}finally{"
            "$doc.Close($false);"
            "}"
            "}finally{"
            "$word.Quit();"
            "}"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
        )
        return proc.returncode == 0 and output_pdf.exists()

    def _normalize_layout_adjustments(self, layout_adjustments: Optional[Dict[str, float]]) -> Dict[str, float]:
        if not isinstance(layout_adjustments, dict):
            return {}

        normalized: Dict[str, float] = {}
        for key in (
            "marginTopCm",
            "marginRightCm",
            "marginBottomCm",
            "marginLeftCm",
            "paragraphLeftIndentCm",
            "paragraphRightIndentCm",
            "firstLineIndentCm",
            "paragraphSpaceBeforePt",
            "paragraphSpaceAfterPt",
        ):
            value = layout_adjustments.get(key)
            if value in (None, ""):
                continue
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                continue
        return normalized

    def _create_adjusted_docx_for_preview(
        self,
        source_docx: Path,
        task_id: int,
        layout_adjustments: Optional[Dict[str, float]],
    ) -> Path:
        normalized = self._normalize_layout_adjustments(layout_adjustments)
        if not normalized:
            return source_docx

        doc = Document(str(source_docx))

        for section in doc.sections:
            if "marginTopCm" in normalized:
                section.top_margin = Cm(normalized["marginTopCm"])
            if "marginRightCm" in normalized:
                section.right_margin = Cm(normalized["marginRightCm"])
            if "marginBottomCm" in normalized:
                section.bottom_margin = Cm(normalized["marginBottomCm"])
            if "marginLeftCm" in normalized:
                section.left_margin = Cm(normalized["marginLeftCm"])

        for paragraph in doc.paragraphs:
            fmt = paragraph.paragraph_format
            if "paragraphLeftIndentCm" in normalized:
                fmt.left_indent = Cm(normalized["paragraphLeftIndentCm"])
            if "paragraphRightIndentCm" in normalized:
                fmt.right_indent = Cm(normalized["paragraphRightIndentCm"])
            if "firstLineIndentCm" in normalized:
                fmt.first_line_indent = Cm(normalized["firstLineIndentCm"])
            if "paragraphSpaceBeforePt" in normalized:
                fmt.space_before = Pt(normalized["paragraphSpaceBeforePt"])
            if "paragraphSpaceAfterPt" in normalized:
                fmt.space_after = Pt(normalized["paragraphSpaceAfterPt"])

        adjusted_path = source_docx.parent / f"{source_docx.stem}_layout_{task_id}_{uuid.uuid4().hex[:8]}.docx"
        doc.save(str(adjusted_path))
        return adjusted_path

    def _paragraph_to_text(self, paragraph) -> str:
        if not paragraph.runs:
            text = (paragraph.text or "").strip()
            if not text:
                return text
            text = DOCX_FIELD_CODE_RE.sub("", text)
            text = DOCX_FIELD_SWITCH_RE.sub("", text)
            text = DOCX_LAYOUT_ARTIFACT_RE.sub("", text)
            text = re.sub(r"\s{2,}", " ", text).strip()
            return text

        parts: List[str] = []
        for run in paragraph.runs:
            text = run.text or ""
            if run.underline:
                if text.strip():
                    text = re.sub(r"\s", "_", text)
                else:
                    text = "_" * max(4, len(text))
            parts.append(text)
        merged = "".join(parts).strip()
        if not merged:
            return merged
        merged = DOCX_FIELD_CODE_RE.sub("", merged)
        merged = DOCX_FIELD_SWITCH_RE.sub("", merged)
        merged = DOCX_LAYOUT_ARTIFACT_RE.sub("", merged)
        merged = re.sub(r"\s{2,}", " ", merged).strip()
        return merged

    def _to_alpha(self, value: int, upper: bool = True) -> str:
        if value <= 0:
            return str(value)
        chars: List[str] = []
        current = value
        while current > 0:
            current -= 1
            chars.append(chr(ord("A") + (current % 26)))
            current //= 26
        result = "".join(reversed(chars))
        return result if upper else result.lower()

    def _to_roman(self, value: int, upper: bool = True) -> str:
        if value <= 0:
            return str(value)
        numerals = [
            (1000, "M"),
            (900, "CM"),
            (500, "D"),
            (400, "CD"),
            (100, "C"),
            (90, "XC"),
            (50, "L"),
            (40, "XL"),
            (10, "X"),
            (9, "IX"),
            (5, "V"),
            (4, "IV"),
            (1, "I"),
        ]
        current = value
        chars: List[str] = []
        for integer, symbol in numerals:
            while current >= integer:
                chars.append(symbol)
                current -= integer
        result = "".join(chars)
        return result if upper else result.lower()

    def _to_simple_chinese(self, value: int) -> str:
        if value <= 0:
            return str(value)
        digit_map = {
            0: "零",
            1: "一",
            2: "二",
            3: "三",
            4: "四",
            5: "五",
            6: "六",
            7: "七",
            8: "八",
            9: "九",
        }
        if value <= 10:
            return "十" if value == 10 else digit_map[value]
        if value < 20:
            return f"十{digit_map[value - 10]}"
        if value < 100:
            tens = value // 10
            units = value % 10
            if units == 0:
                return f"{digit_map[tens]}十"
            return f"{digit_map[tens]}十{digit_map[units]}"
        # 文档编号层级通常不会超过两位；超过时保留数字避免错误转换。
        return str(value)

    def _format_list_counter(self, num_fmt: str, value: int) -> str:
        fmt = (num_fmt or "decimal").lower()
        if fmt in {"bullet", "none"}:
            return ""
        if fmt == "decimalzero":
            return f"{value:02d}"
        if fmt in {
            "chinesecounting",
            "chinesecountingthousand",
            "chineselegal",
            "chineselegalsimplified",
            "ideographtraditional",
            "ideographdigital",
            "ideographzodiac",
        }:
            return self._to_simple_chinese(value)
        if fmt == "upperletter":
            return self._to_alpha(value, upper=True)
        if fmt == "lowerletter":
            return self._to_alpha(value, upper=False)
        if fmt == "upperroman":
            return self._to_roman(value, upper=True)
        if fmt == "lowerroman":
            return self._to_roman(value, upper=False)
        return str(value)

    def _safe_int(self, value, default: Optional[int] = None) -> Optional[int]:
        if value is None:
            return default
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return default

    def _extract_num_info(self, num_pr) -> Optional[Tuple[int, int]]:
        if num_pr is None:
            return None
        num_id_el = getattr(num_pr, "numId", None)
        ilvl_el = getattr(num_pr, "ilvl", None)
        num_id = self._safe_int(num_id_el.val if num_id_el is not None else None)
        ilvl = self._safe_int(ilvl_el.val if ilvl_el is not None else 0, default=0)
        if num_id is None:
            return None
        return num_id, max(ilvl or 0, 0)

    def _extract_numbering_from_style(self, paragraph) -> Optional[Tuple[int, int]]:
        style = getattr(paragraph, "style", None)
        visited = set()
        while style is not None:
            style_id = getattr(style, "style_id", None)
            if style_id in visited:
                break
            visited.add(style_id)
            style_element = getattr(style, "_element", None)
            style_ppr = getattr(style_element, "pPr", None)
            if style_ppr is not None:
                info = self._extract_num_info(getattr(style_ppr, "numPr", None))
                if info:
                    return info
            style = getattr(style, "base_style", None)
        return None

    def _get_paragraph_numbering_info(self, paragraph) -> Optional[Tuple[int, int]]:
        p_pr = getattr(paragraph._p, "pPr", None)
        if p_pr is not None:
            direct = self._extract_num_info(getattr(p_pr, "numPr", None))
            if direct:
                return direct
        return self._extract_numbering_from_style(paragraph)

    def _build_numbering_maps(
        self, doc: Document
    ) -> Tuple[Dict[int, int], Dict[int, Dict[int, Dict[str, object]]], Dict[Tuple[int, int], Dict[str, object]]]:
        try:
            numbering_element = doc.part.numbering_part.element
        except Exception:
            return {}, {}, {}

        abstract_levels: Dict[int, Dict[int, Dict[str, object]]] = {}
        for abstract_num in numbering_element.findall(qn("w:abstractNum")):
            abstract_id = self._safe_int(abstract_num.get(qn("w:abstractNumId")))
            if abstract_id is None:
                continue
            levels: Dict[int, Dict[str, object]] = {}
            for lvl in abstract_num.findall(qn("w:lvl")):
                ilvl = self._safe_int(lvl.get(qn("w:ilvl")), default=0) or 0
                start_el = lvl.find(qn("w:start"))
                num_fmt_el = lvl.find(qn("w:numFmt"))
                lvl_text_el = lvl.find(qn("w:lvlText"))
                suffix_el = lvl.find(qn("w:suff"))
                levels[ilvl] = {
                    "start": self._safe_int(start_el.get(qn("w:val")) if start_el is not None else None, default=1) or 1,
                    "fmt": (num_fmt_el.get(qn("w:val")) if num_fmt_el is not None else "decimal"),
                    "text": (lvl_text_el.get(qn("w:val")) if lvl_text_el is not None else f"%{ilvl + 1}."),
                    "suffix": (suffix_el.get(qn("w:val")) if suffix_el is not None else ""),
                }
            abstract_levels[abstract_id] = levels

        num_to_abstract: Dict[int, int] = {}
        num_overrides: Dict[Tuple[int, int], Dict[str, object]] = {}
        for num in numbering_element.findall(qn("w:num")):
            num_id = self._safe_int(num.get(qn("w:numId")))
            abstract_num_id_el = num.find(qn("w:abstractNumId"))
            abstract_id = self._safe_int(
                abstract_num_id_el.get(qn("w:val")) if abstract_num_id_el is not None else None
            )
            if num_id is not None and abstract_id is not None:
                num_to_abstract[num_id] = abstract_id

            if num_id is None:
                continue
            for lvl_override in num.findall(qn("w:lvlOverride")):
                ilvl = self._safe_int(lvl_override.get(qn("w:ilvl")), default=0) or 0
                override: Dict[str, object] = {}
                start_override = lvl_override.find(qn("w:startOverride"))
                if start_override is not None:
                    override["start"] = self._safe_int(start_override.get(qn("w:val")), default=1) or 1
                lvl = lvl_override.find(qn("w:lvl"))
                if lvl is not None:
                    start_el = lvl.find(qn("w:start"))
                    num_fmt_el = lvl.find(qn("w:numFmt"))
                    lvl_text_el = lvl.find(qn("w:lvlText"))
                    suffix_el = lvl.find(qn("w:suff"))
                    if start_el is not None:
                        override["start"] = self._safe_int(start_el.get(qn("w:val")), default=1) or 1
                    if num_fmt_el is not None:
                        override["fmt"] = num_fmt_el.get(qn("w:val"))
                    if lvl_text_el is not None:
                        override["text"] = lvl_text_el.get(qn("w:val"))
                    if suffix_el is not None:
                        override["suffix"] = suffix_el.get(qn("w:val"))
                if override:
                    num_overrides[(num_id, ilvl)] = override

        return num_to_abstract, abstract_levels, num_overrides

    def _resolve_level_definition(
        self,
        num_id: int,
        ilvl: int,
        num_to_abstract: Dict[int, int],
        abstract_levels: Dict[int, Dict[int, Dict[str, object]]],
        num_overrides: Dict[Tuple[int, int], Dict[str, object]],
    ) -> Dict[str, object]:
        abstract_id = num_to_abstract.get(num_id)
        base = {}
        if abstract_id is not None:
            base = abstract_levels.get(abstract_id, {}).get(ilvl, {})
        override = num_overrides.get((num_id, ilvl), {})
        merged = dict(base)
        merged.update(override)
        if "start" not in merged:
            merged["start"] = 1
        if "fmt" not in merged:
            merged["fmt"] = "decimal"
        if "text" not in merged:
            merged["text"] = f"%{ilvl + 1}."
        if "suffix" not in merged:
            merged["suffix"] = ""
        return merged

    def _build_numbering_prefix(
        self,
        num_id: int,
        ilvl: int,
        counters: Dict[int, Dict[int, int]],
        num_to_abstract: Dict[int, int],
        abstract_levels: Dict[int, Dict[int, Dict[str, object]]],
        num_overrides: Dict[Tuple[int, int], Dict[str, object]],
    ) -> str:
        level_counters = counters.setdefault(num_id, {})
        for existing_level in list(level_counters):
            if existing_level > ilvl:
                level_counters.pop(existing_level, None)

        level_def = self._resolve_level_definition(
            num_id=num_id,
            ilvl=ilvl,
            num_to_abstract=num_to_abstract,
            abstract_levels=abstract_levels,
            num_overrides=num_overrides,
        )
        start = self._safe_int(level_def.get("start"), default=1) or 1
        level_counters[ilvl] = level_counters.get(ilvl, start - 1) + 1

        for parent_level in range(ilvl):
            if parent_level not in level_counters:
                parent_def = self._resolve_level_definition(
                    num_id=num_id,
                    ilvl=parent_level,
                    num_to_abstract=num_to_abstract,
                    abstract_levels=abstract_levels,
                    num_overrides=num_overrides,
                )
                level_counters[parent_level] = self._safe_int(parent_def.get("start"), default=1) or 1

        template = str(level_def.get("text") or f"%{ilvl + 1}.")

        def replace_token(match: re.Match) -> str:
            token_level = int(match.group(1)) - 1
            token_value = level_counters.get(token_level, 1)
            token_def = self._resolve_level_definition(
                num_id=num_id,
                ilvl=token_level,
                num_to_abstract=num_to_abstract,
                abstract_levels=abstract_levels,
                num_overrides=num_overrides,
            )
            return self._format_list_counter(str(token_def.get("fmt") or "decimal"), token_value)

        prefix = re.sub(r"%(\d+)", replace_token, template).strip()
        return prefix

    def _collect_docx_lines(self, doc: Document) -> List[str]:
        lines: List[str] = []
        num_to_abstract, abstract_levels, num_overrides = self._build_numbering_maps(doc)
        counters: Dict[int, Dict[int, int]] = {}
        for paragraph in doc.paragraphs:
            text = self._paragraph_to_text(paragraph)
            numbering_info = self._get_paragraph_numbering_info(paragraph)
            if numbering_info is not None:
                num_id, ilvl = numbering_info
                prefix = self._build_numbering_prefix(
                    num_id=num_id,
                    ilvl=ilvl,
                    counters=counters,
                    num_to_abstract=num_to_abstract,
                    abstract_levels=abstract_levels,
                    num_overrides=num_overrides,
                )
                if prefix:
                    if text:
                        text = f"{prefix} {text}"
                    else:
                        text = prefix
            if text:
                lines.append(text)
        return lines

    def _collect_docx_header_footer(self, doc: Document) -> Tuple[List[str], List[str]]:
        headers: List[str] = []
        footers: List[str] = []
        for section in doc.sections:
            header = " ".join(p.text.strip() for p in section.header.paragraphs if p.text.strip())
            footer = " ".join(p.text.strip() for p in section.footer.paragraphs if p.text.strip())
            if header:
                headers.append(header)
            if footer:
                footers.append(footer)
        return headers, footers

    def _process_docx(
        self,
        task_id: int,
        file_path: Path,
        answer_patterns: List[re.Pattern],
        preview_source_path: Optional[Path] = None,
    ) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[Dict]]:
        lines: List[str] = []
        headers: List[str] = []
        footers: List[str] = []
        doc_loaded = False
        try:
            doc = Document(str(file_path))
            lines = self._collect_docx_lines(doc)
            headers, footers = self._collect_docx_header_footer(doc)
            doc_loaded = True
        except Exception:
            # Some files use .docx extension but are not valid OOXML packages.
            # Fallback to PDF text extraction so recognition can still proceed.
            doc_loaded = False

        preview_pdf_path: Optional[Path] = None
        preview_page_lines: List[List[str]] = []
        try:
            # Keep source layout unchanged: use Office->PDF conversion for preview.
            preview_pdf_path = self._convert_office_to_pdf(preview_source_path or file_path)
            preview_page_lines = self._extract_pdf_page_lines(preview_pdf_path)
        except Exception:
            if not lines:
                lines = self._read_fallback_text_lines(preview_source_path or file_path)
            preview_pdf_path = self._create_fallback_pdf(task_id, lines, "fallback_preview")
            preview_page_lines = [lines]

        if not lines:
            lines = [line for page in preview_page_lines for line in page]
        if doc_loaded and not lines:
            # Converted docx may contain only drawing/textbox content.
            # Use PDF text extraction as source for recognition in this case.
            lines = [line for page in preview_page_lines for line in page]
        split_idx, inline_main_prefix, inline_answer_first_line = self._detect_answer_split(lines, answer_patterns)
        main_lines, answer_lines = self._apply_answer_split(
            lines,
            split_idx,
            inline_main_prefix,
            inline_answer_first_line,
        )

        inferred_answer_start_page: Optional[int] = None
        if answer_lines:
            inferred_answer_start_page = self._infer_answer_start_page(preview_page_lines, split_idx, answer_lines)

        heading_answer_start_page = self._find_answer_heading_page(preview_page_lines, answer_patterns)
        answer_start_page = (
            inferred_answer_start_page if inferred_answer_start_page is not None else heading_answer_start_page
        )
        main_page_urls, answer_page_urls = self._split_pdf_preview(task_id, preview_pdf_path, answer_start_page)

        if doc_loaded:
            pages_count = max(len(preview_page_lines), 1)
            default_header = headers[0] if headers else ""
            default_footer = footers[0] if footers else ""
            header_footer_items = [
                {"page": idx, "header": default_header, "footer": default_footer}
                for idx in range(1, pages_count + 1)
            ]
        else:
            header_footer_items = detect_pdf_header_footer(preview_page_lines)
        return (
            lines,
            main_lines,
            answer_lines,
            main_page_urls,
            answer_page_urls,
            header_footer_items,
        )

    def _render_pdf_pages(self, task_id: int, file_path: Path, page_lines: List[List[str]]) -> List[str]:
        urls: List[str] = []
        if fitz is None:
            for idx, lines in enumerate(page_lines, start=1):
                urls.append(self._render_text_page(task_id, lines, idx, "pdf"))
            return urls

        document = fitz.open(str(file_path))
        try:
            for idx in range(document.page_count):
                page = document.load_page(idx)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                filename = f"{task_id}_pdf_{idx + 1}_{uuid.uuid4().hex[:8]}.png"
                output_path = settings.pages_dir / filename
                pixmap.save(str(output_path))
                urls.append(f"{settings.static_url_prefix}/pages/{filename}")
        finally:
            document.close()
        return urls

    def _process_pdf(
        self,
        task_id: int,
        file_path: Path,
        answer_patterns: List[re.Pattern],
    ) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[Dict]]:
        page_lines = self._extract_pdf_page_lines(file_path)
        all_lines = [line for lines in page_lines for line in lines]
        split_idx, inline_main_prefix, inline_answer_first_line = self._detect_answer_split(all_lines, answer_patterns)
        main_lines, answer_lines = self._apply_answer_split(
            all_lines,
            split_idx,
            inline_main_prefix,
            inline_answer_first_line,
        )

        inferred_answer_start_page: Optional[int] = None
        if answer_lines:
            inferred_answer_start_page = self._infer_answer_start_page(page_lines, split_idx, answer_lines)

        heading_answer_start_page = self._find_answer_heading_page(page_lines, answer_patterns)
        answer_start_page = (
            inferred_answer_start_page if inferred_answer_start_page is not None else heading_answer_start_page
        )

        main_page_urls, answer_page_urls = self._split_pdf_preview(task_id, file_path, answer_start_page)
        if answer_start_page is None and not answer_lines:
            main_lines = all_lines
        header_footer_items = detect_pdf_header_footer(page_lines)
        return (
            all_lines,
            main_lines,
            answer_lines,
            main_page_urls,
            answer_page_urls,
            header_footer_items,
        )

    def _convert_doc_to_docx(self, doc_path: Path) -> Path:
        out_dir = doc_path.parent
        soffice_cmd = self._resolve_libreoffice_cmd()
        if not soffice_cmd:
            raise RuntimeError(
                "LibreOffice executable not found. Install LibreOffice or set LIBREOFFICE_CMD to full soffice path."
            )

        cmd = [
            soffice_cmd,
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(out_dir),
            str(doc_path),
        ]
        proc = subprocess.run(cmd, capture_output=True)
        stdout = self._decode_process_output(proc.stdout)
        stderr = self._decode_process_output(proc.stderr)
        converted_path = out_dir / f"{doc_path.stem}.docx"
        if proc.returncode != 0 or not converted_path.exists():
            raise RuntimeError(
                f"Failed to convert .doc file. command={soffice_cmd}, "
                f"stdout={stdout}, stderr={stderr}"
            )
        return converted_path

    def _resolve_libreoffice_cmd(self) -> Optional[str]:
        configured = (settings.libreoffice_cmd or "").strip()
        candidates: List[str] = []

        if configured:
            candidates.append(configured)
            resolved = shutil.which(configured)
            if resolved:
                candidates.append(resolved)

        if os.name == "nt":
            candidates.extend(
                [
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                ]
            )
        else:
            candidates.extend(["/usr/bin/soffice", "/usr/local/bin/soffice"])

        for item in candidates:
            if not item:
                continue
            path = Path(item)
            if path.exists():
                return str(path)
            resolved = shutil.which(item)
            if resolved:
                return resolved
        return None

