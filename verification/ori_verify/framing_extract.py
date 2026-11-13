# SPDX-License-Identifier: Apache-2.0
"""Extract Chapter 6 framing and bracing subjects from an IFC model.

Representation (documented in docs/CH6-FRAMING-DRAFT.md):

* ``IfcWall`` with ``Pset_ORI_Framing`` -> subject kind ``framed_wall``. Properties:
  StudNominalSize (label, e.g. "2x6"), StudSpacing, StudHeight, TopPlateSpliceOffset,
  MaxBoredHoleDiameter, MaxNotchDepth (lengths in model units), FloorsSupported,
  TopPlateCount (integers), StudsDoubledAtHoles (boolean), StudGrade, StudSpecies
  (labels; recorded, not checked). Bearing comes from Pset_WallCommon.LoadBearing.
  The wall body height (geometry) is kept as ``wall_height``.
* ``IfcPlate`` with ``Pset_ORI_BracedWallPanel`` -> ``braced_wall_panel``. Panel length
  and height are measured from the body geometry (plan extent along the panel's long
  axis; vertical extent). Properties: Method ("VA-R602.12" for Virginia practical
  bracing; other values are recorded), Location (exterior | interior),
  SheathingMaterial (wood_structural_panel | structural_fiberboard | gypsum_board),
  SheathingThickness, AdjacentOpeningClearHeight (lengths), AdjacentOneStoryGarageDoor
  (boolean), WallHeight (optional length; overrides the measured height).
* ``IfcAnnotation`` with ``Pset_ORI_BracingRectangle`` -> one ``bracing_rectangle`` and
  four ``bracing_rectangle_side`` subjects. Properties: OriginX, OriginY, LengthX,
  LengthY (lengths; axis-aligned only), RequiredBracingAlongX, RequiredBracingAlongY
  (lengths the applicant computed from the bracing table for sides parallel to X / Y),
  BuildingMatchesRectangle (boolean: the building outline has no corners other than
  the rectangle corners), BracingPlanComplete (boolean: every braced panel is modelled;
  without it, a missing panel is not treated as evidence of absence).

Element-level stud modelling (``IfcMember`` studs) is not needed by these rules; a
detailed stud-level assembly can feed the same facts later. Nothing here infers a
value that is not in the model: absent properties stay missing, so rules give unknown.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import ifcopenshell.util.element as uel
import ifcopenshell.util.placement as upl

from .facts import Fact, Subject

# Actual depth of dressed dimension lumber by nominal size (inches).
STUD_DEPTH_IN = {"2x3": 2.5, "2x4": 3.5, "3x4": 3.5, "2x5": 4.5, "2x6": 5.5, "2x8": 7.25}
SIDE_TOL_IN = 24.0  # an exterior panel is "on" a side if its centreline lies within this band


def _r(x: float) -> float:
    return float(round(float(x), 6))


def framing_subjects(fx) -> list[Subject]:
    return _walls(fx) + _panels_and_rectangles(fx)


def _walls(fx) -> list[Subject]:
    out = []
    for w in fx.f.by_type("IfcWall"):
        ps = uel.get_pset(w, "Pset_ORI_Framing")
        if not ps:
            continue
        a = fx.anchor(w)
        s = Subject(kind="framed_wall", subject_id=f"ifc:{w.GlobalId}", label=w.Name or w.GlobalId, anchor=a)
        common = uel.get_pset(w, "Pset_WallCommon") or {}
        if common.get("LoadBearing") is not None:
            s.facts["bearing"] = Fact(bool(common["LoadBearing"]), "ifc_property", a, "Pset_WallCommon.LoadBearing")
        if common.get("IsExternal") is not None:
            s.facts["exterior"] = Fact(bool(common["IsExternal"]), "ifc_property", a, "Pset_WallCommon.IsExternal")
        size = ps.get("StudNominalSize")
        if size:
            size = str(size).lower().replace(" ", "")
            s.facts["stud_size"] = Fact(size, "ifc_property", a, "Pset_ORI_Framing.StudNominalSize")
            if size in STUD_DEPTH_IN:
                s.facts["stud_depth"] = Fact(STUD_DEPTH_IN[size], "ifc_property", a, "dressed depth for the declared nominal size")
        for key, fact in (("StudSpacing", "stud_spacing"), ("StudHeight", "stud_height"), ("TopPlateSpliceOffset", "top_plate_splice_offset"),
                          ("MaxBoredHoleDiameter", "max_bored_hole_diameter"), ("MaxNotchDepth", "max_notch_depth")):
            if ps.get(key) is not None:
                s.facts[fact] = Fact(_r(fx.len_in(ps[key])), "ifc_property", a, f"Pset_ORI_Framing.{key}")
        for key, fact in (("FloorsSupported", "floors_supported"), ("TopPlateCount", "top_plate_count")):
            if ps.get(key) is not None:
                s.facts[fact] = Fact(int(ps[key]), "ifc_property", a, f"Pset_ORI_Framing.{key}")
        if ps.get("StudsDoubledAtHoles") is not None:
            s.facts["stud_doubled"] = Fact(bool(ps["StudsDoubledAtHoles"]), "ifc_property", a, "Pset_ORI_Framing.StudsDoubledAtHoles")
        for key in ("StudGrade", "StudSpecies"):
            if ps.get(key):
                s.facts[key.lower().replace("stud", "stud_")] = Fact(str(ps[key]), "ifc_property", a, f"Pset_ORI_Framing.{key}")
        bb = fx.bbox_in(w)
        if bb is not None:
            s.facts["wall_height"] = Fact(_r(bb[1][2] - bb[0][2]), "ifc_geometry", a, "wall body vertical extent (includes plates)")
        out.append(s)
    return out


def _panel(fx, el, ps) -> Subject:
    a = fx.anchor(el)
    s = Subject(kind="braced_wall_panel", subject_id=f"ifc:{el.GlobalId}", label=el.Name or el.GlobalId, anchor=a)
    for key, fact in (("Method", "bracing_method"), ("Location", "panel_location"), ("SheathingMaterial", "sheathing_material")):
        if ps.get(key):
            s.facts[fact] = Fact(str(ps[key]), "ifc_property", a, f"Pset_ORI_BracedWallPanel.{key}")
    for key, fact in (("SheathingThickness", "sheathing_thickness"), ("AdjacentOpeningClearHeight", "adjacent_opening_clear_height")):
        if ps.get(key) is not None:
            s.facts[fact] = Fact(_r(fx.len_in(ps[key])), "ifc_property", a, f"Pset_ORI_BracedWallPanel.{key}")
    if ps.get("AdjacentOneStoryGarageDoor") is not None:
        s.facts["adjacent_one_story_garage_door"] = Fact(bool(ps["AdjacentOneStoryGarageDoor"]), "ifc_property", a, "Pset_ORI_BracedWallPanel.AdjacentOneStoryGarageDoor")
    bb = fx.bbox_in(el)
    if bb is not None:
        (x0, y0, z0), (x1, y1, z1) = bb
        along_x = (x1 - x0) >= (y1 - y0)
        s.facts["panel_length"] = Fact(_r(max(x1 - x0, y1 - y0)), "ifc_geometry", a, "panel body extent along its long plan axis")
        s.facts["panel_plan_extent"] = Fact([_r(x0), _r(y0), _r(x1), _r(y1)], "ifc_geometry", a, "panel body plan bounding box (in)")
        s.facts["panel_axis"] = Fact("x" if along_x else "y", "ifc_geometry", a, "long plan axis")
        if ps.get("WallHeight") is not None:
            s.facts["wall_height"] = Fact(_r(fx.len_in(ps["WallHeight"])), "ifc_property", a, "Pset_ORI_BracedWallPanel.WallHeight")
        else:
            s.facts["wall_height"] = Fact(_r(z1 - z0), "ifc_geometry", a, "panel body vertical extent (full-height panel)")
    return s


def _panels_and_rectangles(fx) -> list[Subject]:
    panels = []
    for el in fx.f.by_type("IfcPlate"):
        ps = uel.get_pset(el, "Pset_ORI_BracedWallPanel")
        if ps:
            panels.append(_panel(fx, el, ps))
    out: list[Subject] = list(panels)
    for ann in fx.f.by_type("IfcAnnotation"):
        rp = uel.get_pset(ann, "Pset_ORI_BracingRectangle")
        if not rp:
            continue
        out.extend(_rectangle(fx, ann, rp, panels))
    return out


def _rectangle(fx, ann, rp, panels) -> list[Subject]:
    a = {"type": "ifc_element", "ifc_guid": ann.GlobalId, "ifc_class": ann.is_a(), "name": ann.Name, "model": fx.source_path}
    rect = Subject(kind="bracing_rectangle", subject_id=f"ifc:{ann.GlobalId}", label=ann.Name or ann.GlobalId, anchor=a)
    need = ("OriginX", "OriginY", "LengthX", "LengthY")
    if any(rp.get(k) is None for k in need):
        rect.notes.append("Rectangle extent incomplete; facts left missing.")
        return [rect]
    ox, oy, lx, ly = (fx.len_in(rp[k]) for k in need)
    rect.facts["rectangle_sides"] = Fact([_r(lx / 12), _r(ly / 12)], "ifc_property", a, "Pset_ORI_BracingRectangle.LengthX / LengthY (ft)")
    out = [rect]
    # side: (name, axis it runs along, fixed coordinate, start coordinate, length)
    sides = [("south", "x", oy, ox, lx), ("north", "x", oy + ly, ox, lx), ("west", "y", ox, oy, ly), ("east", "y", ox + lx, oy, ly)]
    for name, axis, fixed, start, length in sides:
        s = Subject(kind="bracing_rectangle_side", subject_id=f"ifc:{ann.GlobalId}#{name}", label=f"{rect.label} {name} side",
                    anchor=dict(a, side=name))
        s.facts["side_length"] = Fact(_r(length / 12), "ifc_property", a, "rectangle side length (ft)")
        req_key = "RequiredBracingAlongX" if axis == "x" else "RequiredBracingAlongY"
        if rp.get(req_key) is not None:
            s.facts["required_bracing_length"] = Fact(_r(fx.len_in(rp[req_key]) / 12), "ifc_property", a,
                                                      f"Pset_ORI_BracingRectangle.{req_key} (applicant's table lookup, ft)")
        if rp.get("BracingPlanComplete") is not None:
            s.facts["bracing_plan_complete"] = Fact(bool(rp["BracingPlanComplete"]), "ifc_property", a,
                                                    "Pset_ORI_BracingRectangle.BracingPlanComplete (every braced panel is modelled)")
        if rp.get("BuildingMatchesRectangle") is not None:
            s.facts["building_matches_rectangle"] = Fact(bool(rp["BuildingMatchesRectangle"]), "ifc_property", a,
                                                         "Pset_ORI_BracingRectangle.BuildingMatchesRectangle")
        assigned, origin_ok = [], True
        for p in panels:
            ext, ax, loc = p.get("panel_plan_extent"), p.get("panel_axis"), p.get("panel_location")
            if ext is None or ax is None or ax.value != axis:
                continue
            x0, y0, x1, y1 = ext.value
            centre_perp = (y0 + y1) / 2 if axis == "x" else (x0 + x1) / 2
            lo, hi = (x0, x1) if axis == "x" else (y0, y1)
            if hi < start - 1e-6 or lo > start + length + 1e-6:
                continue
            dist = abs(centre_perp - fixed)
            location = loc.value if loc is not None else None
            if location == "exterior" and dist > SIDE_TOL_IN:
                continue
            if location != "exterior" and dist > 4 * 12 + SIDE_TOL_IN:  # candidates only; the rule applies the 4 ft limit
                continue
            if not all(f.usable for f in (ext, ax)) or (loc is not None and not loc.usable):
                origin_ok = False
            assigned.append({"panel": p.label, "ifc_guid": p.subject_id.split(":", 1)[1], "location": location,
                             "length_ft": _r((hi - lo) / 12), "start_ft": _r((lo - start) / 12), "end_ft": _r((hi - start) / 12),
                             "distance_from_side_ft": _r(dist / 12)})
        assigned.sort(key=lambda d: d["start_ft"])
        s.facts["assigned_panels"] = Fact(assigned, "ifc_geometry" if origin_ok else "vector_extracted_unconfirmed", a,
                                          "braced wall panels parallel to and on (or, if interior, near) this side")
        out.append(s)
    return out
