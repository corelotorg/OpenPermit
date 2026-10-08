# SPDX-License-Identifier: Apache-2.0
"""PDF path: artifact manifest, declared values on the same rule units, extraction gating."""

import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from conftest import FIXED_TIME, REPO, states
from ori_verify import cli, declared, pdf_extract, pdf_manifest
from ori_verify.synthetic_pdf import make_text_pdf

VA = "urn:ori:jurisdiction:us-va"
DECLARED_SCHEMA = Draft202012Validator(json.loads((REPO / "spec" / "ori-declared-values-0.1.schema.json").read_text()))
MANIFEST_SCHEMA = Draft202012Validator(json.loads((REPO / "spec" / "ori-pdf-artifact-manifest-0.1.schema.json").read_text()))

PAGES_V1 = [["SHEET A-101 FLOOR PLAN", "BEDROOM 1 CLG HT 8'-0\""],
            ["SHEET A-301 STAIR SECTION", "RISER 8\" MAX", "TREAD 9 1/2\"", "HEADROOM 6'-10\""]]
PAGES_V2 = [PAGES_V1[0], ["SHEET A-301 STAIR SECTION REV 1", "RISER 8 1/2\" MAX", "TREAD 9 1/2\""]]


@pytest.fixture()
def plan_sets(tmp_path):
    v1 = make_text_pdf(tmp_path / "plans-v1.pdf", PAGES_V1, pdfa_claim=(2, "B"), page_labels=["A-101", "A-301"])
    v2 = make_text_pdf(tmp_path / "plans-v2.pdf", PAGES_V2, page_labels=["A-101", "A-301"])
    m1 = pdf_manifest.build_manifest([v1], "ps-demo", 1, "applicant:demo", FIXED_TIME)
    m2 = pdf_manifest.build_manifest([v2], "ps-demo", 2, "applicant:demo", FIXED_TIME, supersedes=[m1["artifacts"][0]["artifact_id"]])
    return v1, v2, m1, m2


def test_manifest_hashes_and_supersession(plan_sets, core_validator):
    v1, v2, m1, m2 = plan_sets
    a1 = m1["artifacts"][0]
    assert a1["sha256"] == hashlib.sha256(v1.read_bytes()).hexdigest()
    assert a1["artifact_id"] == "urn:ori:artifact:sha256:" + a1["sha256"]
    assert a1["page_count"] == 2 and [p["page_label"] for p in a1["pages"]] == ["A-101", "A-301"]
    assert a1["pdfa"]["claimed"] is True and a1["pdfa"]["part"] == 2 and a1["pdfa"]["conformance"] == "B"
    assert m2["artifacts"][0]["pdfa"]["claimed"] is False
    assert m2["supersedes"] == [a1["artifact_id"]]
    for m in (m1, m2):
        assert not list(MANIFEST_SCHEMA.iter_errors(m))
        for ev in pdf_manifest.evidence_objects(m):
            assert not list(core_validator.iter_errors(ev))
    with pytest.raises(ValueError):
        pdf_manifest.build_manifest([v2], "ps-demo", 2, "applicant:demo", FIXED_TIME)


def test_page_level_diff_targets_rereview(plan_sets):
    *_, m1, m2 = plan_sets
    d = pdf_manifest.diff_manifests(m1, m2)
    assert d["changed"] == ["A-301"] and d["unchanged"] == ["A-101"] and not d["added"] and not d["removed"]


def _declared(aid, **over):
    a = lambda page, sheet: {"artifact_id": aid, "page": page, "sheet": sheet}
    doc = {
        "declared_values_profile": "ori-declared-values-0.1", "submission_id": "demo-1", "jurisdiction": VA,
        "declared_by": "applicant:demo", "declared_at": FIXED_TIME,
        "plan_set": {"plan_set_id": "ps-demo", "version": 1, "artifact_ids": [aid]},
        "stairs": [{"id": "s1", "label": "Stair 1 flight 1",
                    "riser_heights_in": {"value": [8.0] * 13, "anchor": a(2, "A-301")},
                    "tread_depths_in": {"value": [9.5] * 12, "anchor": a(2, "A-301")},
                    "min_headroom_in": {"value": 82.0, "anchor": a(2, "A-301")}}],
        "spaces": [{"id": "b1", "label": "Bedroom 1", "use": {"value": "habitable", "anchor": a(1, "A-101")},
                    "ceiling_height_in": {"value": 96.0, "anchor": a(1, "A-101")}, "floor_area_ft2": {"value": 110.0, "anchor": a(1, "A-101")}},
                   {"id": "k1", "label": "Kitchen", "use": {"value": "kitchen", "anchor": a(1, "A-101")},
                    "ceiling_height_in": {"value": 96.0, "anchor": a(1, "A-101")}, "floor_area_ft2": {"value": 56.0, "anchor": a(1, "A-101")}},
                   {"id": "ba1", "label": "Bath 1", "use": {"value": "bathroom", "anchor": a(1, "A-101")},
                    "ceiling_height_in": {"value": 81.0, "anchor": a(1, "A-101")}, "floor_area_ft2": {"value": 40.0, "anchor": a(1, "A-101")}}],
        "eeros": [{"id": "w1", "label": "Bedroom 1 EERO", "net_clear_height_in": {"value": 36.0, "anchor": a(1, "A-101")},
                   "net_clear_width_in": {"value": 24.0, "anchor": a(1, "A-101")},
                   "grade_floor_or_below_grade": {"value": False, "anchor": a(1, "A-101")}, "sill_height_in": {"value": 42.0, "anchor": a(1, "A-101")}}],
        "walking_surfaces": [{"id": "d1", "label": "Deck 0", "drop_height_in": {"value": 48.0, "anchor": a(1, "A-101")},
                              "guard_present": {"value": True, "anchor": a(1, "A-101")}}],
        "guards": [{"id": "g1", "label": "Deck 0 guard", "height_in": {"value": 36.0, "anchor": a(1, "A-101")},
                    "on_stair_open_side": {"value": False, "anchor": a(1, "A-101")}}],
    }
    doc.update(over)
    return doc


def test_declared_values_run_the_same_rules_as_ifc(plan_sets, ifc_models, core_validator):
    *_, m1, _ = plan_sets
    aid = m1["artifacts"][0]["artifact_id"]
    doc = _declared(aid)
    assert not list(DECLARED_SCHEMA.iter_errors(doc))
    rep = cli.run_declared(doc, m1, executed_at=FIXED_TIME)
    assert rep["anchor_problems"] == []
    ifc = cli.run_ifc(ifc_models["pass"], executed_at=FIXED_TIME)
    by_rule = lambda r: sorted((k[0], k[1], v) for k, v in states(r).items())
    assert by_rule(rep) == by_rule(ifc)
    for obj in rep["records"] + rep["evidence"]:
        assert not list(core_validator.iter_errors(obj)), obj["id"]
    rec = next(r for r in rep["records"] if r["metadata"]["section"] == "R311.7.5.1")
    assert rec["metadata"]["subject"]["anchor"]["sheet"] == "A-301"
    assert rec["metadata"]["facts_used"]["riser_heights"]["origin"] == "applicant_declared"


def test_declared_fail_values(plan_sets):
    *_, m1, _ = plan_sets
    aid = m1["artifacts"][0]["artifact_id"]
    doc = _declared(aid)
    doc["stairs"][0]["riser_heights_in"]["value"] = [8.0] * 12 + [8.5]
    rep = cli.run_declared(doc, m1, executed_at=FIXED_TIME)
    assert states(rep)[("R311.7.5.1", "maximum riser", "Stair 1 flight 1")] == "fail"


def test_anchor_to_missing_page_is_not_used(plan_sets):
    *_, m1, _ = plan_sets
    aid = m1["artifacts"][0]["artifact_id"]
    doc = _declared(aid)
    doc["stairs"][0]["riser_heights_in"]["anchor"]["page"] = 9
    rep = cli.run_declared(doc, m1, executed_at=FIXED_TIME)
    assert rep["anchor_problems"]
    assert states(rep)[("R311.7.5.1", "maximum riser", "Stair 1 flight 1")] == "unknown"


def test_vector_extraction_is_unknown_until_confirmed(plan_sets):
    v1, _, m1, _ = plan_sets
    art = m1["artifacts"][0]
    callouts = pdf_extract.extract_callouts(v1, art["artifact_id"], art)
    keys = {c["key"]: c for c in callouts}
    assert keys["riser_heights_in"]["value_in"] == 8.0 and keys["riser_heights_in"]["anchor"]["sheet"] == "A-301"
    assert keys["tread_depths_in"]["value_in"] == 9.5
    assert keys["min_headroom_in"]["value_in"] == 82.0
    assert keys["ceiling_height_in"]["value_in"] == 96.0
    doc = pdf_extract.declared_from_callouts(callouts, submission_id="demo-x", jurisdiction=VA, declared_by="extractor:vector",
                                             declared_at=FIXED_TIME, plan_set={"plan_set_id": "ps-demo", "version": 1, "artifact_ids": [art["artifact_id"]]})
    assert not list(DECLARED_SCHEMA.iter_errors(doc))
    rep = cli.run_declared(doc, m1, executed_at=FIXED_TIME)
    riser = ("R311.7.5.1", "maximum riser", "Extracted candidate (stairs)")
    assert states(rep)[riser] == "unknown"
    assert rep["counts"]["pass"] == 0 and rep["counts"]["fail"] == 0
    confirmed = declared.confirm(doc, "stairs", "stair-extracted", "riser_heights_in", by="reviewer")
    confirmed = declared.confirm(confirmed, "stairs", "stair-extracted", "tread_depths_in", by="applicant")
    rep2 = cli.run_declared(confirmed, m1, executed_at=FIXED_TIME)
    assert states(rep2)[riser] == "pass"
    assert states(rep2)[("R311.7.5.2", "minimum tread", "Extracted candidate (stairs)")] == "pass"


def test_ai_extraction_label_is_never_used_for_pass_fail(plan_sets):
    *_, m1, _ = plan_sets
    aid = m1["artifacts"][0]["artifact_id"]
    doc = _declared(aid)
    doc["stairs"][0]["riser_heights_in"]["origin"] = "ai_extracted_unverified"
    doc["stairs"][0]["riser_heights_in"]["value"] = [9.0] * 13
    rep = cli.run_declared(doc, m1, executed_at=FIXED_TIME)
    assert states(rep)[("R311.7.5.1", "maximum riser", "Stair 1 flight 1")] == "unknown"
