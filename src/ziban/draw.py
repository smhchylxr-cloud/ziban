"""Paint laid-out lines.

``layout()`` decides where lines break; this module is the other half — it puts
those lines on a canvas and *honours the decisions*: compressed punctuation is
drawn compressed, hanging punctuation is allowed to cross the margin, justified
lines get the extra space between the gaps the breaker counted, and centred
lines are centred on their measured width.

Without this half, "typesetting" is only half done: every caller re-implements
drawing and quietly drops every adjustment the breaker made.
"""

from __future__ import annotations

from typing import Optional, Sequence

from .layout import Line, Layout, clusters
from .metrics import Metrics

__all__ = ["draw_lines", "draw_line", "block_height"]


def block_height(lines: Sequence[Line], line_height: float) -> float:
    """Height of a block of lines at a given line height."""
    return len(lines) * line_height


def draw_line(
    draw,
    x: float,
    y: float,
    line: Line,
    *,
    font,
    metrics: Metrics,
    fill: str,
    tracking: float = 0.0,
    justify: float = 0.0,
) -> float:
    """Draw one line at ``(x, y)`` and return the pen position at its end."""
    units = clusters(line.text)
    squeezed = {a.index: a.delta for a in line.adjustments if a.kind == "compress"}
    # Justification spreads over spaces in Latin runs, between clusters in CJK.
    spread_on_space = " " in line.text

    pen = float(x)
    for index, unit in enumerate(units):
        draw.text((pen, y), unit, font=font, fill=fill)
        pen += metrics.advance(unit) + tracking - squeezed.get(index, 0.0)
        if justify > 0.0 and index < len(units) - 1:
            if (spread_on_space and unit == " ") or not spread_on_space:
                pen += justify
    return pen


def draw_lines(
    draw,
    x: float,
    y: float,
    layout: Layout,
    *,
    font,
    metrics: Metrics,
    fill: str,
    leading: float = 1.6,
    tracking: float = 0.0,
    justify: bool = False,
    width: Optional[float] = None,
) -> float:
    """Draw a whole layout; returns the y coordinate below the last line."""
    line_height = layout.style.size * leading
    pen_y = float(y)
    for line in layout.lines:
        if not line.text:
            pen_y += line_height
            continue
        offset = 0.0
        if width is not None:
            if layout.style.align == "center":
                offset = (width - line.width) / 2.0
            elif layout.style.align == "right":
                offset = width - line.width
        draw_line(
            draw,
            x + offset,
            pen_y,
            line,
            font=font,
            metrics=metrics,
            fill=fill,
            tracking=tracking,
            justify=line.justify_spacing if justify else 0.0,
        )
        pen_y += line_height
    return pen_y
