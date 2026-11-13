# SPDX-License-Identifier: Apache-2.0
"""Chapter 6 (wall framing and Virginia practical wall bracing): rules, fixtures, safeguards."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import pytest

from conftest import FIXED_TIME, REPO, VERIFICATION
from ori_verify import cli, framing_fixtures as F, ifc_extract, rules, units
from ori_verify.records import dumps

EX = VERIFICATION / "examples"
COL = json.loads((REPO / "rules" / "irc2021" / "ch06" / "va-vrc-2021-ch06.units.json").read_text())


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    d = tmp_path_factory.mktemp("ch06")
    out = {}
    for name, fn in F.MODELS.items():
        p = F.write(fn(), d / f"{name}.ifc")
        subs, _ = ifc_extract.extract(p)
        out[name] = [r for r in rules.evaluate(subs, units.implemented_units()) if r.unit_id.startswith("urn:ori:rule-unit:irc2021-va:R6")]
    return out


def _states(rs):
    return Counter(r.state for r in rs)


def test_collection_shape():
    assert COL["unit_count"] == len(COL["units"]) == 88
    assert COL["executable_unit_count"] == 13
    assert COL["executable_with_verified_thresholds"] == 7
    for u in COL["units"]:
        assert u["paraphrase"] and u["source_url"].startswith("https://codes.iccsafe.org/")
        assert u["legal_boundary"]["machine_result_is_approval"] is False


def test_va_layer_items_match_regulation():
    by = {u["source_section"]["section"]: u["jurisdiction_layers"][0] for u in COL["units"]}
    assert by["R602.10"]["amendment_ref"]["item"] == "310.8 item 62"
    assert by["R602.10.9"]["override_mode"] == "adds_exception"
    assert by["R602.12.6"]["override_mode"] == "replaces_section"
    assert by["R602.3.1"]["override_mode"] == "adopts_base"


def test_every_estimate_value_gives_unknown(results):
    for rs in results.values():
        for r in rs:
            if any(q["value_status"] == "estimate" for q in r.required):
                assert r.state in ("unknown", "not_applicable"), (r.unit_id, r.state)


def test_pass_fixture_has_no_fail(results):
    s = _states(results["pass"])
    assert s["fail"] == 0 and s["pass"] >= 30


def test_fail_fixture_fails_each_verified_rule(results):
    failed = {(r.section, r.part) for r in results["fail"] if r.state == "fail"}
    assert {("R602.12.1", None), ("R602.12.2", "exterior panel length"), ("R602.12.2", "interior panel length"), ("R602.12.3", None),
            ("R602.12.4.2", None), ("R602.12.6", "corner distance"), ("R602.12.6", "panel gap")} <= failed


def test_fail_fixture_unverified_violations_are_flagged_not_failed(results):
    flagged = [r for r in results["fail"] if r.reason_code == "threshold_unverified" and "would not meet" in r.message]
    assert {r.section for r in flagged} >= {"R602.3.1", "R602.3.2", "R602.6"}


def test_incomplete_fixture_never_passes_or_fails(results):
    s = _states(results["incomplete"])
    assert s["pass"] == 0 and s["fail"] == 0 and s["unknown"] > 0


def test_missing_info_never_fails(results):
    for rs in results.values():
        for r in rs:
            if r.state == "fail":
                assert r.reason_code not in rules.MISSING_INFORMATION_REASONS


def test_base_jurisdiction_has_no_practical_bracing_values(tmp_path):
    p = F.write(F.passing_model(), tmp_path / "p.ifc")
    rep = cli.run_ifc(p, jurisdiction="base", executed_at=FIXED_TIME)
    subs, _ = ifc_extract.extract(p)
    rs = [r for r in rules.evaluate(subs, units.implemented_units(None)) if r.section.startswith("R602.12")]
    assert rs and all(r.state in ("unknown", "not_applicable") for r in rs)
    assert rep["counts"]["fail"] == 0


def test_absent_panels_are_not_evidence_without_complete_plan(tmp_path):
    m = F.passing_model()
    m.panels = [p for p in m.panels if not p.name.startswith("N")]
    m.rect.props["BracingPlanComplete"] = False
    subs, _ = ifc_extract.extract(F.write(m, tmp_path / "m.ifc"))
    north = [r for r in rules.evaluate(subs, units.implemented_units()) if "north side" in r.subject.label]
    assert north and all(r.state != "fail" for r in north)
    assert any(r.reason_code == "required_element_not_found" for r in north)


def test_unreviewed_takeoff_framing_is_unconfirmed(tmp_path):
    p = F.write(F.passing_model(), tmp_path / "t.ifc")
    m = ifcopenshell.open(str(p))
    for el in m.by_type("IfcPlate"):
        ps = api.run("pset.add_pset", m, product=el, name="Pset_ORI_Takeoff")
        api.run("pset.edit_pset", m, pset=ps, properties={"Method": "auto_extracted", "ReviewStatus": "unreviewed"})
    m.write(str(tmp_path / "t2.ifc"))
    rep = cli.run_ifc(tmp_path / "t2.ifc", executed_at=FIXED_TIME)
    subs, _ = ifc_extract.extract(tmp_path / "t2.ifc")
    panel_rs = [r for r in rules.evaluate(subs, units.implemented_units()) if r.subject.kind == "braced_wall_panel"]
    assert panel_rs and all(r.state != "pass" for r in panel_rs)
    assert rep["auto_extracted_pass"] == 0


@pytest.mark.parametrize("name", ["pass", "fail", "incomplete"])
def test_committed_ch06_reports_reproduce(name):
    report = cli.run_ifc(EX / "ch06" / f"ori-ch06-{name}.ifc", executed_at=FIXED_TIME)
    report["artifact"]["filename"] = f"ori-ch06-{name}.ifc"
    assert dumps(report) == (EX / "reports" / f"ifc-ch06-{name}.report.json").read_text()


def test_ch06_rule_functions_registered():
    for u in units.implemented_units():
        assert u.function in rules.RULES, u.id
