# SPDX-License-Identifier: Apache-2.0
"""Score raster recognition against ORI's synthetic ground truth (DRAFT 0.1).

Measured on ORI's own synthetic sheets only; not a general accuracy claim.
Ground truth comes from the vector sample's authored overlay; the known
page-to-pixel transform of each degraded image is used here only.
"""
from __future__ import annotations

import math

import numpy as np

from .. import units as U

WALL_TOL_PT = 6.0   # 4 in at 1/4" = 1'-0"
TEXT_TOL_PT = 40.0


def _inv(M):
    A = np.vstack([np.asarray(M, float), [0, 0, 1]])
    return np.linalg.inv(A)[:2]


def _apply(M, p):
    return (M[0][0] * p[0] + M[0][1] * p[1] + M[0][2], M[1][0] * p[0] + M[1][1] * p[1] + M[1][2])


def _samples(p0, p1, step=1.0):
    L = math.dist(p0, p1)
    n = max(2, int(L / step) + 1)
    return [(p0[0] + (p1[0] - p0[0]) * i / (n - 1), p0[1] + (p1[1] - p0[1]) * i / (n - 1)) for i in range(n)], L


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _in_any(p, boxes):
    return any(b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3] for b in boxes)


def _covered(segs_a, segs_b, tol, skip=()):
    """Length of segs_a lying within tol of some segment in segs_b (points inside skip boxes ignored)."""
    tot = hit = 0.0
    for a0, a1 in segs_a:
        pts, L = _samples(a0, a1)
        pts = [p for p in pts if not _in_any(p, skip)]
        if L == 0 or not pts:
            continue
        L = L * len(pts) / len(_samples(a0, a1)[0])
        ok = sum(1 for p in pts if any(_seg_dist(p, b0, b1) <= tol for b0, b1 in segs_b))
        tot += L
        hit += L * ok / len(pts)
    return hit, tot


def _norm(s: str) -> str:
    return "".join(ch for ch in U.normalize(s).upper() if ch.isalnum() or ch in "/")


def score(gt_page: dict, rec: dict, page_to_px) -> dict:
    inv = _inv(page_to_px)
    k_gt = gt_page["scale"]["real_in_per_page_unit"]
    walls_gt, thick_gt = [], []
    for e in gt_page["elements"]:
        if e["ifc_class"] == "IfcWall":
            c = e["axis_page"]["coordinates"]
            walls_gt.append((tuple(c[0]), tuple(c[-1])))
            thick_gt.append(e["properties"]["thickness_in"])
    det = [it for it in rec["items"] if it["kind"] == "wall"]
    walls_ex = [(_apply(inv, it["p0_px"]), _apply(inv, it["p1_px"])) for it in det]
    # Ground-truth axes run through door and window openings; those spans are not drawn as wall.
    holes = []
    for e in gt_page["elements"]:
        if e["ifc_class"] in ("IfcDoor", "IfcWindow"):
            cs = e["geometry_page"]["coordinates"][0]
            xs, ys = [c[0] for c in cs], [c[1] for c in cs]
            holes.append((min(xs) + 1, min(ys) - 10, max(xs) - 1, max(ys) + 10) if max(xs) - min(xs) > max(ys) - min(ys)
                         else (min(xs) - 10, min(ys) + 1, max(xs) + 10, max(ys) - 1))
    hit_r, tot_r = _covered(walls_gt, walls_ex, WALL_TOL_PT, holes)
    hit_p, tot_p = _covered(walls_ex, walls_gt, WALL_TOL_PT)
    # thickness: each detected segment against its nearest GT wall (by midpoint)
    terr = []
    for it, (a, b) in zip(det, walls_ex):
        if it.get("thickness_in") is None:
            continue
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        d, j = min((_seg_dist(mid, *g), j) for j, g in enumerate(walls_gt))
        if d <= WALL_TOL_PT:
            terr.append(abs(it["thickness_in"] - thick_gt[j]))
    texts = [it for it in rec["items"] if it["kind"] in ("text", "dimension_text")]
    texts_pg = [(_apply(inv, it["at_px"]), it) for it in texts]

    def find(target_pt, pred):
        return any(math.dist(p, target_pt) <= TEXT_TOL_PT and pred(it) for p, it in texts_pg)

    labels = [(e["properties"].get("label") or e["name"], e) for e in gt_page["elements"] if e["ifc_class"] == "IfcSpace"]
    lab_hit = 0
    for name, e in labels:
        xs = [c[0] for c in e["geometry_page"]["coordinates"][0]]
        ys = [c[1] for c in e["geometry_page"]["coordinates"][0]]
        ctr = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        want = _norm(name)
        if any(want in _norm(it["text"]) and math.dist(p, ctr) <= 0.5 * max(max(xs) - min(xs), max(ys) - min(ys))
               for p, it in texts_pg):
            lab_hit += 1
    dims = [e for e in gt_page["elements"] if e.get("annotation_type") == "dimension"]
    dim_found = dim_value = 0
    for e in dims:
        c = e["geometry_page"]["coordinates"]
        mid = ((c[0][0] + c[-1][0]) / 2, (c[0][1] + c[-1][1]) / 2)
        v = e["properties"]["value_in"]
        if find(mid, lambda it: it["kind"] == "dimension_text"):
            dim_found += 1
        if find(mid, lambda it: it.get("value_in") is not None and abs(it["value_in"] - v) < 0.01):
            dim_value += 1
    scale = rec["scale"]
    ex_k = scale.get("real_in_per_px")
    true_k_px = k_gt / math.hypot(page_to_px[0][0], page_to_px[1][0])
    r = lambda a, b: None if b == 0 else round(a / b, 3)
    return {
        "walls": {"gt_centreline_pt": round(tot_r, 1), "length_recall": r(hit_r, tot_r),
                  "length_precision": r(hit_p, tot_p), "detected_segments": len(det), "gt_walls": len(walls_gt),
                  "tolerance_pt": WALL_TOL_PT,
                  "thickness_abs_err_in": None if not terr else {"n": len(terr), "mean": round(float(np.mean(terr)), 2),
                                                                  "max": round(float(np.max(terr)), 2)}},
        "room_labels": {"gt": len(labels), "found": lab_hit, "recall": r(lab_hit, len(labels))},
        "dimensions": {"gt": len(dims), "string_found": dim_found, "value_exact": dim_value,
                       "value_recall": r(dim_value, len(dims))},
        "scale": {"status": scale["status"],
                  "rel_error": None if ex_k is None else round(abs(ex_k - true_k_px) / true_k_px, 4)},
        "skew_deg": {"estimated": rec["skew_estimated_deg"]},
    }
