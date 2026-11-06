"""Draft semantic checks for the review-comment record (issue #140; review comment v0.2). Each check validates
the record schema, then the invariants the schema alone cannot express. A review comment is reviewer evidence,
not an approval."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
_SCHEMAS = {
    "ori-review-comment-0.2": ROOT / "spec" / "ori-review-comment-0.2.schema.json",
    "ori-review-comment-event-0.2": ROOT / "spec" / "ori-review-comment-event-0.2.schema.json",
}
_validators: dict[str, Draft202012Validator] = {}

# A comment note points at what is missing; it must not restate a requirement.
_REQUIREMENT_TERMS = ("shall", "shall not", "is required to", "are required to", "must comply", "must be provided")
_REQUIREMENT_WORDING = re.compile(r"\b(" + "|".join(map(re.escape, _REQUIREMENT_TERMS)) + r")\b", re.I)
_RC, _RC_EVENT = "ori-review-comment-0.2", "ori-review-comment-event-0.2"
# One shared role list for comment authors and resolvers; spec $defs/role must match it exactly.
ROLES = ("plan_reviewer", "building_official", "fire_reviewer", "zoning_reviewer", "third_party_reviewer",
         "inspector", "applicant", "design_professional", "other")
_REVIEWER_ROLES = {"plan_reviewer", "building_official", "fire_reviewer", "zoning_reviewer", "third_party_reviewer"}
_SPECIFIC_ANCHORS = {"element", "spatial", "code_section"}


def _registry() -> Registry:
    res = [(s["$id"], Resource.from_contents(s)) for s in
           (json.loads(_SCHEMAS[p].read_text(encoding="utf-8")) for p in (_RC, _RC_EVENT))]
    return Registry().with_resources(res)


def _schema_errors(obj: dict[str, Any], profile: str) -> list[str]:
    if profile not in _validators:
        schema = json.loads(_SCHEMAS[profile].read_text(encoding="utf-8"))
        _validators[profile] = Draft202012Validator(schema, format_checker=FormatChecker(), registry=_registry())
    errs = sorted(_validators[profile].iter_errors(obj), key=lambda e: list(e.path))
    return [f"{obj.get('id')}: schema: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]


def _of(case: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    return [o for o in case.get("objects", []) if isinstance(o, dict) and o.get("record_profile") == profile]


def _comment_events(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [o for o in case.get("objects", []) if isinstance(o, dict) and o.get("specversion") is not None]


def _is_specific(anchor: dict[str, Any]) -> bool:
    kind = anchor.get("anchor_type")
    return kind in _SPECIFIC_ANCHORS or (kind == "sheet" and "region" in anchor)


def review_comment_record(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    comments = _of(case, _RC)
    # Status changes travel as CloudEvents envelopes; their data is a comment.
    for ev in _comment_events(case):
        eid = ev.get("id")
        errors += [f"{eid}: event {m}" for m in _schema_errors(ev, _RC_EVENT)]
        data = ev.get("data") if isinstance(ev.get("data"), dict) else {}
        if ev.get("subject") != data.get("id"):
            errors.append(f"{eid}: event subject must be the id of the comment it carries")
        if "orikind" in ev and ev["orikind"] != data.get("kind"):
            errors.append(f"{eid}: orikind does not match the comment kind")
        if data.get("record_profile") == _RC:
            comments.append(data)
    if not comments:
        return errors + [f"no {_RC} objects in case"]
    spec_roles = json.loads(_SCHEMAS[_RC].read_text(encoding="utf-8"))["$defs"]["role"]["enum"]
    if list(spec_roles) != list(ROLES):
        errors.append("spec $defs/role differs from the shared ROLES list in records_140.py")
    by_id = {c.get("id"): c for c in comments}
    for c in comments:
        schema = _schema_errors(c, _RC)
        errors += schema
        cid = c.get("id")
        if c.get("is_approval") is not False:
            errors.append(f"{cid}: is_approval must be false; a comment is reviewer evidence, not approval")
        if _REQUIREMENT_WORDING.search(c.get("note", "")):
            errors.append(f"{cid}: note restates a requirement; point at the rule unit instead")
        for role in (c.get("author_role"), (c.get("resolution") or {}).get("by_role")):
            if role is not None and role not in ROLES:
                errors.append(f"{cid}: role {role!r} is not in the shared role list")
        if c.get("kind") == "correction" and not any(_is_specific(a) for a in c.get("anchors", []) if isinstance(a, dict)):
            errors.append(f"{cid}: a formal correction needs a specific anchor (element, model-space point or box, sheet region, or code section)")
        if c.get("in_reply_to") == cid or cid in c.get("supersedes", []):
            errors.append(f"{cid}: a comment cannot reply to or supersede itself")
        parent = by_id.get(c.get("in_reply_to"))
        if parent and c.get("resubmittal_round", 0) < parent.get("resubmittal_round", 0):
            errors.append(f"{cid}: reply is in an earlier resubmittal round than its parent")
        for old_id in c.get("supersedes", []):
            old = by_id.get(old_id)
            if old and c.get("resubmittal_round", 0) <= old.get("resubmittal_round", 0):
                errors.append(f"{cid}: supersedes {old_id} but is not in a later resubmittal round")
        if c.get("status") == "resolved":
            # Unknown is never turned into a result: an unresolved rule unit cannot close a correction.
            if c.get("rule_unit_ref") in (None, "unknown"):
                errors.append(f"{cid}: resolving needs a real rule unit, not 'unknown'")
            res = c.get("resolution") or {}
            if res.get("by_role") not in _REVIEWER_ROLES:
                errors.append(f"{cid}: only a reviewer role can resolve a comment; the applicant answers")
            if res.get("model_version", {}).get("sha256") == (c.get("model_version") or {}).get("sha256"):
                errors.append(f"{cid}: resolution must cite the resubmitted model version, not the one commented on")
    return errors

