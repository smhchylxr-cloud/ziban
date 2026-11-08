"""Three palettes and one type scale, sized for 1080×1440 cards.

Themes are data: colours plus a type scale.  Nothing about a layout lives
here, so a fourth theme is a new entry, not new code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping

__all__ = ["Theme", "THEMES", "get", "names"]


@dataclass(frozen=True)
class Theme:
    """A palette plus the sizes a card template may ask for."""

    name: str
    label: str
    bg: str
    ink: str
    muted: str
    accent: str
    accent_ink: str
    rule: str
    #: base sizes in px, measured against a 1080-wide canvas
    sizes: Mapping[str, int] = field(default_factory=dict)

    def size(self, role: str, fallback: int = 38) -> int:
        return int(self.sizes.get(role, fallback))

    def scaled(self, factor: float) -> "Theme":
        """Same palette, every size multiplied — for canvases that aren't 1080 wide."""
        if abs(factor - 1.0) < 1e-6:
            return self
        return Theme(
            name=self.name,
            label=self.label,
            bg=self.bg,
            ink=self.ink,
            muted=self.muted,
            accent=self.accent,
            accent_ink=self.accent_ink,
            rule=self.rule,
            sizes={k: int(round(v * factor)) for k, v in self.sizes.items()},
        )


_SCALE = {
    "display": 96,
    "h1": 64,
    "h2": 44,
    "body": 38,
    "small": 28,
    "micro": 22,
    "mono": 34,
    "numeral": 72,
}

THEMES: Dict[str, Theme] = {
    # 克莱因蓝印在米白纸上 —— 我们自己的默认主题
    "ikb": Theme(
        name="ikb",
        label="IKB 蓝 / 米白纸",
        bg="#F4F1EA",
        ink="#0B0B0C",
        muted="#6A655C",
        accent="#002FA7",
        accent_ink="#F4F1EA",
        rule="#D9D4C8",
        sizes=_SCALE,
    ),
    # 墨黑底 —— 深色信息流里最抓眼的一版
    "ink": Theme(
        name="ink",
        label="墨黑 / 朱橙",
        bg="#131416",
        ink="#F3F0E9",
        muted="#9C968A",
        accent="#FF5A36",
        accent_ink="#131416",
        rule="#2C2D31",
        sizes=_SCALE,
    ),
    # 柠檬黄 —— 用来做对比图、强调页
    "citron": Theme(
        name="citron",
        label="柠檬黄 / 墨字",
        bg="#EFF84A",
        ink="#14140F",
        muted="#54542F",
        accent="#14140F",
        accent_ink="#EFF84A",
        rule="#C6D036",
        sizes=_SCALE,
    ),
}


def get(name: str) -> Theme:
    try:
        return THEMES[name]
    except KeyError:
        raise KeyError(
            f"unknown theme {name!r}; available: {', '.join(sorted(THEMES))}"
        ) from None


def names() -> list:
    return sorted(THEMES)
