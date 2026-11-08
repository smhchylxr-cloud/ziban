"""The engine has to survive real documents, not just sentences.

100k characters of mixed prose is roughly a long article; if it is slow or it
crashes, nobody will use this on a book.
"""

from __future__ import annotations

import time

from ziban import Style, layout, load_default

BASE = (
    "中文排版不是把字排整齐，而是让标点不去它不该去的地方。"
    "「这次不一样。」他说。2026 年的 GitHub 上，Agent Skills 很热。"
)
RULES = load_default()
SIZE = 16.0


def test_100k_characters_in_under_a_second():
    text = (BASE * 1500)[:100_000]
    started = time.perf_counter()
    result = layout(text, width=24 * SIZE, style=Style(size=SIZE, align="justify"))
    elapsed = time.perf_counter() - started

    assert len(result.lines) > 1000
    assert elapsed < 1.0, f"100k characters took {elapsed:.2f}s"
    assert result.overflow == 0


def test_100k_characters_are_reassembled_without_loss():
    text = (BASE * 1500)[:100_000]
    result = layout(text, width=24 * SIZE, style=Style(size=SIZE))
    assert "".join("".join(line.text for line in result.lines).split()) == "".join(
        text.split()
    )


def test_no_illegal_line_edges_in_a_long_document():
    text = (BASE * 300)[:20_000]
    result = layout(text, width=18 * SIZE, style=Style(size=SIZE))
    for index, line in enumerate(result.lines):
        if not line.text:
            continue
        if index and not result.lines[index - 1].hard_break:
            assert not RULES.is_head_forbidden(line.text[0]), line.text
        if not line.hard_break and index < len(result.lines) - 1:
            assert not RULES.is_tail_forbidden(line.text[-1]), line.text


def test_pathological_input_does_not_hang():
    for text in ["。", "，。！？", " " * 50, "\n\n\n", "a" * 500, "中" * 2000]:
        layout(text, width=10 * SIZE, style=Style(size=SIZE))
