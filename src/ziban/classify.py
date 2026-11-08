"""Unicode line-breaking classes, reduced to what CJK typesetting actually needs.

Why a hand-written table?  Python's :mod:`unicodedata` does not expose the
``Line_Break`` property, and depending on ICU (via PyICU) would trade a 30 KB
table for a 30 MB binary dependency — unacceptable for a library whose whole
promise is "``pip install`` and go, no browser, no native build".

So we ship a curated subset of UAX #14 classes.  Anything outside the table
falls back to: wide/fullwidth characters are ``ID`` (ideographic, breakable
between each other), everything else is ``AL`` (alphabetic, never breakable
inside a run).  That fallback is deliberately conservative: a missed rule
gives a slightly ugly line; a wrong rule gives broken text.
"""

from __future__ import annotations

import bisect
import unicodedata
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------
# classes (plain str constants: cheaper than Enum, and they show up in JSON)
# --------------------------------------------------------------------------

BK = "BK"  # mandatory break
CR = "CR"
LF = "LF"
SP = "SP"  # space
ZW = "ZW"  # zero width space
GL = "GL"  # non-breaking glue (NBSP, word joiner-ish)
WJ = "WJ"  # word joiner
CL = "CL"  # close punctuation  。）」 — cannot start a line
CP = "CP"  # close parenthesis )
EX = "EX"  # exclamation ！？
IS = "IS"  # infix separator ，：；
SY = "SY"  # symbol allowing break after /
OP = "OP"  # open punctuation （「 — cannot end a line
QU = "QU"  # quotation mark
NS = "NS"  # nonstarter 々ー…· — cannot start a line
ID = "ID"  # ideographic — breakable between peers
AL = "AL"  # alphabetic
NU = "NU"  # numeric
PO = "PO"  # postfix numeric % ‰ — cannot start a line
PR = "PR"  # prefix numeric ￥$ — cannot end a line
HY = "HY"  # hyphen — break after, hyphen stays
BA = "BA"  # break after (dashes, tabs)
BB = "BB"  # break before
IN = "IN"
CM = "CM"  # combining mark — sticks to the previous cluster
EB = "EB"  # emoji base
EM = "EM"

#: Classes that must never begin a line (避头点 / non-starters).
NON_STARTER = frozenset({CL, CP, EX, IS, SY, NS, PO, CM, WJ, GL})

#: Classes that must never end a line (避尾点 / non-enders).
NON_ENDER = frozenset({OP, QU, PR, BB})

#: Classes that are "wide" by default — used by :class:`EmMetrics` and by the
#: east-asian-width fallback.
WIDE = frozenset({ID, CL, CP, EX, IS, SY, OP, NS})

__all__ = [
    "line_break_class",
    "can_break",
    "is_wide",
    "NON_STARTER",
    "NON_ENDER",
    "WIDE",
]


def _ascii_table() -> List[str]:
    table = [AL] * 128
    table[0x09] = BA
    table[0x0A] = BK
    table[0x0D] = CR
    table[0x20] = SP
    for cp, cls in {
        0x21: EX,
        0x22: QU,
        0x24: PR,
        0x25: PO,
        0x27: QU,
        0x28: OP,
        0x29: CP,
        0x2C: IS,
        0x2D: HY,
        0x2E: IS,
        0x2F: SY,
        0x3A: IS,
        0x3B: IS,
        0x3F: EX,
        0x5B: OP,
        0x5D: CP,
        0x7B: OP,
        0x7D: CL,
    }.items():
        table[cp] = cls
    for cp in range(0x30, 0x3A):
        table[cp] = NU
    return table


_ASCII = _ascii_table()


def _r(first: int, last: int, cls: str) -> Tuple[int, int, str]:
    return (first, last, cls)


#: (first, last, class) — sorted by ``first``; scanned with bisect.
_RANGES: List[Tuple[int, int, str]] = [
    _r(0x00A0, 0x00A0, GL),   # no-break space
    _r(0x00AD, 0x00AD, BA),   # soft hyphen
    _r(0x00B0, 0x00B0, PO),   # degree sign
    _r(0x2010, 0x2010, HY),
    _r(0x2011, 0x2011, GL),   # non-breaking hyphen
    _r(0x2012, 0x2013, BA),   # figure / en dash
    _r(0x2014, 0x2014, NS),   # em dash (中文破折号 —— 不可行首)
    _r(0x2015, 0x2015, NS),   # horizontal bar
    _r(0x2018, 0x2018, OP),
    _r(0x2019, 0x2019, CL),
    _r(0x201A, 0x201B, OP),
    _r(0x201C, 0x201C, OP),
    _r(0x201D, 0x201D, CL),
    _r(0x201E, 0x201F, OP),
    _r(0x2025, 0x2026, NS),   # ‥ … 不可行首
    _r(0x2030, 0x2030, PO),
    _r(0x2032, 0x2033, PO),
    _r(0x203C, 0x203C, NS),
    _r(0x2044, 0x2044, SY),
    _r(0x20AC, 0x20AC, PR),
    _r(0x2116, 0x2116, PR),   # №
    _r(0x3000, 0x3000, SP),   # ideographic space
    _r(0x3001, 0x3003, CL),   # 、。〃
    _r(0x3005, 0x3006, NS),   # 々〆
    _r(0x3007, 0x3007, ID),   # 〇 is an ideograph, not punctuation
    _r(0x3008, 0x3008, OP),
    _r(0x3009, 0x3009, CL),
    _r(0x300A, 0x300A, OP),
    _r(0x300B, 0x300B, CL),
    _r(0x300C, 0x300C, OP),
    _r(0x300D, 0x300D, CL),
    _r(0x300E, 0x300E, OP),
    _r(0x300F, 0x300F, CL),
    _r(0x3010, 0x3010, OP),
    _r(0x3011, 0x3011, CL),
    _r(0x3014, 0x3014, OP),
    _r(0x3015, 0x3015, CL),
    _r(0x3016, 0x3016, OP),
    _r(0x3017, 0x3017, CL),
    _r(0x3018, 0x3018, OP),
    _r(0x3019, 0x3019, CL),
    _r(0x301A, 0x301A, OP),
    _r(0x301B, 0x301B, CL),
    _r(0x301C, 0x301C, NS),   # 〜
    _r(0x301D, 0x301D, OP),
    _r(0x301E, 0x301F, CL),
    _r(0x3021, 0x3029, NS),   # 〡-〩
    _r(0x3030, 0x3030, NS),
    _r(0x3031, 0x3035, NS),
    _r(0x3038, 0x303C, NS),
    _r(0x303D, 0x303D, NS),
    _r(0x3041, 0x3096, ID),   # hiragana
    _r(0x3099, 0x309A, CM),   # combining kana marks
    _r(0x309B, 0x309C, NS),
    _r(0x30A1, 0x30FA, ID),   # katakana
    _r(0x30FB, 0x30FB, NS),   # ・
    _r(0x30FC, 0x30FE, NS),   # ーヽヾ
    _r(0x31F0, 0x31FF, ID),
    _r(0x3400, 0x4DBF, ID),   # CJK ext A
    _r(0x4E00, 0x9FFF, ID),   # CJK unified
    _r(0xA000, 0xA4CF, ID),   # Yi
    _r(0xAC00, 0xD7A3, ID),   # Hangul syllables (breakable between syllables)
    _r(0xF900, 0xFAFF, ID),   # compatibility ideographs
    _r(0xFE00, 0xFE0F, CM),   # variation selectors
    _r(0xFE30, 0xFE30, OP),
    _r(0xFE31, 0xFE34, NS),
    _r(0xFE35, 0xFE35, OP),
    _r(0xFE36, 0xFE36, CL),
    _r(0xFE37, 0xFE37, OP),
    _r(0xFE38, 0xFE38, CL),
    _r(0xFE39, 0xFE39, OP),
    _r(0xFE3A, 0xFE3A, CL),
    _r(0xFE3B, 0xFE3B, OP),
    _r(0xFE3C, 0xFE3C, CL),
    _r(0xFE3D, 0xFE3D, OP),
    _r(0xFE3E, 0xFE3E, CL),
    _r(0xFE3F, 0xFE3F, OP),
    _r(0xFE40, 0xFE40, CL),
    _r(0xFE41, 0xFE41, OP),
    _r(0xFE42, 0xFE42, CL),
    _r(0xFE43, 0xFE43, OP),
    _r(0xFE44, 0xFE44, CL),
    _r(0xFE45, 0xFE46, NS),
    _r(0xFE47, 0xFE47, OP),
    _r(0xFE48, 0xFE48, CL),
    _r(0xFE50, 0xFE52, CL),
    _r(0xFE54, 0xFE57, CL),
    _r(0xFE59, 0xFE59, OP),
    _r(0xFE5A, 0xFE5A, CL),
    _r(0xFE5B, 0xFE5B, OP),
    _r(0xFE5C, 0xFE5C, CL),
    _r(0xFE5D, 0xFE5D, OP),
    _r(0xFE5E, 0xFE5E, CL),
    _r(0xFF01, 0xFF01, EX),
    _r(0xFF02, 0xFF02, CL),
    _r(0xFF03, 0xFF03, AL),
    _r(0xFF04, 0xFF04, PR),
    _r(0xFF05, 0xFF05, PO),
    _r(0xFF06, 0xFF06, AL),
    _r(0xFF07, 0xFF07, CL),
    _r(0xFF08, 0xFF08, OP),
    _r(0xFF09, 0xFF09, CL),
    _r(0xFF0A, 0xFF0A, AL),
    _r(0xFF0B, 0xFF0B, PR),
    _r(0xFF0C, 0xFF0C, CL),
    _r(0xFF0D, 0xFF0D, HY),
    _r(0xFF0E, 0xFF0E, IS),
    _r(0xFF0F, 0xFF0F, SY),
    _r(0xFF10, 0xFF19, NU),
    _r(0xFF1A, 0xFF1B, IS),
    _r(0xFF1C, 0xFF1E, AL),
    _r(0xFF1F, 0xFF1F, EX),
    _r(0xFF20, 0xFF20, AL),
    _r(0xFF21, 0xFF3A, AL),
    _r(0xFF3B, 0xFF3B, OP),
    _r(0xFF3C, 0xFF3C, AL),
    _r(0xFF3D, 0xFF3D, CL),
    _r(0xFF3E, 0xFF40, AL),
    _r(0xFF41, 0xFF5A, AL),
    _r(0xFF5B, 0xFF5B, OP),
    _r(0xFF5C, 0xFF5C, AL),
    _r(0xFF5D, 0xFF5D, CL),
    _r(0xFF5E, 0xFF5E, NS),
    _r(0xFF5F, 0xFF5F, OP),
    _r(0xFF60, 0xFF61, CL),
    _r(0xFF62, 0xFF62, OP),
    _r(0xFF63, 0xFF64, CL),
    _r(0xFF65, 0xFF65, NS),
    _r(0xFF66, 0xFF9F, ID),   # halfwidth katakana
    _r(0xFFE0, 0xFFE0, PO),
    _r(0xFFE1, 0xFFE1, PR),
    _r(0xFFE5, 0xFFE5, PR),
    _r(0xFFE6, 0xFFE6, PR),
    _r(0x1F300, 0x1FAFF, ID),  # emoji (wide, breakable between bases)
    _r(0x20000, 0x2FA1F, ID),  # CJK ext B..F
    _r(0x30000, 0x3134F, ID),  # CJK ext G
]

_STARTS = [r[0] for r in _RANGES]

_CACHE: Dict[int, str] = {}


def _compute(cp: int) -> str:
    if cp < 0x80:
        return _ASCII[cp]
    idx = bisect.bisect_right(_STARTS, cp) - 1
    if idx >= 0:
        first, last, cls = _RANGES[idx]
        if first <= cp <= last:
            return cls
    # Conservative fallback: wide characters behave like ideographs.
    ch = chr(cp)
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return ID
    if unicodedata.combining(ch):
        return CM
    return AL


def line_break_class(ch: str) -> str:
    """Return the UAX #14 line-break class of a single character."""
    cp = ord(ch)
    cached = _CACHE.get(cp)
    if cached is None:
        cached = _compute(cp)
        _CACHE[cp] = cached
    return cached


def is_wide(ch: str) -> bool:
    """True for full-width / ideographic characters (used by metrics)."""
    return line_break_class(ch) in WIDE or unicodedata.east_asian_width(ch) in ("W", "F")


def can_break(before: str, after: str) -> bool:
    """Can a line break be inserted *between* two characters?

    ``before`` is the last character of the current line, ``after`` the first
    character of the next one.  This is the pair-table part of UAX #14,
    simplified to the classes CJK typesetting cares about.
    """
    a = line_break_class(before)
    b = line_break_class(after)

    # Hard prohibitions first: nothing may start with a non-starter, nothing
    # may end with a non-ender.
    if b in NON_STARTER or a in NON_ENDER:
        return False

    if a == SP or a == ZW or a == BA:
        return True
    if a == HY:
        return True  # hyphen stays on the first line
    if a == ID:
        return True
    if a in (AL, NU) and b == ID:
        return True
    if a in (AL, NU) and b in (AL, NU):
        return False
    return True
