# SPDX-License-Identifier: Apache-2.0
"""DRAFT semantic checks for the evidence-attestation record (v0.1) and the hosted-model
georeference record (v0.1). Each check validates the schema first, then the invariants a schema
alone cannot express:

- a world-location to model-element match is computed only through an identified georeference
  of the same hosted model version (status crs_identified); local_only, none, unknown or a
  missing georeference leaves the match unknown, never a failure;
- the element, anchor and georeference all name the same model version SHA-256;
- an inline georeference status never claims more than the referenced record says;
- CRS identifiers are compared exactly as given; different strings need a stated transformation;
- every unknown match says why (basis), and the reason matches the facts;
- is_approval is false everywhere.

Machine checks are reviewer evidence, never approval. No vendor, device or exporter is required."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PROFILE = "ori-evidence-attestation-0.1"
GEOREF_PROFILE = "ori-model-georeference-0.1"
_SCHEMA_FILES = {
    EVIDENCE_PROFILE: ROOT / "spec" / "ori-evidence-attestation-0.1.schema.json",
    GEOREF_PROFILE: ROOT / "spec" / "ori-model-georeference-0.1.schema.json",
}
_REGISTRY_FILES = (
    ROOT / "spec" / "ori-review-comment-0.2.schema.json",
    ROOT / "spec" / "ori-model-georeference-0.1.schema.json",
)
_STATUS_BASIS = {
    "local_only": "model_georeference_local_only",
    "none": "model_georeference_none",
    "unknown": "model_georeference_unknown",
}
_MAX_ERRORS = 50
_validators: dict[str, Draft202012Validator] = {}


# Evidence-attestation records are validated against the $def their type names, so errors point at
# the offending field instead of a bare oneOf failure.
_TYPE_DEFS = {"Evidence": "evidence", "Attestation": "attestation"}


def _validator(profile: str, rtype: Any = None) -> Draft202012Validator:
    key = f"{profile}#{rtype if profile == EVIDENCE_PROFILE and rtype in _TYPE_DEFS else ''}"
    if key not in _validators:
        docs = [json.loads(p.read_text(encoding="utf-8")) for p in (*_REGISTRY_FILES, _SCHEMA_FILES[EVIDENCE_PROFILE])]
        reg = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
        schema = json.loads(_SCHEMA_FILES[profile].read_text(encoding="utf-8"))
        if key.endswith("#"):
            target = schema
        else:
            target = {"$ref": f"{schema['$id']}#/$defs/{_TYPE_DEFS[rtype]}"}
        _validators[key] = Draft202012Validator(target, format_checker=FormatChecker(), registry=reg)
    return _validators[key]


def schema_errors(obj: Any) -> list[str]:
    if not isinstance(obj, dict):
        return [f"<non-object>: schema: record must be an object, got {type(obj).__name__}"]
    profile = obj.get("record_profile")
    rid = obj.get("id", "<missing-id>")
    if profile not in _SCHEMA_FILES:
        return [f"{rid}: unknown record_profile {profile!r}"]
    errs = sorted(_validator(profile, obj.get("type")).iter_errors(obj), key=lambda e: list(e.path))
    return [f"{rid}: schema: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]


def _walk(node: Any, path: str = "") -> Iterator[tuple[str, str, Any]]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield path, k, v
            yield from _walk(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}/{i}")


def _sha(mv: Any) -> Any:
    return mv.get("sha256") if isinstance(mv, dict) else None


def _crs_id(crs: Any) -> Any:
    if isinstance(crs, dict):
        return crs.get("identifier")
    return crs


def _match_errors(ev: dict[str, Any], georefs: dict[str, dict[str, Any]]) -> list[str]:
    rid, errors = ev.get("id"), []
    m = ev.get("element_location_match")
    if not isinstance(m, dict):
        return errors
    geo = ev.get("geo_attestation") or {}
    sha = _sha(m.get("model_version"))
    anchor = ev.get("spatial_anchor") or {}
    if anchor.get("type") == "ifc_element":
        av = anchor.get("value") or {}
        if av.get("ifc_global_id") != m.get("ifc_global_id"):
            errors.append(f"{rid}: element_location_match names a different element than the ifc_element anchor")
        if _sha(av.get("model_version")) != sha:
            errors.append(f"{rid}: element_location_match and the ifc_element anchor name different model versions")
    mg = m.get("model_georeference")
    match, basis = m.get("match"), set(m.get("basis") or [])
    status = mg.get("status") if isinstance(mg, dict) else None
    record = None
    if isinstance(mg, dict):
        if _sha(mg.get("model_version")) != sha:
            errors.append(f"{rid}: model_georeference comes from another model version; a georeference never carries over between versions")
        ref = mg.get("ref")
        if ref is not None:
            record = georefs.get(ref)
            if record is None and match != "unknown":
                errors.append(f"{rid}: computed match relies on {ref}, which is not present to check")
            elif record is not None:
                if record.get("status") != status:
                    errors.append(f"{rid}: inline georeference status {status!r} differs from {ref} status {record.get('status')!r}")
                if _sha(record.get("model_version")) != sha:
                    errors.append(f"{rid}: {ref} describes another model version")
        elif match != "unknown":
            errors.append(f"{rid}: a computed match must name the georeference record it relied on (model_georeference.ref)")
    # Every unknown says why, and the stated reasons must match the facts.
    if mg is None and match == "unknown" and "model_georeference_missing" not in basis:
        errors.append(f"{rid}: match is unknown because no model georeference was given; basis must include model_georeference_missing")
    if status in _STATUS_BASIS and _STATUS_BASIS[status] not in basis:
        errors.append(f"{rid}: georeference status {status!r} requires basis {_STATUS_BASIS[status]!r}")
    if geo.get("crs") == "unknown" and "evidence_crs_unknown" not in basis:
        errors.append(f"{rid}: evidence CRS is unknown; basis must include evidence_crs_unknown")
    if geo.get("horizontal_accuracy_m") == "unknown" and "accuracy_unknown" not in basis:
        errors.append(f"{rid}: horizontal accuracy is unknown; basis must include accuracy_unknown")
    if match == "unknown" and m.get("method") == "not_attempted" and not basis:
        errors.append(f"{rid}: unknown match without a basis")
    if match in ("consistent", "inconsistent"):
        used = m.get("location_used")
        if used not in geo:
            errors.append(f"{rid}: location_used {used!r} is not present in geo_attestation")
        if record is not None:
            model_crs = _crs_id(record.get("crs"))
            if model_crs != geo.get("crs") and "crs_transformation_ref" not in m:
                errors.append(f"{rid}: evidence CRS {geo.get('crs')!r} and model CRS {model_crs!r} differ as given; a computed match needs crs_transformation_ref")
    return errors


def evidence_attestation_record(case: dict[str, Any]) -> list[str]:
    try:
        return _evidence_attestation_record(case)
    except Exception as exc:  # noqa: BLE001 - conformance must not crash on malformed fixtures
        return [f"evidence-attestation-record: malformed input: {type(exc).__name__}: {exc}"]


def _evidence_attestation_record(case: dict[str, Any]) -> list[str]:
    objs = case.get("objects")
    if not isinstance(objs, list) or not objs:
        return ["evidence-attestation-record: case needs a non-empty objects list"]
    errors: list[str] = []
    ids: set[str] = set()
    for o in objs:
        errs = schema_errors(o)
        errors += errs
        rid = o.get("id") if isinstance(o, dict) else None
        if rid in ids:
            errors.append(f"{rid}: duplicate id")
        ids.add(rid)
        for path, key, value in _walk(o):
            if key == "is_approval" and value is not False:
                errors.append(f"{rid}: {path}/is_approval must be false; evidence is not approval")
    if errors:
        return errors[:_MAX_ERRORS]
    georefs = {o["id"]: o for o in objs if o.get("record_profile") == GEOREF_PROFILE}
    for o in objs:
        if o.get("type") == "Evidence":
            errors += _match_errors(o, georefs)
    return errors[:_MAX_ERRORS]
