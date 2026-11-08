"""Character classification is the foundation — if it is wrong, everything is."""

from __future__ import annotations

import pytest

from ziban.classify import NON_ENDER, NON_STARTER, can_break, is_wide, line_break_class


@pytest.mark.parametrize(
    "char,expected",
    [
        ("的", "ID"),
        ("〇", "ID"),
        ("あ", "ID"),
        ("한", "ID"),
        ("。", "CL"),
        ("，", "CL"),
        ("、", "CL"),
        ("」", "CL"),
        ("）", "CL"),
        ("（", "OP"),
        ("「", "OP"),
        ("《", "OP"),
        ("！", "EX"),
        ("？", "EX"),
        ("：", "IS"),
        ("；", "IS"),
        ("…", "NS"),
        ("—", "NS"),
        ("々", "NS"),
        ("ー", "NS"),
        ("a", "AL"),
        ("Z", "AL"),
        ("7", "NU"),
        ("%", "PO"),
        ("$", "PR"),
        (" ", "SP"),
        ("-", "HY"),
        ("\u3000", "SP"),
    ],
)
def test_classes(char: str, expected: str):
    assert line_break_class(char) == expected


def test_combining_marks_are_combining():
    assert line_break_class("\u0301") == "CM"


def test_unknown_wide_character_falls_back_to_ideograph():
    # U+20BB7 (𠮷) is a CJK extension B character, wide by East Asian Width.
    assert line_break_class("\U00020bb7") == "ID"


def test_unknown_narrow_character_falls_back_to_alphabetic():
    assert line_break_class("∂") == "AL"


def test_wide_detection():
    assert is_wide("的")
    assert is_wide("，")
    assert not is_wide("a")
    assert not is_wide("1")


@pytest.mark.parametrize(
    "before,after,expected",
    [
        ("一", "二", True),
        ("一", "a", True),
        ("a", "一", True),
        ("a", "b", False),
        ("1", "2", False),
        ("a", "1", False),
        ("一", "。", False),  # 。 may not start a line
        ("（", "一", False),  # （ may not end a line
        (" ", "一", True),
        ("。", "一", True),
        ("\u3000", "一", True),
        ("一", "（", True),
    ],
)
def test_can_break(before: str, after: str, expected: bool):
    assert can_break(before, after) is expected


def test_non_starter_and_non_ender_are_disjoint():
    assert NON_STARTER.isdisjoint(NON_ENDER)
