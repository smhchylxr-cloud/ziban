"""Render the README's money shot: naive chunking vs ziban, same text, same column.

    python examples/compare.py --font C:/Windows/Fonts/NotoSansSC-VF.ttf

The left panel cuts the string every N characters — the way almost every
non-browser renderer does it.  The right panel asks ziban.  The dashed line is
the measure: punctuation on the right is allowed to cross it (hanging) instead
of being pushed onto the next line.

Text is drawn cluster by cluster so that compressed punctuation is actually
drawn compressed, at the same positions the breaker computed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ziban import Style, layout, load_default
from ziban.metrics import PillowMetrics

TEXT = (
    "他说：「这次不一样。」然后关掉了对话框。"
    "中文排版不是把字排整齐，而是让标点不去它不该去的地方。"
)

BG = "#FCFCFA"
INK = "#1A1A1A"
MUTED = "#8A8A85"
BAD = "#C0392B"
GOOD = "#2D6A4F"
RULE = "#DCDCD4"


def naive_lines(text: str, width_em: int) -> list[str]:
    return [text[i : i + width_em] for i in range(0, len(text), width_em)]


def draw_line(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    line,
    *,
    font: ImageFont.FreeTypeFont,
    metrics: PillowMetrics,
    fill: str,
) -> float:
    """Draw one laid-out line, honouring compression, and return its end x."""
    squeezed = {a.index: a.delta for a in line.adjustments if a.kind == "compress"}
    pen = x
    for index, char in enumerate(text):
        draw.text((pen, y), char, font=font, fill=fill)
        pen += metrics.advance(char) - squeezed.get(index, 0.0)
    return pen


def panel(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    title: str,
    subtitle: str,
    lines: list,
    *,
    font: ImageFont.FreeTypeFont,
    title_font: ImageFont.FreeTypeFont,
    small: ImageFont.FreeTypeFont,
    metrics: PillowMetrics,
    line_height: float,
    width: float,
    mark_violations: bool,
    rules,
) -> int:
    draw.text((x, y - 86), title, font=title_font, fill=INK)
    draw.text((x, y - 48), subtitle, font=small, fill=MUTED)

    bottom = y + line_height * len(lines) - 6
    for dash in range(y - 10, int(bottom), 10):
        draw.line([(x + width, dash), (x + width, dash + 5)], fill=RULE, width=2)

    violations = 0
    for index, line in enumerate(lines):
        baseline = y + index * line_height
        text = line.text if hasattr(line, "text") else line
        if mark_violations and index > 0 and text and rules.is_head_forbidden(text[0]):
            violations += 1
            draw.text((x - 26, baseline + 2), "\u2715", font=small, fill=BAD)
            draw.line(
                [(x - 2, baseline + line_height - 16), (x + metrics.advance(text[0]), baseline + line_height - 16)],
                fill=BAD,
                width=2,
            )
        if hasattr(line, "text"):
            draw_line(draw, x, baseline, text, line, font=font, metrics=metrics, fill=INK)
        else:
            draw.text((x, baseline), text, font=font, fill=INK)
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", required=True)
    parser.add_argument("--out", default="docs/compare.png")
    parser.add_argument("--size", type=int, default=36)
    parser.add_argument("--width-em", type=int, default=10)
    args = parser.parse_args()

    size, width_em = args.size, args.width_em
    line_height = size * 1.75
    panel_w = width_em * size
    gap, margin = 96, 86

    rules = load_default()
    metrics = PillowMetrics(args.font, size)
    result = layout(
        TEXT,
        width=panel_w,
        style=Style(size=size, leading=1.75),
        metrics=metrics,
    )
    naive = naive_lines(TEXT, width_em)

    rows = max(len(naive), len(result.lines))
    height = int(190 + rows * line_height + 110)
    width = margin * 2 + panel_w * 2 + gap
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype(args.font, size)
    title_font = ImageFont.truetype(args.font, 34)
    small = ImageFont.truetype(args.font, 15)
    header_font = ImageFont.truetype(args.font, 22)

    draw.text((margin, 44), "Same text. Same column.", font=header_font, fill=INK)
    draw.text(
        (margin, 76),
        "\u5b57\u6570\u786c\u5207 vs \u6309 CLREQ \u89c4\u5219\u65ad\u884c",
        font=small,
        fill=MUTED,
    )

    y = 190
    left = panel(
        draw,
        margin,
        y,
        "\u786c\u5207",
        "\u6bcf N \u4e2a\u5b57\u780d\u4e00\u5200",
        naive,
        font=font,
        title_font=title_font,
        small=small,
        metrics=metrics,
        line_height=line_height,
        width=panel_w,
        mark_violations=True,
        rules=rules,
    )
    panel(
        draw,
        margin + panel_w + gap,
        y,
        "ziban",
        "\u907f\u5934\u5c3e \u00b7 \u6324\u538b \u00b7 \u6807\u70b9\u60ac\u6302",
        result.lines,
        font=font,
        title_font=title_font,
        small=small,
        metrics=metrics,
        line_height=line_height,
        width=panel_w,
        mark_violations=False,
        rules=rules,
    )

    caption_y = height - 92
    draw.text(
        (margin, caption_y),
        f"{left} \u5904\u884c\u9996\u8fdd\u89c4  \u2192  0",
        font=title_font,
        fill=BAD if left else GOOD,
    )
    draw.text(
        (margin, caption_y + 46),
        "\u865a\u7ebf\u662f\u7248\u5fc3\uff1a\u53f3\u4fa7\u6807\u70b9\u53ef\u4ee5\u60ac\u51fa\u7248\u5fc3\uff0c\u800c\u4e0d\u5fc5\u6324\u5230\u4e0b\u4e00\u884c\u3002",
        font=small,
        fill=MUTED,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, optimize=True)
    print(f"wrote {out} ({image.width}x{image.height}), {left} violation(s) on the left")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
