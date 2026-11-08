"""ziban — CJK typesetting for programmatic renderers.

    >>> from ziban import layout, Style
    >>> page = layout("他说：「这次不一样。」", width=96, style=Style(size=16))
    >>> [line.text for line in page.lines]
    ['他说：「这次不一样。」']

The browser got ``text-spacing-trim`` and correct CJK line breaking years ago.
Everything that renders outside a browser — Pillow, ReportLab, SVG, ffmpeg
subtitles, python-pptx — still reimplements it badly.  This library is that
missing layer: kinsoku (避头尾), punctuation compression (标点挤压), hanging
punctuation (行末悬挂), and a diagnostic report when none of it fits.

The core is dependency-free.  ``ziban.cards`` needs Pillow and is imported
lazily, so ``import ziban`` stays cheap on a server with no image stack.
"""

from __future__ import annotations

from typing import Any

from .classify import can_break, line_break_class
from .draw import draw_line, draw_lines
from .fonts import FontSet
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
from .theme import THEMES, Theme, get as get_theme

__version__ = "0.2.0"

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
    "draw_lines",
    "draw_line",
    "FontSet",
    "Theme",
    "THEMES",
    "get_theme",
    "render_card",
    "OVERFLOW",
    "NO_BREAK_OPPORTUNITY",
    "KINSOKU_FALLBACK",
    "ORPHAN_LINE",
]


def __getattr__(name: str) -> Any:
    """Lazy access to the Pillow-backed card renderer.

    ``import ziban`` must not require Pillow; ``ziban.render_card`` does.
    """
    if name in {"render_card", "CANVAS", "MARGIN", "KINDS"}:
        from . import cards as _cards

        return getattr(_cards, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
