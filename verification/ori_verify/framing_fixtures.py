# SPDX-License-Identifier: Apache-2.0
"""Synthetic Chapter 6 framing and bracing IFC fixtures (pass / fail / incomplete).

SYNTHETIC test models for the ORI reference evaluator; they describe no real building.
Representation: see ``framing_extract.py`` and docs/CH6-FRAMING-DRAFT.md. Each fixture is a
one-storey rectangle with framed walls (IfcWall + Pset_ORI_Framing), braced wall panels
(IfcPlate + Pset_ORI_BracedWallPanel) and one circumscribed bracing rectangle
(IfcAnnotation + Pset_ORI_BracingRectangle). Expected results are listed per fixture in
``EXPECTED`` and asserted by tests/test_ch06.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import ifcopenshell.api as api

from .ifc_fixtures import IN, _Builder


@dataclass
class WallSpec:
    name: str
    x0: float
    y0: float
    dx: float
    dy: float
    bearing: bool | None = True
    exterior: bool | None = True
    framing: dict = field(default_factory=dict)  # Pset_ORI_Framing values; lengths in inches


@dataclass
class PanelSpec:
    name: str
    x: float
    y: float
    length: float
    axis: str = "x"
    height: float = 96.0
    props: dict = field(default_factory=dict)  # Pset_ORI_BracedWallPanel values; lengths in inches


@dataclass
class RectSpec:
    name: str
    lx_ft: float | None
    ly_ft: float | None
    props: dict = field(default_factory=dict)  # extra Pset_ORI_BracingRectangle values; lengths in inches


@dataclass
class FramingModel:
    walls: list[WallSpec]
    panels: list[PanelSpec]
    rect: RectSpec | None


LENGTH_KEYS = {"StudSpacing", "StudHeight", "TopPlateSpliceOffset", "MaxBoredHoleDiameter", "MaxNotchDepth", "SheathingThickness",
               "AdjacentOpeningClearHeight", "WallHeight", "RequiredBracingAlongX", "RequiredBracingAlongY",
               "OriginX", "OriginY", "LengthX", "LengthY"}


def _props(b, d):
    out = {}
    for k, v in d.items():
        if v is None:
            continue
        out[k] = b.f.createIfcLengthMeasure(float(v) * IN) if k in LENGTH_KEYS else v
    return out


def write(model: FramingModel, path: str | Path, name: str = "ORI synthetic framing fixture") -> Path:
    b = _Builder(name)
    for w in model.walls:
        wall = api.run("root.create_entity", b.f, ifc_class="IfcWall", name=w.name, predefined_type="SOLIDWALL")
        wall.ObjectPlacement = b.placement(w.x0 * IN, w.y0 * IN, 0.0)
        b.assign_body(wall, b.rect_solid(w.dx * IN, w.dy * IN, 96.0 * IN))
        b.contain(wall)
        common = {k: v for k, v in (("LoadBearing", w.bearing), ("IsExternal", w.exterior)) if v is not None}
        if common:
            b.pset(wall, "Pset_WallCommon", common)
        if w.framing:
            b.pset(wall, "Pset_ORI_Framing", _props(b, w.framing))
    for p in model.panels:
        plate = api.run("root.create_entity", b.f, ifc_class="IfcPlate", name=p.name, predefined_type="SHEET")
        plate.ObjectPlacement = b.placement(p.x * IN, p.y * IN, 0.0)
        dx, dy = (p.length, 0.5) if p.axis == "x" else (0.5, p.length)
        b.assign_body(plate, b.rect_solid(dx * IN, dy * IN, p.height * IN))
        b.contain(plate)
        b.pset(plate, "Pset_ORI_BracedWallPanel", _props(b, p.props))
    if model.rect is not None:
        r = model.rect
        ann = api.run("root.create_entity", b.f, ifc_class="IfcAnnotation", name=r.name)
        b.contain(ann)
        props = {"OriginX": 0.0, "OriginY": 0.0, "LengthX": r.lx_ft * 12 if r.lx_ft else None, "LengthY": r.ly_ft * 12 if r.ly_ft else None,
                 "Note": "SYNTHETIC bracing rectangle"}
        props.update(r.props)
        b.pset(ann, "Pset_ORI_BracingRectangle", _props(b, props))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    b.f.write(str(path))
    return path


FRAMING_OK = {"StudNominalSize": "2x6", "StudSpacing": 16, "StudHeight": 92.25, "FloorsSupported": 1, "TopPlateCount": 2,
              "TopPlateSpliceOffset": 48, "MaxBoredHoleDiameter": 1.25, "MaxNotchDepth": 1.0, "StudsDoubledAtHoles": False,
              "StudGrade": "No. 2", "StudSpecies": "SPF"}
PRACTICAL = "VA-R602.12"


def _ext_panel(name, x, y, length, axis="x", opening=60.0, **kw):
    props = {"Method": PRACTICAL, "Location": "exterior", "SheathingMaterial": "wood_structural_panel", "SheathingThickness": 0.4375,
             "AdjacentOpeningClearHeight": opening}
    props.update(kw)
    return PanelSpec(name, x, y, length, axis, props=props)


def _perimeter(lx_ft, ly_ft, framing):
    lx, ly = lx_ft * 12, ly_ft * 12
    return [WallSpec("South wall", 0, 0, lx, 5.5, framing=dict(framing)), WallSpec("North wall", 0, ly - 5.5, lx, 5.5, framing=dict(framing)),
            WallSpec("West wall", 0, 0, 5.5, ly, framing=dict(framing)), WallSpec("East wall", lx - 5.5, 0, 5.5, ly, framing=dict(framing))]


def passing_model() -> FramingModel:
    lx, ly = 40, 30
    walls = _perimeter(lx, ly, FRAMING_OK)
    walls.append(WallSpec("Interior partition", 120, 120, 200, 3.5, bearing=False, exterior=False,
                          framing={"StudNominalSize": "2x4", "StudSpacing": 24, "TopPlateCount": 1, "MaxBoredHoleDiameter": 1.0, "MaxNotchDepth": 0.75}))
    panels = []
    for i, x in enumerate((0, 18 * 12, 36 * 12)):
        panels.append(_ext_panel(f"S{i + 1}", x, 0, 48))
        panels.append(_ext_panel(f"N{i + 1}", x, ly * 12 - 0.5, 48))
    for i, y in enumerate((0, 13 * 12, 26 * 12)):
        panels.append(_ext_panel(f"W{i + 1}", 0, y, 48, "y"))
        panels.append(_ext_panel(f"E{i + 1}", lx * 12 - 0.5, y, 48, "y"))
    panels.append(PanelSpec("I1", 120, 120, 48, "x", props={"Method": PRACTICAL, "Location": "interior", "SheathingMaterial": "gypsum_board", "SheathingThickness": 0.5}))
    rect = RectSpec("Bracing rectangle A", lx, ly, {"RequiredBracingAlongX": 10 * 12, "RequiredBracingAlongY": 7 * 12, "BuildingMatchesRectangle": True,
                                                   "BracingPlanComplete": True})
    return FramingModel(walls, panels, rect)


def failing_model() -> FramingModel:
    lx, ly = 90, 25
    bad = dict(FRAMING_OK, StudSpacing=24, FloorsSupported=2, TopPlateCount=1, TopPlateSpliceOffset=12, MaxBoredHoleDiameter=3.0, MaxNotchDepth=2.0,
               StudHeight=130)
    walls = _perimeter(lx, ly, bad)
    panels = [_ext_panel("S1", 0, 0, 20, opening=70.0), _ext_panel("S2", 30 * 12, 0, 48, SheathingThickness=0.375),
              _ext_panel("S3", 34 * 12 + 6, 0, 48, SheathingMaterial="gypsum_board", SheathingThickness=0.5),
              PanelSpec("I1", 120, 120, 36, "x", props={"Method": PRACTICAL, "Location": "interior", "SheathingMaterial": "gypsum_board", "SheathingThickness": 0.5})]
    rect = RectSpec("Bracing rectangle B", lx, ly, {"RequiredBracingAlongX": 20 * 12, "RequiredBracingAlongY": 8 * 12, "BuildingMatchesRectangle": True,
                                                   "BracingPlanComplete": True})
    return FramingModel(walls, panels, rect)


def incomplete_model() -> FramingModel:
    lx, ly = 40, 30
    walls = _perimeter(lx, ly, {"StudNominalSize": "2x6"})
    walls[0].bearing = None
    panels = [PanelSpec("S1", 0, 0, 48, props={"Location": "exterior"}),
              PanelSpec("S2", 18 * 12, 0, 48, props={"Method": PRACTICAL, "Location": "exterior", "SheathingMaterial": "wood_structural_panel"}),
              PanelSpec("S3", 36 * 12, 0, 48, height=108, props={"Method": PRACTICAL, "Location": "exterior", "SheathingMaterial": "wood_structural_panel",
                                                               "AdjacentOpeningClearHeight": 60})]
    rect = RectSpec("Bracing rectangle C", lx, None, {})
    return FramingModel(walls, panels, rect)


MODELS = {"pass": passing_model, "fail": failing_model, "incomplete": incomplete_model}


def write_all(outdir: str | Path) -> list[Path]:
    return [write(fn(), Path(outdir) / f"ori-ch06-{name}.ifc", f"ORI synthetic framing fixture ({name})") for name, fn in MODELS.items()]
