"""Render every card kind in every theme, then one contact sheet.

    python examples/cards/build.py

This is the demo that has to keep working: it is what a new user runs first,
and what the README screenshots come from.  It fails loudly (non-zero exit) if
any card reports TEXT_OVERFLOW, because a clipped card is worse than no card.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from ziban.cards import render_card
from ziban.fonts import FontSet
from ziban.theme import THEMES

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
KINDS = ("cover", "list", "steps", "note")
THEME_ORDER = ("ikb", "ink", "citron")


def main() -> int:
    fonts = FontSet.discover()
    print(f"fonts: {fonts.describe()}")
    OUT.mkdir(parents=True, exist_ok=True)

    specs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (HERE / "specs").glob("*.json")}
    missing = [k for k in KINDS if k not in specs]
    if missing:
        print(f"missing specs: {', '.join(missing)}", file=sys.stderr)
        return 2

    failures = 0
    tiles = []
    for theme_name in THEME_ORDER:
        theme = THEMES[theme_name]
        for kind in KINDS:
            image, issues = render_card(specs[kind], theme, fonts)
            path = OUT / f"{theme_name}-{kind}.png"
            image.save(path, optimize=True)
            codes = ", ".join(f"{i.code}" for i in issues) or "clean"
            print(f"  {path.name:<22} {image.width}x{image.height}  {codes}")
            failures += sum(1 for i in issues if i.code == "TEXT_OVERFLOW")
            tiles.append(image)

    # Contact sheet: 3 themes across, 4 kinds down.
    tile_w, tile_h, gap, pad = 340, 453, 24, 32
    sheet_w = pad * 2 + tile_w * 3 + gap * 2
    sheet_h = pad * 2 + tile_h * 4 + gap * 3
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#FFFFFF")
    for index, image in enumerate(tiles):
        col, row = index % 3, index // 3
        x = pad + col * (tile_w + gap)
        y = pad + row * (tile_h + gap)
        sheet.paste(image.resize((tile_w, tile_h), Image.LANCZOS), (x, y))
    sheet_path = OUT / "contact-sheet.png"
    sheet.save(sheet_path, optimize=True)
    print(f"contact sheet: {sheet_path.name} ({sheet.width}x{sheet.height})")

    if failures:
        print(f"FAILED: {failures} card(s) reported TEXT_OVERFLOW", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
