# SPDX-License-Identifier: Apache-2.0
"""Extract ORI facts from an IFC model with IfcOpenShell.

What is measured from geometry and what is read from properties:
* Stair risers and treads: measured from the flight's stepped extrusion profile
  (IfcArbitraryClosedProfileDef polyline) transformed to world coordinates.
* Stair headroom: world-space nosing line against the underside of overhead
  IfcSlab/IfcCovering/IfcBeam elements that overlap the flight in plan.
* Space ceiling height: top minus bottom of the IfcSpace body (world bbox).
* Space floor area: IfcSpace footprint area from the geometry kernel.
* EERO sill: window placement elevation above the containing storey elevation,
  plus the declared frame-to-clear-opening offset where present.
* EERO net clear height/width: read from Pset_ORI_EscapeOpening. They are
  never inferred from overall window size, because overall size is not net
  clear opening.
* Deck drop: deck top minus the lowest other slab top within the 36 in band
  beyond the deck edge (the band width is read from the rule unit).
* Guard height: IfcRailing (GUARDRAIL) top minus deck top.

Anything that cannot be measured is left missing, so the rule yields unknown.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import ifcopenshell
import ifcopenshell.geom as geom
import ifcopenshell.util.element as uel
import ifcopenshell.util.placement as upl
import ifcopenshell.util.shape as ushape
import ifcopenshell.util.unit as uunit

from .facts import Fact, Subject

M_PER_IN = 0.0254


def r6(x) -> float:
    """Plain float rounded to 6 places (keeps numpy scalars out of records)."""
    return float(round(float(x), 6))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class IfcFacts:
    def __init__(self, model: ifcopenshell.file, source_path: str | None = None, guard_band_in: float = 36.0):
        self.f = model
        self.source_path = source_path
        self.scale = uunit.calculate_unit_scale(model)  # metres per file length unit
        self.settings = geom.settings()
        self.settings.set("use-world-coords", True)
        self.guard_band_in = guard_band_in
        self._shape_cache: dict[int, Any] = {}

    # -- helpers ---------------------------------------------------------------
    def anchor(self, el) -> dict[str, Any]:
        a = {"type": "ifc_element", "ifc_guid": el.GlobalId, "ifc_class": el.is_a(), "name": el.Name, "model": self.source_path}
        bb = self.bbox_in(el)
        if bb is not None:
            c = (bb[0] + bb[1]) / 2 * M_PER_IN
            a["centroid_m"] = [r6(c[0]), r6(c[1]), r6(c[2])]
        return a

    def shape(self, el):
        if el.id() not in self._shape_cache:
            try:
                self._shape_cache[el.id()] = geom.create_shape(self.settings, el)
            except Exception:  # geometry kernel could not build a shape
                self._shape_cache[el.id()] = None
        return self._shape_cache[el.id()]

    def bbox_in(self, el):
        sh = self.shape(el)
        if sh is None:
            return None
        v = np.array(sh.geometry.verts, dtype=float).reshape(-1, 3)
        if v.size == 0:
            return None
        return v.min(0) / M_PER_IN, v.max(0) / M_PER_IN  # geometry kernel returns metres

    def len_in(self, value) -> float:
        return float(value) * self.scale / M_PER_IN

    def storey_elevation_in(self, el) -> float | None:
        container = uel.get_container(el)
        if container is None or not container.is_a("IfcBuildingStorey"):
            return None
        m = upl.get_local_placement(container.ObjectPlacement) if container.ObjectPlacement else np.eye(4)
        z = m[2, 3] if container.ObjectPlacement else float(container.Elevation or 0.0)
        return self.len_in(z)

    # -- stairs ----------------------------------------------------------------
    def _flight_profile_world(self, flight):
        """Return world (x, z) points in inches of the stepped profile, or None."""
        rep = flight.Representation
        if rep is None:
            return None
        for r in rep.Representations:
            if r.RepresentationIdentifier != "Body":
                continue
            for item in r.Items:
                if not item.is_a("IfcExtrudedAreaSolid"):
                    continue
                prof = item.SweptArea
                if not prof.is_a("IfcArbitraryClosedProfileDef") or not prof.OuterCurve.is_a("IfcPolyline"):
                    continue
                pts2 = [p.Coordinates for p in prof.OuterCurve.Points]
                solid_m = upl.get_axis2placement(item.Position) if item.Position else np.eye(4)
                obj_m = upl.get_local_placement(flight.ObjectPlacement) if flight.ObjectPlacement else np.eye(4)
                m = obj_m @ solid_m
                out = []
                for x, y in pts2:
                    w = m @ np.array([x, y, 0.0, 1.0])
                    out.append((self.len_in(w[0]), self.len_in(w[2])))
                return out
        return None

    @staticmethod
    def _steps_from_profile(pts: list[tuple[float, float]]):
        """Walk the stepped edge: alternating vertical rises and horizontal runs from the start."""
        tol = 1e-6
        risers, treads, nosings = [], [], []
        i = 0
        while i + 1 < len(pts):
            (x0, z0), (x1, z1) = pts[i], pts[i + 1]
            dx, dz = x1 - x0, z1 - z0
            if abs(dx) <= tol and dz > tol:
                risers.append(dz)
                nosings.append((x1, z1))
            elif abs(dz) <= tol and abs(dx) > tol and risers:
                treads.append(abs(dx))
            else:
                break
            i += 1
        return risers, treads, nosings

    def stair_subjects(self, overhead_classes=("IfcSlab", "IfcCovering", "IfcBeam")) -> list[Subject]:
        subjects = []
        overheads = [e for c in overhead_classes for e in self.f.by_type(c)]
        for flight in self.f.by_type("IfcStairFlight"):
            s = Subject(kind="stair_flight", subject_id=f"ifc:{flight.GlobalId}", label=flight.Name or flight.GlobalId, anchor=self.anchor(flight))
            pts = self._flight_profile_world(flight)
            if not pts:
                s.notes.append("No measurable stepped extrusion profile; riser, tread and headroom facts left missing.")
                subjects.append(s)
                continue
            risers, treads, nosings = self._steps_from_profile(pts)
            if len(risers) < 2 or len(treads) != len(risers) - 1:
                s.notes.append("Stepped profile not recognised; facts left missing.")
                subjects.append(s)
                continue
            anchor = self.anchor(flight)
            s.facts["riser_heights"] = Fact([r6(r) for r in risers], "ifc_geometry", anchor, "measured from stepped profile")
            s.facts["tread_depths"] = Fact([r6(t) for t in treads], "ifc_geometry", anchor, "measured from stepped profile")
            s.facts["headroom_clearances"] = Fact(self._headroom(flight, nosings, overheads), "ifc_geometry", anchor,
                                                  "vertical clearance from nosing line to underside of overlapping overhead elements")
            subjects.append(s)
        return subjects

    def _headroom(self, flight, nosings, overheads) -> list[float]:
        fb = self.bbox_in(flight)
        if fb is None:
            return []
        (fx0, fy0, _), (fx1, fy1, _) = fb
        xs = [n[0] for n in nosings]
        zs = [n[1] for n in nosings]
        top_z = max(zs)
        clearances = []
        for el in overheads:
            if el == flight:
                continue
            bb = self.bbox_in(el)
            if bb is None:
                continue
            (ox0, oy0, oz0), (ox1, oy1, _) = bb
            if oz0 <= top_z + 1e-6:  # not above the top of the flight
                continue
            lo, hi = max(ox0, min(xs)), min(ox1, max(xs))
            if lo > hi or oy1 < fy0 or oy0 > fy1:
                continue
            sample_x = [lo, hi] + [x for x in xs if lo <= x <= hi]
            for x in sample_x:
                z_line = float(np.interp(x, xs, zs))
                clearances.append(r6(oz0 - z_line))
        return clearances

    # -- spaces ----------------------------------------------------------------
    def space_subjects(self) -> list[Subject]:
        out = []
        for sp in self.f.by_type("IfcSpace"):
            s = Subject(kind="space", subject_id=f"ifc:{sp.GlobalId}", label=sp.Name or sp.GlobalId, anchor=self.anchor(sp))
            a = self.anchor(sp)
            props = uel.get_pset(sp, "Pset_ORI_SpaceUse") or {}
            if props.get("UseCategory") is not None:
                s.facts["space_use"] = Fact(props["UseCategory"], "ifc_property", a, "Pset_ORI_SpaceUse.UseCategory")
            if props.get("SlopedCeiling") is not None:
                s.facts["sloped_ceiling"] = Fact(bool(props["SlopedCeiling"]), "ifc_property", a, "Pset_ORI_SpaceUse.SlopedCeiling")
            bb = self.bbox_in(sp)
            sh = self.shape(sp)
            if bb is not None:
                s.facts["ceiling_height"] = Fact(r6(bb[1][2] - bb[0][2]), "ifc_geometry", a, "IfcSpace body top minus bottom")
            if sh is not None:
                area_m2 = ushape.get_footprint_area(sh.geometry)
                s.facts["floor_area"] = Fact(r6(area_m2 / (M_PER_IN * 12) ** 2), "ifc_geometry", a, "IfcSpace footprint area")
            out.append(s)
        return out

    # -- EERO ------------------------------------------------------------------
    def eero_subjects(self) -> list[Subject]:
        out = []
        for win in self.f.by_type("IfcWindow"):
            props = uel.get_pset(win, "Pset_ORI_EscapeOpening") or {}
            if not props.get("IsEmergencyEscapeOpening"):
                continue
            a = self.anchor(win)
            s = Subject(kind="eero", subject_id=f"ifc:{win.GlobalId}", label=win.Name or win.GlobalId, anchor=a)
            for key, fact in (("NetClearHeight", "net_clear_height"), ("NetClearWidth", "net_clear_width")):
                if props.get(key) is not None:
                    s.facts[fact] = Fact(r6(self.len_in(props[key])), "ifc_property", a, f"Pset_ORI_EscapeOpening.{key}")
            if props.get("NetClearArea") is not None:
                s.facts["net_clear_area"] = Fact(float(props["NetClearArea"]) * self.scale ** 2 / (M_PER_IN * 12) ** 2, "ifc_property", a, "Pset_ORI_EscapeOpening.NetClearArea")
            if props.get("GradeFloorOrBelowGrade") is not None:
                s.facts["grade_floor_or_below_grade"] = Fact(bool(props["GradeFloorOrBelowGrade"]), "ifc_property", a, "Pset_ORI_EscapeOpening.GradeFloorOrBelowGrade")
            storey_z = self.storey_elevation_in(win)
            if win.ObjectPlacement is not None and storey_z is not None:
                z = self.len_in(upl.get_local_placement(win.ObjectPlacement)[2, 3])
                frame_bottom = r6(z - storey_z)
                if props.get("SillToClearOpeningOffset") is not None:
                    s.facts["sill_height"] = Fact(r6(frame_bottom + self.len_in(props["SillToClearOpeningOffset"])), "ifc_geometry", a,
                                                  "window placement above storey plus declared frame-to-clear-opening offset")
                else:
                    s.facts["frame_bottom_height"] = Fact(frame_bottom, "ifc_geometry", a, "window placement above storey (frame bottom)")
            out.append(s)
        return out

    # -- decks and guards --------------------------------------------------------
    def deck_and_guard_subjects(self) -> list[Subject]:
        out = []
        slabs = list(self.f.by_type("IfcSlab"))
        rails = [r for r in self.f.by_type("IfcRailing") if (r.PredefinedType or "") == "GUARDRAIL"]
        band = self.guard_band_in
        for deck in slabs:
            ws = uel.get_pset(deck, "Pset_ORI_WalkingSurface") or {}
            if not ws.get("OpenSided"):
                continue
            bb = self.bbox_in(deck)
            a = self.anchor(deck)
            s = Subject(kind="walking_surface", subject_id=f"ifc:{deck.GlobalId}", label=deck.Name or deck.GlobalId, anchor=a)
            if bb is None:
                out.append(s)
                continue
            (dx0, dy0, _), (dx1, dy1, dtop) = bb
            below = []
            for other in slabs:
                if other == deck:
                    continue
                ob = self.bbox_in(other)
                if ob is None:
                    continue
                (ox0, oy0, _), (ox1, oy1, otop) = ob
                # intersects the band ring beyond the deck edge (expanded box, not fully inside the deck)
                intersects_expanded = not (ox1 < dx0 - band or ox0 > dx1 + band or oy1 < dy0 - band or oy0 > dy1 + band)
                inside_deck = ox0 >= dx0 and ox1 <= dx1 and oy0 >= dy0 and oy1 <= dy1
                if intersects_expanded and not inside_deck and otop < dtop - 1e-6:
                    below.append(otop)
            if below:
                s.facts["drop_height"] = Fact(r6(dtop - min(below)), "ifc_geometry", a, f"deck top minus lowest slab top within {band} in band")
            guards = []
            for r in rails:
                rb = self.bbox_in(r)
                if rb is None:
                    continue
                (rx0, ry0, rz0), (rx1, ry1, rtop) = rb
                near = not (rx1 < dx0 - 6 or rx0 > dx1 + 6 or ry1 < dy0 - 6 or ry0 > dy1 + 6)
                if near and abs(rz0 - dtop) <= 2.0:
                    guards.append((r, r6(rtop - dtop)))
            if guards:
                s.facts["guard_present"] = Fact(True, "ifc_geometry", a, "IfcRailing GUARDRAIL found at deck edge")
            # No railing found: guard_present stays missing (absence in a model is not evidence of absence).
            out.append(s)
            for r, h in guards:
                g = Subject(kind="guard", subject_id=f"ifc:{r.GlobalId}", label=r.Name or r.GlobalId, anchor=self.anchor(r))
                g.facts["guard_height"] = Fact(h, "ifc_geometry", self.anchor(r), "railing top minus walking-surface top")
                g.facts["on_stair_open_side"] = Fact(False, "ifc_geometry", self.anchor(r), "railing is at a deck edge, not a stair")
                out.append(g)
        return out

    def subjects(self) -> list[Subject]:
        return self.stair_subjects() + self.space_subjects() + self.eero_subjects() + self.deck_and_guard_subjects()


def extract(path: str | Path, guard_band_in: float = 36.0) -> tuple[list[Subject], dict[str, Any]]:
    path = Path(path)
    model = ifcopenshell.open(str(path))
    fx = IfcFacts(model, source_path=path.name, guard_band_in=guard_band_in)
    artifact = {
        "artifact_id": f"urn:ori:artifact:sha256:{sha256_file(path)}",
        "media_type": "application/x-step",
        "schema": model.schema,
        "filename": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
    return fx.subjects(), artifact
