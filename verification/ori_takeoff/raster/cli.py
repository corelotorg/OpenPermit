# SPDX-License-Identifier: Apache-2.0
"""Raster track command line (DRAFT 0.1). Run from verification/.

  python -m ori_takeoff.raster.cli recognise IMAGE --dpi 200 --out rec.json
  python -m ori_takeoff.raster.cli benchmark --out examples/takeoff/raster-accuracy-sample.json

Output is reviewer evidence only. Every recognised item is
ai_extracted_unverified with value status unknown.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import VERSION
from . import degrade as G
from . import evaluate as E
from . import recognise as R

HERE = Path(__file__).resolve().parents[2]
SAMPLE = HERE / "examples" / "takeoff" / "ori-sample-house.pdf"
GT = HERE / "examples" / "takeoff" / "ori-sample-house.pdf.groundtruth.overlay.json"


def benchmark(pages=(0, 1), levels=None) -> dict:
    gt = json.loads(GT.read_text())
    runs = {}
    for d in levels or G.LEVELS:
        per = []
        for pi in pages:
            s = G.make_scan(SAMPLE, pi, d)
            rec = R.recognise(s["image"], s["dpi"])
            sc = E.score(gt["pages"][pi], rec, s["page_to_px"].tolist())
            sc["page"] = pi + 1
            sc["skew_deg"]["true"] = d.skew_deg
            per.append(sc)
        runs[d.name] = {"degradation": G.asdict(d), "pages": per}
    return {"report": "ori-scan-accuracy-0.1", "license": "CC0-1.0", "tool": f"ori_takeoff.raster {VERSION}",
            "label": "Measured on ORI's own synthetic CC0 sample, rasterised and degraded by ORI; "
                     "not a general accuracy claim and not tested on any real scanned plan.",
            "engines": {"tesseract": _tess_version(), "opencv": _cv_version()},
            "sample": SAMPLE.name, "runs": runs}


def _tess_version():
    try:
        import pytesseract
        return str(pytesseract.get_tesseract_version())
    except Exception:  # pragma: no cover
        return None


def _cv_version():
    import cv2
    return cv2.__version__


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ori_takeoff.raster")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("recognise")
    a.add_argument("image")
    a.add_argument("--dpi", type=int, required=True, help="resolution the scanner declared")
    a.add_argument("--out", required=True)
    b = sub.add_parser("benchmark")
    b.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "recognise":
        import cv2
        img = cv2.imread(args.image, cv2.IMREAD_GRAYSCALE)
        if img is None:
            ap.error(f"cannot read image {args.image}")
        res = R.recognise(img, args.dpi)
    else:
        res = benchmark()
    Path(args.out).write_text(json.dumps(res, indent=1) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
