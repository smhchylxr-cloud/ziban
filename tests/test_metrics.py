"""Metrics adapters."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ziban.metrics import EmMetrics, PillowMetrics, measure

WINDOWS_FONTS = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
]
FONT = next((p for p in WINDOWS_FONTS if p.exists()), None)


def test_em_metrics_are_wide_for_cjk_and_narrow_for_latin():
    metrics = EmMetrics(20.0)
    assert metrics.advance("的") == pytest.approx(20.0)
    assert metrics.advance("a") == pytest.approx(10.0)
    assert metrics.advance(" ") == pytest.approx(5.0)


def test_em_metrics_ignore_combining_marks():
    assert EmMetrics(16.0).advance("e\u0301") == pytest.approx(8.0)


def test_em_metrics_are_deterministic():
    assert EmMetrics(16.0).advance("中文") == EmMetrics(16.0).advance("中文")


def test_measure_sums_clusters():
    metrics = EmMetrics(10.0)
    assert measure("一a", metrics) == pytest.approx(15.0)


def test_em_metrics_reject_bad_size():
    with pytest.raises(ValueError):
        EmMetrics(0)


@pytest.mark.skipif(FONT is None, reason="no CJK system font available")
def test_pillow_metrics_measure_a_real_font():
    metrics = PillowMetrics(str(FONT), 32.0)
    width = metrics.advance("中")
    assert width > 0
    assert metrics.advance("中文") == pytest.approx(2 * width, rel=0.05)


def test_pillow_metrics_report_a_missing_dependency_clearly(tmp_path: Path):
    with pytest.raises(Exception):
        PillowMetrics(str(tmp_path / "nope.ttf"), 16.0)
