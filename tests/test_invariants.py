"""Invariants that must hold for *every* text and *every* width.

These are the real contract.  Golden tests pin specific decisions; invariants
prove the breaker never produces text that a typesetter would reject outright.
"""

from __future__ import annotations

import pytest

from corpus import CORPUS, WIDTHS_EM

from ziban import Style, layout, load_default

RULES = load_default()
SIZE = 16.0

CASES = [
    (text, width_em)
    for text in CORPUS
    for width_em in WIDTHS_EM
]


@pytest.mark.parametrize("text,width_em", CASES)
def test_no_character_is_lost(text: str, width_em: int) -> None:
    result = layout(text, width=width_em * SIZE, style=Style(size=SIZE))
    rebuilt = "".join(line.text for line in result.lines)
    # Trailing spaces are dropped by design, so compare on non-space content.
    assert "".join(rebuilt.split()) == "".join(text.split())


@pytest.mark.parametrize("text,width_em", CASES)
def test_no_line_starts_with_head_forbidden(text: str, width_em: int) -> None:
    result = layout(text, width=width_em * SIZE, style=Style(size=SIZE))
    for index, line in enumerate(result.lines):
        if not line.text:
            continue
        # A paragraph is allowed to *begin* with a closing mark ("……开头" is
        # normal prose); only a wrapped line may not.
        if index == 0 or result.lines[index - 1].hard_break:
            continue
        assert not RULES.is_head_forbidden(line.text[0]), (
            f"line {index + 1} starts with {line.text[0]!r}: {line.text!r}"
        )


@pytest.mark.parametrize("text,width_em", CASES)
def test_no_line_ends_with_tail_forbidden(text: str, width_em: int) -> None:
    result = layout(text, width=width_em * SIZE, style=Style(size=SIZE))
    for index, line in enumerate(result.lines):
        if not line.text:
            continue
        # The end of a paragraph may legitimately end with an opening mark.
        if line.hard_break or index == len(result.lines) - 1:
            continue
        assert not RULES.is_tail_forbidden(line.text[-1]), (
            f"line {index + 1} ends with {line.text[-1]!r}: {line.text!r}"
        )


@pytest.mark.parametrize("text,width_em", CASES)
def test_lines_fit_the_box(text: str, width_em: int) -> None:
    box = width_em * SIZE
    result = layout(text, width=box, style=Style(size=SIZE))
    for index, line in enumerate(result.lines):
        # Hanging punctuation is *supposed* to sit outside the margin, so the
        # ink may exceed the box by exactly the hung amount — no more.
        hung = sum(a.delta for a in line.adjustments if a.kind == "hang")
        if any(d.line == index for d in result.diagnostics):
            continue
        assert line.width <= box + hung + 1e-6, (
            f"line {index + 1} is {line.width:.1f}px wide in a {box:.0f}px box "
            f"(hang {hung:.1f}): {line.text!r}"
        )


@pytest.mark.parametrize("text,width_em", CASES)
def test_layout_is_deterministic(text: str, width_em: int) -> None:
    first = layout(text, width=width_em * SIZE, style=Style(size=SIZE))
    second = layout(text, width=width_em * SIZE, style=Style(size=SIZE))
    assert first.to_dict() == second.to_dict()


@pytest.mark.parametrize("text,width_em", CASES)
def test_hard_breaks_are_honoured(text: str, width_em: int) -> None:
    result = layout(text, width=width_em * SIZE, style=Style(size=SIZE))
    expected = text.count("\n")
    assert sum(1 for line in result.lines if line.hard_break) == expected
