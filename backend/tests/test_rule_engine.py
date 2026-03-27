import re

from app.services.rule_engine import (
    _parse_heading,
    compile_score_patterns,
    _count_text_slot_markers,
    _merge_empty_numbering_leaf_nodes,
    _normalize_duplicate_paren_arabic_siblings,
    _collapse_statement_option_paren_children,
    _collect_blank_segments,
    _fill_scored_underline_leaf_blank_text,
    analyze_document_lines,
    detect_pdf_header_footer,
    extract_symbol_texts,
    normalize_outline_blank_scores,
)


def test_outline_and_restart_mode_detection():
    lines = [
        "\u4e00\u3001\u9009\u62e9\u9898\uff0810\u5206\uff09",
        "1. \u7b2c\u4e00\u5c0f\u9898\uff082\u5206\uff09",
        "(1) \u5b50\u9898A\uff081\u5206\uff09",
        "(2) \u5b50\u9898B\uff081\u5206\uff09",
        "\u4e8c\u3001\u586b\u7a7a\u9898\uff086\u5206\uff09",
        "1. \u586b\u7a7a\u4e00\uff083\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    assert analysis["detectedMaxLevel"] >= 3
    assert analysis["secondLevelModeDetected"] == "restart"
    assert len(analysis["outlineItems"]) == 2
    assert analysis["scores"]["score"] == 16.0


def test_continuous_mode_detection():
    lines = [
        "\u4e00\u3001\u9009\u62e9\u9898\uff0810\u5206\uff09",
        "1. \u9898\u76ee\u4e00\uff082\u5206\uff09",
        "2. \u9898\u76ee\u4e8c\uff082\u5206\uff09",
        "\u4e8c\u3001\u586b\u7a7a\u9898\uff088\u5206\uff09",
        "3. \u9898\u76ee\u4e09\uff082\u5206\uff09",
        "4. \u9898\u76ee\u56db\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    assert analysis["secondLevelModeDetected"] == "continuous"


def test_score_fallback_to_zero():
    lines = [
        "\u4e00\u3001\u9009\u62e9\u9898",
        "1. \u7b2c\u4e00\u9898",
        "2. \u7b2c\u4e8c\u9898",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="restart")
    child_scores = analysis["scores"]["childScores"]
    assert child_scores
    assert child_scores[0]["score"] == 0.0
    assert child_scores[0]["childScores"][0]["score"] == 0.0


def test_parent_score_should_be_evenly_distributed_when_all_children_are_underlines():
    lines = [
        "1. \u586b\u7a7a\u9898\uff0810\u5206\uff09",
        "(1) ______",
        "(2) ______",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["scores"]["childScores"][0]
    assert root["score"] == 10.0
    assert [item["score"] for item in root["childScores"]] == [5.0, 5.0]


def test_parent_score_should_be_evenly_distributed_when_all_children_have_slot_markers():
    lines = [
        "1. \u586b\u7a7a\u9898\uff0810\u5206\uff09",
        "(1) \u586b\u7a7a\uff1a______",
        "(2) ______",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["scores"]["childScores"][0]
    assert root["score"] == 10.0
    assert [item["score"] for item in root["childScores"]] == [5.0, 5.0]


def test_parent_score_should_not_be_lower_than_sum_of_scored_children():
    lines = [
        "一、选择题（3分）",
        "1．第一题（1分）",
        "2．第二题（1分）",
        "3．第三题（1分）",
        "4．默写填空。（8分）",
        "①________（2分）",
        "②________（2分）",
        "③________（2分）",
        "④________（2分）",
        "6．语言运用（2分）",
        "7．文学常识（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "一"
    assert root["score"] == 15.0
    assert analysis["scores"]["childScores"][0]["score"] == 15.0


def test_inline_writing_requirements_should_not_be_extracted_as_children():
    lines = [
        "三、作文（30分）",
        "23.请以“不一样的_________”为题，写一篇文章。 要求：",
        "（1）在横线上填上适当的词语，将文题补充完整。",
        "（2）文体自选（诗歌除外）。",
        "（3）不少于600字，不出现真实校名、人名。",
        "（4）书写工整规范。（4分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    prompt = root["children"][0]
    assert root["numbering"] == "三"
    assert root["score"] == 30.0
    assert prompt["numbering"] == "23"
    assert prompt["score"] == 30.0
    assert prompt["children"] == []


def test_normalize_outline_blank_scores_should_trim_overflow_blank_tokens_by_raw_slot_count():
    nodes = [
        {
            "lineNumber": 30,
            "level": 3,
            "numbering": "1",
            "title": "示例",
            "rawText": "(1) 示例________，示例________（1分），示例______________（1分）____",
            "blankText": "________（0.33分） ________（0.33分） ______________（0.33分） ____（0.33分） __________________（0.33分） ____________________（0.35分）",
            "score": 2.0,
            "children": [],
        }
    ]
    normalize_outline_blank_scores(nodes)
    assert len(str(nodes[0].get("blankText") or "").split()) == 4


def test_count_text_slot_markers_should_include_empty_brackets():
    text = "(2) 下列说法正确的是（ ） A. ____ B. ____"
    assert _count_text_slot_markers(text) == 3


def test_choice_question_should_still_have_no_children_after_tail_refill():
    lines = [
        "一、选择题（2分）",
        "1. 下列说法正确的是（ ） A. 甲 B. 乙（1分）",
        "2. 下列说法错误的是（ ） A. 丙 B. 丁（1分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    first = root["children"][0]
    second = root["children"][1]
    assert first["children"] == []
    assert second["children"] == []


def test_quoted_underline_should_not_be_stripped_without_instruction_hint():
    lines = [
        "一、基础题（3分）",
        "2. 给加点字选择正确的读音，打“√”。其中“_______”是多音字，它的另一个读音可以组词:_________。(3分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q2 = analysis["outlineItems"][0]["children"][0]
    blank = str(q2.get("blankText") or "")
    assert blank
    assert len(blank.split()) >= 2


def test_choice_semantic_paren_subquestion_should_collapse_multi_blanks():
    lines = [
        "一、阅读（2分）",
        "2. 阅读材料。（2分）",
        "(4) 将下列语句填入横线上，正确的一项是( ) 游走大漠，______;探访名山，______;踏访古镇，______;梦游江南，______。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q4 = None
    for root in analysis["outlineItems"]:
        for child in root.get("children", []):
            if str(child.get("numbering") or "").strip() == "2":
                for sub in child.get("children", []):
                    if str(sub.get("numbering") or "").strip() in {"4", "(4)"}:
                        q4 = sub
                        break
    assert q4 is not None
    blank = str(q4.get("blankText") or "")
    assert len(blank.split()) <= 1


def test_scored_chinese_paren_reading_marker_should_reset_following_question_level():
    lines = [
        "七、阅读。（29分）",
        "（一）阅读课文节选，完成练习。（11分）",
        "1.划去选文括号中错误的拼音或生字。（2分）",
        "2.选文中画“_____”的句子采用了____________的说明方法。（2分）",
        "3.选文中画“_____”的句子形象地概括了地球的两大特征_______和________。（4分）",
        "4.认真读文段，判断下面问题，对的打“√”，错的打“×”。（3分）",
        "（1）因为科学家提出那么多设想，人类完全有理由指望在破坏了地球以后移居到别的星球上去。( )",
        "（2）“又有多少人能够去居住呢？”这句话的意思是没有多少人能够去居住。( )",
        "（3）读了这段话让我们明白了保护地球的重要性和紧迫性。( )",
        "（二）阅读短文，完成练习。（18分）",
        "1.写近义词。（2分）",
        "2.写反义词。（2分）",
        "3.根据下面意思在短文中找到相应的词语写下来。（2分）",
        "4.当大家都说鲁迅是天才时，鲁迅是怎么回答的？用“____”在文中画出来。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "七"
    first_four = root["children"][3]
    assert first_four["numbering"] == "4"
    assert [child["numbering"] for child in first_four["children"]] == ["1", "2", "3"]
    assert root["children"][4]["numbering"] == "1"
    assert "写近义词" in root["children"][4]["title"]


def test_mixed_root_numbering_should_normalize_leading_arabic_to_chinese():
    lines = [
        "1、勇闯字音关。(16分)",
        "1. 看拼音，写词语。（10分）",
        "2. 填同音字，组成词语。（6分）",
        "2、书法展示台。（2分）",
        "三、词语积累与运用。（14分）",
        "1．照样子写词语。（3分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots[:3]] == ["一", "二", "三"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2"]


def test_pure_arabic_root_numbering_should_not_be_forced_to_chinese():
    lines = [
        "1、选择题（40分）",
        "2、填空题（20分）",
        "3、解答题（40分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots[:3]] == ["1", "2", "3"]


def test_choice_option_lines_are_not_question_numbers():
    lines = [
        "1. \u7b2c\u4e00\u9898\uff082\u5206\uff09",
        "A. \u9009\u9879A",
        "B. \u9009\u9879B",
        "2. \u7b2c\u4e8c\u9898\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="restart")
    numbers = [item["numbering"] for item in analysis["outlineItems"]]
    assert numbers == ["1", "2"]


def test_numeric_prefixed_option_lines_inside_choice_section_should_not_create_extra_questions():
    lines = [
        "\u4e00\u3001\u5355\u9879\u9009\u62e9\u9898\uff0824\u5206\uff09",
        "1. \u7b2c\u4e00\u9898\uff083\u5206\uff09",
        "2. \u7b2c\u4e8c\u9898\uff083\u5206\uff09",
        "1. A. \u9009\u9879\u6587\u672c",
        "2. B. \u9009\u9879\u6587\u672c",
        "3. C. \u9009\u9879\u6587\u672c",
        "3. \u7b2c\u4e09\u9898\uff083\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="restart")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2", "3"]


def test_numeric_prefixed_multi_option_line_should_be_ignored_without_choice_keyword_root():
    lines = [
        "\u4e00\u3001\u542c\u529b\uff0810\u5206\uff09",
        "1.A.want B.walk C.watch",
        "2.A.use B.usually C.useful",
        "1. \u6b63\u5e38\u9898\u76ee\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00"]
    numeric_children = [
        item["numbering"]
        for item in roots[0]["children"]
        if str(item.get("numbering") or "").strip().isdigit()
    ]
    assert numeric_children == ["1"]


def test_bracket_prefixed_numeric_option_line_should_be_ignored():
    lines = [
        "\u4e00\u3001\u542c\u529b\uff0810\u5206\uff09",
        "(\u3000)1.A.want B.walk C.watch",
        "(\u3000)2.A.use B.usually C.useful",
        "1. \u6b63\u5e38\u9898\u76ee\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1"]


def test_numeric_prefixed_sentence_starting_with_letter_should_not_be_ignored():
    lines = [
        "\u4e00\u3001\u9605\u8bfb\uff086\u5206\uff09",
        "1. A good friend is helpful.\uff082\u5206\uff09",
        "2. Another question.\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2"]


def test_non_numbered_choice_section_heading_with_wrapped_score_should_be_recognized():
    lines = [
        "选择题:下列各题的四个选项中，只有一项符合题意。请在答题卡上填涂你认为正确",
        "的选项（51分）",
        "1. 第一题（3分）",
        "2. 第二题（3分）",
        "2、非选择题（49分）",
        "18. 第十八题（14分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert roots[0]["numbering"] == "选择题"
    assert roots[0]["score"] == 51.0
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2"]
    assert roots[1]["numbering"] == "2"


def test_arabic_heading_without_delimiter_but_with_score_should_be_recognized():
    lines = [
        "19\uff0818\u5206\uff09\u4e0a\u4e00\u5927\u9898",
        "\uff081\uff09\u7b2c\u4e00\u5c0f\u95ee",
        "20\uff0820\u5206\uff09\u4e0b\u4e00\u5927\u9898",
        "\uff081\uff09\u7b2c\u4e8c\u5927\u9898\u7b2c\u4e00\u5c0f\u95ee",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["19", "20"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1"]
    assert [item["numbering"] for item in roots[1]["children"]] == ["1"]


def test_scored_arabic_section_heading_should_bind_questions_but_keep_next_section_as_sibling():
    lines = [
        "1\u3001\u9009\u62e9\u9898\uff0830\u5206\uff09",
        "1. \u7b2c\u4e00\u9898\uff082\u5206\uff09",
        "2. \u7b2c\u4e8c\u9898\uff082\u5206\uff09",
        "2\u3001\u586b\u7a7a\u9898\uff0820\u5206\uff09",
        "16. \u7b2c\u5341\u516d\u9898\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["1", "2"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2"]
    assert [item["numbering"] for item in roots[1]["children"]] == ["16"]


def test_arabic_writing_section_root_should_not_be_nested_under_previous_chinese_root():
    lines = [
        "一、基础题（共24分）",
        "1. 根据课文默写古诗（10分）",
        "二（46分）",
        "6、解释加点的词语（3分）",
        "18、请你用简洁的语言说说题目“轻放”的含义。（5分）",
        "3、作文（50分）",
        "19. 跋山涉水，风景就在眼前。",
        "4、附加题（10分）",
        "1. 选段【A】中的“他”指的是（ ），这两段文字均是出自老舍的长篇小说《 》（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert len(roots) == 4
    assert [item["title"] for item in roots] == [
        "基础题（共24分）",
        "（46分）",
        "作文（50分）",
        "附加题（10分）",
    ]
    assert [item["numbering"] for item in roots[1]["children"]] == ["6", "18"]
    assert [item["numbering"] for item in roots[2]["children"]] == ["19"]


def test_c_option_line_should_not_be_parsed_as_roman_root_heading():
    lines = [
        "\u4e8c\u3001\u975e\u9009\u62e9\u9898\uff0c\u5168\u90e8\u4e3a\u5fc5\u8003\u9898\u3002",
        "9. \uff085\u5206\uff09",
        "\uff081\uff09\u7528\u591a\u7528\u8868\u7684\u6b27\u59c6\u6863\u6d4b\u91cf\u963b\u503c\u7ea6\u4e3a\u51e0\u5341\u5343\u6b27\u7684\u7535\u963bRx\uff0c",
        "a\uff0e\u673a\u68b0\u8c03\u96f6\uff0c\u4f7f\u6307\u9488\u5bf9\u51c6\u5de6\u8fb9\u96f6\u523b\u7ebf",
        "b\uff0e\u65cb\u8f6c\u9009\u62e9\u5f00\u5173\u7f6e\u4e8e\u6b27\u59c6\u6863\u00d71k",
        "c\uff0e\u65cb\u8f6cS\u4f7f\u5176\u5c16\u7aef\u5bf9\u51c6\u6b27\u59c6\u68631k",
        "d\uff0e\u5c06\u4e24\u8868\u7b14\u77ed\u63a5\uff0c\u8c03\u8282\u6b27\u59c6\u8c03\u96f6\u65cb\u94ae",
        "10. \uff0810\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e8c"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["9", "10"]


def test_symbol_text_extraction_skips_cover_title_brackets_before_questions():
    lines = [
        "\u0032\u0030\u0031\u0037\u002d\u0032\u0030\u0031\u0038\u5e74\u5ea6\u7b2c\u4e00\u5b66\u671f\u516b\u5e74\u7ea7\u5730\u7406\u8bd5\u5377",
        "\u57f9\u4f18\u8bd5\u5377\uFF08\u4e09\uFF09",
        "\u4e00\u3001\u5355\u9009\u9898\uFF0830\u5206\uFF09",
        "1. \u6211\u56fd\u5404\u5730\u533a\u519c\u4e1a\u751f\u4ea7\u6761\u4ef6\u5dee\u5f02\u5f88\u5927\uFF08 \uFF09",
    ]
    symbols = extract_symbol_texts(lines)
    assert "\uFF08\u4e09\uFF09" not in symbols
    assert "____\uFF080\u5206\uFF09" in symbols


def test_symbol_text_extracts_all_underline_occurrences_in_one_line():
    lines = [
        "\uff081\uff09A\u70b9\u90fd\u4f4d\u4e8e\u5730\u7403\u4e0a\u4e94\u5e26\u4e2d\u7684____\u5e26\uff0c\u4e00\u5e74\u4e2d\u6709_________\u6b21\u592a\u9633\u76f4\u5c04\u3002",
        "\uff082\uff09\u5f53\u5730\u7403\u4f4d\u4e8e\u516c\u8f6c\u8f68\u9053\u4e0a\u7684\u4e59\u5904\u65f6\uff0c\u5317\u534a\u7403\u5904\u5728____\u5b63\uff0c\u5357\u534a\u7403\u5904\u5728____\u5b63\u3002",
    ]
    symbols = extract_symbol_texts(lines)
    assert symbols.count("____\uFF080\u5206\uFF09") >= 3


def test_symbol_text_should_not_synthesize_underline_for_plain_question_heading():
    lines = [
        "\u4e00\u3001\u542c\u529b\uff0820\u5206\uff09",
        "1. What does the girl look like?",
        "2. Where does Jack come from?",
    ]
    symbols = extract_symbol_texts(lines)
    assert "____\uFF080\u5206\uFF09" not in symbols


def test_heading_without_blank_markers_should_keep_blank_text_empty():
    lines = [
        "\u4e00\u3001\u5355\u9879\u9009\u62e9\uff0815\u5206\uff09",
        "1. What does the girl look like?",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    child = root["children"][0]
    assert root.get("blankText") == ""
    assert child.get("blankText") == ""


def test_pdf_header_footer_detection():
    page_lines = [
        ["\u67d0\u5b66\u6821\u671f\u672b\u8bd5\u5377", "\u9898\u76ee1", "\u7b2c1\u9875"],
        ["\u67d0\u5b66\u6821\u671f\u672b\u8bd5\u5377", "\u9898\u76ee2", "\u7b2c2\u9875"],
        ["\u67d0\u5b66\u6821\u671f\u672b\u8bd5\u5377", "\u9898\u76ee3", "\u7b2c3\u9875"],
    ]
    data = detect_pdf_header_footer(page_lines)
    assert data[0]["header"] == "\u67d0\u5b66\u6821\u671f\u672b\u8bd5\u5377"
    assert data[1]["footer"] == ""


def test_indexed_cloze_markers_should_not_be_extracted_as_blank_segments():
    line = (
        "Kitty wanted a present but not e__86___. "
        "She went s__87__ after lunch. Then she r_91___ home."
    )
    assert _collect_blank_segments(line) == []


def test_variable_digit_prefix_underlines_should_be_kept_as_answer_blanks():
    line = (
        "则力F1_______（>／＝／<）F2，拉力做的功W1_______（>／＝／<）W2，"
        "拉力做功的功率P1_______（>／＝／<）P2。"
    )
    segments = _collect_blank_segments(line)
    assert len(segments) == 3



def test_short_standalone_underline_after_existing_blank_should_not_merge():
    lines = [
        "一、填空（6分）",
        "13. 在横线上填空：_______，_______。（4分）",
        "____",
        "14. 下一题。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    child = analysis["outlineItems"][0]["children"][0]
    score_tags = re.findall(r"[（(]\d+(?:\.\d+)?分[）)]", str(child.get("blankText") or ""))
    assert len(score_tags) == 2


def test_circled_or_spaced_numeric_labels_before_underline_should_be_kept():
    line = "1 ________ ②________ ③________ ④________ ⑤______"
    segments = _collect_blank_segments(line)
    assert len(segments) == 5


def test_arabic_continuation_score_after_existing_blanks_should_be_evenly_distributed():
    lines = [
        "\u4e00\u3001\u9605\u8bfb\u9898\uff0810\u5206\uff09",
        "2. 顺序是：_______→_______→",
        "________\u3002\uff083\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    child = analysis["outlineItems"][0]["children"][0]
    score_tags = re.findall(
        r"[\uFF08(](\d+(?:\.\d+)?)\u5206[\uFF09)]",
        str(child.get("blankText") or ""),
    )
    assert score_tags
    values = [float(v) for v in score_tags]
    assert abs(sum(values) - 3.0) < 1e-6
    assert all(value > 0 for value in values)


def test_mixed_text_empty_brackets_should_merge_into_heading_blank_text():
    line3 = "沙\uFF08     \uFF09 沐\uFF08     \uFF09 萍\uFF08     \uFF09 \uFF08     \uFF09约"
    line4 = "\uFF08     \uFF09生 \uFF08     \uFF09习 \uFF08     \uFF09堂 \uFF08     \uFF09束"
    lines = [
        "\u4e00\u3001\u8bcd\u8bed\u8fd0\u7528\uff086\u5206\uff09",
        "2.\u586b\u540c\u97f3\u5b57\uff0c\u7ec4\u6210\u8bcd\u8bed\u3002\uff086\u5206\uff09",
        line3,
        line4,
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q2 = analysis["outlineItems"][0]["children"][0]
    values = [
        float(item)
        for item in re.findall(
            r"[\uFF08(](\d+(?:\.\d+)?)\u5206[\uFF09)]",
            str(q2.get("blankText") or ""),
        )
    ]
    assert len(values) == 8
    assert abs(sum(values) - 6.0) < 1e-6
    assert all(value > 0 for value in values)


def test_continuation_sentence_blank_with_own_score_should_keep_score():
    lines = [
        "二、非选择题（5分）",
        "9. （5分）",
        "（1）步骤填写在横线上___________。（2分）",
        "根据上图所示指针位置，此被测电阻的阻值约为_______。（1分）",
        "（2）下述说法中正确的是_________。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q9 = analysis["outlineItems"][0]["children"][0]
    part1 = q9["children"][0]
    assert part1["score"] == 3.0
    assert "_______（1分）" in str(part1.get("blankText") or "")


def test_unnumbered_scored_follow_up_between_subquestions_should_merge_into_previous():
    lines = [
        "二、材料题（40分）",
        "26、材料一：xxxx",
        "（1）第一问。（2分）",
        "由材料一可知，补充追问。（2分）",
        "（2）第二问。（2分）",
        "（3）第三问。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    q26 = roots[0]["children"][0]
    assert [item["numbering"] for item in q26["children"]] == ["1", "2", "3"]
    assert q26["children"][0]["score"] == 4.0
    assert "由材料一可知" in str(q26["children"][0].get("rawText") or "")


def test_wrapped_scored_follow_up_line_should_not_create_unnumbered_child():
    lines = [
        "1、综合题（6分）",
        "(1) 第一问。（2分）",
        "(2) 第二问前半句。（1分）并在思想领域",
        "采取了什么措施使其形成统一格局？（1分）",
        "(3) 第三问。（1分）",
        "(4) 第四问。（1分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    children = root["children"]
    assert [str(item.get("numbering") or "") for item in children] == ["1", "2", "3", "4"]
    assert children[1]["score"] == 2.0
    assert "采取了什么措施" in str(children[1].get("rawText") or "")


def test_source_note_with_year_before_inline_number_should_not_split_new_question():
    lines = [
        "\u4e00\u3001\u9009\u62e9\u9898\uff0810\u5206\uff09",
        "1\u3001\u7b2c\u4e00\u9898\uff082\u5206\uff09",
        "2\u3001\u7b2c\u4e8c\u9898\uff082\u5206\uff09",
        "3\u3001\u7b2c\u4e09\u9898\uff082\u5206\uff09",
        "4\u3001\u7b2c\u56db\u9898\uff082\u5206\uff09",
        "5\u3001\uff082008\u00b7\u5e7f\u897f\u7389\u6797\uff0912.\u89c2\u5bdf\u4e0b\u5217\u56fe\u7247\uff1a",
        "6\u3001\u7b2c\u516d\u9898\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    numbers = [str(item.get("numbering") or "") for item in root["children"]]
    assert "12" not in numbers
    assert numbers == ["1", "2", "3", "4", "5", "6"]
    assert "12." in str(root["children"][4].get("rawText") or "")


def test_error_blank_lines_following_one_arabic_question_should_accumulate_total_score():
    lines = [
        "二、改一改（共计10分）",
        "21．以下材料中有五处错误，找出并改正。",
        "错误1：（             ）  改正：（                ）（2分）",
        "错误2：（             ）  改正：（                ）（2分）",
        "错误3：（             ）  改正：（                ）（2分）",
        "错误4：（             ）  改正：（                ）（2分）",
        "错误5：（             ）  改正：（                ）（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q21 = analysis["outlineItems"][0]["children"][0]
    assert q21["score"] == 10.0
    values = [
        float(item)
        for item in re.findall(
            r"[\uFF08(](\d+(?:\.\d+)?)\u5206[\uFF09)]",
            str(q21.get("blankText") or ""),
        )
    ]
    assert values
    assert abs(sum(values) - 10.0) < 1e-6


def test_heading_score_should_be_inferred_from_previous_section_summary_line():
    lines = [
        "一、选择题（40分）",
        "1. 第一题（5分）",
        "第Ⅱ卷 非选择题共5题，共60分",
        "二、非选择题，全部为必考题。",
        "9. （5分）",
        "10. （10分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["一", "二"]
    assert roots[1]["score"] == 60.0


def test_paper_volume_heading_should_split_choice_and_non_choice_questions_without_chinese_section_title():
    lines = [
        "一、选择题（40分）",
        "1、第一题（2分）",
        "20、第二十题（2分）",
        "第Ⅱ卷（非选择题 共 60 分）",
        "21、（10分）读图，回答问题。",
        "（1）第一问",
        "（2）第二问",
        "22、（10分）第二十一题",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert len(roots) >= 2
    assert roots[0]["numbering"] == "一"
    assert [str(item.get("numbering")) for item in roots[0].get("children", [])] == ["1", "20"]

    second_root = next((item for item in roots if str(item.get("numbering")) in {"Ⅱ", "II", "2", "二"}), None)
    assert second_root is not None
    assert [str(item.get("numbering")) for item in second_root.get("children", [])][:2] == ["21", "22"]


def test_arabic_range_prompt_line_with_same_number_following_should_be_pruned():
    lines = [
        "一、单项选择题（30分）",
        "18．我国夏季气温最低的地区分布在",
        "19．读“某河流流量图”，回答19~20题。",
        "19．图中数码表示的河流补给类型正确的是",
        "20．我国是一个旱涝灾害频繁的国家，主要是由于",
        "二、读图题（20分）",
        "31．读“中国空白政区图”，完成下列问题。（5分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert len(roots) == 2
    first_children = [str(item.get("numbering")) for item in roots[0].get("children", [])]
    assert first_children == ["18", "19", "20"]
    second_children = [str(item.get("numbering")) for item in roots[1].get("children", [])]
    assert second_children == ["31"]


def test_interleaved_choice_answer_key_line_should_not_be_parsed_as_question_heading():
    lines = [
        "一、单项选择题（3分）",
        "1．第一题（1分）",
        "2．第二题（1分）",
        "3．第三题（1分）",
        "1、D   2、C   3、B",
        "二、填空题（2分）",
        "1. 第一道填空（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [str(item.get("numbering")) for item in roots] == ["一", "二"]
    first_children = [str(item.get("numbering")) for item in roots[0].get("children", [])]
    assert first_children == ["1", "2", "3"]
    second_children = [str(item.get("numbering")) for item in roots[1].get("children", [])]
    assert second_children == ["1"]


def test_answer_card_pure_index_block_should_not_be_parsed_as_questions():
    lines = [
        "二、阅读材料，回答问题。（30分）",
        "10．材料一……",
        "（1）问题一",
        "（2）问题二",
        "（3）问题三",
        "1.",
        "2.",
        "3.",
        "4.",
        "5.",
        "6.",
        "7.",
        "8.",
        "9.",
        "10.",
        "答案：1.C 2.D",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert len(roots) == 1
    children = roots[0].get("children", [])
    assert [str(item.get("numbering")) for item in children] == ["10"]


def test_paren_subquestion_marker_line_should_merge_following_circled_continuation_text():
    lines = [
        "三、综合题（30分）",
        "21. 读图完成各题。（30分）",
        "(1) 第一问内容。",
        "(2)",
        "③山脉主要位于我国地势的第______级阶梯上，",
        "④山脉呈_________走向，其东侧为__________平原。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q21 = analysis["outlineItems"][0]["children"][0]
    part2 = q21["children"][1]
    assert part2["numbering"] == "2"
    assert "山脉主要位于我国地势的第" in str(part2.get("title") or "")
    assert "山脉呈" in str(part2.get("title") or "")
    assert part2.get("children") == []


def test_scored_text_merged_into_parent_should_rebalance_zero_blank_segments():
    lines = [
        "二、非选择题（10分）",
        "10. （10分）",
        "(1) fill _____ _____ _____ _____ （4分）",
        "(2) expr ______ ______",
        "answer only with R1/R2 （6分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q10 = analysis["outlineItems"][0]["children"][0]
    part2 = q10["children"][1]
    assert part2["score"] == 6.0
    values = [
        float(item)
        for item in re.findall(r"[\uff08(]\s*(\d+(?:\.\d+)?)\s*\u5206\s*[\uff09)]", str(part2.get("blankText") or ""))
    ]
    assert values
    assert abs(sum(values) - 6.0) < 1e-6
    assert all(value > 0 for value in values)


def test_arabic_scored_question_should_not_be_promoted_to_root_when_chinese_section_exists():
    lines = [
        "\u4e00\u3001\u79ef\u7d2f\u4e0e\u8fd0\u7528\u3002(56\u5206)",
        "1. \u5c0f\u5c0f\u4e66\u6cd5\u5bb6\u3002(3\u5206)",
        "2. \u8bfb\u62fc\u97f3\uff0c\u7ed3\u5408\u8bed\u5883\u5199\u8bcd\u8bed\u3002(6\u5206)",
        "3. \u9009\u5b57\u586b\u7a7a\u3002(6\u5206)",
        "4. \u5199\u51fa\u8bcd\u8bed\u8fd1\u4e49\u8bcd\u3002(4\u5206)",
        "5. \u586b\u7a7a\u9898\u3002(6\u5206)",
        "6. \u8fde\u7ebf\u9898\u3002(4\u5206)",
        "7. \u5c06\u4e0b\u5217\u8bcd\u8bed\u8865\u5145\u5b8c\u6574\uff0c\u518d\u9009\u8bcd\u586b\u7a7a\u3002(6\u5206)",
        "8. \u9009\u62e9\u9898\u3002(2\u5206)",
        "\u4e8c\u3001\u9605\u8bfb\u4e0e\u611f\u609f\u3002(19\u5206)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00", "\u4e8c"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2", "3", "4", "5", "6", "7", "8"]


def test_appendix_section_should_not_be_nested_under_previous_section():
    lines = [
        "\u4e00\u3001\u57fa\u7840\u77e5\u8bc6\uff0824\u5206\uff09",
        "1. \u7b2c\u4e00\u9898\uff0824\u5206\uff09",
        "\u4e09\u3001\u4f5c\u6587\uff0840\u5206\uff09",
        "16. \u4f5c\u6587\u9898\uff0840\u5206\uff09",
        "\u9644\u52a0\u9898\uff0810\u5206\uff09",
        "1. \u9644\u52a0\u9898\u7b2c\u4e00\u9898\uff085\u5206\uff09",
        "2. \u9644\u52a0\u9898\u7b2c\u4e8c\u9898\uff082\u5206\uff09",
        "3. \u9644\u52a0\u9898\u7b2c\u4e09\u9898\uff083\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00", "\u4e09", "\u9644\u52a0\u9898"]
    assert [item["numbering"] for item in roots[1]["children"]] == ["16"]
    assert [item["numbering"] for item in roots[2]["children"]] == ["1", "2", "3"]
    assert [item["score"] for item in analysis["scores"]["childScores"]] == [24.0, 40.0, 10.0]


def test_chinese_paren_heading_should_keep_own_score_when_following_question_is_inline():
    lines = [
        "\u4e8c\u3001\u9605\u8bfb\uff0836\u5206\uff09",
        "\uff08\u4e00\uff09\u89c2\u6f6e\uff0810\u5206\uff096.\u89e3\u91ca\u4e0b\u5217\u8bcd\u8bed\uff083\u5206\uff09",
        "7.\u7ffb\u8bd1\uff084\u5206\uff09",
        "8.\u9009\u62e9\uff083\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert roots[0]["numbering"] == "\u4e8c"
    assert roots[0]["score"] == 36.0
    section = roots[0]["children"][0]
    assert section["numbering"] == "\u4e00"
    assert section["score"] == 10.0


def test_scored_question_with_zero_scored_paren_children_should_distribute_to_children():
    lines = [
        "\u4e8c\u3001\u9605\u8bfb\uff0836\u5206\uff09",
        "\uff08\u4e00\uff09\u89c2\u6f6e\uff0810\u5206\uff09",
        "7.\u628a\u4e0b\u5217\u53e5\u5b50\u7ffb\u8bd1\u6210\u73b0\u4ee3\u6c49\u8bed\uff084\u5206\uff09",
        "\uff081\uff09\u65b9\u5176\u8fdc\u51fa\u6d77\u95e8\uff0c\u4ec5\u5982\u94f6\u7ebf\u3002",
        "\uff082\uff09\u4e89\u5148\u9f13\u52c7\uff0c\u6eaf\u8fce\u800c\u4e0a\uff0c\u51fa\u6ca1\u4e8e\u9cb8\u6ce2\u4e07\u4ede\u4e2d\u3002",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    question = analysis["outlineItems"][0]["children"][0]["children"][0]
    assert question["numbering"] == "7"
    assert question["score"] == 4.0
    assert [item["score"] for item in question["children"]] == [2.0, 2.0]


def test_chinese_heading_without_delimiter_but_with_score_should_be_level1():
    lines = [
        "\u4e00\u3001\u57fa\u7840\u9898\uff0824\u5206\uff09",
        "1. \u7b2c\u4e00\u9898\uff0810\u5206\uff09",
        "\u4e8c \uff0846\u5206\uff09",
        "6. \u7b2c\u4e8c\u90e8\u5206\u7b2c\u4e00\u9898\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00", "\u4e8c"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1"]
    assert [item["numbering"] for item in roots[1]["children"]] == ["6"]


def test_arabic_section_restart_inside_chinese_root_should_promote_to_level1():
    lines = [
        "\u4e00\u3001\u8bed\u8a00\u79ef\u7d2f\u548c\u8fd0\u7528\uff0820\u5206\uff09",
        "1. \u7b2c\u4e00\u9898\uff084\u5206\uff09",
        "2. \u7b2c\u4e8c\u9898\uff086\u5206\uff09",
        "3. \u7b2c\u4e09\u9898\uff084\u5206\uff09",
        "4. \u7b2c\u56db\u9898\uff086\u5206\uff09",
        "2\u3001 \u9605\u8bfb\u7406\u89e3\uff0850\u5206\uff09",
        "\uff08\u4e00\uff09\u9605\u8bfb\u300a\u6625\u671b\u300b\uff0813\u5206\uff09",
        "\u4e09\u3001\u4f5c\u6587\uff0850\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00", "\u4e8c", "\u4e09"]


def test_extraction_start_should_keep_sequential_questions_before_loose_heading():
    lines = [
        "1、积累与运用。(47分)",
        "1. 读拼音，把词语规范地写在田字格里。（8分）",
        "2. 把加点字的正确读音用“√”标出来。（4分）",
        "3. 把下列词语补充完整。（4分）",
        "4. 给下列加点字选择正确的解释。（4分）",
        "5. 找出下列词语中的错别字并改正。（3分）",
        "6. 写出四个各包含一对反义词的词语。（4分）",
        "7. 按要求改写句子。（12分）",
        "二、阅读理解。（19分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["1", "二"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2", "3", "4", "5", "6", "7"]


def test_section_word_in_question_stem_should_not_shift_start_to_late_number():
    lines = [
        "1. 下列词语中加点字注音完全正确的一项是：（ ）（3分）",
        "2. 下面词语中没有错别字的一项是：( ) （3分）",
        "3. 下列句子中加点词语使用有误的一项是（ ）（3分）",
        "4. 下列句子中加点词语解释有误的一项是（ ）（3分）",
        "5. 下列句子有语病的一项是（ ）（3分）",
        "6. 依次填入下列各句横线处的词语，最恰当的一组是( )（3分）",
        "7. 下列各句中，标点符号的使用不合乎规范的一项是（ ）（3分）",
        "8. 文学常识搭配不正确的一项是（ ）（3分）",
        "9. 阅读下面的材料，给这段文字拟一个恰当的标题。（4分）",
        "10. 补写出下列古诗文名句中的空缺部分。（16分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert roots[0]["numbering"] == "1"
    assert roots[-1]["numbering"] == "10"


def test_currency_or_unit_expression_should_not_be_parsed_as_tight_arabic_heading():
    lines = [
        "\u4e00\u3001\u586b\u7a7a\u3002(20\u5206)",
        "4.\u5728\u62ec\u53f7\u91cc\u586b\u4e0a\u5408\u9002\u7684\u5c0f\u6570\u3002",
        "5\u51436\u89d2=( )\u5143 3\u7c7370\u5398\u7c73=( )\u7c73",
        "1\u51439\u89d22\u5206=( )\u5143 3\u5206\u7c73=( )\u7c73",
        "5.\u5728\u25cb\u91cc\u586b\u4e0a\u201c>\u201d\u201c<\u201d\u6216\u201c=\u201d\u3002",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e00"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["4", "5"]


def test_arabic_main_sections_should_stay_as_parallel_roots_without_chinese_headings():
    lines = [
        "1.\u586b\u7a7a\u3002(30\u5206)",
        "(1)\u7b2c\u4e00\u5c0f\u9898",
        "(2)\u7b2c\u4e8c\u5c0f\u9898",
        "2.\u5224\u65ad\u3002(10\u5206)",
        "(1)\u5224\u65ad\u5c0f\u9898",
        "3.\u9009\u62e9\u3002(20\u5206)",
        "4.\u666e\u901a\u8ba1\u65f6\u6cd5\u548c24\u65f6\u8ba1\u65f6\u6cd5\u4e92\u76f8\u8f6c\u5316\u3002(16\u5206)",
        "5.\u89e3\u51b3\u95ee\u9898\u3002(16\u5206)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["1", "2", "3", "4", "5"]


def test_duration_minutes_line_should_still_use_parent_remaining_score_distribution():
    lines = [
        "5.解決问题。(16分)",
        "3.聪聪周日写作业用了50分，他在9时30分写完作业。",
        "4.小明从家到电影院要走20分，他至少要在下午3时前出发。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert len(roots) == 1
    children = roots[0]["children"]
    assert [item["numbering"] for item in children] == ["3", "4"]
    assert children[0]["score"] == 8.0
    assert children[1]["score"] == 8.0


def test_chinese_tight_section_heading_should_not_merge_score_into_previous_question():
    lines = [
        "一、填空。(10分)",
        "1.第一题",
        "5.小刚小时走了千米,他每走1千米,需用多少小时?正确的算式是( )。",
        "二选择。(15分)",
        "1.第二部分第一题",
        "三计算。(40分)",
        "1.脱式计算。(15分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["一", "二", "三"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "5"]
    assert roots[0]["children"][1]["score"] == 5.0
    assert roots[2]["score"] == 40.0


def test_inline_chinese_section_heading_should_split_from_previous_question_line():
    lines = [
        "一填空。(16分)",
        "1.第一题",
        "8.第八题。二判断。(10分)",
        "1.判断第一题",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["一", "二"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "8"]
    assert [item["numbering"] for item in roots[1]["children"]] == ["1"]


def test_reading_material_paragraph_markers_should_not_be_extracted_as_questions():
    lines = [
        "二、阅读理解。(60分)",
        "(一)阅读下面的文字，回答1-4题。",
        "(1)国有国徽，校有校徽，厂有厂徽。奇怪吗?我家竟有家徽。",
        "(2)祖父在世时，膝下有父亲他们弟兄四个，个个都是牛高马大的男子汉。",
        "1.结合全文内容，分析文章第(2)段的作用。(4分)",
        "2.阅读文中画线句子，说说作者如何表现贼人的心理变化。(4分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    section_one = roots[0]["children"][0]
    assert section_one["numbering"] == "一"
    assert [item["numbering"] for item in section_one["children"]] == ["1", "2"]


def test_material_chinese_heading_inside_reading_block_should_not_be_promoted():
    lines = [
        "二、阅读理解。(60分)",
        "(一)阅读下面文字，完成1-2题。",
        "一、这是材料中的小标题，不是题目结构。",
        "1.根据材料内容回答问题。(4分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    section_one = roots[0]["children"][0]
    assert section_one["numbering"] == "一"
    assert [item["numbering"] for item in section_one["children"]] == ["1"]


def test_material_paragraph_before_first_arabic_question_should_be_pruned():
    lines = [
        "二、阅读理解。(60分)",
        "(二) 节制是心灵的闸(21分)",
        "(1)著名学者说，人类面临难题。为什么这样说呢?生活中，我们常常打败别人，却很难战胜自己。",
        "1.本文的中心论点是什么? (4分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    section_two = roots[0]["children"][0]
    assert section_two["numbering"] == "二"
    assert [item["numbering"] for item in section_two["children"]] == ["1"]


def test_inline_paren_subquestions_after_underline_should_split():
    lines = [
        "一、填空题(10分)",
        "1.按要求作答。",
        "(3)第一空__________(4)第二空__________",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    first = analysis["outlineItems"][0]["children"][0]
    assert [item["numbering"] for item in first["children"]] == ["3", "4"]


def test_inline_circled_markers_should_split_into_multiple_children():
    lines = [
        "1. 阅读下面的文字，按要求答题。(6分)",
        "(1)根据拼音写汉字。(4分)",
        "①晨（xī）______ ②细（nì）______ ③照（yào）_____ ④赋（yǔ）_____",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    sub = root["children"][0]
    assert root["numbering"] == "1"
    assert sub["numbering"] == "1"
    assert sub["children"] == []
    assert str(sub.get("blankText") or "").count("（1分）") == 4


def test_inline_circled_markers_after_paren_subquestion_should_split():
    lines = [
        "1. 阅读下面的文字，按要求答题。(6分)",
        "(1)①晨（xī）______ ②细（nì）______ ③照（yào）_____ ④赋（yǔ）_____",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    sub = root["children"][0]
    assert root["numbering"] == "1"
    assert sub["numbering"] == "1"
    assert sub["children"] == []
    assert str(sub.get("blankText") or "").count("（1.5分）") == 4


def test_wrapped_underlines_after_circled_subquestion_should_merge_into_same_node():
    lines = [
        "二、识图题。（16分）",
        "1、读右图，回答问题。",
        "①右图是____________,它出现于_____________的_________",
        "地区, 是世界上最早的_____________。（4分）",
        "②纸币与金属货币相比有什么优点？（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    q1 = root["children"][0]
    sub1 = q1["children"][0]

    assert root["numbering"] == "二"
    assert q1["numbering"] == "1"
    assert sub1["numbering"] == "①"
    assert sub1.get("children") == []
    assert len(str(sub1.get("blankText") or "").split()) == 4



def test_sentence_like_circled_translation_subquestions_should_remain_children():
    lines = [
        "（3）文言文阅读（19分）",
        "15、翻译句子。（4分）",
        "①寡人反取病焉_______________________________________________________________",
        "②得无楚之水土使民善盗耶___________________________________________________",
        "16、给下面的句子用/划分节奏，只划分一次，该怎么划分？（1分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    section = analysis["outlineItems"][0]
    q15 = section["children"][0]
    q16 = section["children"][1]

    assert section["numbering"] == "3"
    assert q15["numbering"] == "15"
    assert q16["numbering"] == "16"
    assert [child["numbering"] for child in q15["children"]] == ["①", "②"]
    assert str(q15.get("blankText") or "") == ""
    assert all("（2分）" in str(child.get("blankText") or "") for child in q15["children"])

def test_heading_with_leading_underline_prefix_should_keep_arabic_number():
    lines = [
        "（三）最小的星星也闪光（14分）",
        "____12．请你谈谈对题目的理解。（4分）",
        "13．请你用四字词语，将小说的主要情节补充完整。（3分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    third = analysis["outlineItems"][0]
    assert third["numbering"] == "三"
    assert [item["numbering"] for item in third["children"]] == ["12", "13"]
    assert third["children"][0]["blankText"] == ""


def test_inline_arabic_heading_after_blank_prompt_should_split():
    lines = [
        "三、阅读（14分）",
        "13．请你用四字词语，将小说的主要情节补充完整。（3分）",
        "（ ）——星夜家访——（ ）——（ ） 14．从人物描写角度分析下面句子的表达效果。（3分）",
        "15．仔细品味最后一段中的划线句子，说说它在内容和结构上的作用。（4分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "三"
    assert [item["numbering"] for item in root["children"]] == ["13", "14", "15"]


def test_inline_compact_arabic_heading_after_blank_tail_should_split():
    lines = [
        "三、词语积累与运用。（14分）",
        "1．照样子写出带有“清”字的词语，分别和下面的词语搭配。（填上的词语不重复）（3分）",
        "2．在下列词语补充完整。（7分）",
        "（    ）（    ）落后 （    ）然如故 囫囵（    ）（    ）   一（    ）无（    ）3．写出表示“多”的成语。（4分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["三"]
    section = roots[0]
    assert section["score"] == 14.0
    assert [item["numbering"] for item in section["children"]] == ["1", "2", "3"]
    assert section["children"][1]["score"] == 7.0
    assert section["children"][2]["score"] == 4.0
    assert section["children"][1]["children"] == []


def test_compact_numeric_list_in_stem_should_not_be_split_as_extra_question():
    lines = [
        "二．填空题：本题共12分；第24题4分，第25题8分。",
        "24．用接在50 Hz交流电源上的打点计时器测定小车速度，分别标明0、l、2、3、4……，量得0与1两点间距离x1=30mm，3与4两点间距离x2=48mm，求平均速度。（4分）",
        "25．用落体验证机械能守恒定律（8分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    children = roots[0]["children"]
    assert [item["numbering"] for item in children] == ["24", "25"]
    assert children[0]["score"] == 4.0
    assert children[1]["score"] == 8.0


def test_duplicated_outer_and_paren_numbering_should_be_nested_under_parent_question():
    lines = [
        "四、论述、计算题（30分）",
        "22．（12分）求：",
        "1. （1）小孩与冰车受到的支持力大小；（4分）",
        "2. （2）小孩与冰车的加速度大小；（4分）",
        "3. （3）拉力作用t =8s时间内，冰车位移的大小。（4分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["四"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["22"]
    q22 = roots[0]["children"][0]
    assert q22["score"] == 12.0
    assert [item["numbering"] for item in q22["children"]] == ["1", "2", "3"]
    assert [item["score"] for item in q22["children"]] == [4.0, 4.0, 4.0]


def test_wrapped_l1_l2_continuation_should_not_create_extra_question():
    lines = [
        "一、选择题（4分）",
        "7．如图所示的电路中（灯L",
        "1、L2两端电压均未超过其额定电压），下列说法中正确的是（2分）",
        "8．下一题（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["一"]
    children = roots[0]["children"]
    assert [item["numbering"] for item in children] == ["7", "8"]
    assert "L1、L2" in str(children[0].get("rawText") or "")
    assert children[0]["score"] == 2.0


def test_parenthesized_range_markers_should_not_create_outline_nodes():
    lines = [
        "3、运用课外阅读积累的知识，完成",
        "(1)—",
        "(2)题。(7分)",
        "(1).以上选段选自_____________，作者是__________。",
        "(2).请概述选文省略的有关情节。(4分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["3"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2"]


def test_chinese_tight_heading_with_question_mark_and_score_should_be_kept():
    lines = [
        "三找规律,看看第五行该填哪些数?(10分)",
        "1.子题",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["三"]
    assert roots[0]["score"] == 10.0


def test_chinese_tight_heading_with_guide_id_suffix_should_be_kept():
    lines = [
        "五观察填表。(22分)(导学号 58702200)",
        "1. 子题",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["五"]
    assert roots[0]["score"] == 22.0


def test_heading_score_should_prefer_current_question_when_next_question_is_inline():
    lines = [
        "二、阅读（30分）",
        "23. 第二问的题干描述。（4分） 第24题 下面一题标题（20分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["23"]
    assert roots[0]["children"][0]["score"] == 4.0


def test_circled_material_paragraph_with_question_mark_should_not_be_extracted():
    lines = [
        "二、阅读（60分）",
        "（五）半岛小夜曲",
        "⑦在霓虹灯下，沿着街道一路走来。谁家的女人在夜影里喊：明天还上不上学了？",
        "23、以“半岛小夜曲”为标题，好在哪里？（3分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    section = roots[0]["children"][0]
    assert section["numbering"] == "五"
    assert [item["numbering"] for item in section["children"]] == ["23"]


def test_reading_material_blank_paragraph_should_not_create_empty_number_node():
    lines = [
        "五、阅读短文，回答问题。（20分）",
        "（一）《月光曲》节选（8分）",
        "皮鞋匠静静地________着。他好像__________着大海，月亮正从____________的地方升起来。_________的海面上，霎时间________了银光。",
        "1．在“______”填上所缺的部分。（3分）",
        "2．皮鞋匠眼前出现的景象与钢琴曲《月光曲》有什么联系？（3分）",
        "3．把描绘钢琴曲《月光曲》内容的句子用“________”标出来。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "五"
    section = root["children"][0]
    assert section["numbering"] == "一"
    assert [item["numbering"] for item in section["children"]] == ["1", "2", "3"]


def test_writing_instruction_options_should_not_create_extra_outline_nodes():
    lines = [
        "三、写作（60分）",
        "28、根据下面的题目，按要求作文。",
        "题目：（一）请以“温暖的旅程”为题，写一篇不少于600字的记叙文。",
        "（二）请以“一勤天下无难事”为题，写一篇不少于600字的议论文。",
        "要求：（1）上列两题，请任选其一作答；",
        "（2）文中不得出现真实的人名、地名、校名。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["三"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["28"]


def test_parent_score_should_distribute_to_slot_like_paren_children_in_outline():
    lines = [
        "一、基础知识（10分）",
        "2. 根据拼音写出相应词语。（4分）",
        "(1) 词语一（ ）",
        "(2) 词语二（ ）",
        "(3) 词语三（ ）",
        "(4) 词语四（ ）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q2 = analysis["outlineItems"][0]["children"][0]
    assert q2["score"] == 4.0
    assert [child["score"] for child in q2["children"]] == [1.0, 1.0, 1.0, 1.0]
    assert all(str(child.get("blankText") or "") == "" for child in q2["children"])


def test_parent_score_should_distribute_to_non_slot_children():
    lines = [
        "一、阅读（10分）",
        "2. 问答题（4分）",
        "(1) 请概括本文主旨。",
        "(2) 请分析作者情感。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q2 = analysis["outlineItems"][0]["children"][0]
    assert q2["score"] == 4.0
    assert [child["score"] for child in q2["children"]] == [2.0, 2.0]


def test_parent_score_should_distribute_to_underline_slot_children():
    lines = [
        "六、日积月累。（4分）",
        "2. 请简要写出理由。（4分）",
        "（1）________________",
        "（2）________________",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q2 = analysis["outlineItems"][0]["children"][0]
    assert q2["score"] == 4.0
    assert [child["score"] for child in q2["children"]] == [2.0, 2.0]
    assert all("（2分）" in str(child.get("blankText") or "") for child in q2["children"])


def test_long_underline_continuation_should_not_create_leaf_slot_children():
    lines = [
        "四、词句理解。（12分）",
        "2．按要求完成句子练习。（8分）",
        "（1）祖宗疆土，当以死守，不可以尺寸与人。（翻译）",
        "______________________________________________________________________________",
        "（2）灯下读书。（扩写）",
        "______________________________________________________________________________",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q2 = analysis["outlineItems"][0]["children"][0]
    assert q2["numbering"] == "2"
    assert [item["numbering"] for item in q2["children"]] == ["1", "2"]
    first = q2["children"][0]
    second = q2["children"][1]
    assert first["score"] == 4.0
    assert second["score"] == 4.0
    assert first["children"] == []
    assert second["children"] == []
    assert str(first.get("blankText") or "") == ""
    assert str(second.get("blankText") or "") == ""


def test_paren_arabic_reading_sections_should_not_nest_under_previous_question():
    lines = [
        "一、语言积累和运用（20分）",
        "1、前题。（4分）",
        "2、阅读理解（50分）",
        "（一）阅读《春望》，回答后面的问题（13分）",
        "5、第一问。（1分）",
        "8、第四问。（4分）",
        "（2）阅读下面文段，回答问题（18分）",
        "9、第二部分第一问。（3分）",
        "（3）文言文阅读（19分）",
        "14、第三部分第一问。（6分）",
        "三、写作（50分）",
        "19、作文。（50分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")

    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.get("children", []))

    all_nodes = list(walk(analysis["outlineItems"]))
    node8 = next(node for node in all_nodes if node.get("numbering") == "8")
    assert node8["children"] == []

    section_two = next(
        node for node in all_nodes
        if node.get("numbering") in {"2", "\u4e8c"} and node.get("score") == 18.0
    )
    section_three = next(
        node for node in all_nodes
        if node.get("numbering") in {"3", "\u4e09"} and node.get("score") == 19.0
    )
    assert section_two is not None
    assert section_three is not None
    assert [child.get("numbering") for child in section_two.get("children", [])] == ["9"]
    assert [child.get("numbering") for child in section_three.get("children", [])] == ["14"]
    assert str(section_two.get("blankText") or "") == ""


def test_mixed_reading_paren_section_numbering_should_preserve_original_arabic_markers():
    lines = [
        "一、语言积累和运用（20分）",
        "4、班级要召开“我的中国心”的主题班会，请你设计一段开场白和一段结束语。（6分）",
        "二、阅读理解（50分）",
        "（一）阅读《春望》，回答后面的问题（13分）",
        "5、诗的前四句都统领在一个“____”字中。（1分）",
        "（2）阅读下面文段，回答问题（18分）",
        "9、第二部分第一问。（3分）",
        "（3）文言文阅读（19分）",
        "14、第三部分第一问。（6分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]

    reading_root = roots[1]
    assert reading_root["numbering"] == "二"
    assert [child["numbering"] for child in reading_root["children"]] == ["一", "2", "3"]
    assert str(reading_root["children"][1].get("rawText") or "").startswith("（2）")
    assert str(reading_root["children"][2].get("rawText") or "").startswith("（3）")


def test_question_tail_with_following_wrapped_underline_line_should_merge_into_same_raw_text():
    lines = [
        "二、阅读理解（50分）",
        "（一）阅读《春望》，回答后面的问题（13分）",
        "7、诗中“草木深”表面上写的是__________________________________________________，",
        "实际上是写____________________________________________________________。（4分）",
        "8、本诗将眼前景、胸中情融为一体。（4分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q7 = analysis["outlineItems"][0]["children"][0]["children"][0]

    assert q7["numbering"] == "7"
    assert "实际上是写" in str(q7.get("rawText") or "")
    assert str(q7.get("blankText") or "").count("（2分）") == 2


def test_question_tail_should_not_merge_plain_sentence_with_score_into_previous_blank_question():
    lines = [
        "二、阅读理解（20分）",
        "17、文章第(1)段中的划线句子属于什么描写，有何作用?(3分)_______________",
        "(1)陪一个父亲，去八百里外的戒毒所，探视他在那里戒毒的儿子。（1分）",
        "18、下一题。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q17 = analysis["outlineItems"][0]["children"][0]
    assert q17["numbering"] == "17"
    assert "陪一个父亲" not in str(q17.get("rawText") or "")


def test_parenthesized_heading_with_score_should_not_attach_following_plain_text_line():
    lines = [
        "二、阅读理解（20分）",
        "（2）根据材料判断正误。 ( ) (1分)",
        "（1）郑州的剪纸活动在除夕至正月十五最为盛行。",
        "（3）下一问。 ( ) (1分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    second = analysis["outlineItems"][0]["children"][0]
    assert second["numbering"] == "2"
    assert "郑州的剪纸活动" not in str(second.get("rawText") or "")


def test_empty_numbering_child_starting_with_paren_index_should_not_merge_into_previous_sibling():
    nodes = [
        {
            "numbering": "17",
            "title": "第17题",
            "rawText": "17、第17题（3分）_______________",
            "blankText": "_______________（3分）",
            "score": 3.0,
            "_tokenType": "arabic",
            "children": [
                {
                    "numbering": "",
                    "title": "(1)郑州的剪纸活动在除夕至正月十五",
                    "rawText": "(1)郑州的剪纸活动在除夕至正月十五（1分）",
                    "blankText": "",
                    "score": 1.0,
                    "children": [],
                }
            ],
        }
    ]
    _merge_empty_numbering_leaf_nodes(nodes)
    assert len(nodes[0]["children"]) == 1
    assert nodes[0]["children"][0]["rawText"].startswith("(1)郑州")
    assert "郑州的剪纸活动" not in str(nodes[0].get("rawText") or "")


def test_empty_numbering_long_material_paragraph_should_not_merge_into_previous_sibling():
    nodes = [
        {
            "numbering": "17",
            "title": "第17题",
            "rawText": "17、文章第(1)段中的句子有什么作用?(3分)_______________",
            "blankText": "_______________（3分）",
            "score": 3.0,
            "_tokenType": "arabic",
            "children": [
                {
                    "numbering": "",
                    "title": "有一天，我半信半疑。过了好几天，它活了，又长出了新的叶子。",
                    "rawText": "有一天，我半信半疑。过了好几天，它活了，又长出了新的叶子。",
                    "blankText": "",
                    "score": 0.0,
                    "children": [],
                }
            ],
        }
    ]
    _merge_empty_numbering_leaf_nodes(nodes)
    assert len(nodes[0]["children"]) == 1
    assert "半信半疑" in str(nodes[0]["children"][0].get("rawText") or "")
    assert "半信半疑" not in str(nodes[0].get("rawText") or "")


def test_duplicate_paren_arabic_siblings_should_preserve_source_raw_prefix():
    nodes = [
        {
            "numbering": "1",
            "title": "第1题",
            "rawText": "1、第1题",
            "_tokenType": "arabic",
            "children": [
                {"numbering": "1", "rawText": "（1）甲", "title": "（1）甲", "_tokenType": "paren_arabic", "children": []},
                {"numbering": "2", "rawText": "（2）乙", "title": "（2）乙", "_tokenType": "paren_arabic", "children": []},
                {"numbering": "1", "rawText": "（1）丙", "title": "（1）丙", "_tokenType": "paren_arabic", "children": []},
                {"numbering": "2", "rawText": "（2）丁", "title": "（2）丁", "_tokenType": "paren_arabic", "children": []},
            ],
        }
    ]
    _normalize_duplicate_paren_arabic_siblings(nodes)
    children = nodes[0]["children"]
    assert [item["numbering"] for item in children] == ["1", "2", "1", "2"]
    assert [item["rawText"] for item in children] == ["（1）甲", "（2）乙", "（1）丙", "（2）丁"]


def test_mixed_level1_sequence_should_normalize_arabic_root_to_chinese():
    lines = [
        "\u4e00\u3001\u8bed\u8a00\u79ef\u7d2f\u548c\u8fd0\u7528\uff0820\u5206\uff09",
        "1\u3001\u8bf7\u7ed9\u4e0b\u5217\u52a0\u70b9\u5b57\u6ce8\u97f3\uff084\u5206\uff09",
        "2\u3001\u9ed8\u5199\u586b\u7a7a\uff086\u5206\uff09",
        "3\u3001\u8bed\u75c5\u4fee\u6539\uff084\u5206\uff09",
        "4\u3001\u8bed\u8a00\u8fd0\u7528\uff086\u5206\uff09",
        "2\u3001 \u9605\u8bfb\u7406\u89e3\uff0850\u5206\uff09",
        "\uff08\u4e00\uff09\u9605\u8bfb\u300a\u6625\u671b\u300b\uff0813\u5206\uff09",
        "5\u3001\u8bd7\u7684\u524d\u56db\u53e5\u95ee\u9898\uff081\u5206\uff09",
        "\uff082\uff09 \u9605\u8bfb\u4e0b\u9762\u6587\u6bb5\uff0818\u5206\uff09",
        "9\u3001\u7b2c\u4e8c\u90e8\u5206\u7b2c\u4e00\u95ee\uff083\u5206\uff09",
        "\u4e09\u3001\u5199\u4f5c\uff0850\u5206\uff09",
        "19\u3001\u4f5c\u6587\uff0850\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [node.get("numbering") for node in roots] == ["\u4e00", "\u4e8c", "\u4e09"]


def test_section_heading_should_not_absorb_intermediate_underline_lines():
    lines = [
        "\u4e00\u3001\u8bed\u8a00\u79ef\u7d2f\u548c\u8fd0\u7528\uff0820\u5206\uff09",
        "1\u3001\u524d\u9898\u3002\uff084\u5206\uff09",
        "2\u3001 \u9605\u8bfb\u7406\u89e3\uff0850\u5206\uff09",
        "\uff082\uff09 \u9605\u8bfb\u4e0b\u9762\u6587\u6bb5\uff0c\u56de\u7b54\u95ee\u9898\uff0818\u5206\uff09",
        "____________________________________________________________",
        "9\u3001\u7b2c\u4e8c\u90e8\u5206\u7b2c\u4e00\u95ee\uff083\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.get("children", []))

    section_two = next(
        node
        for node in walk(analysis["outlineItems"])
        if node.get("numbering") == "2" and node.get("score") == 18.0
    )
    assert str(section_two.get("blankText") or "") == ""
    assert [child.get("numbering") for child in section_two.get("children", [])] == ["9"]


def test_mixed_chinese_and_paren_arabic_sections_should_normalize_to_chinese():
    lines = [
        "\u4e8c\u3001\u9605\u8bfb\u7406\u89e3\uff0850\u5206\uff09",
        "\uff08\u4e00\uff09\u9605\u8bfbA\uff0813\u5206\uff09",
        "5\u3001A1\uff081\u5206\uff09",
        "\uff082\uff09\u9605\u8bfbB\uff0818\u5206\uff09",
        "9\u3001B1\uff083\u5206\uff09",
        "\uff083\uff09\u9605\u8bfbC\uff0819\u5206\uff09",
        "14\u3001C1\uff086\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "\u4e8c"
    assert [child["numbering"] for child in root["children"]] == ["\u4e00", "\u4e8c", "\u4e09"]
    assert root["children"][1]["rawText"].startswith("\uFF08\u4e8c\uFF09")


def test_arabic_heading_with_leading_paren_subquestion_should_keep_parent_and_children():
    lines = [
        "二．综合运用（6分）",
        "9．（1）请用一句话概括这则新闻的内容。（2分）",
        "（2）请针对这则新闻的内容进行简要评论，不少于40字。（2分）",
        "（3）不同的传统节日，有不同的故事或传说。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")

    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["9"]
    q9 = roots[0]["children"][0]
    assert [item["numbering"] for item in q9["children"]] == ["1", "2", "3"]
    assert [item["score"] for item in q9["children"]] == [2.0, 2.0, 2.0]


def test_inline_consecutive_paren_subquestions_should_split_into_separate_children():
    lines = [
        "12.请用“／”标示下面语句的语意停顿（每句标一处）。（4分）",
        "（1）至于夏水襄陵 （2）自既望以至十八日为盛",
        "13.解释下列加点的词语。（8分）",
        "（1）或王命急宣 （2）虽乘奔御风",
        "（3）既而渐近 （4）则玉城雪岭际天而来",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    q12 = roots[0]
    q13 = roots[1]

    assert q12["numbering"] == "12"
    assert [item["numbering"] for item in q12["children"]] == ["1", "2"]
    assert "（2）" not in str(q12["children"][0].get("rawText") or "")
    assert "（1）" not in str(q12["children"][1].get("rawText") or "")

    assert q13["numbering"] == "13"
    assert [item["numbering"] for item in q13["children"]] == ["1", "2", "3", "4"]


def test_scored_followup_question_after_paren_subquestion_should_merge_into_previous():
    lines = [
        "二、材料题（40分）",
        "26. 阅读材料，回答问题。（6分）",
        "（1）材料一中的“开元全盛”时代是哪个皇帝当政时期？（2分）",
        "由材料一可知唐朝主要的粮食品种是什么？（2分）",
        "（2）阅读材料二，结合教材知识指出，开元年间统治者采取了哪些措施？（2分）",
        "（3）除了“开元盛世”，唐朝前期还出现了哪些盛世、治世局面？（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]

    section_two = roots[0]
    assert section_two["numbering"] == "二"
    q26 = section_two["children"][0]
    assert q26["numbering"] == "26"
    assert [item["numbering"] for item in q26["children"]] == ["1", "2", "3"]
    assert q26["children"][0]["score"] == 4.0
    assert "由材料一可知" in str(q26["children"][0].get("rawText") or "")
    assert q26["children"][0]["children"] == []


def test_arabic_question_title_should_strip_inline_option_tail():
    lines = [
        "一、单项选择（30分）",
        "6．1947年3月，中共中央撤离延安是在国民党军队大举进攻＿＿时 （ ）A．山东解放区 B．中原解放区 C．陕甘宁解放区 D．大别山根据地",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    q6 = root["children"][0]
    assert q6["numbering"] == "6"
    assert "A．" not in str(q6.get("title") or "")


def test_number_only_placeholder_lines_should_not_be_extracted_as_questions():
    lines = [
        "二、材料分析（70分）",
        "11．阅读材料，回答问题。",
        "（1）子问1",
        "12．阅读材料，回答问题。",
        "（1）子问2",
        "1.",
        "2.",
        "3.",
        "4.",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "二"
    assert [item["numbering"] for item in root["children"]] == ["11", "12"]


def test_scored_chinese_question_section_with_answer_card_hint_should_not_be_filtered_as_prelude():
    lines = [
        "注意事项：",
        "1．试题的答案书写在答题卡上，不得在试题卷上直接作答。",
        "2．作答前认真阅读答题卡上的注意事项。",
        "一、选择题：本大题共15小题，每小题1分，共15分。请按要求在答题卡上作答。",
        "1. 第一题（1分）",
        "2. 第二题（1分）",
        "二、非选择题：本大题共2小题，共10分。",
        "16. 阅读材料，回答问题。（5分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["一", "二"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["1", "2"]
    assert [item["numbering"] for item in roots[1]["children"]] == ["16"]


def test_sequential_arabic_questions_should_not_be_nested_under_first_question():
    lines = [
        "1．汉朝建立的时间是 （2分） （ ）",
        "2．西汉的都城是 （2分） （ ）",
        "3．公元前200年，在白登山被匈奴围困7天7夜的皇帝是 （2分） （ ）",
        "10．阅读材料，回答问题：（15分）",
        "（1）材料说明了什么问题？",
        "（2）出现这种问题的原因是什么？",
        "11．阅读材料，回答问题。（27分）",
        "（1）两则材料分别说明了什么问题？",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["1", "2", "3", "10", "11"]
    assert [item["numbering"] for item in roots[3]["children"]] == ["1", "2"]
    assert [item["numbering"] for item in roots[4]["children"]] == ["1"]


def test_unnumbered_scored_section_should_not_auto_generate_arabic_numbering():
    lines = [
        "16.填空。（6分）",
        "阅读下文，完成题目。（23分）",
        "17.阅读上述材料，下列说法不符合文意的一项是（ ）（4分）",
        "18.下列对传统阅读与数字阅读的概述，符合文意的一项是（ ）（4分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]

    assert [item["numbering"] for item in roots] == ["16", ""]
    section = roots[1]
    assert section["score"] == 23.0
    assert section["rawText"] == "阅读下文，完成题目。（23分）"
    assert [item["numbering"] for item in section["children"]] == ["17", "18"]


def test_directive_parent_score_should_distribute_to_paren_children():
    lines = [
        "12.请用“／”标示下面语句的语意停顿（每句标一处）。（4分）",
        "（1）至于夏水襄陵",
        "（2）自既望以至十八日为盛",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["12"]
    q12 = roots[0]
    assert [item["numbering"] for item in q12["children"]] == ["1", "2"]
    assert [item["score"] for item in q12["children"]] == [2.0, 2.0]

    score_tree = analysis["scores"]["childScores"][0]
    assert [item["score"] for item in score_tree["childScores"]] == [2.0, 2.0]


def test_reading_article_markers_should_not_be_extracted_as_chinese_paren_levels():
    lines = [
        "三、阅读下面文章，完成相关问题。（38分）",
        "（一）《我的母亲》（7分）",
        "10. 第一问（2分）",
        "11. 第二问（3分）",
        "（二）（8分）",
        "12. 第三问（4分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")

    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["三"]
    # "（一）/（二）" here are article markers, not structural outline levels.
    assert [item["numbering"] for item in roots[0]["children"]] == ["10", "11", "12"]


def test_reading_named_chinese_paren_markers_should_flatten_when_children_are_arabic_questions():
    lines = [
        "二、阅读（36分）",
        "（一）观潮（10分）",
        "6. 第一问（3分）",
        "7. 第二问（4分）",
        "8. 第三问（3分）",
        "（二）雪人（12分）",
        "9. 第四问（4分）",
        "10. 第五问（4分）",
        "11. 第六问（4分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    # "（一）观潮 / （二）雪人" are reading material partitions, not
    # extractable structural nodes.
    assert [item["numbering"] for item in roots[0]["children"]] == ["6", "7", "8", "9", "10", "11"]


def test_scored_reading_chinese_paren_partitions_should_be_kept_when_numbering_restarts():
    lines = [
        "七、阅读。（29分）",
        "（一）阅读课文节选，完成练习。（11分）",
        "1. 第一问。（2分）",
        "2. 第二问。（2分）",
        "（二）阅读短文，完成练习。（18分）",
        "1. 第三问。（2分）",
        "2. 第四问。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["七"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["一", "二"]
    assert [item["numbering"] for item in roots[0]["children"][0]["children"]] == ["1", "2"]
    assert [item["numbering"] for item in roots[0]["children"][1]["children"]] == ["1", "2"]


def test_scored_reading_partitions_with_reading_prompt_titles_should_not_be_ignored():
    lines = [
        "二、阅读理解。（60分）",
        "（一）阅读下面的文字，回答1-4题。（23分）",
        "1. 第一问。（4分）",
        "2. 第二问。（5分）",
        "（二）阅读下面的文字，回答1-4题。（21分）",
        "1. 第三问。（4分）",
        "2. 第四问。（5分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["一", "二"]
    assert [item["numbering"] for item in roots[0]["children"][0]["children"]] == ["1", "2"]
    assert [item["numbering"] for item in roots[0]["children"][1]["children"]] == ["1", "2"]


def test_continuous_arabic_questions_should_not_promote_middle_as_section():
    lines = [
        "1．给下列加点的字词选择正确的解释。(填序号)（20分）",
        "2．下列诗句中与乡村田园景色无关的一项是（ ）。（20分）",
        "3．与“山衔落日浸寒漪”使用了相同的修辞方法的诗句是（ ）。（20分）",
        "4．对人物的描写和其他诗句不同的一项是（ ）。 （20分）",
        "5．下面说法不正确的一项是（ ） （20分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["1", "2", "3", "4", "5"]
    assert all(not item.get("children") for item in roots)


def test_reading_material_circled_paragraph_marker_should_not_be_extracted_as_question():
    lines = [
        "三、阅读下面材料，回答问题。（10分）",
        "（六）地震后为什么会有余震（5分）",
        "③ 地震后为什么会有余震呢？",
        "25．请概括余震的另外两个特征及余震产生的原因。（2分）",
        "26．第②段采用的说明方法除打比方之外，还有什么说明方法？（3分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["三"]
    section = roots[0]["children"][0]
    assert section["numbering"] in {"六", "6"}
    assert [item["numbering"] for item in section["children"]] == ["25", "26"]


def test_reading_article_partition_markers_with_scores_should_flatten_to_question_peers():
    lines = [
        "三、阅读下面文章，完成相关问题。（38分）",
        "（一）《我的母亲》（7分）",
        "10. 第一问。（2分）",
        "11. 第二问。（3分）",
        "12. 第三问。（2分）",
        "（二）（8分）",
        "13. 第四问。（1分）",
        "14. 第五问。（2分）",
        "15. 第六问。（2分）",
        "16. 第七问。（3分）",
        "（六）地震后为什么会有余震（5分）",
        "25. 第八问。（2分）",
        "26. 第九问。（1分）",
        "27. 第十问。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["三"]
    assert [item["numbering"] for item in roots[0]["children"]] == [
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "25",
        "26",
        "27",
    ]


def test_article_explanatory_chinese_paren_heading_should_not_be_extracted():
    lines = [
        "二、阅读（10分）",
        "24. 阅读文章，回答问题。（10分）",
        "（一）地震的形成",
        "地震是地壳运动的结果。",
        "1. 第一问。（2分）",
        "2. 第二问。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["二"]
    q24 = roots[0]["children"][0]
    assert q24["numbering"] == "24"
    assert [item["numbering"] for item in q24["children"]] == ["1", "2"]


def test_scored_section_text_after_paren_question_should_not_become_child():
    lines = [
        "1. 基础知识（15分）",
        "(5)．下面对文章内容的理解有误的一项是（ ）",
        "A．第一项",
        "B．第二项",
        "C．第三项",
        "D．第四项",
        "古诗文填空（15分）",
        "2.孟武伯问孝。子曰：“____”。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["1", "2"]

    root = roots[0]
    q5 = root["children"][0]
    assert q5["numbering"] == "5"
    assert q5["children"] == []

    second_root = roots[1]
    assert second_root["score"] == 15.0
    assert [item["numbering"] for item in second_root["children"]] == ["2"]


def test_scored_section_text_should_promote_to_chinese_root_peer():
    lines = [
        "一、基础知识（36分）",
        "(5)．下面对文章内容的理解有误的一项是（ ）",
        "A．第一项",
        "B．第二项",
        "C．第三项",
        "D．第四项",
        "古诗文填空（15分）",
        "2.孟武伯问孝。子曰：“____”。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]

    assert [item["numbering"] for item in roots] == ["一", "二"]
    assert roots[0]["children"][0]["children"] == []
    assert roots[1]["score"] == 15.0
    assert [item["numbering"] for item in roots[1]["children"]] == ["2"]


def test_reading_passage_blank_line_before_first_question_should_not_create_anonymous_child():
    lines = [
        "六、语段阅读(9分)",
        "阅读《搭石》，完成练习。",
        "搭石，构成了家乡的一道风景。秋凉以后，人们早早地将搭石摆放好。________别处都有搭石，唯独这一处没有，人们会谴责这里的人懒惰。",
        "15．（2分）在文中横向上填上恰当的关联词。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["六"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["15"]
    assert roots[0]["children"][0]["score"] == 2.0


def test_per_item_score_heading_should_expand_total_and_child_scores():
    lines = [
        "二、古诗文阅读与积累(24分)",
        "（三）古诗文积累(8分)",
        "12. 填补下列名句的空缺处或按要求填空。（每空1分）",
        "(1)树树皆秋色，_____________________。",
        "(2)土地平旷，_______________________。",
        "(3)出淤泥而不染，______________________。",
        "(4)________________，孤帆天际看。",
        "(5)《长歌行》名句_____________________，_____________________。",
        "(6)《陋室铭》主旨_____________________，_____________________。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    section = roots[0]["children"][0]
    assert section["numbering"] in {"三", "3"}
    assert section["score"] == 8.0
    q12 = section["children"][0]
    assert q12["numbering"] == "12"
    assert q12["score"] == 8.0
    assert [item["score"] for item in q12["children"]] == [1.0, 1.0, 1.0, 1.0, 2.0, 2.0]


def test_parent_remaining_distribution_should_not_overassign_mixed_nested_children():
    lines = [
        "二、填空题（20分）",
        "21．请回答：",
        "(1) __________",
        "(2) __________",
        "22．请填空：__________ __________",
        "23．请回答：",
        "(1) __________",
        "(2) __________",
        "24．请填空：__________ __________",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "二"
    assert root["score"] == 20.0

    children = root["children"]
    assert [item["numbering"] for item in children] == ["21", "22", "23", "24"]
    assert [item["score"] for item in children] == [5.0, 5.0, 5.0, 5.0]
    assert [item["score"] for item in children[0]["children"]] == [2.5, 2.5]
    assert [item["score"] for item in children[2]["children"]] == [2.5, 2.5]

    def display_score(node):
        node_children = node.get("children", [])
        if node_children:
            return round(sum(display_score(child) for child in node_children), 2)
        return round(float(node.get("score") or 0), 2)

    assert display_score(root) == 20.0


def test_parent_with_explicit_score_and_zero_slot_descendants_should_backfill_leaf_scores():
    lines = [
        "\u4e09\u3001\u628a\u4e0b\u9762\u7684\u8bcd\u8bed\u8865\u5145\u5b8c\u6574\uff0c\u518d\u6309\u8981\u6c42\u5b8c\u6210\u7ec3\u4e60\u3002(3\u5206)",
        "( )( )\u5730\u9614",
        "( )( )\u6591\u6593",
        "1.\u6839\u636e\u610f\u601d\u586b\u7a7a\u3002",
        "(1)\u5f62\u5bb9\u4eba\u6216\u793e\u4f1a\u5bcc\u6709\u671d\u6c14\u3002 ( )",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["score"] == 3.0

    def display_score(node):
        children = node.get("children", [])
        if children:
            return sum(display_score(child) for child in children)
        return float(node.get("score") or 0)

    assert display_score(root) == 3.0
    flat = []
    stack = [root]
    while stack:
        current = stack.pop(0)
        flat.append(current)
        stack.extend(current.get("children", []))
    positive_leaves = [
        node
        for node in flat
        if not node.get("children")
        and float(node.get("score") or 0) > 0
    ]
    assert len(positive_leaves) >= 3
    first_leaf = root["children"][0]
    assert str(first_leaf.get("blankText") or "").count("____") >= 2


def test_writing_section_answer_lines_should_not_be_merged_as_blank_slots():
    lines = [
        "三、写作（50分）",
        "19、阅读下面文字，根据要求作文：",
        "_______文题_________________",
        "____",
        "____",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "三"
    assert root["score"] == 50.0
    assert [item["numbering"] for item in root["children"]] == ["19"]
    essay = root["children"][0]
    assert essay["score"] == 50.0
    assert essay["children"] == []
    assert str(essay.get("blankText") or "") == ""


def test_multi_blank_leaf_with_single_total_score_should_rebalance_evenly():
    lines = [
        "一、语言积累和运用（20分）",
        "2、默写填空（6分）",
        "1）人生自古谁无死，_____________________________。",
        "2）_____________________________，铁马冰河入梦来。",
        "3）默写《泊秦淮》",
        "________________________，______________________。",
        "________________________，______________________。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q2 = analysis["outlineItems"][0]["children"][0]
    assert q2["numbering"] == "2"
    assert q2["score"] == 6.0
    assert [child["numbering"] for child in q2["children"]] == ["1", "2", "3"]
    assert str(q2.get("blankText") or "") == ""
    assert str(q2["children"][0].get("blankText") or "").count("（1分）") == 1
    assert str(q2["children"][1].get("blankText") or "").count("（1分）") == 1
    assert str(q2["children"][2].get("blankText") or "").count("（1分）") == 4


def test_two_blank_continuation_with_single_total_score_should_rebalance_evenly():
    lines = [
        "一、语言积累和运用（20分）",
        "3、下面文段有两处语病，请找出来并修改。（4分）",
        "1） ______________________________________________________________________",
        "2） ______________________________________________________________________",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q3 = analysis["outlineItems"][0]["children"][0]
    assert q3["numbering"] == "3"
    assert q3["score"] == 4.0
    assert [child["numbering"] for child in q3["children"]] == ["1", "2"]
    assert str(q3.get("blankText") or "") == ""
    assert str(q3["children"][0].get("blankText") or "").count("（2分）") == 1
    assert str(q3["children"][1].get("blankText") or "").count("（2分）") == 1


def test_scored_empty_bracket_leaf_should_fill_blank_text_with_score():
    lines = [
        "一、选择题（6分）",
        "3. 下列选项正确的是（ ）（3分）",
        "4. 下列选项错误的是（ ）（3分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    q3 = root["children"][0]
    q4 = root["children"][1]
    assert q3["score"] == 3.0
    assert q4["score"] == 3.0
    assert "（3分）" in str(q3.get("blankText") or "")
    assert "（3分）" in str(q4.get("blankText") or "")


def test_scored_paren_subquestion_single_slot_should_not_create_blank_slot_text():
    lines = [
        "一、基础知识（4分）",
        "2. 根据拼音写出相应词语。（4分）",
        "(1) 词语一（ ）（1分）",
        "(2) 词语二（ ）（1分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q2 = analysis["outlineItems"][0]["children"][0]
    assert q2["score"] == 4.0
    assert [child["score"] for child in q2["children"]] == [1.0, 1.0]
    assert all(str(child.get("blankText") or "") == "" for child in q2["children"])


def test_writing_section_single_child_should_inherit_section_score_for_display_consistency():
    lines = [
        "三、作文（40分）",
        "16. 阅读下面的文字，按要求作文。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["numbering"] == "三"
    assert root["score"] == 40.0
    assert len(root["children"]) == 1
    assert root["children"][0]["numbering"] == "16"
    assert root["children"][0]["score"] == 40.0


def test_writing_requirement_bullets_should_not_be_extracted_as_subquestions():
    lines = [
        "二、综合实践与作文（60分）",
        "（二）作文（50分）",
        "28．以下作文，任选其一。",
        "作文要求：",
        "(1)选择你最擅长的文体，结合你最熟悉的生活，抒发你最真挚的情感；",
        "(2)认真书写，力求工整、美观；",
        "(3)文章不得出现真实的校名、姓名；",
        "(4)不少于600字。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    composition_section = roots[0]["children"][0]
    q28 = composition_section["children"][0]
    assert q28["numbering"] == "28"
    assert q28["score"] == 50.0
    assert q28["children"] == []

    # requirement lines should not appear as extracted nodes
    flat_raw = []
    stack = list(roots)
    while stack:
        node = stack.pop(0)
        flat_raw.append(str(node.get("rawText") or ""))
        stack.extend(node.get("children", []))
    assert not any(raw.startswith("(1)选择你最擅长的文体") for raw in flat_raw)
    assert not any(raw.startswith("(2)认真书写") for raw in flat_raw)
    assert not any(raw.startswith("(3)文章不得出现真实的校名") for raw in flat_raw)
    assert not any(raw.startswith("(4)不少于600字") for raw in flat_raw)


def test_article_marker_scored_text_should_not_create_new_outline_node():
    lines = [
        "一、阅读（60分）",
        "（二）文言文阅读（15分）",
        "13.邹忌说“王之蔽甚矣”。（3分）",
        "（乙）阅读下文，回答问题。（5分）",
        "14.解释下列加点词语的含义。（1分）",
        "15.翻译下面句子。（2分）",
        "16.文中的“主人”是一个怎样的人？（2分）",
        "（三）现代文阅读（25分）",
        "17.为下列加点字注音。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["一"]

    root = roots[0]
    assert [item["numbering"] for item in root["children"]] == ["二", "三"]
    section_two = root["children"][0]
    assert [item["numbering"] for item in section_two["children"]] == ["13", "14", "15", "16"]
    assert not any("（乙）阅读下文，回答问题" in str(item.get("rawText") or "") for item in root["children"])


def test_fallback_parent_score_should_be_evenly_distributed_to_multiple_underline_segments():
    lines = [
        "一、仿写（4分）",
        "5. 在横线上补写句子。（4分）",
        "_________________ ______________ _________________ _________________",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q5 = analysis["outlineItems"][0]["children"][0]
    blank_text = str(q5.get("blankText") or "")
    assert blank_text.count("（1分）") == 4


def test_parent_score_should_distribute_across_multi_line_empty_bracket_slots():
    lines = [
        "一、勇闯字音关。（16分）",
        "1. 看拼音，写词语。（10分）",
        "（ ） （ ） （ ） （ ） （ ）",
        "（ ） （ ） （ ） （ ） （ ）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]["children"][0]
    assert q1["score"] == 10.0
    blank_text = str(q1.get("blankText") or "")
    assert blank_text.count("（1分）") == 10


def test_parent_score_equal_total_slot_count_should_distribute_by_slot_count():
    lines = [
        "一、阅读（5分）",
        "（一）名句积累与运用（5分）",
        "1.沉舟侧畔千帆过，________________。",
        "2.________________，________________。",
        "3.________________，________________。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    section = analysis["outlineItems"][0]["children"][0]
    assert section["numbering"] == "一"
    assert section["score"] == 5.0
    children = section["children"]
    assert [child["numbering"] for child in children] == ["1", "2", "3"]
    assert [child["score"] for child in children] == [1.0, 2.0, 2.0]
    assert str(children[0].get("blankText") or "").count("（1分）") == 1
    assert str(children[1].get("blankText") or "").count("（1分）") == 2
    assert str(children[2].get("blankText") or "").count("（1分）") == 2


def test_mixed_malformed_bracket_score_lines_should_merge_into_parent_question():
    lines = [
        "七、课内阅读。(12分)",
        "2.从文中找出下列词语的近义词。(4分)",
        "血缘—(　　　(1分))　　后代—(　　　)(1分)",
        "描画—(　　　)(1分)　　依据—(　　　)(1分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    q2 = root["children"][0]
    assert q2["numbering"] == "2"
    assert q2["score"] == 4.0
    assert q2["children"] == []
    blank_text = str(q2.get("blankText") or "")
    assert blank_text.count("（1分）") == 4

    score_q2 = analysis["scores"]["childScores"][0]["childScores"][0]
    assert score_q2["score"] == 4.0
    assert score_q2["childScores"] == []


def test_indexed_cloze_markers_should_not_emit_number_only_placeholder_children():
    lines = [
        "\u4e03\u3001\u8865\u5168\u5bf9\u8bdd\uff0810\u5206\uff09",
        "85. A",
        "__86___ __87___ __88___",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    children = root.get("children", [])
    assert [child.get("numbering") for child in children] == ["85"]
    assert all(str(child.get("title") or "").strip() for child in children)
    score_children = analysis["scores"]["childScores"][0]["childScores"]
    assert len(score_children) == 1


def test_remaining_parent_score_should_average_to_unscored_siblings():
    lines = [
        "\u4e00\u3001\u7efc\u5408\u9898\uff0810\u5206\uff09",
        "1. \u7b2c\u4e00\u95ee\uff084\u5206\uff09",
        "2. \u7b2c\u4e8c\u95ee ____",
        "3. \u7b2c\u4e09\u95ee ____",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    scores = [child.get("score") for child in root.get("children", [])]
    assert scores == [4.0, 3.0, 3.0]
    assert "（3分）" in str(root["children"][1].get("blankText") or "")
    assert "（3分）" in str(root["children"][2].get("blankText") or "")

    score_children = analysis["scores"]["childScores"][0]["childScores"]
    assert [item["score"] for item in score_children] == [4.0, 3.0, 3.0]


def test_remaining_parent_score_should_distribute_recursively():
    lines = [
        "\u4e00\u3001\u7efc\u5408\u9898\uff0820\u5206\uff09",
        "1. \u7b2c\u4e00\u5927\u95ee\uff088\u5206\uff09",
        "(1) \u5b50\u95eeA\uff082\u5206\uff09",
        "(2) \u5b50\u95eeB ____",
        "(3) \u5b50\u95eeC ____",
        "2. \u7b2c\u4e8c\u5927\u95ee ____",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    q1 = root["children"][0]
    q2 = root["children"][1]
    assert q1["score"] == 8.0
    assert q2["score"] == 12.0
    assert [child["score"] for child in q1["children"]] == [2.0, 3.0, 3.0]

    score_root = analysis["scores"]["childScores"][0]
    assert [item["score"] for item in score_root["childScores"]] == [8.0, 12.0]
    assert [item["score"] for item in score_root["childScores"][0]["childScores"]] == [2.0, 3.0, 3.0]


def test_remaining_parent_score_equal_nested_slot_count_should_distribute_by_descendant_slots():
    lines = [
        "一、综合题（6分）",
        "1. 大题（6分）",
        "（1）小问甲",
        "① ____",
        "② ____",
        "（2）小问乙",
        "① ____",
        "② ____",
        "③ ____",
        "④ ____",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]["children"][0]
    assert q1["score"] == 6.0
    assert [child["score"] for child in q1["children"]] == [2.0, 4.0]

    assert q1["children"][0]["children"] == []
    assert q1["children"][1]["children"] == []
    assert str(q1["children"][0].get("blankText") or "").count("（1分）") == 2
    assert str(q1["children"][1].get("blankText") or "").count("（1分）") == 4

def test_remaining_parent_score_should_distribute_to_numbered_children_without_slots():
    lines = [
        "\u4e00\u3001\u7efc\u5408\u9898\uff0810\u5206\uff09",
        "1. \u7b2c\u4e00\u95ee\uff084\u5206\uff09",
        "2. \u7b2c\u4e8c\u95ee",
        "(1) \u5b50\u95eeA",
        "(2) \u5b50\u95eeB",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["score"] == 10.0
    assert [child["score"] for child in root["children"]] == [4.0, 6.0]
    assert [child["score"] for child in root["children"][1]["children"]] == [3.0, 3.0]

    score_root = analysis["scores"]["childScores"][0]
    assert [item["score"] for item in score_root["childScores"]] == [4.0, 6.0]
    assert [item["score"] for item in score_root["childScores"][1]["childScores"]] == [3.0, 3.0]


def test_scoreless_arabic_section_heading_should_not_stay_under_previous_chinese_paren():
    lines = [
        "\u4e09\u3001\u6587\u8a00\u6587\u9605\u8bfb\uff0820\u5206\uff09",
        "\uff08\u4e00\uff09\u8bfe\u5185\u6587\u8a00\u6587\uff0815\u5206\uff09",
        "10. \u7b2c\u4e00\u95ee\uff082\u5206\uff09",
        "\uff08\u4e8c\uff09\u8bfe\u5916\u6587\u8a00\u6587\uff085\u5206\uff09",
        "15. \u7b2c\u4e8c\u95ee\uff081\u5206\uff09",
        "1\u3001\u73b0\u4ee3\u6587\u9605\u8bfb",
        "18. \u7b2c\u4e09\u95ee\uff082\u5206\uff09",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u4e09", "1"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["\u4e00", "\u4e8c"]
    section_two = roots[0]["children"][1]
    assert section_two["numbering"] == "\u4e8c"
    assert [item["numbering"] for item in section_two["children"]] == ["15"]
    modern_reading = roots[1]
    assert [item["numbering"] for item in modern_reading["children"]] == ["18"]


def test_writing_subsections_should_keep_chinese_paren_nodes_instead_of_forced_flatten():
    lines = [
        "\u56db\u3001\u4f5c\u6587(56\u5206)",
        "\uff08\u4e00\uff09\u7efc\u5408\u6027\u5b66\u4e60\uff086\u5206\uff09",
        "24. \u8bf7\u4e3a\u8fd9\u5219\u6d88\u606f\u62df\u5199\u4e00\u4e2a\u6807\u9898\uff083\u5206\uff09",
        "25. \u8bf7\u4f60\u7ed9\u4e2d\u56fd\u5973\u6392\u53d1\u4e00\u6761\u795d\u8d3a\u77ed\u4fe1\uff083\u5206\uff09",
        "\uff08\u4e8c\uff09\u5199\u4f5c\uff0850\u5206\uff09",
        "26. \u4ee5\u201c\u611f\u6069\u60a8\u7684\u771f\u60c5\u201d\u4e3a\u9898\uff0c\u5199\u4e00\u7bc7\u8bb0\u53d9\u6587\u3002",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]
    assert [item["numbering"] for item in roots] == ["\u56db"]
    assert [item["numbering"] for item in roots[0]["children"]] == ["\u4e00", "\u4e8c"]
    assert [item["numbering"] for item in roots[0]["children"][0]["children"]] == ["24", "25"]
    assert [item["numbering"] for item in roots[0]["children"][1]["children"]] == ["26"]


def test_wrapped_underline_tail_should_not_create_extra_blank_slot():
    lines = [
        "二、阅读与感悟。(19分)",
        "3.这段话描写的动物中，______________的速度最慢，_____________的速度最快，____",
        "______________的方法最省力。(3分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    q3 = root["children"][0]
    blank_text = str(q3.get("blankText") or "")
    score_tags = re.findall(r"[（(]\d+(?:\.\d+)?分[）)]", blank_text)
    assert len(score_tags) == 3
    assert q3.get("children") == []


def test_quoted_underlines_with_choice_bracket_should_not_create_extra_slots():
    lines = [
        "1.画“____”和“____”的句子，选出修辞手法( )。(1分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]
    blank_text = str(q1.get("blankText") or "")
    score_tags = re.findall(r"[（(]\d+(?:\.\d+)?分[）)]", blank_text)
    assert len(score_tags) == 1


def test_mixed_underlines_and_empty_brackets_should_keep_all_slots():
    lines = [
        "5.请写出结果：_____ （ ） （ ） （3分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q5 = analysis["outlineItems"][0]
    blank_text = str(q5.get("blankText") or "")
    score_tags = re.findall(r"[（(]\d+(?:\.\d+)?分[）)]", blank_text)
    assert len(score_tags) == 3


def test_instruction_quoted_short_underline_should_not_be_extracted_as_blank():
    lines = [
        "3.“老师不禁一惊”,老师为什么惊住了?用“____”画出原因。(2分)",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q3 = analysis["outlineItems"][0]
    assert q3["score"] == 2.0
    assert str(q3.get("blankText") or "") == ""


def test_choice_question_tail_empty_bracket_should_not_generate_blank_text():
    lines = [
        "一、选择题（10分）",
        "18、关于图中山脉的叙述，正确的是（ ）",
        "A. 甲",
        "B. 乙",
        "C. 丙",
        "D. 丁",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q18 = analysis["outlineItems"][0]["children"][0]
    assert q18["numbering"] == "18"
    assert str(q18.get("blankText") or "") == ""
    assert re.search(r"[\uFF08(]\s*[\uFF09)]", str(q18.get("rawText") or ""))


def test_choice_question_stem_em_dash_should_not_be_treated_as_blank_slot():
    lines = [
        "一、选择题（40分）",
        "7．为确保国家粮食安全，中国的耕地保有量不得低于18亿亩——这既是中国耕地面积的底线，也是不能突破的政策“红线”．下列做法有利于保护耕地的是（ ）",
        "A. 甲",
        "B. 乙",
        "C. 丙",
        "D. 丁",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q7 = analysis["outlineItems"][0]["children"][0]
    assert q7["numbering"] == "7"
    assert str(q7.get("blankText") or "") == ""
    assert re.search(r"[\uFF08(]\s*[\uFF09)]", str(q7.get("rawText") or ""))
    assert _collect_blank_segments(str(q7.get("rawText") or "")) == []


def test_choice_question_tail_empty_bracket_with_score_should_not_generate_blank_text():
    lines = [
        "一、选择题（6分）",
        "1．关于位移的说法正确的是（ ）（3分）",
        "A. 甲",
        "B. 乙",
        "2．下一题（3分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]["children"][0]
    assert q1["numbering"] == "1"
    assert str(q1.get("blankText") or "") == ""
    assert re.search(r"[\uFF08(]\s*[\uFF09)]", str(q1.get("rawText") or ""))


def test_non_choice_question_empty_bracket_should_remain_in_raw_text_after_score_assignment():
    lines = [
        "1．下列说法正确的是（ ）（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]
    assert q1["numbering"] == "1"
    assert str(q1.get("blankText") or "") == "____（2分）"
    assert re.search(r"[\uFF08(]\s*[\uFF09)]", str(q1.get("rawText") or ""))


def test_unumbered_scored_slot_children_should_not_be_merged_back_into_parent_raw_text():
    lines = [
        "4普通计时法和24时计时法互相转化。（16分）",
        "早晨7时40分是( ) 凌晨3时30分是( )",
        "中午12时是( ) 下午5时10分是( )",
        "14时28分是( ) 6时是( )",
        "23时是( ) 17时28分是( )",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q4 = analysis["outlineItems"][0]
    assert q4["numbering"] == "4"
    assert "早晨7时40分是" not in str(q4.get("rawText") or "")
    assert len(q4.get("children") or []) == 4


def test_sentence_subquestion_with_explicit_bracket_slots_should_keep_blank_text():
    lines = [
        "七、按要求写数。(3分)",
        "1. 用4、8、5、2、0、0、0七个数字,按要求组成七位数。(3分)",
        "(6)在组成的七位数中,比较大的三个数是( )>( )>( )。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q6 = analysis["outlineItems"][0]["children"][0]["children"][0]
    assert q6["numbering"] == "6"
    assert ">( )>(" in str(q6.get("rawText") or "")
    assert str(q6.get("blankText") or "").count("（") == 3


def test_sentence_subquestion_single_bracket_slot_should_not_be_suppressed():
    lines = [
        "二、读图分析。（3.5分）",
        "4.(4)这星期借出的多还是归还的多?( )的多。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q4 = analysis["outlineItems"][0]["children"][0]
    assert q4["numbering"] == "4"
    assert re.search(r"[\uFF08(]\s*[\uFF09)]", str(q4.get("rawText") or ""))
    assert "____" in str(q4.get("blankText") or "")


def test_quoted_underline_in_actual_prompt_should_remain_in_raw_text():
    lines = [
        "18. 看图填空。（5分）",
        "(1)面“学”的对面是面“________”。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]["children"][0]
    assert q1["numbering"] == "1"
    assert "“________”" in str(q1.get("rawText") or "")
    assert "________" in str(q1.get("blankText") or "")


def test_choice_question_multiple_underlines_should_collapse_to_single_blank():
    lines = [
        "一、单项选择（2分）",
        "1. 南朝时开凿的大运河可以____ ____为中心。（ ）",
        "A. 长安",
        "B. 洛阳",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]["children"][0]
    blank_text = str(q1.get("blankText") or "")
    assert blank_text.count("（") <= 1


def test_choice_question_single_real_underline_should_be_preserved():
    lines = [
        "一、选择题（2分）",
        "1、隋朝时开凿的南北大运河以____为中心。（ ）",
        "A. 长安",
        "B. 洛阳",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]["children"][0]
    blank_text = str(q1.get("blankText") or "")
    assert "____" in blank_text
    assert blank_text.count("（") == 1


def test_non_choice_continuous_underline_should_keep_single_blank_on_same_sentence_line():
    lines = [
        "1. 请填写完整句子：____________ ____________。（2分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]
    blank_text = str(q1.get("blankText") or "")
    assert blank_text.count("（2分）") == 1


def test_choice_question_with_w1_w2_w3_should_not_split_into_fake_1_2_questions():
    lines = [
        "一、选择题（4分）",
        "7．该力在这三个过程中所做的功分别为W1、W2、W3，关于它们之间的大小关系说法正确的是（ ）",
        "A. 甲",
        "B. 乙",
        "8．下一题（ ）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    children = analysis["outlineItems"][0]["children"]
    assert [item["numbering"] for item in children] == ["7", "8"]


def test_choice_question_with_f1_f2_f3_should_not_split_into_fake_1_2_questions():
    lines = [
        "一、选择题（4分）",
        "10．在方向如图所示的力F1、F2、F3作用下处于平衡状态，那么（ ）",
        "A. 甲",
        "B. 乙",
        "11．下一题（ ）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    children = analysis["outlineItems"][0]["children"]
    assert [item["numbering"] for item in children] == ["10", "11"]


def test_parent_score_without_explicit_value_should_sum_from_children():
    lines = [
        "二、综合题",
        "21、读图，完成下列各题。（10分）",
        "（1）第一问。（5分）",
        "（2）第二问。（5分）",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    assert root["score"] == 10.0
    scores = analysis["scores"]
    assert scores["score"] == 10.0
    assert scores["childScores"][0]["score"] == 10.0
    assert scores["childScores"][0]["childScores"][0]["score"] == 10.0


def test_sentence_like_paren_subquestion_with_inline_slots_should_not_emit_blank_text():
    lines = [
        "二、综合题（10分）",
        "21、读图回答问题。（10分）",
        "（4）图中铁路①为________线,②为_________线,两条铁路线相比，修建难度大的是哪一条？为什么？",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    sub = analysis["outlineItems"][0]["children"][0]["children"][0]
    assert sub["numbering"] == "4"
    assert str(sub.get("blankText") or "") == ""
    assert "____" not in str(sub.get("rawText") or "")


def test_short_fill_paren_subquestion_should_keep_blank_text():
    lines = [
        "二、综合题（2分）",
        "21、请填写。（2分）",
        "（1）________",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    sub = analysis["outlineItems"][0]["children"][0]["children"][0]
    assert sub["numbering"] == "1"
    assert str(sub.get("blankText") or "") != ""


def test_wrapped_followup_blank_line_should_not_be_lost_after_score_distribution():
    lines = [
        "二、识图题（10分）",
        "21、读图回答问题：",
        "（1）从_______到_______ 年，",
        "明政府先后七次派郑和下西洋。2005年是郑和首次下西洋__________周年。",
        "（2）请填出出发地点和最远到达的地区",
        "A． ___________________ B． ______________________ C． _______________________",
        "（3）第三问。",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q21 = analysis["outlineItems"][0]["children"][0]
    sub1, sub2, _ = q21["children"]
    assert str(sub1.get("blankText") or "").count("（") == 3
    assert str(sub2.get("blankText") or "").count("（") == 3


def test_option_label_blank_line_should_be_merged_as_real_blank_slots():
    lines = [
        "1. 请填出对应内容。（6分）",
        "（1）填写地点",
        "A． ______ B． ______ C． ______",
        "（2）下一问",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    q1 = analysis["outlineItems"][0]
    sub1 = q1["children"][0]
    assert sub1["numbering"] == "1"
    assert str(sub1.get("blankText") or "").count("（") == 3


def test_unscored_sibling_should_not_force_positive_score_when_parent_remaining_is_zero():
    lines = [
        "一、综合题（10分）",
        "1. 第一部分（10分）",
        "（1）已评分子问（10分）",
        "（2）未评分子问",
    ]
    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    parent = analysis["outlineItems"][0]["children"][0]
    children = parent["children"]
    assert len(children) == 2
    assert float(children[0]["score"]) == 10.0
    second_score = children[1].get("score")
    assert second_score is None or float(second_score) <= 0.0


def test_reading_passage_circled_paragraph_should_not_be_recognized_as_question_heading():
    lines = [
        "八、课外阅读。(12分)",
        "当风筝遇上风",
        "①风悄悄地来了，她看着草坪上那只刚买回来的风筝，心想：怎么风还不来？等她回过神来的时候，风已经走了。",
        "②她一手拿着风筝，一手握着风筝线，正紧张地注视着四周的动静。一阵微风滑过脸颊，她轻轻放开了拿在手中的风筝，并将其推向空中，接着，慢慢地放着另一只手中的线。她开心地笑了。",
        "③看着她的笑容，我也笑了，望着她看了很久，心里萌发出了一丝感触。",
        "④当风筝遇上风，不正像人遇上机遇吗？",
        "⑤许多觉得自己不够成功的人，总会怨天尤人，抱怨自己遇不上好的机遇，总觉得平日伯乐见不着一个，众马却成群结队地拥挤喧哗在大街小巷。",
        "解释下列词语。(2分)",
        "(1)怨天尤人：____________________________________________",
        "(2)怀才不遇：____________________________________________",
        "文题“当风筝遇上风”中，除了表面含义，“风筝”还指__________，“风”还指_________，“当风筝遇上风”的深层意思是__________________________________________。(3分)",
        "文中画线的句子属于什么描写？表现了人物什么样的心情？(3分)",
        "当还没有遇上“风”的时候，我们应该怎样做？(4分)",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")

    root = analysis["outlineItems"][0]
    child_numberings = [str(child.get("numbering") or "") for child in root.get("children", [])]
    assert "④" not in child_numberings
    assert root["score"] == 12.0


def test_statement_option_parent_with_scored_children_should_not_be_collapsed():
    roots = [
        {
            "lineNumber": 5,
            "level": 2,
            "numbering": "1",
            "title": "读句子，选择读音与字形完全正确的一项填空。(填序号)(9分)",
            "rawText": "1.读句子，选择读音与字形完全正确的一项填空。(填序号)(9分)",
            "blankText": "",
            "score": 9.0,
            "_tokenType": "arabic",
            "children": [
                {
                    "lineNumber": 6,
                    "level": 3,
                    "numbering": "1",
                    "title": "这时候，小小的天窗是你唯一的( )。",
                    "rawText": "(1)这时候，小小的天窗是你唯一的( )。",
                    "blankText": "____（3分）",
                    "score": 3.0,
                    "children": [],
                },
                {
                    "lineNumber": 8,
                    "level": 3,
                    "numbering": "2",
                    "title": "那( )的低语，是在和刚刚从雪被里伸出头来的麦苗谈心。",
                    "rawText": "(2)那( )的低语，是在和刚刚从雪被里伸出头来的麦苗谈心。",
                    "blankText": "____（3分）",
                    "score": 3.0,
                    "children": [],
                },
                {
                    "lineNumber": 10,
                    "level": 3,
                    "numbering": "3",
                    "title": "从他们的房前屋后走过，你肯定会瞧见一只母鸡，( )一群小鸡，在竹林中觅食。",
                    "rawText": "(3)从他们的房前屋后走过，你肯定会瞧见一只母鸡，( )一群小鸡，在竹林中觅食。",
                    "blankText": "____（3分）",
                    "score": 3.0,
                    "children": [],
                },
            ],
        }
    ]

    _collapse_statement_option_paren_children(roots)

    assert roots[0]["rawText"] == "1.读句子，选择读音与字形完全正确的一项填空。(填序号)(9分)"
    assert roots[0]["blankText"] == ""
    assert [child["numbering"] for child in roots[0]["children"]] == ["1", "2", "3"]


def test_scored_leaf_should_fill_blank_text_from_title_underline_when_raw_text_lost_it():
    roots = [
        {
            "lineNumber": 24,
            "level": 3,
            "numbering": "1",
            "title": "醉里吴音相媚好，白发谁家翁媪？(用自己的话说说句子的意思)________________________________________________________________________________",
            "rawText": "(1)醉里吴音相媚好，白发谁家翁媪？(用自己的话说说句子的意思)",
            "blankText": "",
            "score": 3.0,
            "_tokenType": "paren_arabic",
            "children": [],
        }
    ]

    _fill_scored_underline_leaf_blank_text(roots)

    assert roots[0]["blankText"] == "________________________________________________________________________________（3分）"


def test_arabic_heading_with_semicolon_delimiter_should_be_recognized_as_sibling():
    lines = [
        "八、按要求写句子。(8分）",
        "1、风将银色的雨幕斜挂起来。（改“被”字句）",
        "___________________________________________________________",
        "2；这不是难为蝴蝶吗？（改陈述句）",
        "___________________________________________________________",
        "3、它们身上的彩粉是那样素洁。（改感叹句）",
        "___________________________________________________________",
        "4、钱塘江大潮是伟大的奇观。（改反问句）",
        "___________________________________________________________",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")

    root = analysis["outlineItems"][0]
    assert root["numbering"] == "八"
    assert [child["numbering"] for child in root["children"]] == ["1", "2", "3", "4"]
    assert root["children"][1]["blankText"]


def test_wrapped_paren_subquestion_continuation_should_not_drop_last_subquestion():
    lines = [
        "十．仔细阅读下面短文，并按要求回答问题。（21分）",
        "5.仔细读短文，判断选择，对的打“√”，错的打“×”。(3分)",
        "（1）太阳花不要根也能栽活，可见它的生命力很强。(    )",
        "（2）太阳花是一种木本植物花。(    )",
        "（3）“它的花既比不上水仙清雅，也不如君子兰高贵，平常极了。”这句话是",
        "说太阳花既比水仙清雅，也比君子兰高贵，平常极了。(    )",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")

    root = analysis["outlineItems"][0]
    question = root["children"][0]
    assert question["numbering"] == "5"
    assert [child["numbering"] for child in question["children"]] == ["1", "2", "3"]
    assert question["children"][2]["blankText"] == "____（1分）"


def test_instruction_quoted_underline_should_not_be_counted_as_answer_blank():
    lines = [
        "十．仔细阅读下面短文，并按要求回答问题。（21分）",
        "3.用“_______”画出文中比喻句，写出用_____________比喻____________。(2分)",
        "4.用“_______”画出第2、3自然段的中心句。(2分)",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")

    root = analysis["outlineItems"][0]
    q3, q4 = root["children"]
    assert q3["blankText"] == "_____________（1分） ____________（1分）"
    assert q4["blankText"] == ""


def test_instruction_quoted_underline_should_remain_in_raw_text_while_not_counting_as_blank():
    lines = [
        "十．仔细阅读下面短文，并按要求回答问题。（21分）",
        "3.用“_______”画出文中比喻句，写出用_____________比喻____________。(2分)",
        "4.用“_______”画出第2、3自然段的中心句。(2分)",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")

    root = analysis["outlineItems"][0]
    q3, q4 = root["children"]
    assert "“_______”" in str(q3.get("rawText") or "")
    assert "“_______”" in str(q4.get("rawText") or "")
    assert q3["blankText"] == "_____________（1分） ____________（1分）"
    assert q4["blankText"] == ""


def test_material_paragraph_with_many_brackets_should_not_be_merged_into_previous_question():
    lines = [
        "第二部分 阅读提升",
        "16．用文段中加点的词写一写动物园里活泼可爱的小猴子：小猴子一会儿_________，一会儿_________，一会儿_________，一会儿__________。（4分）",
        "有一天，我半信半疑。过了好几天，它（ ）活了，（ ）长出了新的叶子。又过了几天，它（ ）没枯萎，（ ）长得（ ）茂盛了。",
        "17．给文中加点的字圈出的正确的读音。（3分）",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    root = analysis["outlineItems"][0]
    q16 = root["children"][0]

    # 第16题只应保留题干中的 4 个下划线空位，不能吸附材料段里的 5 个括号空。
    assert q16["numbering"] == "16"
    assert len((q16.get("blankText") or "").split()) == 4


def test_second_major_section_with_arabic_2_should_not_be_attached_under_first_chinese_section():
    lines = [
        "一、语言积累和运用（20分）",
        "1、请给下列加点字注音（4分）",
        "2、默写填空（6分）",
        "3、下面文段有两处语病，请找出来并修改。（4分）",
        "4、班级要召开“我的中国心”的主题班会，请你设计一段开场白和一段结束语。（6分）",
        "2、阅读理解（50分）",
        "（一）阅读《春望》，回答后面的问题（13分）",
        "5、诗的前四句都统领在一个“____”字中。（1分）",
        "6、展开想像，描述画面并揭示含义。（4分）",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]

    # “2、阅读理解”应是并列大题，不应挂到“一、”的子级中造成重复编号。
    assert len(roots) >= 2
    assert roots[0]["numbering"] == "一"
    assert roots[1]["numbering"] == "2"
    assert not any(
        child.get("numbering") == "2" and "阅读理解" in str(child.get("title") or "")
        for child in roots[0].get("children", [])
    )


def test_chinese_prefixed_choice_section_should_not_be_parsed_as_paper_volume():
    lines = [
        "一、单项选择题（20分）",
        "1．甲乙丙丁（ ）",
        "二、非选择题（30分）",
        "21．请简要说明原因。（10分）",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]

    # “一、单项选择题”是中文一级大题，不应被误判为 paper_volume，
    # 否则后续“二、...”会被错误降级挂到“一、”下面。
    assert len(roots) >= 2
    assert [roots[0]["numbering"], roots[1]["numbering"]] == ["一", "二"]
    assert roots[0].get("_tokenType") != "paper_volume"


def test_parse_heading_should_keep_chinese_choice_section_as_chinese():
    line = "\u4e00\u3001 \u5355\u9879\u9009\u62e9\u9898\uff0c\u628a\u7b54\u6848\u586b\u5165\u4e0b\u4e00\u9875\u7684\u8868\u683c\u5185\u3002\uff0820\u5206\uff09"
    heading = _parse_heading(0, line, compile_score_patterns(None))
    assert heading is not None
    assert heading.token_type == "chinese"
    assert heading.number_text == "\u4e00"


def test_same_paren_subquestion_should_sum_multiple_inline_scores():
    lines = [
        "1、孔子所创立的儒家思想是中国传统文化的主流。",
        "请回答：",
        "(1)右图这位东方先哲——孔子，他的哪些思想观点在构建和谐社会方面有一些合理成分或值得借鉴的地方？(2分)",
        "(2)为了巩固政治统一，汉朝哪位皇帝开始用儒家思想作为治国思想？(1分)并在思想领域采取了什么措施使汉朝形成“大一统”的政治格局？(1分)",
        "(3)唐太宗是大唐盛世的奠基人。他在位时采取了一些缓和社会矛盾的措施，开创了唐初的繁荣时代，史称什么?(1分)",
        "(4)结合所学知识，你认为儒家思想的精华是什么?(1分)",
    ]

    analysis = analyze_document_lines(lines, max_level=8, second_level_mode="auto")
    roots = analysis["outlineItems"]

    assert len(roots) == 1
    assert roots[0]["numbering"] == "1"
    assert roots[0]["score"] == 6
    assert len(roots[0]["children"]) == 4
    assert roots[0]["children"][1]["numbering"] == "2"
    assert roots[0]["children"][1]["score"] == 2
    assert roots[0]["children"][1]["children"] == []



