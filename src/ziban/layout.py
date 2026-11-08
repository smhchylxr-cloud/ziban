"""The breaker.

One pass over a paragraph, one decision per line, and every decision is
explainable: ``adjustments`` say *how* a line was made to fit (compressed
punctuation, hanging punctuation) and ``diagnostics`` say *when it could not*
(overflow, forced break, kinsoku fallback).  Silent wrong output is the one
thing this module refuses to produce.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .classify import can_break, is_wide, line_break_class
from .metrics import EmMetrics, Metrics
from .rules import RuleSet, load_default

__all__ = [
    "Style",
    "Line",
    "Adjustment",
    "Diagnostic",
    "Layout",
    "layout",
    "OVERFLOW",
    "NO_BREAK_OPPORTUNITY",
    "KINSOKU_FALLBACK",
    "ORPHAN_LINE",
]

EPS = 1e-6

#: The line is wider than the box and nothing could fix it.
OVERFLOW = "OVERFLOW"
#: A single unbreakable run (a long Latin word, a URL) is wider than the box.
NO_BREAK_OPPORTUNITY = "NO_BREAK_OPPORTUNITY"
#: Hanging/compression were refused, so the line was cut short on purpose.
KINSOKU_FALLBACK = "KINSOKU_FALLBACK"
#: The final line of a paragraph holds a single character (孤字).
ORPHAN_LINE = "ORPHAN_LINE"

_MESSAGES: Dict[str, Tuple[str, str]] = {
    OVERFLOW: (
        "Line is wider than the box.",
        "Widen the box, reduce size, or enable allow_hang/allow_compress.",
    ),
    NO_BREAK_OPPORTUNITY: (
        "No legal break point exists inside this run.",
        "Insert a zero-width space, allow hyphenation, or widen the box.",
    ),
    KINSOKU_FALLBACK: (
        "Punctuation could not be kept on the previous line.",
        "Raise hang_max_ratio or compressed_ratio, or accept a shorter line.",
    ),
    ORPHAN_LINE: (
        "The last line of this paragraph holds a single character.",
        "Shorten the text or let the renderer rebalance the final two lines.",
    ),
}


@dataclass(frozen=True)
class Style:
    """Everything the caller is allowed to argue about."""

    size: float = 16.0
    leading: float = 1.7
    letter_spacing: float = 0.0
    first_line_indent: float = 0.0  # in em
    align: str = "left"
    allow_hang: bool = True
    allow_compress: bool = True

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("Style.size must be > 0")
        if self.leading <= 0:
            raise ValueError("Style.leading must be > 0")
        if self.align not in ("left", "justify", "center", "right"):
            raise ValueError(f"unknown align: {self.align!r}")


@dataclass(frozen=True)
class Adjustment:
    """A local fix applied to one cluster of a line.

    ``kind == "compress"``: the cluster was drawn narrower, freeing ``delta`` px.
    ``kind == "hang"``: the cluster was allowed to stick out by ``delta`` px.
    """

    kind: str
    index: int  # cluster index, relative to the start of this line
    delta: float


@dataclass(frozen=True)
class Line:
    text: str
    width: float
    start: int  # character offset in the source text
    end: int
    hard_break: bool = False
    adjustments: Tuple[Adjustment, ...] = ()
    slack: float = 0.0
    justify_spacing: float = 0.0
    overflow: float = 0.0

    @property
    def fill(self) -> float:
        """How full the line is, 0..1-ish (can exceed 1 for hanging lines)."""
        total = self.width + self.slack
        return 0.0 if total <= 0 else self.width / total


@dataclass(frozen=True)
class Diagnostic:
    code: str
    line: int
    message: str
    fix: str


@dataclass
class Layout:
    lines: List[Line]
    diagnostics: List[Diagnostic]
    width: float
    style: Style
    rules: RuleSet
    text: str = ""
    _char_count: int = field(default=0, repr=False)

    @property
    def overflow(self) -> float:
        return max((ln.overflow for ln in self.lines), default=0.0)

    @property
    def ok(self) -> bool:
        return not self.diagnostics

    def codes(self) -> List[str]:
        return [d.code for d in self.diagnostics]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "style": {
                "size": self.style.size,
                "leading": self.style.leading,
                "align": self.style.align,
                "first_line_indent": self.style.first_line_indent,
                "allow_hang": self.style.allow_hang,
                "allow_compress": self.style.allow_compress,
            },
            "rules_version": self.rules.version,
            "overflow": self.overflow,
            "lines": [
                {
                    "text": ln.text,
                    "width": round(ln.width, 3),
                    "start": ln.start,
                    "end": ln.end,
                    "hard_break": ln.hard_break,
                    "slack": round(ln.slack, 3),
                    "justify_spacing": round(ln.justify_spacing, 3),
                    "overflow": round(ln.overflow, 3),
                    "adjustments": [
                        {"kind": a.kind, "index": a.index, "delta": round(a.delta, 3)}
                        for a in ln.adjustments
                    ],
                }
                for ln in self.lines
            ],
            "diagnostics": [
                {"code": d.code, "line": d.line, "message": d.message, "fix": d.fix}
                for d in self.diagnostics
            ],
        }

    def __str__(self) -> str:  # pragma: no cover - convenience
        return "\n".join(ln.text for ln in self.lines)


def _clusters(paragraph: str) -> List[str]:
    """Split into unbreakable clusters; combining marks join the previous one."""
    out: List[str] = []
    for ch in paragraph:
        if out and (line_break_class(ch) == "CM" or ch == "\u200d"):
            out[-1] += ch
        else:
            out.append(ch)
    return out


class _Breaker:
    """Holds the per-paragraph state so the methods stay readable."""

    def __init__(
        self,
        clusters: Sequence[str],
        widths: Sequence[float],
        can_break_before: Sequence[bool],
        width: float,
        style: Style,
        rules: RuleSet,
    ) -> None:
        self.clusters = list(clusters)
        self.widths = list(widths)
        self.can_break_before = list(can_break_before)
        self.n = len(self.clusters)
        self.width = width
        self.style = style
        self.rules = rules
        self.cum: List[float] = [0.0]
        for w in self.widths:
            self.cum.append(self.cum[-1] + w)

    # -- one line --------------------------------------------------------

    def _cut(
        self, start: int, avail: float
    ) -> Tuple[int, Tuple[Adjustment, ...], Tuple[str, ...]]:
        n, cum = self.n, self.cum
        limit = bisect.bisect_right(cum, cum[start] + avail + EPS) - 1
        if limit > n:
            limit = n

        if limit <= start:
            # Not even one cluster fits: emit it anyway and say so.
            return min(start + 1, n), (), (NO_BREAK_OPPORTUNITY,)

        # Longest legal break that fits on this line.
        best = limit
        while best > start and not self.can_break_before[best]:
            best -= 1

        if best == start:
            # Nothing legal fits; run to the next legal break and overflow.
            end = limit
            while end < n and not self.can_break_before[end]:
                end += 1
            if end == start:
                end = min(start + 1, n)
            return end, (), (NO_BREAK_OPPORTUNITY,)

        if best == limit:
            # The natural cut is already a legal break point.
            return limit, (), ()

        # best < limit: a head-forbidden cluster blocked the natural cut.
        # Try to keep it on this line — squeeze first, then hang.
        end = limit
        adjustments: List[Adjustment] = []
        saved_total = 0.0
        while (
            end < n
            and not self.can_break_before[end]
            and self.rules.is_head_forbidden(self.clusters[end])
        ):
            ch, w = self.clusters[end], self.widths[end]
            over = (cum[end + 1] - cum[start]) - avail - saved_total
            if over <= EPS:  # it just fits; nothing to explain
                end += 1
                continue

            budget = (
                self.rules.hang_budget(self.style.size, avail)
                if self.style.allow_hang
                else 0.0
            )
            saving = (
                self.rules.compression_saving(ch, w)
                if self.style.allow_compress
                else 0.0
            )

            if saving > 0.0 and over <= saving + EPS:
                # Squeezing alone is enough: keep the mark inside the margin.
                adjustments.append(Adjustment("compress", end - start, saving))
                saved_total += saving
                end += 1
                continue
            if over <= budget + EPS:
                adjustments.append(Adjustment("hang", end - start, over))
                end += 1
                continue
            if saving > 0.0 and over - saving <= budget + EPS:
                # Heavy mark: squeeze it and hang what is left. This is what
                # keeps "。」" on one line instead of pushing both down.
                adjustments.append(Adjustment("compress", end - start, saving))
                adjustments.append(Adjustment("hang", end - start, over - saving))
                saved_total += saving
                end += 1
                continue
            break

        if end < n and not self.can_break_before[end]:
            # Back off to a legal cut. Only shout if kinsoku was the reason:
            # refusing to break inside "2026" is normal, not a compromise.
            if self.rules.is_head_forbidden(self.clusters[limit]):
                return best, (), (KINSOKU_FALLBACK,)
            return best, (), ()
        return end, tuple(adjustments), ()

    # -- all lines -------------------------------------------------------

    def run(self, base_offset: int) -> Tuple[List[Line], List[Diagnostic]]:
        lines: List[Line] = []
        diagnostics: List[Diagnostic] = []
        n = self.n
        i = 0
        first = True

        while i < n:
            indent = self.style.first_line_indent * self.style.size if first else 0.0
            avail = self.width - indent
            if avail <= EPS:
                avail = self.width

            cut, adjustments, codes = self._cut(i, avail)

            end = cut
            while end > i and self.clusters[end - 1] == " ":
                end -= 1
            if end == i:  # the line held only spaces
                end = cut

            text = "".join(self.clusters[i:end])
            compressed = sum(a.delta for a in adjustments if a.kind == "compress")
            hung = sum(a.delta for a in adjustments if a.kind == "hang")
            width = self.cum[end] - self.cum[i] - compressed
            # A hanging glyph is *supposed* to sit outside the margin, so it
            # only counts against us if it exceeds its own hang budget.
            overflow = max(0.0, (width - hung) - self.width)
            slack = (self.width - indent) - width

            justify = 0.0
            if self.style.align == "justify" and slack > EPS and cut < n:
                gaps = self._gaps(i, end)
                if gaps > 0:
                    justify = slack / gaps

            for code in codes:
                message, fix = _MESSAGES[code]
                diagnostics.append(
                    Diagnostic(code, len(lines), message, fix)
                )
            if overflow > EPS and OVERFLOW not in codes:
                message, fix = _MESSAGES[OVERFLOW]
                diagnostics.append(Diagnostic(OVERFLOW, len(lines), message, fix))

            lines.append(
                Line(
                    text=text,
                    width=width,
                    start=base_offset + self._offset(i),
                    end=base_offset + self._offset(end),
                    hard_break=False,
                    adjustments=adjustments,
                    slack=slack,
                    justify_spacing=justify,
                    overflow=overflow,
                )
            )
            i = cut
            first = False

        return lines, diagnostics

    def _gaps(self, i: int, end: int) -> int:
        count = end - i
        if count < 2:
            return 0
        wide = sum(1 for k in range(i, end) if is_wide(self.clusters[k]))
        if wide * 2 >= count:  # CJK-dominant: justify between characters
            return count - 1
        return sum(1 for k in range(i, end) if self.clusters[k] == " ")

    def _offset(self, cluster_index: int) -> int:
        if not hasattr(self, "_offsets"):
            offsets = [0]
            for c in self.clusters:
                offsets.append(offsets[-1] + len(c))
            self._offsets = offsets
        return self._offsets[cluster_index]


def layout(
    text: str,
    *,
    width: float,
    style: Optional[Style] = None,
    metrics: Optional[Metrics] = None,
    rules: Optional[RuleSet] = None,
) -> Layout:
    """Break ``text`` into lines that fit ``width`` pixels.

    Hard breaks (``\\n``) are always honoured; every other decision follows the
    ruleset.  This function never raises on typographically impossible input —
    it returns diagnostics instead.
    """
    if width <= 0:
        raise ValueError("width must be > 0")
    style = style or Style()
    rules = rules or load_default()
    metrics = metrics if metrics is not None else EmMetrics(style.size)

    lines: List[Line] = []
    diagnostics: List[Diagnostic] = []
    offset = 0

    paragraphs = text.split("\n")
    for index, paragraph in enumerate(paragraphs):
        is_last_paragraph = index == len(paragraphs) - 1
        if paragraph == "":
            lines.append(
                Line(
                    text="",
                    width=0.0,
                    start=offset,
                    end=offset,
                    hard_break=not is_last_paragraph,
                    slack=width,
                )
            )
            offset += 1
            continue

        clusters = _clusters(paragraph)
        widths = [metrics.advance(c) + style.letter_spacing for c in clusters]
        if not widths:  # pragma: no cover - guarded by paragraph == ""
            offset += len(paragraph) + 1
            continue

        can_break_before: List[bool] = [False] * (len(clusters) + 1)
        for k in range(1, len(clusters)):
            can_break_before[k] = can_break(clusters[k - 1], clusters[k])
        can_break_before[len(clusters)] = True

        breaker = _Breaker(clusters, widths, can_break_before, width, style, rules)
        para_lines, para_diags = breaker.run(offset)

        if para_lines:
            if is_last_paragraph:
                pass
            else:
                last = para_lines[-1]
                para_lines[-1] = Line(
                    text=last.text,
                    width=last.width,
                    start=last.start,
                    end=last.end,
                    hard_break=True,
                    adjustments=last.adjustments,
                    slack=last.slack,
                    justify_spacing=last.justify_spacing,
                    overflow=last.overflow,
                )
            if len(para_lines) > 1 and len(para_lines[-1].text) <= 1:
                message, fix = _MESSAGES[ORPHAN_LINE]
                para_diags.append(
                    Diagnostic(ORPHAN_LINE, len(lines) + len(para_lines) - 1, message, fix)
                )

        shift = len(lines)
        for d in para_diags:
            diagnostics.append(
                Diagnostic(d.code, d.line + shift, d.message, d.fix)
            )
        lines.extend(para_lines)
        offset += len(paragraph) + (0 if is_last_paragraph else 1)

    return Layout(
        lines=lines,
        diagnostics=diagnostics,
        width=width,
        style=style,
        rules=rules,
        text=text,
        _char_count=len(text),
    )



