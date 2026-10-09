#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Regenerate the committed examples under verification/examples/.

Synthetic models and documents only; they describe no real building and are
not a pilot. Outputs are reviewer evidence, not approval.

IFC files carry creation timestamps, so they are written only when missing
(pass --regen-ifc to rebuild them). Reports are always rebuilt from the
committed IFC files with a fixed executed_at, so they are reproducible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from ori_verify import bcf, cli, ifc_fixtures, pdf_extract, pdf_manifest  # noqa: E402
from ori_verify.records import dumps  # noqa: E402
from ori_verify.synthetic_pdf import make_text_pdf  # noqa: E402

FIXED_TIME = "2026-09-27T12:00:00Z"
VA = "urn:ori:jurisdiction:us-va"
PAGES_V1 = [
    ["SYNTHETIC EXAMPLE - NOT A REAL PROJECT", "SHEET A-101 FLOOR PLAN", "BEDROOM 1 CLG HT 8'-0\"", "BEDROOM 1 EERO NET CLEAR 24\" W x 36\" H, SILL HT 42\""],
    ["SYNTHETIC EXAMPLE - NOT A REAL PROJECT", "SHEET A-301 STAIR SECTION", "RISER 8\" MAX", "TREAD 9 1/2\"", "HEADROOM 6'-10\""],
]
PAGES_V2 = [PAGES_V1[0], ["SYNTHETIC EXAMPLE - NOT A REAL PROJECT", "SHEET A-301 STAIR SECTION REV 1", "RISER 8 1/2\" MAX", "TREAD 9 1/2\"", "HEADROOM 6'-10\""]]


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def declared_pass(aid: str) -> dict:
    a = lambda page, sheet, detail=None: {"artifact_id": aid, "page": page, "sheet": sheet, **({"detail": detail} if detail else {})}
    return {
        "declared_values_profile": "ori-declared-values-0.1",
        "submission_id": "synthetic-demo-1",
        "jurisdiction": VA,
        "declared_by": "applicant:synthetic-demo",
        "declared_at": FIXED_TIME,
        "plan_set": {"plan_set_id": "synthetic-demo-plans", "version": 1, "artifact_ids": [aid]},
        "legal_boundary": "Applicant-declared values are evidence for review. They are not verified facts and not approval.",
        "stairs": [{"id": "s1", "label": "Main stair flight 1",
                    "riser_heights_in": {"value": [8.0] * 13, "anchor": a(2, "A-301", "stair section riser callout")},
                    "tread_depths_in": {"value": [9.5] * 12, "anchor": a(2, "A-301", "stair section tread callout")},
                    "min_headroom_in": {"value": 82.0, "anchor": a(2, "A-301", "headroom dimension")}}],
        "spaces": [{"id": "b1", "label": "Bedroom 1", "use": {"value": "habitable", "anchor": a(1, "A-101")},
                    "ceiling_height_in": {"value": 96.0, "anchor": a(1, "A-101")}, "floor_area_ft2": {"value": 110.0, "anchor": a(1, "A-101")},
                    "sloped_ceiling": {"value": False, "anchor": a(1, "A-101")}}],
        "eeros": [{"id": "w1", "label": "Bedroom 1 EERO", "net_clear_height_in": {"value": 36.0, "anchor": a(1, "A-101")},
                   "net_clear_width_in": {"value": 24.0, "anchor": a(1, "A-101")},
                   "grade_floor_or_below_grade": {"value": False, "anchor": a(1, "A-101")},
                   "sill_height_in": {"value": 42.0, "anchor": a(1, "A-101")}}],
    }


def main(regen_ifc: bool = False) -> None:
    ifc_dir, rep_dir, pdf_dir, dec_dir = HERE / "ifc", HERE / "reports", HERE / "pdf", HERE / "declared"
    for d in (ifc_dir, rep_dir, pdf_dir, dec_dir):
        d.mkdir(parents=True, exist_ok=True)
    specs = {"pass": ifc_fixtures.passing_spec(), "fail": ifc_fixtures.failing_spec(), "incomplete": ifc_fixtures.incomplete_spec()}
    for name, spec in specs.items():
        p = ifc_dir / f"ori-ch03-{name}.ifc"
        if regen_ifc or not p.exists():
            ifc_fixtures.write_fixture(spec, p)
        report = cli.run_ifc(p, executed_at=FIXED_TIME)
        report["artifact"]["filename"] = p.name
        (rep_dir / f"ifc-{name}.report.json").write_text(dumps(report), encoding="utf-8")
    bcf.write_bcf(json.loads((rep_dir / "ifc-fail.report.json").read_text()), rep_dir / "ifc-fail.bcf")

    v1 = make_text_pdf(pdf_dir / "synthetic-plans-v1.pdf", PAGES_V1, pdfa_claim=(2, "B"), page_labels=["A-101", "A-301"])
    v2 = make_text_pdf(pdf_dir / "synthetic-plans-v2.pdf", PAGES_V2, page_labels=["A-101", "A-301"])
    m1 = pdf_manifest.build_manifest([v1], "synthetic-demo-plans", 1, "applicant:synthetic-demo", FIXED_TIME)
    m2 = pdf_manifest.build_manifest([v2], "synthetic-demo-plans", 2, "applicant:synthetic-demo", FIXED_TIME,
                                     supersedes=[m1["artifacts"][0]["artifact_id"]])
    for m in (m1, m2):
        for a in m["artifacts"]:
            a["filename"] = Path(a["filename"]).name
    write_json(pdf_dir / "manifest-v1.json", m1)
    write_json(pdf_dir / "manifest-v2.json", m2)
    write_json(pdf_dir / "diff-v1-v2.json", pdf_manifest.diff_manifests(m1, m2))

    aid = m1["artifacts"][0]["artifact_id"]
    doc = declared_pass(aid)
    write_json(dec_dir / "declared-values-v1.json", doc)
    (rep_dir / "declared-v1.report.json").write_text(dumps(cli.run_declared(doc, m1, executed_at=FIXED_TIME)), encoding="utf-8")

    callouts = pdf_extract.extract_callouts(v1, aid, m1["artifacts"][0])
    cand = pdf_extract.declared_from_callouts(callouts, submission_id="synthetic-demo-1-extracted", jurisdiction=VA,
                                              declared_by="extractor:ori-vector-text-0.1", declared_at=FIXED_TIME,
                                              plan_set={"plan_set_id": "synthetic-demo-plans", "version": 1, "artifact_ids": [aid]})
    write_json(dec_dir / "extracted-candidates-v1.json", cand)
    (rep_dir / "extracted-v1.report.json").write_text(dumps(cli.run_declared(cand, m1, executed_at=FIXED_TIME)), encoding="utf-8")
    print("examples written to", HERE)


if __name__ == "__main__":
    main(regen_ifc="--regen-ifc" in sys.argv)
