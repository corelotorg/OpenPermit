# SPDX-License-Identifier: Apache-2.0
"""Draft semantic checks for the four lifecycle records (transmission envelope, completeness report,
limited change record, decision record; all v0.1 drafts). Each check validates the record schema,
then the invariants the schema alone cannot express. All four records are reviewer evidence; none
is an approval, and missing information is unknown, never fail.

ChatGPT independent-review regressions (2026-11-05): F1–F10 plus interop (spatial @list,
conditional pre_reviewed_design_ref)."""
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
# F9: canonical IFC compressed GlobalId.
GLOBAL_ID = re.compile(r"^[0-3][0-9A-Za-z_$]{21}$")
_CONTENT_ADDRESS = re.compile(r"^urn:ori:artifact:sha256:([0-9a-f]{64})$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MODEL_ANCHORS = {"element", "spatial", "view"}
ENV, CR, LC, DR = PROFILES  # profile ids in declaration order
_MAX_ERRORS = 50


def pinned_context() -> dict[str, Any]:
    return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))["@context"]


def _bounded(errors: list[str]) -> list[str]:
    if len(errors) <= _MAX_ERRORS:
        return errors
    return errors[:_MAX_ERRORS] + [f"... truncated {len(errors) - _MAX_ERRORS} further error(s)"]


def _schema_errors(obj: Any, profile: str) -> list[str]:
    if not isinstance(obj, dict):
        return [f"<non-object>: schema: <root>: record must be an object, got {type(obj).__name__}"]
    if profile not in _validators:
        rc = json.loads(_RC.read_text(encoding="utf-8"))
        reg = Registry().with_resources([(rc["$id"], Resource.from_contents(rc))])
        schema = json.loads(_SCHEMAS[profile].read_text(encoding="utf-8"))
        _validators[profile] = Draft202012Validator(schema, format_checker=FormatChecker(), registry=reg)
    errs = sorted(_validators[profile].iter_errors(obj), key=lambda e: list(e.path))
    rid = obj.get("@id", "<missing-id>")
    return [f"{rid}: schema: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]


def _of(case: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    objs = case.get("objects", [])
    if not isinstance(objs, list):
        return []
    return [o for o in objs if isinstance(o, dict) and o.get("record_profile") == profile]


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
    except (ValueError, TypeError):
        return None


def _safe(fn, *args, label: str = "") -> list[str]:
    """F8: never let shape-dependent traversal raise; return a bounded error instead."""
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 — conformance must not crash on malformed fixtures
        return [f"{label or 'check'}: malformed input: {type(exc).__name__}: {exc}"]


def _common(r: dict[str, Any], profile: str) -> list[str]:
    # F8: schema errors first; skip shape-dependent walks when schema already failed hard.
    errors = _schema_errors(r, profile)
    if errors:
        return _bounded(errors)
    rid = r.get("@id")
    if r.get("@context") != pinned_context():
        errors.append(f"{rid}: @context must equal the pinned context in vocab/ori-lifecycle-records-0.1.context.json")
    for path, key, value in _walk(r):
        if key == "is_approval" and value is not False:
            errors.append(f"{rid}: {path}/is_approval must be false; the record is reviewer evidence, not approval")
    errors += _hashref_errors(r)
    errors += _digest_ref_errors(r)
    errors += _model_anchor_errors(r)
    return _bounded(errors)


def _hashrefs(r: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    for path, key, value in _walk(r):
        if isinstance(value, dict) and "artifact_state" in value and "sha256" in value:
            yield f"{path}/{key}" if key != "sha256" else path, value
        elif isinstance(value, list):
            for i, v in enumerate(value):
                if isinstance(v, dict) and "artifact_state" in v and "sha256" in v:
                    yield f"{path}/{key}/{i}", v


def _hashref_errors(r: dict[str, Any]) -> list[str]:
    """Unrebuilt or unknown artifacts carry unknown hashes; a hash is never fabricated.
    F5: available-with-unknown-hash must not keep a content-addressed ID."""
    rid, errors = r.get("@id"), []
    for where, h in _hashrefs(r):
        if not isinstance(h, dict):
            continue
        sha, state, status = h.get("sha256"), h.get("artifact_state"), h.get("hash_status")
        aref = h.get("artifact_ref")
        m = _CONTENT_ADDRESS.match(str(aref or ""))
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
        # F5: available + unknown hash must not keep content-addressed ID.
        if state == "available" and sha == "unknown" and m:
            errors.append(f"{rid}: {where}: available-with-unknown-hash must not keep a content-addressed artifact_ref")
        if m and sha != "unknown" and m.group(1) != sha:
            errors.append(f"{rid}: {where}: content-addressed artifact_ref does not match sha256")
    return errors


def _digest_ref_errors(r: dict[str, Any]) -> list[str]:
    """F5: digest/ID consistency on every digest-bearing reference, not just state-bearing HashRefs."""
    rid, errors = r.get("@id"), []
    for path, key, value in _walk(r):
        if key in ("document_sha256", "sha256") and isinstance(value, str) and value != "unknown":
            if not _SHA256.match(value):
                errors.append(f"{rid}: {path}/{key}: digest must be lowercase 64-hex or unknown")
        if key == "artifact_id" and isinstance(value, str):
            m = _CONTENT_ADDRESS.match(value)
            # sibling sha256 on the same object (modelVersion)
            parent_path = path.rsplit("/", 1)[0] if "/" in path else ""
            # walk doesn't give parent object; re-check via containing dict when possible
        if isinstance(value, dict) and "artifact_id" in value and "sha256" in value:
            aid, sha = value.get("artifact_id"), value.get("sha256")
            m = _CONTENT_ADDRESS.match(str(aid or ""))
            if m and sha == "unknown":
                errors.append(f"{rid}: {path}/{key if key else ''}: content-addressed artifact_id with unknown sha256".rstrip(":"))
            if m and sha != "unknown" and m.group(1) != sha:
                errors.append(f"{rid}: {path}: content-addressed artifact_id does not match sha256")
    return errors


def _model_anchor_errors(r: dict[str, Any]) -> list[str]:
    """Element, spatial and view anchors bind a known model version in the enclosing item."""
    rid, errors = r.get("@id"), []

    def check(holder: dict[str, Any], anchors_key: str, mv_keys: tuple[str, ...], where: str) -> None:
        anchors = holder.get(anchors_key) or []
        if not isinstance(anchors, list):
            errors.append(f"{rid}: {where}: {anchors_key} must be an array")
            return
        if any(isinstance(a, dict) and a.get("anchor_type") in _MODEL_ANCHORS for a in anchors):
            if not any(isinstance(holder.get(k) or r.get(k), dict) for k in mv_keys):
                errors.append(f"{rid}: {where}: model anchors need a known model_version")
        for i, a in enumerate(anchors):
            if not isinstance(a, dict):
                errors.append(f"{rid}: {where}/{anchors_key}/{i}: anchor must be an object")
                continue
            gid = a.get("ifc_global_id")
            if gid is not None and not GLOBAL_ID.match(str(gid)):
                errors.append(f"{rid}: {where}/{anchors_key}/{i}: ifc_global_id is not a canonical IFC GlobalId")

    items = r.get("items")
    if isinstance(items, list):
        for i, it in enumerate(items):
            if isinstance(it, dict):
                check(it, "anchors", ("model_version",), f"items/{i}")
    crecs = r.get("condition_records")
    if isinstance(crecs, list):
        for i, c in enumerate(crecs):
            if isinstance(c, dict):
                check(c, "anchors", ("model_version",), f"condition_records/{i}")
    te = r.get("touched_elements")
    if isinstance(te, dict):
        for gid, t in te.items():
            if isinstance(t, dict):
                if any(isinstance(a, dict) and a.get("anchor_type") in _MODEL_ANCHORS for a in (t.get("before_anchors") or []) if isinstance(t.get("before_anchors"), list)) and not isinstance(t.get("before_model_version"), dict):
                    errors.append(f"{rid}: touched_elements/{gid}: before anchors need before_model_version")
                if any(isinstance(a, dict) and a.get("anchor_type") in _MODEL_ANCHORS for a in (t.get("after_anchors") or []) if isinstance(t.get("after_anchors"), list)) and not isinstance(t.get("after_model_version"), dict):
                    errors.append(f"{rid}: touched_elements/{gid}: after anchors need after_model_version")
    return errors


def _typed_id_index(case: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """F4: typed ID index; duplicate IDs rejected."""
    index: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    objs = case.get("objects", [])
    if not isinstance(objs, list):
        return index, ["case objects must be an array"]
    for i, o in enumerate(objs):
        if not isinstance(o, dict):
            errors.append(f"objects/{i}: must be an object")
            continue
        oid = o.get("@id") or o.get("id")
        if not oid:
            continue
        if oid in index:
            errors.append(f"duplicate ID {oid!r}: appears more than once in the case")
        else:
            index[str(oid)] = o
    return index, errors


def _all(case: dict[str, Any], profile: str) -> tuple[list[dict[str, Any]], list[str]]:
    idx_errors: list[str] = []
    _, idx_errors = _typed_id_index(case)
    recs = _of(case, profile)
    base = ([] if recs else [f"no {profile} objects in case"]) + idx_errors
    return recs, base


def transmission_envelope_record(case: dict[str, Any]) -> list[str]:
    return _bounded(_safe(_transmission_envelope_record, case, label="transmission-envelope-record"))


def _transmission_envelope_record(case: dict[str, Any]) -> list[str]:
    recs, errors = _all(case, ENV)
    index, _ = _typed_id_index(case)
    for r in recs:
        errors += _common(r, ENV)
        if any(": schema: " in s for s in errors if r.get("@id", "") in s):
            continue
        rid = r.get("@id")
        manifest = r.get("manifest") if isinstance(r.get("manifest"), list) else []
        receipt = r.get("receipt") if isinstance(r.get("receipt"), dict) else {}
        refs = [m.get("artifact_ref") for m in manifest if isinstance(m, dict)]
        if len(refs) != len(set(refs)):
            errors.append(f"{rid}: manifest artifact_ref values must be unique")
        if receipt.get("state") == "received" and receipt.get("received_at") == "unknown":
            errors.append(f"{rid}: a received receipt needs a known received_at")
        if receipt.get("state") != "received" and receipt.get("manifest_verification") != "unknown":
            errors.append(f"{rid}: manifest_verification needs a received receipt")
        if receipt.get("manifest_verification") == "verified" and any(
                isinstance(m, dict) and m.get("artifact_state") == "available" and m.get("hash_status") != "verified"
                for m in manifest):
            errors.append(f"{rid}: receipt claims verified manifest but an available artifact is not hash-verified")
        # F1: receipt_ref omit-when-unknown
        if "receipt_ref" in receipt and receipt.get("receipt_ref_status") == "unknown":
            errors.append(f"{rid}: omit receipt_ref when receipt_ref_status is unknown")
        if receipt.get("receipt_ref_status") == "known" and "receipt_ref" not in receipt:
            errors.append(f"{rid}: receipt_ref_status known requires receipt_ref")
        for i, m in enumerate(manifest):
            if not isinstance(m, dict):
                errors.append(f"{rid}: manifest/{i}: invalid manifest entry")
                continue
            if m.get("role") == "view_model" and "source_ifc_ref" not in m:
                errors.append(f"{rid}: manifest/{i}: a view model must name its source IFC")
            if m.get("schema_identifier_verification") == "verified" and m.get("hash_status") != "verified":
                errors.append(f"{rid}: manifest/{i}: schema identifier cannot be verified without verified bytes")
        # F10: NAICS verified needs edition-specific verification receipt
        for party_key in ("sender", "receiver"):
            party = r.get(party_key) if isinstance(r.get(party_key), dict) else {}
            for j, c in enumerate(party.get("classifications") or []):
                if not isinstance(c, dict):
                    continue
                if c.get("status") == "verified" and not c.get("verification_receipt_ref"):
                    errors.append(f"{rid}: {party_key}/classifications/{j}: NAICS status verified requires verification_receipt_ref")
        for ch in _of(case, LC):
            if ch.get("envelope_ref") == rid and r.get("change_record_ref") != ch.get("@id"):
                errors.append(f"{rid}: change record {ch.get('@id')} names this envelope but change_record_ref does not link it")
        # F4: application binding with linked change
        for ch in _of(case, LC):
            if ch.get("envelope_ref") == rid and ch.get("application_ref") != r.get("application_ref"):
                errors.append(f"{rid}: linked change record application_ref does not match envelope")
        _ = index  # available for unresolved-ref checks
    return errors


def _derive(items: list[dict[str, Any]], sets: list[dict[str, Any]]) -> tuple[str, str, list[str], list[str]]:
    """Three-valued aggregation from spec/completeness-report-0.1-draft.md."""
    coverage_known = all(isinstance(s, dict) and s.get("coverage") == "complete" for s in sets)
    uncertain = (not coverage_known) or any(
        isinstance(it, dict) and (it.get("result") == "unknown" or it.get("effect") == "unknown" or it.get("basis") == "applicability_unknown") for it in items)
    if uncertain:
        overall = "indeterminate"
    elif any(isinstance(it, dict) and it.get("result") == "fail" for it in items):
        overall = "incomplete"
    else:
        overall = "complete"
    blocking = [it["item_id"] for it in items if isinstance(it, dict) and it.get("effect") == "blocking" and it.get("result") != "pass"]
    advisory = [it["item_id"] for it in items if isinstance(it, dict) and it.get("effect") == "advisory" and it.get("result") != "pass"]
    blockers_unknown = (not coverage_known) or any(
        isinstance(it, dict) and (it.get("effect") == "unknown" or (it.get("effect") == "blocking" and it.get("result") == "unknown")) for it in items)
    if blockers_unknown:
        bstatus = "unknown"
    elif any(isinstance(it, dict) and it.get("effect") == "blocking" and it.get("result") == "fail" for it in items):
        bstatus = "unsatisfied"
    else:
        bstatus = "satisfied"
    return overall, bstatus, blocking, advisory


def completeness_report_record(case: dict[str, Any]) -> list[str]:
    return _bounded(_safe(_completeness_report_record, case, label="completeness-report-record"))


def _completeness_report_record(case: dict[str, Any]) -> list[str]:
    recs, errors = _all(case, CR)
    index, _ = _typed_id_index(case)
    for r in recs:
        schema = _common(r, CR)
        errors += schema
        if any(": schema: " in s for s in schema):
            continue
        rid = r["@id"]
        items = r["items"] if isinstance(r.get("items"), list) else []
        sets = r["requirement_sets"] if isinstance(r.get("requirement_sets"), list) else []
        acc = r["acceptance"] if isinstance(r.get("acceptance"), dict) else {}
        ids = [it["item_id"] for it in items if isinstance(it, dict) and "item_id" in it]
        if len(ids) != len(set(ids)):
            errors.append(f"{rid}: item_id values must be unique")
        set_refs = {s["requirement_set_ref"] for s in sets if isinstance(s, dict) and "requirement_set_ref" in s}
        for s in sets:
            if not isinstance(s, dict):
                continue
            # F1: omit artifact_ref when unknown
            status = s.get("artifact_ref_status")
            if status == "unknown" and "artifact_ref" in s:
                errors.append(f"{rid}: omit requirement_sets artifact_ref when artifact_ref_status is unknown")
            if status == "known" and "artifact_ref" not in s:
                errors.append(f"{rid}: artifact_ref_status known requires artifact_ref")
            # F4: pinned required item ids vs coverage complete
            required = s.get("required_item_ids") or []
            if s.get("coverage") == "complete" and isinstance(required, list):
                missing = [i for i in required if i not in ids]
                if missing:
                    errors.append(f"{rid}: coverage complete but required_item_ids omitted from items: {missing}")
        for it in items:
            if not isinstance(it, dict):
                continue
            iid = it.get("item_id")
            if it.get("requirement_set_ref") not in set_refs:
                errors.append(f"{rid}: item {iid}: requirement_set_ref is not one of the report's requirement_sets")
            if it.get("basis") != "observed" and it.get("result") != "unknown":
                errors.append(f"{rid}: item {iid}: basis {it.get('basis')} must give result unknown, not {it.get('result')}")
            if it.get("result") == "fail" and not it.get("evidence_refs"):
                errors.append(f"{rid}: item {iid}: fail needs observed evidence_refs that contradict the requirement")
        overall, bstatus, blocking, advisory = _derive(items, sets)
        if r.get("overall") != overall:
            errors.append(f"{rid}: overall {r.get('overall')!r} does not match the items ({overall!r})")
        if r.get("blocking_status") != bstatus:
            errors.append(f"{rid}: blocking_status {r.get('blocking_status')!r} does not match the items ({bstatus!r})")
        if sorted(r.get("blocking_items") or []) != sorted(blocking):
            errors.append(f"{rid}: blocking_items must list exactly the blocking items that are not pass {sorted(blocking)}")
        if sorted(r.get("advisory_items") or []) != sorted(advisory):
            errors.append(f"{rid}: advisory_items must list exactly the advisory items that are not pass {sorted(advisory)}")
        # F6: acceptance derives from resolved blocking coverage + explicit intake act, not overall aggregate.
        accepted = acc.get("state") == "accepted"
        if accepted:
            if acc.get("actor_ref") == "unknown" or acc.get("accepted_at") == "unknown":
                errors.append(f"{rid}: acceptance needs an identified intake actor and a known time")
            if bstatus != "satisfied":
                errors.append(f"{rid}: cannot accept while blocking_status is {bstatus}; the review clock cannot start")
            # overall aggregate must NOT gate acceptance (advisory unknown/fail may leave overall incomplete/indeterminate).
        elif acc.get("transition_event_ref") != "unknown":
            errors.append(f"{rid}: only an accepted report may name a clock transition event")
        env = index.get(str(r.get("envelope_ref")))
        # F4: unresolved references resolve to unknown — skip binding checks when the target is absent.
        if isinstance(env, dict):
            if env.get("application_ref") != r.get("application_ref"):
                errors.append(f"{rid}: envelope belongs to a different application")
        for sc in (o for o in case.get("objects", []) if isinstance(o, dict) and o.get("record_profile") == "ori-status-clock-0.1"
                   and o.get("id") == r.get("status_record_ref")):
            events = sc.get("events") if isinstance(sc.get("events"), list) else []
            started = [e for e in events if isinstance(e, dict) and e.get("event_type") in ("accepted_complete", "clock_started")]
            if started and not (accepted and bstatus == "satisfied"):
                errors.append(f"{rid}: status record {sc.get('id')} starts the clock but this report is not accepted with satisfied blockers")
            if not started and isinstance(sc.get("clock"), dict) and sc["clock"].get("state") in ("running", "paused", "stopped", "deemed"):
                errors.append(f"{rid}: status record {sc.get('id')} shows a started clock without an accepted_complete event")
            # F4: clock must not start before acceptance or with unrelated transition refs
            if accepted and acc.get("transition_event_ref") not in (None, "unknown"):
                tre = acc["transition_event_ref"]
                matching = [e for e in events if isinstance(e, dict) and (
                    e.get("@id") == tre or f"{sc.get('id')}:event:{e.get('seq')}" == tre or
                    f"{sc.get('id')}:event:{e.get('seq')}" == tre or
                    tre.endswith(f":event:{e.get('seq')}")
                )]
                # Also allow exact fixture form urn:ori:status:...:event:N
                if not matching and not any(tre.endswith(f":event:{e.get('seq')}") for e in events if isinstance(e, dict)):
                    # if status record present, transition must refer to an accepted_complete on it
                    acc_events = [e for e in events if isinstance(e, dict) and e.get("event_type") == "accepted_complete"]
                    if acc_events and not any(tre.endswith(f":event:{e.get('seq')}") for e in acc_events):
                        errors.append(f"{rid}: transition_event_ref does not match an accepted_complete event on the status record")
                acc_at = _dt(acc.get("accepted_at"))
                for e in started:
                    et = _dt(e.get("at"))
                    if acc_at and et and et < acc_at:
                        errors.append(f"{rid}: clock must not start before acceptance")
    return errors


def limited_change_record(case: dict[str, Any]) -> list[str]:
    return _bounded(_safe(_limited_change_record, case, label="limited-change-record"))


def _limited_change_record(case: dict[str, Any]) -> list[str]:
    recs, errors = _all(case, LC)
    index, _ = _typed_id_index(case)
    for r in recs:
        schema = _common(r, LC)
        errors += schema
        if any(": schema: " in s for s in schema):
            continue
        rid = r["@id"]
        te = r["touched_elements"] if isinstance(r.get("touched_elements"), dict) else {}
        cf = r["carry_forward"] if isinstance(r.get("carry_forward"), dict) else {}
        rs = r["reviewer_scope"] if isinstance(r.get("reviewer_scope"), dict) else {}
        if r.get("parent_revision_ref") == r.get("child_revision_ref"):
            errors.append(f"{rid}: parent and child revisions must differ")
        if cf.get("basis_revision_ref") != r.get("parent_revision_ref"):
            errors.append(f"{rid}: carry_forward basis must be the parent revision")
        child_model = r.get("child_model") if isinstance(r.get("child_model"), dict) else {}
        parent_model = r.get("parent_model") if isinstance(r.get("parent_model"), dict) else {}
        child_built = child_model.get("artifact_state") == "available" and child_model.get("hash_status") == "verified"
        parent_built = parent_model.get("artifact_state") == "available" and parent_model.get("hash_status") == "verified"
        if child_model.get("sha256") != "unknown" and child_model.get("sha256") == parent_model.get("sha256"):
            errors.append(f"{rid}: child model hash equals the parent; no change to record")
        item_refs: set[str] = set()
        for key, t in te.items():
            if not isinstance(t, dict):
                errors.append(f"{rid}: touched_elements/{key}: must be an object")
                continue
            if not GLOBAL_ID.match(key):
                errors.append(f"{rid}: touched_elements key {key!r} is not a canonical IFC GlobalId")
            if t.get("ifc_global_id") != key:
                errors.append(f"{rid}: touched_elements key {key} does not match its ifc_global_id {t.get('ifc_global_id')}")
            before = t.get("before_anchors") if isinstance(t.get("before_anchors"), list) else []
            after = t.get("after_anchors") if isinstance(t.get("after_anchors"), list) else []
            for a in before + after:
                if isinstance(a, dict) and a.get("anchor_type") == "element" and a.get("ifc_global_id") not in (None, key):
                    errors.append(f"{rid}: touched element {key} anchors a different GlobalId")
            op = t.get("operation")
            if op == "added" and before:
                errors.append(f"{rid}: {key}: an added element has no parent anchors")
            if op == "removed" and after:
                errors.append(f"{rid}: {key}: a removed element has no child anchors")
            if not child_built:
                if after or "after_model_version" in t or t.get("after_anchor_status") == "bound":
                    errors.append(f"{rid}: {key}: child model is not built; after anchors must be empty and unbound")
                if op != "removed" and t.get("after_anchor_status") != "unknown":
                    errors.append(f"{rid}: {key}: after_anchor_status must be unknown while the child is unbuilt")
            elif "after_model_version" in t and isinstance(t.get("after_model_version"), dict) and t["after_model_version"].get("sha256") != child_model.get("sha256"):
                errors.append(f"{rid}: {key}: after_model_version must be the child model")
            if "before_model_version" in t and isinstance(t.get("before_model_version"), dict) and t["before_model_version"].get("sha256") != parent_model.get("sha256"):
                errors.append(f"{rid}: {key}: before_model_version must be the parent model")
            if t.get("change_basis") == "compared" and rs.get("comparison_state") != "compared":
                errors.append(f"{rid}: {key}: change_basis compared needs a recorded comparison")
            item_refs |= set(t.get("answers_comment_refs") or [])
        if not item_refs <= set(r.get("answers_comment_refs") or []):
            errors.append(f"{rid}: element-level answers_comment_refs must also appear at record level")
        compared_ok = parent_built and child_built
        if rs.get("comparison_state") == "compared" and not compared_ok:
            errors.append(f"{rid}: comparison_state compared needs verified parent and child bytes")
        if rs.get("verified_scope_status") == "unknown" and rs.get("verified_scope"):
            errors.append(f"{rid}: verified_scope lists elements while its status is unknown")
        if rs.get("verified_scope_status") == "verified" and rs.get("comparison_state") != "compared":
            errors.append(f"{rid}: verified_scope given without a comparison; it must stay unknown, not copy the declaration")
        diffs = set(rs.get("verified_differences") or [])
        deps = set(rs.get("dependency_scope") or [])
        vscope = set(rs.get("verified_scope") or [])
        if rs.get("verified_scope_status") == "verified":
            if not set(te) <= vscope:
                errors.append(f"{rid}: verified_scope omits declared touched elements; show them, do not hide them")
            if diffs | deps != vscope and vscope:
                # allow verified_scope to be the union
                if not diffs | deps <= vscope or not vscope <= diffs | deps | set(te):
                    if vscope != diffs | deps:
                        errors.append(f"{rid}: verified_scope must equal verified_differences ∪ dependency_scope")
            if diffs & deps:
                errors.append(f"{rid}: a GlobalId cannot be both a verified difference and dependency-only")
        # F2: verified carry-forward requires verified complete comparison and no difference outside touched
        if cf.get("verification") == "verified":
            if rs.get("comparison_state") != "compared":
                errors.append(f"{rid}: carry_forward cannot be verified without a comparison of parent and child bytes")
            if rs.get("verified_scope_status") != "verified":
                errors.append(f"{rid}: carry_forward cannot be verified while verified_scope_status is unknown")
            if rs.get("verified_scope_status") == "unknown" and not rs.get("verified_scope"):
                errors.append(f"{rid}: verified_scope_status unknown with empty scope must not allow verified carry-forward")
            if not diffs <= set(te):
                errors.append(f"{rid}: carry_forward cannot be verified: difference outside touched set {sorted(diffs - set(te))}")
        env = index.get(str(r.get("envelope_ref"))) if r.get("envelope_ref") else None
        # F4: unresolved envelope_ref → unknown; only enforce bindings when the target is in the case.
        if isinstance(env, dict):
            if env.get("purpose") != "resubmittal":
                errors.append(f"{rid}: a change record travels with a resubmittal envelope")
            if env.get("application_ref") != r.get("application_ref"):
                errors.append(f"{rid}: envelope/application binding mismatch")
    return errors


def decision_record(case: dict[str, Any]) -> list[str]:
    return _bounded(_safe(_decision_record, case, label="decision-record"))


def _decision_record(case: dict[str, Any]) -> list[str]:
    recs, errors = _all(case, DR)
    by_id = {r.get("@id"): r for r in recs if r.get("@id")}
    # F7: also index all decision-shaped objects in the case for multi-node cycles
    all_decisions = {o.get("@id"): o for o in case.get("objects", [])
                     if isinstance(o, dict) and (o.get("record_profile") == DR or o.get("@type") == "Decision") and o.get("@id")}
    for r in recs:
        schema = _common(r, DR)
        errors += schema
        if r.get("is_machine") is not False:
            errors.append(f"{r.get('@id')}: is_machine must be false; a Decision is a human act")
        if any(": schema: " in s for s in schema):
            continue
        rid = r["@id"]
        conds = r.get("conditions") if isinstance(r.get("conditions"), list) else []
        crecs = r.get("condition_records") if isinstance(r.get("condition_records"), list) else []
        if r.get("outcome") == "approve_with_conditions" and not conds:
            errors.append(f"{rid}: approve_with_conditions needs at least one condition")
        if r.get("outcome") != "approve_with_conditions" and conds:
            errors.append(f"{rid}: only approve_with_conditions carries conditions; rationale belongs in evidence")
        if sorted(conds) != sorted(c.get("@id") for c in crecs if isinstance(c, dict)):
            errors.append(f"{rid}: conditions must reference exactly the condition_records")
        vf = r.get("validity", {}).get("valid_from") if isinstance(r.get("validity"), dict) else None
        vu = r.get("validity", {}).get("valid_until") if isinstance(r.get("validity"), dict) else None
        if vf != "unknown" and vu != "unknown" and _dt(vu) and _dt(vf) and _dt(vu) <= _dt(vf):
            errors.append(f"{rid}: valid_until must be after valid_from")
        att = r.get("attestation") if isinstance(r.get("attestation"), dict) else {}
        # F3: verified validity rejects unknown signer_ref / signed_artifact_ref / signature_ref
        if r.get("validity_status") == "verified":
            if att.get("identity_status") != "verified" or att.get("signature_status") != "verified" or "unknown" in (vf, vu):
                errors.append(f"{rid}: validity_status verified needs verified identity, signature and a known term")
            for field in ("signer_ref", "signed_artifact_ref", "signature_ref"):
                if att.get(field) in (None, "unknown"):
                    errors.append(f"{rid}: validity_status verified rejects unknown {field}")
        if r.get("pre_review_status") != "unknown" and r.get("validity_status") != "verified":
            errors.append(f"{rid}: pre_review_status stays unknown until validity is verified")
        link = r.get("pre_review_link_role")
        # Interop: pre_reviewed_design_ref required only when link role is active
        if link in ("reuse_evidence", "establishes_pre_review") and not r.get("pre_reviewed_design_ref"):
            errors.append(f"{rid}: pre_review_link_role {link} requires pre_reviewed_design_ref")
        if link == "none" and r.get("pre_reviewed_design_ref"):
            errors.append(f"{rid}: omit pre_reviewed_design_ref when pre_review_link_role is none")
        if link == "establishes_pre_review" and r.get("decision_type") != "pre_review_disposition":
            errors.append(f"{rid}: only a pre_review_disposition establishes a pre-review")
        # F3: pre-review subject must match pre_reviewed_design_ref
        if link == "establishes_pre_review" and r.get("pre_reviewed_design_ref") and r.get("subject") != r.get("pre_reviewed_design_ref"):
            errors.append(f"{rid}: pre-review subject must match pre_reviewed_design_ref")
        # F3: deny must not establish current pre-review
        if r.get("outcome") == "deny" and link == "establishes_pre_review" and r.get("pre_review_status") == "current":
            errors.append(f"{rid}: deny must not establish current pre-review")
        if r.get("outcome") == "deny" and link == "establishes_pre_review":
            errors.append(f"{rid}: deny must not establish a pre-review")
        supersedes = r.get("supersedes") if isinstance(r.get("supersedes"), list) else []
        if rid in supersedes:
            errors.append(f"{rid}: a Decision cannot supersede itself")
        if len(supersedes) != len(set(supersedes)):
            errors.append(f"{rid}: supersedes contains duplicate IDs")
        unresolved = [old for old in supersedes if old not in all_decisions]
        for old in unresolved:
            errors.append(f"{rid}: unresolved supersedes predecessor {old!r} (reported separately)")
        for c in crecs:
            if isinstance(c, dict) and "model_version" in c and "model_version" in r and isinstance(c.get("model_version"), dict) and isinstance(r.get("model_version"), dict):
                if c["model_version"].get("sha256") != r["model_version"].get("sha256"):
                    errors.append(f"{rid}: condition {c.get('@id')} binds a different model than the Decision")
    # F7: supersession cycle check over all resolved supersedes edges (3+ node cycles)
    errors += _supersession_cycles(all_decisions)
    return errors


def _supersession_cycles(by_id: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    graph = {oid: [s for s in (o.get("supersedes") or []) if s in by_id]
             for oid, o in by_id.items()}
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str, stack: list[str]) -> None:
        if node in visiting:
            cycle = stack[stack.index(node):] + [node]
            if len(set(cycle)) >= 3 or len(cycle) > 2:
                errors.append(f"supersedes cycle: {' -> '.join(cycle)}")
            elif len(cycle) == 2 or (len(cycle) == 3 and cycle[0] == cycle[2]):
                errors.append(f"{node}: supersedes cycle with {stack[-1] if stack else node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for nxt in graph.get(node, []):
            dfs(nxt, stack + [node])
        visiting.remove(node)
        visited.add(node)

    for oid in graph:
        dfs(oid, [])
    # Also catch 2-node mutual cycles explicitly
    for oid, o in by_id.items():
        for old in o.get("supersedes") or []:
            if old in by_id and oid in (by_id[old].get("supersedes") or []):
                msg = f"{oid}: supersedes cycle with {old}"
                if msg not in errors and not any(oid in e and old in e and "cycle" in e for e in errors):
                    errors.append(msg)
    return errors
