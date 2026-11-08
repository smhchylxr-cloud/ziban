"""Golden cases: hand-checked break decisions.

Every expected list below was verified by reading the text, not by copying
whatever the engine printed.  If a change makes one of these fail, the change
is wrong until proven otherwise.
"""

from __future__ import annotations

import pytest

from ziban import (
    KINSOKU_FALLBACK,
    NO_BREAK_OPPORTUNITY,
    ORPHAN_LINE,
    OVERFLOW,
    Style,
    layout,
)

SIZE = 16.0


def wrap(text: str, width_em: float, **style_kwargs) -> list:
    return layout(
        text, width=width_em * SIZE, style=Style(size=SIZE, **style_kwargs)
    ).lines


def texts(text: str, width_em: float, **style_kwargs) -> list:
    return [line.text for line in wrap(text, width_em, **style_kwargs)]


# -- plain breaking ------------------------------------------------------


def test_exact_fit_is_one_line():
    assert texts("一二三四五六七八九十", 10) == ["一二三四五六七八九十"]


def test_cjk_breaks_between_ideographs():
    assert texts("一二三四五六七八九十一", 10) == ["一二三四五六七八九十", "一"]


def test_latin_words_are_never_split():
    assert texts("Hello world", 3) == ["Hello", "world"]
    assert texts("supercalifragilistic", 5) == ["supercalifragilistic"]


def test_mixed_script_breaks_between_cjk_and_latin():
    assert texts("中文English混排测试", 6) == ["中文English", "混排测试"]


def test_trailing_spaces_are_dropped():
    assert texts("a b  c", 2) == ["a b", "c"]


# -- kinsoku -------------------------------------------------------------


def test_closing_punctuation_hangs_instead_of_starting_a_line():
    lines = wrap("你好，世界。", 5)
    assert [line.text for line in lines] == ["你好，世界。"]
    assert [a.kind for a in lines[0].adjustments] == ["hang"]


def test_hang_can_be_disabled_and_then_the_line_backs_off():
    result = layout(
        "你好，世界。",
        width=5 * SIZE,
        style=Style(size=SIZE, allow_hang=False),
    )
    assert [line.text for line in result.lines] == ["你好，世", "界。"]
    assert KINSOKU_FALLBACK in result.codes()


def test_punctuation_is_compressed_when_that_is_enough():
    lines = wrap("abc一二三四五六七八，", 10)
    assert [line.text for line in lines] == ["abc一二三四五六七八，"]
    assert [a.kind for a in lines[0].adjustments] == ["compress"]
    assert lines[0].width == pytest.approx(10 * SIZE)


def test_opening_bracket_never_ends_a_line():
    assert texts("一二三（四五六", 4) == ["一二三", "（四五六"]


def test_narrow_measure_caps_the_overhang():
    # On a 3em column a bracket may stick out, but never more than the budget
    # (a quarter of the measure), and never at the start of a line.
    box = 3 * SIZE
    lines = wrap("（）（）（）", 3)
    for line in lines:
        assert line.width - box <= 0.25 * box + 1e-6
        assert not line.text.startswith("）")


def test_quote_closing_stays_on_the_line():
    lines = wrap("他说：「这次不一样。」", 10)
    assert [line.text for line in lines] == ["他说：「这次不一样。」"]
    assert lines[0].adjustments[0].kind == "hang"


def test_ellipsis_pair_is_not_split():
    assert texts("……他说完就沉默了", 4) == ["……他说", "完就沉默", "了"]


# -- structure -----------------------------------------------------------


def test_hard_breaks_are_preserved():
    lines = wrap("第一行\n第二行", 4)
    assert [line.text for line in lines] == ["第一行", "第二行"]
    assert lines[0].hard_break is True
    assert lines[1].hard_break is False


def test_blank_paragraph_produces_an_empty_line():
    lines = wrap("甲\n\n乙", 3)
    assert [line.text for line in lines] == ["甲", "", "乙"]
    assert lines[0].hard_break and lines[1].hard_break


def test_first_line_indent_shortens_only_the_first_line():
    assert texts("这是一个用于测试首行缩进的段落", 6, first_line_indent=1.0) == [
        "这是一个用",
        "于测试首行缩",
        "进的段落",
    ]


# -- diagnostics ---------------------------------------------------------


def test_orphan_line_is_reported():
    result = layout(
        "一二三四五六七八九十一", width=10 * SIZE, style=Style(size=SIZE)
    )
    assert [line.text for line in result.lines][-1] == "一"
    assert ORPHAN_LINE in result.codes()


def test_unbreakable_run_overflows_loudly():
    word = "a" * 40
    result = layout(word, width=10 * SIZE, style=Style(size=SIZE))
    assert len(result.lines) == 1
    assert result.lines[0].text == word
    assert NO_BREAK_OPPORTUNITY in result.codes()
    assert OVERFLOW in result.codes()
    assert result.overflow > 0


def test_url_breaks_after_slashes():
    # A URL is not one unbreakable word: "/" is a legal break point.
    url = "https://example.com/a/very/long/url"
    result = layout(url, width=10 * SIZE, style=Style(size=SIZE))
    assert len(result.lines) > 1
    assert all(line.overflow == 0 for line in result.lines)


def test_diagnostics_carry_a_line_number_and_a_fix():
    result = layout(
        "一二三四五六七八九十一", width=10 * SIZE, style=Style(size=SIZE)
    )
    orphan = [d for d in result.diagnostics if d.code == ORPHAN_LINE][0]
    assert orphan.line == 1
    assert orphan.fix


# -- api behaviour -------------------------------------------------------


def test_zero_width_is_rejected():
    with pytest.raises(ValueError):
        layout("x", width=0)


def test_unknown_alignment_is_rejected():
    with pytest.raises(ValueError):
        Style(align="middle")


def test_to_dict_is_json_friendly():
    import json

    result = layout("你好，世界。", width=5 * SIZE, style=Style(size=SIZE))
    payload = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
    assert payload["lines"][0]["text"] == "你好，世界。"
    assert payload["rules_version"]


def test_justify_distributes_the_slack():
    result = layout(
        "Hello world 中文测试",
        width=8 * SIZE,
        style=Style(size=SIZE, align="justify"),
    )
    first = result.lines[0]
    assert first.justify_spacing > 0
    assert first.width + first.slack == pytest.approx(8 * SIZE)


def test_empty_input_yields_one_empty_line():
    result = layout("", width=4 * SIZE, style=Style(size=SIZE))
    assert [line.text for line in result.lines] == [""]
    assert result.overflow == 0
