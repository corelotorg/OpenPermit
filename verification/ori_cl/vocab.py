# SPDX-License-Identifier: Apache-2.0
"""Load the ORI-CL vocabulary and check term provenance.

Every keyword, unit, subject kind, fact and IFC name used by ORI-CL must be a
term in vocab/ori-cl-vocab-0.1.json with a recorded source and license. Sources
marked not allowed (for example MasterFormat or OmniClass) may never supply a
term. Candidate sources (Uniclass) carry license evidence but supply no terms.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VOCAB_PATH = REPO_ROOT / "vocab" / "ori-cl-vocab-0.1.json"

# Names that must never appear as a vocabulary source, whatever the file says.
FORBIDDEN_SOURCE_MARKERS = ("masterformat", "uniformat", "omniclass", "e1557", "iccsafe", "icc heading")


@dataclass(frozen=True)
class Vocabulary:
    data: dict[str, Any]

    @property
    def keywords(self) -> set[str]:
        return {k["word"] for k in self.data["keywords"]}

    @property
    def units(self) -> dict[str, dict[str, Any]]:
        return {u["symbol"]: u for u in self.data["units"]}

    @property
    def subjects(self) -> dict[str, dict[str, Any]]:
        return {s["kind"]: s for s in self.data["subjects"]}

    @property
    def facts(self) -> dict[str, dict[str, Any]]:
        return {f["name"]: f for f in self.data["facts"]}

    @property
    def relations(self) -> dict[str, dict[str, Any]]:
        return {r["word"]: r for r in self.data["relations"]}

    @property
    def geometry(self) -> set[str]:
        return {g["name"] for g in self.data["reference_geometry"]}

    @property
    def ifc_names(self) -> dict[str, set[str | None]]:
        """IFC entity name -> allowed predefined types (None = no predefined type)."""
        out: dict[str, set[str | None]] = {}
        for e in self.data["ifc_terms"] + [s["ifc"] for s in self.data["subjects"]]:
            out.setdefault(e["name"], {None}).add(e.get("predefined_type"))
        return out

    def enum_values(self, fact: str) -> list[str] | None:
        f = self.facts.get(fact)
        if not f or not f.get("values"):
            return None
        return [v["value"] for v in f["values"]]

    def fact_for_relation(self, rel: str, entity: str, predef: str | None) -> str:
        return f"{rel}:{entity}" + (f":{predef}" if predef else "")


@lru_cache(maxsize=4)
def load(path: str | None = None) -> Vocabulary:
    return Vocabulary(json.loads(Path(path or VOCAB_PATH).read_text(encoding="utf-8")))


def _term_records(data: dict[str, Any]):
    for section in ("keywords", "units", "subjects", "facts", "relations", "ifc_terms", "reference_geometry", "defined_terms"):
        for rec in data.get(section, []):
            name = rec.get("word") or rec.get("symbol") or rec.get("kind") or rec.get("name") or rec.get("defined_term")
            yield section, name, rec
            for key in ("maps_to", "also"):
                for sub in rec.get(key, []) or []:
                    yield section, f"{name} -> {sub.get('name') or sub.get('code') or sub.get('defined_term') or sub.get('quantity_kind')}", sub
            if isinstance(rec.get("ifc"), dict):
                yield section, f"{name} -> {rec['ifc'].get('name')}", rec["ifc"]
            for v in rec.get("values", []) or []:
                if "maps_to_defined_term" in v:
                    yield section, f"{name}={v['value']}", v["maps_to_defined_term"]


def provenance_errors(data: dict[str, Any]) -> list[str]:
    """Every term needs a source and license; sources must be declared and allowed."""
    errors: list[str] = []
    sources = data.get("sources", {})
    for sid, s in sources.items():
        for key in ("name", "publisher", "license", "license_evidence", "use_position", "allowed"):
            if key not in s:
                errors.append(f"source {sid}: missing {key}")
        if not s.get("license_evidence"):
            errors.append(f"source {sid}: license_evidence must record at least one fetched page")
        blob = (str(s.get("name", "")) + " " + str(s.get("url", ""))).lower()
        if any(m in blob for m in FORBIDDEN_SOURCE_MARKERS):
            errors.append(f"source {sid}: restricted source ({s.get('name')}) may not supply ORI-CL terms")
        if s.get("allowed") is not True:
            errors.append(f"source {sid}: only allowed sources may be listed under sources")
    for cid, c in (data.get("candidate_sources") or {}).items():
        if cid in sources:
            errors.append(f"candidate source {cid}: cannot also be an allowed source")
        if c.get("allowed") is not False:
            errors.append(f"candidate source {cid}: must be allowed: false until adopted")
        if not c.get("license_evidence") or not c.get("license"):
            errors.append(f"candidate source {cid}: record the license and the fetched license evidence")
        if c.get("terms_imported", 0) != 0:
            errors.append(f"candidate source {cid}: supplies no terms until adopted")
        blob = (str(c.get("name", "")) + " " + str(c.get("url", ""))).lower()
        if any(m in blob for m in FORBIDDEN_SOURCE_MARKERS):
            errors.append(f"candidate source {cid}: restricted source ({c.get('name')}) cannot be a candidate")
    for dec in data.get("decisions", []) or []:
        for key in ("id", "date", "decided_by", "decision"):
            if not dec.get(key):
                errors.append(f"decision {dec.get('id')!r}: missing {key}")
    for r in data.get("restricted_sources", []):
        if r.get("allowed") is True:
            errors.append(f"restricted source {r.get('name')}: cannot be marked allowed")
        if not r.get("findings"):
            errors.append(f"restricted source {r.get('name')}: record the license findings")
    for section, name, rec in _term_records(data):
        src, lic = rec.get("source"), rec.get("license")
        if not src or not lic:
            errors.append(f"{section} term {name!r}: needs source and license")
            continue
        if src not in sources:
            errors.append(f"{section} term {name!r}: source {src!r} is not a declared, allowed source")
        if "definition" in rec or "definition_text" in rec:
            errors.append(f"{section} term {name!r}: definition text is not stored; map defined terms by citation")
        if rec.get("defined_term") and rec.get("definition_copied") is not False:
            errors.append(f"{section} term {name!r}: defined terms must record definition_copied: false")
    return errors
