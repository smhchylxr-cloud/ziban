"""ziban — CJK typesetting for programmatic renderers.

    >>> from ziban import layout, Style
    >>> page = layout("他说：「这次不一样。」", width=96, style=Style(size=16))
    >>> [line.text for line in page.lines]
    ['他说：「这次不一样。」']

The browser got ``text-spacing-trim`` and correct CJK line breaking years ago.
Everything that renders outside a browser — Pillow, ReportLab, SVG, ffmpeg
subtitles, python-pptx — still reimplements it badly.  This library is that
missing layer: kinbun kinsoku (避头尾), punctuation compression (标点挤压),
hanging punctuation (行末悬挂), and a diagnostic report when none of it fits.
"""

from __future__ import annotations

from .classify import can_break, line_break_class
from .layout import (
    KINSOKU_FALLBACK,
    NO_BREAK_OPPORTUNITY,
    ORPHAN_LINE,
    OVERFLOW,
    Adjustment,
    Diagnostic,
    Layout,
    Line,
    Style,
    layout,
)
from .metrics import EmMetrics, Metrics, PillowMetrics, measure
from .rules import RuleSet, load, load_default

__version__ = "0.1.1"

__all__ = [
    "__version__",
    "layout",
    "Style",
    "Line",
    "Layout",
    "Adjustment",
    "Diagnostic",
    "Metrics",
    "EmMetrics",
    "PillowMetrics",
    "measure",
    "RuleSet",
    "load_default",
    "load",
    "can_break",
    "line_break_class",
    "OVERFLOW",
    "NO_BREAK_OPPORTUNITY",
    "KINSOKU_FALLBACK",
    "ORPHAN_LINE",
]
