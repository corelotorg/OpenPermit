# SPDX-License-Identifier: Apache-2.0
"""Command line for ORI plan takeoff (DRAFT 0.1). Run from verification/.

  python -m ori_takeoff.cli extract PLAN.pdf|PLAN.dxf --out overlay.json [--preview-dir DIR] [--no-lineweight]
  python -m ori_takeoff.cli evaluate GROUND_TRUTH.json OVERLAY.json --out accuracy.json
  python -m ori_takeoff.cli ifc OVERLAY.json --out model.ifc [--check report.json]
  python -m ori_takeoff.cli export OVERLAY.json --coco coco.json --geojson-dir DIR
  python -m ori_takeoff.cli gate OVERLAY.json          # exit 1 if the overlay may not enter the training set
  python -m ori_takeoff.cli sample OUTDIR              # write the CC0 sample plan, DXF and ground truth

Every output is reviewer evidence and candidate training data, not approval.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import EVIDENCE_LABEL
from . import detect as D
from . import evaluate as E
from . import extract as X
from . import overlay as ov
from . import preview as P
from . import sample_plan as S
from . import to_ifc as T


def _load(p):
    return json.loads(Path(p).read_text())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ori_takeoff", description=f"ORI plan takeoff. {EVIDENCE_LABEL}.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("extract"); a.add_argument("plan"); a.add_argument("--out", required=True)
    a.add_argument("--preview-dir"); a.add_argument("--no-lineweight", action="store_true"); a.add_argument("--license-record")
    e = sub.add_parser("evaluate"); e.add_argument("gt"); e.add_argument("overlay"); e.add_argument("--out", required=True)
    i = sub.add_parser("ifc"); i.add_argument("overlay"); i.add_argument("--out", required=True); i.add_argument("--check")
    x = sub.add_parser("export"); x.add_argument("overlay"); x.add_argument("--coco"); x.add_argument("--geojson-dir")
    g = sub.add_parser("gate"); g.add_argument("overlay"); g.add_argument("--allow-unreviewed", action="store_true")
    s = sub.add_parser("sample"); s.add_argument("outdir")
    ns = ap.parse_args(argv)
    if ns.cmd == "extract":
        params = D.Params(use_lineweight=not ns.no_lineweight)
        lic = _load(ns.license_record) if ns.license_record else None
        fn = X.extract_dxf if ns.plan.lower().endswith(".dxf") else X.extract_pdf
        doc = fn(ns.plan, params, lic)
        errs = ov.schema_errors(doc)
        Path(ns.out).write_text(ov.dumps(doc))
        print(f"{EVIDENCE_LABEL}: {len(doc['pages'])} page(s) -> {ns.out}; schema errors: {len(errs)}")
        if ns.preview_dir:
            d = Path(ns.preview_dir); d.mkdir(parents=True, exist_ok=True)
            for pg in doc["pages"]:
                if pg["status"] == "needs_tracing":
                    continue
                stem = f"{Path(ns.plan).stem}-p{pg['page']}"
                P.write_png(pg, d / f"{stem}.overlay.png", ns.plan if fn is X.extract_pdf else None)
                P.write_svg(pg, d / f"{stem}.overlay.svg")
                if fn is X.extract_pdf:  # uncropped page render for the markup editor background
                    P.render_pdf_page(ns.plan, pg["page"], 100).save(d / f"{stem}.page.png")
        return 1 if errs else 0
    if ns.cmd == "evaluate":
        r = E.compare(_load(ns.gt), _load(ns.overlay))
        Path(ns.out).write_text(json.dumps(r, indent=1) + "\n")
        print(f"accuracy -> {ns.out}")
        return 0
    if ns.cmd == "ifc":
        summ = T.overlay_to_ifc(_load(ns.overlay), ns.out)
        print(json.dumps(summ))
        if ns.check:
            rep = T.check_ifc(ns.out)
            Path(ns.check).write_text(json.dumps(rep, indent=1) + "\n")
            print(f"{EVIDENCE_LABEL}: {rep['counts']}; schema issues {rep['schema_validation']['issues']} -> {ns.check}")
        return 0
    if ns.cmd == "export":
        doc = _load(ns.overlay)
        if ns.coco:
            Path(ns.coco).write_text(json.dumps(ov.to_coco(doc)) + "\n")
        if ns.geojson_dir:
            d = Path(ns.geojson_dir); d.mkdir(parents=True, exist_ok=True)
            for pg in doc["pages"]:
                (d / f"p{pg['page']}.geojson").write_text(json.dumps(ov.to_geojson(doc, pg["page"])) + "\n")
        return 0
    if ns.cmd == "gate":
        errs = ov.training_gate_errors(_load(ns.overlay), allow_unreviewed=ns.allow_unreviewed)
        print("ADMIT to training set" if not errs else "REFUSE:\n  " + "\n  ".join(errs[:30]))
        return 0 if not errs else 1
    for k, v in S.build_all(ns.outdir).items():
        print(k, v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
