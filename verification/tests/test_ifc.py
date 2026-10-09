# SPDX-License-Identifier: Apache-2.0
"""End-to-end on programmatic IFC models: extraction, rules, ORI records, IDS, BCF."""

import zipfile
from xml.etree import ElementTree as ET

import ifcopenshell
import ifctester.ids
import pytest

from conftest import FIXED_TIME, REPO, states
from ori_verify import EVIDENCE_LABEL, bcf, cli

IDS_DIR = REPO / "rules" / "irc2021" / "ch03" / "ids"


@pytest.fixture(scope="module")
def reports(ifc_models):
    return {k: cli.run_ifc(p, executed_at=FIXED_TIME) for k, p in ifc_models.items()}


def test_pass_model_has_no_fail_or_unknown(reports):
    c = reports["pass"]["counts"]
    assert c["fail"] == 0 and c["unknown"] == 0 and c["pass"] == 15


def test_fail_model_fails_each_implemented_check(reports):
    st = states(reports["fail"])
    expected_fail = [
        ("R311.7.5.1", "maximum riser"), ("R311.7.5.1", "riser uniformity"), ("R311.7.5.2", "minimum tread"),
        ("R311.7.5.2", "tread uniformity"), ("R311.7.2", None), ("R304.1", None), ("R305.1", "habitable"),
        ("R305.1", "bath-toilet-laundry"), ("R310.2.1", "net clear area"), ("R310.2.1", "net clear height"),
        ("R310.2.1", "net clear width"), ("R310.2.3", None), ("R312.1.2", "general"),
    ]
    for sec, part in expected_fail:
        assert any(k[0] == sec and k[1] == part and v == "fail" for k, v in st.items()), (sec, part)


def test_incomplete_model_never_fails(reports):
    r = reports["incomplete"]
    assert r["counts"]["fail"] == 0
    assert r["counts"]["unknown"] >= 9
    for rec in r["records"]:
        if rec["metadata"]["result_state"] == "unknown":
            assert rec["outcome"] == "indeterminate"


def test_irc_base_without_va_layer_fails_the_va_passing_stair(ifc_models):
    base = cli.run_ifc(ifc_models["pass"], jurisdiction="base", executed_at=FIXED_TIME)
    st = states(base)
    assert st[("R311.7.5.1", "maximum riser", "Stair 1 flight 1")] == "fail"
    assert st[("R311.7.5.2", "minimum tread", "Stair 1 flight 1")] == "fail"


def test_records_are_core_valid_and_labeled(reports, core_validator):
    for rep in reports.values():
        assert rep["label"] == EVIDENCE_LABEL and rep["is_approval"] is False
        for obj in rep["records"] + rep["evidence"]:
            errors = list(core_validator.iter_errors(obj))
            assert not errors, (obj["id"], [e.message for e in errors])
        for rec in rep["records"]:
            assert rec["type"] == "Verification"
            assert rec["metadata"]["label"] == EVIDENCE_LABEL
            assert rec["metadata"]["is_approval"] is False
            assert rec["inputs"] == [rep["artifact"]["artifact_id"]]
        assert not any(o["type"] == "Decision" for o in rep["records"] + rep["evidence"])


def test_records_are_reproducible(ifc_models):
    a = cli.run_ifc(ifc_models["fail"], executed_at=FIXED_TIME)
    b = cli.run_ifc(ifc_models["fail"], executed_at=FIXED_TIME)
    assert a == b


def test_ids_information_requirements(ifc_models):
    """IDS checks the information a rule needs; geometry stays with the evaluator."""
    def run(ids_name, model):
        spec = ifctester.ids.open(str(IDS_DIR / ids_name))
        spec.validate(ifcopenshell.open(str(model)))
        return [s.status for s in spec.specifications]
    for name in ("ori-ch03-stairs.ids", "ori-ch03-spaces.ids", "ori-ch03-eero.ids", "ori-ch03-guards.ids"):
        assert all(run(name, ifc_models["pass"])), name
    assert not all(run("ori-ch03-spaces.ids", ifc_models["incomplete"]))
    assert not all(run("ori-ch03-eero.ids", ifc_models["incomplete"]))


def test_bcf_topics_for_fail_and_unknown(reports, tmp_path):
    rep = reports["fail"]
    path, n = bcf.write_bcf(rep, tmp_path / "fail.bcf")
    assert n == rep["counts"]["fail"] + rep["counts"]["unknown"]
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        assert "bcf.version" in names and "extensions.xml" in names
        markups = [x for x in names if x.endswith("markup.bcf")]
        assert len(markups) == n
        for m in markups:
            root = ET.fromstring(z.read(m))
            title = root.find("Topic/Title").text
            assert title.startswith(bcf.TITLE_PREFIX)
            assert "not approval" in root.find("Topic/Description").text
        vps = [x for x in names if x.endswith("viewpoint.bcfv")]
        guids = {ET.fromstring(z.read(v)).find("Components/Selection/Component").get("IfcGuid") for v in vps}
        subject_guids = {r["metadata"]["subject"]["anchor"]["ifc_guid"] for r in rep["records"] if r["metadata"]["result_state"] in ("fail", "unknown")}
        assert guids == subject_guids
