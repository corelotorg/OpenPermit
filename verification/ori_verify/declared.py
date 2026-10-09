# SPDX-License-Identifier: Apache-2.0
"""Declared-values input: run the same rule units on values an applicant declares.

This is the PDF path. A PDF plan set enters ORI as an evidence artifact (see
pdf_manifest.py). The applicant declares the values a rule needs, and each
value is tied to an anchor: the artifact id, sheet id and page number where a
reviewer can see it. Extracted values (vector text or AI) come in with
unconfirmed origins and give ``unknown`` until the applicant or a reviewer
confirms them.

Format: spec/ori-declared-values-0.1.schema.json. Example: verification/examples/.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .facts import Fact, Subject

# declared key -> (subject kind, fact name, transform)
FIELD_MAP = {
    "stairs": ("stair_flight", {
        "riser_heights_in": ("riser_heights", None),
        "tread_depths_in": ("tread_depths", None),
        "min_headroom_in": ("headroom_clearances", lambda v: [v]),
    }),
    "spaces": ("space", {
        "use": ("space_use", None),
        "ceiling_height_in": ("ceiling_height", None),
        "floor_area_ft2": ("floor_area", None),
        "sloped_ceiling": ("sloped_ceiling", None),
    }),
    "eeros": ("eero", {
        "net_clear_height_in": ("net_clear_height", None),
        "net_clear_width_in": ("net_clear_width", None),
        "net_clear_area_ft2": ("net_clear_area", None),
        "grade_floor_or_below_grade": ("grade_floor_or_below_grade", None),
        "sill_height_in": ("sill_height", None),
    }),
    "walking_surfaces": ("walking_surface", {
        "drop_height_in": ("drop_height", None),
        "guard_present": ("guard_present", None),
    }),
    "guards": ("guard", {
        "height_in": ("guard_height", None),
        "on_stair_open_side": ("on_stair_open_side", None),
    }),
}


def load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def anchor_problems(doc: dict[str, Any], manifest: dict[str, Any] | None) -> list[str]:
    """Check every anchor names an artifact in the manifest and a page that exists."""
    if manifest is None:
        return []
    pages = {a["artifact_id"]: a["page_count"] for a in manifest.get("artifacts", [])}
    problems = []
    for group in FIELD_MAP:
        for item in doc.get(group, []):
            for key, entry in item.items():
                if not isinstance(entry, dict) or "anchor" not in entry:
                    continue
                a = entry["anchor"]
                aid, page = a.get("artifact_id"), a.get("page")
                if aid not in pages:
                    problems.append(f"{group}/{item.get('id')}/{key}: artifact {aid} is not in the plan-set manifest")
                elif not isinstance(page, int) or page < 1 or page > pages[aid]:
                    problems.append(f"{group}/{item.get('id')}/{key}: page {page} does not exist in {aid} ({pages[aid]} pages)")
    return problems


def subjects_from_declared(doc: dict[str, Any], manifest: dict[str, Any] | None = None) -> list[Subject]:
    bad = set(anchor_problems(doc, manifest))
    subjects = []
    for group, (kind, fields) in FIELD_MAP.items():
        for item in doc.get(group, []):
            sid = f"declared:{doc.get('submission_id', 'submission')}:{group}:{item['id']}"
            s = Subject(kind=kind, subject_id=sid, label=item.get("label", item["id"]))
            first_anchor = None
            for key, (fact, transform) in fields.items():
                entry = item.get(key)
                if entry is None:
                    continue
                anchor = dict(entry["anchor"], type="pdf_page")
                prefix = f"{group}/{item.get('id')}/{key}:"
                if any(p.startswith(prefix) for p in bad):
                    s.notes.append(f"{key}: anchor does not resolve in the manifest; value not used.")
                    continue
                value = entry["value"]
                if transform and value is not None:
                    value = transform(value)
                s.facts[fact] = Fact(value, entry.get("origin", "applicant_declared"), anchor, entry.get("note"))
                first_anchor = first_anchor or anchor
            s.anchor = first_anchor
            subjects.append(s)
    return subjects


def confirm(doc: dict[str, Any], group: str, item_id: str, key: str, by: str, confirmed_value=None) -> dict[str, Any]:
    """Return a copy of doc with one extracted value confirmed by the applicant or a reviewer."""
    if by not in ("applicant", "reviewer"):
        raise ValueError("by must be 'applicant' or 'reviewer'")
    out = copy.deepcopy(doc)
    for item in out.get(group, []):
        if item["id"] == item_id:
            entry = item[key]
            entry["origin"] = f"{by}_confirmed"
            if confirmed_value is not None:
                entry["value"] = confirmed_value
            return out
    raise KeyError(f"{group}/{item_id}/{key}")


def artifact_for(doc: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    """The declared-values document is itself an evidence artifact (hash of its canonical JSON)."""
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "artifact_id": f"urn:ori:artifact:sha256:{digest}",
        "media_type": "application/json",
        "profile": "ori-declared-values-0.1",
        "filename": Path(path).name if path else None,
        "sha256": digest,
        "hash_basis": "sha256 of canonical JSON (sorted keys, no whitespace)",
        "plan_set": doc.get("plan_set"),
    }
