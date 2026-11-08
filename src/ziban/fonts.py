"""Find a CJK font on the machine, without shipping one.

The library must not bundle fonts: Microsoft YaHei and PingFang are not
redistributable, and a package that ships one is a package companies cannot
use.  So we probe the system, in a documented order, and fail with a message
that says exactly what to install.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

__all__ = ["FontSet", "candidates", "find_regular", "find_bold"]

#: (regular, bold, mono) triples, most preferred first, per platform.
_WINDOWS: Sequence[Tuple[str, str, str]] = (
    (
        r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
        r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
        r"C:\Windows\Fonts\consola.ttf",
    ),
    (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\consola.ttf",
    ),
    (
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\consola.ttf",
    ),
    (
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\simsunb.ttf",
        r"C:\Windows\Fonts\consola.ttf",
    ),
)

_MACOS: Sequence[Tuple[str, str, str]] = (
    (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Menlo.ttc",
    ),
    (
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Menlo.ttc",
    ),
    (
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ),
)

_LINUX: Sequence[Tuple[str, str, str]] = (
    (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ),
    (
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ),
    (
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ),
)


def candidates() -> List[Tuple[Path, Path, Path]]:
    """The (regular, bold, mono) triples worth trying, in order, for this OS."""
    table = _WINDOWS if sys.platform.startswith("win") else (
        _MACOS if sys.platform == "darwin" else _LINUX
    )
    return [(Path(a), Path(b), Path(c)) for a, b, c in table]


def find_regular() -> Path:
    """First existing CJK font, or a RuntimeError that names the fix."""
    for regular, _bold, _mono in candidates():
        if regular.exists():
            return regular
    raise RuntimeError(
        "no CJK font found. Install one of: Noto Sans CJK / Source Han Sans / "
        "any system CJK font, or pass an explicit path (ziban --font)."
    )


def find_bold() -> Path:
    for _regular, bold, _mono in candidates():
        if bold.exists():
            return bold
    return find_regular()


@dataclass(frozen=True)
class FontSet:
    """Three font files: body/display, bold, and a monospace for figures."""

    regular: Path
    bold: Path
    mono: Path

    @classmethod
    def discover(cls) -> "FontSet":
        for regular, bold, mono in candidates():
            if regular.exists():
                return cls(
                    regular=regular,
                    bold=bold if bold.exists() else regular,
                    mono=mono if mono.exists() else regular,
                )
        raise RuntimeError(
            "no CJK font found. On Debian/Ubuntu: apt install fonts-noto-cjk. "
            "On macOS the system PingFang is used. On Windows, Microsoft YaHei."
        )

    @classmethod
    def from_path(cls, path: str | Path) -> "FontSet":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"font not found: {p}")
        return cls(regular=p, bold=p, mono=p)

    def load(self, size: float, *, weight: str = "regular"):
        """A Pillow font at ``size`` (points == pixels here).

        Variable fonts (Noto Sans SC-VF, Source Han Sans VF) expose every weight
        from one file, so asking for "bold" means selecting an axis instance —
        passing the same file twice would silently render a regular weight.
        """
        from PIL import ImageFont

        path = {"regular": self.regular, "bold": self.bold, "mono": self.mono}[weight]
        font = ImageFont.truetype(str(path), int(round(size)))

        # Variable fonts expose every weight from one file, and their *default*
        # instance is not always Regular — Noto Sans SC-VF defaults to Thin
        # (weight 100), which silently renders every card in a hairline weight.
        # So the axis is set explicitly, for regular as well as bold.
        if weight in ("regular", "bold"):
            wanted = (
                ("Bold", "SemiBold", "Medium", "DemiBold")
                if weight == "bold"
                else ("Regular", "Medium", "Light")
            )
            for instance in wanted:
                try:
                    font.set_variation_by_name(instance)
                    break
                except Exception:
                    # Not a variable font (a real bold file was chosen instead).
                    continue
        return font

    def describe(self) -> str:
        return f"{self.regular.name} / {self.bold.name} / {self.mono.name}"
