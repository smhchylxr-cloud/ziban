"""The ruleset is data, so it can be tested like data."""

from __future__ import annotations

from pathlib import Path

import pytest

from ziban.rules import RuleSet, load, load_default


def test_bundled_ruleset_loads():
    rules = load_default()
    assert rules.version
    assert rules.clreq.startswith("https://www.w3.org/TR/clreq/")
    assert "，" in rules.head_forbidden
    assert "（" in rules.tail_forbidden


def test_default_ruleset_is_cached():
    assert load_default() is load_default()


def test_head_forbidden_covers_uax_non_starters_even_without_the_char_list():
    rules = load_default()
    # "…" is not in the TOML list by accident of curation; the UAX class
    # still forbids it at line start.  This is the belt-and-braces guarantee.
    assert rules.is_head_forbidden("…")
    assert rules.is_head_forbidden("。")
    assert not rules.is_head_forbidden("一")


def test_tail_forbidden_covers_opening_brackets():
    rules = load_default()
    for ch in "（「《【〈":
        assert rules.is_tail_forbidden(ch)
    assert not rules.is_tail_forbidden("一")


def test_compression_saving_is_zero_for_normal_characters():
    rules = load_default()
    assert rules.compression_saving("一", 16.0) == 0.0
    assert rules.compression_saving("，", 16.0) == pytest.approx(8.0)


def test_hang_budget_is_capped_by_the_measure():
    rules = load_default()
    assert rules.hang_budget(16.0, 400.0) == pytest.approx(16.0)  # one em
    assert rules.hang_budget(16.0, 48.0) == pytest.approx(12.0)  # a quarter of 48


def test_overrides_are_additive():
    rules = load_default()
    stricter = rules.with_overrides(head_forbidden="●", compressed_ratio=0.25)
    assert "，" in stricter.head_forbidden and "●" in stricter.head_forbidden
    assert stricter.compressed_ratio == 0.25
    assert rules.compressed_ratio != 0.25  # original untouched


def test_custom_ruleset_can_be_loaded_from_a_file(tmp_path: Path):
    path = tmp_path / "jp.toml"
    path.write_text(
        """
version = "test"
clreq = "https://www.w3.org/TR/jlreq/"

[kinsoku]
head_forbidden = "、。"
tail_forbidden = "「"

[compress]
compressed_ratio = 0.5
chars = "、。"

[hang]
max_ratio = 0.5
max_share = 0.2
chars = "、。"
""",
        encoding="utf-8",
    )
    rules = load(path)
    assert isinstance(rules, RuleSet)
    assert rules.version == "test"
    assert rules.hang_max_ratio == 0.5
    assert rules.hang_max_share == 0.2
