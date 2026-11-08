"""Rule sets: the CLREQ-derived data that drives the breaker.

Everything a typesetter would want to argue about lives in
``data/clreq.toml``: which characters may not start a line, which may not end
one, which may be squeezed, how far they may hang.  Code stays generic, so a
Japanese or Korean ruleset is a second TOML file rather than a second engine.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Dict, FrozenSet, Mapping, Union

try:  # Python >= 3.11
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - 3.9 / 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from .classify import NON_ENDER, NON_STARTER, line_break_class

__all__ = ["RuleSet", "load_default", "load"]


@dataclass(frozen=True)
class RuleSet:
    """An immutable set of typographic rules."""

    version: str
    clreq: str
    head_forbidden: FrozenSet[str]
    tail_forbidden: FrozenSet[str]
    compressible: FrozenSet[str]
    hangable: FrozenSet[str]
    compressed_ratio: float = 0.5
    hang_max_ratio: float = 1.0
    hang_max_share: float = 0.25
    cjk_latin_gap: float = 0.25

    # -- queries ---------------------------------------------------------

    def is_head_forbidden(self, ch: str) -> bool:
        """May ``ch`` start a line?  Explicit list first, UAX #14 class second."""
        return ch in self.head_forbidden or line_break_class(ch) in NON_STARTER

    def is_tail_forbidden(self, ch: str) -> bool:
        """May ``ch`` end a line?"""
        return ch in self.tail_forbidden or line_break_class(ch) in NON_ENDER

    def compression_saving(self, ch: str, width: float) -> float:
        """Pixels freed by squeezing ``ch`` (0 if not compressible)."""
        if ch not in self.compressible:
            return 0.0
        return width * (1.0 - self.compressed_ratio)

    def hang_budget(self, size: float, avail: float) -> float:
        """How far a mark may stick out: one em, but never a big share of the column."""
        return min(self.hang_max_ratio * size, self.hang_max_share * avail)

    # -- construction ----------------------------------------------------

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RuleSet":
        kinsoku = data.get("kinsoku", {})
        compress = data.get("compress", {})
        hang = data.get("hang", {})
        spacing = data.get("spacing", {})
        return cls(
            version=str(data.get("version", "0")),
            clreq=str(data.get("clreq", "")),
            head_forbidden=frozenset(kinsoku.get("head_forbidden", "")),
            tail_forbidden=frozenset(kinsoku.get("tail_forbidden", "")),
            compressible=frozenset(compress.get("chars", "")),
            hangable=frozenset(hang.get("chars", "")),
            compressed_ratio=float(compress.get("compressed_ratio", 0.5)),
            hang_max_ratio=float(hang.get("max_ratio", 1.0)),
            hang_max_share=float(hang.get("max_share", 0.25)),
            cjk_latin_gap=float(spacing.get("cjk_latin_gap", 0.25)),
        )

    def with_overrides(
        self,
        *,
        head_forbidden: Union[str, None] = None,
        tail_forbidden: Union[str, None] = None,
        compressible: Union[str, None] = None,
        hangable: Union[str, None] = None,
        compressed_ratio: Union[float, None] = None,
        hang_max_ratio: Union[float, None] = None,
        hang_max_share: Union[float, None] = None,
    ) -> "RuleSet":
        """Return a copy with some fields replaced (additive for char sets)."""
        changes: Dict[str, Any] = {}
        if head_forbidden is not None:
            changes["head_forbidden"] = self.head_forbidden | frozenset(head_forbidden)
        if tail_forbidden is not None:
            changes["tail_forbidden"] = self.tail_forbidden | frozenset(tail_forbidden)
        if compressible is not None:
            changes["compressible"] = self.compressible | frozenset(compressible)
        if hangable is not None:
            changes["hangable"] = self.hangable | frozenset(hangable)
        if compressed_ratio is not None:
            changes["compressed_ratio"] = compressed_ratio
        if hang_max_ratio is not None:
            changes["hang_max_ratio"] = hang_max_ratio
        if hang_max_share is not None:
            changes["hang_max_share"] = hang_max_share
        return replace(self, **changes)


def _read_bundled(name: str) -> str:
    return resources.files("ziban").joinpath("data", name).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_default() -> RuleSet:
    """Load the bundled CLREQ subset (cached — it is immutable)."""
    return RuleSet.from_mapping(tomllib.loads(_read_bundled("clreq.toml")))


def load(path: Union[str, Path]) -> RuleSet:
    """Load a ruleset from an arbitrary TOML file."""
    raw = Path(path).read_text(encoding="utf-8")
    return RuleSet.from_mapping(tomllib.loads(raw))
