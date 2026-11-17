# SPDX-License-Identifier: Apache-2.0
"""Evidence-attestation 0.1 and model-georeference 0.1 drafts: schemas are valid, positive fixtures
pass, every negative fixture is rejected for its intended reason, and the georeference invariants
hold under mutation. All fixtures are synthetic: fictional model hashes, CRS identifier and
coordinates; no real site, survey or EPSG code."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ori_records_evidence_t", ROOT / "conformance" / "records_evidence.py")
re_ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(re_)
EV_SCHEMA = json.loads((ROOT / "spec" / "ori-evidence-attestation-0.1.schema.json").read_text(encoding="utf-8"))
GEO_SCHEMA = json.loads((ROOT / "spec" / "ori-model-georeference-0.1.schema.json").read_text(encoding="utf-8"))
POS = sorted((ROOT / "conformance" / "positive").glob("evidence-*.json"))
NEG = sorted((ROOT / "conformance" / "negative").glob("evidence-*.json"))

# Intended rejection reason for each negative fixture (substring of one error).
REASON = {
    "evidence-local-only-match-computed": "element_location_match/match: 'unknown' was expected",
    "evidence-none-match-computed": "element_location_match/match: 'unknown' was expected",
    "evidence-missing-georeference-match-computed": "element_location_match/match: 'unknown' was expected",
    "evidence-crs-unknown-match-computed": "element_location_match/match: 'unknown' was expected",
    "evidence-accuracy-unknown-match-computed": "element_location_match/match: 'unknown' was expected",
    "evidence-missing-crs-as-fail": "'fail' is not one of",
    "evidence-is-approval-true": "is_approval",
    "evidence-ifc-element-bad-globalid": "spatial_anchor/value/ifc_global_id",
    "evidence-ifc-element-no-model-hash": "spatial_anchor/value/model_version/sha256",
    "evidence-ifc-element-anchor-mismatch": "different element than the ifc_element anchor",
    "evidence-georeference-other-version": "another model version",
    "evidence-georeference-status-upgraded": "differs from urn:ori:model-georeference:synthetic-local status 'local_only'",
    "evidence-georeference-unresolved": "not present to check",
    "evidence-crs-differs-no-transformation": "needs crs_transformation_ref",
    "evidence-unknown-match-without-basis": "'basis' is a required property",
    "evidence-georeference-identified-without-tie": "map_conversion",
    "evidence-georeference-identified-without-crs": "crs/identifier",
    "evidence-sha256-digest-malformed": "integrity/digest",
}


def _case(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _base():
    return _case(ROOT / "conformance" / "positive" / "evidence-crs-identified-match-consistent.json")


def test_schemas_are_valid():
    Draft202012Validator.check_schema(EV_SCHEMA)
    Draft202012Validator.check_schema(GEO_SCHEMA)


def test_fixture_sets_present_and_mapped():
    assert POS and NEG
    assert {p.stem for p in NEG} == set(REASON), "every negative fixture needs an intended reason, and only those"
    for p in POS + NEG:
        assert _case(p)["rule"] == "evidence-attestation-record"


@pytest.mark.parametrize("path", POS, ids=lambda p: p.stem)
def test_positive_fixtures_pass(path):
    case = _case(path)
    assert case["expected"] == "pass"
    assert re_.evidence_attestation_record(case) == []


@pytest.mark.parametrize("path", NEG, ids=lambda p: p.stem)
def test_negative_fixtures_rejected_for_intended_reason(path):
    case = _case(path)
    assert case["expected"] == "fail"
    errors = re_.evidence_attestation_record(case)
    assert errors, "negative fixture was accepted"
    assert any(REASON[path.stem] in e for e in errors), errors


@pytest.mark.parametrize("status", ["local_only", "none", "unknown"])
def test_non_identified_georeference_never_supports_a_computed_match(status):
    case = _base()
    geo, ev = case["objects"][0], case["objects"][1]
    geo["status"] = status
    ev["element_location_match"]["model_georeference"]["status"] = status
    if status in ("none", "unknown"):
        geo["crs"], geo["map_conversion"] = "unknown", "unknown"
    for match in ("consistent", "inconsistent"):
        ev["element_location_match"]["match"] = match
        assert re_.evidence_attestation_record(case), f"{status} must not support a {match} match"


def test_match_vocabulary_has_no_fail_and_unknown_is_always_allowed():
    m = EV_SCHEMA["$defs"]["elementLocationMatch"]["properties"]
    assert "fail" not in m["match"]["enum"] and "unknown" in m["match"]["enum"]
    statuses = GEO_SCHEMA["$defs"]["georeferenceStatus"]["enum"]
    assert statuses == ["crs_identified", "local_only", "none", "unknown"]


def test_canonical_globalid_pattern_not_weakened():
    rc = json.loads((ROOT / "spec" / "ori-review-comment-0.2.schema.json").read_text(encoding="utf-8"))
    env = json.loads((ROOT / "spec" / "ori-transmission-envelope-0.1.schema.json").read_text(encoding="utf-8"))
    canon = env["$defs"]["globalId"]["pattern"]
    assert canon == "^[0-3][0-9A-Za-z_$]{21}$"
    assert rc["$defs"]["elementAnchor"]["properties"]["ifc_global_id"]["pattern"] == canon
    assert EV_SCHEMA["$defs"]["globalId"]["pattern"] == canon


def test_is_approval_false_everywhere():
    for path in POS:
        for o in _case(path)["objects"]:
            assert o["is_approval"] is False and o["label"] == "Reviewer evidence, not approval"


def test_crs_identifiers_preserved_as_given():
    """A receiver never rewrites a CRS identifier: two different strings without a stated
    transformation cannot support a computed match, even if they might name the same system."""
    case = _base()
    ev = case["objects"][1]
    ev["geo_attestation"]["crs"] = ev["geo_attestation"]["crs"].upper()
    assert any("crs_transformation_ref" in e for e in re_.evidence_attestation_record(case))
    ev["element_location_match"]["crs_transformation_ref"] = "urn:ori:artifact:synthetic-transformation-1"
    assert re_.evidence_attestation_record(case) == []


def test_fixtures_are_synthetic_no_real_crs_codes():
    for path in POS + NEG:
        text = json.dumps(_case(path)["objects"])
        assert "EPSG" not in text.upper() and "opengis.net/def/crs" not in text, path.name
        assert "Synthetic test data" in _case(path)["description"]


def test_world_location_with_unknown_crs_is_kept_not_dropped():
    """Coordinates with an unknown CRS are kept as captured; they just cannot be matched."""
    case = _case(ROOT / "conformance" / "positive" / "evidence-world-point-no-match.json")
    ev = case["objects"][0]
    assert ev["geo_attestation"]["crs"] == "unknown" and ev["geo_attestation"]["observed_location"]["coordinates"]
    bad = copy.deepcopy(case)
    bad["objects"][0]["geo_attestation"]["horizontal_accuracy_m"] = None
    assert re_.evidence_attestation_record(bad)


def test_core_schema_accepts_typed_spatial_anchor():
    """R1 alignment: the core evidence slot accepts the same typed anchor (and still a legacy string)."""
    core = json.loads((ROOT / "spec" / "ori-core-0.1.schema.json").read_text(encoding="utf-8"))
    slot = Draft202012Validator(core["$defs"]["evidence"]["properties"]["spatial_anchor"])
    for path in POS:
        for o in _case(path)["objects"]:
            if o.get("type") == "Evidence":
                assert slot.is_valid(o["spatial_anchor"]), path.name
    assert slot.is_valid("urn:ori:legacy-anchor:1") and slot.is_valid(None)
    assert not slot.is_valid({"type": "ifc_element"})


def test_readme_counts_computed_from_fixtures():
    text = (ROOT / "conformance" / "README.md").read_text(encoding="utf-8")
    assert f"{len(POS)} positive cases MUST be accepted (`positive/evidence-*.json`)" in text
    assert f"{len(NEG)} negative cases MUST be rejected (`negative/evidence-*.json`)" in text
