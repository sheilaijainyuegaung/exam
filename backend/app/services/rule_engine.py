import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


# 规则说明：下划线与括号空提取的规则定义。
CHINESE_NUM_RE = r"[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07]+"
CIRCLED_MARKER_CLASS = r"[\u2460-\u2473\u2474-\u2487\u3251-\u325f\u32b1-\u32bf]"
UNDERLINE_RE = re.compile(r"(?:[_\uFF3F\uFE4D\uFE4E]{2,}|[\u2014]{4,})")
OPTION_PREFIX_RE = re.compile(r"^\s*[A-Da-d\uFF21-\uFF24\uFF41-\uFF44][\u3001\.\uFF0E]\s*")
LEADING_HEADING_UNDERLINE_RE = re.compile(
    r"^\s*([_\uFF3F\uFE4D\uFE4E\u2014]{2,})\s*(\d{1,4})\s*[\u3001\.\uFF0E]"
)
INDEXED_BLANK_TOKEN_RE = re.compile(
    r"[_\uFF3F\uFE4D\uFE4E]{1,}\s*\d{1,3}\s*[_\uFF3F\uFE4D\uFE4E]{1,}"
)
INDEXED_BLANK_NUMBER_RE = re.compile(
    r"[_\uFF3F\uFE4D\uFE4E]{1,}\s*(\d{1,3})\s*[_\uFF3F\uFE4D\uFE4E]{1,}"
)
ONE_SIDED_TRAILING_INDEX_RE = re.compile(
    r"(?:^|(?<=[\s，,。；;:：!！？?、]))(\d{1,3})\s*[_\uFF3F\uFE4D\uFE4E]{2,}(?![_\uFF3F\uFE4D\uFE4E\d])"
)
ONE_SIDED_LEADING_INDEX_RE = re.compile(
    r"(?:^|(?<=[\s，,。；;:：!！？?、]))[_\uFF3F\uFE4D\uFE4E]{2,}\s*(\d{1,3})(?!\d)(?=(?:[\s，,。；;:：!！？?、]|$))"
)
LEADING_QUESTION_MARK_BLANK_RE = re.compile(
    rf"^\s*(?:[\uFF08(]\s*\d{{1,3}}\s*[\uFF09)]|\d{{1,4}}\s*[\u3001\.\uFF0E]|{CIRCLED_MARKER_CLASS})\s*[\uFF1F?]+\s*(?=[\u4e00-\u9fa5A-Za-z])"
)
EMPTY_BRACKET_RE = re.compile(r"[\uFF08(]\s*[\uFF09)]")
MALFORMED_EMPTY_BRACKET_WITH_SCORE_RE = re.compile(
    r"[\uFF08(]\s*[\u3000\s]*[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]\s*[\uFF09)]"
)
INLINE_PAREN_NUM_RE = re.compile(r"[\uFF08(]\s*\d{1,3}\s*[\uFF09)]")
INLINE_CHOICE_NUM_RE = re.compile(
    r"[\uFF08(]\s*[\u3000\s]*[\uFF09)]\s*\d{1,4}\s*[\u3001\.\uFF0E]"
)
SINGLE_QUESTION_PROMPT_HEADING_RE = re.compile(
    r"^\s*(?:阅读|读|根据|结合).{0,120}?完成第\s*(\d{1,3})\s*题(?:[。．\.,，;；:：\s]|$)"
)
RANGE_QUESTION_PROMPT_RE = re.compile(
    r"(?:回答|完成)\s*(?:第\s*)?\d{1,3}\s*[-~\uFF5E\u2013\u2014\u2015\u2212至到]\s*\d{1,3}\s*题"
)
NON_NUMBERED_UNDERLINE_PROMPT_RE = re.compile(
    r"(?:回答问题|默写古诗|古诗默写|补全古诗|古诗文默写|根据.+回答问题|阅读.+回答问题)"
)
INLINE_ARABIC_NUM_RE = re.compile(
    r"(?:(?<=^)|(?<=[\s\u3000]))(\d{1,4})\s*[\u3001\.\uFF0E](?!\d)"
)
INLINE_COMPACT_ARABIC_NUM_RE = re.compile(
    r"(\d{1,4})\s*[\u3001\.\uFF0E](?=[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A\u4e00-\u9fa5_\uFF3F\uFE4D\uFE4E\uFF08(])"
)
INLINE_CIRCLED_MARKER_RE = re.compile(rf"{CIRCLED_MARKER_CLASS}")

QUOTED_UNDERLINE_RE = re.compile(
    r"[\"\u201c\u201d\u2018\u2019']\s*[_\uFF3F\uFE4D\uFE4E\u2014]{2,}\s*[\"\u201c\u201d\u2018\u2019']"
)
QUOTED_UNDERLINE_INSTRUCTION_HINT_RE = re.compile(
    r"(?:\u753b\u51fa|\u627e\u51fa|\u6458\u6284|\u5708\u51fa|\u6807\u51fa|\u5199\u51fa|\u586b\u5165)"
)
LEADING_PAREN_ARABIC_RE = re.compile(r"^[\uFF08(]\s*\d{1,3}\s*[\uFF09)]\s*$")
SCORE_TEXT_RE = re.compile(
    r"[\uFF08(]\s*(?:\u5171\s*)?(\d+(?:\.\d+)?)\s*\u5206\s*[\uFF09)]|"
    r"(\d+(?:\.\d+)?)\s*\u5206(?=(?:[\uFF09)\]】,，。；;:：\s]|$))|"
    r"[\uFF08(]\s*(?:\u5171\s*)?(\d+(?:\.\d+)?)\s*\u5206(?=(?:[_\uFF3F\uFE4D\uFE4E\u2014\s,，。；;:：]|$))"
)
INLINE_FOLLOWING_HEADING_RE = re.compile(
    r"(?:^|[\s\u3000\)\]\uFF09\u3011,，。；;:：、])"
    r"((?:\d{1,4}\s*[\u3001\.\uFF0E]|[\uFF08(]\s*\d{1,3}\s*[\uFF09)]|第\s*\d{1,4}\s*题))\s*"
    r"(?=[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A\u4e00-\u9fa5])"
)
INLINE_OPTION_MARKER_RE = re.compile(r"[A-DＡ-Ｄa-dａ-ｄ]\s*[\.\uFF0E\u3001]")
NUMERIC_OPTION_STUB_HEADING_RE = re.compile(
    r"^\s*(?:[\uFF08(]\s*[\uFF09)]\s*)?\d{1,3}\s*[\u3001\.\uFF0E]\s*[A-DＡ-Ｄa-dａ-ｄ]\s*[\u3001\.\uFF0E]"
)
NUMERIC_SINGLE_OPTION_STUB_RE = re.compile(
    r"^\s*(?:[\uFF08(]\s*[\uFF09)]\s*)?\d{1,3}\s*[\u3001\.\uFF0E]\s*[A-DＡ-Ｄa-dａ-ｄ]\s*[\u3001\.\uFF0E]\s*.+$"
)
MERGED_BLANK_TOKEN_RE = re.compile(
    r"^([_\uFF3F\uFE4D\uFE4E\u2014]{2,})[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]$"
)
PAREN_SCORE_ONLY_RE = re.compile(r"[\uFF08(]\s*(?:\u5171\s*)?\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]")
TOTAL_SCORE_HINT_RE = re.compile(r"(?:\u5171|\u603b\u8ba1|\u603b\u5206|\u6ee1\u5206)\s*(\d+(?:\.\d+)?)\s*\u5206")
PER_ITEM_SCORE_HINT_RE = re.compile(r"(?:\u6bcf\u5c0f\u9898|\u6bcf\u9898|\u6bcf\u95ee|\u6bcf\u7a7a|\u6bcf\u4e2a)")

DEFAULT_SCORE_PATTERNS = [
    r"[\uFF08(]\s*(?:\u5171\s*)?(\d+(?:\.\d+)?)\s*\u5206\s*[\uFF09)]",
    r"(\d+(?:\.\d+)?)\s*\u5206(?=(?:[\uFF09)\]】,，。；;:：\s]|$))",
    r"[\uFF08(]\s*(?:\u5171\s*)?(\d+(?:\.\d+)?)\s*\u5206(?=(?:[_\uFF3F\uFE4D\uFE4E\u2014\s,，。；;:：]|$))",
]
COVER_TITLE_HINT_RE = re.compile(
    r"(?:\u8bd5\u5377|\u8bd5\u9898|\u8003\u8bd5|\u5b66\u5e74|\u5b66\u671f|\u6708\u8003|\u671f\u4e2d|\u671f\u672b|\u57f9\u4f18)"
)
QUESTION_START_HINT_RE = re.compile(
    rf"^\s*(?:\u7b2c\s*\d+\s*\u9898|\d{{1,4}}\s*[\u3001\.\uFF0E;；]|[\uFF08(]\s*\d{{1,3}}\s*[\uFF09)]|{CHINESE_NUM_RE}[\u3001\.\uFF0E])"
)
INLINE_CHINESE_SECTION_SPLIT_RE = re.compile(
    r"(?<=[。；;!！?？])\s*([一二三四五六七八九十])(?=(?:[、\.\uFF0E]|"
    r"\u5355\u9009|\u591a\u9009|\u9009\u62e9|\u586b\u7a7a|\u5224\u65ad|\u8ba1\u7b97|\u89e3\u7b54|\u5e94\u7528|"
    r"\u89e3(?:\u51b3|\u6c7a)\u95ee\u9898|\u4f5c\u56fe|\u9605\u8bfb|\u542c\u529b|\u4f5c\u6587|"
    r"\u89c2\u5bdf|\u627e\u89c4\u5f8b|\u731c\u4e00\u731c|\u53e3\u7b97|\u5217\u7ad6\u5f0f|\u8131\u5f0f))"
)
INLINE_ACTIVITY_SPLIT_RE = re.compile(r"(活动[一二三四五六七八九十]+[:：])")
INLINE_MATERIAL_SPLIT_RE = re.compile(r"(材料[一二三四五六七八九十甲乙丙丁]+[:：])")
INLINE_ACTIVITY_MATERIAL_HEADING_RE = re.compile(
    r"^(?:活动[一二三四五六七八九十]|任务[一二三四五六七八九十]|材料[一二三四五六七八九十甲乙丙丁])[:：]"
)
TITLE_ORDINAL_BRACKET_RE = re.compile(rf"^(?:\d+|[０-９]+|{CHINESE_NUM_RE})$")
ARABIC_RANGE_PROMPT_RE = re.compile(
    r"(?:\u8bfb|\u9605\u8bfb|\u6839\u636e|\u7ed3\u5408|\u89c2\u5bdf|\u4e0b\u56fe).{0,80}"
    r"(?:\u56de\u7b54|\u5b8c\u6210).{0,30}\d{1,3}\s*[~\uFF5E\u2013\u2014\u2015\u2212\-至到]\s*\d{1,3}\s*\u9898"
)
INTERLEAVED_CHOICE_ANSWER_PAIR_RE = re.compile(
    r"(?:^|[\s,，;；])\d{1,3}\s*[、\.\uFF0E]?\s*[A-D\uFF21-\uFF24](?=$|[\s,，;；])"
)
SINGLE_CHOICE_ANSWER_KEY_LINE_RE = re.compile(
    r"^\s*\d{1,3}\s*[、\.\uFF0E]?\s*[A-D\uFF21-\uFF24]\s*$"
)
PURE_ARABIC_INDEX_LINE_RE = re.compile(r"^\s*(\d{1,4})\s*[、\.\uFF0E]\s*$")
QUESTION_SECTION_TITLE_RE = re.compile(
    r"(?:\u5355\u9009|\u591a\u9009|\u9009\u62e9|\u586b\u7a7a|\u5224\u65ad|\u89e3\u7b54|\u7b80\u7b54|\u7efc\u5408|\u5b9e\u9a8c|"
    r"\u63a2\u7a76|\u9605\u8bfb|\u4f5c\u6587|\u542c\u529b|\u8bed\u6cd5|\u7ffb\u8bd1|\u6539\u9519|\u8ba1\u7b97|\u8bc1\u660e|"
    r"\u4f5c\u56fe|\u975e\u9009\u62e9|\u90e8\u5206|\u6a21\u5757|\u9898\u578b|"
    r"\u79ef\u7d2f|\u57fa\u7840|\u79ef\u7d2f\u4e0e\u8fd0\u7528|\u79ef\u7d2f\u8fd0\u7528|\u8bed\u8a00\u79ef\u7d2f|\u7efc\u5408\u6027\u5b66\u4e60|\u540d\u8457\u9605\u8bfb|"
    r"\u4efb\u52a1\u578b\u9605\u8bfb|\u4efb\u52a1\u578b|\u7f3a\u8bcd\u586b\u7a7a|\u7f3a\u8bcd)"
)
NON_NUMBERED_QUESTION_SECTION_LABELS = (
    "非选择题",
    "单项选择题",
    "多项选择题",
    "选择题",
    "单选题",
    "多选题",
    "单选",
    "多选",
    "判断题",
    "填空题",
    "解答题",
    "简答题",
    "阅读理解",
    "阅读题",
    "综合题",
    "材料分析题",
    "作文",
    "写作",
    "书面表达",
    "听力",
    "语言知识运用",
    "积累与运用",
    "积累运用",
)
CHOICE_SECTION_TITLE_RE = re.compile(r"(?:选择题|单选|多选|单项选择|多项选择)")
def _is_choice_root_title(title_text: str) -> bool:
    title = normalize_line(title_text or "")
    if not title:
        return False
    # “非选择题”不是选择题根，避免误应用选择题规则。
    if re.search(r"(?:非\s*选择题|非选择题|非选择)", title):
        return False
    return bool(CHOICE_SECTION_TITLE_RE.search(title))


def _extract_non_numbered_question_section_label(text: str) -> str:
    normalized = normalize_line(text or "")
    if not normalized:
        return ""
    for label in NON_NUMBERED_QUESTION_SECTION_LABELS:
        if not normalized.startswith(label):
            continue
        if len(normalized) == len(label):
            return label
        next_char = normalized[len(label)]
        if next_char in {" ", "\u3000", "：", ":", "，", ",", "。", "．"}:
            return label
    return ""


NON_QUESTION_SECTION_TITLE_RE = re.compile(
    r"(?:\u6ce8\u610f|\u987b\u77e5|\u8bf4\u660e|\u5bc6\u5c01\u7ebf|\u5b66\u6821|\u59d3\u540d|\u8003\u53f7|\u51c6\u8003\u8bc1|"
    r"\u73ed\u7ea7|\u547d\u9898|\u5ba1\u9898|\u7b54\u9898)"
)
PART_SECTION_HEADING_RE = re.compile(
    r"^\s*第\s*[一二三四五六七八九十百\d]+\s*部分"
)
PART_SECTION_HEADING_CAPTURE_RE = re.compile(
    r"^\s*第\s*([一二三四五六七八九十百\d]+)\s*部分\s*(.*)$"
)
PART_SUBSECTION_HEADING_CAPTURE_RE = re.compile(
    r"^\s*第\s*([一二三四五六七八九十百\d]+)\s*节\s*[、，,\.\uFF0E]?\s*(.*)$"
)
NAMED_PART_SECTION_RE = re.compile(
    r"^\s*((?:听力|笔试|口试|阅读|写作|语法|词汇|语言知识运用|综合运用|综合能力|完形填空|阅读理解|书面表达)\s*部分)\s*(.*)$",
    flags=re.IGNORECASE,
)
PAPER_VOLUME_HEADING_RE = re.compile(
    r"^\s*第\s*[ⅠⅡⅢⅣⅤⅥIVXLCM一二三四五六七八九十\d]+\s*卷"
)
PAPER_VOLUME_HEADING_CAPTURE_RE = re.compile(
    r"^\s*第\s*([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVXLCM一二三四五六七八九十\d]+)\s*卷\s*(.*)$",
    flags=re.IGNORECASE,
)
ALPHA_VOLUME_HEADING_RE = re.compile(
    r"^\s*(?:[A-Za-zＡ-Ｚａ-ｚ]|[甲乙丙丁]|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVXLCM]+)\s*卷"
)
PROMPT_PREFIX_SET = {
    "求",
    "解",
    "答",
    "计算",
    "作答",
    "回答",
    "请回答",
    "请计算",
    "请解答",
    "请作答",
    "试求",
    "求解",
}

ARITHMETIC_OPERATOR_RE = re.compile(r"[+\-×xX*÷/＝=＋－﹢﹣—]")
ARITHMETIC_LINE_ALLOWED_RE = re.compile(r"^[\d\.\s+\-×xX*÷/＝=＋－﹢﹣—\(\)\uFF08\uFF09]+$")
EXPLICIT_ARABIC_SECTION_TITLE_RE = re.compile(
    r"(?:\u5355\u9879\u9009\u62e9|\u591a\u9879\u9009\u62e9|\u5355\u9879\u586b\u7a7a|\u9009\u62e9\u9898|\u5224\u65ad\u9898|\u586b\u7a7a\u9898|\u89e3\u7b54\u9898|\u5e94\u7528\u9898|"
    r"\u8ba1\u7b97\u9898|\u7efc\u5408\u9898|\u5b9e\u9a8c\u9898|\u4f5c\u56fe\u9898|\u9605\u8bfb\u9898|"
    r"\u9605\u8bfb\u7406\u89e3|\u5b8c\u5f62\u586b\u7a7a|\u9009\u8bcd\u586b\u7a7a|\u7f3a\u8bcd\u586b\u7a7a|\u8865\u5168\u5bf9\u8bdd|"
    r"\u8bcd\u6c47\u8fd0\u7528|\u4e66\u9762\u8868\u8fbe|\u542c\u529b|\u542c\u529b\u6d4b\u8bd5|"
    r"\u9898\u578b|(?:\u7b2c\s*[一二三四五六七八九十\d]+\s*\u90e8\u5206)|(?:\u7b2c\s*[一二三四五六七八九十\d]+\s*\u6a21\u5757))"
)
LOOSE_ARABIC_SECTION_TITLE_RE = re.compile(
    r"(?:\u586b\u4e00\u586b|\u9009\u4e00\u9009|\u5224\u4e00\u5224|\u7b97\u4e00\u7b97|\u8fde\u4e00\u8fde|"
    r"\u505a\u4e00\u505a|\u770b\u56fe|\u89e3\u51b3\u95ee\u9898|"
    r"\u6309\u8981\u6c42(?:\u5b8c\u6210|\u56de\u7b54|\u89e3\u7b54|\u4f5c\u7b54))"
)
STRICT_ARABIC_SECTION_TITLE_RE = re.compile(
    r"^(?:\u5355\u9009\u9898|\u591a\u9009\u9898|\u5355\u9879\u9009\u62e9|\u591a\u9879\u9009\u62e9|\u5355\u9879\u586b\u7a7a|\u9009\u62e9\u9898|\u5224\u65ad\u9898|\u586b\u7a7a\u9898|"
    r"\u89e3\u7b54\u9898|\u5e94\u7528\u9898|\u8ba1\u7b97\u9898|\u7efc\u5408\u9898|\u5b9e\u9a8c\u9898|"
    r"\u4f5c\u56fe\u9898|\u9605\u8bfb\u9898|\u9605\u8bfb\u7406\u89e3|\u5b8c\u5f62\u586b\u7a7a|\u9009\u8bcd\u586b\u7a7a|"
    r"\u7f3a\u8bcd\u586b\u7a7a|\u8865\u5168\u5bf9\u8bdd|\u8bcd\u6c47\u8fd0\u7528|\u4e66\u9762\u8868\u8fbe|"
    r"\u542c\u529b|\u542c\u529b\u6d4b\u8bd5|\u9898\u578b|(?:\u7b2c\s*[一二三四五六七八九十\d]+\s*\u90e8\u5206)|(?:\u7b2c\s*[一二三四五六七八九十\d]+\s*\u6a21\u5757))$"
)
PRELUDE_META_HINT_RE = re.compile(
    r"(?:\u8003\u8bd5\u65f6\u95f4|\u6ce8\u610f\u4e8b\u9879|\u672c\u8bd5\u5377|\u4f5c\u7b54|\u586b\u5199|"
    r"\u59d3\u540d|\u73ed\u7ea7|\u5b66\u6821|\u8003\u53f7|\u51c6\u8003\u8bc1|\u5bc6\u5c01\u7ebf|\u987b\u77e5|"
    r"\u6838\u5bf9|\u7b54\u9898\u5361)"
)

# 听力说明过滤：类似"每段对话听二遍"的说明性文字
LISTENING_INSTRUCTION_RE = re.compile(
    r"(?:\u6bcf\u6bb5\u5bf9\u8bdd\u542c|\u6bcf\u6bb5\u5bf9\u8bdd\u542c\u4e24\u904d|\u542c\u4e24\u904d|"
    r"\u542c\u4e09\u904d|\u6bcf\u8ff0\u542c|\u6bcf\u8ff0\u542c\u4e24\u904d|\u8bf4\u660e\u5185\u5bb9|\u8bf4\u660e|\u4e00\u904d|\u4e24\u904d|\u4e09\u904d)"
)
READING_MATERIAL_PARENT_HINT_RE = re.compile(
    r"(?:\u9605\u8bfb\u4e0b\u9762|\u9605\u8bfb\u4e0b\u5217|\u9605\u8bfb\u4ee5\u4e0b|\u9605\u8bfb\u77ed\u6587|"
    r"\u9605\u8bfb\u6587\u6bb5|\u9605\u8bfb\u6750\u6599|\u9605\u8bfb\u7406\u89e3|\u73b0\u4ee3\u6587\u9605\u8bfb|"
    r"\u6587\u8a00\u6587\u9605\u8bfb|\u56de\u7b54\s*\d+\s*-\s*\d+\s*\u9898|\u5b8c\u6210\s*\d+\s*-\s*\d+\s*\u9898)"
)
READING_PAREN_HEADING_SKIP_RE = re.compile(
    r"^(?:\u9605\u8bfb|\u9605\u8bfb(?:\u4e0b\u9762|\u4e0b\u5217|\u4ee5\u4e0b|\u77ed\u6587|\u6587\u6bb5|\u6750\u6599|"
    r"\u7406\u89e3|\u6587\u7ae0|\u4e0a\u6587|\u4e0b\u6587|\u9009\u6587))"
)
QUESTION_DIRECTIVE_HINT_RE = re.compile(
    r"(?:\u8bf7|\u8bd5|\u6839\u636e|\u7ed3\u5408|\u5206\u6790|\u6982\u62ec|\u89e3\u91ca|\u7ffb\u8bd1|\u6307\u51fa|"
    r"\u8bf4\u660e|\u7b80\u8ff0|\u8c08\u8c08|\u5224\u65ad|\u9009\u62e9|\u5199\u51fa|\u8865\u5199|\u586b\u7a7a|"
    r"\u5b8c\u6210|\u56de\u7b54|\u4e3a\u4ec0\u4e48|\u5982\u4f55|\u4f5c\u7528|\u542b\u4e49|\u610f\u601d|\u7406\u7531|"
    r"\u542f\u793a|\u6bd4\u8f83|\u8d4f\u6790|\u5f52\u7eb3)"
)
QUESTION_DIRECTIVE_PREFIX_RE = re.compile(
    r"^(?:\u8bf7|\u8bd5|\u6839\u636e|\u7ed3\u5408|\u5206\u6790|\u6982\u62ec|\u89e3\u91ca|\u7ffb\u8bd1|"
    r"\u6307\u51fa|\u8bf4\u660e|\u7b80\u8ff0|\u8c08\u8c08|\u5224\u65ad|\u9009\u62e9|\u5199\u51fa|"
    r"\u8865\u5199|\u586b\u7a7a|\u5b8c\u6210|\u56de\u7b54|\u4e3a\u4ec0\u4e48|\u4e3a\u4f55|\u5982\u4f55|"
    r"\u6bd4\u8f83|\u8d4f\u6790|\u5f52\u7eb3|\u8054\u7cfb)"
)
READING_KEEP_CHINESE_TITLE_RE = re.compile(
    r"^(?:\u5355\u9009|\u591a\u9009|\u9009\u62e9|\u586b\u7a7a|\u5224\u65ad|\u9605\u8bfb|\u4f5c\u6587|"
    r"\u5199\u4f5c|\u542c\u529b|\u8bed\u6cd5|\u7ffb\u8bd1|\u89e3\u7b54|\u8ba1\u7b97|\u7efc\u5408|"
    r"\u79ef\u7d2f|\u6587\u8a00|\u73b0\u4ee3\u6587|\u540d\u8457|\u8bed\u8a00|\u53e3\u8bed|\u5b9e\u8df5|"
    r"\u53e4\u8bd7\u6587|\u4e66\u9762\u8868\u8fbe|\u7b2c[一二三四五六七八九十\d]+(?:\u90e8\u5206|\u6a21\u5757)|\u9644\u52a0\u9898)"
)
SECTION_TITLE_FALLBACK_HINT_RE = re.compile(
    r"(?:\u53e4\u8bd7\u6587|\u6587\u8a00\u6587|\u73b0\u4ee3\u6587|\u9605\u8bfb|\u586b\u7a7a|\u9009\u62e9|"
    r"\u540d\u8457\u9605\u8bfb|\u7efc\u5408\u5b9e\u8df5|\u5199\u4f5c|\u4f5c\u6587|\u57fa\u7840\u77e5\u8bc6|"
    r"\u8bed\u8a00\u79ef\u7d2f|\u79ef\u7d2f\u4e0e\u8fd0\u7528|\u79ef\u7d2f\u8fd0\u7528)"
)
RANGE_MARKER_PARENT_HINT_RE = re.compile(
    r"(?:\u5b8c\u6210|\u56de\u7b54|\u4f5c\u7b54|\u89e3\u7b54|\u7b54\s*\d+\s*[-\u2014\u301c~\u5230\u81f3]\s*\d+\s*\u9898)"
)
RANGE_MARKER_ONLY_RE = re.compile(r"^(?:[-\u2014\uff0d~\u301c]+|\u9898[\u3002\uff0e.]?)$")
ZERO_CHILD_SCORE_DISTRIBUTION_PARENT_HINT_RE = re.compile(
    r"(?:\u7ffb\u8bd1|\u89e3\u91ca|\u5199\u51fa|\u7b80\u7b54|\u56de\u7b54|\u6982\u62ec|\u5206\u6790|\u8bf4\u660e|\u8c08\u8c08|"
    r"\u6807\u793a|\u6807\u51fa|\u6807\u6ce8|\u505c\u987f|\u65ad\u53e5)"
)
WRITING_SECTION_TITLE_RE = re.compile(r"(?:\u4e66\u9762\u8868\u8fbe|\u4f5c\u6587|\u5199\u4f5c|\u4e60\u4f5c)")
WRITING_REQUIREMENT_HINT_RE = re.compile(
    r"(?:\u4f5c\u6587\u8981\u6c42|\u5199\u4f5c\u8981\u6c42|\u8ba4\u771f\u4e66\u5199|\u5de5\u6574|\u7f8e\u89c2|"
    r"\u4e0d\u5f97\u51fa\u73b0|\u4e0d\u5f97\u6294\u88ad|\u4e0d\u5f97\u5957\u4f5c|"
    r"\u4e0d\u5c11\u4e8e|\u4e0d\u4f4e\u4e8e|\u5b57\u6570|\u6821\u540d|\u59d3\u540d|"
    r"\u9898\u76ee\u81ea\u62df|\u81ea\u9009\u89d2\u5ea6|\u7acb\u610f\u81ea\u5b9a|"
    r"\u9664\u8bd7\u6b4c\u5916|\u6587\u4f53\u4e0d\u9650|\u9009\u62e9\u4f60\u6700\u64c5\u957f\u7684\u6587\u4f53)"
)
WRITING_PROMPT_OPTION_HINT_RE = re.compile(
    r"(?:\u547d\u9898\u4f5c\u6587|\u534a\u547d\u9898\u4f5c\u6587|\u6750\u6599\u4f5c\u6587|\u8bdd\u9898\u4f5c\u6587|"
    r"\u8bf7\u4ee5|\u9605\u8bfb\u4e0b\u9762\u6750\u6599|\u9898\u76ee[:\uff1a]|\u4efb\u9009\u5176\u4e00|\u4e8c\u9009\u4e00)"
)
STATEMENT_OPTION_COLLAPSE_HINT_RE = re.compile(
    r"(?:\u5176\u4e2d(?:\u6b63\u786e|\u9519\u8bef|\u4e0d\u6b63\u786e|\u4e0d\u7b26\u5408|\u7b26\u5408|\u6210\u7acb|\u4e0d\u6210\u7acb)|"
    r"\u6b63\u786e\u7684(?:\u662f|\u6709)|\u9519\u8bef\u7684(?:\u662f|\u6709)|\u586b\u5e8f\u53f7|\u586b\u5165\u5e8f\u53f7)"
)
ARTICLE_EXPLANATION_HEADING_RE = re.compile(
    r"(?:^|\s)(?:\u9605\u8bfb(?:\u4e0b\u9762|\u4e0b\u5217|\u4ee5\u4e0b)?(?:\u6750\u6599|\u6587\u7ae0|\u6587\u6bb5|\u8bd7\u6b4c|\u53e4\u8bd7|\u6587\u8a00\u6587)?|"
    r"\u6750\u6599[一二三四五六七八九]?|"
    r"\u4f5c\u6587\u8981\u6c42|\u5199\u4f5c\u8981\u6c42|\u6309\u8981\u6c42\u4f5c\u6587|"
    r"\u9898\u76ee[:\uff1a]|\u8bf7\u4ee5)"
)
ARTICLE_MARKER_READING_SCORED_LINE_RE = re.compile(
    r"^\s*[\uFF08(]\s*[\u7532\u4e59\u4e19\u4e01\u620a\u5df1\u5e9a\u8f9b\u58ec\u7678]\s*[\uFF09)]"
    r".*(?:\u9605\u8bfb|\u9009\u6587|\u6750\u6599|\u4e0b\u6587|\u4e0a\u6587|\u77ed\u6587)"
)
PAREN_ARABIC_SECTION_TITLE_RE = re.compile(
    r"(?:\u9605\u8bfb|\u6587\u8a00\u6587|\u73b0\u4ee3\u6587|\u542c\u529b|\u5199\u4f5c|\u4f5c\u6587|"
    r"\u90e8\u5206|\u6a21\u5757|\u9898\u578b|\u9009\u62e9|\u586b\u7a7a|\u5224\u65ad|\u5b8c\u5f62)"
)
SECTION_SCORE_CONTEXT_RE = re.compile(r"(?:\u5171|\u603b\u8ba1|\u603b\u5206|\u6ee1\u5206)\s*\d+(?:\.\d+)?\s*\u5206")
SECTION_SHARED_KEYWORDS = (
    "\u975e\u9009\u62e9\u9898",
    "\u9009\u62e9\u9898",
    "\u586b\u7a7a",
    "\u9605\u8bfb",
    "\u4f5c\u6587",
    "\u542c\u529b",
    "\u5b9e\u9a8c",
    "\u89e3\u7b54",
    "\u8ba1\u7b97",
    "\u5e94\u7528",
)


@dataclass
class HeadingCandidate:
    line_no: int
    raw: str
    token_type: str
    number_text: str
    number_value: Optional[int]
    title: str
    score: Optional[float]


@dataclass
class BlankScoreCandidate:
    line_no: int
    raw: str
    score: float
    underlines: List[str]


@dataclass
class ScoredTextCandidate:
    line_no: int
    raw: str
    score: float


@dataclass
class IndexedBlankMarkerCandidate:
    line_no: int
    raw: str
    numbers: List[int]


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line or "").strip()


def _parse_ascii_int(value: object) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    if any(ch < "0" or ch > "9" for ch in text):
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _parse_simple_chinese_int(value: object) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None

    digit_map = {
        "\u4e00": 1,
        "\u4e8c": 2,
        "\u4e09": 3,
        "\u56db": 4,
        "\u4e94": 5,
        "\u516d": 6,
        "\u4e03": 7,
        "\u516b": 8,
        "\u4e5d": 9,
    }
    allowed = set(digit_map.keys()) | {"\u5341"}
    if any(ch not in allowed for ch in text):
        return None

    if text == "\u5341":
        return 10
    if "\u5341" not in text:
        return digit_map.get(text)

    left, right = text.split("\u5341", 1)
    if left:
        tens = digit_map.get(left)
        if tens is None:
            return None
    else:
        tens = 1

    if right:
        units = digit_map.get(right)
        if units is None:
            return None
    else:
        units = 0

    value_int = tens * 10 + units
    if value_int <= 0:
        return None
    return value_int


def _to_simple_chinese_number(value: int) -> str:
    digit_map = {
        1: "\u4e00",
        2: "\u4e8c",
        3: "\u4e09",
        4: "\u56db",
        5: "\u4e94",
        6: "\u516d",
        7: "\u4e03",
        8: "\u516b",
        9: "\u4e5d",
    }
    if value <= 0:
        return str(value)
    if value < 10:
        return digit_map[value]
    if value == 10:
        return "\u5341"
    if value < 20:
        return "\u5341" + digit_map[value - 10]
    tens = value // 10
    units = value % 10
    if tens <= 9:
        if units == 0:
            return digit_map[tens] + "\u5341"
        return digit_map[tens] + "\u5341" + digit_map[units]
    return str(value)


def _strip_leading_heading_underline_prefix(line: str) -> Tuple[str, bool]:
    text = line or ""
    if not text:
        return text, False
    if not LEADING_HEADING_UNDERLINE_RE.match(text):
        return text, False
    stripped = re.sub(r"^\s*[_\uFF3F\uFE4D\uFE4E\u2014]{2,}\s*", "", text, count=1)
    return stripped, True


def _get_leading_heading_underline_range(line: str) -> Optional[Tuple[int, int]]:
    match = LEADING_HEADING_UNDERLINE_RE.match(line or "")
    if not match:
        return None
    return match.start(1), match.end(1)


def _split_inline_numbered_segments(line: str) -> List[str]:
    # 规则说明：识别规则处理的逻辑约束。
    # 规则说明：题号与层级识别的规则定义。
    text = (line or "").strip()
    if not text:
        return []

    choice_markers = list(INLINE_CHOICE_NUM_RE.finditer(text))
    if len(choice_markers) > 1:
        segments: List[str] = []
        for idx, marker in enumerate(choice_markers):
            start = marker.start()
            end = choice_markers[idx + 1].start() if idx + 1 < len(choice_markers) else len(text)
            segment = text[start:end].strip()
            if segment:
                segments.append(segment)
        if segments:
            return segments

    arabic_markers = list(INLINE_ARABIC_NUM_RE.finditer(text))
    if len(arabic_markers) > 1 and arabic_markers[0].start() == 0:
        segments: List[str] = []
        for idx, marker in enumerate(arabic_markers):
            start = marker.start()
            end = arabic_markers[idx + 1].start() if idx + 1 < len(arabic_markers) else len(text)
            segment = text[start:end].strip()
            if segment:
                segments.append(segment)
        if len(segments) > 1:
            return segments

    def _should_split_inline_arabic_heading(marker_match: re.Match) -> bool:
        start = marker_match.start()
        if start <= 0:
            return False
        prefix = text[:start].strip()
        suffix = text[start:].strip()
        if not prefix or not suffix:
            return False
        # 选项桩行（如“( )1.A...B...C...”）不应拆成“空括号 + 题号”。
        if NUMERIC_OPTION_STUB_HEADING_RE.match(suffix):
            return False

        # 规则说明：下划线与括号空提取的条件过滤。
        if not (UNDERLINE_RE.search(prefix) or EMPTY_BRACKET_RE.search(prefix)):
            return False

        # 规则说明：识别规则处理的条件过滤。
        if not re.match(r"^\d{1,4}\s*[\u3001\.\uFF0E]\s*.+$", suffix):
            return False
        suffix_title = re.sub(r"^\d{1,4}\s*[\u3001\.\uFF0E]\s*", "", suffix).strip()
        if not suffix_title:
            return False
        if not (
            SCORE_TEXT_RE.search(suffix)
            or EMPTY_BRACKET_RE.search(suffix)
            or UNDERLINE_RE.search(suffix)
            or QUESTION_DIRECTIVE_HINT_RE.search(suffix_title)
        ):
            # 规则说明：题号与层级识别的条件过滤。
            if len(suffix_title) < 8:
                return False
        return True

    if arabic_markers:
        for marker in arabic_markers:
            if _should_split_inline_arabic_heading(marker):
                prefix = text[: marker.start()].strip()
                suffix = text[marker.start() :].strip()
                return _split_inline_numbered_segments(prefix) + _split_inline_numbered_segments(suffix)

    compact_arabic_markers = list(INLINE_COMPACT_ARABIC_NUM_RE.finditer(text))
    if compact_arabic_markers:
        for marker in compact_arabic_markers:
            if _should_split_inline_arabic_heading(marker):
                prefix = text[: marker.start()].strip()
                suffix = text[marker.start() :].strip()
                return _split_inline_numbered_segments(prefix) + _split_inline_numbered_segments(suffix)
    if len(compact_arabic_markers) > 1 and compact_arabic_markers[0].start() == 0:
        def _is_safe_compact_split_marker(marker_match: re.Match) -> bool:
            start = marker_match.start()
            if start <= 0:
                return True
            idx = start - 1
            while idx >= 0 and text[idx].isspace():
                idx -= 1
            if idx < 0:
                return True
            prev_char = text[idx]
            # “5、（2008·广西玉林）12.观察...”中的“12.”多为题干内来源注记，
            # 不应拆成新题号。
            if prev_char in {"）", ")"}:
                probe = text[max(0, start - 48) : start]
                if re.search(
                    r"[\uFF08(]\s*(?:19|20)?\d{2}(?:[·\.\-－]\d{1,2})?[^)\uFF09]{0,18}[\uFF09)]\s*$",
                    probe,
                ):
                    return False
            # 仅在明显边界后才允许紧凑编号断开，避免把题干中的 0、1、2… 列表误拆成新题。
            if prev_char in {
                "。",
                "；",
                ";",
                "!",
                "！",
                "?",
                "？",
                "：",
                ":",
                "，",
                ",",
                "、",
                "）",
                ")",
                "】",
                "]",
                "》",
                ">",
                "_",
                "\uFF3F",
                "\uFE4D",
                "\uFE4E",
                "\u2014",
                "“",
                "”",
                "\"",
                "'",
            }:
                return True
            # 避免把变量下标（如 W1、F1、P1）和中文正文内容误切成新题号。
            if re.match(r"[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A0-9\uFF10-\uFF19_\u4e00-\u9fff]", prev_char):
                return False
            return False

        split_markers: List[re.Match] = [compact_arabic_markers[0]]
        for marker in compact_arabic_markers[1:]:
            if _is_safe_compact_split_marker(marker):
                split_markers.append(marker)
        if len(split_markers) <= 1:
            return [text]

        segments: List[str] = []
        for idx, marker in enumerate(split_markers):
            start = marker.start()
            end = split_markers[idx + 1].start() if idx + 1 < len(split_markers) else len(text)
            segment = text[start:end].strip()
            if segment:
                segments.append(segment)
        if len(segments) > 1:
            return segments

    circled_markers = list(INLINE_CIRCLED_MARKER_RE.finditer(text))
    # 规则说明：①②③ 等圈号若跟在“1.”或“(1)”后，按题干内容处理，不拆成独立子题。
    if len(circled_markers) > 1 and circled_markers[0].start() == 0:
        def is_circled_boundary(position: int) -> bool:
            if position <= 0:
                return True
            idx = position - 1
            while idx >= 0 and text[idx].isspace():
                idx -= 1
            if idx < 0:
                return True
            return text[idx] in {"。", "；", ";", "：", ":", "，", ",", "、", "）", ")", "_", "\uFF3F", "\uFE4D", "\uFE4E", "\u2014"}

        split_markers = [circled_markers[0]]
        for marker in circled_markers[1:]:
            if is_circled_boundary(marker.start()):
                split_markers.append(marker)
        if len(split_markers) > 1:
            segments: List[str] = []
            for idx, marker in enumerate(split_markers):
                start = marker.start()
                end = split_markers[idx + 1].start() if idx + 1 < len(split_markers) else len(text)
                segment = text[start:end].strip()
                if segment:
                    segments.append(segment)
            if len(segments) > 1:
                return segments

    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的规则定义。
    inline_chinese_sections = list(INLINE_CHINESE_SECTION_SPLIT_RE.finditer(text))
    if inline_chinese_sections:
        marker = inline_chinese_sections[0]
        start = marker.start(1)
        if start > 0:
            prefix = text[:start].strip()
            suffix = text[start:].strip()
            if prefix and suffix:
                return _split_inline_numbered_segments(prefix) + _split_inline_numbered_segments(suffix)

    # 处理“上一题末尾)二、阅读理解…”这类粘连：在明确分节标题场景下强制切开。
    inline_chinese_heading_markers = list(re.finditer(rf"{CHINESE_NUM_RE}\s*[\u3001\.\uFF0E]", text))
    for marker in inline_chinese_heading_markers:
        start = marker.start()
        if start <= 0:
            continue
        prefix = text[:start].strip()
        suffix = text[start:].strip()
        if not prefix or not suffix:
            continue
        if not re.search(r"[\uFF09)\]】。；;!！?？:：]$", prefix):
            continue
        suffix_wo_marker = re.sub(rf"^\s*{CHINESE_NUM_RE}\s*[\u3001\.\uFF0E]\s*", "", suffix)
        if not suffix_wo_marker:
            continue
        if not (
            QUESTION_SECTION_TITLE_RE.search(suffix_wo_marker)
            or EXPLICIT_ARABIC_SECTION_TITLE_RE.search(suffix_wo_marker)
            or SECTION_TITLE_FALLBACK_HINT_RE.search(suffix_wo_marker)
            or WRITING_SECTION_TITLE_RE.search(suffix_wo_marker)
            or re.search(r"[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]", suffix_wo_marker)
        ):
            continue
        return _split_inline_numbered_segments(prefix) + _split_inline_numbered_segments(suffix)

    # 行内“活动二：/材料二：”常与前一小题粘连，切开后再递归解析。
    for marker in list(INLINE_ACTIVITY_SPLIT_RE.finditer(text)) + list(INLINE_MATERIAL_SPLIT_RE.finditer(text)):
        start = marker.start(1)
        if start <= 0:
            continue
        prefix = text[:start].strip()
        suffix = text[start:].strip()
        if not prefix or not suffix:
            continue
        if not (
            SCORE_TEXT_RE.search(prefix)
            or re.search(r"[\uFF09\)\u3002\uff01\uff1f\uff1b;]$", prefix)
        ):
            continue
        return _split_inline_numbered_segments(prefix) + _split_inline_numbered_segments(suffix)

    # 行内“（一）/（二）...”标题拆分：处理“上一题末尾 + （二）新材料标题”粘连场景。
    inline_chinese_paren_markers = list(
        re.finditer(r"[\uFF08(]\s*[一二三四五六七八九十]{1,3}\s*[\uFF09)]", text)
    )
    for marker in inline_chinese_paren_markers:
        start = marker.start()
        if start <= 0:
            continue
        prefix = text[:start].strip()
        suffix = text[start:].strip()
        if not prefix or not suffix:
            continue

        prefix_tail = prefix[-1]
        has_slot_tail = bool(UNDERLINE_RE.search(prefix[-16:]))
        if prefix_tail not in {"。", "；", ";", "!", "！", "?", "？", "：", ":", "）", ")", "_", "\uFF3F", "\uFE4D", "\uFE4E", "\u2014"} and not has_slot_tail:
            continue

        suffix_wo_marker = re.sub(
            r"^\s*[\uFF08(]\s*[一二三四五六七八九十]{1,3}\s*[\uFF09)]\s*",
            "",
            suffix,
        )
        if not suffix_wo_marker:
            continue

        looks_like_heading = bool(
            re.search(
                r"(?:\u9605\u8bfb|\u77ed\u6587|\u6750\u6599|\u4f5c\u6587|\u5199\u4f5c|\u56de\u7b54|\u5b8c\u6210|\u8282\u9009|\u9898\u76ee|\u9898)",
                suffix_wo_marker,
            )
            or re.search(r"[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]", suffix_wo_marker)
            or (len(suffix_wo_marker) <= 30 and not re.search(r"[。；;！!？?]", suffix_wo_marker))
        )
        if not looks_like_heading:
            continue

        return _split_inline_numbered_segments(prefix) + _split_inline_numbered_segments(suffix)

    def is_subquestion_boundary(position: int) -> bool:
        # 规则说明：题号与层级识别的逻辑约束。
        # 规则说明：题号与层级识别的条件过滤。
        if position <= 0:
            return True
        idx = position - 1
        while idx >= 0 and text[idx].isspace():
            idx -= 1
        if idx < 0:
            return True
        return text[idx] in {
            "。",
            "；",
            ";",
            "!",
            "！",
            "?",
            "？",
            "：",
            ":",
            "）",
            ")",
            ".",
            "\uFF0E",
            "\u3001",
            "_",
            "\uFF3F",
            "\uFE4D",
            "\uFE4E",
            "\u2014",
        }

    def is_prompt_prefix(prefix_text: str) -> bool:
        normalized = re.sub(r"\s+", "", prefix_text or "")
        normalized = normalized.rstrip("：:")
        return normalized in PROMPT_PREFIX_SET

    if not re.match(r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]", text):
        markers = list(INLINE_PAREN_NUM_RE.finditer(text))
        if markers:
            first = markers[0]
            prefix = text[: first.start()].strip()
            if is_prompt_prefix(prefix):
                suffix = text[first.start() :].strip()
                if suffix:
                    return _split_inline_numbered_segments(suffix)

        if re.match(r"^\s*\d{1,4}\s*[\u3001,\uFF0C\.\uFF0E]", text):
            if markers:
                first = None
                for marker in markers:
                    if is_subquestion_boundary(marker.start()):
                        first = marker
                        break
                # 规则说明：题号与层级识别的逻辑约束。
                # 规则说明：题号与层级识别（示例：\d{1,3}）的逻辑约束。
                # 规则说明：题号与层级识别（示例：\d{1,3}）的条件过滤。
                if len(markers) >= 2:
                    marker_nums: List[int] = []
                    for marker in markers[:2]:
                        num_match = re.search(r"\d{1,3}", marker.group(0))
                        if not num_match:
                            marker_nums = []
                            break
                        marker_nums.append(int(num_match.group(0)))
                    if marker_nums == [1, 2] and markers[0].start() > 0 and (
                        first is None or first.start() != markers[0].start()
                    ):
                        first = markers[0]
                # 规则说明：题号与层级识别（示例：\d{1,3}）的逻辑约束。
                # 规则说明：题号与层级识别（示例：\d{1,3}）的条件过滤。
                if first is None and len(markers) == 1:
                    single = markers[0]
                    num_match = re.search(r"\d{1,3}", single.group(0))
                    marker_num = int(num_match.group(0)) if num_match else None
                    if marker_num == 1 and single.start() > 0:
                        suffix_text = text[single.start() :].strip()
                        after_marker = re.sub(
                            r"^\s*[\uFF08(]\s*1\s*[\uFF09)]\s*",
                            "",
                            suffix_text,
                        )
                        if re.match(
                            r"^(?:\u5148|\u518d|\u6c42|\u8bbe|\u8bd5|\u5728|\u5c06|\u628a|\u753b|\u5199|\u8ba1\u7b97|\u89e3|\u5224\u65ad|\u8bc1\u660e|\u8bf4\u660e|\u586b|\u6c42\u51fa|\u56de\u7b54|\u5b8c\u6210|\u6bd4\u8f83|\u5316\u7b80|\u82e5|\u5df2\u77e5|\u5f53|\u8bf7)",
                            after_marker,
                        ):
                            first = single
                if first is not None and first.start() > 0:
                    prefix = text[: first.start()].strip()
                    suffix = text[first.start() :].strip()
                    if prefix and suffix:
                        # “2.文中(3)(4)两段……”这类是题干中的引用编号，不是子题分隔，不能拆分。
                        if re.search(
                            r"(?:文中|第)\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]\s*$",
                            prefix,
                        ) and re.match(
                            r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]\s*(?:[一二三四五六七八九十两\d]+)?(?:段|句|项|点|处|节|章|部分|自然段)",
                            suffix,
                        ):
                            return [text]
                        # 规则说明：题号与层级识别的逻辑约束。
                        # 规则说明：题号与层级识别的条件过滤。
                        if re.fullmatch(r"\d{1,4}\s*[\u3001,\uFF0C\.\uFF0E]\s*", prefix):
                            return [text]
                        return [prefix] + _split_inline_numbered_segments(suffix)
        return [text]

    markers = list(INLINE_PAREN_NUM_RE.finditer(text))
    if len(markers) <= 1:
        return [text]

    split_markers = [markers[0]]
    for marker in markers[1:]:
        if is_subquestion_boundary(marker.start()):
            split_markers.append(marker)

    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别（示例：\d{1,3}）的逻辑约束。
    # 规则说明：题号与层级识别（示例：\d{1,3}）的条件过滤。
    if len(split_markers) <= 1 and len(markers) >= 2 and markers[0].start() == 0:
        marker_nums: List[int] = []
        for marker in markers:
            num_match = re.search(r"\d{1,3}", marker.group(0))
            if not num_match:
                marker_nums = []
                break
            marker_nums.append(int(num_match.group(0)))
        if marker_nums and all(marker_nums[i] == marker_nums[i - 1] + 1 for i in range(1, len(marker_nums))):
            split_markers = list(markers)

    if len(split_markers) <= 1:
        return [text]

    segments: List[str] = []
    for idx, marker in enumerate(split_markers):
        start = marker.start()
        end = split_markers[idx + 1].start() if idx + 1 < len(split_markers) else len(text)
        segment = text[start:end].strip()
        if segment:
            segments.append(segment)
    return segments if segments else [text]


def _expand_lines_for_parsing(lines: List[str]) -> List[str]:
    expanded: List[str] = []

    def should_merge_wrapped_underline(prev_line: str, next_line: str) -> bool:
        prev = prev_line or ""
        nxt = next_line or ""
        if not prev or not nxt:
            return False
        if not re.search(r"[_\uFF3F\uFE4D\uFE4E\u2014]{2,}\s*$", prev):
            return False
        if not re.match(r"^\s*[_\uFF3F\uFE4D\uFE4E\u2014]{2,}", nxt):
            return False
        return True

    def should_attach_following_underline(prev_line: str, next_line: str) -> bool:
        prev = prev_line or ""
        nxt = next_line or ""
        if not prev or not nxt:
            return False
        # 下一行必须是以下划线起始的续行。
        if not re.match(r"^\s*[_\uFF3F\uFE4D\uFE4E\u2014]{2,}", nxt):
            return False
        # 当前行已经有空位时，不再重复拼接。
        if _collect_blank_segments(prev):
            return False
        # 作文题干后的“文题横线/书写横线”只是版式，不应预拼接成题目正文。
        if _looks_like_writing_option_prompt(prev):
            return False
        # 仅对明确小题前缀拼接，避免把普通正文误并入。
        if not re.match(
            r"^\s*(?:"
            r"[\u2460-\u2473\u3251-\u325F\u32B1-\u32BF]"  # ①②③…
            r"|[\u2474-\u2487]"  # ⑴⑵⑶…
            r"|[\uFF08(]\s*\d{1,3}\s*[\uFF09)]"  # (1)/(2)
            r"|\d{1,4}\s*[\u3001,\uFF0C\.\uFF0E;；]"  # 1. 1、 1． 1, 1；
            r")",
            prev,
        ):
            return False
        return True

    def should_attach_following_score_only(prev_line: str, next_line: str) -> bool:
        prev = prev_line or ""
        nxt = next_line or ""
        if not prev or not nxt:
            return False
        if not re.fullmatch(r"\s*[\uFF08(]\s*(?:\u5171\s*)?\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]\s*", nxt):
            return False
        # 前一行已有分值时不拼接。
        if PAREN_SCORE_ONLY_RE.search(prev):
            return False
        # 仅拼接到明确题号行，避免误合并正文段落。
        if not re.match(
            r"^\s*(?:"
            r"\d{1,4}\s*[\u3001,\uFF0C\.\uFF0E]"
            r"|[\uFF08(]\s*\d{1,3}\s*[\uFF09)]"
            r"|[\u2460-\u2473\u3251-\u325F\u32B1-\u32BF]"
            r"|[\u2474-\u2487]"
            r"|(?:第\s*[一二三四五六七八九十百0-9]+\s*[题节部分])"
            r")",
            prev,
        ):
            return False
        return True

    def should_attach_following_question_section_continuation(prev_line: str, next_line: str) -> bool:
        prev = prev_line or ""
        nxt = next_line or ""
        if not prev or not nxt:
            return False
        prev_norm = normalize_line(prev)
        nxt_norm = normalize_line(nxt)
        if not prev_norm or not nxt_norm:
            return False
        if SCORE_TEXT_RE.search(prev_norm):
            return False
        if not _extract_non_numbered_question_section_label(prev_norm):
            return False
        if QUESTION_START_HINT_RE.match(nxt_norm) or OPTION_PREFIX_RE.match(nxt_norm):
            return False
        if _extract_non_numbered_question_section_label(nxt_norm):
            return False
        if re.match(r"^\s*(?:第\s*[一二三四五六七八九十百\d]+\s*[题节部分])", nxt_norm):
            return False
        if not (
            prev_norm.endswith(("：", ":"))
            or nxt_norm.startswith("的")
            or SCORE_TEXT_RE.search(nxt_norm)
        ):
            return False
        return True

    def should_attach_following_heading_text_continuation(prev_line: str, next_line: str) -> bool:
        prev = prev_line or ""
        nxt = next_line or ""
        if not prev or not nxt:
            return False
        prev_norm = normalize_line(prev)
        nxt_norm = normalize_line(nxt)
        if not prev_norm or not nxt_norm:
            return False
        if QUESTION_START_HINT_RE.match(nxt_norm) or OPTION_PREFIX_RE.match(nxt_norm):
            return False
        if _extract_non_numbered_question_section_label(nxt_norm):
            return False
        if not re.match(
            r"^\s*(?:"
            r"[\u2460-\u2473\u3251-\u325F\u32B1-\u32BF]"
            r"|[\u2474-\u2487]"
            r"|[\uFF08(]\s*\d{1,3}\s*[\uFF09)]"
            r")",
            prev_norm,
        ):
            return False
        # 当前行已经携带显式分值时，通常是完整小题，不再吸附下一行正文。
        if SCORE_TEXT_RE.search(prev_norm):
            return False
        if not (EMPTY_BRACKET_RE.search(nxt_norm) or _collect_blank_segments(nxt_norm)):
            return False
        if re.search(r"[。！？?；;]\s*$", prev_norm):
            return False
        return True

    def should_attach_following_question_tail_continuation(prev_line: str, next_line: str) -> bool:
        prev = prev_line or ""
        nxt = next_line or ""
        if not prev or not nxt:
            return False

        prev_norm = normalize_line(prev)
        nxt_norm = normalize_line(nxt)
        if not prev_norm or not nxt_norm:
            return False
        if QUESTION_START_HINT_RE.match(nxt_norm) or OPTION_PREFIX_RE.match(nxt_norm):
            return False
        if _extract_non_numbered_question_section_label(nxt_norm):
            return False
        if re.match(r"^\s*(?:第\s*[一二三四五六七八九十百\d]+\s*[题节部分])", nxt_norm):
            return False
        if re.search(r"[。！？?；;]\s*$", prev_norm):
            return False
        if not re.match(
            r"^\s*(?:"
            r"[\u2460-\u2473\u3251-\u325F\u32B1-\u32BF]"
            r"|[\u2474-\u2487]"
            r"|[\uFF08(]\s*\d{1,3}\s*[\uFF09)]"
            r"|\d{1,4}\s*[\u3001,\uFF0C\.\uFF0E;；]"
            r")",
            prev_norm,
        ):
            return False
        if not _collect_blank_segments(prev_norm):
            return False
        # 仅允许“下一行仍是空位续行”时拼接。
        # 若下一行只是普通句子（即使含分值），常是下一题/材料起始，不应并入。
        if not _collect_blank_segments(nxt_norm):
            return False
        return True

    physical_lines: List[str] = []
    for line in lines:
        raw = (line or "").replace("\r\n", "\n").replace("\r", "\n")
        for physical in raw.split("\n"):
            physical = physical.strip()
            if not physical:
                continue
            if physical_lines and (
                should_merge_wrapped_underline(physical_lines[-1], physical)
                or should_attach_following_underline(physical_lines[-1], physical)
                or should_attach_following_score_only(physical_lines[-1], physical)
                or should_attach_following_question_section_continuation(physical_lines[-1], physical)
                or should_attach_following_heading_text_continuation(physical_lines[-1], physical)
                or should_attach_following_question_tail_continuation(physical_lines[-1], physical)
            ):
                physical_lines[-1] = f"{physical_lines[-1]}{physical.lstrip()}"
                continue
            physical_lines.append(physical)
    for physical in physical_lines:
        expanded.extend(_split_inline_numbered_segments(physical))
    return expanded


def compile_score_patterns(patterns: Optional[List[str]]) -> List[re.Pattern]:
    raw_patterns = patterns if patterns else DEFAULT_SCORE_PATTERNS
    compiled: List[re.Pattern] = []
    for item in raw_patterns:
        try:
            compiled.append(re.compile(item))
        except re.error:
            continue
    if not compiled:
        compiled = [re.compile(item) for item in DEFAULT_SCORE_PATTERNS]
    return compiled


def _is_clock_minute_context(text: str, value_start: int) -> bool:
    idx = value_start - 1
    while idx >= 0 and text[idx].isspace():
        idx -= 1
    if idx < 0:
        return False
    prev = text[idx]
    if prev in {"时", "点", "點"}:
        return True
    if prev in {":", "："}:
        j = idx - 1
        while j >= 0 and text[j].isspace():
            j -= 1
        return j >= 0 and text[j].isdigit()
    return False


def _is_currency_fen_context(text: str, value_start: int) -> bool:
    idx = value_start - 1
    while idx >= 0 and text[idx].isspace():
        idx -= 1
    if idx < 0:
        return False
    prev = text[idx]
    if prev in {"\u89d2", "\u6bdb"}:
        return True
    prefix = text[:value_start]
    return bool(re.search(r"(?:\u5143|\u89d2|\u6bdb)\s*$", prefix))


def _is_duration_fen_context(text: str, value_start: int, match_end: int) -> bool:
    if not text:
        return False
    prefix = text[max(0, value_start - 6) : value_start]
    suffix = text[match_end : min(len(text), match_end + 6)]
    if re.search(
        r"(?:\u7528\u4e86|\u8017\u65f6|\u9700\u8981|\u8981\u8d70|\u8d70\u4e86|\u8fd0\u884c|\u7ecf\u8fc7|\u82b1\u4e86|\u5199\u4e86|\u51fa\u53d1)\s*$",
        prefix,
    ):
        return True
    if re.match(r"(?:\u949f|\u79d2|\u540e|\u524d|\u6574)", suffix):
        return True
    if re.search(r"\d+\s*\u65f6\s*\d+\s*\u5206", text):
        if re.search(r"(?:\u4e0a\u5348|\u4e0b\u5348|\u665a\u4e0a|\u65e9\u4e0a|\u51cc\u6668|\u4e2d\u5348|\u5f00\u59cb|\u7ed3\u675f|\u5199\u5b8c|\u51fa\u53d1|\u5230\u8fbe|\u8981\u8d70|\u7528\u4e86)", text):
            return True
    return False


def _has_valid_score_tail_boundary(text: str, match_end: int) -> bool:
    if not text:
        return True
    if match_end >= len(text):
        return True
    ch = text[match_end]
    return bool(re.match(r"[\uFF09)\]】,，。；;:：\s]", ch))


def _extract_scores_from_text(text: str, score_patterns: List[re.Pattern]) -> List[Tuple[float, int]]:
    hits: List[Tuple[float, int]] = []
    # 处理小写l被误认为数字1的情况（如"l0分"应为"10分"）
    processed_text = text
    if text:
        # 替换各种"l"被误认为数字1的情况
        processed_text = text.replace('l0', '10')  # l0 -> 10 (如 l0分, l0空)
        processed_text = processed_text.replace('l1', '11')  # l1 -> 11
        processed_text = processed_text.replace('l2', '12')  # l2 -> 12
        processed_text = processed_text.replace('l3', '13')  # l3 -> 13
        processed_text = processed_text.replace('l4', '14')  # l4 -> 14
        processed_text = processed_text.replace('l5', '15')  # l5 -> 15
        processed_text = processed_text.replace('l6', '16')  # l6 -> 16
        processed_text = processed_text.replace('l7', '17')  # l7 -> 17
        processed_text = processed_text.replace('l8', '18')  # l8 -> 18
        processed_text = processed_text.replace('l9', '19')  # l9 -> 19
        processed_text = re.sub(r'(\d)l(\d)', r'\1\2', processed_text)  # 1l0 -> 10, 2l0 -> 20
        processed_text = re.sub(r'l(?=\s*分)', '1', processed_text)  # l分 -> 1分 (独立时)
        processed_text = re.sub(r'l(?=\s*空)', '1', processed_text)  # l空 -> 1空 (独立时)
        processed_text = re.sub(r'l(?=\s*题)', '1', processed_text)  # l题 -> 1题 (独立时)
    for pattern in score_patterns:
        for match in pattern.finditer(processed_text or ""):
            matched_text = match.group(0) or ""
            number_match = re.search(r"\d+(?:\.\d+)?", matched_text)
            value_start_abs = match.start() + number_match.start() if number_match else match.start()
            # 规则说明：识别规则处理（示例：\d+(?:\.\d+)?）的条件过滤。
            if not matched_text.lstrip().startswith(("(", "\uFF08")) and _is_clock_minute_context(processed_text or "", value_start_abs):
                continue
            if not matched_text.lstrip().startswith(("(", "\uFF08")) and _is_currency_fen_context(processed_text or "", value_start_abs):
                continue
            if not matched_text.lstrip().startswith(("(", "\uFF08")) and _is_duration_fen_context(processed_text or "", value_start_abs, match.end()):
                continue
            # 规则说明：分数提取与分配的逻辑约束。
            # 规则说明：分数提取与分配的条件过滤。
            if not matched_text.lstrip().startswith(("(", "\uFF08")) and not _has_valid_score_tail_boundary(processed_text or "", match.end()):
                continue
            if match.groups():
                value_text = next((group for group in match.groups() if group), None)
            else:
                value_text = number_match.group(0) if number_match else None
            if not value_text:
                continue
            try:
                score = float(value_text)
            except ValueError:
                continue
            if score < 0:
                continue
            hits.append((score, match.start()))
    hits.sort(key=lambda item: item[1])
    return hits


def extract_score_from_text(text: str, score_patterns: List[re.Pattern]) -> Optional[float]:
    hits = _extract_scores_from_text(text, score_patterns)
    if not hits:
        return None
    # 返回最后一个分数（通常是总分，如"计10分"中的10分）
    return hits[-1][0]


def _extract_heading_score_from_text(text: str, score_patterns: List[re.Pattern]) -> Optional[float]:
    total_hits = list(TOTAL_SCORE_HINT_RE.finditer(text or ""))
    if total_hits:
        value_text = total_hits[-1].group(1)
        try:
            score = float(value_text)
            if score >= 0:
                return score
        except ValueError:
            pass

    hits = _extract_scores_from_text(text, score_patterns)
    # 同一分值在相邻字符位重复命中（常见于多条分值正则重叠）时，按一个命中处理，
    # 避免“12分 + 多个(1分)”场景被误判成 1 分。
    deduped_hits: List[Tuple[float, int]] = []
    for score, pos in hits:
        if deduped_hits:
            prev_score, prev_pos = deduped_hits[-1]
            if abs(float(score) - float(prev_score)) < 1e-9 and abs(int(pos) - int(prev_pos)) <= 1:
                continue
        deduped_hits.append((float(score), int(pos)))
    hits = deduped_hits
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0][0]

    normalized_text = text or ""

    # 题干同一行出现“总分 + 多个(1分)/(2分)”时，优先取首个总分，
    # 避免把后续小分值当成题干分导致 12 -> 1 或后续叠加异常。
    first_score = float(hits[0][0])
    trailing_scores = [float(score) for score, _ in hits[1:]]
    if (
        len(hits) >= 3
        and first_score >= 3
        and trailing_scores
        and all(value <= 2 for value in trailing_scores)
        and any(value < first_score for value in trailing_scores)
    ):
        return first_score

    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的规则定义。
    following_heading_pos = None
    for heading_match in INLINE_FOLLOWING_HEADING_RE.finditer(normalized_text):
        marker_pos = heading_match.start(1)
        if marker_pos <= 0:
            continue
        following_heading_pos = marker_pos
        break
    if following_heading_pos is not None:
        current_heading_hits = [score for score, pos in hits if pos < following_heading_pos]
        if current_heading_hits:
            return current_heading_hits[-1]

    # 单个括号子问内部若直接出现多个“(1分)/(2分)”且没有继续分裂出后续题号，
    # 这类通常是同一问内多个得分点，应合并成当前子问总分。
    if re.match(r"^\s*[\uFF08(]\s*\d+\s*[\uFF09)]", normalized_text):
        inline_bracket_scores = list(
            re.finditer(r"[\uFF08(]\s*(?:\u5171\s*)?(\d+(?:\.\d+)?)\s*\u5206\s*[\uFF09)]", normalized_text)
        )
        if len(inline_bracket_scores) >= 2:
            bracket_values: List[float] = []
            for match in inline_bracket_scores:
                try:
                    bracket_values.append(float(match.group(1)))
                except (TypeError, ValueError):
                    continue
            if len(bracket_values) >= 2 and len(bracket_values) == len(hits):
                return round(sum(bracket_values), 2)

    # 规则说明：分数提取与分配的逻辑约束。
    # 规则说明：分数提取与分配的条件过滤。
    if re.search(r"[\uFF08(]\s*1\s*[\uFF09)]", normalized_text):
        return hits[0][0]

    if PER_ITEM_SCORE_HINT_RE.search(normalized_text):
        return max(score for score, _ in hits)
    return hits[-1][0]


def _extract_per_item_unit_score(text: str, score_patterns: List[re.Pattern]) -> Optional[float]:
    line = text or ""
    if not PER_ITEM_SCORE_HINT_RE.search(line):
        return None
    # 规则说明：分数提取与分配的逻辑约束。
    # 规则说明：分数提取与分配的条件过滤。
    if TOTAL_SCORE_HINT_RE.search(line):
        return None
    hits = _extract_scores_from_text(line, score_patterns)
    if len(hits) != 1:
        return None
    unit = float(hits[0][0])
    if unit <= 0:
        return None
    return unit


def _heading_patterns() -> List[Tuple[str, re.Pattern]]:
    return [
        ("decimal", re.compile(r"^\s*(\d+(?:\.\d+){1,7})[\u3001,\uFF0C\.\uFF0E]?\s*(.*)$")),
        ("chinese", re.compile(rf"^\s*({CHINESE_NUM_RE})[\u3001,\uFF0C\.\uFF0E]\s*(.*)$")),
        ("appendix", re.compile(r"^\s*(附加题)(?![\u4e00-\u9fa5A-Za-z])\s*(?:[\u3001\.\uFF0E:：]\s*)?(.*)$")),
        ("chinese_loose", re.compile(rf"^\s*({CHINESE_NUM_RE})\s+(.+)$")),
        ("chinese_tight", re.compile(r"^\s*([一二三四五六七八九十])([^\s\u3001\.\uFF0E].+)$")),
        ("choice_arabic", re.compile(r"^\s*[\uFF08(]\s*[\u3000\s]*[\uFF09)]\s*(\d{1,4})\s*[\u3001,\uFF0C\.\uFF0E]?\s*(.*)$")),
        ("paren_arabic", re.compile(r"^\s*[\uFF08(]\s*(\d{1,4})\s*[\uFF09)]\s*(.*)$")),
        ("paren_arabic", re.compile(r"^\s*(\d{1,4})\s*[）)]\s*(.*)$")),
        ("circled", re.compile(rf"^\s*({CIRCLED_MARKER_CLASS})[\u3001,\uFF0C\.\uFF0E]?\s*(.*)$")),
        ("arabic", re.compile(r"^\s*(\d{1,4})\s*[\u3001,\uFF0C\.\uFF0E;；]\s*(.*)$")),
        (
            "arabic_score_tight",
            re.compile(
                r"^\s*(\d{1,4})\s*([\uFF08(]\s*(?:\u5171\s*)?\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)].+)$"
            ),
        ),
        ("arabic_tight", re.compile(r"^\s*(\d{1,3})([\u4e00-\u9fa5].+)$")),
        ("arabic_loose", re.compile(r"^\s*(\d{1,3})\s+(.+)$")),
        (
            "roman",
            re.compile(r"^\s*([IVXLCM\u2160-\u2169\u216A-\u216F]{1,8})[\u3001,\uFF0C\.\uFF0E]\s*(.*)$", flags=re.IGNORECASE),
        ),
        ("chinese_paren", re.compile(rf"^\s*[\uFF08(]\s*({CHINESE_NUM_RE})\s*[\uFF09)]\s*(.*)$")),
    ]


def _circled_number_to_int(number_text: str) -> Optional[int]:
    if not number_text:
        return None
    code = ord(number_text[0])
    if 0x2460 <= code <= 0x2473:
        return code - 0x2460 + 1
    if 0x2474 <= code <= 0x2487:
        return code - 0x2474 + 1
    if 0x3251 <= code <= 0x325F:
        return code - 0x3251 + 21
    if 0x32B1 <= code <= 0x32BF:
        return code - 0x32B1 + 36
    return None


def _is_likely_decimal_heading(line: str, number_text: str, title: str) -> bool:
    normalized_title = normalize_line(title)
    if not normalized_title:
        return False

    # 规则说明：识别规则处理的逻辑约束。
    # 规则说明：识别规则处理的逻辑约束。
    # 规则说明：识别规则处理的条件过滤。
    if number_text.count(".") >= 2:
        if not re.match(r"^\s*\d+(?:\.\d+){2,7}(?:\s*[\u3001\.\uFF0E]\s*|\s+)", line or ""):
            return False

    # 规则说明：识别规则处理的逻辑约束。
    # 规则说明：识别规则处理的逻辑约束。
    # 规则说明：识别规则处理的条件过滤。
    if number_text.count(".") == 1:
        if not re.match(r"^\s*\d+(?:\.\d+){1,7}(?:\s*[\u3001\.\uFF0E]\s*|\s+)", line or ""):
            return False
        # 规则说明：识别规则处理的逻辑约束。
        # 规则说明：识别规则处理的条件过滤。
        if re.match(r"^\s*\d+(?:\.\d+){1,7}\s+\d", line or ""):
            return False
        # 规则说明：结构归一化处理（示例：[\u4e00-\u9fa5]）的逻辑约束。
        # 规则说明：结构归一化处理（示例：[\u4e00-\u9fa5]）的规则定义。
        parts = number_text.split(".", 1)
        decimal_digits = parts[1] if len(parts) == 2 else ""
        title_starts_with_digit = bool(re.match(r"^[\s,\uFF0C\u3001;；:：-]*\d", normalized_title))
        title_has_cjk = bool(re.search(r"[\u4e00-\u9fa5]", normalized_title))
        if len(decimal_digits) >= 3 and title_starts_with_digit and not title_has_cjk:
            return False
        if re.match(
            r"^(?:[年月日时分秒点]|厘米|分米|毫米|米|m\b|cm\b|mm\b|dm\b)",
            normalized_title,
            flags=re.IGNORECASE,
        ):
            return False
    return True


def _is_likely_loose_arabic_heading(line: str, title: str, score_patterns: List[re.Pattern]) -> bool:
    normalized = normalize_line(line)
    normalized_title = normalize_line(title)
    if not normalized_title:
        return False
    if len(normalized_title) > 120:
        return False
    if OPTION_PREFIX_RE.match(normalized_title):
        return False

    # 规则说明：分数提取与分配的逻辑约束。
    # 规则说明：分数提取与分配的规则定义。
    has_score = extract_score_from_text(normalized, score_patterns) is not None
    has_empty_bracket = bool(re.search(r"[\uFF08(]\s*[\uFF09)]", normalized))
    has_underline = bool(UNDERLINE_RE.search(normalized))
    if has_underline and not has_score and not has_empty_bracket:
        # 题干中“8 比如……________”这类长段落说明行，不应误判为新题号。
        if _is_material_paragraph_like_text(normalized_title):
            return False
        if len(normalized_title) >= 28 and not (
            QUESTION_DIRECTIVE_HINT_RE.search(normalized_title)
            or re.search(r"[？?]", normalized_title)
        ):
            return False
        if re.search(r"(?:比如|例如|总之|如果|因为|所以|然后|可以|应该|通常|往往)", normalized_title):
            return False
    return has_score or has_empty_bracket or has_underline


def _is_likely_loose_chinese_heading(line: str, title: str, score_patterns: List[re.Pattern]) -> bool:
    normalized = normalize_line(line)
    normalized_title = normalize_line(title)
    if not normalized_title:
        return False
    if len(normalized) > 96:
        return False
    if OPTION_PREFIX_RE.match(normalized_title):
        return False

    has_score = extract_score_from_text(normalized, score_patterns) is not None
    title_without_score = PAREN_SCORE_ONLY_RE.sub("", normalized_title).strip()
    if has_score and not title_without_score:
        return True
    if has_score and len(title_without_score) <= 20 and not re.search(r"[？?]", title_without_score):
        return True
    if QUESTION_SECTION_TITLE_RE.search(title_without_score):
        return True
    return False


def _is_likely_tight_chinese_heading(line: str, title: str, score_patterns: List[re.Pattern]) -> bool:
    normalized = normalize_line(line)
    normalized_title = normalize_line(title)
    if not normalized_title:
        return False
    if len(normalized) > 96:
        return False

    title_without_score = PAREN_SCORE_ONLY_RE.sub("", normalized_title).strip().strip("。．.,，、；;:：")
    if not title_without_score:
        title_without_score = normalized_title
    title_core = re.sub(r"[\uFF08(]\s*\u5bfc\u5b66\u53f7[^\uFF09)]*[\uFF09)]\s*$", "", title_without_score).strip()
    if not title_core:
        title_core = title_without_score

    # “一点即可（2分）”这类续行正文不能当作“一、”标题。
    if re.match(r"^点(?:即可|就可|作答|回答)", title_core):
        return False

    if re.match(
        r"^(?:\u5e74\u7ea7|\u5b66\u671f|\u5b66\u5e74|\u6708\u8003|\u671f\u4e2d|\u671f\u672b|\u8bd5\u5377|\u8bd5\u9898|\u8c03\u7814\u5377|\u7efc\u5408\u8d28\u91cf)",
        title_core,
    ):
        return False

    has_score = extract_score_from_text(normalized, score_patterns) is not None
    has_question_hint = bool(
        re.match(
            r"^(?:\u5355\u9009|\u591a\u9009|\u9009\u62e9|\u586b\u7a7a|\u5224\u65ad|\u8ba1\u7b97|\u89e3\u7b54|\u5e94\u7528|"
            r"\u89e3(?:\u51b3|\u6c7a)\u95ee\u9898|\u4f5c\u56fe|\u9605\u8bfb|\u542c\u529b|\u4f5c\u6587|"
            r"\u53e3\u7b97|\u5217\u7ad6\u5f0f|\u8131\u5f0f|\u89e3\u51b3|\u64cd\u4f5c|\u7edf\u8ba1|\u5b9e\u9a8c|\u8bc1\u660e|"
            r"\u89c2\u5bdf|\u627e\u89c4\u5f8b|\u731c\u4e00\u731c|\u586b\u8868)",
            title_core,
        )
    )
    if re.match(
        r"^(?:\u5224\u65ad|\u9009\u62e9|\u586b\u7a7a|\u8ba1\u7b97|\u89e3\u7b54|\u5e94\u7528|\u89e3(?:\u51b3|\u6c7a)\u95ee\u9898|\u4f5c\u56fe|\u9605\u8bfb|\u542c\u529b|\u4f5c\u6587)(?:\u9898)?",
        title_core,
    ):
        has_question_hint = True

    if re.search(r"[？?]", title_core) and not has_score and not has_question_hint:
        return False

    if has_question_hint:
        return True
    if has_score and len(title_core) <= 18:
        return True
    return False


def _is_likely_tight_arabic_heading(line: str, title: str, score_patterns: List[re.Pattern]) -> bool:
    normalized = normalize_line(line)
    normalized_title = normalize_line(title)
    if not normalized_title:
        return False
    if re.match(r"^\d{4}\s*[\u5e74/\-]", normalized):
        return False
    if re.match(
        r"^(?:[\u5e74\u6708\u65e5\u65f6\u5206\u79d2\u70b9\u5c81]|\u5143|\u89d2|\u5206|\u514b|\u5343\u514b|\u516c\u65a4|\u65a4|\u5428|\u5206\u7c73|\u5398\u7c73|\u6beb\u7c73|\u5343\u7c73|\u7c73|kg|g|t|cm|mm|dm|m)",
        normalized_title,
        flags=re.IGNORECASE,
    ):
        return False

    has_score = extract_score_from_text(normalized, score_patterns) is not None
    has_empty_bracket = bool(re.search(r"[\uFF08(]\s*[\uFF09)]", normalized))
    has_underline = bool(UNDERLINE_RE.search(normalized))
    has_question_hint = bool(
        re.search(
            r"[\uFF1F?]|\u8bfb\u4f5c|\u586b\u7a7a|\u5224\u65ad|\u9009\u62e9|\u8ba1\u7b97|\u89e3\u51b3|\u8fde\u4e00\u8fde|\u91cc\u9762|\u6bd4",
            normalized_title,
        )
    )
    if re.search(r"[=＝]", normalized) and not has_score and not has_question_hint:
        return False
    return has_score or has_empty_bracket or has_underline or has_question_hint


def _is_decimal_value_expression_line(line: str, title: str) -> bool:
    normalized = normalize_line(line)
    if not normalized:
        return False
    if not re.match(r"^\d{1,4}[\.．]\d", normalized):
        return False
    if re.match(r"^\d{1,4}[\.．]\s+\d", normalized):
        return False

    normalized_title = normalize_line(title)
    if not normalized_title:
        return False

    # 规则说明：下划线与括号空提取（示例：[\u4e00-\u9fa5]）的规则定义。
    has_cjk = bool(re.search(r"[\u4e00-\u9fa5]", normalized))
    if not has_cjk and re.search(r"[=＝○><＜＋\-—－×xX*÷/]", normalized):
        # 规则说明：下划线与括号空提取（示例：[\u4e00-\u9fa5]）的逻辑约束。
        # 规则说明：下划线与括号空提取（示例：[=＝○><＜＋\-—－×xX*÷/]）的条件过滤。
        if _collect_blank_segments(normalized):
            return False
        return True

    # 规则说明：结构归一化处理的条件过滤。
    if re.match(
        r"^\d+(?:\.\d+)?\s*(?:\u5143|\u89d2|\u5206|\u5343\u514b|\u514b|\u5428|\u5343\u7c73|\u5206\u7c73|\u5398\u7c73|\u6beb\u7c73|\u7c73|kg|g|t|cm|mm|dm|m)\s*[=＝]",
        normalized_title,
        flags=re.IGNORECASE,
    ):
        return True
    if re.match(
        r"^\d+(?:\.\d+)?\s*(?:\u5143|\u89d2|\u5206|\u5343\u514b|\u514b|\u5428|\u5343\u7c73|\u5206\u7c73|\u5398\u7c73|\u6beb\u7c73|\u7c73|kg|g|t|cm|mm|dm|m)",
        normalized_title,
        flags=re.IGNORECASE,
    ) and re.search(r"[=＝+\uFF0B]", normalized):
        return True
    return False


def _is_decimal_arithmetic_expression_line(line: str) -> bool:
    normalized = normalize_line(line)
    if not normalized:
        return False
    # 规则说明：结构归一化处理（示例：^\d+\.\d+）的逻辑约束。
    # 规则说明：结构归一化处理（示例：^\d+\.\d+）的逻辑约束。
    # 规则说明：结构归一化处理（示例：^\d+\.\d+）的条件过滤。
    if not re.match(r"^\d+\.\d+", normalized):
        return False
    if not ARITHMETIC_OPERATOR_RE.search(normalized):
        return False
    return bool(ARITHMETIC_LINE_ALLOWED_RE.fullmatch(normalized))


def _unwrap_prefixed_numeric_heading(
    token_type: str,
    number_text: str,
    title: str,
) -> Tuple[str, str, str]:
    if token_type not in {"arabic", "arabic_loose"}:
        return token_type, number_text, title

    normalized_title = normalize_line(title)
    if not normalized_title:
        return token_type, number_text, title

    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的规则定义。
    nested_arabic = re.match(r"^\s*(\d{1,4})\s*[\u3001,\uFF0C\.\uFF0E;；]\s*(.*)$", normalized_title)
    if nested_arabic:
        inner_number = nested_arabic.group(1)
        inner_title = (nested_arabic.group(2) or "").strip()
        # 规则说明：题号与层级识别的逻辑约束。
        # 规则说明：题号与层级识别的逻辑约束。
        # 规则说明：题号与层级识别的条件过滤。
        if inner_title and not re.match(r"^\d", inner_title):
            return "arabic", inner_number, inner_title

    nested_paren = re.match(r"^\s*[\uFF08(]\s*(\d{1,3})\s*[\uFF09)]\s*(.*)$", normalized_title)
    if nested_paren:
        inner_number = nested_paren.group(1)
        inner_title = (nested_paren.group(2) or "").strip()
        # 规则说明：结构归一化处理的逻辑约束。
        # 规则说明：结构归一化处理的条件过滤。
        if not inner_title:
            return token_type, number_text, title
        if re.fullmatch(r"[\uFF08(]\s*\d{1,3}\s*[\uFF09)]", normalize_line(inner_title)):
            return token_type, number_text, title
        outer_value = _parse_ascii_int(number_text)
        inner_value = _parse_ascii_int(inner_number)
        # 规则说明：像“1.（1）xxx”这种重复编号，按括号编号作为同一子级题号处理。
        if outer_value is not None and inner_value is not None and outer_value == inner_value:
            return "paren_arabic", inner_number, inner_title
        # 规则说明：结构归一化处理的逻辑约束。
        # 规则说明：识别规则处理的逻辑约束。
        # 规则说明：识别规则处理的返回策略。
        return token_type, number_text, title

    return token_type, number_text, title


def _parse_heading(line_no: int, line: str, score_patterns: List[re.Pattern]) -> Optional[HeadingCandidate]:
    # 规则说明：分数提取与分配的条件过滤。
    if OPTION_PREFIX_RE.match(line):
        return None

    parse_line, _ = _strip_leading_heading_underline_prefix(line)

    paper_volume_match = PAPER_VOLUME_HEADING_CAPTURE_RE.match(parse_line)
    if paper_volume_match:
        number_text = (paper_volume_match.group(1) or "").strip()
        title_tail = normalize_line(paper_volume_match.group(2) or "")
        if title_tail:
            title_tail = re.sub(r"^[\uFF08(]\s*", "", title_tail)
            title_tail = re.sub(r"\s*[\uFF09)]$", "", title_tail)
            title_tail = title_tail.strip()
        title = title_tail or f"第{number_text}卷"
        score = _extract_heading_score_from_text(parse_line, score_patterns)
        return HeadingCandidate(
            line_no=line_no,
            raw=line,
            token_type="paper_volume",
            number_text=number_text,
            number_value=None,
            title=title,
            score=score,
        )

    part_section_match = PART_SECTION_HEADING_CAPTURE_RE.match(parse_line)
    if part_section_match:
        number_text = (part_section_match.group(1) or "").strip()
        title_tail = normalize_line(part_section_match.group(2) or "")
        section_label = f"第{number_text}部分"
        title = title_tail or section_label
        return HeadingCandidate(
            line_no=line_no,
            raw=line,
            token_type="paper_volume",
            number_text=section_label,
            number_value=None,
            title=title,
            score=None,
        )

    part_subsection_match = PART_SUBSECTION_HEADING_CAPTURE_RE.match(parse_line)
    if part_subsection_match:
        number_text = (part_subsection_match.group(1) or "").strip()
        title_tail = normalize_line(part_subsection_match.group(2) or "")
        section_label = f"第{number_text}节"
        title = title_tail or section_label
        return HeadingCandidate(
            line_no=line_no,
            raw=line,
            token_type="paper_volume",
            number_text=section_label,
            number_value=None,
            title=title,
            score=None,
        )

    named_part_match = NAMED_PART_SECTION_RE.match(parse_line)
    if named_part_match:
        section_label = normalize_line(named_part_match.group(1) or "")
        title_tail = normalize_line(named_part_match.group(2) or "")
        if section_label:
            return HeadingCandidate(
                line_no=line_no,
                raw=line,
                token_type="paper_volume",
                number_text=section_label,
                number_value=None,
                title=title_tail or section_label,
                score=None,
            )

    section_label = _extract_non_numbered_question_section_label(parse_line)
    if section_label:
        score = _extract_heading_score_from_text(parse_line, score_patterns)
        title = normalize_line(parse_line)
        if title:
            return HeadingCandidate(
                line_no=line_no,
                raw=line,
                token_type="paper_volume",
                number_text=section_label,
                number_value=None,
                title=title,
                score=score,
            )

    # 兼容“1. 选择题...”“2、非选择题...”这类“阿拉伯数字前缀”的题型分节标题。
    # 中文序号（如“一、选择题”）应按普通中文一级题号处理，不能在这里提升为 paper_volume，
    # 否则会把后续“二、...”错误降级为二级子节点。
    prefixed_section_match = re.match(
        r"^\s*([0-9０-９]{1,3})\s*[\u3001\.\uFF0E:：]\s*(.+)$",
        parse_line,
    )
    if prefixed_section_match:
        section_title_tail = normalize_line(prefixed_section_match.group(2) or "")
        prefixed_label = _extract_non_numbered_question_section_label(section_title_tail)
        if prefixed_label:
            score = _extract_heading_score_from_text(parse_line, score_patterns)
            return HeadingCandidate(
                line_no=line_no,
                raw=line,
                token_type="paper_volume",
                number_text=str(prefixed_section_match.group(1) or "").strip(),
                number_value=None,
                title=normalize_line(parse_line),
                score=score,
            )

    single_question_prompt_match = SINGLE_QUESTION_PROMPT_HEADING_RE.match(parse_line)
    if single_question_prompt_match:
        number_text = (single_question_prompt_match.group(1) or "").strip()
        try:
            number_value = int(number_text)
        except (TypeError, ValueError):
            number_value = None
        if number_value is not None and number_value > 0:
            score = _extract_heading_score_from_text(parse_line, score_patterns)
            return HeadingCandidate(
                line_no=line_no,
                raw=line,
                token_type="arabic",
                number_text=number_text,
                number_value=number_value,
                title=normalize_line(parse_line),
                score=score,
            )

    for token_type, pattern in _heading_patterns():
        match = pattern.match(parse_line)
        if not match:
            continue
        number_text = match.group(1)
        title = (match.group(2) or "").strip()
        if token_type == "decimal" and not _is_likely_decimal_heading(parse_line, number_text, title):
            continue
        if token_type == "arabic" and _is_decimal_value_expression_line(parse_line, title):
            continue
        if token_type == "arabic" and _is_decimal_arithmetic_expression_line(parse_line):
            continue
        if token_type == "chinese_loose" and not _is_likely_loose_chinese_heading(parse_line, title, score_patterns):
            continue
        if token_type == "chinese_tight" and not _is_likely_tight_chinese_heading(parse_line, title, score_patterns):
            continue
        if token_type in {"arabic_tight", "arabic_score_tight"} and not _is_likely_tight_arabic_heading(
            parse_line, title, score_patterns
        ):
            continue
        if token_type == "arabic_loose" and not _is_likely_loose_arabic_heading(parse_line, title, score_patterns):
            continue
        if token_type == "chinese_tight":
            token_type = "chinese"
        if token_type in {"arabic_tight", "arabic_score_tight"}:
            token_type = "arabic"
        if token_type == "choice_arabic":
            token_type = "arabic"
        token_type, number_text, title = _unwrap_prefixed_numeric_heading(token_type, number_text, title)
        if token_type in {"arabic", "arabic_loose", "arabic_bare"} and title:
            title = _strip_inline_option_tail_from_heading_title(title)
        score = _extract_heading_score_from_text(parse_line, score_patterns)
        if token_type in {"arabic", "arabic_loose"} and title:
            normalized_title = normalize_line(title)
            starts_with_section_keyword = bool(
                re.match(
                    r"^\s*(?:非\s*选择题|选择题|单项选择题?|多项选择题?|单选题?|多选题?|判断题|填空题|"
                    r"解答题|简答题|阅读理解|阅读题|材料(?:题|分析题?)|作文|写作|书面表达|听力|语言知识运用|积累(?:与)?运用)",
                    normalized_title,
                )
            )
            # 兼容“1. 选择题：...”“2、非选择题：...”这类带前缀编号的题型总标题。
            prefixed_section_heading = bool(
                re.match(
                    r"^\s*(?:\d+|[一二三四五六七八九十]+)\s*[\u3001\.\uFF0E:：]\s*"
                    r"(?:非\s*选择题|选择题|单项选择题?|多项选择题?|单选题?|多选题?|判断题|填空题|"
                    r"解答题|简答题|阅读理解|阅读题|材料(?:题|分析题?)|作文|写作|书面表达|听力|语言知识运用|积累(?:与)?运用)",
                    normalized_title,
                )
            )
            if score is not None and float(score or 0) > 0 and (starts_with_section_keyword or prefixed_section_heading):
                token_type = "paper_volume"
        if token_type in {"arabic", "arabic_loose"} and not title and score is None:
            token_type = "arabic_bare"
        number_value = None
        if token_type in {"arabic", "arabic_loose", "arabic_bare", "paren_arabic"}:
            try:
                number_value = int(number_text)
            except ValueError:
                number_value = None
        elif token_type == "circled":
            number_value = _circled_number_to_int(number_text)
        if token_type == "circled" and score is None:
            # 规则说明：分数提取与分配（示例：[？?]）的逻辑约束。
            # 规则说明：分数提取与分配（示例：[？?]）的规则定义。
            normalized_title = normalize_line(title or line)
            has_blank_marker = bool(UNDERLINE_RE.search(line) or EMPTY_BRACKET_RE.search(line))
            has_question_mark = bool(re.search(r"[？?]", normalized_title))
            has_directive_hint = bool(
                QUESTION_DIRECTIVE_PREFIX_RE.match(normalized_title)
                or QUESTION_DIRECTIVE_HINT_RE.search(normalized_title)
            )
            if not has_blank_marker:
                if not (has_question_mark and (has_directive_hint or len(normalized_title) <= 42)):
                    continue
                if _is_material_paragraph_like_text(normalized_title):
                    continue
        return HeadingCandidate(
            line_no=line_no,
            raw=line,
            token_type=token_type,
            number_text=number_text,
            number_value=number_value,
            title=title,
            score=score,
        )
    return None


def _strip_inline_option_tail_from_heading_title(title: str) -> str:
    text = str(title or "").strip()
    if not text:
        return text

    markers = list(INLINE_OPTION_MARKER_RE.finditer(text))
    if len(markers) < 2:
        return text

    split_at = markers[0].start()
    if split_at < 6:
        return text

    stem = normalize_line(text[:split_at]).strip()
    if not stem:
        return text

    # 规则说明：仅在明显“题干 + 选项同一行”的场景裁剪，避免误伤普通内容。
    if not (
        len(stem) >= 18
        or re.search(r"[\uFF08(][^\uFF08\uFF09()]{0,30}[\uFF09)]", stem)
        or re.search(r"[？?]", stem)
        or re.search(r"[\u4e00-\u9fa5]", stem)
    ):
        return text

    return text[:split_at].rstrip()


def _parse_blank_score(line_no: int, line: str, score_patterns: List[re.Pattern]) -> Optional[BlankScoreCandidate]:
    underline_hits = [segment for segment, _ in _collect_blank_segments(line)]
    score = extract_score_from_text(line, score_patterns)
    if OPTION_PREFIX_RE.match(line):
        if not underline_hits:
            return None
        # 仅当整行本质上是“A/B/C + 空位”时，才允许继续走空位提取。
        option_label_hits = re.findall(
            r"[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A][\u3001\.\uFF0E:：?]",
            line,
        )
        option_blank_probe = UNDERLINE_RE.sub("", line)
        option_blank_probe = EMPTY_BRACKET_RE.sub("", option_blank_probe)
        option_blank_probe = re.sub(
            r"[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A][\u3001\.\uFF0E:：?]\s*",
            " ",
            option_blank_probe,
        )
        option_blank_probe = re.sub(r"[\s\u3000,，。；;:：、\(\)\[\]【】（）]+", "", option_blank_probe)
        if len(option_label_hits) < 2 or re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", option_blank_probe):
            return None
    if not underline_hits:
        # 规则说明：下划线与括号空提取的逻辑约束。
        # 规则说明：下划线与括号空提取的规则定义。
        bracket_slots = _collect_empty_bracket_slot_segments(line)
        bracket_count = len(bracket_slots)
        if bracket_count <= 0:
            return None
        normalized_line = normalize_line(line)
        has_question_semantic = bool(QUESTION_DIRECTIVE_PREFIX_RE.match(normalized_line))
        if (
            score is None
            and _is_material_paragraph_like_text(normalized_line)
            and not has_question_semantic
        ):
            # 材料段落中的“（ ）”常用于文章内容示例，不能并入上一题空位。
            return None
        if not _is_pure_empty_bracket_line(line) and bracket_count < 2:
            # 规则说明：分数提取与分配（示例：____）的逻辑约束。
            # 规则说明：分数提取与分配（示例：____）的条件过滤。
            if score is None:
                return None
        underline_hits = ["____" for _ in range(bracket_count)]
    if not underline_hits:
        return None
    return BlankScoreCandidate(
        line_no=line_no,
        raw=line,
        score=float(score) if score is not None else 0.0,
        underlines=underline_hits,
    )


def _parse_scored_text(line_no: int, line: str, score_patterns: List[re.Pattern]) -> Optional[ScoredTextCandidate]:
    if not line:
        return None
    if PART_SECTION_HEADING_RE.search(line):
        return None
    if PAPER_VOLUME_HEADING_RE.search(line):
        return None
    if ALPHA_VOLUME_HEADING_RE.search(line):
        return None
    if not PAREN_SCORE_ONLY_RE.search(line):
        return None
    # 标题行（含题号/层级号）上的分值由 heading 统一处理，避免 scored_text 重复落点后累加。
    heading_probe = _parse_heading(line_no, line, score_patterns)
    if heading_probe is not None:
        return None
    score = extract_score_from_text(line, score_patterns)
    if score is None:
        return None
    if UNDERLINE_RE.search(line):
        return None
    normalized = normalize_line(line)
    if re.fullmatch(r"[\uFF08(]\s*(?:\u5171\s*)?\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]", normalized):
        return None
    return ScoredTextCandidate(
        line_no=line_no,
        raw=line,
        score=float(score),
    )


def _parse_indexed_blank_markers(line_no: int, line: str) -> Optional[IndexedBlankMarkerCandidate]:
    if not line:
        return None
    numbers: List[int] = []
    seen = set()
    for match in INDEXED_BLANK_NUMBER_RE.finditer(line):
        value_text = match.group(1)
        if not value_text:
            continue
        try:
            value = int(value_text)
        except ValueError:
            continue
        if value in seen:
            continue
        seen.add(value)
        numbers.append(value)
    if not numbers:
        return None
    has_one_sided_marker = bool(ONE_SIDED_TRAILING_INDEX_RE.search(line) or ONE_SIDED_LEADING_INDEX_RE.search(line))
    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的条件过滤。
    if has_one_sided_marker:
        ordered_unique = sorted(set(numbers))
        inferred: List[int] = []
        for left, right in zip(ordered_unique, ordered_unique[1:]):
            if right - left == 2:
                inferred.append(left + 1)
        if inferred:
            numbers = sorted(set(numbers + inferred))
    return IndexedBlankMarkerCandidate(
        line_no=line_no,
        raw=line,
        numbers=numbers,
    )


def _extract_score_with_positions(line: str) -> List[Tuple[float, int]]:
    hits: List[Tuple[float, int]] = []
    for match in SCORE_TEXT_RE.finditer(line or ""):
        matched_text = match.group(0) or ""
        number_match = re.search(r"\d+(?:\.\d+)?", matched_text)
        value_start_abs = match.start() + number_match.start() if number_match else match.start()
        if not matched_text.lstrip().startswith(("(", "\uFF08")) and _is_clock_minute_context(line or "", value_start_abs):
            continue
        if not matched_text.lstrip().startswith(("(", "\uFF08")) and _is_currency_fen_context(line or "", value_start_abs):
            continue
        if not matched_text.lstrip().startswith(("(", "\uFF08")) and _is_duration_fen_context(line or "", value_start_abs, match.end()):
            continue
        if not matched_text.lstrip().startswith(("(", "\uFF08")) and not _has_valid_score_tail_boundary(line or "", match.end()):
            continue
        value_text = next((group for group in match.groups() if group), None)
        if not value_text:
            continue
        try:
            score = float(value_text)
        except ValueError:
            continue
        if score < 0:
            continue
        hits.append((score, match.start()))
    return hits


def _collect_blank_segments(line: str) -> List[Tuple[str, int]]:
    text = line or ""
    heading_prefix_range = _get_leading_heading_underline_range(text)
    indexed_marker_count = len(list(INDEXED_BLANK_NUMBER_RE.finditer(text)))
    one_sided_marker_count = len(list(ONE_SIDED_TRAILING_INDEX_RE.finditer(text))) + len(
        list(ONE_SIDED_LEADING_INDEX_RE.finditer(text))
    )
    if indexed_marker_count + one_sided_marker_count >= 3:
        # 规则说明：下划线与括号空提取的逻辑约束。
        # 规则说明：下划线与括号空提取的返回策略。
        return []

    indexed_ranges: List[Tuple[int, int]] = [
        (match.start(), match.end()) for match in INDEXED_BLANK_TOKEN_RE.finditer(text)
    ]
    has_empty_bracket = bool(EMPTY_BRACKET_RE.search(text))
    quote_ranges: List[Tuple[int, int]] = []
    quote_pairs: List[Tuple[str, str]] = [("\u201c", "\u201d"), ('"', '"'), ("\u2018", "\u2019"), ("'", "'")]
    for open_q, close_q in quote_pairs:
        cursor = 0
        text_len = len(text)
        while cursor < text_len:
            start = text.find(open_q, cursor)
            if start < 0:
                break
            end = text.find(close_q, start + len(open_q))
            if end < 0:
                break
            quote_ranges.append((start, end + len(close_q)))
            cursor = end + len(close_q)
    quote_ranges.sort(key=lambda item: item[0])

    def in_indexed_blank_token(start: int, end: int) -> bool:
        for range_start, range_end in indexed_ranges:
            if start >= range_start and end <= range_end:
                return True
        return False

    def in_quote_range(start: int, end: int) -> bool:
        for quote_start, quote_end in quote_ranges:
            if start >= quote_start and end <= quote_end:
                return True
        return False

    def is_instruction_quote_blank(start: int, end: int) -> bool:
        if not in_quote_range(start, end):
            return False
        if end - start > 4:
            return False
        prefix = re.sub(r"\s+", "", text[max(0, start - 8) : start]).rstrip(
            "\u201c\u201d\u2018\u2019\"'.,\uFF0C\u3002;；:：!?？"
        )
        suffix = re.sub(r"\s+", "", text[end : min(len(text), end + 12)]).lstrip(
            "\u201c\u201d\u2018\u2019\"'"
        )
        if re.search(r"(?:用|请用|并用|分别用|画|划|圈|选|标|找)$", prefix):
            if re.match(r"(?:画|划|圈|选|标|找|填|写|出|句|词|字|原因|读音|表示|标示|标出|[的地得])", suffix):
                return True
        if re.search(r"(?:画|划|圈|标)$", prefix) and suffix.startswith("的"):
            return True
        return False

    def follows_numeric_index(start: int, end: int) -> bool:
        idx = start - 1
        skipped_spaces = 0
        while idx >= 0 and text[idx].isspace():
            skipped_spaces += 1
            idx -= 1
        # 规则说明：识别规则处理的逻辑约束。
        # 规则说明：识别规则处理的逻辑约束。
        # 规则说明：识别规则处理的条件过滤。
        if idx < 0 or not ("0" <= text[idx] <= "9"):
            return False

        run_end = idx + 1
        run_start = idx
        while run_start - 1 >= 0 and ("0" <= text[run_start - 1] <= "9"):
            run_start -= 1
        if run_end - run_start > 3:
            return False
        if skipped_spaces > 0:
            return False

        before = text[run_start - 1] if run_start - 1 >= 0 else ""
        if before in {".", "\uFF0E"}:
            return False
        if before and (before.isdigit() or before in {"_", "\uFF3F", "\uFE4D", "\uFE4E"}):
            return False
        # 规则说明：识别规则处理（示例：[A-Za-z]）的逻辑约束。
        # 规则说明：识别规则处理（示例：[A-Za-z]）的条件过滤。
        if before and re.match(r"[A-Za-z]", before):
            return False

        after = end
        while after < len(text) and text[after].isspace():
            after += 1
        if after < len(text) and text[after].isdigit():
            return False

        # 规则说明：识别规则处理的条件过滤。
        if end - start >= 8:
            return False
        return True

    segments: List[Tuple[str, int]] = []
    for match in UNDERLINE_RE.finditer(text):
        start = match.start()
        end = match.end()
        if heading_prefix_range is not None and start == heading_prefix_range[0] and end == heading_prefix_range[1]:
            # 规则说明：下划线与括号空提取的逻辑约束。
            # 规则说明：下划线与括号空提取的逻辑约束。
            continue
        # 规则说明：下划线与括号空提取的逻辑约束。
        # 规则说明：下划线与括号空提取的条件过滤。
        if has_empty_bracket and in_quote_range(start, end):
            continue
        # 规则说明：下划线与括号空提取的逻辑约束。
        # 规则说明：下划线与括号空提取的条件过滤。
        if is_instruction_quote_blank(start, end):
            continue
        # 规则说明：下划线与括号空提取的逻辑约束。
        # 规则说明：下划线与括号空提取的条件过滤。
        if in_indexed_blank_token(start, end):
            continue
        if follows_numeric_index(start, end):
            continue
        segments.append((match.group(0), start))
    segments.sort(key=lambda item: item[1])
    return _merge_continuous_underline_segments(text, segments)


def _merge_continuous_underline_segments(
    text: str,
    segments: List[Tuple[str, int]],
) -> List[Tuple[str, int]]:
    if len(segments) <= 1:
        return segments

    # 纯答题线场景要保留多空，避免把整行多个空位误并成一个。
    pure_blank_probe = UNDERLINE_RE.sub("", text)
    pure_blank_probe = PAREN_SCORE_ONLY_RE.sub("", pure_blank_probe)
    pure_blank_probe = EMPTY_BRACKET_RE.sub("", pure_blank_probe)
    pure_blank_probe = re.sub(r"[\s\u3000,，。；;:：、\(\)\[\]【】（）]+", "", pure_blank_probe)
    if not pure_blank_probe:
        return segments

    merged: List[Tuple[str, int]] = []
    current_text, current_start = segments[0]
    current_end = current_start + len(current_text)
    current_token = re.sub(r"\s+", "", current_text)

    for token, start in segments[1:]:
        between = text[current_end:start]
        compact_between = re.sub(r"[\s\u3000]", "", between)
        token_compact = re.sub(r"\s+", "", token)
        if compact_between == "":
            current_token = f"{current_token}{token_compact}"
            current_end = start + len(token)
            continue

        merged.append((current_token, current_start))
        current_text, current_start = token, start
        current_end = current_start + len(current_text)
        current_token = token_compact

    merged.append((current_token, current_start))
    return merged


def _collect_empty_bracket_slot_segments(line: str) -> List[Tuple[str, int]]:
    text = line or ""
    slot_positions: Dict[int, str] = {}
    for match in EMPTY_BRACKET_RE.finditer(text):
        slot_positions.setdefault(match.start(), "____")
    for match in MALFORMED_EMPTY_BRACKET_WITH_SCORE_RE.finditer(text):
        slot_positions.setdefault(match.start(), "____")
    return [(token, start) for start, token in sorted(slot_positions.items(), key=lambda item: item[0])]


def _collect_question_mark_placeholder_segments(line: str) -> List[Tuple[str, int]]:
    text = line or ""
    if not text:
        return []
    if UNDERLINE_RE.search(text) or EMPTY_BRACKET_RE.search(text):
        return []

    marker = LEADING_QUESTION_MARK_BLANK_RE.search(text)
    if marker is None:
        return []

    normalized = normalize_line(text)
    if not normalized:
        return []
    # 仅处理“编号后紧跟问号占位”的乱码兜底，避免影响正常疑问句。
    if re.search(r"[\uFF1F?].*[\uFF1F?]", normalized):
        return []
    if QUESTION_DIRECTIVE_HINT_RE.search(normalized):
        return []

    return [("____", marker.start())]


def _build_scored_underline_segments(line: str, fallback_score: float = 0.0) -> List[Tuple[str, float]]:
    segments = _collect_blank_segments(line)
    bracket_segments = _collect_empty_bracket_slot_segments(line)
    if segments and bracket_segments:
        existing_positions = {start for _, start in segments}
        for token, start in bracket_segments:
            if start not in existing_positions:
                segments.append((token, start))
        segments.sort(key=lambda item: item[1])
    elif not segments:
        # 规则说明：下划线与括号空提取的逻辑约束。
        # 规则说明：下划线与括号空提取的逻辑约束。
        # "（ （1分））".
        segments = bracket_segments
    if not segments and fallback_score > 0:
        segments = _collect_question_mark_placeholder_segments(line)
    if not segments:
        return []

    assigned_scores: List[Optional[float]] = [None for _ in segments]
    used_indexes = set()
    score_hits = _extract_score_with_positions(line)

    # 规则说明：分数提取与分配的逻辑约束。
    # 规则说明：分数提取与分配的条件过滤。
    if (
        len(segments) > 1
        and score_hits
        and re.match(r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]", line or "")
    ):
        return [(underline_text, 0.0) for underline_text, _ in segments]

    for score_value, score_pos in score_hits:
        before_indexes = [
            idx for idx, (_, underline_pos) in enumerate(segments)
            if idx not in used_indexes and underline_pos <= score_pos
        ]
        if before_indexes:
            target_idx = before_indexes[-1]
        else:
            remaining_indexes = [idx for idx in range(len(segments)) if idx not in used_indexes]
            if not remaining_indexes:
                continue
            target_idx = remaining_indexes[0]

        assigned_scores[target_idx] = score_value
        used_indexes.add(target_idx)

    if all(score is None for score in assigned_scores) and fallback_score > 0:
        if len(segments) == 1:
            assigned_scores[-1] = float(fallback_score)
        else:
            total = float(fallback_score)
            count = len(segments)
            base = round(total / count, 2)
            assigned = [base for _ in range(count)]
            diff = round(total - base * count, 2)
            assigned[-1] = round(assigned[-1] + diff, 2)
            for idx, score_value in enumerate(assigned):
                assigned_scores[idx] = score_value

    result: List[Tuple[str, float]] = []
    for idx, (underline_text, _) in enumerate(segments):
        result.append((underline_text, assigned_scores[idx] if assigned_scores[idx] is not None else 0.0))
    return result


def _format_blank_segments_from_line(line: str, fallback_score: float = 0.0) -> str:
    segments = _build_scored_underline_segments(line, fallback_score=fallback_score)
    if not segments:
        return ""
    return " ".join(f"{underline}{_format_score_text(score)}" for underline, score in segments)


def _format_zero_blank_segments_from_line(line: str) -> str:
    underlines = [segment for segment, _ in _collect_blank_segments(line)]
    if not underlines:
        return ""
    return " ".join(f"{underline}{_format_score_text(0.0)}" for underline in underlines)


def _is_single_empty_slot_paren_subquestion(raw_text: str, token_type: str, score: Optional[float]) -> bool:
    if token_type != "paren_arabic":
        return False
    if score is None or float(score) <= 0:
        return False
    text = str(raw_text or "")
    if not text:
        return False
    if _collect_blank_segments(text):
        return False
    empty_matches = list(EMPTY_BRACKET_RE.finditer(text))
    if len(empty_matches) != 1:
        return False
    slots = _build_scored_underline_segments(text, fallback_score=float(score))
    return len(slots) == 1


def _is_blank_dominant_continuation_line(line: str) -> bool:
    text = normalize_line(line or "")
    if not text:
        return True
    text = PAREN_SCORE_ONLY_RE.sub("", text)
    text = re.sub(r"\d+(?:\.\d+)?\s*\u5206(?=(?:[\uFF09)\]】,，。；;:：\s]|$))", "", text)
    text = re.sub(r"[_\uFF3F\uFE4D\uFE4E\u2014]{2,}", "", text)
    text = re.sub(
        r"[\s\u3000,\uFF0C\.\u3002;；:：、\-—→=＝<＜>＞~～·•!！?？\(\)\[\]【】\uFF08\uFF09]+",
        "",
        text,
    )
    return not bool(re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", text))


def _has_shared_section_keyword(context_line: str, heading_title: str) -> bool:
    context = normalize_line(context_line)
    title = normalize_line(heading_title)
    if not context or not title:
        return False
    for keyword in SECTION_SHARED_KEYWORDS:
        if keyword in context and keyword in title:
            return True
    return False


def _infer_heading_score_from_context(
    lines: List[str],
    line_no: int,
    heading_title: str,
    score_patterns: List[re.Pattern],
) -> Optional[float]:
    if not lines or line_no <= 0:
        return None

    for offset in (1, 2):
        idx = line_no - offset
        if idx < 0 or idx >= len(lines):
            continue
        context_line = normalize_line(lines[idx] or "")
        if not context_line:
            continue
        if not SECTION_SCORE_CONTEXT_RE.search(context_line):
            continue
        if not _has_shared_section_keyword(context_line, heading_title):
            continue
        score = extract_score_from_text(context_line, score_patterns)
        if score is not None and float(score) > 0:
            return float(score)
    return None


def _should_zero_continuation_blank_scores(parent: Dict, candidate: BlankScoreCandidate) -> bool:
    token_type = str(parent.get("_tokenType") or "")
    if token_type not in {"paren_arabic", "arabic", "arabic_loose", "arabic_bare", "decimal"}:
        return False

    line = candidate.raw or ""
    if re.match(r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]", line):
        # 规则说明：下划线与括号空提取（示例：if re.match(r）的逻辑约束。
        # 规则说明：下划线与括号空提取的返回策略。
        return False

    underline_count = len(_collect_blank_segments(line))
    if underline_count <= 0:
        return False

    score_hits = _extract_score_with_positions(line)
    if len(score_hits) != 1:
        return False

    parent_has_blank = bool(_collect_blank_segments(str(parent.get("rawText") or "")))
    merged_blank_segments = parent.get("_mergedBlankSegments")
    if isinstance(merged_blank_segments, list) and merged_blank_segments:
        parent_has_blank = True

    if underline_count == 1 and not parent_has_blank:
        return False

    if not _is_blank_dominant_continuation_line(line):
        return False

    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的返回策略。
    return True


BLANK_SUBITEM_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"错误\s*\d{1,3}|"
    r"第\s*\d{1,3}\s*空|空\s*\d{1,3}|"
    r"[\uFF08(]\s*\d{1,3}\s*[\uFF09)]\s*[:：]?|"
    r"(?:\d{1,3}|[一二三四五六七八九十]{1,3})\s*[\u3001\.\uFF0E:：]"
    r")"
)


def _should_accumulate_blank_line_score(parent: Dict, candidate: BlankScoreCandidate) -> bool:
    token_type = str(parent.get("_tokenType") or "")
    if token_type not in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
        return False
    if parent.get("children"):
        return False
    if float(candidate.score or 0) <= 0:
        return False

    line = candidate.raw or ""
    underline_count = len(candidate.underlines or [])
    if underline_count <= 0:
        underline_count = len(_collect_blank_segments(line))
    if underline_count <= 0:
        return False

    normalized = normalize_line(line)
    if not BLANK_SUBITEM_PREFIX_RE.match(normalized):
        return False

    parent_line_no = int(parent.get("lineNumber") or 0) - 1
    distance = candidate.line_no - parent_line_no
    if distance <= 0 or distance > 12:
        return False
    return True


def detect_second_level_mode_auto(candidates: List[HeadingCandidate]) -> str:
    groups: List[List[int]] = []
    current_group: List[int] = []
    has_chinese = False

    for item in candidates:
        if item.token_type in {"chinese", "chinese_loose", "appendix", "paper_volume"}:
            has_chinese = True
            if current_group:
                groups.append(current_group)
            current_group = []
        elif item.token_type in {"arabic", "arabic_loose"} and has_chinese and item.number_value is not None:
            current_group.append(item.number_value)

    if current_group:
        groups.append(current_group)

    if len(groups) < 2:
        return "unknown"

    first_values = [group[0] for group in groups if group]
    if not first_values:
        return "unknown"

    restart_ratio = sum(1 for value in first_values if value == 1) / len(first_values)
    if restart_ratio >= 0.6:
        return "restart"

    merged = [value for group in groups for value in group]
    if len(merged) >= 2:
        non_decreasing = all(merged[i] >= merged[i - 1] for i in range(1, len(merged)))
        if non_decreasing and any(value > 1 for value in first_values):
            return "continuous"

    return "unknown"


def _calc_level(
    candidate: HeadingCandidate,
    max_level: int,
    has_chinese_level1: bool,
    has_non_roman_level1: bool,
    has_arabic: bool,
    last_level: Optional[int],
    has_paper_volume: bool = False,
) -> int:
    if candidate.token_type == "decimal":
        return min(len(candidate.number_text.split(".")), max_level)
    if candidate.token_type in {"chinese", "chinese_loose", "paper_volume"}:
        # 中文大题序号（如“一、/二、”）始终视为一级。
        # 不能因为文中出现“第Ⅱ卷”等分卷标题就把中文序号降级，
        # 否则会把“二、非选择题”误挂到“一、...”下面。
        return 1
    if candidate.token_type == "roman":
        # 当文档只有 I/II/III 这类罗马分段时，应把它当作一级；只有在已存在中文一级时才降为二级。
        return 2 if has_non_roman_level1 else 1
    if candidate.token_type == "chinese_paren":
        return 2 if has_chinese_level1 else 1
    if candidate.token_type in {"arabic", "arabic_loose", "arabic_bare"}:
        return 2 if has_chinese_level1 else 1
    if candidate.token_type == "paren_arabic":
        if has_chinese_level1 and has_arabic:
            return min(3, max_level)
        return 2
    if candidate.token_type == "circled":
        if last_level is not None:
            if last_level >= 4:
                return min(last_level, max_level)
            return min(last_level + 1, max_level)
        if has_chinese_level1 and has_arabic:
            return min(4, max_level)
        if has_arabic:
            return min(3, max_level)
        return 2
    return 1


def _adjust_arabic_level_by_chinese_paren_context(
    current_level: int,
    stack: List[Dict],
    max_level: int,
    force_bind: bool = True,
    current_item: Optional[HeadingCandidate] = None,
) -> int:
    if not force_bind:
        return current_level
    # 规则说明：题号与层级识别（示例：_bindSectionChildren）的逻辑约束。
    # 规则说明：题号与层级识别（示例：_bindSectionChildren）的遍历处理。
    for node in reversed(stack):
        if bool(node.get("_bindSectionChildren")):
            # 阿拉伯编号分节题（如 24、25、26）在同一大题内连续出现时应保持同级，
            # 避免被前一个分节题错误吸附为子级（典型问题：24 下挂 25/26/...）。
            if current_item is not None:
                parent_token = str(node.get("_tokenType") or "")
                if (
                    parent_token in {"arabic", "arabic_loose", "arabic_bare", "decimal"}
                    and current_item.number_value is not None
                ):
                    parent_number = _parse_ascii_int(node.get("numbering"))
                    current_score = float(current_item.score) if current_item.score is not None else 0.0
                    if (
                        parent_number is not None
                        and current_item.number_value == parent_number + 1
                        and current_score > 0
                    ):
                        continue
            parent_level = int(node.get("level", 1))
            return min(max(current_level, parent_level + 1), max_level)
        if node.get("_tokenType") == "chinese_paren":
            parent_level = int(node.get("level", 1))
            return min(parent_level + 1, max_level)
        if (
            current_item is not None
            and current_item.number_value is not None
            and current_item.number_value <= 9
            and str(node.get("_tokenType") or "") in {"arabic", "arabic_loose", "arabic_bare", "decimal"}
        ):
            parent_number = _parse_ascii_int(node.get("numbering"))
            parent_text = normalize_line(str(node.get("title") or node.get("rawText") or ""))
            if (
                parent_number is not None
                and parent_number > current_item.number_value
                and re.search(r"(?:\u9605\u8bfb|\u6587\u7ae0|\u77ed\u6587|\u6587\u6bb5|\u6750\u6599|\u56de\u7b54|\u5b8c\u6210)", parent_text)
            ):
                parent_level = int(node.get("level", 1))
                return min(max(current_level, parent_level + 1), max_level)
    return current_level


def _adjust_paren_arabic_level_by_context(
    current_level: int,
    stack: List[Dict],
    max_level: int,
) -> int:
    # 规则说明：题号与层级识别（示例：_tokenType）的遍历处理。
    for node in reversed(stack):
        token_type = node.get("_tokenType")
        node_level = int(node.get("level", 1))
        if token_type in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
            return min(node_level + 1, max_level)
        if token_type == "chinese_paren":
            return min(max(current_level, node_level + 1), max_level)
    return current_level


def _is_section_like_paren_arabic_heading(item: HeadingCandidate) -> bool:
    if item.token_type != "paren_arabic":
        return False
    if item.score is None or float(item.score) < 8:
        return False
    title = normalize_line(item.title or "")
    if not title:
        return False
    title_wo_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", title))
    if not title_wo_score:
        return False
    # “（2）阅读下面文段，完成18-22题（20分）……”这类标题可能较长，不能仅按长度过滤。
    has_strong_section_hint = bool(
        PAREN_ARABIC_SECTION_TITLE_RE.search(title_wo_score)
        or re.search(r"(?:\u9605\u8bfb\u4e0b\u9762|\u56de\u7b54|\u5b8c\u6210)\s*\d{1,3}\s*[-~\uFF5E\u2013\u2014\u2015\u2212至到]\s*\d{1,3}\s*\u9898", title_wo_score)
    )
    if len(title_wo_score) > 72 and not has_strong_section_hint:
        return False
    if not PAREN_ARABIC_SECTION_TITLE_RE.search(title_wo_score):
        if not re.search(r"(?:\u9605\u8bfb\u4e0b\u9762|\u56de\u7b54|\u5b8c\u6210)\s*\d{1,3}\s*[-~\uFF5E\u2013\u2014\u2015\u2212至到]\s*\d{1,3}\s*\u9898", title_wo_score):
            return False
    if _is_material_paragraph_like_text(title_wo_score) and not has_strong_section_hint:
        return False
    return True


def _promote_paren_arabic_section_level(
    current_level: int,
    item: HeadingCandidate,
    stack: List[Dict],
    max_level: int,
) -> int:
    if not _is_section_like_paren_arabic_heading(item):
        return current_level
    level1_parent = next((node for node in reversed(stack) if int(node.get("level", 1)) == 1), None)
    if level1_parent is None:
        return current_level
    return min(int(level1_parent.get("level", 1)) + 1, max_level)


def _adjust_circled_level_by_context(
    current_level: int,
    stack: List[Dict],
    max_level: int,
) -> int:
    # 规则说明：题号与层级识别（示例：_tokenType）的逻辑约束。
    # 规则说明：题号与层级识别（示例：_tokenType）的条件过滤。
    if not stack:
        return current_level
    top = stack[-1]
    top_type = str(top.get("_tokenType") or "")
    top_level = int(top.get("level", 1))
    if top_type == "circled":
        return min(top_level, max_level)
    if top_type in {"arabic", "arabic_loose", "decimal", "paren_arabic"}:
        return min(top_level + 1, max_level)
    return current_level


def _adjust_arabic_level_by_roman_context(
    current_level: int,
    stack: List[Dict],
    max_level: int,
) -> int:
    """当阿拉伯数字题目在罗马数字章节下面时，将其层级设为roman的下一级"""
    if not stack:
        return current_level
    # 查找父节点中是否有roman类型
    for node in reversed(stack):
        node_type = str(node.get("_tokenType") or "")
        node_level = int(node.get("level", 1))
        if node_type == "roman":
            # 如果当前level <= roman的level，则提升到roman的下一级
            if current_level <= node_level:
                return min(node_level + 1, max_level)
            return current_level
    return current_level


def _append_outline_node(roots: List[Dict], stack: List[Dict], node: Dict) -> None:
    # 当添加 Chinese 标题（level 2）时，如果当前 stack 顶部也是 level 2，
    # 需要找到 paper_volume 父节点后再添加
    node_level = node["level"]
    node_token_type = node.get("_tokenType", "")
    if node_level == 2 and node_token_type in {"chinese", "chinese_loose"}:
        # 找到 paper_volume 父节点
        target_parent = None
        for i in range(len(stack) - 1, -1, -1):
            parent_type = stack[i].get("_tokenType", "")
            if parent_type == "paper_volume":
                target_parent = stack[i]
                break
            # 如果遇到 level 1 的节点，也可能是父节点
            if stack[i].get("level", 1) == 1:
                target_parent = stack[i]
                break
        if target_parent:
            # 将 stack 弹出到目标父节点
            while stack and stack[-1] != target_parent:
                stack.pop()
            target_parent["children"].append(node)
            stack.append(node)
            return

    while stack and stack[-1]["level"] >= node_level:
        stack.pop()
    if stack:
        stack[-1]["children"].append(node)
    else:
        roots.append(node)
    stack.append(node)


def _has_following_paren_subquestion_heading(
    events: List[Tuple[str, int, object]],
    start_index: int,
    current_line_no: int,
    max_line_gap: int = 8,
) -> bool:
    for idx in range(start_index + 1, len(events)):
        event_type, _, payload = events[idx]
        if event_type != "heading":
            continue
        candidate = payload
        if not isinstance(candidate, HeadingCandidate):
            continue

        if candidate.line_no - current_line_no > max_line_gap:
            return False

        if candidate.token_type == "paren_arabic" and candidate.number_value == 2:
            return True

        if candidate.token_type in {
            "arabic",
            "arabic_loose",
            "arabic_bare",
            "decimal",
            "chinese",
            "chinese_loose",
            "roman",
            "appendix",
        }:
            return False
    return False


def _append_blank_score_node(
    roots: List[Dict],
    stack: List[Dict],
    candidate: BlankScoreCandidate,
    max_level: int,
) -> None:
    # 规则说明：分数提取与分配的逻辑约束。
    # 规则说明：分数提取与分配的条件过滤。
    if candidate.score <= 0 and _is_pure_underline_answer_line(candidate.raw):
        return

    # 无序号前缀的“说明句 + 下划线”不作为结构节点（如：默写古诗提示行后的诗句空）。
    if (
        stack
        and candidate.score <= 0
        and _collect_blank_segments(candidate.raw)
        and re.search(r"[\u4e00-\u9fa5]", candidate.raw or "")
        and not QUESTION_START_HINT_RE.match(normalize_line(candidate.raw or ""))
    ):
        normalized_raw = normalize_line(candidate.raw or "")
        parent = stack[-1]
        parent_token_type = str(parent.get("_tokenType") or "")
        parent_level = int(parent.get("level", 1))
        parent_probe_text = normalize_line(str(parent.get("rawText") or parent.get("title") or ""))
        if parent_level == 1 and parent_token_type in {"chinese", "chinese_loose", "roman", "appendix", "paper_volume"}:
            return
        if (
            parent_token_type in {"arabic", "arabic_loose", "arabic_bare", "decimal", "paren_arabic"}
            and NON_NUMBERED_UNDERLINE_PROMPT_RE.search(normalized_raw)
        ):
            return
        if (
            (_is_under_writing_section(stack) or _looks_like_writing_option_prompt(parent_probe_text))
            and _is_writing_title_placeholder_line(normalized_raw)
        ):
            return

    # 规则说明：分数提取与分配（示例：_tokenType）的逻辑约束。
    # 规则说明：分数提取与分配（示例：_tokenType）的逻辑约束。
    # 规则说明：分数提取与分配（示例：_tokenType）的条件过滤。
    if stack and candidate.score <= 0:
        parent = stack[-1]
        parent_token_type = str(parent.get("_tokenType") or "")
        if (
            parent_token_type == "chinese_paren"
            and not _has_arabic_question_children(parent)
            and _is_material_paragraph_like_text(candidate.raw)
        ):
            return
        if parent_token_type in {"chinese", "chinese_loose", "roman", "appendix"}:
            level1_parent = next(
                (node for node in reversed(stack) if int(node.get("level", 1)) == 1),
                parent,
            )
            if (
                level1_parent is not None
                and not _has_arabic_question_children(level1_parent)
                and _is_under_reading_root(stack)
                and _is_material_paragraph_like_text(candidate.raw)
            ):
                # 规则说明：分数提取与分配的逻辑约束。
                # 规则说明：分数提取与分配的逻辑约束。
                return

    blank_text = _format_blank_segments_from_line(candidate.raw, candidate.score)
    if not stack:
        roots.append(
            {
                "lineNumber": candidate.line_no + 1,
                "level": 1,
                "numbering": "",
                "title": candidate.raw,
                "rawText": candidate.raw,
                "blankText": blank_text,
                "score": candidate.score,
                "children": [],
            }
        )
        return

    parent = stack[-1]
    parent["children"].append(
        {
            "lineNumber": candidate.line_no + 1,
            "level": min(parent["level"] + 1, max_level),
            "numbering": "",
            "title": candidate.raw,
            "rawText": candidate.raw,
            "blankText": blank_text,
            "score": candidate.score,
            "children": [],
        }
    )


def _is_pure_underline_answer_line(line: str) -> bool:
    text = line or ""
    if not text or not _collect_blank_segments(text):
        return False
    stripped = UNDERLINE_RE.sub("", text)
    stripped = EMPTY_BRACKET_RE.sub("", stripped)
    stripped = re.sub(
        r"[\s\.\u3002\uFF0E,\uFF0C\u3001;；:：!！?？\"'“”‘’\(\)\uFF08\uFF09\[\]\u3010\u3011\-\u2014\u00b7\u2026]+",
        "",
        stripped,
    )
    return stripped == ""


def _is_long_single_underline_answer_line(line: str, min_length: int = 20) -> bool:
    text = line or ""
    if not _is_pure_underline_answer_line(text):
        return False
    segments = _collect_blank_segments(text)
    if len(segments) != 1:
        return False
    token, _ = segments[0]
    return len(token or "") >= min_length


def _append_scored_text_node(
    stack: List[Dict],
    candidate: ScoredTextCandidate,
    max_level: int,
) -> bool:
    if not stack:
        return False
    if _is_article_marker_reading_scored_line(candidate.raw):
        return False

    parent = stack[-1]
    parent_token = str(parent.get("_tokenType") or "")
    parent_text = normalize_line(str(parent.get("title") or parent.get("rawText") or ""))
    # 阅读分节标题（如“（二）文言文阅读”）下面的“阅读下文，回答问题（x分）”
    # 属于材料提示语，不作为结构题目节点落库。
    if (
        parent_token in {"chinese_paren", "chinese", "chinese_loose"}
        and (READING_MATERIAL_PARENT_HINT_RE.search(parent_text) or "\u9605\u8bfb" in parent_text)
        and _is_section_like_scored_text_line(candidate.raw)
        and re.search(r"(?:\u9605\u8bfb|\u56de\u7b54|\u5b8c\u6210)\s*(?:\u4e0b\u6587|\u4e0b\u5217|\u4ee5\u4e0b)?", normalize_line(candidate.raw))
    ):
        return False
    if parent_token in {"paren_arabic", "arabic", "arabic_loose", "arabic_bare", "decimal"}:
        if _is_section_like_scored_text_line(candidate.raw):
            return False

    # 规则说明：当“（1）”已是有分值的小问时，后续无编号但带分值的追问
    # 往往与“（1）/（2）/（3）”同级，不能误挂成“（1）”的子级。
    if (
        parent_token == "paren_arabic"
        and len(stack) >= 2
        and parent.get("score") is not None
        and float(parent.get("score") or 0) > 0
        and candidate.score is not None
        and float(candidate.score) > 0
        and bool(re.search(r"[？?]", candidate.raw or ""))
    ):
        sibling_parent = stack[-2]
        sibling_parent["children"].append(
            {
                "lineNumber": candidate.line_no + 1,
                "level": min(int(sibling_parent.get("level", 1)) + 1, max_level),
                "numbering": "",
                "title": candidate.raw,
                "rawText": candidate.raw,
                "blankText": _format_blank_segments_from_line(candidate.raw, candidate.score),
                "score": candidate.score,
                "children": [],
            }
        )
        return True

    parent["children"].append(
        {
            "lineNumber": candidate.line_no + 1,
            "level": min(parent["level"] + 1, max_level),
            "numbering": "",
            "title": candidate.raw,
            "rawText": candidate.raw,
            "blankText": _format_blank_segments_from_line(candidate.raw, candidate.score),
            "score": candidate.score,
            "children": [],
        }
    )
    return True


def _is_section_like_scored_text_line(line: str) -> bool:
    normalized = normalize_line(line or "")
    if not normalized:
        return False
    if not PAREN_SCORE_ONLY_RE.search(normalized):
        return False
    if UNDERLINE_RE.search(normalized):
        return False
    if EMPTY_BRACKET_RE.search(normalized):
        return False

    title_without_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", normalized))
    if not title_without_score:
        return False
    if len(title_without_score) > 40:
        return False
    if re.search(r"[？?]", title_without_score):
        return False
    if re.search(r"\u7b2c\s*[一二三四五六七八九十\d]+\s*\u9898", title_without_score):
        return False

    if QUESTION_SECTION_TITLE_RE.search(title_without_score):
        return True
    return bool(
        re.search(
            r"(?:\u53e4\u8bd7\u6587|\u6587\u8a00\u6587|\u73b0\u4ee3\u6587|\u9605\u8bfb|\u586b\u7a7a|\u9009\u62e9|\u7efc\u5408\u5b9e\u8df5|\u57fa\u7840\u77e5\u8bc6|\u8bed\u8a00\u79ef\u7d2f|\u79ef\u7d2f\u4e0e\u8fd0\u7528|\u540d\u8457\u9605\u8bfb|\u5199\u4f5c|\u4f5c\u6587|\u8bd7\u8bcd|\u9ed8\u5199)",
            title_without_score,
        )
    )


def _infer_next_root_numbering(roots: List[Dict]) -> Optional[Tuple[str, str]]:
    level1_nodes = [node for node in roots if int(node.get("level", 1)) == 1]
    if not level1_nodes:
        return None

    for node in reversed(level1_nodes):
        numbering = str(node.get("numbering") or "").strip()
        if not numbering:
            continue
        chinese_value = _parse_simple_chinese_int(numbering)
        if chinese_value is not None:
            return _to_simple_chinese_number(chinese_value + 1), "chinese"
        arabic_value = _parse_ascii_int(numbering)
        if arabic_value is not None:
            return str(arabic_value + 1), "arabic"

    fallback_index = len(level1_nodes) + 1
    first_token_type = str(level1_nodes[0].get("_tokenType") or "")
    if first_token_type in {"chinese", "chinese_loose", "roman", "appendix"}:
        return _to_simple_chinese_number(fallback_index), "chinese"
    return str(fallback_index), "arabic"


def _try_promote_scored_text_to_section_root(
    roots: List[Dict],
    stack: List[Dict],
    candidate: ScoredTextCandidate,
    max_level: int,
) -> bool:
    if not roots or not stack:
        return False
    if _is_article_marker_reading_scored_line(candidate.raw):
        return False
    if not _is_section_like_scored_text_line(candidate.raw):
        return False

    parent = stack[-1]
    parent_token = str(parent.get("_tokenType") or "")
    if parent_token not in {"paren_arabic", "arabic", "arabic_loose", "arabic_bare", "decimal"}:
        return False

    parent_line_no = int(parent.get("lineNumber") or 0) - 1
    if candidate.line_no <= parent_line_no:
        return False
    if candidate.line_no - parent_line_no > 12:
        return False

    numbering_info = _infer_next_root_numbering(roots)
    if numbering_info is None:
        return False
    next_numbering, token_type = numbering_info

    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的规则定义。
    parent_number_value = _parse_ascii_int(parent.get("numbering"))
    next_number_value = _parse_ascii_int(next_numbering)
    if (
        token_type == "arabic"
        and parent_number_value is not None
        and next_number_value is not None
        and (
            (
                next_number_value >= 10
                and next_number_value == parent_number_value + 1
            )
            or (
                parent_number_value >= 10
                and next_number_value >= 10
                and next_number_value <= parent_number_value
            )
        )
    ):
        next_numbering = ""
        token_type = "section_text"

    title_without_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", candidate.raw or ""))
    if not title_without_score:
        return False

    node = {
        "lineNumber": candidate.line_no + 1,
        "level": min(1, max_level),
        "numbering": next_numbering,
        "title": title_without_score,
        "rawText": candidate.raw,
        "blankText": "",
        "score": float(candidate.score),
        "_tokenType": token_type,
        "_isSectionHeading": True,
        "_bindSectionChildren": True,
        "children": [],
    }
    _append_outline_node(roots, stack, node)
    return True


def _find_recent_chinese_paren_parent(stack: List[Dict]) -> Optional[Dict]:
    for node in reversed(stack):
        if str(node.get("_tokenType") or "") != "chinese_paren":
            continue
        return node
    return None


def _is_under_writing_section(stack: List[Dict]) -> bool:
    for node in reversed(stack):
        if int(node.get("level", 1)) != 1:
            continue
        title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        if WRITING_SECTION_TITLE_RE.search(title):
            return True
        return False
    return False


def _is_article_marker_reading_scored_line(text: str) -> bool:
    normalized = normalize_line(text)
    if not normalized:
        return False
    return bool(ARTICLE_MARKER_READING_SCORED_LINE_RE.search(normalized))


def _is_writing_requirement_text(text: str) -> bool:
    normalized = normalize_line(text)
    if not normalized:
        return False
    if WRITING_PROMPT_OPTION_HINT_RE.search(normalized):
        return False
    if re.match(r"^(?:\u4f5c\u6587\u8981\u6c42|\u5199\u4f5c\u8981\u6c42|\u8981\u6c42[:\uff1a]?)", normalized):
        return True
    if WRITING_REQUIREMENT_HINT_RE.search(normalized):
        return True
    return False


def _looks_like_writing_option_prompt(text: str) -> bool:
    normalized = normalize_line(text)
    if not normalized:
        return False
    return bool(WRITING_PROMPT_OPTION_HINT_RE.search(normalized))


def _is_writing_title_placeholder_line(text: str) -> bool:
    normalized = normalize_line(text)
    if not normalized or not _collect_blank_segments(normalized):
        return False
    if not re.search(r"(?:文题|题目|标题)", normalized):
        return False
    stripped = UNDERLINE_RE.sub("", normalized)
    stripped = re.sub(r"(?:文题|题目|标题)", "", stripped)
    stripped = re.sub(r"[\s:：\\-—_]+", "", stripped)
    return stripped == ""


def _should_skip_writing_requirement_heading(
    item: HeadingCandidate,
    stack: List[Dict],
) -> bool:
    if item.token_type not in {"paren_arabic", "circled"}:
        return False
    if item.score is not None and float(item.score) > 0:
        return False
    if not _is_under_writing_section(stack):
        return False

    line = item.raw or ""
    if _collect_blank_segments(line):
        return False
    if EMPTY_BRACKET_RE.search(line):
        return False

    title = normalize_line(item.title or line)
    return _is_writing_requirement_text(title)


def _is_under_reading_root(stack: List[Dict]) -> bool:
    for node in reversed(stack):
        if int(node.get("level", 1)) != 1:
            continue
        title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        if not title:
            return False
        if READING_MATERIAL_PARENT_HINT_RE.search(title) or "\u9605\u8bfb" in title:
            return True
        return False
    return False


def _reset_stack_to_reading_root_on_skipped_chinese_paren_heading(
    item: "HeadingCandidate",
    stack: List[Dict],
) -> None:
    if item.token_type != "chinese_paren":
        return
    if not stack or not _is_under_reading_root(stack):
        return

    line = item.raw or item.title or ""
    title = normalize_line(item.title or line)
    if not title:
        return

    is_scored_reading_partition = bool(
        item.score is not None
        and float(item.score) > 0
        and (
            _is_article_marker_reading_scored_line(line)
            or re.search(r"(?:阅读|完成练习|回答问题)", title)
        )
    )
    if not is_scored_reading_partition:
        return

    while stack and int(stack[-1].get("level", 1)) > 1:
        stack.pop()
    if stack and int(stack[-1].get("level", 1)) == 1:
        stack[-1]["_afterSkippedReadingPartition"] = True


def _is_under_choice_root(stack: List[Dict]) -> bool:
    for node in reversed(stack):
        if int(node.get("level", 1)) != 1:
            continue
        title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        if not title:
            return False
        return _is_choice_root_title(title)
    return False


def _is_choice_stem_empty_bracket_only_heading(raw_text: str) -> bool:
    text = normalize_line(raw_text or "")
    if not text:
        return False
    if UNDERLINE_RE.search(text):
        return False
    empty_bracket = re.search(r"[（(]\s*[）)]", text)
    if empty_bracket is None:
        return False
    # 选择题题干中“( )”通常为作答占位，若后缀仅剩分值/标点则抑制空位提取。
    tail = text[empty_bracket.end() :].strip()
    if tail and not re.fullmatch(
        r"[（(]\s*(?:共|总计|总分)?\s*\d+(?:\.\d+)?\s*分\s*[）)]\s*[。．\.,，;；:：!?？！]?",
        tail,
    ):
        return False
    return bool(
        re.search(
            r"(?:一项|一组|最恰当|正确|不正确|符合|不符合|有误|有语病|的是|选择)",
            text,
        )
    )


def _is_choice_question_heading_text(text: str) -> bool:
    normalized = normalize_line(text or "")
    if not normalized:
        return False
    return bool(
        re.search(
            r"(?:选项|单项选择|多项选择|一项|最恰当|正确的一项|不正确的一项|符合题意|不符合题意|有语病)",
            normalized,
        )
    )


def _has_following_choice_option_lines(lines: List[str], start_line_no: int, lookahead: int = 8) -> bool:
    if not lines:
        return False
    option_hits = 0
    upper = min(len(lines), start_line_no + max(1, lookahead) + 1)
    for idx in range(start_line_no + 1, upper):
        line = normalize_line(lines[idx] if idx < len(lines) else "")
        if not line:
            continue
        if OPTION_PREFIX_RE.match(line):
            option_hits += 1
            if option_hits >= 2:
                return True
            continue
        if re.match(r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]", line):
            # 选择题题干后可先出现“(1)(2)(3)”分句，不应提前终止选项探测。
            continue
        if re.match(
            rf"^\s*(?:\d{{1,4}}\s*[\u3001\.\uFF0E]|{CHINESE_NUM_RE}[\u3001\.\uFF0E]|{CIRCLED_MARKER_CLASS})",
            line,
        ):
            break
    return False


def _has_arabic_question_children(node: Dict) -> bool:
    for child in node.get("children", []):
        token_type = str(child.get("_tokenType") or "")
        if token_type in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
            return True
        if _parse_ascii_int(child.get("numbering")) is not None and token_type != "paren_arabic":
            return True
    return False


def _has_dense_paren_subquestions(node: Dict) -> bool:
    children = node.get("children", []) or []
    if len(children) < 3:
        return False
    paren_children = [
        child
        for child in children
        if str(child.get("_tokenType") or "") == "paren_arabic"
        and not child.get("children")
    ]
    if len(paren_children) < 3:
        return False
    return len(paren_children) >= max(3, len(children) - 1)


def _should_skip_circled_material_heading(
    item: HeadingCandidate,
    stack: List[Dict],
) -> bool:
    if item.token_type != "circled":
        return False
    if item.score is not None and float(item.score) > 0:
        return False

    line = item.raw or ""
    title = normalize_line(item.title or line)
    has_slot_marker = bool(_collect_blank_segments(line) or EMPTY_BRACKET_RE.search(line))
    if has_slot_marker:
        # 阅读材料正文中的圈号段落即便出现下划线，也不作为题目提取。
        if (
            _is_under_reading_root(stack)
            and _is_material_paragraph_like_text(title)
            and not QUESTION_DIRECTIVE_HINT_RE.search(title)
            and not re.search(r"[\uFF1F?]", title)
        ):
            return True
        return False

    direct_parent = stack[-1] if stack else None
    if direct_parent is not None:
        parent_type = str(direct_parent.get("_tokenType") or "")
        parent_level = int(direct_parent.get("level", 1))
        parent_text = normalize_line(str(direct_parent.get("title") or direct_parent.get("rawText") or ""))
        keep_fill_blank_circled = bool(
            re.search(
                r"(?:默写|补写|填空|名句|古诗文|按要求|积累|运用|词句|句子|仿写|改写)",
                parent_text,
            )
        )
        # 圈号出现在数字题号下时默认属于同一题干内容，不额外提取层级。
        if (
            parent_type in {"arabic", "arabic_loose", "arabic_bare", "paren_arabic", "decimal"}
            and parent_level >= 2
            and (item.score is None or float(item.score) <= 0)
            and not QUESTION_SECTION_TITLE_RE.search(title)
        ):
            if keep_fill_blank_circled:
                return False
            return True
        # ①②等出现在“1./(1)”题干内时，通常是行内说明序号，不作为新层级提取。
        if parent_type in {"arabic", "arabic_loose", "arabic_bare", "paren_arabic", "decimal"} and parent_level >= 3:
            if (
                title
                and not QUESTION_DIRECTIVE_HINT_RE.search(title)
                and not re.search(r"[？?]", title)
                and not QUESTION_SECTION_TITLE_RE.search(title)
            ):
                if keep_fill_blank_circled:
                    return False
                return True

    parent = _find_recent_chinese_paren_parent(stack)
    if parent is None:
        direct_parent = stack[-1] if stack else None
        if direct_parent is None:
            return False
        if int(direct_parent.get("level", 1)) != 1:
            return False
        if not _is_under_reading_root(stack):
            return False
        parent = direct_parent
    if _has_arabic_question_children(parent):
        return False
    if not _is_under_reading_root(stack):
        return False

    title = normalize_line(item.title or line)
    if not title:
        return True
    # 规则说明：题号与层级识别（示例：[？?]）的条件过滤。
    if QUESTION_DIRECTIVE_PREFIX_RE.match(title):
        return False
    # 规则说明：阅读/作文内容防误提（示例：[？?]）的逻辑约束。
    # 规则说明：阅读/作文内容防误提（示例：[？?]）的条件过滤。
    if re.search(r"[？?]", title):
        return True
    return _is_material_paragraph_like_text(title) or len(title) >= 4


def _should_skip_chinese_paren_reading_heading(
    item: HeadingCandidate,
    stack: List[Dict],
) -> bool:
    if item.token_type != "chinese_paren":
        return False

    line = item.raw or ""
    if _collect_blank_segments(line):
        return False
    if EMPTY_BRACKET_RE.search(line):
        return False

    title = normalize_line(item.title or line)
    if not title:
        return False

    if re.match(r"^(?:阅读|阅读下面|阅读下列|阅读以下|材料[一二三四五六七八九十甲乙丙丁])", title):
        # 阅读大题下带分值或明确题目范围的“（一）（二）...”通常是有效分块，不应在入口直接忽略。
        if _is_under_reading_root(stack) and (
            (item.score is not None and float(item.score) > 0)
            or _extract_question_range_from_text(title) is not None
        ):
            return False
        return True

    parent = stack[-1] if stack else None
    parent_token = str(parent.get("_tokenType") or "") if parent else ""
    if item.score is not None and float(item.score) > 0:
        if _is_under_reading_root(stack):
            if _is_article_marker_reading_scored_line(line):
                return True
            # 阅读大题中的“（一）课内文言文/（二）课外文言文”等分块标题应保留为结构层级。
            if re.search(
                r"(?:\u8bfe\u5185|\u8bfe\u5916|\u6587\u8a00\u6587|\u73b0\u4ee3\u6587|\u540d\u8457|\u53e4\u8bd7\u6587|\u8bd7\u6b4c|\u7efc\u5408\u6027\u5b66\u4e60|\u7efc\u5408\u5b9e\u8df5|\u5199\u4f5c|\u4f5c\u6587)",
                title,
            ):
                return False
            # 带分值且标题较短的“（一）/（二）”通常是阅读分组，先保留，后续再由扁平化规则判定是否展开。
            if not _is_material_paragraph_like_text(title):
                return False
            # 阅读大题中的“（一）（二）（三）+篇章标题（含分值）”一般是材料分块，不作为题目节点。
            has_slot_marker = bool(_collect_blank_segments(line) or EMPTY_BRACKET_RE.search(line))
            has_question_semantic = bool(
                QUESTION_DIRECTIVE_HINT_RE.search(title)
                or QUESTION_SECTION_TITLE_RE.search(title)
                or _extract_question_range_from_text(title) is not None
                or re.search(r"[\uFF1F?]", title)
            )
            if not has_slot_marker and not has_question_semantic:
                return True
            if (
                _is_material_paragraph_like_text(title)
                and not QUESTION_DIRECTIVE_HINT_RE.search(title)
                and not re.search(r"[\uFF1F?]", title)
            ):
                return True
        return False
    if parent_token in {"arabic", "arabic_loose", "arabic_bare", "decimal", "paren_arabic"}:
        parent_text = normalize_line(str(parent.get("title") or parent.get("rawText") or ""))
        is_range_prompt_heading = _extract_question_range_from_text(title) is not None
        if (
            parent_text
            and re.search(r"(?:\u9605\u8bfb|\u6587\u7ae0|\u77ed\u6587|\u6587\u6bb5|\u6750\u6599|\u4f5c\u6587)", parent_text)
            and not QUESTION_DIRECTIVE_HINT_RE.search(title)
            and not QUESTION_SECTION_TITLE_RE.search(title)
            and not READING_KEEP_CHINESE_TITLE_RE.search(title)
            and not is_range_prompt_heading
        ):
            return True
        # 题号正文内的“（一）阅读……”或长材料段落仍跳过；
        # 但像“（二）某篇目标题”这种短标题需要保留，作为新子节承接后续重排题号。
        if (READING_PAREN_HEADING_SKIP_RE.search(title) or READING_MATERIAL_PARENT_HINT_RE.search(title)) and not is_range_prompt_heading:
            return True
        if _is_material_paragraph_like_text(title):
            return True
        return False
    if not (READING_PAREN_HEADING_SKIP_RE.search(title) or READING_MATERIAL_PARENT_HINT_RE.search(title)):
        return False
    if _is_under_reading_root(stack):
        # 阅读大题下“（一）阅读下面……回答x-x题”通常是有效层级，保留。
        if READING_MATERIAL_PARENT_HINT_RE.search(title) or _extract_question_range_from_text(title) is not None:
            return False
        return _is_material_paragraph_like_text(title)
    if "\u9605\u8bfb" in title and _is_material_paragraph_like_text(title):
        return True
    return False


def _is_pure_empty_bracket_line(line: str) -> bool:
    text = str(line or "")
    if not text:
        return False
    if not EMPTY_BRACKET_RE.search(text):
        return False
    probe = EMPTY_BRACKET_RE.sub("", text)
    probe = re.sub(r"[\s\u3000]", "", probe)
    return probe == ""


def _rebalance_merged_blank_segments(segments: List[str], total_score: float) -> List[str]:
    if not segments:
        return segments
    total = float(total_score)
    if total <= 0:
        return segments
    count = len(segments)
    base = round(total / count, 2)
    assigned = [base for _ in range(count)]
    diff = round(total - base * count, 2)
    assigned[-1] = round(assigned[-1] + diff, 2)

    result: List[str] = []
    for idx, token in enumerate(segments):
        token_text = str(token or "").strip()
        match = MERGED_BLANK_TOKEN_RE.match(token_text)
        underline = match.group(1) if match else "____"
        result.append(f"{underline}{_format_score_text(assigned[idx])}")
    return result


def _parse_merged_blank_segment_score(token: str) -> Optional[float]:
    text = str(token or "").strip()
    if not text:
        return None
    match = re.search(r"[\uFF08(]\s*(\d+(?:\.\d+)?)\s*\u5206\s*[\uFF09)]", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return None


def _all_merged_blank_segments_zero(segments: List[str]) -> bool:
    if not segments:
        return False
    scores: List[float] = []
    for token in segments:
        score = _parse_merged_blank_segment_score(token)
        if score is None:
            return False
        scores.append(float(score))
    return bool(scores) and all(value <= 0 for value in scores)


def _is_material_paragraph_like_text(text: str) -> bool:
    normalized = normalize_line(text)
    if not normalized:
        return False
    if QUESTION_DIRECTIVE_PREFIX_RE.match(normalized):
        return False
    punct_count = len(re.findall(r"[，,。！？?；;：:]", normalized))
    sentence_count = len(re.findall(r"[。！？?；;]", normalized))
    if len(normalized) >= 24 and punct_count >= 2 and sentence_count >= 1:
        return True
    if len(normalized) >= 38 and punct_count >= 3:
        return True
    return False


def _is_interleaved_choice_answer_key_line(line: str) -> bool:
    normalized = normalize_line(line)
    if not normalized:
        return False
    if re.search(r"[\u4e00-\u9fa5]", normalized):
        return False
    pairs = list(INTERLEAVED_CHOICE_ANSWER_PAIR_RE.finditer(normalized))
    if len(pairs) < 3:
        return False
    if pairs[0].start() > 2:
        return False
    stripped = INTERLEAVED_CHOICE_ANSWER_PAIR_RE.sub(" ", normalized)
    stripped = re.sub(r"[\s,，;；:：/\-—_（）()\[\]【】\.\uFF0E、]+", "", stripped)
    return stripped == ""


def _collect_answer_card_index_line_nos(lines: List[str], min_run: int = 5) -> Set[int]:
    marked: Set[int] = set()
    run: List[Tuple[int, int]] = []

    def flush() -> None:
        nonlocal run
        if len(run) < min_run:
            run = []
            return
        start_number = run[0][1]
        if start_number != 1:
            run = []
            return
        for idx, _ in run:
            marked.add(idx)
        run = []

    for idx, line in enumerate(lines):
        normalized = normalize_line(line)
        match = PURE_ARABIC_INDEX_LINE_RE.fullmatch(normalized)
        if match is None:
            flush()
            continue
        number_value = _parse_ascii_int(match.group(1))
        if number_value is None:
            flush()
            continue
        if not run:
            run = [(idx, number_value)]
            continue
        prev_idx, prev_number = run[-1]
        if idx == prev_idx + 1 and number_value == prev_number + 1:
            run.append((idx, number_value))
            continue
        flush()
        run = [(idx, number_value)]
    flush()
    return marked


def _should_skip_interleaved_choice_answer_heading(item: HeadingCandidate, stack: List[Dict]) -> bool:
    if item.token_type not in {"arabic", "arabic_loose", "arabic_bare"}:
        return False
    # Cloze/补全对话中的“85. A”属于题号，不按答案键过滤。
    if _is_under_cloze_section(stack):
        return False
    raw = item.raw or ""
    if SINGLE_CHOICE_ANSWER_KEY_LINE_RE.fullmatch(normalize_line(raw)):
        return True
    return _is_interleaved_choice_answer_key_line(raw)


def _should_skip_numeric_option_stub_heading(item: HeadingCandidate, stack: List[Dict]) -> bool:
    if item.token_type not in {"arabic", "arabic_loose", "arabic_bare"}:
        return False
    if item.score is not None and float(item.score) > 0:
        return False
    raw = normalize_line(item.raw or "")
    if not raw:
        return False
    # 单行“1.A.... / 1. A....”本质是选项片段，不应作为题号节点。
    if NUMERIC_SINGLE_OPTION_STUB_RE.match(raw):
        return True
    if not NUMERIC_OPTION_STUB_HEADING_RE.match(raw):
        return False
    return True


def _try_merge_circled_continuation_into_empty_paren_heading(
    stack: List[Dict],
    item: HeadingCandidate,
) -> bool:
    if item.token_type != "circled":
        return False
    if not stack:
        return False
    parent = stack[-1]
    if str(parent.get("_tokenType") or "") != "paren_arabic":
        return False
    if parent.get("children"):
        return False
    if item.score is not None and float(item.score) > 0:
        return False

    parent_title = normalize_line(str(parent.get("title") or ""))
    allow_merge = (not parent_title) or bool(parent.get("_mergeCircledContinuation"))
    if not allow_merge:
        return False

    item_raw = normalize_line(item.raw or "")
    item_title = normalize_line(item.title or "")
    if not item_raw and not item_title:
        return False
    # 带空位的圈号行默认保留为子题；若明显是长句续写（空“(2)”后的正文），允许并入。
    if _collect_blank_segments(item_raw) or EMPTY_BRACKET_RE.search(item_raw):
        body = normalize_line(re.sub(rf"^\s*{CIRCLED_MARKER_CLASS}\s*", "", item_raw))
        cjk_count = len(re.findall(r"[\u4e00-\u9fa5]", body))
        punct_count = len(re.findall(r"[，,。！？?；;：:]", body))
        if cjk_count < 8 and punct_count == 0:
            return False

    merged_title = f"{parent_title}{item_title}" if item_title else parent_title
    merged_raw = f"{normalize_line(str(parent.get('rawText') or ''))}{item_raw}" if item_raw else normalize_line(
        str(parent.get("rawText") or "")
    )
    parent["title"] = merged_title
    parent["rawText"] = merged_raw
    parent["_mergeCircledContinuation"] = True
    return True


def _should_skip_paren_arabic_material_heading(
    item: HeadingCandidate,
    stack: List[Dict],
) -> bool:
    if item.token_type != "paren_arabic":
        return False
    if item.score is not None and float(item.score) > 0:
        return False
    line = item.raw or ""
    if _collect_blank_segments(line):
        return False
    if EMPTY_BRACKET_RE.search(line):
        return False

    title = normalize_line(item.title or line)

    if item.number_value is not None and item.number_value >= 10:
        direct_parent = stack[-1] if stack else None
        if direct_parent is not None and str(direct_parent.get("_tokenType") or "") in {
            "arabic",
            "arabic_loose",
            "arabic_bare",
            "decimal",
            "paren_arabic",
        }:
            if (
                _is_material_paragraph_like_text(title)
            ):
                return True

    # 阅读大题正文中的“(2)(3)...”段落标号（长叙述句）不作为题目结构提取。
    if _is_under_reading_root(stack):
        if _is_material_paragraph_like_text(title) and not QUESTION_DIRECTIVE_HINT_RE.search(title):
            return True
        punct_count = len(re.findall(r"[，,。；;：:]", title))
        if (
            len(title) >= 12
            and punct_count >= 1
            and not QUESTION_DIRECTIVE_HINT_RE.search(title)
            and not re.search(r"(?:回答|完成)\s*\d{1,3}\s*[-~\uFF5E\u2013\u2014\u2015\u2212至到]\s*\d{1,3}\s*题", title)
        ):
            return True

    parent = _find_recent_chinese_paren_parent(stack)
    if parent is None:
        return False
    if _has_arabic_question_children(parent):
        return False
    if bool(parent.get("_materialParenDetected")):
        return True
    return _is_material_paragraph_like_text(title)


def _mark_material_paren_skip(
    item: HeadingCandidate,
    stack: List[Dict],
) -> None:
    parent = _find_recent_chinese_paren_parent(stack)
    if parent is None:
        return
    parent["_materialParenDetected"] = True
    if item.number_value is not None:
        parent["_materialParenLast"] = int(item.number_value)


def _should_skip_chinese_material_heading(
    item: HeadingCandidate,
    stack: List[Dict],
    score_patterns: List[re.Pattern],
) -> bool:
    if item.token_type not in {"chinese", "chinese_loose"}:
        return False
    # 带有明确分数的中文编号 heading 应该始终保留为独立的部分
    # 例如"二、（9分）阅读下面文章"这种情况不应该被跳过
    if item.score is not None and float(item.score) > 0:
        return False

    line = item.raw or ""
    if _collect_blank_segments(line):
        return False
    if EMPTY_BRACKET_RE.search(line):
        return False

    parent = _find_recent_chinese_paren_parent(stack)
    if parent is None:
        return False
    if _has_arabic_question_children(parent):
        return False

    title = normalize_line(item.title or "")
    if READING_MATERIAL_PARENT_HINT_RE.search(title):
        return False
    if READING_KEEP_CHINESE_TITLE_RE.search(title):
        return False
    if _is_material_paragraph_like_text(title):
        return True
    # 规则说明：阅读/作文内容防误提的逻辑约束。
    # 规则说明：题号与层级识别的返回策略。
    return bool(title) and len(title) >= 6


def _should_skip_paren_range_marker(
    item: HeadingCandidate,
    stack: List[Dict],
) -> bool:
    if item.token_type != "paren_arabic":
        return False
    if not stack:
        return False

    parent = stack[-1]
    parent_type = str(parent.get("_tokenType") or "")
    if parent_type not in {"arabic", "arabic_loose", "arabic_bare", "decimal", "chinese_paren"}:
        return False

    parent_line_no = int(parent.get("lineNumber") or 0) - 1
    if parent_line_no < 0:
        return False
    if item.line_no <= parent_line_no or item.line_no - parent_line_no > 3:
        return False

    parent_text = normalize_line(str(parent.get("rawText") or parent.get("title") or ""))
    if not RANGE_MARKER_PARENT_HINT_RE.search(parent_text):
        return False

    title = normalize_line(item.title or "")
    if not title:
        return False

    title_wo_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", title))
    if not title_wo_score:
        return False

    return bool(RANGE_MARKER_ONLY_RE.fullmatch(title_wo_score))


def _is_range_prompt_only_line(text: str) -> bool:
    normalized = normalize_line(str(text or ""))
    if not normalized:
        return False
    if not RANGE_QUESTION_PROMPT_RE.search(normalized):
        return False

    without_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", normalized))
    without_leading_numbering = re.sub(
        rf"^\s*(?:{CHINESE_NUM_RE}\s*[\u3001\.\uFF0E]|\d{{1,4}}\s*[\u3001\.\uFF0E]|[\uFF08(]\s*\d{{1,3}}\s*[\uFF09)])\s*",
        "",
        without_score,
    )
    reduced = RANGE_QUESTION_PROMPT_RE.sub("", without_leading_numbering)
    reduced = re.sub(
        r"(?:阅读|读|根据|结合|下文|下面|材料|古诗|诗歌|短文|文章|文段|《[^》]{1,40}》|[,，:：。．\s])",
        "",
        reduced,
    )
    return reduced == ""


def _is_cloze_like_section_title(title: str) -> bool:
    normalized = normalize_line(title)
    if not normalized:
        return False
    return bool(
        re.search(
            r"(?:\u5b8c\u5f62\u586b\u7a7a|\u7f3a\u8bcd\u586b\u7a7a|\u9996\u5b57\u6bcd\u586b\u7a7a|\u77ed\u6587\u586b\u7a7a|"
            r"\u8865\u5168\u5bf9\u8bdd|\u8fd8\u539f|\u9009\u53e5\u586b\u7a7a|cloze)",
            normalized,
            flags=re.IGNORECASE,
        )
    )


def _is_under_cloze_section(stack: List[Dict]) -> bool:
    for node in reversed(stack):
        if int(node.get("level", 1)) != 1:
            continue
        title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        if _is_cloze_like_section_title(title):
            return True
        return False
    return False


def _should_attach_indexed_markers_to_non_cloze_section(parent: Dict, candidate_numbers: List[int]) -> bool:
    if not candidate_numbers:
        return False

    children = parent.get("children", [])
    existing_numbers = sorted(
        {
            number_value
            for child in children
            for number_value in [_parse_ascii_int(child.get("numbering"))]
            if number_value is not None
        }
    )
    if not existing_numbers:
        return False

    unique_candidates = sorted(set(candidate_numbers))
    if any((right - left) != 1 for left, right in zip(unique_candidates, unique_candidates[1:])):
        return False

    min_existing, max_existing = existing_numbers[0], existing_numbers[-1]
    # 规则说明：识别规则处理的逻辑约束。
    # 规则说明：识别规则处理的条件过滤。
    if unique_candidates[0] == max_existing + 1 and unique_candidates[-1] <= max_existing + 15:
        return True
    if unique_candidates[-1] == min_existing - 1 and unique_candidates[0] >= min_existing - 15:
        return True

    missing_inside_existing = [n for n in unique_candidates if min_existing <= n <= max_existing and n not in existing_numbers]
    if missing_inside_existing and len(missing_inside_existing) == len(unique_candidates):
        return True
    return False


def _append_missing_indexed_blank_marker_nodes(
    roots: List[Dict],
    indexed_candidates: List[IndexedBlankMarkerCandidate],
    max_level: int,
) -> None:
    if not roots or not indexed_candidates:
        return

    level1_nodes = [node for node in roots if int(node.get("level", 1)) == 1]
    if not level1_nodes:
        return
    level1_nodes.sort(key=lambda node: int(node.get("lineNumber") or 0))

    for candidate in indexed_candidates:
        target_parent: Optional[Dict] = None
        for idx, parent in enumerate(level1_nodes):
            parent_start = int(parent.get("lineNumber") or 0)
            parent_end = (
                int(level1_nodes[idx + 1].get("lineNumber") or 10**9)
                if idx + 1 < len(level1_nodes)
                else 10**9
            )
            candidate_line = candidate.line_no + 1
            if parent_start <= candidate_line < parent_end:
                target_parent = parent
                break
        if target_parent is None:
            continue
        if not _is_cloze_like_section_title(str(target_parent.get("title") or "")) and not (
            _should_attach_indexed_markers_to_non_cloze_section(target_parent, candidate.numbers)
        ):
            continue

        children = target_parent.get("children", [])
        existing_numbers = {
            number_value
            for child in children
            for number_value in [_parse_ascii_int(child.get("numbering"))]
            if number_value is not None
        }
        added = False
        for number in candidate.numbers:
            if number in existing_numbers:
                continue
            children.append(
                {
                    "lineNumber": candidate.line_no + 1,
                    "level": min(int(target_parent.get("level", 1)) + 1, max_level),
                    "numbering": str(number),
                    "title": "",
                    # 规则说明：分数提取与分配的逻辑约束。
                    # 规则说明：分数提取与分配的逻辑约束。
                    # 规则说明：分数提取与分配的逻辑约束。
                    "rawText": "",
                    "blankText": "",
                    "score": None,
                    "_tokenType": "indexed_blank_marker",
                    "children": [],
                }
            )
            existing_numbers.add(number)
            added = True
        if added:
            numeric_children = [
                child
                for child in children
                if _parse_ascii_int(child.get("numbering")) is not None
            ]
            other_children = [
                child
                for child in children
                if _parse_ascii_int(child.get("numbering")) is None
            ]
            numeric_children.sort(
                key=lambda child: _parse_ascii_int(child.get("numbering")) or 0
            )
            target_parent["children"] = numeric_children + other_children


def _is_number_only_placeholder_node(node: Dict) -> bool:
    if not isinstance(node, dict):
        return False
    if node.get("children"):
        return False
    numbering = str(node.get("numbering") or "").strip()
    if not numbering:
        return False
    title = str(node.get("title") or "").strip()
    raw_text = str(node.get("rawText") or "").strip()
    blank_text = str(node.get("blankText") or "").strip()
    if blank_text:
        return False
    number_only_re = re.compile(
        r"^(?:\d{1,4}\s*[\u3001\.\uFF0E]?|[\uFF08(]\s*\d{1,3}\s*[\uFF09)]\s*[\u3001\.\uFF0E]?)$"
    )
    if title:
        if not number_only_re.fullmatch(normalize_line(title)):
            return False
    if raw_text:
        if not number_only_re.fullmatch(normalize_line(raw_text)):
            return False
    score = node.get("score")
    if score is not None and float(score or 0) > 0:
        return False
    return True


def _prune_number_only_placeholder_nodes(nodes: List[Dict]) -> None:
    if not nodes:
        return
    filtered_roots: List[Dict] = []
    for node in nodes:
        if _is_number_only_placeholder_node(node):
            continue
        children = node.get("children", [])
        if children:
            node["children"] = [child for child in children if not _is_number_only_placeholder_node(child)]
            _prune_number_only_placeholder_nodes(node.get("children", []))
        filtered_roots.append(node)
    nodes[:] = filtered_roots


def _has_meaningful_non_slot_text(text: str) -> bool:
    probe = normalize_line(text or "")
    if not probe:
        return False
    probe = PAREN_SCORE_ONLY_RE.sub("", probe)
    probe = UNDERLINE_RE.sub("", probe)
    probe = EMPTY_BRACKET_RE.sub("", probe)
    probe = re.sub(r"[\s\u3000,，。\.；;:：!?？！\-_（）()【】\[\]、]+", "", probe)
    return bool(re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", probe))


def _is_labeled_activity_or_material_line(text: str) -> bool:
    normalized = normalize_line(text or "")
    if not normalized:
        return False
    if re.match(r"^\s*【[^】]{1,40}】", normalized):
        return True
    if INLINE_ACTIVITY_MATERIAL_HEADING_RE.search(normalized):
        return True
    if re.match(r"^\s*(?:活动|任务|材料|板块|栏目)[一二三四五六七八九十甲乙丙丁\d]+[:：]", normalized):
        return True
    return False


def _is_matching_question_heading_text(text: str) -> bool:
    normalized = normalize_line(text or "")
    if not normalized:
        return False
    return bool(
        re.search(
            r"(?:连一连|正确连接|进行正确连接|对应连接|连线|配对|搭配)",
            normalized,
        )
    )


def _merge_empty_numbering_leaf_nodes(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", [])
        if not children:
            continue

        _merge_empty_numbering_leaf_nodes(children)

        node_text = normalize_line(str(node.get("rawText") or node.get("title") or ""))
        if _is_matching_question_heading_text(node_text):
            continue

        def _has_real_blank_slot(target: Dict) -> bool:
            raw_text = str(target.get("rawText") or "")
            title_text = str(target.get("title") or "")
            blank_text = str(target.get("blankText") or "")
            source = " ".join(part for part in [raw_text, title_text, blank_text] if part).strip()
            if not source:
                return False
            if _collect_blank_segments(source):
                return True
            return bool(EMPTY_BRACKET_RE.search(source))

        def _find_next_number_value(start_index: int) -> Optional[int]:
            for future in children[start_index + 1 :]:
                value = _parse_ascii_int(future.get("numbering"))
                if value is not None:
                    return value
            return None

        merged_children: List[Dict] = []
        for idx, child in enumerate(children):
            child_children = child.get("children", [])
            child_numbering = str(child.get("numbering") or "").strip()
            if child_numbering or child_children:
                merged_children.append(child)
                continue

            child_raw = normalize_line(str(child.get("rawText") or ""))
            child_title = normalize_line(str(child.get("title") or ""))
            child_text = child_raw or child_title
            child_score = child.get("score")
            # 无编号但文本前缀像“(1)/(2)/①/⑴”时，视为真实子问，不能并入上一题。
            if child_text and re.match(
                r"^\s*(?:"
                r"[\uFF08(]\s*(?:\d{1,3}|[一二三四五六七八九十]{1,3})\s*[\uFF09)]"
                r"|[\u2460-\u2473\u3251-\u325F\u32B1-\u32BF]"
                r"|[\u2474-\u2487]"
                r")",
                child_text,
            ):
                merged_children.append(child)
                continue
            # “活动二：/材料二：”等说明标题不并入上一题，避免题干分值被错误累加。
            if child_text and INLINE_ACTIVITY_MATERIAL_HEADING_RE.search(child_text):
                merged_children.append(child)
                continue
            # 长材料/叙述段落不并入上一题，后续由材料过滤规则处理。
            if child_text and _is_material_paragraph_like_text(child_text):
                merged_children.append(child)
                continue

            # 具备真实空位的无编号叶子要保留，避免把多行填空误并成一个节点。
            if _has_real_blank_slot(child):
                merged_children.append(child)
                continue
            # 有显式分值且是问句/指令句的无编号追问要保留，避免误并到上一小题。
            if (
                child_score is not None
                and float(child_score or 0) > 0
                and (
                    bool(re.search(r"[？?]", child_text))
                    or bool(QUESTION_DIRECTIVE_HINT_RE.search(child_text))
                )
            ):
                prev_number_value = (
                    _parse_ascii_int(merged_children[-1].get("numbering")) if merged_children else None
                )
                next_number_value = _find_next_number_value(idx)
                between_sequential_numbering = bool(
                    prev_number_value is not None
                    and next_number_value is not None
                    and next_number_value == prev_number_value + 1
                )
                if not between_sequential_numbering:
                    merged_children.append(child)
                    continue

            if not merged_children:
                merged_children.append(child)
                continue

            target = merged_children[-1]
            target_raw_probe = normalize_line(str(target.get("rawText") or target.get("title") or ""))
            target_has_explicit_score_marker = bool(PAREN_SCORE_ONLY_RE.search(target_raw_probe))

            if child_score is not None and float(child_score) > 0:
                skip_score_accumulation = (
                    float(target.get("score") or 0) > 0
                    and _is_labeled_activity_or_material_line(child_text)
                )
                # 父级题干已给总分时，续行中的“(1分)/(2分)”常是题内标注，不应继续叠加到父级总分。
                if (
                    float(target.get("score") or 0) > 0
                    and target_has_explicit_score_marker
                    and not _has_real_blank_slot(child)
                ):
                    skip_score_accumulation = True
                target_score = target.get("score")
                if not skip_score_accumulation:
                    if target_score is None or float(target_score) <= 0:
                        target["score"] = float(child_score)
                    else:
                        target["score"] = _normalize_score_value(float(target_score) + float(child_score))

            child_blank = str(child.get("blankText") or "").strip()
            if not child_blank:
                child_blank = _format_blank_segments_from_line(
                    str(child.get("rawText") or ""),
                    float(child.get("score") or 0.0),
                )
            if child_blank:
                target_blank = str(target.get("blankText") or "").strip()
                target["blankText"] = f"{target_blank} {child_blank}".strip() if target_blank else child_blank

            if child_text and _has_meaningful_non_slot_text(child_text):
                target_title = normalize_line(str(target.get("title") or ""))
                target_raw = normalize_line(str(target.get("rawText") or ""))
                if child_text not in target_title:
                    target["title"] = normalize_line(f"{target_title} {child_text}" if target_title else child_text)
                if child_text not in target_raw:
                    target["rawText"] = normalize_line(f"{target_raw} {child_text}" if target_raw else child_text)

        node["children"] = merged_children

        # 当父节点下仅存在无编号追问时，视为同一小问的续行，直接并回父节点，避免出现空编号子结构。
        if not node["children"]:
            continue
        has_numbered_child = any(str(child.get("numbering") or "").strip() for child in node["children"])
        if has_numbered_child:
            continue
        node_token_type = str(node.get("_tokenType") or "")
        if node_token_type not in {"paren_arabic", "arabic", "arabic_loose", "arabic_bare", "decimal", "circled"}:
            continue
        if any((child.get("children") or []) for child in node["children"]):
            continue

        parent_blank = str(node.get("blankText") or "").strip()
        parent_title = normalize_line(str(node.get("title") or ""))
        parent_raw = normalize_line(str(node.get("rawText") or ""))
        parent_score = float(node.get("score") or 0.0)
        parent_has_explicit_score_marker = bool(PAREN_SCORE_ONLY_RE.search(parent_raw or parent_title))
        parent_is_writing_prompt = _looks_like_writing_option_prompt(parent_raw or parent_title)
        extra_score = 0.0

        for child in node["children"]:
            child_score = float(child.get("score") or 0.0)
            child_text = normalize_line(str(child.get("rawText") or child.get("title") or ""))
            child_has_real_blank = _has_real_blank_slot(child)

            # 作文题干下无编号、无分值的“文题横线/书写横线”只是版式提示，不作为真实空位并入。
            if parent_is_writing_prompt and child_score <= 0 and child_has_real_blank:
                continue

            skip_score_accumulation = (
                parent_score > 0
                and child_score > 0
                and _is_labeled_activity_or_material_line(child_text)
            )
            if parent_score > 0 and child_score > 0 and parent_has_explicit_score_marker and not _has_real_blank_slot(child):
                skip_score_accumulation = True
            if child_score > 0 and not skip_score_accumulation:
                extra_score = round(extra_score + child_score, 2)

            child_blank = str(child.get("blankText") or "").strip()
            if not child_blank:
                child_blank = _format_blank_segments_from_line(
                    str(child.get("rawText") or ""),
                    float(child.get("score") or 0.0),
                )
            if child_blank:
                parent_blank = f"{parent_blank} {child_blank}".strip() if parent_blank else child_blank

            child_is_pure_continuation = bool(
                child_text
                and _has_meaningful_non_slot_text(child_text)
                and not child_blank
                and child_score <= 0
                and not child_has_real_blank
                and not EMPTY_BRACKET_RE.search(child_text)
                and not _is_material_paragraph_like_text(child_text)
                and not re.match(
                    r"^\s*(?:"
                    r"[\uFF08(]\s*(?:\d{1,3}|[一二三四五六七八九十]{1,3})\s*[\uFF09)]"
                    r"|[\u2460-\u2473\u3251-\u325F\u32B1-\u32BF]"
                    r"|[\u2474-\u2487]"
                    r")",
                    child_text,
                )
            )
            if child_is_pure_continuation:
                if child_text not in parent_title:
                    parent_title = normalize_line(f"{parent_title} {child_text}" if parent_title else child_text)
                if child_text not in parent_raw:
                    parent_raw = normalize_line(f"{parent_raw} {child_text}" if parent_raw else child_text)

        if extra_score > 0:
            node["score"] = (
                _normalize_score_value(parent_score + extra_score)
                if parent_score > 0
                else _normalize_score_value(extra_score)
            )
        if parent_blank:
            node["blankText"] = parent_blank
        if parent_title:
            node["title"] = parent_title
        if parent_raw:
            node["rawText"] = parent_raw


def _is_empty_leaf_placeholder_node(node: Dict) -> bool:
    if not isinstance(node, dict):
        return False
    if node.get("children"):
        return False
    numbering = str(node.get("numbering") or "").strip()
    title = str(node.get("title") or "").strip()
    raw_text = str(node.get("rawText") or "").strip()
    blank_text = str(node.get("blankText") or "").strip()
    if numbering or title or raw_text or blank_text:
        return False
    score = node.get("score")
    if score is not None and float(score or 0) > 0:
        return False
    return True


def _prune_empty_leaf_placeholder_nodes(nodes: List[Dict]) -> None:
    if not nodes:
        return
    kept: List[Dict] = []
    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _prune_empty_leaf_placeholder_nodes(children)
            node["children"] = [child for child in children if not _is_empty_leaf_placeholder_node(child)]
        if _is_empty_leaf_placeholder_node(node):
            continue
        kept.append(node)
    nodes[:] = kept


def _prune_unnumbered_material_children(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if not children:
            continue
        _prune_unnumbered_material_children(children)

        has_numbered_sibling = any(str(child.get("numbering") or "").strip() for child in children)
        if not has_numbered_sibling:
            continue

        filtered_children: List[Dict] = []
        for child in children:
            numbering = str(child.get("numbering") or "").strip()
            if numbering:
                filtered_children.append(child)
                continue
            if child.get("children"):
                filtered_children.append(child)
                continue

            raw_text = normalize_line(str(child.get("rawText") or child.get("title") or ""))
            if not raw_text:
                continue
            if re.match(r"^\s*【[^】]{1,24}】", raw_text):
                # 方头括号内多为“模块说明/任务标签”，不作为题号结构节点。
                continue
            if INLINE_ACTIVITY_MATERIAL_HEADING_RE.search(raw_text):
                # “活动/任务/材料”说明标题不作为题目结构节点。
                continue
            if _has_slot_marker(child):
                filtered_children.append(child)
                continue

            child_score = float(child.get("score") or 0.0)
            has_question_style = bool(
                re.search(r"[？?]", raw_text)
                or QUESTION_DIRECTIVE_HINT_RE.search(raw_text)
            )
            # 在已有编号兄弟节点的前提下，无编号且非问句/非空位的长说明行统一剔除。
            if not has_question_style and child_score >= 0 and len(raw_text) >= 16:
                continue
            # 有明确题问特征的无编号行保留，其余长材料说明行剔除，避免“多结构”。
            if child_score > 0 and has_question_style:
                filtered_children.append(child)
                continue
            if child_score <= 0 and has_question_style and len(raw_text) <= 24:
                filtered_children.append(child)
                continue

            if _is_material_paragraph_like_text(raw_text) or len(raw_text) >= 26:
                continue
            filtered_children.append(child)

        node["children"] = filtered_children


def _prune_duplicate_numbering_answer_echo_children(nodes: List[Dict]) -> None:
    if not nodes:
        return

    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _prune_duplicate_numbering_answer_echo_children(children)
        if len(children) < 6:
            continue

        number_positions: Dict[int, List[int]] = {}
        for idx, child in enumerate(children):
            value = _parse_ascii_int(child.get("numbering"))
            if value is None:
                continue
            number_positions.setdefault(value, []).append(idx)

        duplicated_numbers = sorted(
            value for value, positions in number_positions.items() if len(positions) >= 2
        )
        if len(duplicated_numbers) < 3:
            continue
        if duplicated_numbers[0] != 1:
            continue

        run_size = len(duplicated_numbers)
        first_positions = [number_positions[value][0] for value in duplicated_numbers]
        second_positions = [number_positions[value][1] for value in duplicated_numbers]
        if first_positions != list(range(first_positions[0], first_positions[0] + run_size)):
            continue
        if second_positions != list(range(second_positions[0], second_positions[0] + run_size)):
            continue
        if second_positions[0] <= first_positions[-1]:
            continue

        first_block = [children[idx] for idx in first_positions]
        second_block = [children[idx] for idx in second_positions]

        first_slot_hits = sum(1 for child in first_block if _has_slot_marker(child))
        second_slot_hits = sum(1 for child in second_block if _has_slot_marker(child))
        if first_slot_hits < max(2, run_size // 2):
            continue
        if second_slot_hits > 0:
            continue

        second_texts = [
            normalize_line(str(child.get("rawText") or child.get("title") or ""))
            for child in second_block
        ]
        if any(not text for text in second_texts):
            continue
        if any(re.search(r"[？?]", text) for text in second_texts):
            continue
        if any(QUESTION_DIRECTIVE_HINT_RE.search(text) for text in second_texts):
            continue

        avg_second_len = sum(len(text) for text in second_texts) / float(len(second_texts))
        if avg_second_len > 48:
            continue

        drop_indexes = set(second_positions)
        node["children"] = [
            child for idx, child in enumerate(children) if idx not in drop_indexes
        ]


def _duplicate_child_quality(child: Dict) -> Tuple[int, float]:
    text = normalize_line(str(child.get("rawText") or child.get("title") or ""))
    score_value = float(child.get("score") or 0.0)
    has_children = bool(child.get("children"))
    has_slot = _has_slot_marker(child)
    has_question_semantic = bool(
        QUESTION_DIRECTIVE_HINT_RE.search(text)
        or re.search(r"[？?]", text)
    )
    looks_material = bool(_is_material_paragraph_like_text(text))
    looks_writing_requirement = bool(_is_writing_requirement_text(text))
    text_len = len(text)

    quality = 0
    if has_children:
        quality += 8
    if has_slot:
        quality += 6
    if score_value > 0:
        quality += 4
    if has_question_semantic:
        quality += 2
    if looks_material:
        quality -= 3
    if looks_writing_requirement:
        quality -= 4
    if text_len >= 42 and not has_slot and not has_children:
        quality -= 2

    return quality, score_value


def _prune_conflicting_duplicate_numbered_children(nodes: List[Dict]) -> None:
    if not nodes:
        return

    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _prune_conflicting_duplicate_numbered_children(children)
        if len(children) < 2:
            continue

        grouped: Dict[str, List[Tuple[int, Dict]]] = {}
        for idx, child in enumerate(children):
            numbering = str(child.get("numbering") or "").strip()
            if not numbering:
                continue
            grouped.setdefault(numbering, []).append((idx, child))

        drop_indexes: Set[int] = set()
        for _, items in grouped.items():
            if len(items) < 2:
                continue

            ranked = sorted(
                items,
                key=lambda pair: (_duplicate_child_quality(pair[1])[0], _duplicate_child_quality(pair[1])[1]),
                reverse=True,
            )
            best_idx, best_node = ranked[0]
            best_quality, _ = _duplicate_child_quality(best_node)
            best_has_slot = _has_slot_marker(best_node)
            best_has_children = bool(best_node.get("children"))

            for idx, cand in ranked[1:]:
                if idx == best_idx:
                    continue
                cand_quality, cand_score = _duplicate_child_quality(cand)
                cand_has_slot = _has_slot_marker(cand)
                cand_has_children = bool(cand.get("children"))
                cand_text = normalize_line(str(cand.get("rawText") or cand.get("title") or ""))
                cand_material = _is_material_paragraph_like_text(cand_text)
                cand_requirement = _is_writing_requirement_text(cand_text)

                should_drop = False
                # 同题号冲突时，优先保留“有空位/有子级/有分值”的真实题目节点。
                if (
                    (best_has_slot or best_has_children)
                    and not cand_has_slot
                    and not cand_has_children
                    and (cand_material or cand_requirement)
                    and cand_score <= 0
                ):
                    should_drop = True
                elif (
                    best_quality - cand_quality >= 3
                    and not cand_has_slot
                    and not cand_has_children
                    and cand_score <= 0
                ):
                    should_drop = True

                if should_drop:
                    drop_indexes.add(idx)

        if drop_indexes:
            node["children"] = [
                child for idx, child in enumerate(children) if idx not in drop_indexes
            ]


def _increase_outline_levels(node: Dict, delta: int = 1) -> None:
    if not isinstance(node, dict):
        return
    step = max(1, int(delta))
    node["level"] = int(node.get("level", 1)) + step
    for child in node.get("children", []):
        _increase_outline_levels(child, step)


def _replace_leading_paren_number(text: str, new_number: int) -> str:
    raw = str(text or "")
    if not raw:
        return raw
    return re.sub(
        r"^(\s*[\uFF08(]\s*)\d{1,3}(\s*[\uFF09)])",
        rf"\g<1>{int(new_number)}\g<2>",
        raw,
        count=1,
    )


def _normalize_duplicate_paren_arabic_siblings(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _normalize_duplicate_paren_arabic_siblings(children)
        if len(children) < 2:
            continue

        runs: List[List[Dict]] = []
        current_run: List[Dict] = []
        for child in children:
            if str(child.get("_tokenType") or "") == "paren_arabic":
                current_run.append(child)
            else:
                if len(current_run) >= 2:
                    runs.append(current_run)
                current_run = []
        if len(current_run) >= 2:
            runs.append(current_run)

        for run in runs:
            # 保留原文题号：若节点正文本身已含“(n)”前缀，不进行自动重排改号。
            if any(
                re.match(
                    r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]",
                    normalize_line(str(item.get("rawText") or item.get("title") or "")),
                )
                for item in run
            ):
                continue
            nums = [_parse_ascii_int(item.get("numbering")) for item in run]
            if any(value is None for value in nums):
                continue
            parsed_nums: List[int] = [int(value) for value in nums if value is not None]
            has_duplicate = len(parsed_nums) != len(set(parsed_nums))
            has_non_increasing = any(
                right <= left for left, right in zip(parsed_nums, parsed_nums[1:])
            )
            if not has_duplicate and not has_non_increasing:
                continue

            expected = parsed_nums[0] if parsed_nums[0] and parsed_nums[0] <= 3 else 1
            seen: Set[int] = set()
            for child in run:
                value = _parse_ascii_int(child.get("numbering"))
                if value is None:
                    continue
                target = int(value)
                if target in seen or target < expected:
                    target = expected
                while target in seen:
                    target += 1
                if target != int(value):
                    child["numbering"] = str(target)
                seen.add(target)
                expected = max(expected + 1, target + 1)


def _nest_restarted_arabic_children_under_last_paren_child(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _nest_restarted_arabic_children_under_last_paren_child(children)
        if len(children) < 4:
            continue

        paren_end = 0
        while paren_end < len(children) and str(children[paren_end].get("_tokenType") or "") == "paren_arabic":
            paren_end += 1
        if paren_end < 2 or paren_end >= len(children):
            continue

        tail = children[paren_end:]
        if not tail:
            continue
        if any(str(item.get("_tokenType") or "") not in {"arabic", "arabic_loose", "arabic_bare"} for item in tail):
            continue

        tail_nums = [_parse_ascii_int(item.get("numbering")) for item in tail]
        if any(value is None for value in tail_nums):
            continue
        tail_nums = [int(value) for value in tail_nums if value is not None]
        if not tail_nums or tail_nums[0] != 1:
            continue
        if any(right != left + 1 for left, right in zip(tail_nums, tail_nums[1:])):
            continue

        paren_nums = [_parse_ascii_int(item.get("numbering")) for item in children[:paren_end]]
        if all(value is not None for value in paren_nums):
            overlap = set(int(v) for v in paren_nums if v is not None) & set(tail_nums)
            if not overlap:
                continue

        last_paren = children[paren_end - 1]
        if last_paren.get("children"):
            continue

        has_slot_tail = any(_has_slot_marker(item) for item in tail)
        has_short_prompt_tail = any(
            len(normalize_line(str(item.get("rawText") or item.get("title") or ""))) <= 40
            for item in tail
        )
        if not (has_slot_tail or has_short_prompt_tail):
            continue

        for item in tail:
            _increase_outline_levels(item, 1)
        last_paren["children"] = list(last_paren.get("children", [])) + tail
        node["children"] = children[:paren_end]


def _should_attach_arabic_root_to_previous_chinese_root(previous: Dict, current: Dict) -> bool:
    prev_type = str(previous.get("_tokenType") or "")
    curr_type = str(current.get("_tokenType") or "")
    if prev_type not in {"chinese", "chinese_loose", "roman", "appendix", "paper_volume"}:
        return False
    if curr_type not in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
        return False
    if not current.get("children"):
        return False
    if float(current.get("score") or 0) <= 0:
        return False

    # 防误挂：若上一中文根节点下已经存在多个阿拉伯编号子题，
    # 且当前根节点编号与已有子题编号发生重叠/回退，则该节点更可能是“并列大题”而非子题分段。
    previous_children = list(previous.get("children") or [])
    if previous_children:
        existing_arabic_numbers: List[int] = []
        for child in previous_children:
            child_token = str(child.get("_tokenType") or "")
            if child_token not in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
                continue
            child_num = _parse_ascii_int(child.get("numbering"))
            if child_num is not None:
                existing_arabic_numbers.append(int(child_num))

        current_num = _parse_ascii_int(current.get("numbering"))
        if current_num is not None and existing_arabic_numbers:
            if int(current_num) in set(existing_arabic_numbers):
                return False
            if len(existing_arabic_numbers) >= 2 and int(current_num) <= max(existing_arabic_numbers):
                return False

    if prev_type == "paper_volume":
        previous_marker = normalize_line(
            " ".join(
                part
                for part in [
                    str(previous.get("numbering") or ""),
                    str(previous.get("title") or ""),
                    str(previous.get("rawText") or ""),
                ]
                if part
            )
        )
        # “第X部分/第X节”后的阿拉伯分段通常属于该部分内部，不应再并列成新的一级结构。
        if "部分" in previous_marker or re.search(r"第\s*[一二三四五六七八九十百\d]+\s*节", previous_marker):
            return True

    title = normalize_line(str(current.get("title") or current.get("rawText") or ""))
    title_core = normalize_line(PAREN_SCORE_ONLY_RE.sub("", title)).strip("。．.,，、；;:： ")
    if not title_core or len(title_core) > 24:
        return False
    if WRITING_SECTION_TITLE_RE.search(title_core):
        return False
    if QUESTION_DIRECTIVE_HINT_RE.search(title_core) or re.search(r"[？?]", title_core):
        return False

    if "【" in str(current.get("rawText") or "") or "】" in str(current.get("rawText") or ""):
        return True
    if SECTION_TITLE_FALLBACK_HINT_RE.search(title_core) or QUESTION_SECTION_TITLE_RE.search(title_core):
        return True
    if re.search(r"(?:活动[一二三四五六七八九十]|任务[一二三四五六七八九十]|名著阅读|综合实践)", title_core):
        return True
    return False


def _nest_arabic_section_roots_under_previous_chinese_root(roots: List[Dict]) -> None:
    if len(roots) < 2:
        return
    normalized_roots: List[Dict] = []
    for node in roots:
        if (
            normalized_roots
            and _should_attach_arabic_root_to_previous_chinese_root(normalized_roots[-1], node)
        ):
            _increase_outline_levels(node, 1)
            normalized_roots[-1]["children"] = list(normalized_roots[-1].get("children", [])) + [node]
            continue
        normalized_roots.append(node)
    roots[:] = normalized_roots


def _flatten_unnumbered_scored_reading_roots(roots: List[Dict]) -> None:
    if not roots:
        return

    normalized_roots: List[Dict] = []
    for node in roots:
        children = list(node.get("children") or [])
        if children:
            _flatten_unnumbered_scored_reading_roots(children)

        numbering = str(node.get("numbering") or "").strip()
        level = int(node.get("level", 1) or 1)
        score = float(node.get("score") or 0.0)
        title_probe = normalize_line(str(node.get("title") or node.get("rawText") or ""))

        should_flatten = False
        if (
            not numbering
            and level == 1
            and score > 0
            and len(children) >= 2
            and re.search(r"(?:阅读|文言文|现代文|材料|回答问题|完成题目)", title_probe)
        ):
            child_numbers = [_parse_ascii_int(child.get("numbering")) for child in children]
            if child_numbers and all(value is not None for value in child_numbers):
                previous_numeric_root = next(
                    (
                        _parse_ascii_int(prev.get("numbering"))
                        for prev in reversed(normalized_roots)
                        if _parse_ascii_int(prev.get("numbering")) is not None
                    ),
                    None,
                )
                first_child_number = child_numbers[0]
                if (
                    previous_numeric_root is not None
                    and first_child_number is not None
                    and first_child_number == previous_numeric_root + 1
                ):
                    should_flatten = True

        if should_flatten:
            for child in children:
                _decrease_outline_levels(child, 1)
                normalized_roots.append(child)
            continue

        normalized_roots.append(node)

    roots[:] = normalized_roots


def _outline_token_family(token_type: str) -> str:
    token = str(token_type or "")
    if token in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
        return "arabic"
    if token == "paren_arabic":
        return "paren_arabic"
    return token


def _should_promote_same_family_sequential_child(parent: Dict, child: Dict) -> bool:
    parent_family = _outline_token_family(str(parent.get("_tokenType") or ""))
    child_family = _outline_token_family(str(child.get("_tokenType") or ""))
    if parent_family not in {"arabic", "paren_arabic"}:
        return False
    if parent_family != child_family:
        return False

    parent_number = _parse_ascii_int(parent.get("numbering"))
    child_number = _parse_ascii_int(child.get("numbering"))
    if parent_number is None or child_number is None:
        return False
    if child_number != parent_number + 1:
        return False
    return True


def _flatten_same_family_sequential_children(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _flatten_same_family_sequential_children(children)

        children = node.get("children", []) or []
        if not children:
            continue

        changed = True
        while changed:
            changed = False
            rebuilt: List[Dict] = []
            for child in children:
                grand_children = list(child.get("children", []) or [])
                promoted: List[Dict] = []
                while grand_children and _should_promote_same_family_sequential_child(child, grand_children[0]):
                    promoted_node = grand_children.pop(0)
                    _decrease_outline_levels(promoted_node, 1)
                    promoted.append(promoted_node)
                    changed = True
                if promoted:
                    child["children"] = grand_children
                rebuilt.append(child)
                rebuilt.extend(promoted)
            children = rebuilt
        node["children"] = children


def _prune_zero_score_material_marker_leaves(
    nodes: List[Dict],
    under_reading_context: bool = False,
) -> None:
    if not nodes:
        return

    kept: List[Dict] = []
    for node in nodes:
        text_probe = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        current_under_reading = bool(
            under_reading_context
            or READING_MATERIAL_PARENT_HINT_RE.search(text_probe)
            or "\u9605\u8bfb" in text_probe
        )

        children = node.get("children", []) or []
        if children:
            _prune_zero_score_material_marker_leaves(children, current_under_reading)
            node["children"] = children

        if node.get("children"):
            kept.append(node)
            continue

        score = node.get("score")
        score_value = float(score) if score is not None else 0.0
        if score_value > 0:
            kept.append(node)
            continue

        if not current_under_reading:
            kept.append(node)
            continue

        token_type = str(node.get("_tokenType") or "")
        raw_text = normalize_line(str(node.get("rawText") or node.get("title") or ""))
        if not raw_text:
            continue
        if QUESTION_DIRECTIVE_HINT_RE.search(raw_text) or re.search(r"[\uFF1F?]", raw_text):
            kept.append(node)
            continue

        blank_text = str(node.get("blankText") or "").strip()
        has_only_zero_blank = False
        if blank_text:
            parsed_scores = [_parse_merged_blank_segment_score(token) for token in blank_text.split()]
            if parsed_scores and all(value is not None and float(value) <= 0 for value in parsed_scores):
                has_only_zero_blank = True

        if token_type == "circled":
            if _is_material_paragraph_like_text(raw_text) or has_only_zero_blank:
                continue
        if token_type == "paren_arabic":
            number_value = _parse_ascii_int(node.get("numbering"))
            if (
                number_value is not None
                and number_value >= 10
                and (_is_material_paragraph_like_text(raw_text) or has_only_zero_blank)
            ):
                continue

        kept.append(node)

    nodes[:] = kept


def _try_merge_scored_text_into_previous_heading(
    stack: List[Dict],
    candidate: ScoredTextCandidate,
) -> bool:
    if not stack:
        return False
    parent = stack[-1]
    token_type = str(parent.get("_tokenType") or "")
    if token_type not in {"arabic", "arabic_loose", "arabic_bare", "decimal", "paren_arabic", "circled"}:
        return False
    parent_text = normalize_line(str(parent.get("rawText") or parent.get("title") or ""))
    if _is_matching_question_heading_text(parent_text):
        return False
    if parent.get("score") is not None:
        return False
    parent_line_no = int(parent.get("lineNumber") or 0) - 1
    if candidate.line_no <= parent_line_no or candidate.line_no - parent_line_no > 4:
        return False
    parent["score"] = float(candidate.score)

    # 规则说明：分数提取与分配（示例：_mergedBlankSegments）的逻辑约束。
    # 规则说明：下划线与括号空提取（示例：_mergedBlankSegments）的逻辑约束。
    # 规则说明：下划线与括号空提取（示例：_mergedBlankSegments）的逻辑约束。
    # 规则说明：分数提取与分配（示例：_mergedBlankSegments）的条件过滤。
    if not parent.get("children"):
        merged_blank_segments = parent.get("_mergedBlankSegments")
        if isinstance(merged_blank_segments, list) and merged_blank_segments:
            if _all_merged_blank_segments_zero(merged_blank_segments):
                rebalanced = _rebalance_merged_blank_segments(merged_blank_segments, float(candidate.score))
                parent["_mergedBlankSegments"] = rebalanced
                parent["blankText"] = " ".join(rebalanced)
    return True


def _try_merge_wrapped_numeric_continuation_into_previous_heading(
    stack: List[Dict],
    candidate: HeadingCandidate,
) -> bool:
    if not stack:
        return False
    if candidate.token_type not in {"arabic", "arabic_loose"}:
        return False
    if candidate.number_value is None or candidate.number_value <= 0:
        return False
    parent = stack[-1]
    parent_token = str(parent.get("_tokenType") or "")
    if parent_token not in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
        return False
    parent_line_no = int(parent.get("lineNumber") or 0) - 1
    if candidate.line_no <= parent_line_no or candidate.line_no - parent_line_no > 1:
        return False

    parent_raw = str(parent.get("rawText") or "")
    parent_raw_tail = normalize_line(parent_raw)
    if not parent_raw_tail:
        return False
    if not re.search(r"[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A0-9\uFF10-\uFF19]$", parent_raw_tail):
        return False

    candidate_raw = normalize_line(candidate.raw or "")
    if not re.match(
        r"^\d{1,4}\s*[\u3001\.\uFF0E]\s*[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A]\d",
        candidate_raw,
    ):
        return False

    parent_number = _parse_ascii_int(parent.get("numbering"))
    if parent_number is not None and candidate.number_value == parent_number + 1:
        return False

    joiner = "" if re.search(r"[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A0-9\uFF10-\uFF19]$", parent_raw) else " "
    parent["rawText"] = normalize_line(f"{parent_raw}{joiner}{candidate_raw}")

    parent_title = str(parent.get("title") or "")
    parent["title"] = normalize_line(f"{parent_title}{joiner}{candidate_raw}")
    return True


def _try_merge_blank_into_previous_heading(
    stack: List[Dict],
    candidate: BlankScoreCandidate,
) -> bool:
    if not stack:
        return False
    parent = stack[-1]
    token_type = str(parent.get("_tokenType") or "")
    parent_level = int(parent.get("level") or 1)
    parent_line_no = int(parent.get("lineNumber") or 0) - 1

    # 规则说明：题号与层级识别（示例：paren_arabic）的逻辑约束。
    # 规则说明：题号与层级识别（示例：paren_arabic）的条件过滤。
    if token_type in {"paren_arabic", "arabic", "arabic_loose", "arabic_bare", "decimal", "circled"} and parent_level >= 2:
        distance = candidate.line_no - parent_line_no
        allow = False
        if token_type == "paren_arabic":
            allow = distance > 0
        else:
            allow = 0 < distance <= 6
        if allow:
            parent_probe_text = normalize_line(str(parent.get("rawText") or parent.get("title") or ""))
            # 选择题题干下不抽取空位子结构（含续行下划线/括号空），仅保留题目本身。
            if _is_choice_question_heading_text(parent_probe_text):
                return True
            # 规则说明：分数提取与分配（示例：_isSectionHeading）的逻辑约束。
            # 规则说明：分数提取与分配（示例：_isSectionHeading）的条件过滤。
            if bool(parent.get("_isSectionHeading")) and candidate.score <= 0:
                return True
            # 规则说明：分数提取与分配（示例：_isSectionHeading）的逻辑约束。
            # 规则说明：分数提取与分配的条件过滤。
            if candidate.score <= 0 and _is_under_writing_section(stack):
                if _collect_blank_segments(candidate.raw):
                    return True
            # 规则说明：下划线与括号空提取的逻辑约束。
            # 规则说明：下划线与括号空提取的逻辑约束。
            # 规则说明：下划线与括号空提取的条件过滤。
            if _is_pure_underline_answer_line(candidate.raw):
                candidate_segments = _collect_blank_segments(candidate.raw)
                parent_raw_segments = _collect_blank_segments(str(parent.get("rawText") or ""))
                if (
                    len(candidate_segments) == 1
                    and len(candidate_segments[0][0]) <= 4
                    and bool(parent_raw_segments)
                ):
                    return True
                # 规则说明：分数提取与分配的逻辑约束。
                # 规则说明：分数提取与分配的条件过滤。
                if (
                    candidate.score <= 0
                    and len(candidate_segments) == 1
                    and _is_long_single_underline_answer_line(candidate.raw)
                    and not parent.get("children")
                ):
                    parent["_longAnswerUnderline"] = True
                    return True

            zero_continuation = _should_zero_continuation_blank_scores(parent, candidate)
            if candidate.score > 0:
                parent_score = float(parent.get("score") or 0)
                if parent_score <= 0:
                    parent["score"] = float(candidate.score)
                elif token_type == "paren_arabic" and not zero_continuation:
                    parent["score"] = _normalize_score_value(parent_score + float(candidate.score))
                elif _should_accumulate_blank_line_score(parent, candidate):
                    parent["score"] = _normalize_score_value(parent_score + float(candidate.score))
            merged_blank_segments = parent.get("_mergedBlankSegments")
            if not isinstance(merged_blank_segments, list):
                merged_blank_segments = []
                # 规则说明：下划线与括号空提取的逻辑约束。
                # 规则说明：下划线与括号空提取（示例：_mergedBlankSegments）的条件过滤。
                if _collect_blank_segments(str(parent.get("rawText") or "")):
                    existing = str(parent.get("blankText") or "").strip()
                    if existing:
                        merged_blank_segments.extend(existing.split())
                parent["_mergedBlankSegments"] = merged_blank_segments

            if zero_continuation:
                candidate_blank_text = _format_zero_blank_segments_from_line(candidate.raw)
            else:
                fallback_score = float(candidate.score or 0.0)
                if fallback_score <= 0 and not merged_blank_segments:
                    parent_score = parent.get("score")
                    # 规则说明：分数提取与分配的逻辑约束。
                    # 规则说明：分数提取与分配的规则定义。
                    has_underline = bool(_collect_blank_segments(candidate.raw))
                    if parent_score is not None and float(parent_score) > 0 and has_underline:
                        fallback_score = float(parent_score)
                candidate_blank_text = _format_blank_segments_from_line(candidate.raw, fallback_score)
            if candidate_blank_text:
                merged_blank_segments.extend(candidate_blank_text.split())
                if (
                    not parent.get("children")
                    and float(parent.get("score") or 0) > 0
                    and float(candidate.score or 0) <= 0
                    and _is_pure_empty_bracket_line(candidate.raw)
                ):
                    merged_blank_segments = _rebalance_merged_blank_segments(
                        merged_blank_segments,
                        float(parent.get("score") or 0),
                    )
                    parent["_mergedBlankSegments"] = merged_blank_segments
                parent["blankText"] = " ".join(merged_blank_segments)
            return True

    return False


def _assign_sequence(nodes: List[Dict]) -> None:
    for idx, node in enumerate(nodes, start=1):
        node["sequence"] = idx
        _assign_sequence(node["children"])


def _prune_writing_instruction_children(nodes: List[Dict]) -> None:
    writing_instruction_re = re.compile(
        r"(?:^|\s)(?:\u9898\u76ee[:\uff1a]|\u8981\u6c42[:\uff1a]|\u8bf7\u4ee5|\u8bf7\u9009|"
        r"\u4efb\u9009|\u4e0a\u5217\u4e24\u9898|\u6587\u4e2d\u4e0d\u5f97|\u4e0d\u5f97\u51fa\u73b0|"
        r"\u5b57\u6570\u4e0d\u5c11\u4e8e|\u4e0d\u5c11\u4e8e|\u4f5c\u6587)"
    )
    for node in nodes:
        children = node.get("children", [])
        if children:
            title = normalize_line(str(node.get("title") or ""))
            if WRITING_SECTION_TITLE_RE.search(title):
                has_main_arabic_question = any(
                    str(child.get("_tokenType") or "") in {"arabic", "arabic_loose", "arabic_bare"}
                    and _parse_ascii_int(child.get("numbering")) is not None
                    for child in children
                )
                filtered_children: List[Dict] = []
                saw_high_number = False
                for child in children:
                    numbering = str(child.get("numbering") or "").strip()
                    number_value = _parse_ascii_int(numbering)
                    child_token = str(child.get("_tokenType") or "")
                    child_raw = str(child.get("rawText") or "")
                    child_title = normalize_line(str(child.get("title") or child_raw))
                    child_has_slot = bool(_collect_blank_segments(child_raw))
                    if number_value is not None and number_value >= 50:
                        saw_high_number = True

                    if (
                        has_main_arabic_question
                        and child_token in {"chinese_paren", "paren_arabic", "circled"}
                        and float(child.get("score") or 0) <= 0
                        and not child_has_slot
                        and writing_instruction_re.search(child_title)
                    ):
                        continue

                    # 作文部分中的“(1)/(2) 命题材料/写作提示”不作为结构小题提取。
                    if (
                        has_main_arabic_question
                        and child_token in {"arabic", "arabic_loose", "arabic_bare", "decimal", "paren_arabic"}
                        and float(child.get("score") or 0) <= 0
                        and not child_has_slot
                        and not child.get("children")
                        and _looks_like_writing_option_prompt(child_title)
                    ):
                        continue

                    if (
                        saw_high_number
                        and number_value is not None
                        and number_value <= 20
                        and float(child.get("score") or 0) <= 0
                    ):
                        continue
                    filtered_children.append(child)
                node["children"] = filtered_children
                children = filtered_children

            _prune_writing_instruction_children(children)


def _prune_writing_prompt_requirement_children(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _prune_writing_prompt_requirement_children(children)

        children = node.get("children", []) or []
        if not children:
            continue

        node_text = normalize_line(str(node.get("rawText") or node.get("title") or ""))
        if not _looks_like_writing_option_prompt(node_text):
            continue

        removable_children: List[Dict] = []
        keep_children: List[Dict] = []
        for child in children:
            child_text = normalize_line(str(child.get("rawText") or child.get("title") or ""))
            child_token = str(child.get("_tokenType") or "")
            child_numbering = str(child.get("numbering") or "").strip()
            child_has_children = bool(child.get("children"))
            child_has_slot = bool(_collect_blank_segments(str(child.get("rawText") or "")))

            is_requirement_leaf = (
                not child_has_children
                and not child_has_slot
                and (
                    _is_writing_requirement_text(child_text)
                    or child_token in {"paren_arabic", "circled", "chinese_paren"}
                    or bool(re.fullmatch(r"\d+", child_numbering))
                )
            )
            if is_requirement_leaf:
                removable_children.append(child)
            else:
                keep_children.append(child)

        # 作文题干下若只有“(1)(2)(3)(4)要求”这类说明项，则全部剔除，只保留作文题目本身。
        if removable_children and not keep_children:
            node["children"] = []


def _collapse_writing_section_children_to_single_prompt(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _collapse_writing_section_children_to_single_prompt(children)

        title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        if not WRITING_SECTION_TITLE_RE.search(title):
            continue
        children = node.get("children", []) or []
        if len(children) <= 1:
            continue

        # 作文大题下若存在多个“带分值”的真实子节（如：综合性学习6分 + 写作50分），
        # 不能折叠为单子项，否则会丢失有效结构与分值。
        scored_children = [child for child in children if float(child.get("score") or 0.0) > 0]
        if len(scored_children) >= 2:
            continue

        preferred = next(
            (
                child
                for child in children
                if _looks_like_writing_option_prompt(
                    normalize_line(str(child.get("rawText") or child.get("title") or ""))
                )
            ),
            None,
        )
        if preferred is None:
            preferred = children[0]
        node["children"] = [preferred]


def _propagate_writing_section_score_to_single_child(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            title = normalize_line(str(node.get("title") or ""))
            parent_score = node.get("score")
            if (
                parent_score is not None
                and float(parent_score) > 0
                and WRITING_SECTION_TITLE_RE.search(title)
                and len(children) == 1
            ):
                child = children[0]
                child_num = _parse_ascii_int(child.get("numbering"))
                child_children = child.get("children", [])
                if (
                    child_num is not None
                    and not child_children
                ):
                    child["score"] = float(parent_score)
            _propagate_writing_section_score_to_single_child(children)


def _prune_material_paragraph_children(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children and str(node.get("_tokenType") or "") == "chinese_paren":
            arabic_children = [
                child
                for child in children
                if str(child.get("_tokenType") or "") in {"arabic", "arabic_loose", "arabic_bare", "decimal"}
            ]
            if arabic_children:
                first_arabic_line = min(int(child.get("lineNumber") or 10**9) for child in arabic_children)
                filtered_children: List[Dict] = []
                for child in children:
                    child_line = int(child.get("lineNumber") or 0)
                    child_type = str(child.get("_tokenType") or "")
                    raw = str(child.get("rawText") or "")
                    if (
                        child_line < first_arabic_line
                        and child_type in {"paren_arabic", "chinese", "chinese_loose"}
                        and float(child.get("score") or 0) <= 0
                        and not _collect_blank_segments(raw)
                        and _is_material_paragraph_like_text(str(child.get("title") or raw))
                    ):
                        continue
                    filtered_children.append(child)
                node["children"] = filtered_children
                children = filtered_children

        if children and str(node.get("_tokenType") or "") in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
            parent_title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
            in_reading_context = bool(
                READING_MATERIAL_PARENT_HINT_RE.search(parent_title) or "\u9605\u8bfb" in parent_title
            )
            filtered_children: List[Dict] = []
            for child in children:
                child_type = str(child.get("_tokenType") or "")
                child_raw = str(child.get("rawText") or "")
                child_title = normalize_line(str(child.get("title") or child_raw))
                child_number = _parse_ascii_int(child.get("numbering"))
                if (
                    child_type in {"paren_arabic", "circled"}
                    and child_number is not None
                    and (child_number >= 10 or (in_reading_context and child_number >= 5))
                    and not child.get("children")
                    and not _collect_blank_segments(child_raw)
                    and not EMPTY_BRACKET_RE.search(child_raw)
                    and not QUESTION_DIRECTIVE_HINT_RE.search(child_title)
                    and not re.search(r"[\uFF1F?]", child_title)
                    and _is_material_paragraph_like_text(child_title)
                ):
                    continue
                filtered_children.append(child)
            node["children"] = filtered_children
            children = filtered_children

        if children:
            _prune_material_paragraph_children(children)


def _prune_material_style_high_index_paren_children(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if children:
            _prune_material_style_high_index_paren_children(children)

        children = node.get("children", []) or []
        if not children:
            continue

        parent_number = _parse_ascii_int(node.get("numbering"))
        if parent_number is None:
            continue

        filtered_children: List[Dict] = []
        for child in children:
            raw_text = normalize_line(str(child.get("rawText") or child.get("title") or ""))
            if not raw_text or child.get("children"):
                filtered_children.append(child)
                continue

            marker = re.match(r"^\s*[\uFF08(]\s*(\d{2,3})\s*[\uFF09)]", raw_text)
            if not marker:
                filtered_children.append(child)
                continue

            try:
                marker_value = int(marker.group(1))
            except (TypeError, ValueError):
                filtered_children.append(child)
                continue

            if marker_value < 10:
                filtered_children.append(child)
                continue

            has_slot = bool(_collect_blank_segments(raw_text) or EMPTY_BRACKET_RE.search(raw_text))
            if (not has_slot) and _is_material_paragraph_like_text(raw_text):
                continue

            filtered_children.append(child)

        node["children"] = filtered_children


def _prune_duplicate_arabic_range_prompt_nodes(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            remove_idx: set = set()
            for idx, child in enumerate(children):
                token_type = str(child.get("_tokenType") or "")
                if token_type not in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
                    continue
                number_value = _parse_ascii_int(child.get("numbering"))
                if number_value is None:
                    continue
                raw_text = str(child.get("rawText") or "")
                title_text = normalize_line(str(child.get("title") or raw_text))
                prompt_text = normalize_line(PAREN_SCORE_ONLY_RE.sub("", title_text))
                if not prompt_text:
                    continue
                if _collect_blank_segments(raw_text):
                    continue
                if not ARABIC_RANGE_PROMPT_RE.search(prompt_text):
                    continue
                has_same_number_later = False
                for sibling in children[idx + 1 : idx + 4]:
                    sibling_type = str(sibling.get("_tokenType") or "")
                    if sibling_type not in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
                        continue
                    sibling_number = _parse_ascii_int(sibling.get("numbering"))
                    if sibling_number == number_value:
                        has_same_number_later = True
                        break
                if has_same_number_later:
                    remove_idx.add(idx)
            if remove_idx:
                node["children"] = [child for idx, child in enumerate(children) if idx not in remove_idx]
                children = node["children"]
            _prune_duplicate_arabic_range_prompt_nodes(children)


def _extract_question_range_from_text(text: str) -> Optional[Tuple[int, int]]:
    normalized = normalize_line(str(text or ""))
    if not normalized:
        return None
    match = re.search(
        r"(?:回答|完成)\s*(?:第\s*)?[\uFF08(]?\s*(\d{1,3})\s*[\uFF09)]?\s*"
        r"[-~\uFF5E\u2013\u2014\u2015\u2212至到]+\s*[\uFF08(]?\s*(\d{1,3})\s*[\uFF09)]?\s*(?:题|小题)",
        normalized,
    )
    if not match:
        return None
    try:
        start = int(match.group(1))
        end = int(match.group(2))
    except (TypeError, ValueError):
        return None
    if start <= 0 or end <= 0:
        return None
    if end < start:
        start, end = end, start
    return start, end


def _prune_unnumbered_range_prompt_nodes(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if children:
            remove_indexes: Set[int] = set()
            for idx, child in enumerate(children):
                numbering = str(child.get("numbering") or "").strip()
                if numbering:
                    continue
                if child.get("children"):
                    continue
                score = child.get("score")
                if score is None or float(score) <= 0:
                    continue
                raw_text = str(child.get("rawText") or child.get("title") or "")
                if _collect_blank_segments(raw_text) or EMPTY_BRACKET_RE.search(raw_text):
                    continue
                question_range = _extract_question_range_from_text(raw_text)
                if question_range is None:
                    continue
                start, end = question_range
                if end - start < 1:
                    continue
                target_numbers = list(range(start, end + 1))
                scanned = children[idx + 1 : idx + 8]
                if not scanned:
                    continue
                covered: List[Dict] = []
                for cand in scanned:
                    number_value = _parse_ascii_int(cand.get("numbering"))
                    if number_value is None:
                        continue
                    if number_value in target_numbers:
                        covered.append(cand)
                if len(covered) < len(target_numbers):
                    continue
                covered_score = sum(_outline_display_score(cand) for cand in covered)
                if abs(float(score) - float(covered_score)) > 0.01:
                    continue
                remove_indexes.add(idx)
            if remove_indexes:
                node["children"] = [
                    child for i, child in enumerate(children) if i not in remove_indexes
                ]
                children = node["children"]
            _prune_unnumbered_range_prompt_nodes(children)


def _flatten_numbered_range_prompt_nodes(nodes: List[Dict]) -> None:
    if not nodes:
        return
    for node in nodes:
        children = node.get("children", []) or []
        if not children:
            continue
        flattened: List[Dict] = []
        changed = False
        for child in children:
            child_children = child.get("children", []) or []
            raw_text = str(child.get("rawText") or child.get("title") or "")
            prompt_range = _extract_question_range_from_text(raw_text)
            if (
                prompt_range is not None
                and child_children
                and not _collect_blank_segments(raw_text)
                and not EMPTY_BRACKET_RE.search(raw_text)
            ):
                start, end = prompt_range
                expected_numbers = set(range(start, end + 1))
                child_numbers = {
                    number
                    for number in (_parse_ascii_int(grand.get("numbering")) for grand in child_children)
                    if number is not None
                }
                # 仅在“范围内题号基本齐全”时才扁平化，避免误伤普通题。
                if expected_numbers and len(expected_numbers.intersection(child_numbers)) >= max(
                    2, len(expected_numbers) - 1
                ):
                    for grand in child_children:
                        _decrease_outline_levels(grand, 1)
                        flattened.append(grand)
                    changed = True
                    continue

            flattened.append(child)

        if changed:
            node["children"] = flattened
            children = flattened
        _flatten_numbered_range_prompt_nodes(children)


def _hoist_overflow_children_after_scored_container(nodes: List[Dict]) -> None:
    if not nodes:
        return

    idx = 0
    while idx < len(nodes):
        node = nodes[idx]
        children = node.get("children", []) or []
        if children:
            _hoist_overflow_children_after_scored_container(children)
            children = node.get("children", []) or []

        explicit_score = node.get("score")
        token_type = str(node.get("_tokenType") or "")
        if (
            explicit_score is not None
            and float(explicit_score) > 0
            and token_type in {"chinese_paren", "paren_arabic"}
            and len(children) >= 2
        ):
            child_scores = [_outline_display_score(child) for child in children]
            cum = 0.0
            split_at: Optional[int] = None
            for child_idx, value in enumerate(child_scores):
                cum = round(cum + float(value), 2)
                if abs(cum - float(explicit_score)) <= 0.01:
                    split_at = child_idx + 1
                    break
                if cum > float(explicit_score) + 0.01:
                    break

            if split_at is not None and split_at < len(children):
                kept = children[:split_at]
                overflow = children[split_at:]
                if overflow and all(float(_outline_display_score(item)) > 0 for item in overflow):
                    kept_last_num = _parse_ascii_int(kept[-1].get("numbering"))
                    first_overflow_num = _parse_ascii_int(overflow[0].get("numbering"))
                    if (
                        kept_last_num is not None
                        and first_overflow_num is not None
                        and first_overflow_num > kept_last_num
                    ):
                        node["children"] = kept
                        for item in overflow:
                            _decrease_outline_levels(item, 1)
                        nodes[idx + 1 : idx + 1] = overflow
                        idx += len(overflow)
        idx += 1


def _decrease_outline_levels(node: Dict, delta: int = 1) -> None:
    if not isinstance(node, dict):
        return
    current = int(node.get("level", 1))
    node["level"] = max(1, current - max(1, int(delta)))
    for child in node.get("children", []):
        _decrease_outline_levels(child, delta)


def _is_article_marker_chinese_paren_node(
    parent: Dict,
    child: Dict,
    has_multiple_markers: bool,
    force_flatten_by_numbering: bool,
    preserve_by_numbering_restart: bool,
) -> bool:
    token_type = str(child.get("_tokenType") or "")
    raw_text = normalize_line(str(child.get("rawText") or ""))
    is_chinese_paren_marker = bool(
        re.match(r"^\s*[\uFF08(]\s*[一二三四五六七八九十]{1,3}\s*[\uFF09)]", raw_text)
    )
    if token_type != "chinese_paren" and not is_chinese_paren_marker:
        return False

    grandchildren = child.get("children", [])
    if not grandchildren:
        return False

    parent_text = normalize_line(str(parent.get("title") or parent.get("rawText") or ""))
    if not parent_text:
        return False
    if not (READING_MATERIAL_PARENT_HINT_RE.search(parent_text) or "\u9605\u8bfb" in parent_text):
        return False

    has_numbered_question_children = any(
        _parse_ascii_int(grand.get("numbering")) is not None
        for grand in grandchildren
    )
    if not has_numbered_question_children:
        return False

    title = normalize_line(str(child.get("title") or child.get("rawText") or ""))
    title_wo_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", title)).strip()
    explicit_question_range_heading = _extract_question_range_from_text(title_wo_score) is not None
    marker_score = child.get("score")
    has_explicit_marker_score = marker_score is not None and float(marker_score or 0) > 0
    numbered_values = [
        _parse_ascii_int(grand.get("numbering"))
        for grand in grandchildren
    ]
    numbered_values = [value for value in numbered_values if value is not None]
    min_numbered_child = min(numbered_values) if numbered_values else None
    numbered_children_count = sum(
        1
        for grand in grandchildren
        if _parse_ascii_int(grand.get("numbering")) is not None
    )
    single_marker_flatten_candidate = bool(
        not has_multiple_markers
        and has_explicit_marker_score
        and numbered_children_count >= 2
        and min_numbered_child is not None
        and min_numbered_child >= 10
        and title_wo_score
        and not QUESTION_DIRECTIVE_HINT_RE.search(title_wo_score)
        and not re.search(r"[\uFF1F?]", title_wo_score)
    )
    # 仅有一个“（一）/（二）...”分块时，也可能是阅读材料标题（非题目），
    # 尤其其下直接承接连续阿拉伯题号（如20/21/22）。
    single_marker_article_title_flatten_candidate = bool(
        not has_multiple_markers
        and not has_explicit_marker_score
        and numbered_children_count >= 2
        and min_numbered_child is not None
        and min_numbered_child >= 10
        and title_wo_score
        and not explicit_question_range_heading
        and not QUESTION_DIRECTIVE_HINT_RE.search(title_wo_score)
        and not re.search(r"[\uFF1F?]", title_wo_score)
        and not _collect_blank_segments(str(child.get("rawText") or ""))
        and not EMPTY_BRACKET_RE.search(str(child.get("rawText") or ""))
    )
    single_marker_reading_title_flatten_candidate = bool(
        not has_multiple_markers
        and numbered_children_count >= 2
        and min_numbered_child is not None
        and min_numbered_child >= 10
        and title_wo_score
        and len(title_wo_score) <= 24
        and not explicit_question_range_heading
        and not QUESTION_DIRECTIVE_HINT_RE.search(title_wo_score)
        and not re.search(r"[\uFF1F?]", title_wo_score)
        and not re.search(
            r"(?:\u56de\u7b54|\u5b8c\u6210|\u8bf7|\u4e0b\u5217|\u89e3\u91ca|\u5206\u6790|\u6982\u62ec|\u8bf4\u660e|\u5224\u65ad|\u9009\u62e9)",
            title_wo_score,
        )
        and not _collect_blank_segments(str(child.get("rawText") or ""))
        and not EMPTY_BRACKET_RE.search(str(child.get("rawText") or ""))
    )

    # 阅读/材料分块（如“（一）文言文阅读”“（二）课外阅读”）通常只是题组标题，
    # 其下阿拉伯编号才是实际题目，优先扁平化该层，避免把分块标题误当题目节点。
    reading_material_marker_title = bool(
        title_wo_score
        and re.search(
            r"(?:阅读|文言文|现代文|课内|课外|材料|诗歌|古诗|文段|短文|选文|名著|回答问题|完成\d{1,3}\s*[-~～—]\s*\d{1,3}\s*题)",
            title_wo_score,
        )
    )
    if (
        reading_material_marker_title
        and has_numbered_question_children
        and not QUESTION_DIRECTIVE_HINT_RE.search(title_wo_score)
        and not re.search(r"[\uFF1F?]", title_wo_score)
        and not _collect_blank_segments(str(child.get("rawText") or ""))
        and not EMPTY_BRACKET_RE.search(str(child.get("rawText") or ""))
    ):
        return True

    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的条件过滤。
    if (
        not has_multiple_markers
        and not single_marker_flatten_candidate
        and not single_marker_article_title_flatten_candidate
        and not single_marker_reading_title_flatten_candidate
    ):
        return False
    if (
        preserve_by_numbering_restart
        and not single_marker_flatten_candidate
        and not single_marker_article_title_flatten_candidate
        and not single_marker_reading_title_flatten_candidate
    ):
        return False

    if (
        QUESTION_SECTION_TITLE_RE.search(title_wo_score)
        and not explicit_question_range_heading
        and not single_marker_article_title_flatten_candidate
        and not single_marker_reading_title_flatten_candidate
    ):
        return False
    if (
        title_wo_score
        and QUESTION_DIRECTIVE_HINT_RE.search(title_wo_score)
        and not explicit_question_range_heading
    ):
        return False
    if force_flatten_by_numbering:
        if title_wo_score and re.search(
            r"(?:\u8bfe\u5185|\u8bfe\u5916|\u6587\u8a00\u6587|\u73b0\u4ee3\u6587|\u540d\u8457|\u7efc\u5408\u6027\u5b66\u4e60|\u7efc\u5408\u5b9e\u8df5|\u4f5c\u6587|\u5199\u4f5c)",
            title_wo_score,
        ):
            return False
        return True

    if explicit_question_range_heading:
        return True
    if (
        single_marker_flatten_candidate
        or single_marker_article_title_flatten_candidate
        or single_marker_reading_title_flatten_candidate
    ):
        return True

    # 规则说明：识别规则处理的逻辑约束。
    # 规则说明：识别规则处理的逻辑约束。
    # 规则说明：识别规则处理的规则定义。
    if (
        has_multiple_markers
        and numbered_children_count == len(grandchildren)
        and numbered_children_count >= 1
        and title_wo_score
        and len(title_wo_score) <= 24
        and not re.search(
            r"(?:\u8bfe\u5185|\u8bfe\u5916|\u6587\u8a00\u6587|\u73b0\u4ee3\u6587|\u540d\u8457|\u7efc\u5408\u6027\u5b66\u4e60|\u7efc\u5408\u5b9e\u8df5|\u4f5c\u6587|\u5199\u4f5c)",
            title_wo_score,
        )
    ):
        return True

    # 规则说明：分数提取与分配的条件过滤。
    if re.search(r"\u300a[^\u300b]{1,120}\u300b", title_wo_score):
        return True
    if not title_wo_score and child.get("score") is not None and float(child.get("score") or 0) > 0:
        return False
    return False


def _flatten_article_marker_chinese_paren_children(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if not children:
            continue
        chinese_paren_markers = [
            child for child in children if str(child.get("_tokenType") or "") == "chinese_paren"
        ]
        has_multiple_markers = len(chinese_paren_markers) >= 2
        marker_first_numbers: List[int] = []
        for marker in chinese_paren_markers:
            numbered = [
                _parse_ascii_int(grand.get("numbering"))
                for grand in marker.get("children", [])
            ]
            numbered = [value for value in numbered if value is not None]
            if numbered:
                marker_first_numbers.append(min(numbered))
        preserve_by_numbering_restart = (
            len(marker_first_numbers) >= 2
            and sum(1 for value in marker_first_numbers if value == 1) >= 2
        )
        parent_text = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        force_flatten_by_numbering = (
            len(marker_first_numbers) >= 2
            and min(marker_first_numbers) >= 10
            and bool(READING_MATERIAL_PARENT_HINT_RE.search(parent_text) or "\u9605\u8bfb" in parent_text)
        )

        flattened: List[Dict] = []
        changed = False
        for child in children:
            child_raw = normalize_line(str(child.get("rawText") or ""))
            child_title = normalize_line(str(child.get("title") or child_raw))
            child_nums = [
                _parse_ascii_int(grand.get("numbering"))
                for grand in child.get("children", [])
            ]
            child_nums = [value for value in child_nums if value is not None]
            fallback_single_reading_article_marker = bool(
                child_nums
                and len(child_nums) >= 2
                and min(child_nums) >= 10
                and bool(re.match(r"^\s*[\uFF08(]\s*[^\d\s]{1,3}\s*[\uFF09)]", child_raw))
                and ("\u9605\u8bfb" in child_raw or "\u9605\u8bfb" in child_title)
                and not _collect_blank_segments(child_raw)
                and not EMPTY_BRACKET_RE.search(child_raw)
                and not re.search(r"[\uFF1F?]", child_title)
                and not QUESTION_DIRECTIVE_HINT_RE.search(child_title)
            )
            if _is_article_marker_chinese_paren_node(
                node,
                child,
                has_multiple_markers,
                force_flatten_by_numbering,
                preserve_by_numbering_restart,
            ) or fallback_single_reading_article_marker:
                for grand in child.get("children", []):
                    _decrease_outline_levels(grand, 1)
                    flattened.append(grand)
                changed = True
            else:
                flattened.append(child)

        if changed:
            node["children"] = flattened
        _flatten_article_marker_chinese_paren_children(node.get("children", []))


def _is_numeric_outline_parent(node: Dict) -> bool:
    token_type = str(node.get("_tokenType") or "")
    if token_type in {"arabic", "arabic_loose", "arabic_bare", "decimal", "paren_arabic"}:
        return True
    return _parse_ascii_int(node.get("numbering")) is not None


def _collect_leaf_blank_tokens(node: Dict) -> List[str]:
    blank_text = str(node.get("blankText") or "").strip()
    if blank_text:
        return blank_text.split()

    raw_text = str(node.get("rawText") or "")
    score_value = float(node.get("score") or 0.0)
    generated = _format_blank_segments_from_line(raw_text, score_value)
    if generated:
        return generated.split()
    return []


def _should_preserve_circled_child_as_subquestion(node: Dict) -> bool:
    raw_text = normalize_line(str(node.get("rawText") or ""))
    if not raw_text:
        return False
    body = normalize_line(re.sub(rf"^\s*{CIRCLED_MARKER_CLASS}\s*", "", raw_text, count=1))
    if not body:
        return False
    if node.get("children"):
        return True
    cjk_count = len(re.findall(r"[\u4e00-\u9fa5]", body))
    # 带有较完整题干的圈号行应保留为独立子问，避免被压平成父级空位。
    if cjk_count >= 6 and bool(_collect_blank_segments(body)):
        return True
    return False


def _flatten_circled_children_under_numeric_nodes(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _flatten_circled_children_under_numeric_nodes(children)

        children = node.get("children", [])
        parent_level = int(node.get("level", 1))
        parent_token = str(node.get("_tokenType") or "")
        if not children or not _is_numeric_outline_parent(node):
            continue
        if parent_token != "paren_arabic" and parent_level < 3:
            continue

        merged_children: List[Dict] = []
        merged_blank_tokens = str(node.get("blankText") or "").strip().split()
        changed = False

        for child in children:
            if str(child.get("_tokenType") or "") != "circled":
                merged_children.append(child)
                continue
            if _should_preserve_circled_child_as_subquestion(child):
                merged_children.append(child)
                continue

            changed = True
            child_blank_tokens = _collect_leaf_blank_tokens(child)
            if child_blank_tokens:
                merged_blank_tokens.extend(child_blank_tokens)
                continue

            for grand in child.get("children", []):
                _decrease_outline_levels(grand, 1)
                merged_children.append(grand)

        if not changed:
            continue

        node["children"] = merged_children
        if merged_blank_tokens:
            node["blankText"] = " ".join(merged_blank_tokens)


def _collapse_choice_question_multi_blanks(
    nodes: List[Dict],
    under_choice_root: bool = False,
) -> None:
    for node in nodes:
        node_title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        node_is_choice_root = bool(
            int(node.get("level", 1)) == 1 and _is_choice_root_title(node_title)
        )
        current_under_choice = under_choice_root or node_is_choice_root

        children = node.get("children", [])
        if children:
            _collapse_choice_question_multi_blanks(children, current_under_choice)

        if not current_under_choice or children:
            continue

        token_type = str(node.get("_tokenType") or "")
        if token_type not in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
            continue

        raw_text = str(node.get("rawText") or "")
        blank_text = str(node.get("blankText") or "").strip()
        inline_option_count = len(INLINE_OPTION_MARKER_RE.findall(raw_text))
        is_inline_choice_stem = inline_option_count >= 2
        underline_count = len(_collect_blank_segments(raw_text))
        blank_token_count = len(blank_text.split()) if blank_text else 0
        has_choice_tail_bracket = bool(EMPTY_BRACKET_RE.search(raw_text))
        should_collapse = (
            underline_count > 1
            or (underline_count >= 1 and has_choice_tail_bracket)
            or blank_token_count > 1
        )
        if not current_under_choice and not is_inline_choice_stem:
            continue
        if not should_collapse:
            continue

        score_value = float(node.get("score") or 0.0)
        node["blankText"] = f"____{_format_outline_score_text(_normalize_score_value(score_value))}"


def _collapse_choice_semantic_leaf_multi_blanks(nodes: List[Dict]) -> None:
    if not nodes:
        return

    choice_semantic_re = re.compile(
        r"(?:正确的一项|不正确的一项|符合题意|不符合题意|下列选项|选项中|最恰当|有语病)"
    )
    for node in nodes:
        children = node.get("children", [])
        if children:
            _collapse_choice_semantic_leaf_multi_blanks(children)
            continue

        raw_text = normalize_line(str(node.get("rawText") or ""))
        if not raw_text or not choice_semantic_re.search(raw_text):
            continue

        blank_text = str(node.get("blankText") or "").strip()
        if not blank_text:
            continue
        tokens = blank_text.split()
        if len(tokens) <= 1:
            continue

        score_value = float(node.get("score") or 0.0)
        if score_value > 0:
            node["blankText"] = f"____{_format_outline_score_text(float(_normalize_score_value(score_value)))}"
        else:
            node["blankText"] = tokens[0]


def _enforce_choice_question_no_blank_and_no_children(
    nodes: List[Dict],
    under_choice_root: bool = False,
) -> None:
    for node in nodes:
        node_title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        node_is_choice_root = bool(
            int(node.get("level", 1)) == 1 and _is_choice_root_title(node_title)
        )
        current_under_choice = under_choice_root or node_is_choice_root

        children = node.get("children", [])
        if children:
            _enforce_choice_question_no_blank_and_no_children(children, current_under_choice)

        if not current_under_choice:
            continue

        token_type = str(node.get("_tokenType") or "")
        numbering_value = _parse_ascii_int(node.get("numbering"))
        level_value = int(node.get("level", 1))
        is_choice_question_node = bool(
            level_value >= 2
            and (
                token_type in {"arabic", "arabic_loose", "arabic_bare", "decimal"}
                or numbering_value is not None
            )
        )
        if not is_choice_question_node:
            continue

        raw_text = str(node.get("rawText") or "")
        real_underline_segments = _collect_blank_segments(raw_text)
        underline_segments = []
        if real_underline_segments:
            underline_segments = _build_scored_underline_segments(
                raw_text,
                float(node.get("score") or 0.0),
            )

        # 选择题题干默认不抽空位；但若题干中存在真实下划线，只保留一个。
        if underline_segments:
            underline_text, underline_score = underline_segments[0]
            node["blankText"] = f"{underline_text}{_format_outline_score_text(float(_normalize_score_value(underline_score)))}"
        else:
            node["blankText"] = ""


def _collapse_statement_option_paren_children(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _collapse_statement_option_paren_children(children)

        children = node.get("children", [])
        if len(children) < 2:
            continue

        parent_token = str(node.get("_tokenType") or "")
        if parent_token not in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
            continue
        if bool(node.get("_isSectionHeading")):
            continue
        parent_level = int(node.get("level", 1))
        parent_score = float(node.get("score") or 0.0)
        if parent_level == 1 and parent_score >= 8:
            # 一级高分节点通常是大题/题型分节，不能把其下正常题号误折叠。
            continue
        if any(child.get("children") for child in children):
            continue
        if all(float(child.get("score") or 0.0) > 0 for child in children):
            # 子问本身都已有显式分值时，保留原始层级，避免把真实小题错误压平到父级。
            continue

        child_numberings = [str(child.get("numbering") or "").strip() for child in children]
        if not all(re.fullmatch(r"\d{1,2}", numbering or "") for numbering in child_numberings):
            continue
        if child_numberings[0] != "1":
            continue

        parent_text = normalize_line(str(node.get("rawText") or node.get("title") or ""))
        child_texts = [
            normalize_line(str(child.get("rawText") or child.get("title") or ""))
            for child in children
        ]
        if any(not text for text in child_texts):
            continue
        avg_child_len = sum(len(text) for text in child_texts) / float(len(child_texts))
        if avg_child_len >= 56:
            continue
        if any(re.search(r"[？?]", text) for text in child_texts):
            continue
        if not (
            STATEMENT_OPTION_COLLAPSE_HINT_RE.search(parent_text)
            or any(STATEMENT_OPTION_COLLAPSE_HINT_RE.search(text) for text in child_texts)
        ):
            continue

        merged_raw = normalize_line(
            " ".join(
                part
                for part in [str(node.get("rawText") or "")] + [str(child.get("rawText") or "") for child in children]
                if part
            )
        )
        if not merged_raw:
            continue

        node["rawText"] = merged_raw
        score_value = float(node.get("score") or 0.0)
        node["blankText"] = _format_blank_segments_from_line(merged_raw, score_value)


def _is_slot_like_leaf_node(node: Dict) -> bool:
    if node.get("children"):
        return False

    raw = str(node.get("rawText") or "")
    title = str(node.get("title") or "")
    blank_text = str(node.get("blankText") or "")
    source_text = " ".join(part for part in [raw, title] if part).strip()
    probe_text = source_text or blank_text
    if not probe_text:
        return False
    has_underline = bool(_collect_blank_segments(source_text))
    has_empty_bracket = bool(EMPTY_BRACKET_RE.search(source_text))
    # 规则说明：下划线与括号空提取的逻辑约束。
    # 规则说明：下划线与括号空提取（示例：_longAnswerUnderline）的返回策略。
    return has_empty_bracket and not has_underline


def _has_slot_marker(node: Dict) -> bool:
    if bool(node.get("_suppressChoiceStemBlank")):
        return False
    if bool(node.get("_longAnswerUnderline")):
        return True
    raw = str(node.get("rawText") or "")
    title = str(node.get("title") or "")
    blank_text = str(node.get("blankText") or "")
    source = " ".join(part for part in [raw, title, blank_text] if part).strip()
    if not source:
        return False
    if _collect_blank_segments(source):
        return True
    if EMPTY_BRACKET_RE.search(source):
        return True
    if re.search(r"[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]", source):
        return True
    return False


def _should_preserve_choice_stub_bracket(raw_text: str, token_type: str) -> bool:
    normalized = normalize_line(raw_text or "")
    if not normalized:
        return False
    if token_type not in {"arabic", "arabic_loose", "arabic_bare"}:
        return False
    if not re.match(r"^\s*[\uFF08(]\s*[\uFF09)]\s*\d{1,4}\s*[\u3001\.\uFF0E]", normalized):
        return False
    return bool(NUMERIC_OPTION_STUB_HEADING_RE.match(normalized))


def _format_outline_score_text(score: float) -> str:
    value = int(score) if int(score) == score else round(score, 2)
    return f"\uFF08{value}\u5206\uFF09"


def _count_node_slot_markers(node: Dict) -> int:
    children = node.get("children", [])
    if children:
        return sum(_count_node_slot_markers(child) for child in children)
    if bool(node.get("_suppressChoiceStemBlank")):
        return 0

    raw_text = str(node.get("rawText") or "")
    blank_text = str(node.get("blankText") or "")
    source = raw_text if raw_text else blank_text

    underline_segments = _collect_blank_segments(source)
    if underline_segments:
        return len(underline_segments)

    bracket_matches = list(EMPTY_BRACKET_RE.finditer(source))
    if bracket_matches:
        return len(bracket_matches)

    # 规则说明：下划线与括号空提取的条件过滤。
    if blank_text:
        fallback_segments = _collect_blank_segments(blank_text)
        if fallback_segments:
            return len(fallback_segments)
    return 0


def _count_text_slot_markers(text: str) -> int:
    source = str(text or "")
    if not source:
        return 0

    slot_positions: set[int] = set()
    for _, start in _collect_blank_segments(source):
        slot_positions.add(int(start))
    for _, start in _collect_empty_bracket_slot_segments(source):
        slot_positions.add(int(start))

    if slot_positions:
        return len(slot_positions)

    return len(_collect_question_mark_placeholder_segments(source))


def _expand_per_item_unit_scores(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _expand_per_item_unit_scores(children)

        unit = node.get("_perItemUnitScore")
        if unit is None:
            continue
        if not children:
            continue

        unit_value = float(unit)
        if unit_value <= 0:
            continue

        slot_counts = [_count_node_slot_markers(child) for child in children]
        total_slots = sum(slot_counts)
        if total_slots <= 1:
            continue

        current_score = float(node.get("score") or 0.0)
        inferred_total = _normalize_score_value(unit_value * total_slots)
        # 规则说明：分数提取与分配的逻辑约束。
        # 规则说明：分数提取与分配的条件过滤。
        if current_score <= unit_value + 0.01:
            node["score"] = inferred_total
            current_score = float(inferred_total)

        if current_score <= 0:
            continue

        if not all((child.get("score") is None or float(child.get("score") or 0) <= 0) for child in children):
            continue

        assigned_total = 0.0
        for idx, child in enumerate(children):
            slot_count = slot_counts[idx]
            if slot_count <= 0:
                continue
            child_score = _normalize_score_value(unit_value * slot_count)
            child["score"] = child_score
            assigned_total = round(assigned_total + float(child_score), 2)
            if not child.get("children") and _has_slot_marker(child):
                _apply_assigned_score_to_outline_leaf(child, float(child_score))

        diff = round(current_score - assigned_total, 2)
        if abs(diff) > 0.01:
            last_scored = next(
                (
                    child
                    for child, slot_count in reversed(list(zip(children, slot_counts)))
                    if slot_count > 0 and child.get("score") is not None
                ),
                None,
            )
            if last_scored is not None:
                last_scored_score = float(last_scored.get("score") or 0.0)
                adjusted = _normalize_score_value(last_scored_score + diff)
                last_scored["score"] = adjusted
                if not last_scored.get("children") and _has_slot_marker(last_scored):
                    _apply_assigned_score_to_outline_leaf(last_scored, float(adjusted))


def _outline_display_score(node: Dict) -> float:
    children = node.get("children", [])
    if children:
        return sum(_outline_display_score(child) for child in children)
    score = node.get("score")
    if score is None:
        return 0.0
    return float(score) if float(score) > 0 else 0.0


def _collect_zero_slot_leaves_in_order(node: Dict) -> List[Dict]:
    children = node.get("children", [])
    if not children:
        score = node.get("score")
        score_value = float(score) if score is not None else 0.0
        if score_value > 0:
            return []
        if not _has_slot_marker(node):
            return []
        return [node]

    leaves: List[Dict] = []
    for child in children:
        leaves.extend(_collect_zero_slot_leaves_in_order(child))
    return leaves


def _apply_assigned_score_to_outline_leaf(leaf: Dict, assigned_score: float) -> None:
    score_value = _normalize_score_value(float(assigned_score))
    leaf["score"] = score_value

    if bool(leaf.get("_suppressChoiceStemBlank")):
        leaf["blankText"] = ""
        return

    if bool(leaf.get("_longAnswerUnderline")):
        leaf["blankText"] = ""
        return

    existing_blank_tokens = str(leaf.get("blankText") or "").strip().split()
    if existing_blank_tokens:
        leaf["blankText"] = " ".join(
            _rebalance_merged_blank_segments(existing_blank_tokens, float(score_value))
        )
        return

    raw_text = str(leaf.get("rawText") or "")
    if _collect_blank_segments(raw_text):
        leaf["blankText"] = _format_blank_segments_from_line(raw_text, float(score_value))
        return

    if EMPTY_BRACKET_RE.search(raw_text):
        leaf_token_type = str(leaf.get("_tokenType") or "")
        bracket_count = len(list(EMPTY_BRACKET_RE.finditer(raw_text)))
        if leaf_token_type == "paren_arabic" and bracket_count <= 1:
            leaf["blankText"] = ""
        else:
            count = max(1, bracket_count)
            total = float(score_value)
            base = round(total / count, 2)
            assigned = [base for _ in range(count)]
            diff = round(total - base * count, 2)
            assigned[-1] = round(assigned[-1] + diff, 2)
            leaf["blankText"] = " ".join(
                f"____{_format_outline_score_text(float(_normalize_score_value(item_score)))}"
                for item_score in assigned
            )
        return

    leaf["blankText"] = f"____{_format_outline_score_text(float(score_value))}"


def _distribute_outline_parent_score_gap_to_slot_leaves(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _distribute_outline_parent_score_gap_to_slot_leaves(children)

        if not children:
            continue

        explicit_score = node.get("score")
        if explicit_score is None or float(explicit_score) <= 0:
            continue

        child_display_total = sum(_outline_display_score(child) for child in children)
        gap = round(float(explicit_score) - child_display_total, 2)
        if gap <= 0:
            continue

        zero_slot_leaves: List[Dict] = []
        for child in children:
            zero_slot_leaves.extend(_collect_zero_slot_leaves_in_order(child))
        if len(zero_slot_leaves) < 3:
            continue

        remaining = gap
        for leaf in zero_slot_leaves:
            if remaining <= 0:
                break
            assign = 1.0 if remaining >= 1.0 else remaining
            _apply_assigned_score_to_outline_leaf(leaf, assign)
            remaining = round(remaining - assign, 2)


def _distribute_outline_parent_score_to_slot_children(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            explicit_score = node.get("score")
            if explicit_score is not None and float(explicit_score) > 0:
                if (
                    all(not child.get("children") for child in children)
                    and all((child.get("score") is None or float(child.get("score") or 0) <= 0) for child in children)
                    and all(_has_slot_marker(child) for child in children)
                ):
                    total = float(explicit_score)
                    slot_counts = [_count_node_slot_markers(child) for child in children]
                    total_slots = sum(slot_counts)
                    # 规则说明：分数提取与分配的逻辑约束。
                    # 规则说明：分数提取与分配的条件过滤。
                    if (
                        total_slots > 0
                        and all(count > 0 for count in slot_counts)
                        and abs(total - float(total_slots)) <= 0.01
                    ):
                        assigned = [float(count) for count in slot_counts]
                    else:
                        count = len(children)
                        base = round(total / count, 2)
                        assigned = [base for _ in range(count)]
                        diff = round(total - base * count, 2)
                        assigned[-1] = round(assigned[-1] + diff, 2)

                    for idx, child in enumerate(children):
                        child_score = _normalize_score_value(float(assigned[idx]))
                        child["score"] = child_score

                        if bool(child.get("_longAnswerUnderline")):
                            # 规则说明：下划线与括号空提取（示例：_longAnswerUnderline）的规则定义。
                            child["blankText"] = ""
                            continue

                        raw_text = str(child.get("rawText") or "")
                        has_underline = bool(_collect_blank_segments(raw_text))
                        has_empty_bracket = bool(EMPTY_BRACKET_RE.search(raw_text))
                        existing_blank_tokens = str(child.get("blankText") or "").strip().split()
                        if existing_blank_tokens:
                            child["blankText"] = " ".join(
                                _rebalance_merged_blank_segments(existing_blank_tokens, float(child_score))
                            )
                        elif has_underline:
                            child["blankText"] = _format_blank_segments_from_line(raw_text, float(child_score))
                        elif has_empty_bracket:
                            child_token_type = str(child.get("_tokenType") or "")
                            if child_token_type == "paren_arabic":
                                # “(1)/(2)”单空括号子问只保留分值，不生成 blankText，
                                # 避免前端把它再渲染成额外空位行。
                                bracket_count = len(list(EMPTY_BRACKET_RE.finditer(raw_text)))
                                if bracket_count <= 1:
                                    child["blankText"] = ""
                                else:
                                    generated_blank_text = _format_blank_segments_from_line(
                                        raw_text,
                                        float(child_score),
                                    )
                                    child["blankText"] = generated_blank_text
                            else:
                                child["blankText"] = f"____{_format_outline_score_text(float(child_score))}"
                        elif not str(child.get("blankText") or "").strip():
                            child["blankText"] = f"____{_format_outline_score_text(float(child_score))}"

            _distribute_outline_parent_score_to_slot_children(children)


def _is_zero_numbered_text_child(node: Dict) -> bool:
    if node.get("children"):
        return False
    if node.get("score") is not None and float(node.get("score") or 0) > 0:
        return False

    token_type = str(node.get("_tokenType") or "")
    if token_type not in {"paren_arabic", "circled"}:
        return False

    raw_text = str(node.get("rawText") or "")
    if _collect_blank_segments(raw_text):
        return False
    if EMPTY_BRACKET_RE.search(raw_text):
        return False
    return True


def _distribute_outline_parent_score_to_numbered_zero_children(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            explicit_score = node.get("score")
            parent_token_type = str(node.get("_tokenType") or "")
            parent_text = normalize_line(str(node.get("title") or node.get("rawText") or ""))
            if (
                explicit_score is not None
                and float(explicit_score) > 0
                and parent_token_type in {"arabic", "arabic_loose", "arabic_bare", "paren_arabic", "decimal"}
                and bool(ZERO_CHILD_SCORE_DISTRIBUTION_PARENT_HINT_RE.search(parent_text))
                and len(children) >= 2
                and all((child.get("score") is None or float(child.get("score") or 0) <= 0) for child in children)
                and all(_is_zero_numbered_text_child(child) for child in children)
            ):
                total = float(explicit_score)
                count = len(children)
                base = round(total / count, 2)
                assigned = [base for _ in range(count)]
                diff = round(total - base * count, 2)
                assigned[-1] = round(assigned[-1] + diff, 2)
                for idx, child in enumerate(children):
                    child["score"] = _normalize_score_value(float(assigned[idx]))

            _distribute_outline_parent_score_to_numbered_zero_children(children)


def _fill_scored_empty_bracket_leaf_blank_text(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _fill_scored_empty_bracket_leaf_blank_text(children)
            continue

        explicit_score = node.get("score")
        if explicit_score is None or float(explicit_score) <= 0:
            continue
        if bool(node.get("_suppressChoiceStemBlank")):
            node["blankText"] = ""
            continue
        if str(node.get("blankText") or "").strip():
            continue

        raw_text = str(node.get("rawText") or "")
        if not raw_text:
            continue
        if _collect_blank_segments(raw_text):
            continue

        bracket_matches = list(EMPTY_BRACKET_RE.finditer(raw_text))
        if not bracket_matches:
            continue

        token_type = str(node.get("_tokenType") or "")
        if token_type == "paren_arabic" and len(bracket_matches) <= 1:
            # 单个“(1) ...（ ）”子问不生成 blankText，避免被渲染成额外空位行。
            node["blankText"] = ""
            continue

        count = len(bracket_matches)
        total = float(explicit_score)
        base = round(total / count, 2)
        assigned = [base for _ in range(count)]
        diff = round(total - base * count, 2)
        assigned[-1] = round(assigned[-1] + diff, 2)

        node["blankText"] = " ".join(
            f"____{_format_outline_score_text(float(_normalize_score_value(score_value)))}"
            for score_value in assigned
        )

def _fill_scored_underline_leaf_blank_text(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _fill_scored_underline_leaf_blank_text(children)
            continue

        explicit_score = node.get("score")
        if explicit_score is None or float(explicit_score) <= 0:
            continue
        if bool(node.get("_suppressChoiceStemBlank")):
            node["blankText"] = ""
            continue
        if str(node.get("blankText") or "").strip():
            continue

        raw_text = str(node.get("rawText") or "")
        title_text = str(node.get("title") or "")
        source_text = raw_text
        raw_has_slots = bool(_collect_blank_segments(raw_text) or EMPTY_BRACKET_RE.search(raw_text))
        title_has_underlines = bool(_collect_blank_segments(title_text))
        if ((not source_text) or (not raw_has_slots and title_has_underlines)) and title_text:
            source_text = title_text
        if not source_text:
            continue

        # 先用标准分段逻辑，若因引号/语境过滤未命中，再做保底分配。
        source_for_blank = source_text
        if QUOTED_UNDERLINE_RE.search(source_for_blank) and QUOTED_UNDERLINE_INSTRUCTION_HINT_RE.search(
            source_for_blank
        ):
            source_for_blank = normalize_line(QUOTED_UNDERLINE_RE.sub("", source_for_blank))

        generated = _format_blank_segments_from_line(source_for_blank, float(explicit_score))
        if generated:
            node["blankText"] = generated
            continue

        # 引号中的说明型下划线（如“用‘____’画出...”）不作为真实空位。
        if QUOTED_UNDERLINE_RE.search(source_text) and QUOTED_UNDERLINE_INSTRUCTION_HINT_RE.search(source_text):
            node["blankText"] = ""
            continue

        merged_segments = _collect_blank_segments(source_for_blank)
        underline_tokens = [segment for segment, _ in merged_segments]
        if not underline_tokens:
            underline_tokens = [match.group(0) for match in UNDERLINE_RE.finditer(source_for_blank)]
        if not underline_tokens:
            continue

        total = float(explicit_score)
        count = len(underline_tokens)
        base = round(total / count, 2)
        assigned = [base for _ in range(count)]
        diff = round(total - base * count, 2)
        assigned[-1] = round(assigned[-1] + diff, 2)

        node["blankText"] = " ".join(
            f"{underline_tokens[idx]}{_format_outline_score_text(float(_normalize_score_value(assigned[idx])))}"
            for idx in range(count)
        )


def _fill_scored_question_mark_placeholder_blank_text(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _fill_scored_question_mark_placeholder_blank_text(children)
            continue

        explicit_score = node.get("score")
        if explicit_score is None or float(explicit_score) <= 0:
            continue
        if str(node.get("blankText") or "").strip():
            continue

        raw_text = str(node.get("rawText") or "")
        if not raw_text:
            continue
        if not _collect_question_mark_placeholder_segments(raw_text):
            continue

        generated = _format_blank_segments_from_line(raw_text, float(explicit_score))
        if generated:
            node["blankText"] = generated

def _strip_instruction_quoted_underlines_from_blank_text(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _strip_instruction_quoted_underlines_from_blank_text(children)
            continue

        source_text = str(node.get("rawText") or node.get("title") or "")
        if not source_text or not QUOTED_UNDERLINE_RE.search(source_text):
            continue
        if not QUOTED_UNDERLINE_INSTRUCTION_HINT_RE.search(source_text):
            continue

        cleaned_source = normalize_line(QUOTED_UNDERLINE_RE.sub("", source_text))
        explicit_score = float(node.get("score") or 0.0)
        if explicit_score <= 0:
            node["blankText"] = ""
            continue

        generated = _format_blank_segments_from_line(cleaned_source, explicit_score)
        node["blankText"] = generated or ""


def _is_distributable_child_for_remaining_score(node: Dict) -> bool:
    if _node_contains_slot_marker(node):
        return True

    children = node.get("children", [])
    if children:
        has_numeric_child = any(str(child.get("numbering") or "").strip() for child in children)
        has_scored_child = any(
            child.get("score") is not None and float(child.get("score") or 0) > 0
            for child in children
        )
        has_slot_descendant = any(_node_contains_slot_marker(child) for child in children)
        return bool(has_numeric_child or has_scored_child or has_slot_descendant)

    numbering = str(node.get("numbering") or "").strip()

    source_text = normalize_line(str(node.get("rawText") or node.get("title") or ""))
    if not source_text:
        return False
    if EMPTY_BRACKET_RE.search(source_text) or _collect_blank_segments(source_text):
        return True

    token_type = str(node.get("_tokenType") or "")
    has_question_semantic = bool(
        QUESTION_DIRECTIVE_HINT_RE.search(source_text)
        or re.search(r"[？?]", source_text)
    )
    if numbering:
        # 有明确题号时默认按题目处理，不因“要求”字样直接排除。
        # 仅对纯短标题型“作文要求/写作要求”继续视为说明项。
        if _is_writing_requirement_text(source_text):
            compact = re.sub(r"\s+", "", source_text)
            if re.match(r"^(?:作文要求|写作要求|要求[:：]?)", compact) and len(compact) <= 24:
                return False
        if token_type in {"chinese_paren", "circled"}:
            if _is_material_paragraph_like_text(source_text) and not has_question_semantic:
                return False
        return True

    return False


def _node_contains_slot_marker(node: Dict) -> bool:
    if _has_slot_marker(node):
        return True
    for child in node.get("children", []):
        if _node_contains_slot_marker(child):
            return True
    return False


def _distribute_outline_parent_remaining_score_to_unscored_children(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if not children:
            continue

        explicit_score = node.get("score")
        if explicit_score is not None and float(explicit_score) > 0:
            # 修复“父级总分误落到某一个子问”的场景：
            # 若仅有一个子问分值恰好等于父级总分，且该子问文本没有显式分值标记，
            # 则视为误分配，回退为 0 分后再参与后续均分逻辑。
            positive_children = [
                child for child in children if float(child.get("score") or 0.0) > 0
            ]
            if len(children) >= 2 and len(positive_children) == 1:
                only_positive_child = positive_children[0]
                only_positive_score = float(only_positive_child.get("score") or 0.0)
                parent_total = float(explicit_score)
                if abs(only_positive_score - parent_total) <= 0.01:
                    child_text = normalize_line(
                        str(
                            only_positive_child.get("rawText")
                            or only_positive_child.get("title")
                            or ""
                        )
                    )
                    sibling_candidates = [
                        child for child in children if child is not only_positive_child
                    ]
                    if (
                        child_text
                        and not SCORE_TEXT_RE.search(child_text)
                        and any(
                            _is_distributable_child_for_remaining_score(sibling)
                            for sibling in sibling_candidates
                        )
                    ):
                        only_positive_child["score"] = 0.0
                        if not only_positive_child.get("children"):
                            only_positive_child["blankText"] = ""

            if children:
                scored_total = 0.0
                zero_children: List[Dict] = []
                for child in children:
                    explicit_child_score = child.get("score")
                    explicit_value = (
                        float(explicit_child_score)
                        if explicit_child_score is not None
                        else 0.0
                    )
                    # 规则说明：分数提取与分配的逻辑约束。
                    # 规则说明：分数提取与分配的逻辑约束。
                    # 规则说明：分数提取与分配的规则定义。
                    display_value = _outline_display_score(child)
                    effective_value = explicit_value if explicit_value > 0 else display_value
                    if effective_value > 0:
                        if explicit_value <= 0:
                            child["score"] = _normalize_score_value(float(effective_value))
                        scored_total += effective_value
                        continue
                    if _is_distributable_child_for_remaining_score(child):
                        zero_children.append(child)

                remaining = round(float(explicit_score) - scored_total, 2)
                if zero_children:
                    count = len(zero_children)
                    slot_counts = [_count_node_slot_markers(child) for child in zero_children]
                    total_slots = sum(slot_counts)

                    # 严格按“父级总分 - 已有子级分”分配；剩余<=0时不再强行兜底赋分。
                    if remaining <= 0:
                        _distribute_outline_parent_remaining_score_to_unscored_children(children)
                        continue
                    # 若未评分子树里的“可计分空位总数”与父级剩余分一致，
                    # 则按空位数量分配（等价于每个空 1 分）。
                    if (
                        total_slots > 0
                        and all(slot_count > 0 for slot_count in slot_counts)
                        and abs(float(remaining) - float(total_slots)) <= 0.01
                    ):
                        assigned = [float(slot_count) for slot_count in slot_counts]
                    else:
                        base = round(remaining / count, 2)
                        assigned = [base for _ in range(count)]
                        diff = round(remaining - base * count, 2)
                        assigned[-1] = round(assigned[-1] + diff, 2)

                    for idx, child in enumerate(zero_children):
                        raw_value = float(assigned[idx])
                        if raw_value <= 0:
                            continue
                        score_value = _normalize_score_value(raw_value)
                        child["score"] = score_value
                        if not child.get("children") and _has_slot_marker(child):
                            _apply_assigned_score_to_outline_leaf(child, float(score_value))

        _distribute_outline_parent_remaining_score_to_unscored_children(children)


def _force_fill_zero_child_scores_under_scored_parent(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if not children:
            continue

        explicit_score = node.get("score")
        if explicit_score is not None and float(explicit_score) > 0:
            parent_total = float(explicit_score)
            scored_total = 0.0
            zero_children: List[Dict] = []

            for child in children:
                child_score = float(child.get("score") or 0.0)
                if child_score > 0:
                    scored_total += child_score
                    continue

                child_probe = normalize_line(
                    str(child.get("rawText") or child.get("title") or "")
                )
                if _is_writing_requirement_text(child_probe):
                    continue
                zero_children.append(child)

            if zero_children:
                remaining = round(parent_total - scored_total, 2)
                if remaining > 0:
                    base = round(remaining / len(zero_children), 2)
                    assigned = [base for _ in zero_children]
                    diff = round(remaining - base * len(zero_children), 2)
                    assigned[-1] = round(assigned[-1] + diff, 2)
                else:
                    # 兜底策略：即便已分配总和异常，仍确保 0 分子级获得非 0 分。
                    # 采用“父级总分按子级总数均分”的最小改动补分，避免前端出现 0 分子级。
                    divisor = max(len(children), 1)
                    fallback = round(parent_total / divisor, 2)
                    if fallback <= 0:
                        fallback = 0.01
                    assigned = [fallback for _ in zero_children]

                for idx, child in enumerate(zero_children):
                    assigned_score = _normalize_score_value(float(assigned[idx]))
                    child["score"] = assigned_score
                    if not child.get("children") and _has_slot_marker(child):
                        _apply_assigned_score_to_outline_leaf(child, float(assigned_score))

        _force_fill_zero_child_scores_under_scored_parent(children)


def _rebalance_single_child_full_score_leak(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _rebalance_single_child_full_score_leak(children)

        if len(children) < 2:
            continue

        explicit_score = node.get("score")
        if explicit_score is None or float(explicit_score) <= 0:
            continue
        parent_total = float(explicit_score)

        positive_children = [
            child for child in children if float(child.get("score") or 0.0) > 0
        ]
        if len(positive_children) != 1:
            continue

        leaked_child = positive_children[0]
        leaked_score = float(leaked_child.get("score") or 0.0)
        if abs(leaked_score - parent_total) > 0.01:
            continue

        leaked_text = normalize_line(
            str(leaked_child.get("rawText") or leaked_child.get("title") or "")
        )
        if not leaked_text:
            continue
        if SCORE_TEXT_RE.search(leaked_text):
            continue

        distributable_children = [
            child for child in children if _is_distributable_child_for_remaining_score(child)
        ]
        if len(distributable_children) < 2:
            continue

        leaked_child["score"] = 0.0
        if not leaked_child.get("children"):
            leaked_child["blankText"] = ""

        slot_counts = [_count_node_slot_markers(child) for child in distributable_children]
        total_slots = sum(slot_counts)
        if (
            total_slots > 0
            and all(slot_count > 0 for slot_count in slot_counts)
            and abs(parent_total - float(total_slots)) <= 0.01
        ):
            assigned = [float(slot_count) for slot_count in slot_counts]
        else:
            count = len(distributable_children)
            base = round(parent_total / count, 2)
            assigned = [base for _ in range(count)]
            diff = round(parent_total - base * count, 2)
            assigned[-1] = round(assigned[-1] + diff, 2)

        for idx, child in enumerate(distributable_children):
            score_value = _normalize_score_value(float(assigned[idx]))
            child["score"] = score_value
            if not child.get("children") and _has_slot_marker(child):
                _apply_assigned_score_to_outline_leaf(child, float(score_value))


def normalize_outline_blank_scores(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            normalize_outline_blank_scores(children)

        if children:
            continue

        explicit_score = node.get("score")
        if explicit_score is None or float(explicit_score) <= 0:
            continue

        blank_text = str(node.get("blankText") or "").strip()
        if not blank_text:
            continue

        segments = blank_text.split()
        if not segments:
            continue

        raw_text = str(node.get("rawText") or "")
        raw_slot_count = _count_text_slot_markers(raw_text)
        if raw_slot_count > 0 and len(segments) > raw_slot_count:
            # 仅保留与原题干空位数量一致的 token，避免把相邻题干续行空位并入当前小题。
            segments = segments[:raw_slot_count]
            node["blankText"] = " ".join(segments)

        parsed_scores: List[float] = []
        for token in segments:
            score = _parse_merged_blank_segment_score(token)
            if score is None:
                parsed_scores = []
                break
            parsed_scores.append(float(score))
        if not parsed_scores:
            continue

        total = round(sum(parsed_scores), 2)
        target = round(float(explicit_score), 2)
        has_zero = any(value <= 0 for value in parsed_scores)
        has_positive = any(value > 0 for value in parsed_scores)
        raw_title_text = str(node.get("rawText") or node.get("title") or "").strip()
        score_marker_count = len(_extract_score_with_positions(raw_title_text))
        should_rebalance_mixed = (
            len(parsed_scores) > 1
            and has_zero
            and has_positive
            and score_marker_count < len(parsed_scores)
        )
        if should_rebalance_mixed:
            rebalanced = _rebalance_merged_blank_segments(segments, float(explicit_score))
            node["blankText"] = " ".join(rebalanced)
            continue
        if abs(total - target) <= 0.01:
            continue
        # 当题干未给出逐空分值（或给出的分值标记少于空位数）且当前总分偏差明显时，
        # 统一按父分值回算，避免出现 2.43/3 这类累计误差与历史残留分配。
        if len(parsed_scores) > 1 and score_marker_count < len(parsed_scores):
            rebalanced = _rebalance_merged_blank_segments(segments, float(explicit_score))
            node["blankText"] = " ".join(rebalanced)
            continue
        if not all(value <= 0 for value in parsed_scores):
            continue

        rebalanced = _rebalance_merged_blank_segments(segments, float(explicit_score))
        node["blankText"] = " ".join(rebalanced)


def _normalize_score_value(score: float) -> float:
    if int(score) == score:
        return float(int(score))
    return round(score, 2)


def _is_blank_only_child_node(node: Dict) -> bool:
    if node.get("children"):
        return False

    blank_text = str(node.get("blankText") or "")
    if not _collect_blank_segments(blank_text):
        return False

    title = normalize_line(str(node.get("title") or ""))
    raw_text = normalize_line(str(node.get("rawText") or ""))
    probe = title or raw_text
    if not probe:
        return True

    probe = re.sub(r"^\s*(?:[\uFF08(]?\d{1,4}[\uFF09)]?[\u3001\.\uFF0E]?)\s*", "", probe)
    probe = re.sub(r"[_\uFF3F\uFE4D\uFE4E\u2014]+", "", probe)
    probe = re.sub(r"[\uFF08(]\s*\d+(?:\.\d+)?\s*\u5206\s*[\uFF09)]", "", probe)
    probe = re.sub(r"[\uFF08(]\s*[\uFF09)]", "", probe)
    probe = re.sub(r"[\s\d\u3000\.\u3001\uFF0E:：;；,，\-]+", "", probe)
    return not probe


def _distribute_parent_score_to_blank_children(
    node: Dict,
    child_nodes: List[Dict],
    child_items: List[Dict],
) -> None:
    if not child_nodes or len(child_nodes) != len(child_items):
        return

    explicit_score = node.get("score")
    if explicit_score is None:
        return
    total = float(explicit_score)
    if total <= 0:
        return

    if any(child.get("children") for child in child_nodes):
        return
    if any(child.get("score") is not None and float(child.get("score") or 0) > 0 for child in child_nodes):
        return
    if not all(_is_blank_only_child_node(child) for child in child_nodes):
        return

    count = len(child_items)
    base = round(total / count, 2)
    assigned = [base for _ in range(count)]
    diff = round(total - base * count, 2)
    assigned[-1] = round(assigned[-1] + diff, 2)

    for idx, value in enumerate(assigned):
        child_items[idx]["score"] = _normalize_score_value(float(value))


def _distribute_parent_score_to_zero_children_fallback(
    node: Dict,
    child_nodes: List[Dict],
    child_items: List[Dict],
) -> None:
    if not child_nodes or len(child_nodes) != len(child_items):
        return

    explicit_score = node.get("score")
    if explicit_score is None:
        return
    total = float(explicit_score)
    if total <= 0:
        return

    assigned_total = 0.0
    zero_indexes: List[int] = []
    for idx, child_item in enumerate(child_items):
        child_score = float(child_item.get("score") or 0.0)
        if child_score > 0:
            assigned_total += child_score
            continue

        child_text = normalize_line(
            str(child_nodes[idx].get("rawText") or child_nodes[idx].get("title") or "")
        )
        child_numbering = str(child_nodes[idx].get("numbering") or "").strip()
        # 作文提示/材料说明不参与该兜底补分；
        # 但“有明确题号”的子题（例如“20. ...（要求：...）”）必须参与补分。
        if _is_writing_requirement_text(child_text) and not child_numbering:
            continue
        zero_indexes.append(idx)

    if not zero_indexes:
        return

    remaining = round(total - assigned_total, 2)
    if remaining <= 0:
        return

    count = len(zero_indexes)
    base = round(remaining / count, 2)
    assigned = [base for _ in range(count)]
    diff = round(remaining - base * count, 2)
    assigned[-1] = round(assigned[-1] + diff, 2)

    for local_idx, child_idx in enumerate(zero_indexes):
        child_items[child_idx]["score"] = _normalize_score_value(float(assigned[local_idx]))



def _normalize_mixed_root_numbering_to_chinese(roots: List[Dict]) -> None:
    if not roots:
        return
    level1_nodes = [node for node in roots if int(node.get("level", 1)) == 1]
    if len(level1_nodes) < 3:
        return

    parsed: List[Tuple[str, Optional[int], Dict]] = []
    for node in level1_nodes:
        numbering = str(node.get("numbering") or "").strip()
        token_type = str(node.get("_tokenType") or "")
        arabic_value = _parse_ascii_int(numbering)
        chinese_value = _parse_simple_chinese_int(numbering)
        if arabic_value is not None and token_type in {"arabic", "arabic_loose", "arabic_bare"}:
            parsed.append(("arabic", arabic_value, node))
        elif chinese_value is not None and token_type in {"chinese", "chinese_loose"}:
            parsed.append(("chinese", chinese_value, node))
        else:
            parsed.append(("other", None, node))

    first_chinese_idx: Optional[int] = None
    first_chinese_value: Optional[int] = None
    for idx, (kind, value, _) in enumerate(parsed):
        if kind == "chinese" and value is not None and value >= 2:
            first_chinese_idx = idx
            first_chinese_value = value
            break
    if first_chinese_idx is None or first_chinese_value is None:
        return
    if first_chinese_value <= 1:
        return
    if first_chinese_idx != first_chinese_value - 1:
        return

    can_promote_prefix = True
    for idx in range(first_chinese_idx):
        kind, value, _ = parsed[idx]
        expected = idx + 1
        if kind != "arabic" or value != expected:
            can_promote_prefix = False
            break
    if can_promote_prefix:
        for idx in range(first_chinese_idx):
            _, _, node = parsed[idx]
            expected = idx + 1
            node["numbering"] = _to_simple_chinese_number(expected)
            node["_tokenType"] = "chinese"

    # 规则说明：题号与层级识别（示例：_tokenType）的逻辑约束。
    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的逻辑约束。
    # 规则说明：题号与层级识别的规则定义。
    indexed_roots: List[Tuple[int, str, Dict]] = []
    arabic_nodes: List[Tuple[int, Dict]] = []
    chinese_count = 0
    for node in level1_nodes:
        numbering = str(node.get("numbering") or "").strip()
        token_type = str(node.get("_tokenType") or "")
        value: Optional[int]
        kind: str
        arabic_value = _parse_ascii_int(numbering)
        chinese_value = _parse_simple_chinese_int(numbering)
        if arabic_value is not None and token_type in {"arabic", "arabic_loose", "arabic_bare"}:
            value = arabic_value
            kind = "arabic"
        elif chinese_value is not None and token_type in {"chinese", "chinese_loose"}:
            value = chinese_value
            kind = "chinese"
        else:
            return
        indexed_roots.append((value, kind, node))
        if kind == "arabic":
            arabic_nodes.append((value, node))
        else:
            chinese_count += 1

    if not arabic_nodes or chinese_count < 2:
        return
    if indexed_roots[0][1] != "chinese":
        return

    values = [value for value, _, _ in indexed_roots]
    if not values or values[0] != 1:
        return
    expected_values = list(range(1, len(values) + 1))
    if values != expected_values:
        return

    for value, node in arabic_nodes:
        node["numbering"] = _to_simple_chinese_number(value)
        node["_tokenType"] = "chinese"


def _normalize_nonincreasing_chinese_root_numbering(roots: List[Dict]) -> None:
    if not roots:
        return

    level1_nodes = [node for node in roots if int(node.get("level", 1)) == 1]
    if len(level1_nodes) < 2:
        return

    parsed: List[Tuple[Dict, int]] = []
    for node in level1_nodes:
        token_type = str(node.get("_tokenType") or "")
        numbering = str(node.get("numbering") or "").strip()
        value = _parse_simple_chinese_int(numbering)
        if value is None or token_type not in {"chinese", "chinese_loose"}:
            return
        parsed.append((node, value))

    prev_value = parsed[0][1]
    if prev_value <= 0:
        return

    for node, value in parsed[1:]:
        if value > prev_value:
            prev_value = value
            continue

        node_title = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        # 作文/写作段常出现在阅读分块之后，原编号可能回落，按原文保留。
        if WRITING_SECTION_TITLE_RE.search(node_title):
            prev_value = value
            continue

        corrected_value = prev_value + 1
        corrected_numbering = _to_simple_chinese_number(corrected_value)
        node["numbering"] = corrected_numbering
        node["_tokenType"] = "chinese"

        for field in ("rawText", "title"):
            field_text = str(node.get(field) or "")
            if not field_text:
                continue
            updated = re.sub(
                rf"^\s*{CHINESE_NUM_RE}(?=\s*[、\.\uFF0E])",
                corrected_numbering,
                field_text,
                count=1,
            )
            if updated != field_text:
                node[field] = updated

        prev_value = corrected_value


def _normalize_sparse_chinese_root_numbering(roots: List[Dict]) -> None:
    if not roots:
        return

    level1_nodes = [node for node in roots if int(node.get("level", 1)) == 1]
    if len(level1_nodes) < 2:
        return

    parsed: List[Tuple[Dict, int]] = []
    for node in level1_nodes:
        token_type = str(node.get("_tokenType") or "")
        numbering = str(node.get("numbering") or "").strip()
        value = _parse_simple_chinese_int(numbering)
        if value is None or token_type not in {"chinese", "chinese_loose"}:
            return
        parsed.append((node, value))

    if parsed[0][1] != 1:
        return

    has_gap = False
    prev = parsed[0][1]
    for _, value in parsed[1:]:
        if value <= prev:
            return
        if value != prev + 1:
            has_gap = True
        prev = value
    if not has_gap:
        return

    for idx, (node, _) in enumerate(parsed, start=1):
        new_numbering = _to_simple_chinese_number(idx)
        node["numbering"] = new_numbering
        node["_tokenType"] = "chinese"
        for field in ("rawText", "title"):
            field_text = str(node.get(field) or "")
            if not field_text:
                continue
            updated = re.sub(
                rf"^\s*{CHINESE_NUM_RE}(?=\s*[、\.\uFF0E])",
                new_numbering,
                field_text,
                count=1,
            )
            if updated != field_text:
                node[field] = updated


def _normalize_mixed_paren_section_numbering_to_chinese(nodes: List[Dict]) -> None:
    if not nodes:
        return

    for node in nodes:
        parent_text = normalize_line(str(node.get("title") or node.get("rawText") or ""))
        children = node.get("children", [])
        if not children:
            continue

        candidates: List[Tuple[Dict, int, str]] = []
        has_chinese = False
        has_arabic = False

        for child in children:
            token_type = str(child.get("_tokenType") or "")
            # 规则说明：题号与层级识别（示例：_tokenType）的逻辑约束。
            # 规则说明：题号与层级识别（示例：_tokenType）的条件过滤。
            if not (bool(child.get("_isSectionHeading")) or child.get("children")):
                continue

            if token_type == "chinese_paren":
                value = _parse_simple_chinese_int(child.get("numbering"))
                if value is None:
                    continue
                candidates.append((child, value, "chinese"))
                has_chinese = True
                continue

            if token_type == "paren_arabic":
                value = _parse_ascii_int(child.get("numbering"))
                if value is None:
                    continue
                candidates.append((child, value, "arabic"))
                has_arabic = True

        if (
            has_chinese
            and has_arabic
            and len(candidates) >= 2
            and not (READING_MATERIAL_PARENT_HINT_RE.search(parent_text) or "\u9605\u8bfb" in parent_text)
        ):
            expected = 1
            contiguous = True
            for _, value, _ in candidates:
                if value != expected:
                    contiguous = False
                    break
                expected += 1

            if contiguous:
                for child, value, _ in candidates:
                    child["numbering"] = _to_simple_chinese_number(value)
                    child["_tokenType"] = "chinese_paren"
                    raw_text = str(child.get("rawText") or "")
                    if raw_text:
                        child["rawText"] = re.sub(
                            r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]",
                            f"\uFF08{_to_simple_chinese_number(value)}\uFF09",
                            raw_text,
                            count=1,
                        )

        _normalize_mixed_paren_section_numbering_to_chinese(children)



def _repair_embedded_paren_subquestion_fragments(nodes: List[Dict]) -> None:
    if not nodes:
        return

    compiled_score_patterns = compile_score_patterns(None)
    embedded_marker_re = re.compile(r"\s+[\uFF08(]\s*(\d{1,3})\s*[\uFF09)]")

    idx = 0
    while idx < len(nodes):
        node = nodes[idx]
        children = node.get("children", []) or []
        if children:
            _repair_embedded_paren_subquestion_fragments(children)

        raw_text = normalize_line(str(node.get("rawText") or ""))
        if not raw_text:
            idx += 1
            continue

        node_number = _parse_ascii_int(node.get("numbering"))
        matches = list(embedded_marker_re.finditer(raw_text))
        if not matches:
            idx += 1
            continue

        repaired = False
        for match in matches:
            marker_value = _parse_ascii_int(match.group(1))
            if marker_value is None:
                continue
            split_at = match.start()
            if split_at <= 0:
                continue

            head = normalize_line(raw_text[:split_at])
            tail = normalize_line(raw_text[split_at:].lstrip())
            if not head or not tail:
                continue
            if not SCORE_TEXT_RE.search(head):
                continue

            tail_has_slot = bool(_collect_blank_segments(tail) or EMPTY_BRACKET_RE.search(tail))
            tail_has_score = bool(SCORE_TEXT_RE.search(tail))
            tail_is_material_like = _is_material_paragraph_like_text(tail)

            # 先裁剪当前节点，避免后续把下一问正文误并入。
            node["rawText"] = head
            node["title"] = normalize_line(
                re.sub(r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]\s*", "", head, count=1)
            )
            if not node.get("children"):
                head_score = extract_score_from_text(head, compiled_score_patterns)
                if head_score is not None:
                    node["score"] = head_score
                score_for_blank = float(node.get("score") or 0.0)
                node["blankText"] = _format_blank_segments_from_line(head, score_for_blank)

            # 若尾段本身像独立小问（有分值+空位且编号回退），补回一个同级子问节点。
            if (
                node_number is not None
                and marker_value < node_number
                and tail_has_slot
                and tail_has_score
            ):
                sibling_score = extract_score_from_text(tail, compiled_score_patterns)
                sibling_raw = tail
                sibling_title = normalize_line(
                    re.sub(r"^\s*[\uFF08(]\s*\d{1,3}\s*[\uFF09)]\s*", "", sibling_raw, count=1)
                )
                sibling_blank = _format_blank_segments_from_line(
                    sibling_raw,
                    float(sibling_score) if sibling_score is not None else 0.0,
                )
                sibling_node = {
                    "lineNumber": int(node.get("lineNumber") or 0),
                    "level": int(node.get("level") or 1),
                    "numbering": str(marker_value),
                    "title": sibling_title,
                    "rawText": sibling_raw,
                    "blankText": sibling_blank,
                    "score": sibling_score,
                    "_tokenType": "paren_arabic",
                    "_isSectionHeading": False,
                    "_bindSectionChildren": False,
                    "children": [],
                }
                nodes.insert(idx, sibling_node)
                idx += 1
            elif tail_is_material_like:
                # 尾段是材料正文时直接丢弃尾段，不回灌到结构节点。
                pass
            repaired = True
            break

        if not repaired:
            idx += 1
            continue
        idx += 1


def _prune_empty_paper_volume_nodes(nodes: List[Dict]) -> None:
    if not nodes:
        return

    kept: List[Dict] = []
    for node in nodes:
        children = node.get("children", [])
        _prune_empty_paper_volume_nodes(children)
        token_type = str(node.get("_tokenType") or "")
        score = float(node.get("score") or 0)
        if token_type == "paper_volume" and not children:
            raw_or_title = normalize_line(str(node.get("rawText") or node.get("title") or ""))
            # 无分值的空分卷节点直接剔除；
            # 仅包含“共X题/共X分”等统计说明的分卷摘要行也剔除，
            # 避免在根级残留“Ⅱ”这类中间节点（例如：第Ⅱ卷 非选择题共5题，共60分）。
            if score <= 0:
                continue
            if re.search(r"(?:共\s*\d+\s*题|共\s*\d+(?:\.\d+)?\s*分)", raw_or_title):
                continue
        kept.append(node)
    nodes[:] = kept


def _suppress_inline_slot_markers_for_sentence_subquestions(nodes: List[Dict]) -> None:
    if not nodes:
        return

    for node in nodes:
        children = node.get("children", [])
        if children:
            _suppress_inline_slot_markers_for_sentence_subquestions(children)
            continue

        token_type = str(node.get("_tokenType") or "")
        level = int(node.get("level", 1))
        if token_type not in {"paren_arabic", "chinese_paren", "circled"}:
            continue
        if level < 3:
            continue

        raw_text = str(node.get("rawText") or "")
        if not raw_text:
            continue
        if _collect_question_mark_placeholder_segments(raw_text):
            # “（2）？句子...”这类由格式转换导致的问号占位，保留为空位，不做句式抑制。
            continue
        if EMPTY_BRACKET_RE.search(raw_text):
            # 显式括号空位属于真实题目内容，不能在这里清掉。
            continue
        if not (_collect_blank_segments(raw_text) or EMPTY_BRACKET_RE.search(raw_text)):
            continue

        # 子问本身是完整句子时，不再把题干中的空位当作更深层子集，避免前端误展开。
        body = normalize_line(
            re.sub(
                rf"^\s*(?:[\uFF08(]\s*[0-9一二三四五六七八九十]{1,3}\s*[\uFF09)]|{CIRCLED_MARKER_CLASS})",
                "",
                raw_text,
                count=1,
            )
        )
        explicit_score = node.get("score")
        # 有分值的子问默认保留空位；仅在明显“问答句”场景下做抑制。
        if explicit_score is not None and float(explicit_score) > 0:
            if not re.search(r"[？?]|为什么|如何|是否|判断|分析|比较|哪[一二三四五六七八九十]条", body):
                continue
        cjk_count = len(re.findall(r"[\u4e00-\u9fa5]", body))
        if cjk_count < 8:
            continue

        # 仅抑制该类句式子问的空位渲染，保留 rawText 原文，
        # 避免“原文有横线但导出结构 rawText 丢失横线”的对比误差。
        node["blankText"] = ""


def _aggregate_outline_node_score(node: Dict) -> float:
    explicit_score = node.get("score")
    if explicit_score is not None and float(explicit_score) > 0:
        return float(explicit_score)
    children = node.get("children", [])
    if children:
        return sum(_aggregate_outline_node_score(child) for child in children)
    return 0.0


def _backfill_outline_parent_scores_from_children(nodes: List[Dict]) -> None:
    for node in nodes:
        children = node.get("children", [])
        if children:
            _backfill_outline_parent_scores_from_children(children)

        if not children:
            continue

        explicit_score = node.get("score")
        aggregate_score = round(sum(_aggregate_outline_node_score(child) for child in children), 2)
        explicit_value = float(explicit_score) if explicit_score is not None else 0.0
        if aggregate_score > 0 and (explicit_score is None or explicit_value <= 0 or aggregate_score > explicit_value):
            node["score"] = _normalize_score_value(float(aggregate_score))


def build_scores_tree(outline_items: List[Dict]) -> Dict:
    def aggregate(node: Dict) -> float:
        child_nodes = node.get("children", [])
        explicit_score = node.get("score")
        if child_nodes:
            child_total = sum(aggregate(child) for child in child_nodes)
            if explicit_score is not None and float(explicit_score) > 0:
                return max(float(explicit_score), child_total)
            return child_total
        if explicit_score is not None and float(explicit_score) > 0:
            return float(explicit_score)
        return 0.0

    def convert(node: Dict) -> Dict:
        child_nodes = node.get("children", [])
        child_items = [convert(child) for child in child_nodes]
        explicit_score = node.get("score")
        if child_items:
            child_total = sum(float(item.get("score") or 0.0) for item in child_items)
            if explicit_score is not None and float(explicit_score) > 0:
                score = max(float(explicit_score), child_total)
            else:
                score = child_total
        else:
            if explicit_score is not None:
                score = float(explicit_score)
            else:
                score = 0.0
        if child_items:
            _distribute_parent_score_to_blank_children(node, child_nodes, child_items)
            _distribute_parent_score_to_zero_children_fallback(node, child_nodes, child_items)
        return {"score": _normalize_score_value(score), "childScores": child_items}

    child_scores = [convert(item) for item in outline_items]
    total_score = sum(aggregate(item) for item in outline_items) if outline_items else 0.0
    return {"score": _normalize_score_value(total_score), "childScores": child_scores}


def detect_question_type(outline_items: List[Dict], second_level_mode: str) -> int:
    has_level1_chinese = False
    has_level2_arabic = False
    for node in outline_items:
        if re.fullmatch(CHINESE_NUM_RE, node.get("numbering", "")):
            has_level1_chinese = True
        for child in node.get("children", []):
            if _parse_ascii_int(child.get("numbering")) is not None:
                has_level2_arabic = True

    if has_level1_chinese and has_level2_arabic:
        return 4 if second_level_mode == "continuous" else 3
    if has_level1_chinese:
        return 1
    return 2


def analyze_document_lines(
    lines: List[str],
    max_level: int = 8,
    second_level_mode: str = "auto",
    score_patterns: Optional[List[str]] = None,
) -> Dict:
    expanded_lines = _expand_lines_for_parsing(lines)
    normalized_lines = [normalize_line(line) for line in expanded_lines if normalize_line(line)]
    answer_card_index_line_nos = _collect_answer_card_index_line_nos(normalized_lines)
    compiled_score_patterns = compile_score_patterns(score_patterns)

    heading_candidates: List[HeadingCandidate] = []
    blank_candidates: List[BlankScoreCandidate] = []
    scored_text_candidates: List[ScoredTextCandidate] = []
    indexed_blank_candidates: List[IndexedBlankMarkerCandidate] = []
    for idx, line in enumerate(normalized_lines):
        if idx in answer_card_index_line_nos:
            continue
        indexed_blank = _parse_indexed_blank_markers(idx, line)
        if indexed_blank:
            indexed_blank_candidates.append(indexed_blank)

        heading = _parse_heading(idx, line, compiled_score_patterns)
        if heading:
            heading_candidates.append(heading)
            continue
        blank = _parse_blank_score(idx, line, compiled_score_patterns)
        if blank:
            blank_candidates.append(blank)
            continue
        scored_text = _parse_scored_text(idx, line, compiled_score_patterns)
        if scored_text:
            scored_text_candidates.append(scored_text)

    extraction_start_line_no = _resolve_extraction_start_line_no(heading_candidates, compiled_score_patterns)
    filtered_heading_candidates = [
        item
        for item in heading_candidates
        if extraction_start_line_no is None or item.line_no >= extraction_start_line_no
    ]

    has_chinese_level1 = any(
        item.token_type in {"chinese", "chinese_loose", "roman", "appendix", "paper_volume"}
        for item in filtered_heading_candidates
    )
    has_non_roman_level1 = any(
        item.token_type in {"chinese", "chinese_loose", "appendix", "paper_volume"}
        for item in filtered_heading_candidates
    )
    # 检查是否有paper_volume（如第Ⅰ卷），从原始heading_candidates中检查
    has_paper_volume = any(
        item.token_type == "paper_volume"
        for item in heading_candidates
    )
    first_chinese_level1_line_no = min(
        (
            item.line_no
            for item in filtered_heading_candidates
            if item.token_type in {"chinese", "chinese_loose", "roman", "appendix", "paper_volume"}
        ),
        default=None,
    )
    has_arabic = any(
        item.token_type in {"arabic", "arabic_loose", "arabic_bare", "paren_arabic", "decimal"}
        for item in filtered_heading_candidates
    )
    arabic_section_line_nos = _collect_arabic_section_line_nos(
        filtered_heading_candidates,
        compiled_score_patterns,
    )
    has_arabic_section_heading = bool(arabic_section_line_nos)
    detected_mode = (
        second_level_mode
        if second_level_mode in {"restart", "continuous"}
        else detect_second_level_mode_auto(filtered_heading_candidates)
    )

    events = []
    for item in filtered_heading_candidates:
        events.append(("heading", item.line_no, item))
    for item in blank_candidates:
        events.append(("blank", item.line_no, item))
    for item in scored_text_candidates:
        events.append(("scored_text", item.line_no, item))
    events.sort(key=lambda x: x[1])

    roots: List[Dict] = []
    stack: List[Dict] = []
    last_level: Optional[int] = None
    token_counter = Counter()
    ignored_heading_count = len(heading_candidates) - len(filtered_heading_candidates)
    if ignored_heading_count > 0:
        token_counter["heading_prelude_ignored"] = ignored_heading_count

    for event_index, (event_type, _, payload) in enumerate(events):
        if event_type == "blank":
            if extraction_start_line_no is not None and payload.line_no < extraction_start_line_no:
                token_counter["blank_prelude_ignored"] += 1
                continue
            if _try_merge_blank_into_previous_heading(stack, payload):
                token_counter["blank_merged_into_heading"] += 1
                continue
            _append_blank_score_node(roots, stack, payload, max_level)
            token_counter["blank_score"] += 1
            continue
        if event_type == "scored_text":
            if extraction_start_line_no is not None and payload.line_no < extraction_start_line_no:
                token_counter["scored_text_prelude_ignored"] += 1
                continue
            if _is_range_prompt_only_line(payload.raw):
                token_counter["range_prompt_scored_text_ignored"] += 1
                continue
            if _try_merge_scored_text_into_previous_heading(stack, payload):
                token_counter["scored_text_merged_into_heading"] += 1
                continue
            if _append_scored_text_node(stack, payload, max_level):
                token_counter["scored_text"] += 1
            elif _try_promote_scored_text_to_section_root(roots, stack, payload, max_level):
                token_counter["scored_text_promoted_to_root"] += 1
                last_level = 1
            else:
                token_counter["scored_text_orphan_ignored"] += 1
            continue

        item: HeadingCandidate = payload
        if _is_range_prompt_only_line(item.raw or item.title):
            token_counter["range_prompt_heading_ignored"] += 1
            continue
        if (
            item.token_type in {"arabic", "arabic_loose", "arabic_bare", "paren_arabic"}
            and item.number_value is not None
            and item.number_value <= 0
        ):
            token_counter["nonpositive_number_heading_ignored"] += 1
            continue
        if _try_merge_wrapped_numeric_continuation_into_previous_heading(stack, item):
            token_counter["wrapped_numeric_continuation_merged"] += 1
            continue
        if _try_merge_circled_continuation_into_empty_paren_heading(stack, item):
            token_counter["circled_merged_into_paren"] += 1
            continue
        if _should_skip_interleaved_choice_answer_heading(item, stack):
            token_counter["choice_answer_key_ignored"] += 1
            continue
        if _should_skip_numeric_option_stub_heading(item, stack):
            token_counter["choice_option_stub_ignored"] += 1
            continue
        if _should_skip_writing_requirement_heading(item, stack):
            token_counter["writing_requirement_ignored"] += 1
            continue
        if _should_skip_paren_arabic_material_heading(item, stack):
            _mark_material_paren_skip(item, stack)
            token_counter["paren_arabic_material_ignored"] += 1
            continue
        if _should_skip_chinese_paren_reading_heading(item, stack):
            _reset_stack_to_reading_root_on_skipped_chinese_paren_heading(item, stack)
            token_counter["chinese_paren_reading_ignored"] += 1
            continue
        if _should_skip_chinese_material_heading(item, stack, compiled_score_patterns):
            token_counter["chinese_material_ignored"] += 1
            continue
        if _should_skip_circled_material_heading(item, stack):
            token_counter["circled_material_ignored"] += 1
            continue
        if _should_skip_paren_range_marker(item, stack):
            token_counter["paren_arabic_range_marker_ignored"] += 1
            continue
        if item.token_type in {"arabic", "arabic_loose", "arabic_bare", "decimal"}:
            if INDEXED_BLANK_TOKEN_RE.search(item.raw or "") and _is_under_cloze_section(stack):
                token_counter["cloze_indexed_heading_ignored"] += 1
                continue
        if item.token_type == "arabic_bare" and not stack:
            token_counter["arabic_bare_orphan_ignored"] += 1
            continue
        if item.token_type == "arabic_bare" and stack:
            parent = next(
                (node for node in reversed(stack) if int(node.get("level", 1)) == 1),
                stack[0],
            )
            existing_numbers = sorted(
                number_value
                for child in parent.get("children", [])
                for number_value in [_parse_ascii_int(child.get("numbering"))]
                if number_value is not None
            )
            if item.number_value is None:
                token_counter["arabic_bare_orphan_ignored"] += 1
                continue
            if existing_numbers:
                expected_next = existing_numbers[-1] + 1
                if item.number_value != expected_next:
                    token_counter["arabic_bare_nonsequential_ignored"] += 1
                    continue
            else:
                if item.number_value != 1:
                    token_counter["arabic_bare_nonsequential_ignored"] += 1
                    continue
        level = _calc_level(
            item,
            max_level,
            has_chinese_level1,
            has_non_roman_level1,
            has_arabic,
            last_level,
            has_paper_volume,
        )
        is_arabic_section_heading = item.line_no in arabic_section_line_nos
        is_paren_section_heading = item.token_type == "paren_arabic" and _is_section_like_paren_arabic_heading(item)
        is_question_style_arabic_section = False
        should_bind_arabic_section_children = False
        is_scoreless_arabic_section_heading = False
        if item.token_type in {"arabic", "arabic_loose", "arabic_bare"}:
            title_without_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", item.title or ""))
            is_question_style_arabic_section = bool(
                _is_arabic_question_section_heading(item, compiled_score_patterns)
                or QUESTION_SECTION_TITLE_RE.search(title_without_score)
            )
            is_scoreless_arabic_section_heading = bool(
                is_arabic_section_heading
                and item.score is None
                and is_question_style_arabic_section
            )
            has_chinese_paren_parent = any(
                str(node.get("_tokenType") or "") == "chinese_paren" for node in reversed(stack)
            )
            if (
                is_arabic_section_heading
                and is_question_style_arabic_section
                and has_chinese_paren_parent
                and item.score is not None
                and float(item.score) > 0
            ):
                should_bind_arabic_section_children = True
            if (
                is_arabic_section_heading
                and is_question_style_arabic_section
                and not should_bind_arabic_section_children
                and level >= 2
                and item.number_value is not None
            ):
                parent_level = max(level - 1, 1)
                parent_node = next(
                    (node for node in reversed(stack) if int(node.get("level", 1)) == parent_level),
                    None,
                )
                previous_sibling_number: Optional[int] = None
                if parent_node is not None:
                    for sibling in reversed(parent_node.get("children", [])):
                        parsed = _parse_ascii_int(sibling.get("numbering"))
                        if parsed is not None:
                            previous_sibling_number = parsed
                            break
                if previous_sibling_number is None:
                    chinese_paren_parent = next(
                        (node for node in reversed(stack) if str(node.get("_tokenType") or "") == "chinese_paren"),
                        None,
                    )
                    if chinese_paren_parent is not None:
                        for sibling in reversed(chinese_paren_parent.get("children", [])):
                            parsed = _parse_ascii_int(sibling.get("numbering"))
                            if parsed is not None:
                                previous_sibling_number = parsed
                                break
                if previous_sibling_number is not None:
                    should_bind_arabic_section_children = item.number_value != previous_sibling_number + 1
        before_first_chinese_level1 = (
            first_chinese_level1_line_no is not None
            and item.line_no < first_chinese_level1_line_no
        )
        if is_arabic_section_heading:
            # 规则说明：题号与层级识别的逻辑约束。
            # 规则说明：题号与层级识别的逻辑约束。
            # 规则说明：题号与层级识别的逻辑约束。
            # 规则说明：题号与层级识别的逻辑约束。
            # 规则说明：题号与层级识别的规则定义。
            level = 1 if (not has_chinese_level1 or before_first_chinese_level1) else min(2, max_level)
            if has_chinese_level1 and item.number_value is not None:
                latest_level1 = next(
                    (node for node in reversed(stack) if int(node.get("level", 1)) == 1),
                    roots[-1] if roots else None,
                )
                if latest_level1 is not None:
                    sibling_numbers = [
                        number_value
                        for child in latest_level1.get("children", [])
                        for number_value in [_parse_ascii_int(child.get("numbering"))]
                        if number_value is not None
                    ]
                    # 规则说明：题号与层级识别的逻辑约束。
                    # 规则说明：题号与层级识别的条件过滤。
                    if sibling_numbers and item.number_value <= sibling_numbers[-1]:
                        level = 1
            # 规则说明：分数提取与分配的逻辑约束。
            # 规则说明：分数提取与分配的逻辑约束。
            # 规则说明：分数提取与分配的条件过滤。
            if (
                item.score is None
                and has_chinese_level1
                and level >= 2
            ):
                level1_parent = next(
                    (node for node in reversed(stack) if int(node.get("level", 1)) == 1),
                    roots[-1] if roots else None,
                )
                if level1_parent is not None:
                    parent_score = level1_parent.get("score")
                    if parent_score is not None and float(parent_score) > 0:
                        scored_children_total = sum(
                            float(child.get("score") or 0)
                            for child in level1_parent.get("children", [])
                            if child.get("score") is not None and float(child.get("score") or 0) > 0
                        )
                        if scored_children_total >= float(parent_score) - 1e-6:
                            level = 1
        elif (
            item.token_type in {"arabic", "arabic_loose", "arabic_bare"}
            and has_arabic_section_heading
            and (not has_chinese_level1 or before_first_chinese_level1)
        ):
            prev_root_arabic = _latest_root_arabic_number(roots)
            if _is_section_like_scored_arabic_heading(item):
                # 明确题型标题默认一级；但若处在已识别分节内部且不具备强分节信号，则按二级处理。
                level = 1
                if (
                    item.number_value is not None
                    and prev_root_arabic is not None
                    and item.number_value > prev_root_arabic
                ):
                    previous_root = next(
                        (
                            node
                            for node in reversed(roots)
                            if _parse_ascii_int(node.get("numbering")) == prev_root_arabic
                        ),
                        None,
                    )
                    current_title = normalize_line(item.title or "")
                    has_strong_section_keyword = bool(
                        re.search(
                            r"(?:\u9605\u8bfb|\u73b0\u4ee3\u6587|\u6587\u8a00\u6587|\u4f5c\u6587|\u5199\u4f5c|"
                            r"\u7efc\u5408|\u542c\u529b|\u5b8c\u5f62|\u6a21\u5757|\u90e8\u5206|\u9009\u62e9\u9898|\u975e\u9009\u62e9\u9898)",
                            current_title,
                        )
                    )
                    has_following_paren_children = _has_following_paren_subquestion_heading(
                        events, event_index, item.line_no
                    )
                    if (
                        previous_root is not None
                        and bool(previous_root.get("_isSectionHeading"))
                        and not has_strong_section_keyword
                        and not has_following_paren_children
                    ):
                        level = min(2, max_level)
            else:
                # 规则说明：题号与层级识别（示例：arabic_loose）的逻辑约束。
                # 规则说明：题号与层级识别（示例：arabic_loose）的规则定义。
                if (
                    item.number_value is not None
                    and prev_root_arabic is not None
                    and item.number_value == prev_root_arabic + 1
                    and item.score is not None
                    and float(item.score) > 0
                ):
                    # 连号题只有在“明显是分节标题”或“后续跟(1)(2)子问”时保留一级；
                    # 否则按二级处理，避免把普通题目抬升成根节点（如 1-7 全部顶到根级）。
                    is_section_title = bool(
                        _is_strict_arabic_section_heading_title(item.title)
                        or SECTION_TITLE_FALLBACK_HINT_RE.search(normalize_line(item.title or ""))
                    )
                    has_following_paren_children = _has_following_paren_subquestion_heading(
                        events, event_index, item.line_no
                    )
                    level = 1 if (is_section_title or has_following_paren_children) else min(2, max_level)
                else:
                    level = min(2, max_level)
        elif (
            item.token_type in {"arabic", "arabic_loose", "arabic_bare"}
            and has_chinese_level1
            and before_first_chinese_level1
        ):
            level = 1 if not has_arabic_section_heading else min(2, max_level)
        if item.token_type in {"arabic", "arabic_loose", "arabic_bare"}:
            level = _adjust_arabic_level_by_chinese_paren_context(
                level,
                stack,
                max_level,
                force_bind=not (is_arabic_section_heading and item.score is None),
                current_item=item,
            )
            # 阿拉伯父级题号后直接出现“父级+1”的高位题号（如 6 后接 7、8），
            # 更可能是同级题目而非子题，提升为同级以避免误挂子级。
            if (
                not is_arabic_section_heading
                and not should_bind_arabic_section_children
                and has_chinese_level1
                and not before_first_chinese_level1
                and level >= 2
                and item.number_value is not None
                and item.number_value >= 4
            ):
                level1_parent = next(
                    (node for node in reversed(stack) if int(node.get("level", 1)) == 1),
                    None,
                )
                if level1_parent is not None:
                    parent_type = str(level1_parent.get("_tokenType") or "")
                    parent_number = _parse_ascii_int(level1_parent.get("numbering"))
                    if (
                        parent_type in {"arabic", "arabic_loose", "arabic_bare", "decimal"}
                        and parent_number is not None
                        and item.number_value == parent_number + 1
                    ):
                        level = 1
            # 明确作文/写作大题（带总分）应作为一级节点，避免被错误挂到阅读子级下。
            if _is_writing_section_arabic_heading(item) and float(item.score or 0) >= 20:
                level = 1
        elif item.token_type == "paren_arabic":
            level = _adjust_paren_arabic_level_by_context(level, stack, max_level)
            level = _promote_paren_arabic_section_level(level, item, stack, max_level)
        elif item.token_type == "circled":
            level = _adjust_circled_level_by_context(level, stack, max_level)
        if (
            item.token_type in {"arabic", "arabic_loose", "arabic_bare", "decimal"}
            and stack
        ):
            # 当阿拉伯数字在罗马数字章节下面时，调整层级
            level = _adjust_arabic_level_by_roman_context(level, stack, max_level)
            reading_root = next(
                (
                    node
                    for node in reversed(stack)
                    if int(node.get("level", 1)) == 1
                    and bool(node.get("_afterSkippedReadingPartition"))
                ),
                None,
            )
            if (
                reading_root is not None
                and _is_under_reading_root(stack)
            ):
                level = min(int(reading_root.get("level", 1)) + 1, max_level)
                reading_root.pop("_afterSkippedReadingPartition", None)
        last_level = level
        token_counter[item.token_type] += 1
        node_score = item.score
        per_item_unit_score = _extract_per_item_unit_score(item.raw, compiled_score_patterns)
        if (
            node_score is None
            and item.token_type in {"chinese", "chinese_loose", "roman", "appendix"}
            and level == 1
        ):
            node_score = _infer_heading_score_from_context(
                lines=lines,
                line_no=item.line_no,
                heading_title=item.title,
                score_patterns=compiled_score_patterns,
            )
        blank_score = float(item.score) if item.score is not None else 0.0
        raw_text = item.raw
        blank_text = _format_blank_segments_from_line(item.raw, blank_score)
        inline_first_paren_child_node: Optional[Dict] = None

        if item.token_type in {"arabic", "arabic_loose", "arabic_bare"}:
            inline_title = normalize_line(item.title or "")
            inline_match = re.match(r"^[\uFF08(]\s*1\s*[\uFF09)]\s*(.+)$", inline_title)
            if inline_match and _has_following_paren_subquestion_heading(events, event_index, item.line_no):
                child_raw = normalize_line(
                    re.sub(r"^\s*\d{1,4}\s*[\u3001\.\uFF0E]\s*", "", item.raw, count=1)
                )
                if not child_raw:
                    child_raw = f"\uFF081\uFF09{inline_match.group(1)}"
                child_score = float(item.score) if item.score is not None else None
                child_blank_text = _format_blank_segments_from_line(
                    child_raw,
                    float(child_score) if child_score is not None else 0.0,
                )
                if _is_single_empty_slot_paren_subquestion(child_raw, "paren_arabic", child_score):
                    child_blank_text = ""

                inline_first_paren_child_node = {
                    "lineNumber": item.line_no + 1,
                    "level": min(level + 1, max_level),
                    "numbering": "1",
                    "title": inline_match.group(1).strip(),
                    "rawText": child_raw,
                    "blankText": child_blank_text,
                    "score": child_score,
                    "_tokenType": "paren_arabic",
                    "_isSectionHeading": False,
                    "_bindSectionChildren": False,
                    "children": [],
                }
                # 规则说明：分数提取与分配的逻辑约束。
                # 规则说明：分数提取与分配的规则定义。
                node_score = None
                blank_text = ""

        if is_arabic_section_heading or is_paren_section_heading:
            blank_text = ""
        if _is_single_empty_slot_paren_subquestion(item.raw, item.token_type, item.score):
            blank_text = ""
        choice_stem_empty_slot = bool(
            item.token_type in {"arabic", "arabic_loose", "arabic_bare"}
            and _is_choice_stem_empty_bracket_only_heading(item.raw)
        )
        choice_keyword_stem = bool(
            item.token_type in {"arabic", "arabic_loose", "arabic_bare", "paren_arabic"}
            and _is_choice_question_heading_text(raw_text)
        )
        choice_stem_has_slot = bool(
            EMPTY_BRACKET_RE.search(raw_text) or _collect_blank_segments(raw_text)
        )
        has_following_options = bool(
            choice_stem_empty_slot and _has_following_choice_option_lines(normalized_lines, item.line_no)
        )
        suppress_choice_stem_blank = bool(
            (
                choice_stem_empty_slot
                and ((item.score is None or float(item.score) <= 0) or has_following_options)
            )
            or (choice_keyword_stem and choice_stem_has_slot)
        )
        if (
            suppress_choice_stem_blank
            and choice_stem_empty_slot
        ):
            blank_text = ""
        if suppress_choice_stem_blank:
            blank_text = ""
        node = {
            "lineNumber": item.line_no + 1,
            "level": level,
            "numbering": item.number_text,
            "title": item.title,
            "rawText": raw_text,
            "blankText": blank_text,
            "score": node_score,
            "_tokenType": item.token_type,
            "_perItemUnitScore": per_item_unit_score,
            "_isSectionHeading": bool(is_arabic_section_heading or is_paren_section_heading),
            "_bindSectionChildren": bool(
                is_paren_section_heading
                or should_bind_arabic_section_children
                or is_scoreless_arabic_section_heading
            ),
            "_suppressChoiceStemBlank": suppress_choice_stem_blank,
            "children": [],
        }
        _append_outline_node(roots, stack, node)
        if inline_first_paren_child_node is not None:
            _append_outline_node(roots, stack, inline_first_paren_child_node)

    _append_missing_indexed_blank_marker_nodes(roots, indexed_blank_candidates, max_level)
    _prune_number_only_placeholder_nodes(roots)
    _merge_empty_numbering_leaf_nodes(roots)
    _prune_empty_leaf_placeholder_nodes(roots)
    _prune_unnumbered_material_children(roots)
    _prune_duplicate_numbering_answer_echo_children(roots)
    _prune_material_paragraph_children(roots)
    _prune_material_style_high_index_paren_children(roots)
    _prune_duplicate_arabic_range_prompt_nodes(roots)
    _prune_unnumbered_range_prompt_nodes(roots)
    _flatten_numbered_range_prompt_nodes(roots)
    _normalize_duplicate_paren_arabic_siblings(roots)
    _nest_restarted_arabic_children_under_last_paren_child(roots)
    _flatten_article_marker_chinese_paren_children(roots)
    _flatten_same_family_sequential_children(roots)
    _prune_writing_instruction_children(roots)
    _prune_writing_prompt_requirement_children(roots)
    _collapse_writing_section_children_to_single_prompt(roots)
    _nest_arabic_section_roots_under_previous_chinese_root(roots)
    _flatten_unnumbered_scored_reading_roots(roots)
    _collapse_statement_option_paren_children(roots)
    _repair_embedded_paren_subquestion_fragments(roots)
    _expand_per_item_unit_scores(roots)
    _propagate_writing_section_score_to_single_child(roots)
    _distribute_outline_parent_score_to_slot_children(roots)
    _distribute_outline_parent_score_to_numbered_zero_children(roots)
    _distribute_outline_parent_remaining_score_to_unscored_children(roots)
    _distribute_outline_parent_score_gap_to_slot_leaves(roots)
    _distribute_outline_parent_remaining_score_to_unscored_children(roots)
    _force_fill_zero_child_scores_under_scored_parent(roots)
    _rebalance_single_child_full_score_leak(roots)
    _prune_empty_paper_volume_nodes(roots)
    _fill_scored_empty_bracket_leaf_blank_text(roots)
    _fill_scored_underline_leaf_blank_text(roots)
    _fill_scored_question_mark_placeholder_blank_text(roots)
    _flatten_circled_children_under_numeric_nodes(roots)
    _strip_instruction_quoted_underlines_from_blank_text(roots)
    _suppress_inline_slot_markers_for_sentence_subquestions(roots)
    _collapse_choice_question_multi_blanks(roots)
    _collapse_choice_semantic_leaf_multi_blanks(roots)
    _enforce_choice_question_no_blank_and_no_children(roots)
    _prune_zero_score_material_marker_leaves(roots)
    _prune_conflicting_duplicate_numbered_children(roots)
    _prune_number_only_placeholder_nodes(roots)
    _prune_empty_leaf_placeholder_nodes(roots)
    _hoist_overflow_children_after_scored_container(roots)
    _prune_unnumbered_range_prompt_nodes(roots)
    _flatten_numbered_range_prompt_nodes(roots)
    _flatten_same_family_sequential_children(roots)
    _fill_scored_question_mark_placeholder_blank_text(roots)
    normalize_outline_blank_scores(roots)
    _backfill_outline_parent_scores_from_children(roots)
    _normalize_mixed_paren_section_numbering_to_chinese(roots)
    _normalize_mixed_root_numbering_to_chinese(roots)
    # 按"提取而非自动重排"的规则，保留文档原始中文一级编号。
    _normalize_nonincreasing_chinese_root_numbering(roots)

    # 修复缺失的中文编号根节点 - 暂时禁用，逻辑过于复杂导致副作用
    # _fix_missing_chinese_roots(roots)

    # _normalize_sparse_chinese_root_numbering(roots)
    _prune_conflicting_duplicate_numbered_children(roots)
    _prune_number_only_placeholder_nodes(roots)
    _prune_empty_leaf_placeholder_nodes(roots)
    _repair_embedded_paren_subquestion_fragments(roots)
    _rebalance_single_child_full_score_leak(roots)
    # 清理/折叠后部分节点会从“父级”变成“叶子”，这里再做一次空位回填与均分修正。
    _fill_scored_empty_bracket_leaf_blank_text(roots)
    _fill_scored_underline_leaf_blank_text(roots)
    _fill_scored_question_mark_placeholder_blank_text(roots)
    _collapse_choice_question_multi_blanks(roots)
    _collapse_choice_semantic_leaf_multi_blanks(roots)
    _enforce_choice_question_no_blank_and_no_children(roots)
    normalize_outline_blank_scores(roots)
    scores = build_scores_tree(roots)
    detected_max_level = max((node["level"] for node in _walk_nodes(roots)), default=0)
    question_type = detect_question_type(roots, detected_mode)
    _strip_internal_fields(roots)

    # 清理标题中的听力说明文字
    _clean_listening_instruction_from_title(roots)

    return {
        "outlineItems": roots,
        "scores": scores,
        "detectedMaxLevel": detected_max_level,
        "secondLevelModeDetected": detected_mode if detected_mode in {"restart", "continuous"} else "unknown",
        "questionType": question_type,
        "ruleHits": dict(token_counter),
    }


def _clean_listening_instruction_from_title(nodes: List[Dict]) -> None:
    """清理标题中的听力说明性文字，如'每段对话听二遍'"""
    if not nodes:
        return
    for node in nodes:
        title = str(node.get("title") or "")
        raw_text = str(node.get("rawText") or "")
        numbering = str(node.get("numbering") or "")
        # 清理标题中的听力说明文字
        if title and LISTENING_INSTRUCTION_RE.search(title):
            # 找到说明文字的位置并截断
            match = LISTENING_INSTRUCTION_RE.search(title)
            if match:
                # 保留说明文字之前的内容，并清理末尾标点
                cleaned_title = title[:match.start()].strip()
                # 清理末尾的逗号、句号等
                cleaned_title = re.sub(r'[,，.。]+$', '', cleaned_title).strip()
                if cleaned_title:
                    # 使用numbering来构建完整标题
                    if numbering and numbering not in cleaned_title:
                        cleaned_title = numbering + " " + cleaned_title
                    node["title"] = cleaned_title
                    node["rawText"] = cleaned_title
        # 递归处理子节点
        _clean_listening_instruction_from_title(node.get("children", []))


def _walk_nodes(nodes: List[Dict]):
    for node in nodes:
        yield node
        for child in _walk_nodes(node.get("children", [])):
            yield child


def _latest_root_arabic_number(roots: List[Dict]) -> Optional[int]:
    for node in reversed(roots):
        number_value = _parse_ascii_int(node.get("numbering"))
        if number_value is not None:
            return number_value
    return None


def _strip_internal_fields(nodes: List[Dict]) -> None:
    for node in nodes:
        for key in list(node.keys()):
            if key.startswith("_"):
                node.pop(key, None)
        _strip_internal_fields(node.get("children", []))


def _format_score_text(score: float) -> str:
    value = int(score) if int(score) == score else round(score, 2)
    return f"\uFF08{value}\u5206\uFF09"


def _symbol_key(value: str) -> str:
    return (
        value.replace("\uFF08", "(")
        .replace("\uFF09", ")")
        .replace("\u3000", " ")
        .strip()
    )


def _is_empty_bracket(value: str) -> bool:
    normalized = _symbol_key(value)
    if not (normalized.startswith("(") and normalized.endswith(")")):
        return False
    inner = normalized[1:-1].replace(" ", "").replace("\u00a0", "")
    return inner == ""


def _is_question_start_line(line_no: int, line: str, score_patterns: List[re.Pattern]) -> bool:
    normalized = normalize_line(line)
    if not normalized:
        return False
    heading = _parse_heading(line_no, normalized, score_patterns)
    if heading:
        if heading.token_type in {"paren_arabic", "chinese_paren"} and not heading.title:
            return False
        return True
    return bool(QUESTION_START_HINT_RE.match(normalized))


def _is_cover_title_line(line: str) -> bool:
    normalized = normalize_line(line)
    if not normalized:
        return False
    return bool(COVER_TITLE_HINT_RE.search(normalized))


def _is_title_ordinal_bracket(value: str) -> bool:
    normalized = _symbol_key(value)
    if not (normalized.startswith("(") and normalized.endswith(")")):
        return False
    inner = normalized[1:-1].replace(" ", "").replace("\u00a0", "")
    return bool(TITLE_ORDINAL_BRACKET_RE.fullmatch(inner))


def _is_question_section_heading(candidate: HeadingCandidate, score_patterns: List[re.Pattern]) -> bool:
    if candidate.token_type in {"appendix", "paper_volume"}:
        return True
    if candidate.token_type not in {"chinese", "chinese_loose", "roman"}:
        return False

    title = normalize_line(candidate.title)
    if not title:
        return False

    is_non_question_title = bool(NON_QUESTION_SECTION_TITLE_RE.search(title))
    has_question_hint = bool(QUESTION_SECTION_TITLE_RE.search(title))
    has_score = extract_score_from_text(title, score_patterns) is not None

    if is_non_question_title and not has_question_hint:
        return False
    if has_question_hint:
        return True
    if "\u9898" in title and not is_non_question_title:
        return True
    if has_score:
        return True
    return False


def _is_arabic_question_section_heading(candidate: HeadingCandidate, score_patterns: List[re.Pattern]) -> bool:
    if candidate.token_type not in {"arabic", "arabic_loose"}:
        return False

    title = normalize_line(candidate.title)
    if not title:
        return False
    if len(title) > 96:
        return False

    title_without_score = PAREN_SCORE_ONLY_RE.sub("", title).strip()
    if not title_without_score:
        title_without_score = title
    if re.search(r"[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A]", title_without_score):
        return False
    if re.search(r"[\uFF08(]\s*\d{1,3}\s*[\uFF09)]", title_without_score):
        return False

    has_explicit_title = bool(EXPLICIT_ARABIC_SECTION_TITLE_RE.search(title_without_score))
    if re.match(
        r"^(?:\u5224\u65ad|\u9009\u62e9|\u586b\u7a7a|\u8ba1\u7b97|\u89e3\u7b54|\u5e94\u7528|\u89e3(?:\u51b3|\u6c7a)\u95ee\u9898|\u4f5c\u56fe|\u64cd\u4f5c)(?:\u9898)?(?:[\u3002\uFF0E,，\u3001:：\s\(\uff08]|$)",
        title_without_score,
    ):
        has_explicit_title = True
    has_loose_title = bool(LOOSE_ARABIC_SECTION_TITLE_RE.search(title_without_score))
    score_value = extract_score_from_text(candidate.raw, score_patterns)
    if not has_explicit_title and not has_loose_title:
        if not (
            score_value is None
            and (
                QUESTION_SECTION_TITLE_RE.search(title_without_score)
                or SECTION_TITLE_FALLBACK_HINT_RE.search(title_without_score)
            )
        ):
            return False
    if re.search(r"\u5c0f\u9898|\u7b2c\s*[一二三四五六七八九十\d]+\s*\u9898", title):
        return False

    if score_value is None:
        # 规则说明：分数提取与分配（示例：。．.,，、；;:：）的逻辑约束。
        # 规则说明：分数提取与分配（示例：。．.,，、；;:：）的逻辑约束。
        # 规则说明：分数提取与分配（示例：。．.,，、；;:：）的规则定义。
        title_core = title_without_score.strip("。．.,，、；;:：")
        if not title_core:
            return False
        if len(title_core) > 20:
            return False
        if re.search(r"[？?，,；;:：]", title_core):
            return False
        if re.search(
            r"\u7b2c\s*[一二三四五六七八九十\d]+\s*\u9898|\u5c0f\u9898|\u4e0b\u5217|\u4e0b\u9762|\u8bf7|\u56de\u7b54|\u5b8c\u6210",
            title_core,
        ):
            return False
        if not (
            _is_strict_arabic_section_heading_title(title_core)
            or QUESTION_SECTION_TITLE_RE.search(title_core)
            or SECTION_TITLE_FALLBACK_HINT_RE.search(title_core)
        ):
            return False
        return True
    if re.search(r"[？?]", title):
        return False
    return True


def _is_strict_arabic_section_heading_title(title: str) -> bool:
    normalized = normalize_line(title)
    if not normalized:
        return False
    core = PAREN_SCORE_ONLY_RE.sub("", normalized).strip()
    if not core:
        core = normalized
    core = core.strip("。．.,，、；;:：")
    if re.search(r"[A-Za-z\uFF21-\uFF3A\uFF41-\uFF5A]", core):
        return False
    return bool(STRICT_ARABIC_SECTION_TITLE_RE.fullmatch(core))


def _is_section_like_scored_arabic_heading(candidate: HeadingCandidate) -> bool:
    if candidate.token_type not in {"arabic", "arabic_loose"}:
        return False
    if candidate.score is None:
        return False
    if _collect_blank_segments(candidate.raw):
        return False

    title = normalize_line(candidate.title)
    if not title:
        return False
    core = PAREN_SCORE_ONLY_RE.sub("", title).strip().strip("。．.")
    if not core:
        core = title
    core_head = re.split(r"[。．\(\（:：；;，,]", core, maxsplit=1)[0].strip() or core
    if len(core_head) > 24:
        return False
    if re.search(r"[？?，,；;:：]", core):
        return False
    if re.search(r"\u7b2c\s*[一二三四五六七八九十\d]+\s*\u9898|\u5c0f\u9898", core_head):
        return False
    if len(core) >= 6 and re.search(
        r"\u4e0b\u5217|\u4e0b\u9762|\u62ec\u53f7|\u6a2a\u7ebf|\u77ed\u6587|\u53e5\u5b50|\u8bcd\u8bed|\u6750\u6599|\u6587\u6bb5|\u53e4\u8bd7\u6587|\u4e00\u9879",
        core,
    ):
        return False
    if len(core) >= 6 and re.match(
        r"^(?:\u7ed9|\u5728|\u628a|\u5c06|\u6309|\u5199\u51fa|\u8865\u5199|\u586b\u7a7a|\u89e3\u91ca|\u7ffb\u8bd1|\u6539\u5199|\u9605\u8bfb|\u5224\u65ad|\u9009\u62e9)(?![。．、,，:：\s\(\uff08])",
        core,
    ):
        return False
    if re.search(
        r"\u4e0b\u5217|\u5982\u56fe|\u5982\u4e0b|\u8bf7|\u6c42|\u8981\u6c42|\u8bfb\u4f5c|\u91cc\u9762|\u591a\u5c11|\u4e3a\u4ec0\u4e48|\u662f\u5426",
        core,
    ):
        return False
    if re.match(r"^(?:\u6839\u636e(?:\u62fc\u97f3|\u8bed\u5883|\u6750\u6599|\u77ed\u6587)|\u8bf7\u6839\u636e|\u6309\u8981\u6c42)", core):
        return False
    return True


def _collect_arabic_section_line_nos(
    candidates: List[HeadingCandidate],
    score_patterns: List[re.Pattern],
) -> set:
    line_nos: set = set()
    prev_arabic_number: Optional[int] = None
    prev_arabic_line_no: Optional[int] = None
    prev_arabic_question_like: bool = False
    last_chinese_level1_line_no: Optional[int] = None
    has_chinese_level1 = any(
        item.token_type in {"chinese", "chinese_loose", "roman", "appendix", "paper_volume"}
        for item in candidates
    )

    for item in candidates:
        if item.token_type in {"chinese", "chinese_loose", "roman", "appendix", "paper_volume"}:
            last_chinese_level1_line_no = item.line_no
            continue
        if item.token_type not in {"arabic", "arabic_loose"}:
            continue

        has_intervening_chinese_level1 = (
            last_chinese_level1_line_no is not None
            and (
                prev_arabic_line_no is None
                or last_chinese_level1_line_no > prev_arabic_line_no
            )
            and last_chinese_level1_line_no < item.line_no
        )
        is_section_heading = _is_arabic_question_section_heading(item, score_patterns)
        current_title = normalize_line(item.title or "")
        current_question_like = bool(
            QUESTION_DIRECTIVE_HINT_RE.search(current_title)
            or re.search(r"[？?]", current_title)
            or EMPTY_BRACKET_RE.search(item.raw or "")
            or _collect_blank_segments(item.raw or "")
        )

        if (
            is_section_heading
            and has_chinese_level1
            and item.number_value is not None
            and prev_arabic_number is not None
            and not has_intervening_chinese_level1
            and item.number_value == prev_arabic_number + 1
            and prev_arabic_question_like
        ):
            is_section_heading = False

        if (
            is_section_heading
            and item.number_value is not None
            and prev_arabic_number is not None
            and not has_intervening_chinese_level1
            and item.number_value == prev_arabic_number + 1
            and not _is_strict_arabic_section_heading_title(item.title)
            and has_chinese_level1
        ):
            # 规则说明：题号与层级识别的逻辑约束。
            # 规则说明：题号与层级识别的规则定义。
            is_section_heading = False

        # 规则说明：题号与层级识别的逻辑约束。
        # 规则说明：题号与层级识别的逻辑约束。
        # 规则说明：题号与层级识别的条件过滤。
        if (
            is_section_heading
            and not has_chinese_level1
            and item.number_value is not None
            and prev_arabic_number is not None
            and item.number_value == prev_arabic_number + 1
            and not _is_strict_arabic_section_heading_title(item.title)
        ):
            title_core = normalize_line(PAREN_SCORE_ONLY_RE.sub("", item.title or "")).strip("。．.,，、；;:： ")
            if title_core in {
                "\u586b\u7a7a",  # 填空
                "\u9009\u62e9",  # 选择
                "\u5355\u9009",  # 单选
                "\u591a\u9009",  # 多选
                "\u5224\u65ad",  # 判断
                "\u8ba1\u7b97",  # 计算
                "\u89e3\u7b54",  # 解答
                "\u5e94\u7528",  # 应用
                "\u9605\u8bfb",  # 阅读
                "\u4f5c\u6587",  # 作文
                "\u5199\u4f5c",  # 写作
                "\u542c\u529b",  # 听力
                "\u7ffb\u8bd1",  # 翻译
                "\u6539\u9519",  # 改错
                "\u8bc1\u660e",  # 证明
                "\u4f5c\u56fe",  # 作图
            } or item.number_value >= 4:
                is_section_heading = False

        if not is_section_heading and _is_section_like_scored_arabic_heading(item):
            title_core_for_repromote = normalize_line(PAREN_SCORE_ONLY_RE.sub("", item.title or "")).strip(
                "。．.,，、；;:： "
            )
            if item.number_value == 1 and prev_arabic_number is None:
                # 规则说明：避免把“1. 普通题目（含括号空）”误当作阿拉伯分段标题。
                # 仅当首个阿拉伯标题明确呈现“题型/部分”语义时，才提升为分段标题。
                is_section_heading = bool(
                    _is_strict_arabic_section_heading_title(item.title)
                    or QUESTION_SECTION_TITLE_RE.search(title_core_for_repromote)
                    or SECTION_TITLE_FALLBACK_HINT_RE.search(title_core_for_repromote)
                    or EXPLICIT_ARABIC_SECTION_TITLE_RE.search(title_core_for_repromote)
                )
            elif item.number_value is not None and prev_arabic_number is not None:
                if not has_intervening_chinese_level1:
                    if not has_chinese_level1:
                        # 规则说明：题号与层级识别的逻辑约束。
                        # 规则说明：题号与层级识别的逻辑约束。
                        # 规则说明：题号与层级识别的条件过滤。
                        if _is_strict_arabic_section_heading_title(item.title):
                            is_section_heading = True
                        elif item.number_value == prev_arabic_number + 1:
                            # 规则说明：下划线与括号空提取的逻辑约束。
                            # 规则说明：下划线与括号空提取的逻辑约束。
                            # 规则说明：下划线与括号空提取的条件过滤。
                            if not (
                                EMPTY_BRACKET_RE.search(item.raw or "")
                                or _collect_blank_segments(item.raw or "")
                            ) and not (
                                item.number_value >= 4
                                and title_core_for_repromote
                                in {
                                    "\u586b\u7a7a",  # 填空
                                    "\u9009\u62e9",  # 选择
                                    "\u5355\u9009",  # 单选
                                    "\u591a\u9009",  # 多选
                                    "\u5224\u65ad",  # 判断
                                    "\u8ba1\u7b97",  # 计算
                                    "\u89e3\u7b54",  # 解答
                                    "\u5e94\u7528",  # 应用
                                    "\u9605\u8bfb",  # 阅读
                                    "\u4f5c\u6587",  # 作文
                                    "\u5199\u4f5c",  # 写作
                                    "\u542c\u529b",  # 听力
                                    "\u7ffb\u8bd1",  # 翻译
                                    "\u6539\u9519",  # 改错
                                    "\u8bc1\u660e",  # 证明
                                    "\u4f5c\u56fe",  # 作图
                                }
                            ):
                                is_section_heading = True
                        elif item.number_value <= prev_arabic_number:
                            is_section_heading = True
                        elif item.number_value - prev_arabic_number > 1:
                            is_section_heading = True
                    elif item.number_value <= prev_arabic_number:
                        is_section_heading = True
                    elif item.number_value - prev_arabic_number > 1:
                        is_section_heading = True

        if is_section_heading:
            line_nos.add(item.line_no)

        if item.number_value is not None:
            prev_arabic_number = item.number_value
            prev_arabic_line_no = item.line_no
            prev_arabic_question_like = current_question_like

    return line_nos


def _is_writing_section_arabic_heading(item: HeadingCandidate) -> bool:
    if item.token_type not in {"arabic", "arabic_loose", "arabic_bare"}:
        return False
    if item.score is None or float(item.score) <= 0:
        return False
    title = normalize_line(PAREN_SCORE_ONLY_RE.sub("", item.title or item.raw or ""))
    if not title:
        return False
    return bool(WRITING_SECTION_TITLE_RE.search(title))


def _find_question_section_heading_line_no(
    heading_candidates: List[HeadingCandidate],
    score_patterns: List[re.Pattern],
) -> Optional[int]:
    for item in heading_candidates:
        if _is_question_section_heading(item, score_patterns) or _is_arabic_question_section_heading(
            item, score_patterns
        ):
            return item.line_no
    return None


def _is_prelude_meta_heading(candidate: HeadingCandidate) -> bool:
    text = normalize_line(candidate.raw)
    if not text:
        return False
    title = normalize_line(candidate.title)
    title_wo_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", title or ""))
    score_value = float(candidate.score or 0)
    is_scored_question_section = bool(
        score_value > 0
        and (
            QUESTION_SECTION_TITLE_RE.search(title_wo_score)
            or SECTION_TITLE_FALLBACK_HINT_RE.search(title_wo_score)
            or re.search(r"(?:本大题共\d+小题|非选择题|选择题|材料分析|材料题|阅读材料|综合题)", title_wo_score)
        )
    )
    is_unscored_question_section = bool(
        title_wo_score
        and re.search(
            r"(?:非\s*选择题|选择题|单项选择题?|多项选择题?|单选题?|多选题?|判断题|填空题|解答题|简答题|"
            r"阅读理解|阅读题|材料(?:题|分析题?)|作文|写作|书面表达|听力|语言知识运用|积累(?:与)?运用)",
            title_wo_score,
        )
    )
    if PRELUDE_META_HINT_RE.search(text):
        if candidate.token_type in {"chinese", "chinese_loose", "roman", "appendix", "paper_volume", "arabic", "arabic_loose"}:
            if is_scored_question_section or is_unscored_question_section:
                return False
        return True

    if title and PRELUDE_META_HINT_RE.search(title):
        if candidate.token_type in {"chinese", "chinese_loose", "roman", "appendix", "paper_volume", "arabic", "arabic_loose"}:
            if is_scored_question_section or is_unscored_question_section:
                return False
        return True

    if candidate.token_type in {"arabic", "arabic_loose"} and re.match(
        r"^(?:\u6ce8\u610f|\u8bf4\u660e|\u4f5c\u7b54|\u8bf7|\u672c\u8bd5\u5377|\u7b54\u6848|\u59d3\u540d|\u8003\u53f7)",
        title,
    ):
        # 规则说明：分数提取与分配的逻辑约束。
        # 规则说明：分数提取与分配的逻辑约束。
        # 规则说明：分数提取与分配的条件过滤。
        if candidate.score is not None and float(candidate.score) > 0:
            return False
        if candidate.number_value is not None and candidate.number_value > 3:
            return False
        return True
    return False


def _resolve_extraction_start_line_no(
    heading_candidates: List[HeadingCandidate],
    score_patterns: List[re.Pattern],
) -> Optional[int]:
    if not heading_candidates:
        return None

    effective_candidates = [item for item in heading_candidates if not _is_prelude_meta_heading(item)]
    if not effective_candidates:
        effective_candidates = heading_candidates

    section_line_no = _find_question_section_heading_line_no(effective_candidates, score_patterns)
    if section_line_no is not None:
        nearby_part_heading = next(
            (
                item
                for item in reversed(effective_candidates)
                if item.line_no < section_line_no
                and section_line_no - item.line_no <= 3
                and item.token_type == "paper_volume"
                and "部分" in normalize_line(item.number_text)
            ),
            None,
        )
        if nearby_part_heading is not None:
            return nearby_part_heading.line_no

        # 题型行前紧邻的中文一级题号（即使该行本身无分值）应作为提取起点，
        # 避免把“ 一、 ”误丢弃后导致后续阿拉伯题号顶成根节点。
        nearby_chinese_heading = next(
            (
                item
                for item in reversed(effective_candidates)
                if item.line_no < section_line_no
                and section_line_no - item.line_no <= 3
                and item.token_type in {"chinese", "chinese_loose", "roman", "appendix"}
            ),
            None,
        )
        if nearby_chinese_heading is not None:
            # 若“题型行前3行内”命中的是后续分节（如“二、”），
            # 但其前还存在中文一级分节且两者之间已有实题（带分值阿拉伯题号），
            # 则起点应回退到更早的分节（如“一、”），避免整段漏提。
            previous_chinese_heading = next(
                (
                    item
                    for item in reversed(effective_candidates)
                    if item.line_no < nearby_chinese_heading.line_no
                    and item.token_type in {"chinese", "chinese_loose", "roman", "appendix"}
                ),
                None,
            )
            if previous_chinese_heading is not None:
                has_scored_arabic_between_two_sections = any(
                    item.line_no > previous_chinese_heading.line_no
                    and item.line_no < nearby_chinese_heading.line_no
                    and item.token_type in {"arabic", "arabic_loose", "arabic_bare"}
                    and item.score is not None
                    and float(item.score) > 0
                    for item in effective_candidates
                )
                if has_scored_arabic_between_two_sections:
                    return previous_chinese_heading.line_no
            return nearby_chinese_heading.line_no

        # 若后续已识别到某个中文一级分节（如“二、”），则其前面的最近中文一级
        # 通常是上一分节（如“一、”）；当两者之间已出现题号题干时，提取应从该中文分节开始。
        preceding_chinese_heading = next(
            (
                item
                for item in reversed(effective_candidates)
                if item.line_no < section_line_no
                and item.token_type in {"chinese", "chinese_loose", "roman", "appendix"}
            ),
            None,
        )
        if preceding_chinese_heading is not None:
            has_scored_arabic_between = any(
                item.line_no > preceding_chinese_heading.line_no
                and item.line_no < section_line_no
                and item.token_type in {"arabic", "arabic_loose", "arabic_bare"}
                and item.score is not None
                and float(item.score) > 0
                for item in effective_candidates
            )
            if has_scored_arabic_between:
                return preceding_chinese_heading.line_no

        pre_section_candidates = [item for item in effective_candidates if item.line_no < section_line_no]
        pre_section_arabic = [
            item
            for item in pre_section_candidates
            if item.token_type in {"arabic", "arabic_loose", "arabic_bare"}
            and item.number_value is not None
        ]
        # 允许“1、2、... 后接中文大题”的短序列提前进入提取起点，避免漏掉前两个大题。
        if len(pre_section_arabic) >= 2:
            pre_section_arabic.sort(key=lambda item: item.line_no)
            sequence = [int(item.number_value) for item in pre_section_arabic]
            if sequence and sequence[0] == 1:
                sequential_pairs = sum(
                    1 for left, right in zip(sequence, sequence[1:]) if right == left + 1
                )
                required_pairs = min(4, len(sequence) - 1) if len(sequence) >= 4 else min(2, len(sequence) - 1)
                if sequential_pairs >= required_pairs:
                    if len(pre_section_arabic) >= 4:
                        return pre_section_arabic[0].line_no

                    short_run = pre_section_arabic[:3]
                    scored_short = [
                        item
                        for item in short_run
                        if item.score is not None and float(item.score) > 0
                    ]
                    short_section_like = []
                    for item in short_run:
                        title_without_score = normalize_line(PAREN_SCORE_ONLY_RE.sub("", item.title or ""))
                        if (
                            _is_section_like_scored_arabic_heading(item)
                            or QUESTION_SECTION_TITLE_RE.search(title_without_score)
                            or SECTION_TITLE_FALLBACK_HINT_RE.search(title_without_score)
                        ):
                            short_section_like.append(item)
                    if len(scored_short) >= 2 or short_section_like:
                        return pre_section_arabic[0].line_no
        meaningful_pre_section = [
            item
            for item in pre_section_candidates
            if (
                _is_question_section_heading(item, score_patterns)
                or _is_arabic_question_section_heading(item, score_patterns)
                or _is_section_like_scored_arabic_heading(item)
            )
        ]
        # 规则说明：题号与层级识别的逻辑约束。
        # 规则说明：题号与层级识别的逻辑约束。
        # 规则说明：题号与层级识别的逻辑约束。
        # 规则说明：题号与层级识别的条件过滤。
        if len(meaningful_pre_section) >= 2:
            return min(item.line_no for item in meaningful_pre_section)
        return section_line_no

    first_level_line = min(
        (
            item.line_no
            for item in effective_candidates
            if item.token_type in {"chinese", "chinese_loose", "roman", "appendix"}
        ),
        default=None,
    )
    if first_level_line is not None:
        return first_level_line

    return min(item.line_no for item in effective_candidates)


def extract_symbol_texts(lines: List[str]) -> List[str]:
    score_patterns = compile_score_patterns(None)
    bracket_pattern = re.compile(r"[\uFF08(][^\uFF08\uFF09()]{0,200}[\uFF09)]")
    ordered_symbols: List[str] = []
    heading_candidates: List[HeadingCandidate] = []
    for line_no, line in enumerate(lines):
        normalized_line = normalize_line(line)
        if not normalized_line:
            continue
        heading = _parse_heading(line_no, normalized_line, score_patterns)
        if heading:
            heading_candidates.append(heading)

    question_section_line_no = _find_question_section_heading_line_no(heading_candidates, score_patterns)
    extraction_start_line_no = _resolve_extraction_start_line_no(heading_candidates, score_patterns)
    question_started = extraction_start_line_no is None

    for line_no, line in enumerate(lines):
        if question_section_line_no is not None and line_no < question_section_line_no:
            continue

        normalized_line = normalize_line(line)
        if not question_started and _is_question_start_line(line_no, normalized_line, score_patterns):
            question_started = True

        bracket_hits = bracket_pattern.findall(line)
        line_score = extract_score_from_text(line, score_patterns)
        generated_score_symbol = False

        underline_segments = _build_scored_underline_segments(
            line,
            fallback_score=float(line_score) if line_score is not None else 0.0,
        )
        if underline_segments:
            for item, score_value in underline_segments:
                value = f"{item}{_format_score_text(score_value)}"
                ordered_symbols.append(value)
            generated_score_symbol = True

        for item in bracket_hits:
            if not question_started and _is_title_ordinal_bracket(item):
                continue
            if not question_started and _is_cover_title_line(normalized_line):
                continue
            if _is_cover_title_line(normalized_line) and _is_title_ordinal_bracket(item):
                continue
            if generated_score_symbol and extract_score_from_text(item, score_patterns) is not None:
                continue
            if _is_empty_bracket(item):
                if not generated_score_symbol:
                    ordered_symbols.append(f"____{_format_score_text(0.0)}")
                    generated_score_symbol = True
                continue
            ordered_symbols.append(item)

    return ordered_symbols


def detect_pdf_header_footer(page_lines: List[List[str]]) -> List[Dict]:
    first_lines = [page[0] if page else "" for page in page_lines]
    last_lines = [page[-1] if page else "" for page in page_lines]

    first_count = Counter(line for line in first_lines if line)
    last_count = Counter(line for line in last_lines if line)
    shared_headers = {line for line, count in first_count.items() if count >= 2}
    shared_footers = {line for line, count in last_count.items() if count >= 2}

    results = []
    for idx, lines in enumerate(page_lines, start=1):
        header = lines[0] if lines and lines[0] in shared_headers else ""
        footer = lines[-1] if lines and lines[-1] in shared_footers else ""
        results.append({"page": idx, "header": header, "footer": footer})
    return results



