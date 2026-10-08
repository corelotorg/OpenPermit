# SPDX-License-Identifier: Apache-2.0
"""Measure an extracted overlay against a ground-truth overlay (real-world coordinates, inches).

Metrics per page and overall:
* walls: centreline length precision/recall within a tolerance band (default 2 in), thickness error;
* openings: one-to-one matching by axis midpoint distance (default 6 in); class agreement; width error;
* spaces: matching by polygon IoU (>= 0.9); area error; label agreement (letters only, case-folded);
* stairs: riser and tread count agreement, tread depth error;
* dimensions: matched by line midpoint (6 in) and value agreement;
* takeoff totals: wall length, net space area, door and window counts.
Numbers are what this run measured on this pair of files; nothing is extrapolated.
"""

from __future__ import annotations

import math
import re
import statistics

from shapely.geometry import LineString, Polygon, shape
from shapely.ops import unary_union


def _g(e):
    return shape(e["geometry_real"]) if e.get("geometry_real") else None


def _axis(e):
    return shape(e["axis_real"]) if e.get("axis_real") else None


def _norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _match(gt, ex, dist, max_d):
    pairs, used = [], set()
    cand = sorted(((dist(g, x), i, j) for i, g in enumerate(gt) for j, x in enumerate(ex)), key=lambda t: t[0])
    gi = set()
    for d, i, j in cand:
        if d > max_d or i in gi or j in used:
            continue
        gi.add(i)
        used.add(j)
        pairs.append((gt[i], ex[j], d))
    return pairs


def _stats(vals):
    vals = [abs(v) for v in vals]
    if not vals:
        return {"n": 0, "mean_abs": None, "max_abs": None}
    return {"n": len(vals), "mean_abs": round(statistics.mean(vals), 4), "max_abs": round(max(vals), 4)}


def _prf(tp, n_gt, n_ex):
    p = tp / n_ex if n_ex else None
    r = tp / n_gt if n_gt else None
    f = (2 * p * r / (p + r)) if (p and r) else (0.0 if (p == 0 or r == 0) else None)
    rd = lambda v: None if v is None else round(v, 4)  # noqa: E731
    return {"tp": tp, "gt": n_gt, "extracted": n_ex, "precision": rd(p), "recall": rd(r), "f1": rd(f)}


def compare_page(gt_page: dict, ex_page: dict, tol_in: float = 2.0, open_tol_in: float = 6.0) -> dict:
    by = lambda pg, c: [e for e in pg["elements"] if e["ifc_class"] == c]  # noqa: E731
    out = {"page": gt_page["page"], "page_label": gt_page.get("page_label"), "scale_status": ex_page["scale"]["status"]}
    if ex_page["scale"]["real_in_per_page_unit"] is None:
        out["note"] = "Extracted page has no usable scale; real-world metrics not computed."
        return out
    gk, ek = gt_page["scale"]["real_in_per_page_unit"], ex_page["scale"]["real_in_per_page_unit"]
    out["scale_rel_error"] = round(abs(ek - gk) / gk, 6)
    # walls
    gw, ew = by(gt_page, "IfcWall"), by(ex_page, "IfcWall")
    g_ax = unary_union([_axis(e) for e in gw]) if gw else LineString()
    e_ax = unary_union([_axis(e) for e in ew]) if ew else LineString()
    g_len, e_len = g_ax.length, e_ax.length
    rec = g_ax.intersection(e_ax.buffer(tol_in)).length / g_len if g_len else None
    prec = e_ax.intersection(g_ax.buffer(tol_in)).length / e_len if e_len else None
    wp = _match(gw, ew, lambda a, b: _axis(a).centroid.distance(_axis(b).centroid) if _axis(a).buffer(tol_in).intersects(_axis(b)) else 1e9, 1e8)
    out["walls"] = {"gt_count": len(gw), "extracted_count": len(ew), "matched": len(wp),
                    "centreline_length_gt_in": round(g_len, 3), "centreline_length_extracted_in": round(e_len, 3),
                    "length_precision": None if prec is None else round(prec, 4), "length_recall": None if rec is None else round(rec, 4),
                    "thickness_error_in": _stats([a["properties"]["thickness_in"] - b["properties"]["thickness_in"] for a, b, _ in wp]),
                    "tolerance_in": tol_in}
    # openings
    gop = by(gt_page, "IfcDoor") + by(gt_page, "IfcWindow") + by(gt_page, "IfcOpeningElement")
    eop = by(ex_page, "IfcDoor") + by(ex_page, "IfcWindow") + by(ex_page, "IfcOpeningElement")
    op = _match(gop, eop, lambda a, b: _axis(a).interpolate(0.5, normalized=True).distance(_axis(b).interpolate(0.5, normalized=True)), open_tol_in)
    same = [(a, b) for a, b, _ in op if a["ifc_class"] == b["ifc_class"]]
    out["openings"] = {"located": _prf(len(op), len(gop), len(eop)),
                       "located_and_class_correct": _prf(len(same), len(gop), len(eop)),
                       "doors": _prf(sum(1 for a, b in same if a["ifc_class"] == "IfcDoor"), len(by(gt_page, "IfcDoor")), len(by(ex_page, "IfcDoor"))),
                       "windows": _prf(sum(1 for a, b in same if a["ifc_class"] == "IfcWindow"), len(by(gt_page, "IfcWindow")), len(by(ex_page, "IfcWindow"))),
                       "width_error_in": _stats([a["properties"]["width_in"] - b["properties"]["width_in"] for a, b, _ in op]),
                       "tolerance_in": open_tol_in}
    # spaces
    gs, es = by(gt_page, "IfcSpace"), by(ex_page, "IfcSpace")
    def iou(a, b):
        A, B = _g(a), _g(b)
        u = A.union(B).area
        return A.intersection(B).area / u if u else 0
    sp = _match(gs, es, lambda a, b: 1 - iou(a, b), 0.1)
    out["spaces"] = {**_prf(len(sp), len(gs), len(es)),
                     "mean_iou": round(statistics.mean([1 - d for _, _, d in sp]), 5) if sp else None,
                     "area_error_ft2": _stats([b["properties"]["area_ft2"] - a["properties"]["area_ft2"] for a, b, _ in sp]),
                     "area_rel_error_max": round(max(abs(b["properties"]["area_ft2"] - a["properties"]["area_ft2"]) / a["properties"]["area_ft2"] for a, b, _ in sp), 6) if sp else None,
                     "label_correct": sum(1 for a, b, _ in sp if _norm(a["properties"].get("label")) == _norm(b["properties"].get("label"))),
                     "use_correct": sum(1 for a, b, _ in sp if a["properties"].get("use") == b["properties"].get("use"))}
    # stairs
    gst, est = by(gt_page, "IfcStair"), by(ex_page, "IfcStair")
    stp = _match(gst, est, lambda a, b: 1 - iou(a, b), 0.5)
    out["stairs"] = {**_prf(len(stp), len(gst), len(est)),
                     "riser_count_correct": sum(1 for a, b, _ in stp if a["properties"]["riser_count"] == b["properties"]["riser_count"]),
                     "tread_count_correct": sum(1 for a, b, _ in stp if a["properties"]["tread_count"] == b["properties"]["tread_count"]),
                     "tread_depth_error_in": _stats([b["properties"]["tread_depth_in"] - a["properties"]["tread_depth_in"] for a, b, _ in stp])}
    # dimensions
    gd = [e for e in by(gt_page, "IfcAnnotation") if e.get("annotation_type") == "dimension"]
    ed = [e for e in by(ex_page, "IfcAnnotation") if e.get("annotation_type") == "dimension"]
    dp = _match(gd, ed, lambda a, b: _g(a).centroid.distance(_g(b).centroid), 6.0)
    out["dimensions"] = {**_prf(len(dp), len(gd), len(ed)),
                         "value_correct": sum(1 for a, b, _ in dp if b["properties"].get("value_in") is not None
                                              and abs(a["properties"]["value_in"] - b["properties"]["value_in"]) < 0.01)}
    # totals
    gt_area = sum(e["properties"]["area_ft2"] for e in gs)
    ex_area = sum(e["properties"]["area_ft2"] or 0 for e in es)
    out["takeoff_totals"] = {"wall_length_in": {"gt": round(g_len, 3), "extracted": round(e_len, 3), "abs_error": round(abs(e_len - g_len), 3)},
                             "net_space_area_ft2": {"gt": round(gt_area, 3), "extracted": round(ex_area, 3), "abs_error": round(abs(ex_area - gt_area), 3)},
                             "doors": {"gt": len(by(gt_page, "IfcDoor")), "extracted": len(by(ex_page, "IfcDoor"))},
                             "windows": {"gt": len(by(gt_page, "IfcWindow")), "extracted": len(by(ex_page, "IfcWindow"))}}
    return out


def compare(gt: dict, ex: dict, **kw) -> dict:
    pages = []
    for gp in gt["pages"]:
        xp = next((p for p in ex["pages"] if p["page"] == gp["page"]), None)
        if xp is not None:
            pages.append(compare_page(gp, xp, **kw))
    return {"report": "ori-plan-overlay-accuracy-0.1", "label": "Measured on this file pair only; not a general accuracy claim.",
            "ground_truth": gt["overlay_id"], "extracted": ex["overlay_id"], "extractor": ex["tool"], "pages": pages}
