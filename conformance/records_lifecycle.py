# SPDX-License-Identifier: Apache-2.0
"""Draft semantic checks for the four lifecycle records (transmission envelope, completeness report,
limited change record, decision record; all v0.1 drafts). Each check validates the record schema,
then the invariants the schema alone cannot express. All four records are reviewer evidence; none
is an approval, and missing information is unknown, never fail."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_PATH = ROOT / "vocab" / "ori-lifecycle-records-0.1.context.json"
PROFILES = {
    "ori-transmission-envelope-0.1": "TransmissionEnvelope",
    "ori-completeness-report-0.1": "CompletenessReport",
    "ori-limited-change-record-0.1": "LimitedChangeRecord",
    "ori-decision-record-0.1": "Decision",
}
_SCHEMAS = {p: ROOT / "spec" / f"{p}.schema.json" for p in PROFILES}
_RC = ROOT / "spec" / "ori-review-comment-0.2.schema.json"
_validators: dict[str, Draft202012Validator] = {}
GLOBAL_ID = re.compile(r"^[0-9A-Za-z_$]{22}$")
_CONTENT_ADDRESS = re.compile(r"^urn:ori:artifact:sha256:([0-9a-f]{64})$")
_MODEL_ANCHORS = {"element", "spatial", "view"}
ENV, CR, LC, DR = PROFILES  # profile ids in declaration order


def pinned_context() -> dict[str, Any]:
    return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))["@context"]


def _schema_errors(obj: dict[str, Any], profile: str) -> list[str]:
    if profile not in _validators:
        rc = json.loads(_RC.read_text(encoding="utf-8"))
        reg = Registry().with_resources([(rc["$id"], Resource.from_contents(rc))])
        schema = json.loads(_SCHEMAS[profile].read_text(encoding="utf-8"))
        _validators[profile] = Draft202012Validator(schema, format_checker=FormatChecker(), registry=reg)
    errs = sorted(_validators[profile].iter_errors(obj), key=lambda e: list(e.path))
    return [f"{obj.get('@id')}: schema: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]


def _of(case: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    return [o for o in case.get("objects", []) if isinstance(o, dict) and o.get("record_profile") == profile]


def _walk(node: Any, path: str = "") -> Iterator[tuple[str, str, Any]]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield path, k, v
            yield from _walk(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}/{i}")


def _dt(s: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def _common(r: dict[str, Any], profile: str) -> list[str]:
    rid = r.get("@id")
    errors = _schema_errors(r, profile)
    if r.get("@context") != pinned_context():
        errors.append(f"{rid}: @context must equal the pinned context in vocab/ori-lifecycle-records-0.1.context.json")
    for path, key, value in _walk(r):
        if key == "is_approval" and value is not False:
            errors.append(f"{rid}: {path}/is_approval must be false; the record is reviewer evidence, not approval")
    errors += _hashref_errors(r)
    errors += _model_anchor_errors(r)
    return errors


def _hashrefs(r: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    for path, key, value in _walk(r):
        if isinstance(value, dict) and "artifact_state" in value and "sha256" in value:
            yield f"{path}/{key}", value
        elif isinstance(value, list):
            for i, v in enumerate(value):
                if isinstance(v, dict) and "artifact_state" in v and "sha256" in v:
                    yield f"{path}/{key}/{i}", v


def _hashref_errors(r: dict[str, Any]) -> list[str]:
    """Unrebuilt or unknown artifacts carry unknown hashes; a hash is never fabricated."""
    rid, errors = r.get("@id"), []
    for where, h in _hashrefs(r):
        sha, state, status = h.get("sha256"), h.get("artifact_state"), h.get("hash_status")
        m = _CONTENT_ADDRESS.match(str(h.get("artifact_ref", "")))
        if state in ("unrebuilt", "unavailable", "unknown"):
            if sha != "unknown" or status != "unknown":
                errors.append(f"{rid}: {where}: {state} artifact must carry sha256 unknown and hash_status unknown (no fabricated hash)")
            if m:
                errors.append(f"{rid}: {where}: {state} artifact cannot have a content-addressed sha256 artifact_ref")
            if h.get("bytes", "unknown") != "unknown":
                errors.append(f"{rid}: {where}: {state} artifact has no bytes to count; bytes must be unknown")
        if sha == "unknown" and status != "unknown":
            errors.append(f"{rid}: {where}: hash_status {status!r} with an unknown sha256")
        if status == "verified" and state != "available":
            errors.append(f"{rid}: {where}: only available bytes can be hash-verified")
        if m and sha != "unknown" and m.group(1) != sha:
            errors.append(f"{rid}: {where}: content-addressed artifact_ref does not match sha256")
    return errors


def _model_anchor_errors(r: dict[str, Any]) -> list[str]:
    """Element, spatial and view anchors bind a known model version in the enclosing item."""
    rid, errors = r.get("@id"), []

    def check(holder: dict[str, Any], anchors_key: str, mv_keys: tuple[str, ...], where: str) -> None:
        anchors = holder.get(anchors_key) or []
        if any(isinstance(a, dict) and a.get("anchor_type") in _MODEL_ANCHORS for a in anchors):
            if not any(isinstance(holder.get(k) or r.get(k), dict) for k in mv_keys):
                errors.append(f"{rid}: {where}: model anchors need a known model_version")

    for i, it in enumerate(r.get("items", []) if isinstance(r.get("items"), list) else []):
        if isinstance(it, dict):
            check(it, "anchors", ("model_version",), f"items/{i}")
    for i, c in enumerate(r.get("condition_records", []) if isinstance(r.get("condition_records"), list) else []):
        if isinstance(c, dict):
            check(c, "anchors", ("model_version",), f"condition_records/{i}")
    te = r.get("touched_elements")
    if isinstance(te, dict):
        for gid, t in te.items():
            if isinstance(t, dict):
                if any(isinstance(a, dict) and a.get("anchor_type") in _MODEL_ANCHORS for a in t.get("before_anchors", [])) and not isinstance(t.get("before_model_version"), dict):
                    errors.append(f"{rid}: touched_elements/{gid}: before anchors need before_model_version")
                if any(isinstance(a, dict) and a.get("anchor_type") in _MODEL_ANCHORS for a in t.get("after_anchors", [])) and not isinstance(t.get("after_model_version"), dict):
                    errors.append(f"{rid}: touched_elements/{gid}: after anchors need after_model_version")
    return errors


def _all(case: dict[str, Any], profile: str) -> tuple[list[dict[str, Any]], list[str]]:
    recs = _of(case, profile)
    return recs, ([] if recs else [f"no {profile} objects in case"])


def transmission_envelope_record(case: dict[str, Any]) -> list[str]:
    recs, errors = _all(case, ENV)
    for r in recs:
        errors += _common(r, ENV)
        rid, manifest, receipt = r.get("@id"), r.get("manifest") or [], r.get("receipt") or {}
        refs = [m.get("artifact_ref") for m in manifest if isinstance(m, dict)]
        if len(refs) != len(set(refs)):
            errors.append(f"{rid}: manifest artifact_ref values must be unique")
        if receipt.get("state") == "received" and receipt.get("received_at") == "unknown":
            errors.append(f"{rid}: a received receipt needs a known received_at")
        if receipt.get("state") != "received" and receipt.get("manifest_verification") != "unknown":
            errors.append(f"{rid}: manifest_verification needs a received receipt")
        if receipt.get("manifest_verification") == "verified" and any(
                m.get("hash_status") != "verified" for m in manifest if isinstance(m, dict) and m.get("artifact_state") == "available"):
            errors.append(f"{rid}: receipt claims verified manifest but an available artifact is not hash-verified")
        for i, m in enumerate(manifest):
            if not isinstance(m, dict):
                continue
            if m.get("role") == "view_model" and "source_ifc_ref" not in m:
                errors.append(f"{rid}: manifest/{i}: a view model must name its source IFC")
            if m.get("schema_identifier_verification") == "verified" and m.get("hash_status") != "verified":
                errors.append(f"{rid}: manifest/{i}: schema identifier cannot be verified without verified bytes")
        for ch in _of(case, LC):
            if ch.get("envelope_ref") == rid and r.get("change_record_ref") != ch.get("@id"):
                errors.append(f"{rid}: change record {ch.get('@id')} names this envelope but change_record_ref does not link it")
    return errors


def _derive(items: list[dict[str, Any]], sets: list[dict[str, Any]]) -> tuple[str, str, list[str], list[str]]:
    """Three-valued aggregation from spec/completeness-report-0.1-draft.md."""
    coverage_known = all(s.get("coverage") == "complete" for s in sets)
    uncertain = (not coverage_known) or any(
        it.get("result") == "unknown" or it.get("effect") == "unknown" or it.get("basis") == "applicability_unknown" for it in items)
    if uncertain:
        overall = "indeterminate"
    elif any(it.get("result") == "fail" for it in items):
        overall = "incomplete"
    else:
        overall = "complete"
    blocking = [it["item_id"] for it in items if it.get("effect") == "blocking" and it.get("result") != "pass"]
    advisory = [it["item_id"] for it in items if it.get("effect") == "advisory" and it.get("result") != "pass"]
    blockers_unknown = (not coverage_known) or any(
        it.get("effect") == "unknown" or (it.get("effect") == "blocking" and it.get("result") == "unknown") for it in items)
    if blockers_unknown:
        bstatus = "unknown"
    elif any(it.get("effect") == "blocking" and it.get("result") == "fail" for it in items):
        bstatus = "unsatisfied"
    else:
        bstatus = "satisfied"
    return overall, bstatus, blocking, advisory


def completeness_report_record(case: dict[str, Any]) -> list[str]:
    recs, errors = _all(case, CR)
    for r in recs:
        schema = _common(r, CR)
        errors += schema
        if any(": schema: " in s for s in schema):
            continue
        rid, items, sets, acc = r["@id"], r["items"], r["requirement_sets"], r["acceptance"]
        ids = [it["item_id"] for it in items]
        if len(ids) != len(set(ids)):
            errors.append(f"{rid}: item_id values must be unique")
        set_refs = {s["requirement_set_ref"] for s in sets}
        for it in items:
            iid = it["item_id"]
            if it["requirement_set_ref"] not in set_refs:
                errors.append(f"{rid}: item {iid}: requirement_set_ref is not one of the report's requirement_sets")
            # Missing information yields unknown, never fail.
            if it["basis"] != "observed" and it["result"] != "unknown":
                errors.append(f"{rid}: item {iid}: basis {it['basis']} must give result unknown, not {it['result']}")
            if it["result"] == "fail" and not it.get("evidence_refs"):
                errors.append(f"{rid}: item {iid}: fail needs observed evidence_refs that contradict the requirement")
        overall, bstatus, blocking, advisory = _derive(items, sets)
        if r["overall"] != overall:
            errors.append(f"{rid}: overall {r['overall']!r} does not match the items ({overall!r})")
        if r["blocking_status"] != bstatus:
            errors.append(f"{rid}: blocking_status {r['blocking_status']!r} does not match the items ({bstatus!r})")
        if sorted(r["blocking_items"]) != sorted(blocking):
            errors.append(f"{rid}: blocking_items must list exactly the blocking items that are not pass {sorted(blocking)}")
        if sorted(r["advisory_items"]) != sorted(advisory):
            errors.append(f"{rid}: advisory_items must list exactly the advisory items that are not pass {sorted(advisory)}")
        accepted = acc["state"] == "accepted"
        if accepted:
            if acc["actor_ref"] == "unknown" or acc["accepted_at"] == "unknown":
                errors.append(f"{rid}: acceptance needs an identified intake actor and a known time")
            # Blocking uncertainty prevents acceptance and therefore any clock start.
            if bstatus != "satisfied":
                errors.append(f"{rid}: cannot accept while blocking_status is {bstatus}; the review clock cannot start")
            if overall == "incomplete":
                errors.append(f"{rid}: cannot accept an incomplete report")
        elif acc["transition_event_ref"] != "unknown":
            errors.append(f"{rid}: only an accepted report may name a clock transition event")
        for env in (o for o in case.get("objects", []) if isinstance(o, dict) and o.get("@id") == r["envelope_ref"]):
            if env.get("application_ref") != r["application_ref"]:
                errors.append(f"{rid}: envelope belongs to a different application")
        for sc in (o for o in case.get("objects", []) if isinstance(o, dict) and o.get("record_profile") == "ori-status-clock-0.1"
                   and o.get("id") == r.get("status_record_ref")):
            started = [e for e in sc.get("events", []) if e.get("event_type") in ("accepted_complete", "clock_started")]
            if started and not (accepted and bstatus == "satisfied"):
                errors.append(f"{rid}: status record {sc['id']} starts the clock but this report is not accepted with satisfied blockers")
            if not started and sc.get("clock", {}).get("state") in ("running", "paused", "stopped", "deemed"):
                errors.append(f"{rid}: status record {sc['id']} shows a started clock without an accepted_complete event")
    return errors


def limited_change_record(case: dict[str, Any]) -> list[str]:
    recs, errors = _all(case, LC)
    for r in recs:
        schema = _common(r, LC)
        errors += schema
        if any(": schema: " in s for s in schema):
            continue
        rid, te, cf, rs = r["@id"], r["touched_elements"], r["carry_forward"], r["reviewer_scope"]
        if r["parent_revision_ref"] == r["child_revision_ref"]:
            errors.append(f"{rid}: parent and child revisions must differ")
        if cf["basis_revision_ref"] != r["parent_revision_ref"]:
            errors.append(f"{rid}: carry_forward basis must be the parent revision")
        child_built = r["child_model"]["artifact_state"] == "available" and r["child_model"]["hash_status"] == "verified"
        parent_built = r["parent_model"]["artifact_state"] == "available" and r["parent_model"]["hash_status"] == "verified"
        if r["child_model"]["sha256"] != "unknown" and r["child_model"]["sha256"] == r["parent_model"]["sha256"]:
            errors.append(f"{rid}: child model hash equals the parent; no change to record")
        item_refs: set[str] = set()
        for key, t in te.items():
            if not GLOBAL_ID.match(key):
                errors.append(f"{rid}: touched_elements key {key!r} is not a 22-character IFC GlobalId")
            if t["ifc_global_id"] != key:
                errors.append(f"{rid}: touched_elements key {key} does not match its ifc_global_id {t['ifc_global_id']}")
            for a in t["before_anchors"] + t["after_anchors"]:
                if a.get("anchor_type") == "element" and a.get("ifc_global_id") not in (None, key):
                    errors.append(f"{rid}: touched element {key} anchors a different GlobalId")
            op = t["operation"]
            if op == "added" and t["before_anchors"]:
                errors.append(f"{rid}: {key}: an added element has no parent anchors")
            if op == "removed" and t["after_anchors"]:
                errors.append(f"{rid}: {key}: a removed element has no child anchors")
            if not child_built:
                # Unrebuilt child: nothing can bind to it, and no model version is invented.
                if t["after_anchors"] or "after_model_version" in t or t.get("after_anchor_status") == "bound":
                    errors.append(f"{rid}: {key}: child model is not built; after anchors must be empty and unbound")
                if op != "removed" and t.get("after_anchor_status") != "unknown":
                    errors.append(f"{rid}: {key}: after_anchor_status must be unknown while the child is unbuilt")
            elif "after_model_version" in t and t["after_model_version"]["sha256"] != r["child_model"]["sha256"]:
                errors.append(f"{rid}: {key}: after_model_version must be the child model")
            if "before_model_version" in t and t["before_model_version"]["sha256"] != r["parent_model"]["sha256"]:
                errors.append(f"{rid}: {key}: before_model_version must be the parent model")
            if t["change_basis"] == "compared" and rs["comparison_state"] != "compared":
                errors.append(f"{rid}: {key}: change_basis compared needs a recorded comparison")
            item_refs |= set(t.get("answers_comment_refs", []))
        if not item_refs <= set(r["answers_comment_refs"]):
            errors.append(f"{rid}: element-level answers_comment_refs must also appear at record level")
        # Declared scope stays distinct from verified scope.
        compared_ok = parent_built and child_built
        if rs["comparison_state"] == "compared" and not compared_ok:
            errors.append(f"{rid}: comparison_state compared needs verified parent and child bytes")
        if rs["verified_scope_status"] == "unknown" and rs["verified_scope"]:
            errors.append(f"{rid}: verified_scope lists elements while its status is unknown")
        if rs["verified_scope_status"] == "verified" and rs["comparison_state"] != "compared":
            errors.append(f"{rid}: verified_scope given without a comparison; it must stay unknown, not copy the declaration")
        if rs["verified_scope_status"] == "verified" and not set(te) <= set(rs["verified_scope"]):
            # Verified differences may extend past the declaration, but a declared change missing from the
            # verified scope must be shown, not dropped.
            errors.append(f"{rid}: verified_scope omits declared touched elements; show them, do not hide them")
        if cf["verification"] == "verified" and rs["comparison_state"] != "compared":
            errors.append(f"{rid}: carry_forward cannot be verified without a comparison of parent and child bytes")
        for env in (o for o in case.get("objects", []) if isinstance(o, dict) and o.get("@id") == r["envelope_ref"]):
            if env.get("purpose") != "resubmittal":
                errors.append(f"{rid}: a change record travels with a resubmittal envelope")
    return errors


def decision_record(case: dict[str, Any]) -> list[str]:
    recs, errors = _all(case, DR)
    by_id = {r.get("@id"): r for r in recs}
    for r in recs:
        schema = _common(r, DR)
        errors += schema
        if r.get("is_machine") is not False:
            errors.append(f"{r.get('@id')}: is_machine must be false; a Decision is a human act")
        if any(": schema: " in s for s in schema):
            continue
        rid, conds, crecs = r["@id"], r["conditions"], r["condition_records"]
        if r["outcome"] == "approve_with_conditions" and not conds:
            errors.append(f"{rid}: approve_with_conditions needs at least one condition")
        if r["outcome"] != "approve_with_conditions" and conds:
            errors.append(f"{rid}: only approve_with_conditions carries conditions; rationale belongs in evidence")
        if sorted(conds) != sorted(c["@id"] for c in crecs):
            errors.append(f"{rid}: conditions must reference exactly the condition_records")
        vf, vu = r["validity"]["valid_from"], r["validity"]["valid_until"]
        if vf != "unknown" and vu != "unknown" and _dt(vu) <= _dt(vf):
            errors.append(f"{rid}: valid_until must be after valid_from")
        att = r["attestation"]
        if r["validity_status"] == "verified" and (att["identity_status"] != "verified" or att["signature_status"] != "verified" or "unknown" in (vf, vu)):
            errors.append(f"{rid}: validity_status verified needs verified identity, signature and a known term")
        if r["pre_review_status"] != "unknown" and r["validity_status"] != "verified":
            errors.append(f"{rid}: pre_review_status stays unknown until validity is verified")
        if r["pre_review_link_role"] == "establishes_pre_review" and r["decision_type"] != "pre_review_disposition":
            errors.append(f"{rid}: only a pre_review_disposition establishes a pre-review")
        if rid in r["supersedes"]:
            errors.append(f"{rid}: a Decision cannot supersede itself")
        for old in r["supersedes"]:
            if old in by_id and rid in by_id[old].get("supersedes", []):
                errors.append(f"{rid}: supersedes cycle with {old}")
        for c in crecs:
            if "model_version" in c and "model_version" in r and c["model_version"]["sha256"] != r["model_version"]["sha256"]:
                errors.append(f"{rid}: condition {c['@id']} binds a different model than the Decision")
    return errors
