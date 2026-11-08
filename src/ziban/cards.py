"""Four card layouts, rendered with the engine.

This is the first consumer of the breaker — the thing that proves the library
is usable for real work rather than only for tests.  Every text block goes
through :func:`fit`: lay it out at the designed size, and if the block is taller
than its slot, step the size down until it fits (down to 60%), and only then
report `TEXT_OVERFLOW`.  Silent clipping is the one outcome we refuse.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw

from .draw import draw_lines
from .fonts import FontSet
from .layout import Diagnostic, Layout, Style, layout
from .metrics import PillowMetrics
from .theme import Theme

__all__ = ["render_card", "CANVAS", "MARGIN", "KINDS"]

CANVAS: Tuple[int, int] = (1080, 1440)
MARGIN = 96
KINDS = ("cover", "list", "steps", "note")


# --------------------------------------------------------------------------
# fitting
# --------------------------------------------------------------------------


@dataclass
class _Fitted:
    layout: Layout
    font: Any
    metrics: PillowMetrics
    size: float

    @property
    def height(self) -> float:
        return len(self.layout.lines) * self.size * self.layout.style.leading


def _fit(
    text: str,
    *,
    fonts: FontSet,
    weight: str,
    width: float,
    max_height: float,
    start_size: float,
    leading: float,
    align: str = "left",
    min_ratio: float = 0.6,
    indent: float = 0.0,
) -> Tuple[_Fitted, List[Diagnostic]]:
    """Lay ``text`` out at the largest size ≤ ``start_size`` that fits ``max_height``."""
    size = float(start_size)
    floor = max(12.0, start_size * min_ratio)
    last: Optional[_Fitted] = None
    issues: List[Diagnostic] = []

    while size >= floor:
        metrics = PillowMetrics(str(_font_path(fonts, weight)), size)
        style = Style(size=size, leading=leading, align=align, first_line_indent=indent)
        laid = layout(text, width=width, style=style, metrics=metrics)
        candidate = _Fitted(laid, fonts.load(size, weight=weight), metrics, size)
        last = candidate
        if candidate.height <= max_height + 1e-6:
            issues.extend(laid.diagnostics)
            if size < start_size - 0.5:
                issues.append(
                    Diagnostic(
                        "TEXT_SHRUNK",
                        -1,
                        f"block shrank from {start_size:.0f}px to {size:.0f}px to fit its slot.",
                        "Shorten the copy, or give the block more room.",
                    )
                )
            return candidate, issues
        size -= 2.0

    assert last is not None
    issues.extend(last.layout.diagnostics)
    issues.append(
        Diagnostic(
            "TEXT_OVERFLOW",
            -1,
            f"block needs {last.height:.0f}px, slot is {max_height:.0f}px even at {floor:.0f}px.",
            "Shorten the copy, enlarge the canvas, or split the card.",
        )
    )
    return last, issues


def _font_path(fonts: FontSet, weight: str):
    return {"regular": fonts.regular, "bold": fonts.bold, "mono": fonts.mono}[weight]


# --------------------------------------------------------------------------
# chrome
# --------------------------------------------------------------------------


def _kicker(draw, theme: Theme, fonts: FontSet, x: float, y: float, text: str) -> None:
    draw.rectangle([x, y + 4, x + 18, y + 22], fill=theme.accent)
    draw.text(
        (x + 34, y),
        text,
        font=fonts.load(theme.size("micro"), weight="bold"),
        fill=theme.muted,
    )


def _footer(
    draw,
    theme: Theme,
    fonts: FontSet,
    x: float,
    right_x: float,
    y: float,
    left: str,
    right: str,
) -> None:
    draw.line([(x, y - 28), (right_x, y - 28)], fill=theme.rule, width=2)
    font = fonts.load(theme.size("micro"))
    draw.text((x, y), left, font=font, fill=theme.muted)
    if right:
        w = draw.textlength(right, font=font)
        draw.text((right_x - w, y), right, font=font, fill=theme.muted)


# --------------------------------------------------------------------------
# templates
# --------------------------------------------------------------------------


def _cover(draw, spec, theme: Theme, fonts: FontSet, w: int, h: int, issues: List[Diagnostic]):
    x0, x1 = MARGIN, w - MARGIN
    cw = x1 - x0

    title, title_issues = _fit(
        spec["title"],
        fonts=fonts,
        weight="bold",
        width=cw,
        max_height=h * 0.46,
        start_size=theme.size("display"),
        leading=1.12,
    )
    issues.extend(title_issues)

    sub = None
    subtitle = spec.get("subtitle", "")
    if subtitle:
        sub, sub_issues = _fit(
            subtitle,
            fonts=fonts,
            weight="regular",
            width=cw * 0.86,
            max_height=h * 0.20,
            start_size=theme.size("h2"),
            leading=1.6,
        )
        issues.extend(sub_issues)

    # Poster anchoring: kicker + title own the upper third, the subtitle sits
    # just above the footer.  Two anchors beat one centred block — the page
    # stops looking like it forgot to fill the bottom.
    kicker_y = 150.0
    title_y = 300.0

    _kicker(draw, theme, fonts, x0, kicker_y, spec.get("kicker", ""))

    draw_lines(
        draw,
        x0,
        title_y,
        title.layout,
        font=title.font,
        metrics=title.metrics,
        fill=theme.ink,
        leading=1.12,
    )

    bar_y = title_y + title.height + 40
    draw.rectangle([x0, bar_y, x0 + 150, bar_y + 8], fill=theme.accent)

    if sub is not None:
        sub_y = h - 200 - sub.height
        if sub_y < bar_y + 80:  # long title: fall back to flowing below it
            sub_y = bar_y + 80
        draw_lines(
            draw,
            x0,
            sub_y,
            sub.layout,
            font=sub.font,
            metrics=sub.metrics,
            fill=theme.muted,
            leading=1.6,
        )

    _footer(draw, theme, fonts, x0, x1, h - 96, spec.get("footer_left", ""), spec.get("meta", ""))


def _list(draw, spec, theme: Theme, fonts: FontSet, w: int, h: int, issues: List[Diagnostic]):
    x0, x1 = MARGIN, w - MARGIN
    cw = x1 - x0

    _kicker(draw, theme, fonts, x0, 130, spec.get("kicker", ""))

    head, head_issues = _fit(
        spec["title"],
        fonts=fonts,
        weight="bold",
        width=cw,
        max_height=220,
        start_size=theme.size("h1"),
        leading=1.25,
    )
    issues.extend(head_issues)
    y = 250
    draw_lines(
        draw, x0, y, head.layout, font=head.font, metrics=head.metrics, fill=theme.ink, leading=1.25
    )
    y += head.height + 56

    items: Sequence[str] = spec.get("items", [])
    start_y = y
    avail = (h - 130) - start_y
    per_item = avail / max(1, len(items))

    # Measure first, then distribute: a fixed gap leaves the bottom of the card
    # empty when items are short, and a full split looks disconnected when they
    # are long.  Cap the gap at 96px and let the rest breathe.
    measured: List[_Fitted] = []
    for item in items:
        body, body_issues = _fit(
            item,
            fonts=fonts,
            weight="regular",
            width=cw - 132,
            max_height=max(80.0, per_item - 40),
            start_size=theme.size("body"),
            leading=1.55,
        )
        issues.extend(body_issues)
        measured.append(body)

    total = sum(body.height for body in measured)
    gap = max(40.0, min(96.0, (avail - total) / max(1, len(items))))

    for index, body in enumerate(measured, start=1):
        numeral = f"{index:02d}"
        draw.text(
            (x0, y + 2),
            numeral,
            font=fonts.load(theme.size("mono"), weight="mono"),
            fill=theme.accent,
        )
        draw_lines(
            draw,
            x0 + 132,
            y,
            body.layout,
            font=body.font,
            metrics=body.metrics,
            fill=theme.ink,
            leading=1.55,
        )
        y += body.height + gap

    _footer(draw, theme, fonts, x0, x1, h - 96, spec.get("footer_left", ""), spec.get("meta", ""))


def _steps(draw, spec, theme: Theme, fonts: FontSet, w: int, h: int, issues: List[Diagnostic]):
    x0, x1 = MARGIN, w - MARGIN
    cw = x1 - x0

    _kicker(draw, theme, fonts, x0, 130, spec.get("kicker", ""))

    head, head_issues = _fit(
        spec["title"],
        fonts=fonts,
        weight="bold",
        width=cw,
        max_height=200,
        start_size=theme.size("h1"),
        leading=1.25,
    )
    issues.extend(head_issues)
    y = 246
    draw_lines(
        draw, x0, y, head.layout, font=head.font, metrics=head.metrics, fill=theme.ink, leading=1.25
    )
    y += head.height + 70

    steps = spec.get("steps", [])
    slot = (h - 130 - y) / max(1, len(steps))
    rail_x = x0 + 40
    dot_ys = [y + 26 + index * slot for index in range(len(steps))]
    if len(dot_ys) > 1:
        # The rail joins the dots, not the empty space after the last step.
        draw.line([(rail_x, dot_ys[0]), (rail_x, dot_ys[-1])], fill=theme.rule, width=3)

    for index, step in enumerate(steps, start=1):
        dot_y = dot_ys[index - 1]
        draw.ellipse([rail_x - 9, dot_y - 9, rail_x + 9, dot_y + 9], fill=theme.accent)
        title, title_issues = _fit(
            step.get("title", ""),
            fonts=fonts,
            weight="bold",
            width=cw - 120,
            max_height=slot * 0.42,
            start_size=theme.size("h2"),
            leading=1.3,
        )
        issues.extend(title_issues)
        draw_lines(
            draw,
            x0 + 96,
            y,
            title.layout,
            font=title.font,
            metrics=title.metrics,
            fill=theme.ink,
            leading=1.3,
        )
        desc_y = y + title.height + 12
        desc, desc_issues = _fit(
            step.get("desc", ""),
            fonts=fonts,
            weight="regular",
            width=cw - 120,
            max_height=slot - title.height - 36,
            start_size=theme.size("small") + 4,
            leading=1.55,
        )
        issues.extend(desc_issues)
        draw_lines(
            draw,
            x0 + 96,
            desc_y,
            desc.layout,
            font=desc.font,
            metrics=desc.metrics,
            fill=theme.muted,
            leading=1.55,
        )
        y += slot

    _footer(draw, theme, fonts, x0, x1, h - 96, spec.get("footer_left", ""), spec.get("meta", ""))


def _note(draw, spec, theme: Theme, fonts: FontSet, w: int, h: int, issues: List[Diagnostic]):
    x0, x1 = MARGIN, w - MARGIN
    cw = x1 - x0
    quote_w = cw * 0.88

    draw.rectangle([x0, 200, x0 + 72, 208], fill=theme.accent)

    text, text_issues = _fit(
        spec["title"],
        fonts=fonts,
        weight="bold",
        width=quote_w,
        max_height=h * 0.46,
        start_size=theme.size("display") * 0.78,
        leading=1.5,
        align="center",
    )
    issues.extend(text_issues)
    y = (h - text.height) * 0.44
    quote_x = x0 + (cw - quote_w) / 2
    draw_lines(
        draw,
        quote_x,
        y,
        text.layout,
        font=text.font,
        metrics=text.metrics,
        fill=theme.ink,
        leading=1.5,
        width=quote_w,
    )

    cite = spec.get("cite", "")
    if cite:
        font = fonts.load(theme.size("small"))
        width = draw.textlength(cite, font=font)
        draw.text(((w - width) / 2, y + text.height + 48), cite, font=font, fill=theme.muted)

    _footer(draw, theme, fonts, x0, x1, h - 96, spec.get("footer_left", ""), spec.get("meta", ""))


_TEMPLATES = {"cover": _cover, "list": _list, "steps": _steps, "note": _note}


# --------------------------------------------------------------------------
# public entry point
# --------------------------------------------------------------------------


def render_card(
    spec: Dict[str, Any],
    theme: Theme,
    fonts: Optional[FontSet] = None,
    canvas: Tuple[int, int] = CANVAS,
) -> Tuple[Image.Image, List[Diagnostic]]:
    """Render one card.

    ``spec`` keys: ``kind`` (cover/list/steps/note), ``title``, and optionally
    ``kicker`` / ``subtitle`` / ``items`` / ``steps`` / ``cite`` / ``meta`` /
    ``footer_left``.  Returns the image plus every diagnostic produced.
    """
    kind = spec.get("kind", "cover")
    if kind not in _TEMPLATES:
        raise ValueError(f"unknown card kind {kind!r}; expected one of {', '.join(KINDS)}")
    if not spec.get("title"):
        raise ValueError("card spec needs a non-empty 'title'")

    fonts = fonts or FontSet.discover()
    w, h = canvas
    scale = w / CANVAS[0]
    theme = theme.scaled(scale)

    image = Image.new("RGB", (w, h), theme.bg)
    draw = ImageDraw.Draw(image)
    issues: List[Diagnostic] = []
    _TEMPLATES[kind](draw, spec, theme, fonts, w, h, issues)
    return image, issues
