# SPDX-License-Identifier: Apache-2.0
"""Build small IFC4 test models programmatically (millimetre units).

The models are synthetic test fixtures for the ORI reference evaluator. They
do not describe any real building.

Geometry conventions:
* A stair flight is an IfcExtrudedAreaSolid. Its IfcArbitraryClosedProfileDef
  is the stepped side profile in local XY (X = run, Y = rise), extruded along
  local Z by the flight width. The solid's Position maps local Y to world Z.
* Spaces and slabs are extruded rectangles.
* A guard is an IfcRailing (GUARDRAIL) modeled as a thin extruded box.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.guid

IN = 25.4  # mm per inch


@dataclass
class StairSpec:
    risers_in: list[float]
    treads_in: list[float]  # len == len(risers) - 1 (top riser lands on floor)
    width_in: float = 36.0
    origin_in: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class OverheadSpec:
    """An overhead slab or soffit over part of the stair run (world plan extent, bottom elevation)."""
    x0_in: float
    x1_in: float
    bottom_in: float
    thickness_in: float = 10.0
    y0_in: float = -40.0
    y1_in: float = 4.0


@dataclass
class SpaceSpec:
    name: str
    use: str | None
    width_in: float
    depth_in: float
    height_in: float
    sloped: bool | None = False
    origin_in: tuple[float, float] = (0.0, 0.0)


@dataclass
class WindowSpec:
    name: str
    frame_bottom_in: float
    net_clear_height_in: float | None
    net_clear_width_in: float | None
    grade_floor: bool | None
    clear_offset_in: float | None = 2.0
    is_eero: bool = True


@dataclass
class DeckSpec:
    top_in: float
    grade_top_in: float | None  # None: no grade surface modeled
    guard_height_in: float | None  # None: no railing modeled
    size_in: tuple[float, float] = (120.0, 96.0)


@dataclass
class ModelSpec:
    name: str
    stairs: list[StairSpec] = field(default_factory=list)
    overheads: list[OverheadSpec] = field(default_factory=list)
    spaces: list[SpaceSpec] = field(default_factory=list)
    windows: list[WindowSpec] = field(default_factory=list)
    decks: list[DeckSpec] = field(default_factory=list)


class _Builder:
    def __init__(self, name: str):
        f = api.run("project.create_file", version="IFC4")
        self.f = f
        self.project = api.run("root.create_entity", f, ifc_class="IfcProject", name=name)
        api.run("unit.assign_unit", f, length={"is_metric": True, "raw": "MILLIMETERS"})
        ctx = api.run("context.add_context", f, context_type="Model")
        self.body = api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
        self.site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Synthetic site")
        self.building = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Synthetic single-family dwelling")
        self.storey = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Level 1")
        self.storey.Elevation = 0.0
        api.run("aggregate.assign_object", f, products=[self.site], relating_object=self.project)
        api.run("aggregate.assign_object", f, products=[self.building], relating_object=self.site)
        api.run("aggregate.assign_object", f, products=[self.storey], relating_object=self.building)

    # -- low-level helpers (all values in mm) ---------------------------------
    def pt3(self, x, y, z):
        return self.f.createIfcCartesianPoint((float(x), float(y), float(z)))

    def dir(self, x, y, z):
        return self.f.createIfcDirection((float(x), float(y), float(z)))

    def placement(self, x=0.0, y=0.0, z=0.0):
        a = self.f.createIfcAxis2Placement3D(self.pt3(x, y, z), None, None)
        return self.f.createIfcLocalPlacement(None, a)

    def rect_solid(self, dx, dy, depth, ox=0.0, oy=0.0, oz=0.0):
        pts = [(ox, oy), (ox + dx, oy), (ox + dx, oy + dy), (ox, oy + dy), (ox, oy)]
        poly = self.f.createIfcPolyline([self.f.createIfcCartesianPoint((float(a), float(b))) for a, b in pts])
        prof = self.f.createIfcArbitraryClosedProfileDef("AREA", None, poly)
        pos = self.f.createIfcAxis2Placement3D(self.pt3(0, 0, oz), None, None)
        return self.f.createIfcExtrudedAreaSolid(prof, pos, self.dir(0, 0, 1), float(depth))

    def assign_body(self, product, solid, rep_type="SweptSolid"):
        rep = self.f.createIfcShapeRepresentation(self.body, "Body", rep_type, [solid])
        product.Representation = self.f.createIfcProductDefinitionShape(None, None, [rep])

    def contain(self, product):
        api.run("spatial.assign_container", self.f, products=[product], relating_structure=self.storey)

    def pset(self, product, name, props):
        ps = api.run("pset.add_pset", self.f, product=product, name=name)
        api.run("pset.edit_pset", self.f, pset=ps, properties=props)

    # -- elements --------------------------------------------------------------
    def stair(self, s: StairSpec, n: int):
        assert len(s.treads_in) == len(s.risers_in) - 1
        stair = api.run("root.create_entity", self.f, ifc_class="IfcStair", name=f"Stair {n}", predefined_type="STRAIGHT_RUN_STAIR")
        flight = api.run("root.create_entity", self.f, ifc_class="IfcStairFlight", name=f"Stair {n} flight 1", predefined_type="STRAIGHT")
        # Stepped profile: start at (0,0); up riser 1, across tread 1, ... up last riser;
        # then close along the soffit back to the start.
        x = z = 0.0
        pts = [(0.0, 0.0)]
        for i, r in enumerate(s.risers_in):
            z += r * IN
            pts.append((x, z))
            if i < len(s.treads_in):
                x += s.treads_in[i] * IN
                pts.append((x, z))
        pts.append((x + 0.0, z - 200.0))  # soffit thickness under top riser
        pts.append((200.0, 0.0))
        pts.append((0.0, 0.0))
        poly = self.f.createIfcPolyline([self.f.createIfcCartesianPoint((float(a), float(b))) for a, b in pts])
        prof = self.f.createIfcArbitraryClosedProfileDef("AREA", "stepped side profile", poly)
        # local X -> world X, local Y -> world Z, local Z (extrusion) -> world -Y
        pos = self.f.createIfcAxis2Placement3D(self.pt3(0, 0, 0), self.dir(0, -1, 0), self.dir(1, 0, 0))
        solid = self.f.createIfcExtrudedAreaSolid(prof, pos, self.dir(0, 0, 1), float(s.width_in * IN))
        ox, oy, oz = (v * IN for v in s.origin_in)
        flight.ObjectPlacement = self.placement(ox, oy, oz)
        self.assign_body(flight, solid)
        flight.NumberOfRisers = len(s.risers_in)
        flight.NumberOfTreads = len(s.treads_in)
        api.run("aggregate.assign_object", self.f, products=[flight], relating_object=stair)
        self.contain(stair)
        return flight

    def overhead(self, o: OverheadSpec, n: int):
        slab = api.run("root.create_entity", self.f, ifc_class="IfcSlab", name=f"Overhead {n}", predefined_type="FLOOR")
        slab.ObjectPlacement = self.placement(o.x0_in * IN, o.y0_in * IN, o.bottom_in * IN)
        self.assign_body(slab, self.rect_solid((o.x1_in - o.x0_in) * IN, (o.y1_in - o.y0_in) * IN, o.thickness_in * IN))
        self.contain(slab)
        return slab

    def space(self, s: SpaceSpec):
        sp = api.run("root.create_entity", self.f, ifc_class="IfcSpace", name=s.name)
        sp.ObjectPlacement = self.placement(s.origin_in[0] * IN, s.origin_in[1] * IN, 0.0)
        self.assign_body(sp, self.rect_solid(s.width_in * IN, s.depth_in * IN, s.height_in * IN))
        api.run("aggregate.assign_object", self.f, products=[sp], relating_object=self.storey)
        props = {}
        if s.use is not None:
            props["UseCategory"] = s.use
        if s.sloped is not None:
            props["SlopedCeiling"] = bool(s.sloped)
        if props:
            self.pset(sp, "Pset_ORI_SpaceUse", props)
        return sp

    def window(self, w: WindowSpec, n: int):
        win = api.run("root.create_entity", self.f, ifc_class="IfcWindow", name=w.name)
        win.ObjectPlacement = self.placement(0.0, -1000.0 * n, w.frame_bottom_in * IN)
        win.OverallHeight = 1200.0
        win.OverallWidth = 900.0
        self.assign_body(win, self.rect_solid(900.0, 100.0, 1200.0))
        self.contain(win)
        props = {"IsEmergencyEscapeOpening": w.is_eero}
        L = self.f.createIfcLengthMeasure
        if w.net_clear_height_in is not None:
            props["NetClearHeight"] = L(w.net_clear_height_in * IN)
        if w.net_clear_width_in is not None:
            props["NetClearWidth"] = L(w.net_clear_width_in * IN)
        if w.grade_floor is not None:
            props["GradeFloorOrBelowGrade"] = w.grade_floor
        if w.clear_offset_in is not None:
            props["SillToClearOpeningOffset"] = L(w.clear_offset_in * IN)
        self.pset(win, "Pset_ORI_EscapeOpening", props)
        return win

    def deck(self, d: DeckSpec, n: int):
        dx, dy = (v * IN for v in d.size_in)
        base_x = 10000.0 * (n + 1)
        deck = api.run("root.create_entity", self.f, ifc_class="IfcSlab", name=f"Deck {n}", predefined_type="FLOOR")
        deck.ObjectPlacement = self.placement(base_x, 0.0, d.top_in * IN - 150.0)
        self.assign_body(deck, self.rect_solid(dx, dy, 150.0))
        self.contain(deck)
        self.pset(deck, "Pset_ORI_WalkingSurface", {"OpenSided": True})
        if d.grade_top_in is not None:
            grade = api.run("root.create_entity", self.f, ifc_class="IfcSlab", name=f"Grade under deck {n}", predefined_type="BASESLAB")
            grade.ObjectPlacement = self.placement(base_x - 2000.0, -2000.0, d.grade_top_in * IN - 100.0)
            self.assign_body(grade, self.rect_solid(dx + 4000.0, dy + 4000.0, 100.0))
            self.contain(grade)
        if d.guard_height_in is not None:
            rail = api.run("root.create_entity", self.f, ifc_class="IfcRailing", name=f"Deck {n} guard", predefined_type="GUARDRAIL")
            rail.ObjectPlacement = self.placement(base_x, 0.0, d.top_in * IN)
            self.assign_body(rail, self.rect_solid(dx, 50.0, d.guard_height_in * IN))
            self.contain(rail)
        return deck


def build_model(spec: ModelSpec) -> ifcopenshell.file:
    b = _Builder(spec.name)
    for i, s in enumerate(spec.stairs, 1):
        b.stair(s, i)
    for i, o in enumerate(spec.overheads, 1):
        b.overhead(o, i)
    for s in spec.spaces:
        b.space(s)
    for i, w in enumerate(spec.windows, 1):
        b.window(w, i)
    for i, d in enumerate(spec.decks):
        b.deck(d, i)
    return b.f


# Canonical fixtures ---------------------------------------------------------
def passing_spec() -> ModelSpec:
    """Meets the VA values; note riser 8.0 in and tread 9.5 in FAIL the IRC base (7.75 / 10)."""
    risers = [8.0] * 13
    treads = [9.5] * 12
    return ModelSpec(
        name="ORI synthetic PASS model (VA overrides)",
        stairs=[StairSpec(risers, treads)],
        overheads=[OverheadSpec(x0_in=0.0, x1_in=40.0, bottom_in=124.0)],  # floor structure over the lower run
        spaces=[
            SpaceSpec("Bedroom 1", "habitable", 132.0, 120.0, 96.0),
            SpaceSpec("Kitchen", "kitchen", 96.0, 84.0, 96.0, origin_in=(200.0, 0.0)),
            SpaceSpec("Bath 1", "bathroom", 60.0, 96.0, 81.0, origin_in=(400.0, 0.0)),
        ],
        windows=[WindowSpec("Bedroom 1 EERO", frame_bottom_in=40.0, net_clear_height_in=36.0, net_clear_width_in=24.0, grade_floor=False, clear_offset_in=2.0)],
        decks=[DeckSpec(top_in=48.0, grade_top_in=0.0, guard_height_in=36.0)],
    )


def failing_spec() -> ModelSpec:
    risers = [8.0] * 12 + [8.5]
    treads = [9.5] * 11 + [8.75]
    return ModelSpec(
        name="ORI synthetic FAIL model (VA overrides)",
        stairs=[StairSpec(risers, treads)],
        overheads=[OverheadSpec(x0_in=20.0, x1_in=60.0, bottom_in=124.0)],
        spaces=[
            SpaceSpec("Bedroom 2", "habitable", 96.0, 96.0, 80.0, sloped=False),
            SpaceSpec("Bath 2", "bathroom", 60.0, 96.0, 78.0, sloped=False, origin_in=(400.0, 0.0)),
        ],
        windows=[WindowSpec("Bedroom 2 EERO", frame_bottom_in=46.0, net_clear_height_in=22.0, net_clear_width_in=18.0, grade_floor=False, clear_offset_in=2.0)],
        decks=[DeckSpec(top_in=48.0, grade_top_in=0.0, guard_height_in=30.0)],
    )


def incomplete_spec() -> ModelSpec:
    """Information is missing: every affected result must be unknown, never fail."""
    return ModelSpec(
        name="ORI synthetic INCOMPLETE model",
        stairs=[StairSpec([8.0] * 13, [9.5] * 12)],  # no overhead element modeled
        spaces=[SpaceSpec("Room without use", None, 96.0, 96.0, 80.0, sloped=None)],
        windows=[WindowSpec("EERO without net clear data", frame_bottom_in=40.0, net_clear_height_in=None, net_clear_width_in=None, grade_floor=None, clear_offset_in=None)],
        decks=[DeckSpec(top_in=48.0, grade_top_in=None, guard_height_in=None), DeckSpec(top_in=48.0, grade_top_in=0.0, guard_height_in=None)],
    )


def write_fixture(spec: ModelSpec, path: Path) -> Path:
    f = build_model(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    f.write(str(path))
    return path
