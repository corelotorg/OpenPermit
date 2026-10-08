# SPDX-License-Identifier: Apache-2.0
"""Plan takeoff (ori_takeoff, DRAFT 0.1): units, scale, extraction accuracy on the CC0 sample,
raster handling, licensing gate, exports, IFC export and ORI checks."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from ori_takeoff import detect as D
from ori_takeoff import evaluate as E
from ori_takeoff import extract as X
from ori_takeoff import overlay as ov
from ori_takeoff import preview as P
from ori_takeoff import sample_plan as S
from ori_takeoff import to_ifc as T
from ori_takeoff import units as U

EX = Path(__file__).resolve().parents[1] / "examples" / "takeoff"


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    return S.build_all(tmp_path_factory.mktemp("takeoff"))


def _gt(sample, key):
    return json.loads(Path(sample[key]).read_text())


# -- units and scale -------------------------------------------------------------
@pytest.mark.parametrize("text,inches", [("32'-0\"", 384), ("17'-2 1/4\"", 206.25), ("14'-9 3/4\"", 177.75), ("12' 6\"", 150),
                                         ("9'", 108), ("10 1/2\"", 10.5), ("8\u20329\u2033", 105)])
def test_parse_ft_in(text, inches):
    assert U.parse_ft_in(text) == pytest.approx(inches)


def test_parse_ft_in_rejects_non_dimensions():
    assert U.parse_ft_in("UP 14R") is None
    assert U.parse_ft_in("A-101") is None
    assert U.find_ft_in("16'-6\" X 10'-1 1/2\"") == [198.0, 121.5]


@pytest.mark.parametrize("note,val", [("SCALE: 1/4\" = 1'-0\"", 48.0), ("1/8\"=1'-0\"", 96.0), ("3/16\" = 1'-0\"", 64.0),
                                      ("SCALE 1:50", 50.0), ("SCALE: NTS", "not_to_scale"), ("FIRST FLOOR PLAN", None)])
def test_parse_scale_note(note, val):
    assert U.parse_scale_note(note) == (pytest.approx(val) if isinstance(val, float) else val)


def test_format_round_trip():
    for v in (384, 206.25, 121.5, 0.5, 105):
        assert U.parse_ft_in(U.format_ft_in(v)) == pytest.approx(v)


def test_scale_states(tmp_path):
    fl = S.floors()[:1]
    cases = {
        "stated_confirmed": S.write_pdf(tmp_path / "a.pdf", fl),
        "stated": S.write_pdf(tmp_path / "b.pdf", fl, draw_dims=False),
        "calibrated": S.write_pdf(tmp_path / "c.pdf", fl, scale_note=None),
        "conflict": S.write_pdf(tmp_path / "d.pdf", fl, scale_note="SCALE: 1/8\" = 1'-0\""),
        "unknown": S.write_pdf(tmp_path / "e.pdf", fl, scale_note=None, draw_dims=False),
        "not_to_scale": S.write_pdf(tmp_path / "f.pdf", fl, scale_note="SCALE: NTS", draw_dims=False),
    }
    for status, pdf in cases.items():
        doc = X.extract_pdf(pdf)
        pg = doc["pages"][0]
        assert pg["scale"]["status"] == status, (status, pg["scale"])
        assert ov.schema_errors(doc) == []
        if status in ("conflict", "unknown", "not_to_scale"):
            # unknown scale stays unknown: no real-world geometry or totals anywhere
            assert pg["scale"]["real_in_per_page_unit"] is None
            assert all(e["geometry_real"] is None for e in pg["elements"])
            assert pg["takeoff"]["walls"]["total_length_in"] is None
            assert pg["takeoff"]["spaces"]["total_net_area_ft2"] is None
        else:
            assert pg["scale"]["real_in_per_page_unit"] == pytest.approx(2 / 3, rel=1e-3)


def test_unknown_scale_still_finds_walls_and_rooms_in_page_units(tmp_path):
    doc = X.extract_pdf(S.write_pdf(tmp_path / "e.pdf", S.floors()[:1], scale_note=None, draw_dims=False))
    pg = doc["pages"][0]
    assert sum(e["ifc_class"] == "IfcWall" for e in pg["elements"]) == 8
    assert sum(e["ifc_class"] == "IfcSpace" for e in pg["elements"]) == 5


# -- sample plan and ground truth ---------------------------------------------------
def test_sample_pdf_is_deterministic_and_matches_committed_example(sample):
    h = hashlib.sha256(Path(sample["pdf"]).read_bytes()).hexdigest()
    assert h == hashlib.sha256((EX / "ori-sample-house.pdf").read_bytes()).hexdigest()
    assert hashlib.sha256(Path(sample["pdf_noisy"]).read_bytes()).hexdigest() == \
        hashlib.sha256((EX / "ori-sample-house-noisy.pdf").read_bytes()).hexdigest()


def test_ground_truth_is_valid_and_admitted_by_training_gate(sample):
    for key in ("gt_pdf", "gt_pdf_noisy", "gt_dxf_A-101", "gt_dxf_A-102"):
        doc = _gt(sample, key)
        assert ov.schema_errors(doc) == []
        assert ov.training_gate_errors(doc) == []
    gt = _gt(sample, "gt_pdf")
    p1 = gt["pages"][0]
    count = lambda c: sum(e["ifc_class"] == c for e in p1["elements"])  # noqa: E731
    assert (count("IfcWall"), count("IfcDoor"), count("IfcWindow"), count("IfcSpace"), count("IfcStair")) == (8, 7, 7, 5, 1)
    assert sum(e["properties"]["area_ft2"] for e in p1["elements"] if e["ifc_class"] == "IfcSpace") == pytest.approx(811.03125)


def test_committed_overlays_validate():
    for p in sorted(EX.glob("*.overlay.json")):
        assert ov.schema_errors(json.loads(p.read_text())) == [], p.name


# -- extraction accuracy on the sample (measured, not assumed) --------------------
def _check_perfect(page, width_tol=0.01):
    assert page["walls"]["length_recall"] == 1.0 and page["walls"]["length_precision"] == 1.0
    assert page["openings"]["located_and_class_correct"]["f1"] == 1.0
    assert page["openings"]["width_error_in"]["max_abs"] <= width_tol
    assert page["spaces"]["f1"] == 1.0 and page["spaces"]["label_correct"] == page["spaces"]["gt"]
    assert page["spaces"]["area_rel_error_max"] < 1e-4
    assert page["stairs"]["riser_count_correct"] == 1 and page["stairs"]["tread_count_correct"] == 1
    assert page["dimensions"]["value_correct"] == page["dimensions"]["gt"]


@pytest.mark.parametrize("pdf,gt", [("pdf", "gt_pdf"), ("pdf_noisy", "gt_pdf_noisy")])
def test_pdf_extraction_against_ground_truth(sample, pdf, gt):
    doc = X.extract_pdf(sample[pdf])
    assert ov.schema_errors(doc) == []
    rep = E.compare(_gt(sample, gt), doc)
    assert len(rep["pages"]) == 2
    for page in rep["pages"]:
        assert page["scale_status"] == "stated_confirmed"
        # export noise trims outline ends by up to 0.4 in on each side of an opening
        _check_perfect(page, width_tol=0.01 if pdf == "pdf" else 0.8)


@pytest.mark.parametrize("sheet", ["A-101", "A-102"])
def test_dxf_extraction_against_ground_truth(sample, sheet):
    doc = X.extract_dxf(sample[f"dxf_{sheet}"])
    assert doc["pages"][0]["scale"]["status"] == "drawing_units"
    rep = E.compare(_gt(sample, f"gt_dxf_{sheet}"), doc)
    _check_perfect(rep["pages"][0])


def test_geometry_only_mode_is_worse_and_reported(sample):
    """Without line weight, fixtures, glazing and treads pair up as walls; the evaluation must show it."""
    rep = E.compare(_gt(sample, "gt_pdf"), X.extract_pdf(sample["pdf"], D.Params(use_lineweight=False)))
    p = rep["pages"][0]
    assert p["walls"]["length_precision"] < 0.95
    assert p["spaces"]["f1"] < 1.0


def test_extracted_takeoff_quantities(sample):
    t = X.extract_pdf(sample["pdf"])["pages"][0]["takeoff"]
    assert t["walls"]["count"] == 8
    assert t["walls"]["total_length_in"] == pytest.approx(2247.0, abs=0.5)
    assert t["walls"]["exterior_length_in"] == pytest.approx(1416.0, abs=0.5)
    assert t["doors"]["count"] == 7 and t["windows"]["count"] == 7
    assert t["gross_footprint_ft2"] == pytest.approx(896.0, abs=0.1)
    assert t["stairs"][0]["riser_count"] == 14 and t["stairs"][0]["tread_count"] == 13
    assert t["stairs"][0]["tread_depth_in"] == pytest.approx(10.0, abs=0.05)
    assert t["stairs"][0]["riser_height_in"] is None  # not measurable on a plan


def test_every_extracted_element_is_auto_and_unreviewed(sample):
    doc = X.extract_pdf(sample["pdf"])
    for pg in doc["pages"]:
        for e in pg["elements"]:
            assert e["provenance"]["method"] == "auto_extracted"
            assert e["provenance"]["review_status"] == "unreviewed"
            assert 0 <= e["provenance"]["confidence"] <= 1


# -- raster pages -------------------------------------------------------------
def test_raster_page_needs_tracing(tmp_path):
    from PIL import Image, ImageDraw
    from reportlab.pdfgen import canvas
    img = Image.new("L", (600, 400), 255)
    ImageDraw.Draw(img).rectangle([50, 50, 550, 350], outline=0, width=6)
    img.save(tmp_path / "scan.png")
    c = canvas.Canvas(str(tmp_path / "scan.pdf"), pagesize=(792, 612), invariant=1)
    c.drawImage(str(tmp_path / "scan.png"), 36, 36, 720, 540)
    c.showPage()
    c.save()
    doc = X.extract_pdf(tmp_path / "scan.pdf")
    pg = doc["pages"][0]
    assert pg["kind"] == "raster" and pg["status"] == "needs_tracing" and pg["elements"] == []
    assert ov.schema_errors(doc) == []
    assert any("needs tracing" in e for e in ov.training_gate_errors(doc))


# -- licensing gate --------------------------------------------------------------
def test_gate_refuses_unlicensed_extraction(sample):
    errs = ov.training_gate_errors(X.extract_pdf(sample["pdf"]))
    assert any("license_url" in e for e in errs)
    assert any("not reviewed" in e for e in errs)


def test_gate_refuses_nc_nd_tampered_and_unconfirmed(sample):
    gt = _gt(sample, "gt_pdf")
    for lic in ("CC-BY-NC-4.0", "CC-BY-ND-4.0", "CC-BY-NC-SA-4.0"):
        d = copy.deepcopy(gt)
        d["license_record"]["license_id"] = lic
        assert any("not a training-set license" in e for e in ov.training_gate_errors(d))
    d = copy.deepcopy(gt)
    d["license_record"]["license_sha256"] = "0" * 64
    assert any("does not match" in e for e in ov.training_gate_errors(d))
    d = copy.deepcopy(gt)
    d["license_record"]["license_confirmed"] = False
    assert any("not confirmed" in e for e in ov.training_gate_errors(d))
    d = copy.deepcopy(gt)
    d["license_record"]["source_citation"].pop("archive_url")
    assert any("archive_url" in e for e in ov.training_gate_errors(d))
    with pytest.raises(ValueError):
        ov.require_training_ok(d)


def test_reviewed_extraction_with_license_is_admitted(sample):
    doc = X.extract_pdf(sample["pdf"], license_record=S.license_record())
    assert any("not reviewed" in e for e in ov.training_gate_errors(doc))
    for pg in doc["pages"]:
        for e in pg["elements"]:
            e["provenance"].update(review_status="confirmed", by="reviewer:test", at="2026-10-03T00:00:00Z")
    assert ov.training_gate_errors(doc) == []
    assert ov.schema_errors(doc) == []


def test_schema_rejects_training_role_without_allowed_use(sample):
    doc = X.extract_pdf(sample["pdf"])
    doc["dataset_role"] = "training"
    assert any("training_use" in e for e in ov.schema_errors(doc))


# -- exports ------------------------------------------------------------------
def test_coco_and_geojson_exports(sample):
    gt = _gt(sample, "gt_pdf")
    coco = ov.to_coco(gt)
    assert [c["name"] for c in coco["categories"]][:3] == ["IfcWall", "IfcDoor", "IfcWindow"]
    assert len(coco["images"]) == 2 and coco["licenses"][0]["name"] == "CC0-1.0"
    walls = [a for a in coco["annotations"] if a["category_id"] == 1]
    assert len(walls) == 16 and all("segmentation" in a for a in walls)
    assert all(0 <= a["bbox"][0] <= coco["images"][0]["width"] for a in coco["annotations"])
    gj = ov.to_geojson(gt, 1)
    assert gj["type"] == "FeatureCollection" and gj["units"] == "in"
    assert sum(f["properties"]["ifc_class"] == "IfcSpace" for f in gj["features"]) == 5


def test_previews(sample, tmp_path):
    doc = X.extract_pdf(sample["pdf"])
    png = P.write_png(doc["pages"][0], tmp_path / "p1.png", sample["pdf"])
    svg = P.write_svg(doc["pages"][0], tmp_path / "p1.svg")
    assert png.stat().st_size > 10_000 and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert "<svg" in svg.read_text() and "IfcSpace" in svg.read_text()


# -- IFC export and ORI checks -------------------------------------------------------
def test_ground_truth_ifc_export_and_checks(sample, tmp_path):
    gt = _gt(sample, "gt_pdf")
    summ = T.overlay_to_ifc(gt, tmp_path / "gt.ifc")
    assert summ["counts"]["IfcWall"] == 16 and summ["counts"]["IfcSpace"] == 10
    assert summ["counts"]["IfcDoor"] == 11 and summ["counts"]["IfcWindow"] == 15
    assert [s["elevation_in"] for s in summ["storeys"]] == [0.0, 105.0]
    rep = T.check_ifc(tmp_path / "gt.ifc")
    assert rep["schema_validation"]["issues"] == 0
    assert rep["counts"]["fail"] == 0 and rep["counts"]["unknown"] == 0
    assert rep["is_approval"] is False


def test_extracted_ifc_checks_stay_unknown_until_confirmed(sample, tmp_path):
    doc = X.extract_pdf(sample["pdf"])
    summ = T.overlay_to_ifc(doc, tmp_path / "ex.ifc")
    assert "page 1: space height" in summ["placeholders"]
    rep = T.check_ifc(tmp_path / "ex.ifc")
    assert rep["counts"]["fail"] == 0 and rep["counts"]["pass"] == 0 and rep["counts"]["unknown"] > 0
    assert any("placeholder height" in a for a in rep["takeoff_adjustments"])
    reasons = {r["metadata"].get("reason_code") for r in rep["records"]}
    assert reasons <= {"unconfirmed_extraction", "missing_information"}


def test_unknown_scale_pages_are_not_exported_to_ifc(tmp_path):
    doc = X.extract_pdf(S.write_pdf(tmp_path / "e.pdf", S.floors()[:1], scale_note=None, draw_dims=False))
    summ = T.overlay_to_ifc(doc, tmp_path / "e.ifc")
    assert summ["storeys"] == [] and summ["skipped_pages"][0]["page"] == 1


def test_cli_round_trip(sample, tmp_path):
    from ori_takeoff import cli
    out = tmp_path / "x.overlay.json"
    assert cli.main(["extract", str(sample["pdf"]), "--out", str(out), "--preview-dir", str(tmp_path / "prev")]) == 0
    assert (tmp_path / "prev" / "ori-sample-house-p1.overlay.png").exists()
    assert (tmp_path / "prev" / "ori-sample-house-p1.page.png").exists()
    assert cli.main(["gate", str(out)]) == 1  # no license record, unreviewed
    assert cli.main(["gate", str(sample["gt_pdf"])]) == 0
    assert cli.main(["ifc", str(out), "--out", str(tmp_path / "x.ifc"), "--check", str(tmp_path / "c.json")]) == 0
    assert cli.main(["export", str(sample["gt_pdf"]), "--coco", str(tmp_path / "c.coco.json"), "--geojson-dir", str(tmp_path / "gj")]) == 0
    assert (tmp_path / "gj" / "p2.geojson").exists()


def test_editor_is_static_and_dependency_free():
    html = (Path(__file__).resolve().parents[1] / "ori_takeoff" / "editor" / "index.html").read_text()
    assert "<script src" not in html and "http://" not in html.replace("http://www.w3.org", "")
    assert "human_corrected" in html and "human_traced" in html and "derived_from" in html
