# SPDX-License-Identifier: Apache-2.0
"""Optional extraction of dimension callouts from vector PDF text.

This is a conservative, keyword-anchored parser for text a vector PDF already
contains (for example "RISER 7 3/4\"" or "CLG HT 8'-0\""). It does no OCR and
no AI. Every value it returns has origin ``vector_extracted_unconfirmed`` and a
page anchor, and the rules treat it as ``unknown`` until the applicant or a
reviewer confirms it (declared.confirm). An AI or ML extractor plugged in
here must use origin ``ai_extracted_unverified``, which is handled the same way.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

# value patterns (inches)
_FT_IN = r"(?P<ft>\d+)\s*'\s*-?\s*(?P<fin>\d+(?:\.\d+)?)?(?:\s+(?P<fnum>\d+)/(?P<fden>\d+))?\s*\"?"
_IN = r"(?P<inch>\d+(?:\.\d+)?)(?:\s*[- ]\s*(?P<num>\d+)/(?P<den>\d+))?\s*(?:\"|IN\b)"
KEYWORDS = {
    "riser_heights_in": r"RISERS?(?:\s+HEIGHT)?(?:\s+MAX\.?)?",
    "tread_depths_in": r"TREADS?(?:\s+DEPTH)?(?:\s+MIN\.?)?",
    "min_headroom_in": r"HEADROOM(?:\s+MIN\.?)?",
    "ceiling_height_in": r"(?:CLG\.?\s*HT\.?|CEILING\s+HEIGHT)",
    "sill_height_in": r"SILL(?:\s+HEIGHT|\s+HT\.?)?",
}


_MARKS = str.maketrans({"\u2019": "'", "\u2032": "'", "\u00b4": "'", "\u201d": '"', "\u2033": '"', "\u201c": '"'})


def normalize(text: str) -> str:
    """Map typographic feet/inch marks (PDF fonts often encode ' as a right quote) to ASCII."""
    return text.translate(_MARKS)


def parse_length_in(text: str) -> float | None:
    t = normalize(text).strip().upper()
    m = re.fullmatch(_FT_IN, t)
    if m:
        v = int(m.group("ft")) * 12 + float(m.group("fin") or 0)
        if m.group("fnum"):
            v += int(m.group("fnum")) / int(m.group("fden"))
        return v
    m = re.fullmatch(_IN, t)
    if m:
        v = float(m.group("inch"))
        if m.group("num"):
            v += int(m.group("num")) / int(m.group("den"))
        return v
    return None


def extract_callouts(pdf_path: str | Path, artifact_id: str, manifest_artifact: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return keyword-anchored callouts; sheet ids come from the manifest's page labels when given."""
    reader = PdfReader(str(pdf_path))
    labels = {p["page"]: p["page_label"] for p in (manifest_artifact or {}).get("pages", [])}
    out = []
    value_re = rf"(?P<val>{_FT_IN.replace('?P<', '?P<a_')}|{_IN.replace('?P<', '?P<b_')})"
    for pno, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        for line in text.splitlines():
            u = normalize(line).upper()
            for key, kw in KEYWORDS.items():
                for m in re.finditer(rf"\b{kw}\s*[:=]?\s*{value_re}", u):
                    val = parse_length_in(m.group("val"))
                    if val is None:
                        continue
                    out.append({
                        "key": key,
                        "value_in": round(val, 6),
                        "matched_text": m.group(0).strip(),
                        "origin": "vector_extracted_unconfirmed",
                        "anchor": {"artifact_id": artifact_id, "page": pno, "sheet": labels.get(pno)},
                    })
    return out


# where each extracted key lands in a declared-values document
_TARGET = {
    "riser_heights_in": ("stairs", "stair-extracted", lambda v: [v]),
    "tread_depths_in": ("stairs", "stair-extracted", lambda v: [v]),
    "min_headroom_in": ("stairs", "stair-extracted", lambda v: v),
    "ceiling_height_in": ("spaces", "space-extracted", lambda v: v),
    "sill_height_in": ("eeros", "eero-extracted", lambda v: v),
}


def declared_from_callouts(callouts: list[dict[str, Any]], *, submission_id: str, jurisdiction: str, declared_by: str,
                           declared_at: str, plan_set: dict[str, Any]) -> dict[str, Any]:
    """Build a declared-values document whose values are all unconfirmed extractions.

    The first callout per key wins; later duplicates are ignored so a reviewer
    sees one candidate per input. Nothing here is usable for pass/fail until confirmed.
    """
    doc: dict[str, Any] = {
        "declared_values_profile": "ori-declared-values-0.1",
        "submission_id": submission_id,
        "jurisdiction": jurisdiction,
        "declared_by": declared_by,
        "declared_at": declared_at,
        "plan_set": plan_set,
        "legal_boundary": "Extracted candidates are unverified evidence. They need applicant or reviewer confirmation and are not approval.",
    }
    seen = set()
    for c in callouts:
        if c["key"] in seen or c["key"] not in _TARGET:
            continue
        seen.add(c["key"])
        group, item_id, tf = _TARGET[c["key"]]
        items = doc.setdefault(group, [])
        item = next((i for i in items if i["id"] == item_id), None)
        if item is None:
            item = {"id": item_id, "label": f"Extracted candidate ({group})"}
            items.append(item)
        item[c["key"]] = {"value": tf(c["value_in"]), "origin": c["origin"], "anchor": c["anchor"],
                          "note": f"extracted text: {c['matched_text']}"}
    return doc
