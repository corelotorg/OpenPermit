# SPDX-License-Identifier: Apache-2.0
"""Build, validate, gate and export ``ori-plan-overlay-0.1`` documents.

Coordinates:
* ``geometry_page``: PDF points with the origin at the bottom-left of the media box (the same
  convention as ``region_pt`` anchors in docs/PDF-PATH-0.1-DRAFT.md), or DXF drawing units.
* ``geometry_real``: real-world inches on the drawing plane, measured from the page origin
  (``page * scale.real_in_per_page_unit``). It is ``null`` whenever the page scale is unknown
  or conflicting; a real-world value is never guessed.
Geometry objects are GeoJSON geometry objects (Point, LineString, Polygon).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import EVIDENCE_LABEL, OVERLAY_PROFILE, TOOL_ID, __version__

REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "spec" / "ori-plan-overlay-0.1.schema.json"

IFC_CLASSES = ("IfcWall", "IfcDoor", "IfcWindow", "IfcOpeningElement", "IfcSpace", "IfcStair", "IfcAnnotation")
METHODS = ("authored_ground_truth", "auto_extracted", "human_traced", "human_corrected")
REVIEW = ("unreviewed", "confirmed", "corrected", "rejected")
# Licenses under which an overlay may enter the ORI training set. NonCommercial and NoDerivatives
# terms are excluded: overlays are derived works and the training set must be usable by anyone.
TRAINING_LICENSES = ("CC0-1.0", "PD-US-federal-work", "PD-statement", "CC-BY-4.0", "Apache-2.0",
                     "ORI-written-permission")
LICENSE_REQUIRED = ("license_id", "license_basis", "license_url", "license_local_path", "license_sha256",
                    "license_fetched_at", "license_confirmed", "source_url", "source_citation", "training_use")
CITATION_PARTS = ("author", "title", "year", "publisher", "identifier", "archive_url", "accessed")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _r(v: float) -> float:
    return float(round(float(v), 3))


def _map(coords: Any, f) -> Any:
    if coords and isinstance(coords[0], (int, float)):
        return [_r(c) for c in f(coords[0], coords[1])]
    return [_map(c, f) for c in coords]


def point(x, y) -> dict:
    return {"type": "Point", "coordinates": [_r(x), _r(y)]}


def line(pts) -> dict:
    return {"type": "LineString", "coordinates": [[_r(x), _r(y)] for x, y in pts]}


def polygon(ring, holes=()) -> dict:
    def close(r):
        r = [[_r(x), _r(y)] for x, y in r]
        return r if r[0] == r[-1] else r + [r[0]]
    return {"type": "Polygon", "coordinates": [close(ring)] + [close(h) for h in holes]}


def rect(x0, y0, x1, y1) -> dict:
    return polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def scaled(geometry: dict | None, k: float | None) -> dict | None:
    if geometry is None or k is None:
        return None
    return {"type": geometry["type"], "coordinates": _map(geometry["coordinates"], lambda x, y: (x * k, y * k))}


def provenance(method: str, confidence: float | None = None, rule: str | None = None, by: str | None = None,
               at: str | None = None, review_status: str = "unreviewed", derived_from: str | None = None) -> dict:
    assert method in METHODS and review_status in REVIEW
    return {"method": method, "tool": TOOL_ID if method == "auto_extracted" else f"{TOOL_ID} (editor/authoring)",
            "tool_version": __version__, "confidence": None if confidence is None else _r(confidence), "rule": rule,
            "by": by, "at": at, "review_status": review_status, "derived_from": derived_from}


def element(eid: str, ifc_class: str, geometry_page: dict, k: float | None, prov: dict, properties: dict | None = None,
            axis_page: dict | None = None, name: str | None = None, predefined_type: str | None = None,
            annotation_type: str | None = None, relations: dict | None = None) -> dict:
    assert ifc_class in IFC_CLASSES, ifc_class
    e = {"id": eid, "ifc_class": ifc_class, "predefined_type": predefined_type, "name": name,
         "geometry_page": geometry_page, "geometry_real": scaled(geometry_page, k),
         "properties": properties or {}, "relations": relations or {}, "provenance": prov}
    if axis_page is not None:
        e["axis_page"] = axis_page
        e["axis_real"] = scaled(axis_page, k)
    if ifc_class == "IfcAnnotation":
        e["annotation_type"] = annotation_type or "text_label"
    return e


def scale_block(status: str, k: float | None, stated: dict | None = None, calibration: dict | None = None,
                note: str = "") -> dict:
    """``status``: stated | calibrated | stated_confirmed | drawing_units | conflict | not_to_scale | unknown."""
    usable = status in ("stated", "calibrated", "stated_confirmed", "drawing_units")
    return {"status": status, "real_in_per_page_unit": float(round(k, 9)) if (usable and k) else None,
            "stated": stated, "calibration": calibration, "note": note}


def new_document(source: dict, license_record: dict, created_at: str | None = None, dataset_role: str = "candidate",
                 overlay_id: str | None = None) -> dict:
    return {
        "overlay_profile": OVERLAY_PROFILE,
        "label": EVIDENCE_LABEL,
        "overlay_id": overlay_id or f"urn:ori:overlay:{source['sha256'][:16]}:{TOOL_ID.replace(' ', ':')}",
        "status": "DRAFT",
        "created_at": created_at or now_iso(),
        "tool": {"name": "ori_takeoff", "version": __version__,
                 "dependencies": ["pdfplumber (MIT)", "ezdxf (MIT)", "shapely (BSD-3-Clause)", "ifcopenshell (LGPL-3.0-or-later)"]},
        "source": source,
        "license_record": license_record,
        "dataset_role": dataset_role,
        "pages": [],
        "legal_boundary": ("Overlay elements are proposals for reviewer use and training labels. They are not measurements "
                           "certified by anyone and not approval; the building official decides under the adopted code."),
    }


def source_record(path: str | Path, media_type: str, page_count: int) -> dict:
    p = Path(path)
    digest = sha256_file(p)
    return {"artifact_id": f"urn:ori:artifact:sha256:{digest}", "filename": p.name, "media_type": media_type,
            "sha256": digest, "size_bytes": p.stat().st_size, "page_count": page_count}


def unlicensed_record(note: str) -> dict:
    """License record for a plan whose rights are unknown. It can be extracted for a reviewer but never trained on."""
    return {"license_id": "UNKNOWN", "license_basis": "none recorded", "license_url": None, "license_local_path": None,
            "license_sha256": None, "license_fetched_at": None, "license_confirmed": False, "source_url": None,
            "source_citation": None, "training_use": "not_allowed", "license_note": note}


# -- validation ----------------------------------------------------------------
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def schema_errors(doc: dict) -> list[str]:
    from jsonschema import Draft202012Validator, FormatChecker
    v = Draft202012Validator(schema(), format_checker=FormatChecker())
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in v.iter_errors(doc)]


def license_errors(rec: dict | None, repo: Path = REPO) -> list[str]:
    """The corpus license rule applied to plans: license record, local license copy with SHA-256, citation."""
    if not rec:
        return ["no license_record"]
    errs = [f"license_record missing {k}" for k in LICENSE_REQUIRED if rec.get(k) in (None, "", [], {})]
    if errs:
        return errs
    for k in ("source_url", "license_url"):
        if not str(rec[k]).startswith("https://"):
            errs.append(f"license_record.{k} must be an https URL")
    if not _DATE.fullmatch(str(rec["license_fetched_at"])):
        errs.append("license_record.license_fetched_at must be YYYY-MM-DD")
    cit = rec["source_citation"]
    if not isinstance(cit, dict):
        errs.append("license_record.source_citation must be an object")
    else:
        errs += [f"license_record.source_citation missing {k}" for k in CITATION_PARTS if not cit.get(k)]
    lp = str(rec["license_local_path"])
    f = Path(lp) if lp.startswith("/") else repo / lp
    if not f.is_file():
        errs.append(f"local license copy {lp} not found")
    elif sha256_file(f) != rec["license_sha256"]:
        errs.append(f"local license copy {lp} does not match license_sha256")
    if rec["license_confirmed"] is not True:
        errs.append("license not confirmed by a person")
    return errs


def training_gate_errors(doc: dict, repo: Path = REPO, allow_unreviewed: bool = False) -> list[str]:
    """Reasons this overlay may NOT enter the training set. Empty list means it may."""
    rec = doc.get("license_record")
    errs = license_errors(rec, repo)
    if rec and rec.get("license_id") not in TRAINING_LICENSES:
        errs.append(f"license {rec.get('license_id')!r} is not a training-set license {TRAINING_LICENSES}")
    if rec and rec.get("training_use") != "allowed":
        errs.append("license_record.training_use is not 'allowed'")
    for pg in doc.get("pages", []):
        if pg.get("status") == "needs_tracing":
            errs.append(f"page {pg['page']}: needs tracing (raster or empty); no labels to train on")
        for e in pg.get("elements", []):
            pr = e.get("provenance") or {}
            if not pr.get("method"):
                errs.append(f"{e.get('id')}: element without provenance")
            elif (pr["method"] == "auto_extracted" and pr.get("review_status") in ("unreviewed", "rejected")
                  and not allow_unreviewed):
                errs.append(f"{e.get('id')}: auto-extracted label not reviewed by a person")
    return errs


def require_training_ok(doc: dict, **kw) -> None:
    errs = training_gate_errors(doc, **kw)
    if errs:
        raise ValueError("overlay refused for the training set:\n  " + "\n  ".join(errs[:20]))


# -- exports -------------------------------------------------------------------
def to_geojson(doc: dict, page: int, coords: str = "real") -> dict:
    """One FeatureCollection per page. ``coords``: 'real' (inches) or 'page'."""
    pg = next(p for p in doc["pages"] if p["page"] == page)
    feats = []
    for e in pg["elements"]:
        g = e["geometry_real"] if coords == "real" else e["geometry_page"]
        if g is None:
            continue
        props = {"id": e["id"], "ifc_class": e["ifc_class"], "name": e.get("name"),
                 "annotation_type": e.get("annotation_type"), "method": e["provenance"]["method"],
                 "review_status": e["provenance"]["review_status"], "confidence": e["provenance"]["confidence"]}
        props.update({f"p_{k}": v for k, v in e["properties"].items() if isinstance(v, (int, float, str, bool)) or v is None})
        feats.append({"type": "Feature", "id": e["id"], "geometry": g, "properties": props})
    return {"type": "FeatureCollection", "name": f"{doc['source']['filename']} p{page} ({coords})",
            "ori_overlay_id": doc["overlay_id"], "units": "in" if coords == "real" else "page_unit",
            "license_id": doc["license_record"].get("license_id"), "features": feats}


COCO_CATEGORIES = [{"id": i + 1, "name": n, "supercategory": "ifc"} for i, n in enumerate(IFC_CLASSES)]


def to_coco(doc: dict, dpi: float = 72.0, image_names: dict[int, str] | None = None) -> dict:
    """COCO detection/segmentation export in raster pixel space (y down) at ``dpi`` (page points * dpi/72).
    Polygons become segmentation; lines and points become boxes (with a small pad) only."""
    cat = {c["name"]: c["id"] for c in COCO_CATEGORIES}
    k = dpi / 72.0
    images, anns = [], []
    aid = 1
    for pg in doc["pages"]:
        w, h = pg["size_page_units"]
        img_id = pg["page"]
        images.append({"id": img_id, "file_name": (image_names or {}).get(img_id, f"{Path(doc['source']['filename']).stem}-p{img_id}.png"),
                       "width": int(round(w * k)), "height": int(round(h * k)), "license": 1})
        for e in pg["elements"]:
            g = e["geometry_page"]
            pts = g["coordinates"][0] if g["type"] == "Polygon" else (g["coordinates"] if g["type"] == "LineString" else [g["coordinates"]])
            px = [(x * k, (h - y) * k) for x, y in pts]
            xs, ys = [p[0] for p in px], [p[1] for p in px]
            pad = 0 if g["type"] == "Polygon" else 2
            x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
            a = {"id": aid, "image_id": img_id, "category_id": cat[e["ifc_class"]], "bbox": [_r(x0), _r(y0), _r(x1 - x0), _r(y1 - y0)],
                 "area": _r((x1 - x0) * (y1 - y0)), "iscrowd": 0,
                 "attributes": {"ori_id": e["id"], "method": e["provenance"]["method"], "review_status": e["provenance"]["review_status"],
                                "annotation_type": e.get("annotation_type")}}
            if g["type"] == "Polygon":
                a["segmentation"] = [[_r(c) for p in px for c in p]]
            anns.append(a)
            aid += 1
    rec = doc["license_record"]
    return {"info": {"description": f"ORI plan overlay {doc['overlay_id']}", "version": doc["overlay_profile"], "date_created": doc["created_at"]},
            "licenses": [{"id": 1, "name": rec.get("license_id"), "url": rec.get("license_url")}],
            "images": images, "annotations": anns, "categories": COCO_CATEGORIES}


def dumps(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=False) + "\n"
