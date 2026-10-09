# SPDX-License-Identifier: Apache-2.0
"""Linguistic study of code-book language without storing code text.

Reads a local text file that ORI does not commit or publish (for example a
chapter the analyst can lawfully view) and writes only derived statistics:

* per section id: SHA-256 of the whitespace-normalized section text (after its
  id; repeated segments joined by a newline), word and
  sentence counts, counts of modal verbs, ambiguity markers and
  cross-references, and counts of ORI-CL vocabulary labels and defined-term
  names;
* corpus totals.

No sentences, phrases, n-grams, headings or other text from the input are
written. The only strings in the output are section ids, ORI's own marker
names (fixed lists below) and vocabulary names. ``assert_no_text`` checks the
output against the input for shared runs of 6 words (refined: runs made only of free
terms, numbers, units and function words pass; see term_merger.shared_runs).

Usage: python -m ori_cl.corpus_stats INPUT.txt --out stats.json [--label NAME]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .vocab import load

# Marker lists are ORI's own analytic categories (single words or short function-word phrases).
MODALS = {
    "shall": r"\bshall\b(?!\s+not)",
    "shall not": r"\bshall\s+not\b",
    "must": r"\bmust\b(?!\s+not)",
    "must not": r"\bmust\s+not\b",
    "may": r"\bmay\b(?!\s+not)",
    "may not": r"\bmay\s+not\b",
    "should": r"\bshould\b",
    "is/are permitted": r"\b(?:is|are)\s+permitted\b",
    "is/are required": r"\b(?:is|are)\s+required\b",
    "is/are not required": r"\b(?:is|are)\s+not\s+required\b",
}
AMBIGUITY_MARKERS = {
    "approved": r"\bapproved\b",
    "adequate": r"\badequate(?:ly)?\b",
    "sufficient": r"\bsufficient(?:ly)?\b",
    "suitable": r"\bsuitabl[ey]\b",
    "reasonable": r"\breasonabl[ey]\b",
    "acceptable": r"\bacceptable\b",
    "substantial": r"\bsubstantial(?:ly)?\b",
    "readily": r"\breadily\b",
    "properly": r"\bproper(?:ly)?\b",
    "equivalent": r"\bequivalent\b",
    "similar": r"\bsimilar\b",
    "as required": r"\bas\s+required\b",
    "where required": r"\bwhere\s+required\b",
    "where applicable": r"\bwhere\s+applicable\b",
    "as necessary": r"\bas\s+necessary\b",
    "or other": r"\bor\s+other\b",
    "and/or": r"\band/or\b",
    "building official": r"\bbuilding\s+official\b",
    "manufacturer's instructions": r"\bmanufacturer'?s\s+(?:installation\s+)?instructions\b",
}
CROSS_REFERENCES = {
    "section": r"\bSections?\s+R?\d{3}(?:\.\d+)*",
    "table": r"\bTables?\s+R?\d{3}(?:\.\d+)*",
    "figure": r"\bFigures?\s+R?\d{3}(?:\.\d+)*",
    "chapter": r"\bChapters?\s+\d+",
    "bare_section_id": r"(?<![\w.])R\d{3}(?:\.\d+)+",
    "external_standard": r"\b(?:ASTM|UL|ANSI|NFPA|ASCE|CSA|AAMA|WDMA|AWPA|ACI|TMS|NSF|DOC)\s?[A-Z]?\d+",
}
_SECTION_ID = r"R\d{3}(?:\.\d+)*"
# A section starts at an id that is not part of a cross-reference phrase.
_REF_LEAD = r"(?:Sections?|Tables?|Figures?|and|or|through|with|of|in|to|by|under|see|per|Items?|Exceptions?)"
MIN_SHINGLE = 6  # defined-term names (allowed) can reach 5 words


def _heading_positions(text: str, pattern: str | None) -> list[tuple[int, str]]:
    if pattern:
        return [(m.start(), m.group(1)) for m in re.finditer(pattern, text, re.MULTILINE)]
    out = []
    for m in re.finditer(rf"(?<![\w.])({_SECTION_ID})(?=\s+[A-Z])", text):
        before = text[max(0, m.start() - 16):m.start()]
        if re.search(rf"\b{_REF_LEAD}\s*$", before):
            continue
        out.append((m.start(), m.group(1)))
    return out


def split_sections(text: str, pattern: str | None = None) -> list[tuple[str, str]]:
    pos = _heading_positions(text, pattern)
    out: list[tuple[str, str]] = []
    for i, (start, sid) in enumerate(pos):
        end = pos[i + 1][0] if i + 1 < len(pos) else len(text)
        out.append((sid, text[start:end]))
    return out


def _norm(text: str) -> str:
    return " ".join(text.split())


def _count(patterns: dict[str, str], text: str, flags=re.IGNORECASE) -> dict[str, int]:
    return {k: len(re.findall(p, text, flags)) for k, p in patterns.items()}


def section_stats(sid: str, text: str, vocab_terms: dict[str, str], defined: list[str]) -> dict[str, Any]:
    norm = _norm(text)
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", norm)
    low = norm.lower()
    return {
        "section": sid,
        "sha256": hashlib.sha256(norm.encode("utf-8")).hexdigest(),
        "words": len(words),
        "sentences": len(re.findall(r"[.;:](?:\s|$)", norm)),
        "modals": {k: v for k, v in _count(MODALS, norm).items() if v},
        "ambiguity_markers": {k: v for k, v in _count(AMBIGUITY_MARKERS, norm).items() if v},
        "cross_references": {k: v for k, v in _count(CROSS_REFERENCES, norm, 0).items() if v},
        "vocabulary_hits": {name: n for name, label in vocab_terms.items() if (n := len(re.findall(rf"\b{re.escape(label)}s?\b", low)))},
        "defined_term_hits": {t: n for t in defined if (n := len(re.findall(rf"\b{re.escape(t.lower())}s?\b", low)))},
    }


def analyze(text: str, label: str, pattern: str | None = None) -> dict[str, Any]:
    v = load()
    vocab_terms = {f["name"]: f["label"].lower() for f in v.data["facts"]}
    defined = [d["defined_term"] for d in v.data["defined_terms"] if "," not in d["defined_term"]]
    merged: dict[str, list[str]] = {}
    for sid, body in split_sections(text, pattern):  # a table of contents or a table repeats an id
        merged.setdefault(sid, []).append(body[len(sid):])  # the section's own id is not a cross-reference
    stats = []
    for sid, bodies in merged.items():
        st = section_stats(sid, "\n".join(bodies), vocab_terms, defined)
        st["segments"] = len(bodies)
        stats.append(st)
    totals: dict[str, Counter] = {"modals": Counter(), "ambiguity_markers": Counter(), "cross_references": Counter()}
    for s in stats:
        for k in totals:
            totals[k].update(s[k])
    words = sum(s["words"] for s in stats)
    return {
        "study": "ori-cl-corpus-stats-0.1",
        "status": "DRAFT",
        "label": label,
        "input_sha256": hashlib.sha256(_norm(text).encode("utf-8")).hexdigest(),
        "legal_note": "Derived statistics only: section ids, counts and SHA-256 digests. No code text is stored. Not legal advice; flagged for legal review before publication.",
        "method": "verification/ori_cl/corpus_stats.py (spec/ori-cl-0.1-draft.md section 9)",
        "totals": {"sections": len(stats), "words": words, **{k: dict(sorted(c.items())) for k, c in totals.items()},
                   "shall_per_1000_words": round(1000 * (totals["modals"]["shall"] + totals["modals"]["shall not"]) / words, 2) if words else 0.0,
                   "ambiguity_markers_per_1000_words": round(1000 * sum(totals["ambiguity_markers"].values()) / words, 2) if words else 0.0},
        "sections": stats,
    }


def _shingles(text: str, n: int = MIN_SHINGLE) -> set[tuple[str, ...]]:
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def _output_strings(stats: Any) -> list[str]:
    strings: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            for k, val in o.items():
                strings.append(str(k))
                walk(val)
        elif isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, str):
            strings.append(o)

    walk(stats)
    return strings


def assert_no_text(stats: dict[str, Any], source_text: str, n: int = MIN_SHINGLE) -> None:
    """Raise if any output string shares a run of n (6) or more words with the source text.

    This is the STRICT safeguard, the enforced rule everywhere (project decision, 2026-09-28): every shared
    6-word run fails, whatever words it contains. The refined classification of runs
    (``term_merger.shared_runs(..., free_terms)``) is an informational report only and never a
    gate. Each output string is checked on its own, so numbers and keys never join into a phrase."""
    from .term_merger import shared_runs
    runs = shared_runs(_output_strings(stats), source_text, (), n)
    if runs:
        raise AssertionError(f"output shares {len(runs)} {n}-word runs with the source text (strict safeguard); "
                             f"first run: {runs[0]['length']} words, sha256 {runs[0]['sha256'][:12]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ori_cl.corpus_stats", description=__doc__.split("\n\n")[0])
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="unlabeled")
    ap.add_argument("--heading-pattern", default=None, help="regex with one group capturing the section id")
    ns = ap.parse_args(argv)
    text = Path(ns.input).read_text(encoding="utf-8", errors="ignore")
    stats = analyze(text, ns.label, ns.heading_pattern)
    assert_no_text(stats, text)
    Path(ns.out).write_text(json.dumps(stats, indent=1) + "\n", encoding="utf-8")
    print(f"{len(stats['sections'])} sections, {stats['totals']['words']} words -> {ns.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
