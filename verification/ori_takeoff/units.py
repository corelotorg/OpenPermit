# SPDX-License-Identifier: Apache-2.0
"""Feet-inch dimension strings and drawing scale notes.

* ``parse_ft_in("17'-2 1/4\"")`` gives 206.25 (inches). Typographic primes are mapped to ASCII.
* ``parse_scale_note("SCALE: 1/4\" = 1'-0\"")`` gives 48.0 (real inches per paper inch).
  ``NTS`` / ``NOT TO SCALE`` gives the string ``"not_to_scale"``; anything unrecognised gives None.
Nothing is guessed: a string that does not match the patterns below is not a dimension.
"""

from __future__ import annotations

import re
from fractions import Fraction

PT_PER_IN = 72.0

_TYPO = str.maketrans({"\u2032": "'", "\u2019": "'", "\u00b4": "'", "\u2033": '"', "\u201d": '"', "\u201c": '"',
                       "\u2013": "-", "\u2014": "-", "\u00bd": " 1/2", "\u00bc": " 1/4", "\u00be": " 3/4"})

_FRAC = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"
# 17'-2 1/4"   17'-2"   17' 2"   17'2"   17'   (feet required; inches optional)
FT_IN_RE = re.compile(rf"(?<![\d/.])(\d+)\s*'\s*(?:-?\s*({_FRAC})\s*\")?")
# 10 1/2"  (inches only)
IN_RE = re.compile(rf"(?<![\d/.'])({_FRAC})\s*\"")


def normalize(text: str) -> str:
    return text.translate(_TYPO)


def _num(s: str) -> float:
    s = s.strip()
    if " " in s:
        whole, frac = s.split(None, 1)
        return float(int(whole) + Fraction(frac))
    if "/" in s:
        return float(Fraction(s))
    return float(s)


def parse_ft_in(text: str) -> float | None:
    """Parse one feet-inch or inch-only dimension string; returns inches or None."""
    t = normalize(text).strip()
    m = FT_IN_RE.fullmatch(t)
    if m:
        return int(m.group(1)) * 12.0 + (_num(m.group(2)) if m.group(2) else 0.0)
    m = IN_RE.fullmatch(t)
    if m:
        return _num(m.group(1))
    return None


def find_ft_in(text: str) -> list[float]:
    """All feet-inch values in a string (e.g. a room size note ``16'-6" X 16'-6"``)."""
    t = normalize(text)
    return [int(m.group(1)) * 12.0 + (_num(m.group(2)) if m.group(2) else 0.0) for m in FT_IN_RE.finditer(t)]


def format_ft_in(inches: float, denom: int = 8) -> str:
    total = round(inches * denom) / denom
    ft = int(total // 12)
    rest = total - ft * 12
    whole = int(rest)
    frac = Fraction(rest - whole).limit_denominator(denom)
    inch = f"{whole}" if frac == 0 else (f"{whole} {frac}" if whole else f"{frac}")
    return f"{ft}'-{inch}\""


_SCALE_ARCH = re.compile(rf"({_FRAC})\s*\"\s*=\s*(\d+)\s*'\s*(?:-?\s*({_FRAC})\s*\")?")
_SCALE_RATIO = re.compile(r"(?<![\d.])1\s*:\s*(\d+(?:\.\d+)?)(?![\d.])")
_NTS = re.compile(r"\b(NTS|N\.T\.S\.|NOT\s+TO\s+SCALE)\b", re.IGNORECASE)


def parse_scale_note(text: str) -> float | str | None:
    """Real inches per paper inch from a scale note, ``"not_to_scale"``, or None."""
    t = normalize(text)
    if _NTS.search(t):
        return "not_to_scale"
    m = _SCALE_ARCH.search(t)
    if m:
        paper = _num(m.group(1))
        real = int(m.group(2)) * 12.0 + (_num(m.group(3)) if m.group(3) else 0.0)
        if paper > 0 and real > 0:
            return real / paper
    m = _SCALE_RATIO.search(t)
    if m and "SCALE" in t.upper():
        return float(m.group(1))
    return None
