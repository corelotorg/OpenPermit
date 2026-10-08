# SPDX-License-Identifier: Apache-2.0
"""Rule-unit data checks: generator sync, schema validity, sourcing labels."""

import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CH03 = ROOT / "rules" / "irc2021" / "ch03"
_spec = importlib.util.spec_from_file_location("build_units", CH03 / "build_units.py")
build_units = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_units)

RULE_SCHEMA = json.loads((ROOT / "spec" / "ori-rule-unit-0.1.schema.json").read_text())
CORE = Draft202012Validator(json.loads((ROOT / "spec" / "ori-core-0.1.schema.json").read_text()))
UNIT = Draft202012Validator(RULE_SCHEMA)
HEADER = Draft202012Validator({"$defs": RULE_SCHEMA["$defs"], "$ref": "#/$defs/collectionHeader"})
COL = json.loads((CH03 / "va-vrc-2021-ch03.units.json").read_text())


def test_committed_outputs_match_generator():
    j, m = build_units.render()
    assert j == (CH03 / "va-vrc-2021-ch03.units.json").read_text(), "run rules/irc2021/ch03/build_units.py"
    assert m == (CH03 / "CHAPTER-3-TABLE.md").read_text(), "run rules/irc2021/ch03/build_units.py"


def test_collection_and_units_validate():
    assert not list(HEADER.iter_errors(COL))
    for u in COL["units"] + COL["va_added_units"]:
        assert not list(UNIT.iter_errors(u)), (u["id"], [e.message for e in UNIT.iter_errors(u)])
        assert not list(CORE.iter_errors(u)), u["id"]
    for s in COL["sources"]:
        assert not list(CORE.iter_errors(s)), s["id"]


def test_every_section_r301_to_r327_is_classified():
    sections = {int(u["source_section"]["section"][1:4]) for u in COL["units"]}
    assert sections == set(range(301, 328))


def test_sources_referenced_exist_and_classes_are_estimates():
    ids = {s["id"] for s in COL["sources"]}
    for u in COL["units"] + COL["va_added_units"]:
        assert u["classification_basis"] == "estimate"
        for ref in u["source"] + u["provenance"]["sources_checked"]:
            assert ref in ids, (u["id"], ref)
        for p in u["base_model"].get("parameters", []) + [p for l in u["jurisdiction_layers"] for p in l.get("parameters", [])]:
            assert p["source"] in ids


def test_split_matches_units():
    from collections import Counter
    c = Counter(u["check_class"] for u in COL["units"])
    assert COL["class_split_r301_r327"] == {k: c[k] for k in ("data_check", "geometric_deterministic", "judgment")}
    assert sum(COL["class_split_r301_r327"].values()) == COL["unit_count_r301_r327"]


def test_ids_references_resolve():
    for u in COL["units"]:
        ids = u["required_information"]["ids"]
        if ids:
            path, _, name = ids["specification_ref"].partition("#")
            text = (ROOT / path).read_text()
            assert f'name="{name}"' in text, ids["specification_ref"]


def test_no_long_code_text():
    for u in COL["units"]:
        assert len(u.get("paraphrase", "")) <= 400
        assert len(u["title"]) <= 160


INTERP = json.loads((CH03 / "interpretability-ch03.json").read_text())


def test_every_judgment_unit_has_an_interpretability_prescore():
    for u in COL["units"] + COL["va_added_units"]:
        if u["check_class"] == "judgment":
            assert "interpretability" in u, u["id"]
    assert COL["interpretability_summary"]["judgment_units_scored"] == 17


def test_interpretability_records_are_verified_and_consistent():
    reg = INTERP["determinations"]
    used = set()
    for entry in INTERP["scores"].values():
        for i in entry.get("determination_ids", []) + entry.get("local_operationalization_ids", []):
            assert i in reg, i
            used.add(i)
    assert used == set(reg), f"unused determinations: {set(reg) - used}"
    for i, d in reg.items():
        assert d["verification"]["status"] == "fetched_and_read", i
        assert d["url"].startswith("https://"), i
        assert len(d["verification"].get("sha256", "")) == 64, i
    for u in COL["units"] + COL["va_added_units"]:
        it = u.get("interpretability")
        if not it:
            continue
        assert it["scoring_status"] == "estimate", u["id"]  # no human review yet
        assert all(r["role"] == "pre_scorer" for r in it["reviewers"]), u["id"]
        clar = it.get("candidate_clarification")
        if clar:
            assert clar["status"] == "DRAFT_not_submitted"
        for t in it.get("ambiguous_terms", []):
            assert len(t["term"]) <= 60  # short terms only, never long code text


def test_interpretability_summary_matches_units():
    from collections import Counter
    scored = [u for u in COL["units"] + COL["va_added_units"] if "interpretability" in u]
    c = Counter(u["interpretability"]["score"] for u in scored)
    s = COL["interpretability_summary"]
    assert s["units_scored"] == len(scored)
    assert s["score_counts"] == {k: c.get(k, 0) for k in ("clear", "ambiguous_term", "intent_dependent", "conflicting")}


def test_review_pack_matches_generator():
    import pytest
    if not (CH03 / "build_review_pack.py").is_file() or not (ROOT / "docs" / "CH3-REVIEW-PACK.md").is_file():
        pytest.skip("review pack and its generator are not part of this tree")
    spec = importlib.util.spec_from_file_location("build_review_pack", CH03 / "build_review_pack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.render(COL) == (ROOT / "docs" / "CH3-REVIEW-PACK.md").read_text(), "run rules/irc2021/ch03/build_review_pack.py"
