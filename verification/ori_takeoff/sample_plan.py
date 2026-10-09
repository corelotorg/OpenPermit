# SPDX-License-Identifier: Apache-2.0
"""ORI-authored CC0 sample single-family plan: vector PDF, DXF and ground-truth overlay.

The house is invented for testing. It is not a design for any real site, it has not been checked
against any code, and it is not for construction. Two storeys, 32'-0" x 28'-0" outside, 6 in
exterior walls and 4 1/2 in interior walls, a straight stair of 14 risers and 13 treads at
10 in, five rooms per floor, 7 + 4 doors, 7 + 8 windows, overall and chain dimensions, room
labels with size notes, a scale note, plumbing and kitchen fixtures as distractor linework.

Everything here (geometry, drawings and the ground truth) is dedicated to the public domain
under CC0 1.0 by the ORI project. Ground truth comes from the design data in this file, not
from the extractor.

Design coordinates are inches with the origin at the outside south-west corner, x east, y north.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry import Polygon as SPoly
from shapely.geometry import box
from shapely.ops import unary_union

from . import overlay as ov
from .units import format_ft_in

SCALE = 48.0  # 1/4" = 1'-0": real inches per paper inch
PT_PER_IN_REAL = 72.0 / SCALE  # 1.5 pt per real inch
PAGE_W, PAGE_H = 24 * 72.0, 18 * 72.0  # ARCH C landscape
ORIGIN_PT = (216.0, 324.0)
EXT_T, INT_T = 6.0, 4.5
FLOOR_TO_FLOOR_IN = 105.0  # 14 risers at 7 1/2 in; carried in a note and the IFC export only
CEILING_IN = 96.0


@dataclass
class Wall:
    id: str
    x0: float
    y0: float
    x1: float
    y1: float
    exterior: bool = False

    @property
    def horizontal(self) -> bool:
        return (self.x1 - self.x0) >= (self.y1 - self.y0)

    @property
    def thickness(self) -> float:
        return (self.y1 - self.y0) if self.horizontal else (self.x1 - self.x0)

    def axis(self) -> tuple[tuple[float, float], tuple[float, float]]:
        trim = self.thickness / 2 if self.exterior else 0.0  # exterior axes meet at centreline corners
        if self.horizontal:
            c = (self.y0 + self.y1) / 2
            return (self.x0 + trim, c), (self.x1 - trim, c)
        c = (self.x0 + self.x1) / 2
        return (c, self.y0 + trim), (c, self.y1 - trim)


@dataclass
class Opening:
    id: str
    kind: str  # door | window
    wall: str
    a: float  # start along the wall (x for horizontal walls, y for vertical)
    b: float
    hinge: str = "a"  # door: hinge at a or b
    swing: int = 1  # door: leaf opens toward +normal (+y or +x) or -normal

    @property
    def width(self) -> float:
        return self.b - self.a


@dataclass
class Space:
    id: str
    name: str
    use: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def area_ft2(self) -> float:
        return (self.x1 - self.x0) * (self.y1 - self.y0) / 144.0


@dataclass
class Stair:
    id: str
    x0: float
    y0: float
    x1: float
    y1: float
    risers: int
    direction: str  # UP | DN

    @property
    def tread_depth(self) -> float:
        return (self.y1 - self.y0) / (self.risers - 1)


@dataclass
class Floor:
    sheet: str
    title: str
    storey: str
    elevation_in: float
    walls: list[Wall]
    openings: list[Opening]
    spaces: list[Space]
    stair: Stair
    dims: list[tuple] = field(default_factory=list)  # (x0, y0, x1, y1, offset_side, offset_in)
    fixtures: list[list[tuple[float, float]]] = field(default_factory=list)
    ellipses: list[tuple[float, float, float, float]] = field(default_factory=list)  # cx, cy, rx, ry


def _ext_walls() -> list[Wall]:
    return [Wall("WS", 0, 0, 384, EXT_T, True), Wall("WN", 0, 336 - EXT_T, 384, 336, True),
            Wall("WW", 0, 0, EXT_T, 336, True), Wall("WE", 384 - EXT_T, 0, 384, 336, True)]


def floors() -> list[Floor]:
    f1 = Floor(
        "A-101", "FIRST FLOOR PLAN", "Level 1", 0.0,
        _ext_walls() + [Wall("V1", 204, 6, 208.5, 330), Wall("HL", 6, 204, 204, 208.5),
                        Wall("H1", 208.5, 145.5, 378, 150), Wall("V2", 334, 6, 338.5, 145.5)],
        [Opening("D101", "door", "WS", 230, 266, "a", 1), Opening("D102", "door", "V1", 40, 72, "a", -1),
         Opening("D103", "door", "HL", 160, 192, "b", -1), Opening("D104", "door", "V1", 260, 292, "a", 1),
         Opening("D105", "door", "H1", 220, 252, "a", 1), Opening("D106", "door", "H1", 344, 372, "b", -1),
         Opening("D107", "door", "WN", 300, 336, "b", -1),
         Opening("W101", "window", "WS", 60, 120), Opening("W102", "window", "WW", 80, 128),
         Opening("W103", "window", "WW", 240, 288), Opening("W104", "window", "WN", 70, 130),
         Opening("W105", "window", "WN", 220, 268), Opening("W106", "window", "WE", 220, 280),
         Opening("W107", "window", "WE", 90, 114)],
        [Space("S101", "LIVING", "habitable", 6, 6, 204, 204), Space("S102", "DEN", "habitable", 6, 208.5, 204, 330),
         Space("S103", "FOYER", "hallway", 208.5, 6, 334, 145.5), Space("S104", "POWDER / LAUNDRY", "bathroom", 338.5, 6, 378, 145.5),
         Space("S105", "KITCHEN / DINING", "kitchen", 208.5, 150, 378, 330)],
        Stair("ST1", 298, 14, 334, 144, 14, "UP"),
        fixtures=[[(378, 170), (353, 170), (353, 320), (378, 320)], [(358, 220), (374, 220), (374, 250), (358, 250), (358, 220)],
                  [(366, 138), (376, 138), (376, 120), (366, 120), (366, 138)], [(342, 40), (372, 40), (372, 70), (342, 70), (342, 40)]],
        ellipses=[(357, 129, 7, 9), (357, 55, 10, 10)],
    )
    f2 = Floor(
        "A-102", "SECOND FLOOR PLAN", "Level 2", FLOOR_TO_FLOOR_IN,
        _ext_walls() + [Wall("V1", 204, 6, 208.5, 330), Wall("HL", 6, 120, 204, 124.5),
                        Wall("H1", 208.5, 186, 378, 190.5), Wall("V2", 334, 6, 338.5, 186)],
        [Opening("D201", "door", "V1", 60, 92, "a", -1), Opening("D202", "door", "V1", 150, 182, "b", -1),
         Opening("D203", "door", "H1", 220, 252, "a", 1), Opening("D204", "door", "V2", 150, 178, "a", 1),
         Opening("W201", "window", "WS", 70, 130), Opening("W202", "window", "WW", 40, 80),
         Opening("W203", "window", "WW", 200, 248), Opening("W204", "window", "WN", 60, 120),
         Opening("W205", "window", "WN", 260, 320), Opening("W206", "window", "WE", 230, 278),
         Opening("W207", "window", "WE", 80, 104), Opening("W208", "window", "WS", 240, 276)],
        [Space("S201", "BEDROOM 2", "habitable", 6, 6, 204, 120), Space("S202", "BEDROOM 1", "habitable", 6, 124.5, 204, 330),
         Space("S203", "HALL", "hallway", 208.5, 6, 334, 186), Space("S204", "BATH", "bathroom", 338.5, 6, 378, 186),
         Space("S205", "BEDROOM 3", "habitable", 208.5, 190.5, 378, 330)],
        Stair("ST2", 298, 14, 334, 144, 14, "DN"),
        fixtures=[[(346, 8), (376, 8), (376, 68), (346, 68), (346, 8)], [(350, 14), (372, 14), (372, 62), (350, 62), (350, 14)],
                  [(366, 120), (376, 120), (376, 102), (366, 102), (366, 120)]],
        ellipses=[(357, 111, 7, 9), (357, 160, 9, 7)],
    )
    for f in (f1, f2):
        h1 = next(w for w in f.walls if w.id == "H1")
        hc = (h1.y0 + h1.y1) / 2
        f.dims = [(0, 0, 384, 0, "S", 60), (0, 0, 0, 336, "W", 60),
                  (0, 336, 206.25, 336, "N", 48), (206.25, 336, 384, 336, "N", 48),
                  (384, 0, 384, hc, "E", 48), (384, hc, 384, 336, "E", 48)]
    return [f1, f2]


def wall_by_id(f: Floor, wid: str) -> Wall:
    return next(w for w in f.walls if w.id == wid)


def opening_rect(f: Floor, o: Opening) -> tuple[float, float, float, float]:
    w = wall_by_id(f, o.wall)
    return (o.a, w.y0, o.b, w.y1) if w.horizontal else (w.x0, o.a, w.x1, o.b)


def wall_polygon(f: Floor):
    walls = unary_union([box(w.x0, w.y0, w.x1, w.y1) for w in f.walls])
    holes = unary_union([box(*opening_rect(f, o)) for o in f.openings])
    return walls.difference(holes)


def door_geometry(f: Floor, o: Opening):
    """Hinge point, leaf end point, closing jamb point, arc centre angles (degrees) in design inches."""
    w = wall_by_id(f, o.wall)
    if w.horizontal:
        face = w.y1 if o.swing > 0 else w.y0
        hx, jx = (o.a, o.b) if o.hinge == "a" else (o.b, o.a)
        hinge, jamb = (hx, face), (jx, face)
        leaf = (hx, face + o.swing * o.width)
    else:
        face = w.x1 if o.swing > 0 else w.x0
        hy, jy = (o.a, o.b) if o.hinge == "a" else (o.b, o.a)
        hinge, jamb = (face, hy), (face, jy)
        leaf = (face + o.swing * o.width, hy)
    a0 = math.degrees(math.atan2(jamb[1] - hinge[1], jamb[0] - hinge[0]))
    a1 = math.degrees(math.atan2(leaf[1] - hinge[1], leaf[0] - hinge[0]))
    ext = (a1 - a0 + 540) % 360 - 180
    return hinge, leaf, jamb, a0, ext


def window_lines(f: Floor, o: Opening):
    w = wall_by_id(f, o.wall)
    if w.horizontal:
        ys = (w.y0, (w.y0 + w.y1) / 2, w.y1)
        return [((o.a, y), (o.b, y)) for y in ys]
    xs = (w.x0, (w.x0 + w.x1) / 2, w.x1)
    return [((x, o.a), (x, o.b)) for x in xs]


def stair_lines(s: Stair):
    return [((s.x0, s.y0 + i * s.tread_depth), (s.x1, s.y0 + i * s.tread_depth)) for i in range(s.risers)]


def dim_geometry(d):
    """Dimension line endpoints, extension lines, text anchor/angle, value (design inches)."""
    x0, y0, x1, y1, side, off = d
    if side in ("S", "N"):
        yy = (y0 - off) if side == "S" else (y0 + off)
        p0, p1 = (x0, yy), (x1, yy)
        ext = [((x0, y0 + (-6 if side == "S" else 6)), (x0, yy + (-6 if side == "S" else 6))),
               ((x1, y1 + (-6 if side == "S" else 6)), (x1, yy + (-6 if side == "S" else 6)))]
        value = abs(x1 - x0)
        text_at, angle = ((x0 + x1) / 2, yy + 4), 0
    else:
        xx = (x0 - off) if side == "W" else (x0 + off)
        p0, p1 = (xx, y0), (xx, y1)
        ext = [((x0 + (-6 if side == "W" else 6), y0), (xx + (-6 if side == "W" else 6), y0)),
               ((x1 + (-6 if side == "W" else 6), y1), (xx + (-6 if side == "W" else 6), y1))]
        value = abs(y1 - y0)
        text_at, angle = (xx - 4, (y0 + y1) / 2), 90
    return p0, p1, ext, text_at, angle, value


# ---------------------------------------------------------------------------------------------
# PDF
def to_page(x: float, y: float) -> tuple[float, float]:
    return ORIGIN_PT[0] + x * PT_PER_IN_REAL, ORIGIN_PT[1] + y * PT_PER_IN_REAL


def rotated_to_page(rot_deg: float):
    """Design inches to page points with the whole sheet rotated by ``rot_deg`` about the page centre."""
    cx, cy = PAGE_W / 2, PAGE_H / 2
    ca, sa = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))

    def tp(x, y):
        px, py = to_page(x, y)
        dx, dy = px - cx, py - cy
        return cx + ca * dx - sa * dy, cy + sa * dx + ca * dy
    return tp


@dataclass
class Noise:
    """Export artefacts seen in real CAD-to-PDF output, for robustness measurement (deterministic)."""
    seed: int = 7
    rotate_deg: float = 0.4  # sheet scanned/plotted slightly rotated in its page
    break_wall_outlines: bool = True  # outlines as loose segments, ends trimmed 0-0.4 in
    polyline_arcs_every: int = 2  # every n-th door swing drawn as a 6-segment polyline instead of a curve
    hatch_walls: bool = True  # thin 45-degree hatch inside walls
    dashed_overhead: bool = True  # dashed line distractors (upper cabinets)


def write_pdf(path: str | Path, fl: list[Floor] | None = None, noise: Noise | None = None,
              scale_note: str | None = 'SCALE: 1/4" = 1\'-0"', draw_dims: bool = True) -> Path:
    """Write the sample plan. ``scale_note=None`` omits the note and ``draw_dims=False`` omits dimensions
    (test variants for unknown, conflicting and calibrated scale)."""
    from reportlab.lib.colors import Color
    from reportlab.pdfgen import canvas

    fl = fl or floors()
    path = Path(path)
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H), invariant=1, pageCompression=0)
    c.setTitle("ORI sample single-family plan (CC0, synthetic, not for construction)")
    c.setAuthor("ORI project")
    c.setSubject("CC0 1.0 Universal; synthetic test plan")
    for i, f in enumerate(fl):
        if i == 0:
            c.addPageLabel(0, style="D", start=101, prefix="A-")
        if noise:
            c.saveState()
            c.translate(PAGE_W / 2, PAGE_H / 2)
            c.rotate(noise.rotate_deg)
            c.translate(-PAGE_W / 2, -PAGE_H / 2)
        _draw_floor_pdf(c, f, Color, noise, scale_note, draw_dims)
        if noise:
            c.restoreState()
        c.showPage()
    c.save()
    return path


def _ln(c, p, q):
    (x0, y0), (x1, y1) = to_page(*p), to_page(*q)
    c.line(x0, y0, x1, y1)


def _draw_floor_pdf(c, f: Floor, Color, noise: Noise | None = None, scale_note: str | None = None, draw_dims: bool = True):
    import random
    rnd = random.Random(noise.seed if noise else 0)
    thin, heavy = 0.35, 1.4
    # sheet border and title block
    c.setLineWidth(1.0)
    c.rect(36, 36, PAGE_W - 72, PAGE_H - 72)
    c.setLineWidth(thin)
    tb = (PAGE_W - 36 - 360, 36)
    c.rect(tb[0], tb[1], 360, 144)
    for yy in (72, 108, 144):
        c.line(tb[0], yy, tb[0] + 360, yy)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(tb[0] + 10, 156, "ORI SAMPLE SINGLE-FAMILY HOUSE")
    c.setFont("Helvetica", 9)
    c.drawString(tb[0] + 10, 120, f"{f.title}")
    c.drawString(tb[0] + 10, 84, "CC0 1.0 - ORI-AUTHORED SYNTHETIC SAMPLE - NOT FOR CONSTRUCTION")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(tb[0] + 10, 46, f"SHEET {f.sheet}")
    # walls: union minus openings, filled and stroked heavy
    poly = wall_polygon(f)
    geoms = getattr(poly, "geoms", [poly])
    if noise and noise.hatch_walls:
        from shapely.geometry import LineString as SLine
        c.setLineWidth(0.2)
        for kk in range(-400, 800, 4):
            hl = SLine([(kk, -10), (kk + 400, 390)]).intersection(poly)
            for part in getattr(hl, "geoms", [hl]):
                if part.length > 0 and part.geom_type == "LineString":
                    _ln(c, part.coords[0], part.coords[-1])
    c.setLineWidth(heavy)
    c.setFillColor(Color(0.8, 0.8, 0.8))
    if noise and noise.break_wall_outlines:
        for g in geoms:
            for ring in [g.exterior] + list(g.interiors):
                pts = list(ring.coords)
                for p0, p1 in zip(pts, pts[1:]):
                    L = math.dist(p0, p1)
                    if L < 1.0:
                        continue
                    t0, t1 = rnd.uniform(0, 0.4) / L, rnd.uniform(0, 0.4) / L
                    q0 = (p0[0] + (p1[0] - p0[0]) * t0, p0[1] + (p1[1] - p0[1]) * t0)
                    q1 = (p1[0] - (p1[0] - p0[0]) * t1, p1[1] - (p1[1] - p0[1]) * t1)
                    _ln(c, q0, q1)
        geoms = []
    for g in geoms:
        p = c.beginPath()
        for ring in [g.exterior] + list(g.interiors):
            pts = [to_page(x, y) for x, y in list(ring.coords)[:-1]]
            p.moveTo(*pts[0])
            for q in pts[1:]:
                p.lineTo(*q)
            p.close()
        c.drawPath(p, stroke=1, fill=1, fillMode=0)
    c.setFillColor(Color(0, 0, 0))
    c.setLineWidth(thin)
    for n_o, o in enumerate(f.openings):
        if o.kind == "door":
            hinge, leaf, jamb, a0, ext = door_geometry(f, o)
            _ln(c, hinge, leaf)
            if noise and noise.polyline_arcs_every and n_o % noise.polyline_arcs_every == 0:
                pts = [(hinge[0] + o.width * math.cos(math.radians(a0 + ext * t / 6)),
                        hinge[1] + o.width * math.sin(math.radians(a0 + ext * t / 6))) for t in range(7)]
                for p0, p1 in zip(pts, pts[1:]):
                    _ln(c, p0, p1)
                continue
            r = o.width * PT_PER_IN_REAL
            hx, hy = to_page(*hinge)
            p = c.beginPath()
            p.arc(hx - r, hy - r, hx + r, hy + r, startAng=a0, extent=ext)
            c.drawPath(p, stroke=1, fill=0)
        else:
            for p0, p1 in window_lines(f, o):
                _ln(c, p0, p1)
    # stair
    s = f.stair
    for p0, p1 in stair_lines(s):
        _ln(c, p0, p1)
    _ln(c, (s.x0, s.y0), (s.x0, s.y1))
    _ln(c, (s.x1, s.y0), (s.x1, s.y1))
    mx = (s.x0 + s.x1) / 2
    _ln(c, (mx, s.y0 + 4), (mx, s.y1 - 8))
    _ln(c, (mx, s.y1 - 8), (mx - 3, s.y1 - 16))
    _ln(c, (mx, s.y1 - 8), (mx + 3, s.y1 - 16))
    c.setFont("Helvetica", 7)
    tx, ty = to_page(mx - 6, s.y0 - 7)
    c.drawString(tx, ty, f"{s.direction} 14R")
    if noise and noise.dashed_overhead:
        c.setDash(3, 2)
        for poly_pts in f.fixtures[:1]:
            off = [(x - 12 if x < 378 else x, y) for x, y in poly_pts]
            for p0, p1 in zip(off, off[1:]):
                _ln(c, p0, p1)
        c.setDash()
    # fixtures (distractors)
    for poly_pts in f.fixtures:
        for p0, p1 in zip(poly_pts, poly_pts[1:]):
            _ln(c, p0, p1)
    for cx, cy, rx, ry in f.ellipses:
        x, y = to_page(cx, cy)
        c.ellipse(x - rx * PT_PER_IN_REAL, y - ry * PT_PER_IN_REAL, x + rx * PT_PER_IN_REAL, y + ry * PT_PER_IN_REAL)
    # dimensions
    for d in (f.dims if draw_dims else []):
        p0, p1, ext, (tx, ty), angle, value = dim_geometry(d)
        _ln(c, p0, p1)
        for e0, e1 in ext:
            _ln(c, e0, e1)
        for (x, y) in (p0, p1):
            _ln(c, (x - 3, y - 3), (x + 3, y + 3))
        c.setFont("Helvetica", 8)
        px, py = to_page(tx, ty)
        c.saveState()
        c.translate(px, py)
        c.rotate(angle)
        c.drawCentredString(0, 0, format_ft_in(value))
        c.restoreState()
    # room labels with size notes
    for sp in f.spaces:
        cx, cy = to_page((sp.x0 + sp.x1) / 2, (sp.y0 + sp.y1) / 2)
        if sp.id in ("S103",):
            cx, cy = to_page(250, 100)
        if sp.id in ("S203",):
            cx, cy = to_page(250, 120)
        if sp.id in ("S104", "S204"):
            cy = to_page(0, 95 if sp.id == "S104" else 130)[1]
        c.setFont("Helvetica-Bold", 7 if sp.x1 - sp.x0 < 60 else 9)
        name_lines = sp.name.split(" / ") if sp.x1 - sp.x0 < 60 else [sp.name]
        for k, nl in enumerate(name_lines):
            c.drawCentredString(cx, cy + 4 - 9 * k, nl)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cx, cy - 6 - 9 * (len(name_lines) - 1),
                            f"{format_ft_in(sp.x1 - sp.x0)} X {format_ft_in(sp.y1 - sp.y0)}")
    # drawing title and scale note
    tx, ty = to_page(0, -110)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(tx, ty, f.title)
    c.setFont("Helvetica", 9)
    if scale_note:
        c.drawString(tx, ty - 14, scale_note)
    c.drawString(tx, ty - 28, "FLOOR TO FLOOR 8'-9\" (14 RISERS AT 7 1/2\")")


# ---------------------------------------------------------------------------------------------
# DXF
LAYERS = {"A-WALL": 7, "A-DOOR": 2, "A-GLAZ": 4, "A-FLOR-STRS": 3, "A-FLOR-FIXT": 8, "A-ANNO-TEXT": 7, "A-ANNO-DIMS": 1}


def write_dxf(path: str | Path, f: Floor) -> Path:
    import ezdxf
    from ezdxf.enums import TextEntityAlignment

    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 1  # inches
    doc.header["$MEASUREMENT"] = 0
    for name, color in LAYERS.items():
        doc.layers.add(name, color=color)
    msp = doc.modelspace()
    poly = wall_polygon(f)
    for g in getattr(poly, "geoms", [poly]):
        for ring in [g.exterior] + list(g.interiors):
            msp.add_lwpolyline(list(ring.coords)[:-1], close=True, dxfattribs={"layer": "A-WALL", "lineweight": 50})
    for o in f.openings:
        if o.kind == "door":
            hinge, leaf, jamb, a0, ext = door_geometry(f, o)
            msp.add_line(hinge, leaf, dxfattribs={"layer": "A-DOOR"})
            s, e = (a0, a0 + ext) if ext > 0 else (a0 + ext, a0)
            msp.add_arc(hinge, o.width, s, e, dxfattribs={"layer": "A-DOOR"})
        else:
            for p0, p1 in window_lines(f, o):
                msp.add_line(p0, p1, dxfattribs={"layer": "A-GLAZ"})
    s = f.stair
    for p0, p1 in stair_lines(s):
        msp.add_line(p0, p1, dxfattribs={"layer": "A-FLOR-STRS"})
    msp.add_line((s.x0, s.y0), (s.x0, s.y1), dxfattribs={"layer": "A-FLOR-STRS"})
    msp.add_line((s.x1, s.y0), (s.x1, s.y1), dxfattribs={"layer": "A-FLOR-STRS"})
    mx = (s.x0 + s.x1) / 2
    msp.add_text(f"{s.direction} 14R", height=4.5, dxfattribs={"layer": "A-ANNO-TEXT"}).set_placement((mx - 6, s.y0 - 7))
    for pts in f.fixtures:
        msp.add_lwpolyline(pts, dxfattribs={"layer": "A-FLOR-FIXT"})
    for cx, cy, rx, ry in f.ellipses:
        if rx >= ry:
            msp.add_ellipse((cx, cy), major_axis=(rx, 0), ratio=ry / rx, dxfattribs={"layer": "A-FLOR-FIXT"})
        else:
            msp.add_ellipse((cx, cy), major_axis=(0, ry), ratio=rx / ry, dxfattribs={"layer": "A-FLOR-FIXT"})
    for d in f.dims:
        x0, y0, x1, y1, side, off = d
        p0, p1, ext, text_at, angle, value = dim_geometry(d)
        base = p0
        dim = msp.add_linear_dim(base=base, p1=(x0, y0), p2=(x1, y1), angle=angle, dimstyle="EZDXF",
                                 override={"dimtxt": 6, "dimasz": 3, "dimlunit": 4, "dimtsz": 3},
                                 dxfattribs={"layer": "A-ANNO-DIMS"})
        dim.render()
    for sp in f.spaces:
        cx, cy = (sp.x0 + sp.x1) / 2, (sp.y0 + sp.y1) / 2
        if sp.id == "S103":
            cx, cy = 250, 100
        if sp.id == "S203":
            cx, cy = 250, 120
        if sp.id in ("S104", "S204"):
            cy = 95 if sp.id == "S104" else 130
        msp.add_text(sp.name, height=6, dxfattribs={"layer": "A-ANNO-TEXT"}).set_placement((cx, cy + 3), align=TextEntityAlignment.MIDDLE_CENTER)
        msp.add_text(f"{format_ft_in(sp.x1 - sp.x0)} X {format_ft_in(sp.y1 - sp.y0)}", height=4,
                     dxfattribs={"layer": "A-ANNO-TEXT"}).set_placement((cx, cy - 6), align=TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text(f.title, height=8, dxfattribs={"layer": "A-ANNO-TEXT"}).set_placement((0, -110))
    msp.add_text("ORI SAMPLE - CC0 1.0 - NOT FOR CONSTRUCTION", height=5, dxfattribs={"layer": "A-ANNO-TEXT"}).set_placement((0, -124))
    path = Path(path)
    doc.saveas(str(path))
    return path


# ---------------------------------------------------------------------------------------------
# Ground truth
def license_record() -> dict:
    lp = "research/licenses/cc0-1.0-legalcode.txt"
    return {
        "license_id": "CC0-1.0",
        "license_basis": "ORI-authored synthetic plan, dedicated to the public domain by the ORI project (LICENSE-SPEC.md)",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
        "license_local_path": lp,
        "license_sha256": ov.sha256_file(ov.REPO / lp),
        "license_fetched_at": "2026-09-28",
        "license_confirmed": True,
        "source_url": "https://github.com/corelotorg/OpenPermit/tree/test/verification/examples/takeoff",
        "source_citation": {"author": "ORI project (Open Regulatory Infrastructure)", "title": "ORI sample single-family plan (synthetic)",
                            "year": "2026", "publisher": "ORI / OpenPermit repository", "identifier": "verification/ori_takeoff/sample_plan.py",
                            "archive_url": "https://github.com/corelotorg/OpenPermit/tree/test/verification/examples/takeoff",
                            "accessed": "2026-10-03"},
        "training_use": "allowed",
        "license_note": "Generated by code in this repository; the source URL is the canonical repo path and resolves once this tree is published on the main branch.",
    }


def ground_truth(source_path: str | Path, media: str = "pdf", fl: list[Floor] | None = None,
                 created_at: str = "2026-10-03T00:00:00Z", rotate_deg: float = 0.0) -> dict:
    """Ground-truth overlay from the design data. ``media``: 'pdf' (pages in PDF points) or 'dxf' (one floor, drawing inches)."""
    fl = fl or floors()
    src = ov.source_record(source_path, "application/pdf" if media == "pdf" else "image/vnd.dxf", len(fl))
    doc = ov.new_document(src, license_record(), created_at=created_at, dataset_role="ground_truth",
                          overlay_id=f"urn:ori:overlay:groundtruth:{Path(source_path).name}")
    for i, f in enumerate(fl, 1):
        if media == "pdf":
            tp, k = (rotated_to_page(rotate_deg) if rotate_deg else to_page), 1.0 / PT_PER_IN_REAL
            size, units = [PAGE_W, PAGE_H], "pt"
            sc = ov.scale_block("stated_confirmed", k, stated={"text": 'SCALE: 1/4" = 1\'-0"', "real_in_per_paper_in": SCALE},
                                note="Authored scale.")
        else:
            tp, k = (lambda x, y: (x, y)), 1.0
            size, units = None, "in"
            sc = ov.scale_block("drawing_units", 1.0, note="DXF model space, $INSUNITS=1 (inches).")
        doc["pages"].append(_gt_page(f, i, tp, k, sc, size, units))
    return doc


def _gt_page(f: Floor, page: int, tp, k, sc, size, units) -> dict:
    gt = ov.provenance("authored_ground_truth", 1.0, rule="sample_plan design data", by="ORI sample_plan.py",
                       at="2026-10-03T00:00:00Z", review_status="confirmed")
    P = lambda pts: [tp(x, y) for x, y in pts]  # noqa: E731
    els = []
    wall_ids = {}
    for w in f.walls:
        eid = f"p{page}-{w.id}"
        wall_ids[w.id] = eid
        a0, a1 = w.axis()
        els.append(ov.element(eid, "IfcWall", ov.polygon(P([(w.x0, w.y0), (w.x1, w.y0), (w.x1, w.y1), (w.x0, w.y1)])), k, dict(gt),
                              {"thickness_in": w.thickness, "length_in": round(math.dist(a0, a1), 3), "exterior": w.exterior},
                              axis_page=ov.line(P([a0, a1])), name=w.id, predefined_type="SOLIDWALL"))
    for o in f.openings:
        x0, y0, x1, y1 = opening_rect(f, o)
        props = {"width_in": o.width, "host_thickness_in": wall_by_id(f, o.wall).thickness}
        if o.kind == "door":
            hinge, leaf, jamb, a0, ext = door_geometry(f, o)
            props["swing"] = {"hinge_page": list(tp(*hinge)), "leaf_end_page": list(tp(*leaf)), "radius_in": o.width,
                              "direction": "ccw" if ext > 0 else "cw"}
        w = wall_by_id(f, o.wall)
        ax = ((o.a, (w.y0 + w.y1) / 2), (o.b, (w.y0 + w.y1) / 2)) if w.horizontal else (((w.x0 + w.x1) / 2, o.a), ((w.x0 + w.x1) / 2, o.b))
        els.append(ov.element(f"p{page}-{o.id}", "IfcDoor" if o.kind == "door" else "IfcWindow",
                              ov.polygon(P([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])), k, dict(gt), props,
                              axis_page=ov.line(P(list(ax))), name=o.id, predefined_type="DOOR" if o.kind == "door" else "WINDOW",
                              relations={"host_wall": wall_ids[o.wall]}))
    for sp in f.spaces:
        els.append(ov.element(f"p{page}-{sp.id}", "IfcSpace", ov.polygon(P([(sp.x0, sp.y0), (sp.x1, sp.y0), (sp.x1, sp.y1), (sp.x0, sp.y1)])), k,
                              dict(gt), {"area_ft2": round(sp.area_ft2, 3), "use": sp.use, "label": sp.name}, name=sp.name, predefined_type="SPACE"))
    s = f.stair
    els.append(ov.element(f"p{page}-{s.id}", "IfcStair", ov.polygon(P([(s.x0, s.y0), (s.x1, s.y0), (s.x1, s.y1), (s.x0, s.y1)])), k, dict(gt),
                          {"riser_count": s.risers, "tread_count": s.risers - 1, "tread_depth_in": s.tread_depth, "width_in": s.x1 - s.x0,
                           "direction": s.direction, "riser_height_in": None,
                           "riser_height_note": "Not drawn in plan; the sheet note gives 7 1/2 in, which is text, not geometry."},
                          name=s.id, predefined_type="STRAIGHT_RUN_STAIR"))
    for j, d in enumerate(f.dims, 1):
        p0, p1, ext, text_at, angle, value = dim_geometry(d)
        els.append(ov.element(f"p{page}-DIM{j}", "IfcAnnotation", ov.line(P([p0, p1])), k, dict(gt),
                              {"text": format_ft_in(value), "value_in": value}, annotation_type="dimension"))
    return {"page": page, "page_label": f.sheet, "sheet_title": f.title, "kind": "vector" if units == "pt" else "dxf",
            "status": "ground_truth", "size_page_units": size or [384.0, 336.0], "page_units": units, "scale": sc,
            "storey": {"name": f.storey, "elevation_in": f.elevation_in, "elevation_origin": "sample design data",
                       "floor_to_floor_in": FLOOR_TO_FLOOR_IN, "ceiling_height_in": CEILING_IN},
            "elements": els, "takeoff": None, "notes": []}


def build_all(outdir: str | Path) -> dict[str, Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fl = floors()
    out = {"pdf": write_pdf(outdir / "ori-sample-house.pdf", fl)}
    nz = Noise()
    out["pdf_noisy"] = write_pdf(outdir / "ori-sample-house-noisy.pdf", fl, nz)
    g = ground_truth(out["pdf_noisy"], "pdf", fl, rotate_deg=nz.rotate_deg)
    out["gt_pdf_noisy"] = outdir / "ori-sample-house-noisy.pdf.groundtruth.overlay.json"
    out["gt_pdf_noisy"].write_text(ov.dumps(g))
    for f in fl:
        out[f"dxf_{f.sheet}"] = write_dxf(outdir / f"ori-sample-house-{f.sheet}.dxf", f)
    gt = ground_truth(out["pdf"], "pdf", fl)
    (outdir / "ori-sample-house.pdf.groundtruth.overlay.json").write_text(ov.dumps(gt))
    out["gt_pdf"] = outdir / "ori-sample-house.pdf.groundtruth.overlay.json"
    for f in fl:
        g = ground_truth(out[f"dxf_{f.sheet}"], "dxf", [f])
        p = outdir / f"ori-sample-house-{f.sheet}.dxf.groundtruth.overlay.json"
        p.write_text(ov.dumps(g))
        out[f"gt_dxf_{f.sheet}"] = p
    return out
