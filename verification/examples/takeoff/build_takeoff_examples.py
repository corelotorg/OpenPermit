# SPDX-License-Identifier: Apache-2.0
"""Regenerate the plan-takeoff examples in this folder (run from anywhere).

Writes the ORI-authored CC0 sample plan (clean PDF, a PDF with export noise, two DXF floors), the
ground-truth overlays, extracted overlays, previews, accuracy report, IFC 4.3 exports with ORI
check reports, and COCO / GeoJSON exports of the ground truth. Everything is synthetic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from ori_takeoff import detect as D  # noqa: E402
from ori_takeoff import evaluate as E  # noqa: E402
from ori_takeoff import extract as X  # noqa: E402
from ori_takeoff import overlay as ov  # noqa: E402
from ori_takeoff import preview as P  # noqa: E402
from ori_takeoff import sample_plan as S  # noqa: E402
from ori_takeoff import to_ifc as T  # noqa: E402

FIXED = "2026-10-03T00:00:00Z"


def _w(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1) + "\n")


def build(out: Path = HERE) -> dict:
    o = S.build_all(out)
    lic = S.license_record()
    runs = {
        "pdf_clean": (X.extract_pdf, o["pdf"], o["gt_pdf"], D.Params()),
        "pdf_clean_geometry_only": (X.extract_pdf, o["pdf"], o["gt_pdf"], D.Params(use_lineweight=False)),
        "pdf_noisy": (X.extract_pdf, o["pdf_noisy"], o["gt_pdf_noisy"], D.Params()),
        "pdf_noisy_geometry_only": (X.extract_pdf, o["pdf_noisy"], o["gt_pdf_noisy"], D.Params(use_lineweight=False)),
        "dxf_A-101": (X.extract_dxf, o["dxf_A-101"], o["gt_dxf_A-101"], D.Params()),
        "dxf_A-102": (X.extract_dxf, o["dxf_A-102"], o["gt_dxf_A-102"], D.Params()),
    }
    acc = {"report": "ori-plan-overlay-accuracy-0.1", "label": "Measured on ORI's own synthetic sample only; not a general accuracy claim.",
           "runs": {}}
    docs = {}
    for name, (fn, src, gt, params) in runs.items():
        doc = fn(src, params, lic, created_at=FIXED)
        docs[name] = doc
        if name in ("pdf_clean", "pdf_noisy", "dxf_A-101", "dxf_A-102"):
            ov_path = out / f"{Path(src).name}.overlay.json"
            ov_path.write_text(ov.dumps(doc))
        acc["runs"][name] = E.compare(json.loads(Path(gt).read_text()), doc)
    _w(out / "accuracy-sample.json", acc)
    clean = docs["pdf_clean"]
    for pg in clean["pages"]:
        P.write_png(pg, out / f"ori-sample-house-p{pg['page']}.overlay.png", o["pdf"], dpi=100)
        P.write_svg(pg, out / f"ori-sample-house-p{pg['page']}.overlay.svg")
    P.write_png(docs["dxf_A-102"]["pages"][0], out / "ori-sample-house-A-102.dxf.overlay.png")
    _w(out / "takeoff-sample.json", {"label": "Takeoff from auto-extracted, unreviewed elements (clean PDF).",
                                      "pages": {pg["page_label"]: pg["takeoff"] for pg in clean["pages"]}})
    gt = json.loads(o["gt_pdf"].read_text())
    summ = {"groundtruth": T.overlay_to_ifc(gt, out / "ori-sample-house.groundtruth.ifc"),
            "extracted": T.overlay_to_ifc(clean, out / "ori-sample-house.extracted.ifc")}
    for k in ("groundtruth", "extracted"):
        rep = T.check_ifc(out / f"ori-sample-house.{k}.ifc")
        rep["export_summary"] = summ[k]
        _w(out / f"ori-sample-house.{k}.ifc-check.json", rep)
    _w(out / "ori-sample-house.groundtruth.coco.json", ov.to_coco(gt, image_names={1: "ori-sample-house-p1.png", 2: "ori-sample-house-p2.png"}))
    _w(out / "ori-sample-house.groundtruth.p1.geojson", ov.to_geojson(gt, 1))
    return {"outputs": o, "accuracy": acc}


if __name__ == "__main__":
    r = build()
    for name, run in r["accuracy"]["runs"].items():
        for p in run["pages"]:
            print(name, p["page_label"], "walls R/P", p["walls"]["length_recall"], p["walls"]["length_precision"],
                  "openings F1", p["openings"]["located_and_class_correct"]["f1"], "spaces F1", p["spaces"]["f1"],
                  "stairs F1", p["stairs"]["f1"], "dims F1", p["dimensions"]["f1"])
