# SPDX-License-Identifier: Apache-2.0
"""Plan file to ``ori-plan-overlay-0.1`` document: detection, overlay elements and takeoff.

  extract_pdf(path) / extract_dxf(path) -> overlay dict

Raster or empty PDF pages get ``status: needs_tracing`` and no elements. Every proposed element
is ``auto_extracted`` and ``unreviewed``.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from . import detect as D
from . import overlay as ov
from . import units as U
from .sources import PagePrimitives, read_dxf, read_pdf


def _poly_coords(p: Polygon):
    return list(p.exterior.coords)[:-1], [list(r.coords)[:-1] for r in p.interiors]


def _pg(p: Polygon) -> dict:
    ext, holes = _poly_coords(p)
    return ov.polygon(ext, holes)


def detect_page(pp: PagePrimitives, params: D.Params | None = None) -> dict:
    """Run detection on one page; returns an overlay page dict."""
    p = params or D.Params()
    page = {"page": pp.page, "page_label": pp.page_label, "sheet_title": None, "kind": pp.kind,
            "status": "extracted", "size_page_units": [round(pp.width or 0, 3), round(pp.height or 0, 3)],
            "page_units": "pt" if pp.units == "pt" else pp.units, "scale": None,
            "storey": {"name": None, "elevation_in": None, "elevation_origin": "unknown"},
            "elements": [], "takeoff": None, "notes": [],
            "detection": {"weight_source": pp.weight_source, "use_lineweight": p.use_lineweight,
                          "segments": len(pp.segs), "arcs": len(pp.arcs), "other_curves": pp.curves, "text_runs": len(pp.texts)}}
    if pp.kind in ("raster", "empty"):
        page["status"] = "needs_tracing"
        page["scale"] = ov.scale_block("unknown", None, note="Raster or empty page: not extracted in v0.1.")
        page["notes"].append("No vector linework found; this page needs human tracing (raster plans are out of scope for v0.1).")
        return page
    sc = D.detect_scale(pp, p)
    k = sc["k"]
    page["scale"] = ov.scale_block(sc["status"], k, sc["stated"], sc["calibration"], sc["note"])
    k = page["scale"]["real_in_per_page_unit"]
    for t in pp.texts:
        if re.search(r"\bPLAN\b", t.text.upper()) and not page["sheet_title"]:
            page["sheet_title"] = t.text
    els = page["elements"]
    tol = (1.0 / k) if k else 1.0

    # walls
    cands = D._candidates(pp, p)
    rng = D._thickness_range(cands, k, p)
    walls = []
    if rng:
        pieces = D.wall_pieces(cands, rng[0], rng[1], (p.min_piece_in / k) if k else rng[0] / 2)
        walls = D.merge_walls(pieces, max_gap=(p.max_opening_in / k) if k else rng[1] * 12, tol=tol * 0.5)
        walls = [w for w in walls if (w.s1 - w.s0) >= 2 * w.t]
        D.snap_corners(walls, tol)
    if not p.use_lineweight or pp.weight_source == "none":
        page["notes"].append("Line weight not used: every segment was a wall candidate.")
    wall_ids = {}
    openings = []
    for i, w in enumerate(walls, 1):
        wid = f"p{pp.page}-wall-{i:03d}"
        wall_ids[id(w)] = wid
        for g0, g1 in w.gaps:
            if (g1 - g0) * (k or 1) < (p.min_opening_in if k else 0):
                continue
            c = D.classify_gap(w, g0, g1, pp, walls, tol * 3)
            if c:
                openings.append((w, g0, g1, c))
    wall_union = unary_union([w.rect() for w in walls]) if walls else None
    closed = unary_union([wall_union] + [w.rect(g0, g1) for w, g0, g1, _ in openings]) if walls else None
    footprint = None
    rooms = []
    if closed is not None and not closed.is_empty:
        r = (p.wall_t_max_in / 2 / k) if k else (rng[1] / 2)
        closed = closed.buffer(r, join_style="mitre").buffer(-r, join_style="mitre")
        geoms = list(getattr(closed, "geoms", [closed]))
        footprint = unary_union([Polygon(g.exterior) for g in geoms])
        min_area = (p.min_room_ft2 * 144 / (k * k)) if k else 0
        for g in geoms:
            for ring in g.interiors:
                rp = Polygon(ring)
                if rp.area >= min_area:
                    rooms.append(rp.simplify(tol * 0.1))
    exterior_line = footprint.boundary if footprint is not None else None

    for w in walls:
        ext = bool(exterior_line is not None and w.rect().buffer(tol).intersection(exterior_line).length > 0.5 * (w.s1 - w.s0))
        length = (w.s1 - w.s0)
        props = {"thickness_in": _real(w.t, k), "length_in": _real(length, k), "exterior": ext,
                 "thickness_page": round(w.t, 3), "length_page": round(length, 3), "openings": len(w.gaps)}
        els.append(ov.element(wall_ids[id(w)], "IfcWall", _pg(w.rect()), k,
                              ov.provenance("auto_extracted", 0.9 if w.heavy and pp.weight_source != "none" else 0.6,
                                            rule="parallel_line_pair"), props,
                              axis_page=ov.line(list(w.axis().coords)), predefined_type="SOLIDWALL"))
    cls = {"door": "IfcDoor", "window": "IfcWindow", "opening": "IfcOpeningElement"}
    counts = {"door": 0, "window": 0, "opening": 0}
    opening_els = []
    for w, g0, g1, c in openings:
        counts[c["kind"]] += 1
        oid = f"p{pp.page}-{c['kind']}-{counts[c['kind']]:03d}"
        props = {"width_in": _real(g1 - g0, k), "width_page": round(g1 - g0, 3), "host_thickness_in": _real(w.t, k)}
        if "swing" in c:
            sw = dict(c["swing"])
            sw["radius_in"] = _real(sw["radius_page"], k)
            props["swing"] = sw
        e = ov.element(oid, cls[c["kind"]], _pg(w.rect(g0, g1)), k, ov.provenance("auto_extracted", c["confidence"], rule=c["rule"]),
                       props, axis_page=ov.line([w.pt(g0, w.off), w.pt(g1, w.off)]),
                       predefined_type={"door": "DOOR", "window": "WINDOW", "opening": "OPENING"}[c["kind"]],
                       relations={"host_wall": wall_ids[id(w)]})
        els.append(e)
        opening_els.append(e)

    # rooms with labels
    used_text = set()
    for i, rp in enumerate(rooms, 1):
        inside = [t for t in pp.texts if rp.contains(Point(t.x, t.y))]
        names = [t for t in inside if not D.is_dimension_text(t.text) and not D.size_note(t.text)
                 and re.search(r"[A-Za-z]{2,}", t.text) and not re.search(r"\b(UP|DN)\b\s*\d*R?$", t.text)]
        names.sort(key=lambda t: -t.y)
        label = " ".join(t.text for t in names) or None
        note = next((D.size_note(t.text) for t in inside if D.size_note(t.text)), None)
        used_text.update(id(t) for t in names)
        area = (rp.area * k * k / 144.0) if k else None
        props = {"area_ft2": None if area is None else round(area, 3), "area_page2": round(rp.area, 3), "label": label,
                 "use": D.use_from_label(label), "use_source": "inferred_from_label" if label else None,
                 "noted_size_in": note, "noted_area_ft2": round(note[0] * note[1] / 144, 3) if note else None}
        if note and area is not None:
            props["area_matches_note"] = abs(area - props["noted_area_ft2"]) <= max(1.0, 0.02 * area)
        els.append(ov.element(f"p{pp.page}-space-{i:03d}", "IfcSpace", _pg(rp), k,
                              ov.provenance("auto_extracted", 0.85 if label else 0.6, rule="hole_in_closed_wall_network"),
                              props, name=label, predefined_type="SPACE"))

    # stairs
    stairs = D.detect_stairs(pp, k, p, footprint)
    for i, st in enumerate(stairs, 1):
        props = {"riser_count": st["lines"], "tread_count": st["lines"] - 1, "tread_depth_in": _real(st["spacing_page"], k),
                 "width_in": _real(st["width_page"], k), "direction": st["direction"], "noted_riser_count": st["noted_risers"],
                 "riser_height_in": None,
                 "riser_height_note": "Riser height is not measurable on a plan view; left unknown.",
                 "count_convention": "one line per riser including first and last"}
        if st["noted_risers"] is not None:
            props["riser_count_matches_note"] = st["noted_risers"] == st["lines"]
        els.append(ov.element(f"p{pp.page}-stair-{i:03d}", "IfcStair", _pg(st["polygon"]), k,
                              ov.provenance("auto_extracted", 0.7, rule="uniform_parallel_tread_lines"), props,
                              predefined_type="STRAIGHT_RUN_STAIR"))

    # dimensions and other annotations
    nd = 0
    dims = []
    if pp.units != "pt":
        for d in pp.dxf_dims:
            nd += 1
            val = d["measurement"] * (pp.unit_in or 0) if d["measurement"] is not None and pp.unit_in else None
            txt = d["text"] if d["text"] not in ("", "<>") else (U.format_ft_in(val) if val is not None else None)
            dims.append(ov.element(f"p{pp.page}-dim-{nd:03d}", "IfcAnnotation", ov.line([d["p0"], d["p1"]]), k,
                                   ov.provenance("auto_extracted", 0.95, rule="dxf_dimension_entity"),
                                   {"text": txt, "value_in": None if val is None else round(val, 3),
                                    "measured_in": _real(math.dist(d["p0"], d["p1"]), k),
                                    "agrees": None if (val is None or k is None) else abs(math.dist(d["p0"], d["p1"]) * k - val) <= max(0.5, 0.01 * val)},
                                   annotation_type="dimension"))
    for t in pp.texts:
        v = U.parse_ft_in(t.text)
        if v is not None and pp.units == "pt":
            m = D.match_dimension_line(t, pp.segs, max_perp=3.0 * t.size)
            if m:
                s, L = m
                nd += 1
                meas = _real(L, k)
                dims.append(ov.element(f"p{pp.page}-dim-{nd:03d}", "IfcAnnotation", ov.line([(s.x0, s.y0), (s.x1, s.y1)]), k,
                                       ov.provenance("auto_extracted", 0.9, rule="dimension_text_on_parallel_line"),
                                       {"text": t.text, "value_in": v, "measured_in": meas,
                                        "agrees": None if meas is None else abs(meas - v) <= max(0.5, 0.01 * v)},
                                       annotation_type="dimension"))
                used_text.add(id(t))
                continue
        if id(t) in used_text:
            continue
        atype = "scale_note" if U.parse_scale_note(t.text) not in (None,) and "SCALE" in t.text.upper() else (
            "sheet_title" if t.text == page["sheet_title"] else "text_label")
        bx = t.bbox
        els.append(ov.element(f"p{pp.page}-text-{len(els):03d}", "IfcAnnotation", ov.point(t.x, t.y), k,
                              ov.provenance("auto_extracted", 0.95, rule="vector_text_run"),
                              {"text": t.text, "angle_deg": t.angle, "size_page": round(t.size, 3),
                               "bbox_page": [round(c, 3) for c in bx]}, annotation_type=atype))
    els.extend(dims)
    # storey and notes
    for t in pp.texts:
        m = re.search(r"FLOOR\s+TO\s+FLOOR\s+(\d+'\s*-?\s*[\d /]*\")", U.normalize(t.text).upper())
        if m:
            page["storey"]["noted_floor_to_floor_in"] = U.parse_ft_in(m.group(1))
            page["storey"]["noted_floor_to_floor_source"] = "sheet note text (unconfirmed)"
    title = (page["sheet_title"] or "").upper()
    for word, n in (("FIRST", 1), ("SECOND", 2), ("THIRD", 3), ("BASEMENT", 0)):
        if word in title:
            page["storey"]["name"] = f"Level {n}" if n else "Basement"
            page["storey"]["elevation_origin"] = "storey name from sheet title; elevation unknown"
    from .takeoff import page_takeoff
    page["takeoff"] = page_takeoff(page, footprint, k)
    return page


def _real(v, k):
    return None if (k is None or v is None) else float(round(float(v) * k, 3))


def extract_pdf(path: str | Path, params: D.Params | None = None, license_record: dict | None = None,
                created_at: str | None = None) -> dict:
    pages = read_pdf(path)
    doc = ov.new_document(ov.source_record(path, "application/pdf", len(pages)),
                          license_record or ov.unlicensed_record("No license basis recorded for this plan."), created_at=created_at)
    doc["pages"] = [detect_page(pp, params) for pp in pages]
    return doc


def extract_dxf(path: str | Path, params: D.Params | None = None, license_record: dict | None = None,
                created_at: str | None = None) -> dict:
    pp = read_dxf(path)
    doc = ov.new_document(ov.source_record(path, "image/vnd.dxf", 1),
                          license_record or ov.unlicensed_record("No license basis recorded for this drawing."), created_at=created_at)
    doc["pages"] = [detect_page(pp, params)]
    return doc
