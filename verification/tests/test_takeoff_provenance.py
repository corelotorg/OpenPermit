# SPDX-License-Identifier: Apache-2.0
"""Regression: plan-takeoff provenance (Pset_ORI_Takeoff) is honoured by ``ori_verify.cli ifc``.

Before the fix, ``ori_verify.cli ifc`` on a takeoff IFC returned pass for ceiling heights that
were placeholders (not from the plan) and for room areas that nobody had reviewed, because only
``ori_takeoff.to_ifc.check_ifc`` applied the provenance policy. The policy now lives in
``ori_verify.ifc_extract.IfcFacts._takeoff_policy`` and both paths agree.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.element as uel

from ori_takeoff import to_ifc as T
from ori_verify import cli

EX = Path(__file__).resolve().parents[1] / "examples" / "takeoff"
EXTRACTED = EX / "ori-sample-house.extracted.ifc"
GT = EX / "ori-sample-house.groundtruth.ifc"
AT = "2026-10-12T00:00:00Z"


def _by_section(report):
    out = {}
    for r in report["records"]:
        sec = r["source"]["section"] if isinstance(r.get("source"), dict) and "section" in r["source"] else r["metadata"].get("section")
        out.setdefault(sec, []).append(r)
    return out


def _states(report):
    return Counter(r["outcome"]["result"] if isinstance(r["outcome"], dict) else r["outcome"] for r in report["records"])


def _edit(src: Path, dst: Path, fn) -> Path:
    m = ifcopenshell.open(str(src))
    for el in m.by_type("IfcProduct"):
        p = uel.get_pset(el, "Pset_ORI_Takeoff", should_inherit=False)
        if p and "Method" in p:
            fn(m, el, m.by_id(p["id"]))
    m.write(str(dst))
    return dst


def test_placeholder_and_unreviewed_give_no_pass_via_ori_verify():
    rep = cli.run_ifc(EXTRACTED, executed_at=AT)
    assert rep["counts"]["pass"] == 0
    assert rep["counts"]["fail"] == 0
    assert rep["counts"]["unknown"] == sum(rep["counts"].values())
    assert rep["takeoff_adjustments"]
    assert "provenance_warning" in rep and "adjustment(s)" in rep["provenance_warning"]
    assert rep["auto_extracted_pass"] == 0


def test_warning_does_not_claim_adjustments_for_ground_truth():
    rep = cli.run_ifc(GT, executed_at=AT)
    assert rep["takeoff_adjustments"] == []
    assert "No adjustments were needed" in rep["provenance_warning"]


def test_placeholder_heights_removed_unreviewed_relabelled():
    rep = cli.run_ifc(EXTRACTED, executed_at=AT)
    adj = rep["takeoff_adjustments"]
    assert any("ceiling_height removed (placeholder height" in a for a in adj)
    assert any("relabelled unconfirmed" in a for a in adj)


def test_check_ifc_and_run_ifc_agree():
    for path in (EXTRACTED, GT):
        a = cli.run_ifc(path, executed_at=AT)
        b = T.check_ifc(path)
        assert a["counts"] == b["counts"], path.name


def test_ground_truth_takeoff_still_usable():
    rep = cli.run_ifc(GT, executed_at=AT)
    assert rep["counts"]["pass"] > 0
    assert rep["auto_extracted_pass"] == 0


def test_reviewed_elements_can_pass(tmp_path):
    def review(m, el, pset):
        api.run("pset.edit_pset", m, pset=pset, properties={"ReviewStatus": "reviewed", "HeightSource": "overlay"})
    path = _edit(EXTRACTED, tmp_path / "reviewed.ifc", review)
    rep = cli.run_ifc(path, executed_at=AT)
    assert rep["counts"]["pass"] > 0
    assert rep["auto_extracted_pass"] == 0


def test_missing_review_status_fails_closed(tmp_path):
    def blank(m, el, pset):
        api.run("pset.edit_pset", m, pset=pset, properties={"ReviewStatus": "not-a-status", "HeightSource": "overlay"})
    path = _edit(EXTRACTED, tmp_path / "odd.ifc", blank)
    rep = cli.run_ifc(path, executed_at=AT)
    assert rep["counts"]["pass"] == 0


def test_cli_exit_codes(tmp_path):
    assert cli.main(["ifc", str(EXTRACTED), "--out", str(tmp_path / "r.json")]) == 0
    assert cli.main(["ifc", str(GT), "--out", str(tmp_path / "g.json")]) == 0


def test_plain_fixtures_unaffected():
    from ori_verify import ifc_fixtures
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = ifc_fixtures.write_fixture(ifc_fixtures.passing_spec(), Path(d) / "p.ifc")
        rep = cli.run_ifc(p, executed_at=AT)
    assert "takeoff_adjustments" not in rep and "provenance_warning" not in rep
    assert rep["counts"]["fail"] == 0 and rep["counts"]["pass"] > 0
