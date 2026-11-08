"""Text measurement.

Layout never touches a font directly — it asks a :class:`Metrics` object how
wide a cluster is.  That one indirection is why the engine can be tested
without a font file, and why adapters for ReportLab / fontTools / SVG can be
added later without touching the breaker.
"""

from __future__ import annotations

from typing import Dict, Optional, Protocol, runtime_checkable

from .classify import is_wide, line_break_class

__all__ = ["Metrics", "EmMetrics", "PillowMetrics", "measure"]


@runtime_checkable
class Metrics(Protocol):
    """Anything that can measure a run of text."""

    size: float

    def advance(self, cluster: str) -> float:
        """Width in pixels of one unbreakable cluster."""
        ...


class EmMetrics:
    """Font-free metrics with fixed, documented widths.

    Used by tests, by ``--dry-run`` previews, and as a last-resort fallback
    when no font is available.  Widths are approximations of a typical CJK
    sans: ideographs 1 em, Latin 0.5 em, spaces 0.25 em.

    Deterministic by construction — the same text always yields the same
    numbers, on every platform, which is exactly what the golden tests need.
    """

    __slots__ = ("size", "_cache")

    def __init__(self, size: float = 16.0) -> None:
        if size <= 0:
            raise ValueError("size must be positive")
        self.size = float(size)
        self._cache: Dict[str, float] = {}

    def advance(self, cluster: str) -> float:
        cached = self._cache.get(cluster)
        if cached is not None:
            return cached
        width = self._compute(cluster)
        self._cache[cluster] = width
        return width

    def _compute(self, cluster: str) -> float:
        total = 0.0
        for ch in cluster:
            cls = line_break_class(ch)
            if cls == "CM":
                continue  # combining marks add no advance of their own
            if ch == "\t":
                total += 2.0 * self.size
            elif ch == " ":
                total += 0.25 * self.size
            elif is_wide(ch):
                total += self.size
            else:
                total += 0.5 * self.size
        return total

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"EmMetrics(size={self.size})"


class PillowMetrics:
    """Metrics backed by a real font file via Pillow.

    Pillow is imported lazily so the core package stays dependency-free.
    The font is rasterised at 4x and divided back down, which buys enough
    sub-pixel precision for justification without importing FreeType's
    26.6 fixed-point arithmetic ourselves.
    """

    __slots__ = ("size", "_font", "_scale", "_cache")

    def __init__(self, font_path: str, size: float = 16.0) -> None:
        if size <= 0:
            raise ValueError("size must be positive")
        try:
            from PIL import ImageFont
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise ModuleNotFoundError(
                "PillowMetrics needs Pillow: pip install 'ziban[pillow]'"
            ) from exc
        self.size = float(size)
        self._scale = 4
        px = max(1, int(round(size * self._scale)))
        self._font = ImageFont.truetype(font_path, px)
        self._cache: Dict[str, float] = {}

    def advance(self, cluster: str) -> float:
        cached = self._cache.get(cluster)
        if cached is not None:
            return cached
        width = float(self._font.getlength(cluster)) / self._scale
        self._cache[cluster] = width
        return width

    def __repr__(self) -> str:  # pragma: no cover
        return f"PillowMetrics(font={self._font.path!r}, size={self.size})"


def measure(text: str, metrics: Metrics, letter_spacing: float = 0.0) -> float:
    """Total advance width of ``text`` under ``metrics``."""
    return sum(metrics.advance(ch) + letter_spacing for ch in text)


def resolve(metrics: Optional[Metrics], size: float) -> Metrics:
    """Default to :class:`EmMetrics` when no metrics were supplied."""
    return metrics if metrics is not None else EmMetrics(size)
