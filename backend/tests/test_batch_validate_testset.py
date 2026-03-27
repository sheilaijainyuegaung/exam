from tools.batch_validate_testset import (
    _is_source_line_compatible_with_extracted_raw,
    validate_against_source,
)


def test_validate_against_source_should_allow_generated_blank_scores_when_node_has_explicit_score():
    main_lines = [
        "一、填空题（2分）",
        "1．20×50的积的末尾有____个0。",
    ]
    details = {
        "outlineItems": [
            {
                "numbering": "一",
                "rawText": "一、填空题（2分）",
                "lineNumber": 1,
                "blankText": "",
                "score": 2,
                "children": [
                    {
                        "numbering": "1",
                        "rawText": "1．20×50的积的末尾有____个0。",
                        "lineNumber": 2,
                        "blankText": "____（2分）",
                        "score": 2,
                        "children": [],
                    }
                ],
            }
        ]
    }

    issues, warnings = validate_against_source(main_lines, details)
    assert issues == []
    assert warnings == []


def test_source_line_compatible_with_extracted_raw_should_allow_parent_and_subquestion_same_line():
    source_line = "21．(1)同学们就“人生需要梦想”展开讨论，请谈谈你的想法。"
    raw = "(1)同学们就“人生需要梦想”展开讨论，请谈谈你的想法。"
    assert _is_source_line_compatible_with_extracted_raw(source_line, raw, "二/21/1")


def test_source_line_compatible_with_extracted_raw_should_ignore_source_tags_and_heading_token():
    source_line = "一．(1)面对“学”的对面是面“_______”；[来源:学科网]"
    raw = "(1)面对“学”的对面是面“_______”；"
    assert _is_source_line_compatible_with_extracted_raw(source_line, raw, "18/1")


def test_source_line_compatible_with_extracted_raw_should_ignore_source_tag_numbering_noise():
    source_line = "（3）[Z.X.X.K]"
    raw = "（3）[Z.X.X.K]"
    assert _is_source_line_compatible_with_extracted_raw(source_line, raw, "二/21/3")


def test_validate_against_source_should_treat_spaced_underlines_as_one_continuous_blank():
    main_lines = [
        "一、语言积累和运用（20分）",
        "4、班级要召开主题班会，请你设计一段结束语。（3分）",
        "2）结束语：_________________________________________________________________ __________________________________________________________________________",
    ]
    details = {
        "outlineItems": [
            {
                "numbering": "一",
                "rawText": "一、语言积累和运用（20分）",
                "lineNumber": 1,
                "blankText": "",
                "score": 20,
                "children": [
                    {
                        "numbering": "4",
                        "rawText": "4、班级要召开主题班会，请你设计一段结束语。（3分）",
                        "lineNumber": 2,
                        "blankText": "",
                        "score": 3,
                        "children": [
                            {
                                "numbering": "2",
                                "rawText": "2）结束语：_________________________________________________________________ __________________________________________________________________________",
                                "lineNumber": 3,
                                "blankText": "___________________________________________________________________________________________________________________________________________（3分）",
                                "score": 3,
                                "children": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    issues, warnings = validate_against_source(main_lines, details)
    assert issues == []
    assert warnings == []


def test_validate_against_source_should_allow_distributed_scores_for_multi_blank_subquestion():
    main_lines = [
        "一、阅读（10分）",
        "9.根据内容填空。（4分）",
        "（1）第一空________，第二空________。（4分）",
    ]
    details = {
        "outlineItems": [
            {
                "numbering": "一",
                "rawText": "一、阅读（10分）",
                "lineNumber": 1,
                "blankText": "",
                "score": 10,
                "children": [
                    {
                        "numbering": "9",
                        "rawText": "9.根据内容填空。（4分）",
                        "lineNumber": 2,
                        "blankText": "",
                        "score": 4,
                        "children": [
                            {
                                "numbering": "1",
                                "rawText": "（1）第一空________，第二空________。（4分）",
                                "lineNumber": 3,
                                "blankText": "________（2分） ________（2分）",
                                "score": 4,
                                "children": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    issues, warnings = validate_against_source(main_lines, details)
    assert issues == []
    assert warnings == []


def test_validate_against_source_should_ignore_instruction_quoted_underlines_in_raw_count():
    main_lines = [
        "七、阅读（8分）",
        "2.选文中画“_____”的句子采用了____________的说明方法。（2分）",
    ]
    details = {
        "outlineItems": [
            {
                "numbering": "七",
                "rawText": "七、阅读（8分）",
                "lineNumber": 1,
                "blankText": "",
                "score": 8,
                "children": [
                    {
                        "numbering": "2",
                        "rawText": "2.选文中画“_____”的句子采用了____________的说明方法。（2分）",
                        "lineNumber": 2,
                        "blankText": "____________（2分）",
                        "score": 2,
                        "children": [],
                    }
                ],
            }
        ]
    }

    issues, warnings = validate_against_source(main_lines, details)
    assert issues == []
    assert warnings == []
