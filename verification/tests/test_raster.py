# SPDX-License-Identifier: Apache-2.0
"""Raster / scanned-plan track (DRAFT 0.1): separation, labelling and a measured floor."""
import ast
import json
import shutil
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("pytesseract")
pytest.importorskip("pypdfium2")
if shutil.which("tesseract") is None:
    pytest.skip("tesseract binary not installed", allow_module_level=True)

from ori_takeoff.raster import ORIGIN, VALUE_STATUS, degrade as G, evaluate as E, recognise as R  # noqa: E402
from ori_takeoff.raster.cli import GT, SAMPLE  # noqa: E402

RASTER_DIR = Path(__file__).resolve().parents[1] / "ori_takeoff" / "raster"


def test_raster_track_does_not_import_ifc_or_validators():
    for f in RASTER_DIR.glob("*.py"):
        tree = ast.parse(f.read_text())
        mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not any(m.startswith(("ifcopenshell", "ori_verify")) or m.endswith("to_ifc") for m in mods), f.name


def test_ocr_dimension_parse_is_lenient_on_marks_only():
    assert R.parse_ocr_dimension("17'-2 1/4\u00b0") == 206.25
    assert R.parse_ocr_dimension("32'-0\u201d") == 384.0
    assert R.parse_ocr_dimension("10-\u00a7 1/2\u00b0") is None  # never guess a digit
    assert R.parse_ocr_dimension("LIVING") is None
    assert R.parse_ocr_dimension("5'-14\"") is None


def test_degrade_transform_maps_page_points():
    d = G.Degradation("t", dpi=100, skew_deg=2.0, seed=0)
    s = G.make_scan(SAMPLE, 0, d)
    M = s["page_to_px"]
    h, w = s["image"].shape
    x, y = E._apply(M, (0.0, 0.0))  # page lower-left is near image bottom-left
    assert -60 < x < 60 and h - 60 < y < h + 60
    # the round trip through the inverse is exact
    back = E._apply(E._inv(M), E._apply(M, (500.0, 400.0)))
    assert abs(back[0] - 500) < 1e-6 and abs(back[1] - 400) < 1e-6


def test_skew_is_estimated():
    s = G.make_scan(SAMPLE, 0, G.Degradation("t", dpi=150, skew_deg=-3.0, noise_sigma=8, seed=5))
    assert abs(R.estimate_skew(s["image"]) - (-3.0)) < 0.2


def test_clean_scan_recognition_floor_and_labelling():
    gt = json.loads(GT.read_text())
    s = G.make_scan(SAMPLE, 0, G.LEVELS[0])
    rec = R.recognise(s["image"], s["dpi"])
    assert rec["items"] and all(i["origin"] == ORIGIN and i["value_status"] == VALUE_STATUS for i in rec["items"])
    assert rec["scale"]["status"] in ("ocr_scale_note_unconfirmed", "unknown")
    sc = E.score(gt["pages"][0], rec, s["page_to_px"].tolist())
    # floors set below the recorded benchmark; they guard against regressions, not claim accuracy
    assert sc["walls"]["length_recall"] >= 0.95
    assert sc["walls"]["length_precision"] >= 0.95
    assert sc["dimensions"]["value_exact"] >= 5
    assert sc["room_labels"]["found"] >= 3


def test_recorded_benchmark_is_labelled():
    p = GT.parent / "raster-accuracy-sample.json"
    d = json.loads(p.read_text())
    assert "not a general accuracy claim" in d["label"]
    assert set(d["runs"]) == {lv.name for lv in G.LEVELS}
