# SPDX-License-Identifier: Apache-2.0
"""Committed examples must be reproducible from code and committed inputs."""

import importlib.util
import json

import pytest

from conftest import FIXED_TIME, VERIFICATION
from ori_verify import bcf, cli, pdf_manifest
from ori_verify.records import dumps
from ori_verify.synthetic_pdf import make_text_pdf

EX = VERIFICATION / "examples"
_spec = importlib.util.spec_from_file_location("build_examples", EX / "build_examples.py")
build_examples = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_examples)


@pytest.mark.parametrize("name", ["pass", "fail", "incomplete"])
def test_ifc_reports_reproduce(name):
    report = cli.run_ifc(EX / "ifc" / f"ori-ch03-{name}.ifc", executed_at=FIXED_TIME)
    assert dumps(report) == (EX / "reports" / f"ifc-{name}.report.json").read_text()


def test_pdf_examples_reproduce(tmp_path):
    v1 = make_text_pdf(tmp_path / "synthetic-plans-v1.pdf", build_examples.PAGES_V1, pdfa_claim=(2, "B"), page_labels=["A-101", "A-301"])
    assert v1.read_bytes() == (EX / "pdf" / "synthetic-plans-v1.pdf").read_bytes()
    m1 = pdf_manifest.build_manifest([EX / "pdf" / "synthetic-plans-v1.pdf"], "synthetic-demo-plans", 1, "applicant:synthetic-demo", FIXED_TIME)
    assert m1 == json.loads((EX / "pdf" / "manifest-v1.json").read_text())
    doc = json.loads((EX / "declared" / "declared-values-v1.json").read_text())
    assert dumps(cli.run_declared(doc, m1, executed_at=FIXED_TIME)) == (EX / "reports" / "declared-v1.report.json").read_text()


def test_committed_bcf_matches_report(tmp_path):
    report = json.loads((EX / "reports" / "ifc-fail.report.json").read_text())
    _, n = bcf.write_bcf(report, tmp_path / "x.bcf")
    assert n == report["counts"]["fail"] + report["counts"]["unknown"]
    assert (tmp_path / "x.bcf").stat().st_size > 0
