"""Command line interface.

Two jobs: let a human *see* the break decisions in a terminal, and let a
program (or an agent) get the same decisions as JSON.  The terminal view is
the point — once you have watched punctuation stop landing at the start of
lines, you never go back to eyeballing a rendered image.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__
from .layout import Layout, Style, layout
from .metrics import EmMetrics, PillowMetrics
from .rules import load_default


def _width(text: str) -> int:
    """Terminal columns occupied by ``text`` (CJK counts as two)."""
    total = 0
    for ch in text:
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def _pad(text: str, columns: int) -> str:
    return text + " " * max(0, columns - _width(text))


def _marker(line) -> str:
    kinds = {a.kind for a in line.adjustments}
    if line.overflow > 0.01:
        return "!"
    if "hang" in kinds:
        return ">"
    if "compress" in kinds:
        return "<"
    return " "


def render_terminal(result: Layout, *, max_lines: int = 0, show_ruler: bool = False) -> str:
    size = result.style.size
    columns = int(round(result.width / size * 2))
    out: List[str] = []
    if show_ruler:
        out.append(" " * 6 + "+" + "-" * columns + "+")
    for index, line in enumerate(result.lines, 1):
        if max_lines and index > max_lines:
            out.append(f"    ... {len(result.lines) - max_lines} more line(s)")
            break
        em = line.width / size
        marks = []
        for adj in line.adjustments:
            marks.append("hang" if adj.kind == "hang" else "squeeze")
        status = " ".join(marks)
        if line.overflow > 0.01:
            status = f"{status} overflow".strip()
        if line.hard_break:
            status = f"{status} (hard break)".strip()
        gut = f"{index:>3} {_marker(line)} |"
        out.append(
            f"{gut} {_pad(line.text, columns)} |{em:6.1f}em {status}".rstrip()
        )
    out.append("")
    codes = sorted({d.code for d in result.diagnostics})
    summary = f"{len(result.lines)} line(s), box {result.width / size:.1f}em"
    if codes:
        summary += f", diagnostics: {', '.join(codes)}"
    else:
        summary += ", no diagnostics"
    out.append(summary)
    return "\n".join(out)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ziban",
        description="CJK typesetting for programmatic renderers.",
    )
    parser.add_argument("--version", action="version", version=f"ziban {__version__}")
    sub = parser.add_subparsers(dest="command")

    wrap = sub.add_parser("wrap", help="break text into lines and show the result")
    wrap.add_argument("path", nargs="?", default="-", help="file to read, or - for stdin")
    wrap.add_argument(
        "--width-em", type=float, default=24.0, help="line width in em (default: 24)"
    )
    wrap.add_argument("--size", type=float, default=16.0, help="font size in px (default: 16)")
    wrap.add_argument("--font", default=None, help="path to a .ttf/.otf to measure with")
    wrap.add_argument("--indent", type=float, default=0.0, help="first-line indent in em")
    wrap.add_argument("--justify", action="store_true", help="compute justification spacing")
    wrap.add_argument("--no-hang", action="store_true", help="disable hanging punctuation")
    wrap.add_argument("--no-compress", action="store_true", help="disable punctuation compression")
    wrap.add_argument("--max-lines", type=int, default=0, help="only show the first N lines")
    wrap.add_argument("--ruler", action="store_true", help="draw a ruler above the box")
    wrap.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    rules = sub.add_parser("rules", help="show the active ruleset")
    rules.add_argument("--json", action="store_true")

    card = sub.add_parser("card", help="render a card spec (JSON) to PNG")
    card.add_argument("spec", help="path to a card spec JSON file")
    card.add_argument("--theme", default="ikb", help="ikb | ink | citron (default: ikb)")
    card.add_argument("--out", default=None, help="output PNG (default: next to the spec)")
    card.add_argument("--width", type=int, default=1080, help="canvas width in px")
    card.add_argument("--font", default=None, help="path to a CJK font file")

    themes = sub.add_parser("themes", help="list the built-in themes")
    return parser


def _read_text(path: str) -> str:
    if path == "-":
        data = sys.stdin.buffer.read()
        text = data.decode("utf-8")
    else:
        candidate = Path(path)
        if not candidate.exists():
            raise FileNotFoundError(path)
        text = candidate.read_text(encoding="utf-8")
    # Windows pipes and editors hand us CRLF; the breaker only knows "\n".
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


def _cmd_wrap(args: argparse.Namespace) -> int:
    try:
        text = _read_text(args.path)
    except FileNotFoundError:
        print(f"ziban: file not found: {args.path}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as exc:
        print(f"ziban: input is not UTF-8 ({exc})", file=sys.stderr)
        return 2

    if args.font:
        try:
            metrics = PillowMetrics(args.font, args.size)
        except Exception as exc:  # noqa: BLE001 - surface any font failure plainly
            print(f"ziban: cannot load font {args.font!r}: {exc}", file=sys.stderr)
            return 2
    else:
        metrics = EmMetrics(args.size)

    style = Style(
        size=args.size,
        align="justify" if args.justify else "left",
        first_line_indent=args.indent,
        allow_hang=not args.no_hang,
        allow_compress=not args.no_compress,
    )
    result = layout(
        text,
        width=args.width_em * args.size,
        style=style,
        metrics=metrics,
    )

    if args.json:
        payload = result.to_dict()
        payload["engine"] = {"name": "ziban", "version": __version__}
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(render_terminal(result, max_lines=args.max_lines, show_ruler=args.ruler))
    return 0


def _cmd_rules(args: argparse.Namespace) -> int:
    rules = load_default()
    if args.json:
        json.dump(
            {
                "version": rules.version,
                "clreq": rules.clreq,
                "head_forbidden": "".join(sorted(rules.head_forbidden)),
                "tail_forbidden": "".join(sorted(rules.tail_forbidden)),
                "compressible": "".join(sorted(rules.compressible)),
                "hangable": "".join(sorted(rules.hangable)),
                "compressed_ratio": rules.compressed_ratio,
                "hang_max_ratio": rules.hang_max_ratio,
                "cjk_latin_gap": rules.cjk_latin_gap,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0
    print(f"ruleset   {rules.version}  ({rules.clreq})")
    print(f"避头点    {len(rules.head_forbidden)} chars")
    print(f"避尾点    {len(rules.tail_forbidden)} chars")
    print(f"可挤压    {len(rules.compressible)} chars @ {rules.compressed_ratio:.2f}")
    print(f"可悬挂    {len(rules.hangable)} chars, max {rules.hang_max_ratio:.2f}em")
    print(f"中西间隙  {rules.cjk_latin_gap:.2f}em (M2)")
    return 0


def _cmd_themes(_args: argparse.Namespace) -> int:
    from .theme import THEMES

    for name in sorted(THEMES):
        theme = THEMES[name]
        print(f"{name:<8} {theme.label:<18} bg={theme.bg} ink={theme.ink} accent={theme.accent}")
    return 0


def _cmd_card(args: argparse.Namespace) -> int:
    import json

    from .cards import CANVAS, render_card
    from .fonts import FontSet
    from .theme import get as get_theme

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"ziban: spec not found: {spec_path}", file=sys.stderr)
        return 2
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ziban: {spec_path.name} is not valid JSON ({exc})", file=sys.stderr)
        return 2

    try:
        fonts = FontSet.from_path(args.font) if args.font else FontSet.discover()
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"ziban: {exc}", file=sys.stderr)
        return 2

    theme = get_theme(args.theme)
    width = max(200, args.width)
    canvas = (width, int(round(width * CANVAS[1] / CANVAS[0])))
    image, issues = render_card(spec, theme, fonts, canvas)

    out = Path(args.out) if args.out else spec_path.with_suffix(".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, optimize=True)
    print(f"wrote {out} ({image.width}x{image.height}, theme={theme.name}, fonts={fonts.describe()})")
    for issue in issues:
        print(f"  [{issue.code}] {issue.message}")
    return 2 if any(issue.code == "TEXT_OVERFLOW" for issue in issues) else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "wrap":
        return _cmd_wrap(args)
    if args.command == "rules":
        return _cmd_rules(args)
    if args.command == "card":
        return _cmd_card(args)
    if args.command == "themes":
        return _cmd_themes(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
