# SPDX-License-Identifier: Apache-2.0
"""Rule-based detection on vector primitives: scale, walls, openings, rooms, stairs, dimensions.

All thresholds are real-world inches converted to page units with the page scale. Where the
scale is unknown, wall thickness is taken from the most common close parallel spacing of heavy
lines and every real-world value stays null. Heuristics are documented in
docs/PLAN-TAKEOFF-0.1-DRAFT.md §5; confidences are uncalibrated heuristics, not probabilities.
"""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass, field

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from . import units as U
from .sources import Arc, PagePrimitives, Seg, TextRun

ANG_TOL = 1.0  # degrees


@dataclass
class Params:
    wall_t_min_in: float = 3.0
    wall_t_max_in: float = 12.0
    min_piece_in: float = 2.0
    max_opening_in: float = 120.0
    min_opening_in: float = 18.0
    min_room_ft2: float = 10.0
    tread_min_in: float = 8.0
    tread_max_in: float = 14.0
    stair_w_min_in: float = 28.0
    stair_w_max_in: float = 72.0
    use_lineweight: bool = True
    scale_agree_rel: float = 0.02


@dataclass
class WallPiece:
    ang: float  # 0 or folded direction
    off: float  # perpendicular offset of the axis
    t: float  # thickness (page units)
    s0: float  # along-axis interval
    s1: float
    heavy: bool


@dataclass
class Wall:
    ang: float
    off: float
    t: float
    s0: float
    s1: float
    pieces: list[tuple[float, float]] = field(default_factory=list)
    gaps: list[tuple[float, float]] = field(default_factory=list)
    heavy: bool = True
    ext0: float = 0.0  # body extension past the axis start/end at L corners (to the outer face)
    ext1: float = 0.0

    def frame(self):
        u = (math.cos(math.radians(self.ang)), math.sin(math.radians(self.ang)))
        n = (-u[1], u[0])
        return u, n

    def pt(self, s, o):
        u, n = self.frame()
        return (s * u[0] + o * n[0], s * u[1] + o * n[1])

    def rect(self, s0=None, s1=None):
        s0 = (self.s0 - self.ext0) if s0 is None else s0
        s1 = (self.s1 + self.ext1) if s1 is None else s1
        h = self.t / 2
        return Polygon([self.pt(s0, self.off - h), self.pt(s1, self.off - h), self.pt(s1, self.off + h), self.pt(s0, self.off + h)])

    def axis(self):
        return LineString([self.pt(self.s0, self.off), self.pt(self.s1, self.off)])


def _frame(ang):
    u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    return u, (-u[1], u[0])


def _proj(seg: Seg, ang):
    u, n = _frame(ang)
    a = seg.x0 * u[0] + seg.y0 * u[1]
    b = seg.x1 * u[0] + seg.y1 * u[1]
    o = ((seg.x0 + seg.x1) * n[0] + (seg.y0 + seg.y1) * n[1]) / 2
    return min(a, b), max(a, b), o


def _ang_close(a, b, tol=ANG_TOL):
    d = abs(a - b) % 180
    return min(d, 180 - d) <= tol


# -- scale ----------------------------------------------------------------------
def _text_dir(t: TextRun):
    return t.angle % 180


def match_dimension_line(t: TextRun, segs: list[Seg], max_perp: float):
    """Thin segment parallel to a dimension text, centred under it; returns (seg, length) or None."""
    best = None
    ang = _text_dir(t)
    u, n = _frame(ang)
    ta, to = t.x * u[0] + t.y * u[1], t.x * n[0] + t.y * n[1]
    for s in segs:
        if s.heavy or not _ang_close(s.angle, ang, 2.0):
            continue
        a, b, o = _proj(s, ang)
        if not (a + 0.1 * (b - a) <= ta <= b - 0.1 * (b - a)):
            continue
        d = abs(o - to)
        if d > max_perp:
            continue
        if best is None or d < best[0]:
            best = (d, s)
    return (best[1], best[1].length) if best else None


def detect_scale(pp: PagePrimitives, p: Params) -> dict:
    stated_vals, stated_runs = [], []
    nts = False
    for t in pp.texts:
        if "SCALE" not in t.text.upper() and "NTS" not in t.text.upper():
            continue
        v = U.parse_scale_note(t.text)
        if v == "not_to_scale":
            nts = True
        elif v:
            stated_vals.append(v)
            stated_runs.append(t)
    cal = []
    for t in pp.texts:
        v = U.parse_ft_in(t.text)
        if not v:
            continue
        m = match_dimension_line(t, pp.segs, max_perp=3.0 * t.size)
        if m and m[1] > 0:
            cal.append(v / m[1])
    if pp.units != "pt":
        if pp.unit_in:
            return {"status": "drawing_units", "k": pp.unit_in, "stated": None,
                    "calibration": {"n": 0}, "note": f"DXF $INSUNITS gives {pp.unit_in} in per drawing unit."}
        return {"status": "unknown", "k": None, "stated": None, "calibration": {"n": 0}, "note": "DXF without $INSUNITS."}
    calib = None
    if cal:
        med = statistics.median(cal)
        spread = (max(cal) - min(cal)) / med
        calib = {"n": len(cal), "median_real_in_per_page_unit": round(med, 6), "spread_rel": round(spread, 6)}
    stated = None
    k_stated = None
    if stated_vals:
        uniq = sorted({round(v, 6) for v in stated_vals})
        stated = {"text": stated_runs[0].text, "real_in_per_paper_in": uniq[0], "notes_found": len(stated_vals),
                  "distinct_values": uniq}
        if len(uniq) == 1:
            k_stated = uniq[0] / U.PT_PER_IN
    if k_stated and calib:
        if abs(calib["median_real_in_per_page_unit"] - k_stated) / k_stated <= p.scale_agree_rel:
            return {"status": "stated_confirmed", "k": k_stated, "stated": stated, "calibration": calib,
                    "note": "Scale note agrees with dimension strings."}
        return {"status": "conflict", "k": None, "stated": stated, "calibration": calib,
                "note": "Scale note and dimension strings disagree; real-world values withheld."}
    if k_stated:
        return {"status": "stated", "k": k_stated, "stated": stated, "calibration": calib, "note": "Scale note only."}
    if stated and len(stated["distinct_values"]) > 1 and not calib:
        return {"status": "conflict", "k": None, "stated": stated, "calibration": None,
                "note": "Several different scale notes on the page and no dimension strings to choose between them."}
    if calib and calib["n"] >= 2 and calib["spread_rel"] <= p.scale_agree_rel:
        return {"status": "calibrated", "k": calib["median_real_in_per_page_unit"], "stated": stated, "calibration": calib,
                "note": "No usable scale note; scale from dimension strings."}
    if nts:
        return {"status": "not_to_scale", "k": None, "stated": {"text": "NTS"}, "calibration": calib, "note": "Marked not to scale."}
    return {"status": "unknown", "k": None, "stated": stated, "calibration": calib, "note": "No scale note and no consistent dimension strings."}


# -- walls ----------------------------------------------------------------------
def _candidates(pp: PagePrimitives, p: Params):
    if p.use_lineweight and pp.weight_source != "none":
        return [s for s in pp.segs if s.heavy]
    return list(pp.segs)


def _thickness_range(cands, k, p: Params):
    if k:
        return p.wall_t_min_in / k, p.wall_t_max_in / k
    seps = []
    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            if not _ang_close(a.angle, b.angle):
                continue
            a0, a1, oa = _proj(a, a.angle)
            b0, b1, ob = _proj(b, a.angle)
            if min(a1, b1) - max(a0, b0) > 0 and abs(oa - ob) > 1e-6:
                seps.append(round(abs(oa - ob), 2))
    if not seps:
        return None
    m = statistics.mode(sorted(seps)[: max(1, len(seps) // 3)])
    return 0.5 * m, 2.2 * m


def wall_pieces(cands: list[Seg], tmin, tmax, min_piece) -> list[WallPiece]:
    pieces = []
    groups: list[list[Seg]] = []
    for s in sorted(cands, key=lambda s: s.angle):
        for g in groups:
            if _ang_close(g[0].angle, s.angle):
                g.append(s)
                break
        else:
            groups.append([s])
    for g in groups:
        ang = round(g[0].angle, 3)
        pr = [(*_proj(s, ang), s) for s in g]
        for i, (a0, a1, oa, sa) in enumerate(pr):
            # nearest partner on each side for each covered sub-interval: keep the closest pair only
            for b0, b1, ob, sb in pr[i + 1:]:
                d = abs(oa - ob)
                if not (tmin <= d <= tmax):
                    continue
                lo, hi = max(a0, b0), min(a1, b1)
                if hi - lo < min_piece:
                    continue
                # reject if another parallel line lies strictly between them over this interval
                mid = (oa + ob) / 2
                blocked = any(min(oa, ob) + 1e-6 < oc < max(oa, ob) - 1e-6 and min(c1, hi) - max(c0, lo) > 0.5 * (hi - lo)
                              for c0, c1, oc, _ in pr)
                if blocked:
                    continue
                pieces.append(WallPiece(ang, mid, d, lo, hi, bool(sa.heavy and sb.heavy)))
    return pieces


def merge_walls(pieces: list[WallPiece], max_gap: float, tol: float) -> list[Wall]:
    walls: list[Wall] = []
    for pc in sorted(pieces, key=lambda q: (q.ang, round(q.off / tol), q.s0)):
        for w in walls:
            if _ang_close(w.ang, pc.ang) and abs(w.off - pc.off) <= tol and abs(w.t - pc.t) <= tol and pc.s0 <= w.s1 + max_gap:
                if pc.s0 > w.s1 + 1e-6:
                    w.gaps.append((w.s1, pc.s0))
                w.s1 = max(w.s1, pc.s1)
                w.pieces.append((pc.s0, pc.s1))
                break
        else:
            walls.append(Wall(pc.ang, pc.off, pc.t, pc.s0, pc.s1, [(pc.s0, pc.s1)], [], pc.heavy))
    # drop duplicate walls fully inside another (same line found twice)
    out = []
    for w in walls:
        if any(o is not w and _ang_close(o.ang, w.ang) and abs(o.off - w.off) <= tol and o.s0 - tol <= w.s0 and w.s1 <= o.s1 + tol
               and (o.s1 - o.s0) > (w.s1 - w.s0) for o in walls):
            continue
        out.append(w)
    return out


def snap_corners(walls: list[Wall], tol: float):
    """Extend wall ends to meet at L corners (both ends near the axis intersection)."""
    for i, a in enumerate(walls):
        for b in walls[i + 1:]:
            if _ang_close(a.ang, b.ang, 10):
                continue
            ia = a.axis().intersection(b.axis())
            la, lb = LineString([a.pt(a.s0 - a.t * 2, a.off), a.pt(a.s1 + a.t * 2, a.off)]), \
                LineString([b.pt(b.s0 - b.t * 2, b.off), b.pt(b.s1 + b.t * 2, b.off)])
            x = la.intersection(lb)
            if x.is_empty or not isinstance(x, Point) or not ia.is_empty:
                continue
            ua, _ = a.frame()
            ub, _ = b.frame()
            sa = x.x * ua[0] + x.y * ua[1]
            sb = x.x * ub[0] + x.y * ub[1]
            near_a = min(abs(sa - a.s0), abs(sa - a.s1)) <= b.t / 2 + tol
            near_b = min(abs(sb - b.s0), abs(sb - b.s1)) <= a.t / 2 + tol
            if near_a and near_b:
                for w, s_, other in ((a, sa, b), (b, sb, a)):
                    if abs(s_ - w.s0) <= abs(s_ - w.s1):
                        w.s0, w.ext0 = s_, other.t / 2
                    else:
                        w.s1, w.ext1 = s_, other.t / 2


# -- openings -------------------------------------------------------------------
def classify_gap(w: Wall, g0: float, g1: float, pp: PagePrimitives, walls: list[Wall], tol: float) -> dict | None:
    gap_rect = w.rect(g0, g1)
    width = g1 - g0
    # junction, not an opening: another wall crosses the gap
    for o in walls:
        if o is w or _ang_close(o.ang, w.ang, 10):
            continue
        if o.rect().intersection(gap_rect).area > 0.5 * gap_rect.area:
            return None
    jambs = [w.pt(g0, w.off - w.t / 2), w.pt(g0, w.off + w.t / 2), w.pt(g1, w.off - w.t / 2), w.pt(g1, w.off + w.t / 2)]
    best = None
    for a in pp.arcs:
        if abs(a.r - width) > max(0.15 * width, tol):
            continue
        dmin = min(math.dist((a.cx, a.cy), j) for j in jambs)
        if dmin <= max(tol, 0.1 * width) and (best is None or dmin < best[0]):
            best = (dmin, a)
    if best:
        a = best[1]
        hinge = min(jambs, key=lambda j: math.dist((a.cx, a.cy), j))
        _, n = w.frame()
        mid_ang = math.radians((a.a0 + a.a1) / 2)
        side = 1 if (math.cos(mid_ang) * n[0] + math.sin(mid_ang) * n[1]) > 0 else -1
        return {"kind": "door", "confidence": 0.85, "rule": "gap_with_swing_arc",
                "swing": {"hinge_page": [round(hinge[0], 3), round(hinge[1], 3)], "radius_page": round(a.r, 3),
                          "arc_deg": [round(a.a0, 2), round(a.a1, 2)], "opens_to_normal_side": side}}
    inside = 0
    u, n = w.frame()
    for s in pp.segs:
        if s.heavy and pp.weight_source != "none":
            continue
        if not _ang_close(s.angle, w.ang):
            continue
        a0, a1, o = _proj(s, w.ang)
        if abs(o - w.off) <= w.t / 2 + tol * 0.25 and min(a1, g1) - max(a0, g0) >= 0.8 * width:
            inside += 1
    if inside >= 2:
        return {"kind": "window", "confidence": 0.8, "rule": "gap_with_parallel_glazing_lines", "glazing_lines": inside}
    return {"kind": "opening", "confidence": 0.4, "rule": "gap_without_door_or_window_symbol"}


# -- stairs -----------------------------------------------------------------------
def detect_stairs(pp: PagePrimitives, k, p: Params, footprint) -> list[dict]:
    if not k:
        return []
    thin = [s for s in pp.segs if not (s.heavy and pp.weight_source != "none")]
    out = []
    used = set()
    for ang in (0.0, 90.0):
        group = []
        for idx, s in enumerate(thin):
            if not _ang_close(s.angle, ang):
                continue
            L = s.length * k
            if p.stair_w_min_in <= L <= p.stair_w_max_in:
                a0, a1, o = _proj(s, ang)
                group.append((round(a0, 1), round(a1, 1), o, idx))
        buckets: dict = {}
        for a0, a1, o, idx in group:
            key = next((kk for kk in buckets if abs(kk[0] - a0) <= 2 / k and abs(kk[1] - a1) <= 2 / k), (a0, a1))
            buckets.setdefault(key, []).append((o, idx))
        for (a0, a1), items in buckets.items():
            items.sort()
            offs = [o for o, _ in items]
            # longest run of uniform spacing within tread range
            best = []
            run = [items[0]]
            for prev, cur in zip(items, items[1:]):
                sp = (cur[0] - prev[0]) * k
                ok = p.tread_min_in <= sp <= p.tread_max_in
                if ok and (len(run) < 2 or abs(sp - (run[1][0] - run[0][0]) * k) <= 0.05 * sp):
                    run.append(cur)
                else:
                    if len(run) > len(best):
                        best = run
                    run = [cur] if not ok else [prev, cur]
            if len(run) > len(best):
                best = run
            if len(best) < 4:
                continue
            u, n = _frame(ang)
            o0, o1 = best[0][0], best[-1][0]
            corners = [(a0 * u[0] + o * n[0], a0 * u[1] + o * n[1]) for o in (o0, o1)] + \
                      [(a1 * u[0] + o * n[0], a1 * u[1] + o * n[1]) for o in (o1, o0)]
            poly = Polygon(corners)
            if footprint is not None and not footprint.buffer(1e-6).contains(poly):
                continue
            if any(i in used for _, i in best):
                continue
            used.update(i for _, i in best)
            spacing = statistics.median([(b[0] - a[0]) for a, b in zip(best, best[1:])])
            out.append({"polygon": poly, "lines": len(best), "spacing_page": spacing, "width_page": a1 - a0, "axis_ang": ang})
    for st in out:
        grow = st["polygon"].buffer(12 / k)
        st["direction"] = None
        st["noted_risers"] = None
        for t in pp.texts:
            if grow.contains(Point(t.x, t.y)):
                m = re.search(r"\b(UP|DN|DOWN)\b", t.text.upper())
                if m:
                    st["direction"] = "UP" if m.group(1) == "UP" else "DN"
                r = re.search(r"\b(\d+)\s*R\b", t.text.upper())
                if r:
                    st["noted_risers"] = int(r.group(1))
    return out


# -- text helpers -------------------------------------------------------------------
USE_FROM_LABEL = [(r"BED|LIVING|DEN|FAMILY|OFFICE|STUDY|GREAT|DINING", "habitable"), (r"KITCHEN", "kitchen"),
                  (r"BATH|POWDER|TOILET|WC", "bathroom"), (r"LAUNDRY|UTIL", "laundry"), (r"HALL|FOYER|ENTRY|CORR|LANDING", "hallway")]


def use_from_label(label: str | None) -> str | None:
    if not label:
        return None
    up = label.upper()
    if "KITCHEN" in up:
        return "kitchen"
    for pat, use in USE_FROM_LABEL:
        if re.search(pat, up):
            return use
    return "other"


def is_dimension_text(s: str) -> bool:
    return U.parse_ft_in(s) is not None


def size_note(s: str):
    if re.search(r"\d\s*'.*[Xx\u00d7].*\d\s*'", U.normalize(s)):
        v = U.find_ft_in(s)
        if len(v) == 2:
            return v
    return None
