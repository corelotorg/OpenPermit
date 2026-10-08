# SPDX-License-Identifier: Apache-2.0
"""Read vector primitives from PDF pages (pdfplumber) and DXF model space (ezdxf).

Both readers produce the same ``PagePrimitives``: straight segments, circular arcs, other curves
and text runs in page units (PDF points with a bottom-left origin, or DXF drawing units), plus
the hints a detector may use (line weight or layer). No OCR: a page with no vector linework and
a raster image is reported as ``raster`` and left for human tracing.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Seg:
    x0: float
    y0: float
    x1: float
    y1: float
    width: float = 0.0
    heavy: bool | None = None  # None: no weight information
    layer: str | None = None

    @property
    def length(self) -> float:
        return math.hypot(self.x1 - self.x0, self.y1 - self.y0)

    @property
    def angle(self) -> float:
        """Direction in degrees, folded to [0, 180)."""
        return math.degrees(math.atan2(self.y1 - self.y0, self.x1 - self.x0)) % 180.0


@dataclass
class Arc:
    cx: float
    cy: float
    r: float
    a0: float  # degrees, counter-clockwise start
    a1: float  # degrees, counter-clockwise end (a1 > a0)
    width: float = 0.0
    layer: str | None = None

    def point(self, a_deg: float) -> tuple[float, float]:
        return self.cx + self.r * math.cos(math.radians(a_deg)), self.cy + self.r * math.sin(math.radians(a_deg))

    @property
    def sweep(self) -> float:
        return self.a1 - self.a0


@dataclass
class TextRun:
    text: str
    x: float  # centre
    y: float
    angle: float  # degrees
    size: float
    bbox: tuple[float, float, float, float]


@dataclass
class PagePrimitives:
    page: int
    width: float | None
    height: float | None
    units: str  # "pt" or a DXF unit name
    segs: list[Seg] = field(default_factory=list)
    arcs: list[Arc] = field(default_factory=list)
    curves: int = 0
    texts: list[TextRun] = field(default_factory=list)
    images: int = 0
    image_area_fraction: float = 0.0
    page_label: str | None = None
    weight_source: str = "none"  # lineweight | layer | none
    dxf_dims: list[dict] = field(default_factory=list)
    unit_in: float | None = None  # DXF: inches per drawing unit, from $INSUNITS

    @property
    def kind(self) -> str:
        if self.units != "pt":
            return "dxf"
        vector = len(self.segs) + len(self.arcs) >= 20
        if not vector and self.images and self.image_area_fraction > 0.3:
            return "raster"
        if vector and self.images and self.image_area_fraction > 0.3:
            return "mixed"
        return "vector" if vector else "empty"


# -- geometry helpers ---------------------------------------------------------
def _bezier(p0, p1, p2, p3, n=12):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def fit_arc(pts: np.ndarray, tol_rel: float = 0.01) -> Arc | None:
    """Least-squares circle through points; returns an Arc if the residual is small and the sweep < 360."""
    if len(pts) < 5:
        return None
    x, y = pts[:, 0], pts[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy, c = sol
    r2 = c + cx ** 2 + cy ** 2
    if r2 <= 0:
        return None
    r = math.sqrt(r2)
    resid = np.abs(np.hypot(x - cx, y - cy) - r).max()
    if resid > tol_rel * r + 1e-6:
        return None
    ang = np.degrees(np.unwrap(np.arctan2(y - cy, x - cx)))
    a_start, a_end = float(ang[0]), float(ang[-1])
    if abs(a_end - a_start) >= 359:
        return None
    lo, hi = min(a_start, a_end), max(a_start, a_end)
    return Arc(float(cx), float(cy), r, lo, hi)


# -- PDF ----------------------------------------------------------------------
def _flip(h, p):
    return float(p[0]), float(h - p[1])


def _path_to_prims(path, h, width, segs, arcs):
    """Decompose a pdfplumber path (top-left coordinates) into segments and fitted arcs."""
    cur = start = None
    bez_run: list = []
    curves = 0

    def flush():
        nonlocal bez_run, curves
        if bez_run:
            pts = np.vstack([_bezier(*b) for b in bez_run])
            a = fit_arc(pts)
            if a is not None:
                a.width = width
                arcs.append(a)
            else:
                curves += 1
            bez_run = []

    for cmd in path:
        op = cmd[0]
        if op == "m":
            flush()
            cur = start = _flip(h, cmd[1])
        elif op == "l":
            flush()
            p = _flip(h, cmd[1])
            if cur is not None and p != cur:
                segs.append(Seg(cur[0], cur[1], p[0], p[1], width))
            cur = p
        elif op == "c":
            pts = [_flip(h, q) for q in cmd[1:]]
            if cur is not None:
                bez_run.append((cur, pts[0], pts[1], pts[2]))
            cur = pts[2]
        elif op == "h":
            flush()
            if cur is not None and start is not None and cur != start:
                segs.append(Seg(cur[0], cur[1], start[0], start[1], width))
            cur = start
    flush()
    return curves


def text_runs_from_chars(chars, h) -> list[TextRun]:
    """Group characters into runs along their writing direction (handles rotated text)."""
    items = []
    for ch in chars:
        if not ch.get("text"):
            continue
        a, b = ch["matrix"][0], ch["matrix"][1]
        ang = math.degrees(math.atan2(b, a))
        ang = round(ang / 90.0) * 90.0 if abs(ang - round(ang / 90.0) * 90.0) < 2 else ang
        cx, cy = (ch["x0"] + ch["x1"]) / 2, h - (ch["top"] + ch["bottom"]) / 2
        u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
        n = (-u[1], u[0])
        ext = abs(ch["x1"] - ch["x0"]) * abs(u[0]) + abs(ch["bottom"] - ch["top"]) * abs(u[1])
        items.append(dict(t=ch["text"], ang=ang, along=cx * u[0] + cy * u[1], perp=cx * n[0] + cy * n[1], ext=ext,
                          size=float(ch.get("size") or 8), box=(ch["x0"], h - ch["bottom"], ch["x1"], h - ch["top"])))
    runs = []
    items.sort(key=lambda d: (d["ang"], d["perp"], d["along"]))
    groups: list[list[dict]] = []
    for it in items:
        g = groups[-1] if groups else None
        if g and g[0]["ang"] == it["ang"] and abs(it["perp"] - g[0]["perp"]) <= 0.3 * it["size"]:
            g.append(it)
        else:
            groups.append([it])
    for g in groups:
        g.sort(key=lambda d: d["along"])
        cur = [g[0]]
        for it in g[1:]:
            prev = cur[-1]
            gap = (it["along"] - it["ext"] / 2) - (prev["along"] + prev["ext"] / 2)
            if gap > 1.2 * it["size"]:
                runs.append(_mk_run(cur))
                cur = [it]
            else:
                if gap > 0.25 * it["size"] and prev["t"] != " " and it["t"] != " ":
                    cur.append(dict(prev, t=" ", ext=0))
                cur.append(it)
        runs.append(_mk_run(cur))
    return [r for r in runs if r.text]


def _mk_run(items) -> TextRun:
    text = re.sub(r"\s+", " ", "".join(i["t"] for i in items)).strip()
    boxes = [i["box"] for i in items if i["t"] != " "] or [items[0]["box"]]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    return TextRun(text, (x0 + x1) / 2, (y0 + y1) / 2, items[0]["ang"], max(i["size"] for i in items), (x0, y0, x1, y1))


def _assign_weights(pp: PagePrimitives):
    widths = sorted({round(s.width, 3) for s in pp.segs if s.width > 0})
    if len(widths) >= 2 and widths[-1] / widths[0] >= 1.8:
        cut = math.sqrt(widths[-1] * widths[0])
        for s in pp.segs:
            s.heavy = s.width >= cut
        pp.weight_source = "lineweight"


def read_pdf(path: str | Path) -> list[PagePrimitives]:
    import pdfplumber
    from pypdf import PdfReader

    labels = []
    try:
        r = PdfReader(str(path))
        labels = list(r.page_labels) if r.page_labels else []
    except Exception:  # unreadable labels: fall back to page numbers
        labels = []
    out = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            h, w = float(page.height), float(page.width)
            pp = PagePrimitives(i, w, h, "pt", page_label=labels[i - 1] if i - 1 < len(labels) else str(i))
            for obj in list(page.lines) + list(page.curves):
                width = float(obj.get("linewidth") or 0.0)
                if obj.get("stroke") is False and obj.get("fill"):
                    continue  # fills without stroke (hatches, poché) are not linework here
                path = obj.get("path") or [("m", obj["pts"][0])] + [("l", p) for p in obj["pts"][1:]]
                pp.curves += _path_to_prims(path, h, width, pp.segs, pp.arcs)
            for rc in page.rects:
                if rc.get("stroke") is False:
                    continue
                width = float(rc.get("linewidth") or 0.0)
                x0, x1, y0, y1 = rc["x0"], rc["x1"], h - rc["bottom"], h - rc["top"]
                for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
                    pp.segs.append(Seg(a[0], a[1], b[0], b[1], width))
            pp.images = len(page.images)
            if page.images:
                area = sum(abs((im["x1"] - im["x0"]) * (im["bottom"] - im["top"])) for im in page.images)
                pp.image_area_fraction = min(1.0, area / (w * h))
            pp.texts = text_runs_from_chars(page.chars, h)
            pp.segs = [s for s in pp.segs if s.length > 1e-6]
            _assign_weights(pp)
            pp.arcs += arcs_from_polylines(pp.segs)
            out.append(pp)
    return out


# -- DXF ----------------------------------------------------------------------
INSUNITS_IN = {1: 1.0, 2: 12.0, 4: 1 / 25.4, 5: 1 / 2.54, 6: 1 / 0.0254, 3: 63360.0, 10: 36.0}
WALL_LAYER = re.compile(r"(^|[-_ ])WALL", re.IGNORECASE)


def read_dxf(path: str | Path, wall_layer: re.Pattern = WALL_LAYER) -> PagePrimitives:
    import ezdxf

    doc = ezdxf.readfile(str(path))
    units = int(doc.header.get("$INSUNITS", 0) or 0)
    pp = PagePrimitives(1, None, None, {1: "in", 2: "ft", 4: "mm", 5: "cm", 6: "m"}.get(units, "unitless"),
                        unit_in=INSUNITS_IN.get(units), page_label=Path(path).stem)

    def add_entity(e, depth=0):
        t = e.dxftype()
        layer = e.dxf.get("layer", "0")
        lw = e.dxf.get("lineweight", -1)
        width = max(lw, 0) / 100.0
        if t == "LINE":
            s, en = e.dxf.start, e.dxf.end
            pp.segs.append(Seg(s.x, s.y, en.x, en.y, width, layer=layer))
        elif t in ("LWPOLYLINE", "POLYLINE"):
            pts = [(p[0], p[1]) for p in (e.get_points("xy") if t == "LWPOLYLINE" else [v.dxf.location for v in e.vertices])]
            closed = e.closed if t == "LWPOLYLINE" else e.is_closed
            if closed and pts:
                pts = pts + [pts[0]]
            for a, b in zip(pts, pts[1:]):
                pp.segs.append(Seg(a[0], a[1], b[0], b[1], width, layer=layer))
        elif t == "ARC":
            a0, a1 = e.dxf.start_angle % 360, e.dxf.end_angle % 360
            if a1 <= a0:
                a1 += 360
            pp.arcs.append(Arc(e.dxf.center.x, e.dxf.center.y, e.dxf.radius, a0, a1, width, layer))
        elif t in ("CIRCLE", "ELLIPSE", "SPLINE"):
            pp.curves += 1
        elif t in ("TEXT", "MTEXT"):
            txt = e.dxf.text if t == "TEXT" else e.plain_text()
            ins = e.dxf.insert
            if t == "TEXT" and e.dxf.get("halign", 0) or (t == "TEXT" and e.dxf.get("valign", 0)):
                ins = e.dxf.get("align_point", ins)
            h = e.dxf.get("height", 1.0) if t == "TEXT" else e.dxf.get("char_height", 1.0)
            pp.texts.append(TextRun(re.sub(r"\s+", " ", txt).strip(), ins.x, ins.y, e.dxf.get("rotation", 0.0), h,
                                    (ins.x, ins.y, ins.x, ins.y)))
        elif t == "DIMENSION":
            try:
                meas = float(e.get_measurement())
            except Exception:  # dimension types without a scalar measurement
                meas = None
            d2, d3, dp = e.dxf.get("defpoint2"), e.dxf.get("defpoint3"), e.dxf.get("defpoint")
            ang = e.dxf.get("angle", 0.0)
            if d2 is not None and d3 is not None and dp is not None:
                u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
                def proj(p):
                    t_ = (p.x - dp.x) * u[0] + (p.y - dp.y) * u[1]
                    return (dp.x + t_ * u[0], dp.y + t_ * u[1])
                text = e.dxf.get("text", "<>")
                pp.dxf_dims.append({"p0": proj(d2), "p1": proj(d3), "measurement": meas, "text": text, "layer": layer})
        elif t == "INSERT" and depth < 4:
            for ve in e.virtual_entities():
                add_entity(ve, depth + 1)

    for e in doc.modelspace():
        add_entity(e)
    pp.segs = [s for s in pp.segs if s.length > 1e-9]
    if any(wall_layer.search(s.layer or "") for s in pp.segs):
        for s in pp.segs:
            s.heavy = bool(wall_layer.search(s.layer or ""))
        pp.weight_source = "layer"
    else:
        _assign_weights(pp)
    pp.arcs += arcs_from_polylines(pp.segs)
    xs = [c for s in pp.segs for c in (s.x0, s.x1)]
    ys = [c for s in pp.segs for c in (s.y0, s.y1)]
    if xs:
        pp.width, pp.height = max(xs) - min(xs), max(ys) - min(ys)
    return pp


def arcs_from_polylines(segs: list[Seg], min_segments: int = 4, max_turn_deg: float = 35.0) -> list[Arc]:
    """Recover circular arcs drawn as chains of short straight segments (common in CAD exports).

    Chains follow shared endpoints (0.01 unit), turn consistently in one direction by at most
    ``max_turn_deg`` per vertex, and must fit a circle (``fit_arc``). Heavy segments are skipped."""
    key = lambda p: (round(p[0], 2), round(p[1], 2))  # noqa: E731
    ends: dict = {}
    thin = [s for s in segs if not s.heavy]
    for i, s in enumerate(thin):
        ends.setdefault(key((s.x0, s.y0)), []).append(i)
        ends.setdefault(key((s.x1, s.y1)), []).append(i)
    used: set[int] = set()
    arcs = []

    def other(i, p):
        s = thin[i]
        return (s.x1, s.y1) if key((s.x0, s.y0)) == key(p) else (s.x0, s.y0)

    for i, s in enumerate(thin):
        if i in used:
            continue
        # walk both directions from segment i through degree-2 vertices
        chain_pts = [(s.x0, s.y0), (s.x1, s.y1)]
        members = [i]
        for direction in (1, 0):
            p = chain_pts[-1] if direction else chain_pts[0]
            prev = i
            while True:
                nbrs = [j for j in ends.get(key(p), []) if j != prev and j not in members
                        and abs(thin[j].length - s.length) <= 0.3 * s.length]
                if len(nbrs) != 1:
                    break
                j = nbrs[0]
                q = other(j, p)
                members.append(j)
                if direction:
                    chain_pts.append(q)
                else:
                    chain_pts.insert(0, q)
                prev, p = j, q
        if len(members) < min_segments:
            continue
        turns = []
        for a, b, c in zip(chain_pts, chain_pts[1:], chain_pts[2:]):
            h1 = math.atan2(b[1] - a[1], b[0] - a[0])
            h2 = math.atan2(c[1] - b[1], c[0] - b[0])
            turns.append((math.degrees(h2 - h1) + 540) % 360 - 180)
        if not turns or not (all(t > 0.5 for t in turns) or all(t < -0.5 for t in turns)) or max(abs(t) for t in turns) > max_turn_deg:
            continue
        a = fit_arc(np.array(chain_pts, dtype=float), tol_rel=0.02)
        if a is not None:
            a.width = s.width
            a.layer = s.layer
            arcs.append(a)
            used.update(members)
    return arcs
