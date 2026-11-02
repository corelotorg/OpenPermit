# SPDX-License-Identifier: Apache-2.0
"""Overlay to a simple IFC 4.3 model (IfcOpenShell), and ORI checks on that model.

What is exported:
* one IfcBuildingStorey per overlay page that has a usable scale (pages without scale are skipped
  and listed), elevation from the overlay storey where known, otherwise stacked by the noted
  floor-to-floor height, otherwise 0 with ``ElevationKnown = False``;
* IfcWall: axis (IfcPolyline) and an extruded rectangular body;
* IfcOpeningElement voiding the host wall, filled by IfcDoor / IfcWindow (OverallWidth from the
  plan; OverallHeight left empty because a plan does not show it);
* IfcSpace: extruded footprint, Pset_ORI_SpaceUse.UseCategory from the label;
* IfcStair (no flight geometry: riser heights are not measurable on a plan).

Heights are not on a plan. Where the overlay has no height, the body uses a placeholder height
for viewing only, recorded as ``Pset_ORI_Takeoff.HeightSource = "placeholder_not_from_plan"``;
``check_ifc`` drops every fact derived from a placeholder height so it yields unknown. Every
element carries ``Pset_ORI_Takeoff`` (Method, ReviewStatus, Confidence, OverlayElementId, Tool).
Facts from auto-extracted, unreviewed elements are marked ``vector_extracted_unconfirmed`` and
give unknown until a person confirms them.
"""

from __future__ import annotations

import math
import copy
import hashlib
import json
import uuid
from pathlib import Path

import ifcopenshell
import ifcopenshell.api as api

from . import TOOL_ID

MM = 25.4
PLACEHOLDER_STOREY_IN = 96.0
OPENING_PLACEHOLDER_IN = {"IfcDoor": (0.0, 80.0), "IfcWindow": (36.0, 48.0), "IfcOpeningElement": (0.0, 80.0)}


class _B:
    def __init__(self, name: str):
        self.f = api.run("project.create_file", version="IFC4X3")
        self.project = api.run("root.create_entity", self.f, ifc_class="IfcProject", name=name)
        api.run("unit.assign_unit", self.f, length={"is_metric": True, "raw": "MILLIMETERS"})
        ctx = api.run("context.add_context", self.f, context_type="Model")
        self.body = api.run("context.add_context", self.f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
        self.axis = api.run("context.add_context", self.f, context_type="Model", context_identifier="Axis", target_view="GRAPH_VIEW", parent=ctx)
        self.site = api.run("root.create_entity", self.f, ifc_class="IfcSite", name="Site (not georeferenced)")
        self.building = api.run("root.create_entity", self.f, ifc_class="IfcBuilding", name="Building from plan overlay")
        api.run("aggregate.assign_object", self.f, products=[self.site], relating_object=self.project)
        api.run("aggregate.assign_object", self.f, products=[self.building], relating_object=self.site)

    def pt2(self, x, y):
        return self.f.createIfcCartesianPoint((float(x), float(y)))

    def placement(self, x=0.0, y=0.0, z=0.0, ang=0.0, rel=None):
        d = self.f.createIfcDirection((math.cos(ang), math.sin(ang), 0.0))
        a = self.f.createIfcAxis2Placement3D(self.f.createIfcCartesianPoint((float(x), float(y), float(z))),
                                             self.f.createIfcDirection((0.0, 0.0, 1.0)), d)
        return self.f.createIfcLocalPlacement(rel, a)

    def extrude(self, ring_mm, height_mm, z=0.0):
        pts = [self.pt2(x, y) for x, y in ring_mm] + [self.pt2(*ring_mm[0])]
        prof = self.f.createIfcArbitraryClosedProfileDef("AREA", None, self.f.createIfcPolyline(pts))
        pos = self.f.createIfcAxis2Placement3D(self.f.createIfcCartesianPoint((0.0, 0.0, float(z))), None, None)
        return self.f.createIfcExtrudedAreaSolid(prof, pos, self.f.createIfcDirection((0.0, 0.0, 1.0)), float(height_mm))

    def shape(self, product, items, axis_pts=None):
        reps = [self.f.createIfcShapeRepresentation(self.body, "Body", "SweptSolid", items)]
        if axis_pts:
            reps.append(self.f.createIfcShapeRepresentation(self.axis, "Axis", "Curve2D",
                                                            [self.f.createIfcPolyline([self.pt2(*p) for p in axis_pts])]))
        product.Representation = self.f.createIfcProductDefinitionShape(None, None, reps)

    def pset(self, product, name, props):
        ps = api.run("pset.add_pset", self.f, product=product, name=name)
        api.run("pset.edit_pset", self.f, pset=ps, properties={k: v for k, v in props.items() if v is not None})


def _ring_mm(geom, ox, oy):
    return [((x - ox) * MM, (y - oy) * MM) for x, y in geom["coordinates"][0][:-1]]


def overlay_to_ifc(doc: dict, path: str | Path, name: str | None = None) -> dict:
    """Write an IFC 4.3 file; returns a summary with what was skipped and why."""
    # Work on a copy: review exclusions never rewrite original evidence.
    doc = copy.deepcopy(doc)
    overlay_sha = hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    seen = set()
    page_numbers = set()
    for page in doc["pages"]:
        if page["page"] in page_numbers:
            raise ValueError("duplicate overlay page")
        page_numbers.add(page["page"])
        scale = page["scale"]
        factor = scale["real_in_per_page_unit"]
        if factor is not None and (isinstance(factor, bool) or not isinstance(factor, (float, int)) or factor <= 0):
            raise ValueError("invalid page scale")
        for element in page["elements"]:
            key = (page["page"], element["id"])
            if key in seen:
                raise ValueError(f"duplicate overlay element: {key}")
            seen.add(key)
    excluded = []
    for page in doc["pages"]:
        accepted = []
        live_walls = {e["id"] for e in page["elements"] if e["ifc_class"] == "IfcWall" and e.get("geometry_real") and e["provenance"]["review_status"] != "rejected"}
        for e in page["elements"]:
            reason = "review_rejected" if e["provenance"]["review_status"] == "rejected" else None
            if not reason and e["ifc_class"] in OPENING_PLACEHOLDER_IN and e.get("relations", {}).get("host_wall") not in live_walls:
                reason = "host_wall_not_exported"
            if reason:
                excluded.append({"page": page["page"], "element_id": e["id"], "reason": reason})
            else:
                accepted.append(e)
        page["elements"] = accepted
    b = _B(name or f"ORI plan takeoff: {doc['source']['filename']}")
    summary = {"ifc_schema": "IFC4X3", "storeys": [], "skipped_pages": [], "counts": {}, "placeholders": []}
    summary.update({"handoff_profile": "ori-ifc-handoff-0.1", "overlay_id": doc["overlay_id"],
                    "overlay_sha256": overlay_sha, "source_artifact_id": doc["source"]["artifact_id"],
                    "excluded_elements": excluded, "elements": [], "coordinate_transforms": []})
    pages = [p for p in doc["pages"] if p["scale"]["real_in_per_page_unit"] is not None and p["scale"]["status"] in ("stated_confirmed", "stated", "calibrated", "drawing_units") and p["status"] != "needs_tracing"]
    summary["skipped_pages"] = [{"page": p["page"], "reason": f"scale {p['scale']['status']} or {p['status']}"}
                                for p in doc["pages"] if p not in pages]
    # common origin: lower-left of all walls across pages (real inches), so floors stack
    xs, ys = [], []
    for p in pages:
        for e in p["elements"]:
            if e["ifc_class"] == "IfcWall" and e["geometry_real"]:
                for x, y in e["geometry_real"]["coordinates"][0]:
                    xs.append(x)
                    ys.append(y)
    ox, oy = (min(xs), min(ys)) if xs else (0.0, 0.0)
    z_next = 0.0
    counts: dict[str, int] = {}
    for p in pages:
        st = p.get("storey") or {}
        elev = st.get("elevation_in")
        known = elev is not None
        if not known:
            elev = z_next
        ftf = st.get("floor_to_floor_in") or st.get("noted_floor_to_floor_in")
        ceil = st.get("ceiling_height_in") or st.get("noted_ceiling_height_in")
        storey = api.run("root.create_entity", b.f, ifc_class="IfcBuildingStorey", name=st.get("name") or f"Page {p['page']} {p.get('page_label')}")
        storey.Elevation = float(elev * MM)
        storey.ObjectPlacement = b.placement(0, 0, elev * MM)
        api.run("aggregate.assign_object", b.f, products=[storey], relating_object=b.building)
        b.pset(storey, "Pset_ORI_Takeoff", {"ElevationKnown": known, "SourcePage": int(p["page"]), "SourceSheet": str(p.get("page_label")),
                                             "Tool": TOOL_ID, "ScaleStatus": p["scale"]["status"]})
        summary["storeys"].append({"name": storey.Name, "page": p["page"], "elevation_in": elev, "elevation_known": known})
        z_next = elev + (ftf or PLACEHOLDER_STOREY_IN)
        wall_h = ftf or PLACEHOLDER_STOREY_IN
        wall_src = ("sheet_note_unconfirmed" if st.get("noted_floor_to_floor_in") and not st.get("floor_to_floor_in") else "overlay") if ftf else "placeholder_not_from_plan"
        space_h = ceil or PLACEHOLDER_STOREY_IN
        space_src = ("sheet_note_unconfirmed" if st.get("noted_ceiling_height_in") and not st.get("ceiling_height_in") else "overlay") if ceil else "placeholder_not_from_plan"
        if wall_src == "placeholder_not_from_plan":
            summary["placeholders"].append(f"page {p['page']}: wall height")
        if space_src == "placeholder_not_from_plan":
            summary["placeholders"].append(f"page {p['page']}: space height")
        summary["coordinate_transforms"].append({
            "page": p["page"], "sheet": p.get("page_label"), "page_units": p.get("page_units"),
            "page_axis_convention": "pdf_media_box_bottom_left_xy" if p.get("page_units") == "pt" else "source_drawing_xy",
            "real_in_per_page_unit": p["scale"]["real_in_per_page_unit"], "scale_status": p["scale"]["status"],
            "origin_real_in": [ox, oy], "storey_elevation_in": elev, "elevation_known": known,
            "page_xy_to_ifc_world_mm": [[p["scale"]["real_in_per_page_unit"]*MM, 0, -ox*MM],
                                         [0, p["scale"]["real_in_per_page_unit"]*MM, -oy*MM],
                                         [0, 0, elev*MM]],
            "ifc_units": "millimetres", "ifc_up_axis": "Z", "viewer_metres_per_ifc_unit": 0.001,
            "cross_page_registration": "unverified", "georeferenced": False})
        walls = {}

        def tag(prod, e, height_src=None):
            pr = e["provenance"]
            role = "void" if prod.is_a() == "IfcOpeningElement" else "primary"
            identity = json.dumps([doc["source"]["artifact_id"], doc["overlay_id"], p["page"], e["id"], prod.is_a(), role], separators=(",", ":"))
            prod.GlobalId = ifcopenshell.guid.compress(uuid.uuid5(uuid.NAMESPACE_URL, "ori-ifc-element:" + identity).hex)
            summary["elements"].append({"page": p["page"], "sheet": p.get("page_label"), "overlay_element_id": e["id"],
                                        "ifc_guid": prod.GlobalId, "ifc_class": prod.is_a(), "role": role,
                                        "review_status": pr["review_status"], "method": pr["method"],
                                        "height_source": height_src, "derived_from": pr.get("derived_from")})
            b.pset(prod, "Pset_ORI_Takeoff", {"Method": pr["method"], "ReviewStatus": pr["review_status"],
                                               "Confidence": pr.get("confidence"), "OverlayElementId": e["id"], "Tool": TOOL_ID,
                                               "HeightSource": height_src, "SourcePage": int(p["page"]),
                                               "SourceSheet": p.get("page_label"), "SourceArtifactId": doc["source"]["artifact_id"],
                                               "OverlayId": doc["overlay_id"], "OverlaySha256": overlay_sha,
                                               "DerivedFrom": pr.get("derived_from")})
            counts[prod.is_a()] = counts.get(prod.is_a(), 0) + 1

        for e in p["elements"]:
            if e["ifc_class"] != "IfcWall" or not e.get("geometry_real"):
                continue
            w = api.run("root.create_entity", b.f, ifc_class="IfcWall", name=e.get("name") or e["id"], predefined_type="SOLIDWALL")
            w.ObjectPlacement = b.placement(rel=storey.ObjectPlacement)
            ax = [((x - ox) * MM, (y - oy) * MM) for x, y in e["axis_real"]["coordinates"]] if e.get("axis_real") else None
            b.shape(w, [b.extrude(_ring_mm(e["geometry_real"], ox, oy), wall_h * MM)], ax)
            api.run("spatial.assign_container", b.f, products=[w], relating_structure=storey)
            tag(w, e, wall_src)
            walls[e["id"]] = w
        for e in p["elements"]:
            if e["ifc_class"] not in ("IfcDoor", "IfcWindow", "IfcOpeningElement") or not e.get("geometry_real"):
                continue
            host = walls.get(e["relations"].get("host_wall"))
            sill, h = OPENING_PLACEHOLDER_IN[e["ifc_class"]]
            op = api.run("root.create_entity", b.f, ifc_class="IfcOpeningElement", name=f"Opening {e['id']}")
            op.ObjectPlacement = b.placement(rel=storey.ObjectPlacement)
            ring = _ring_mm(e["geometry_real"], ox, oy)
            b.shape(op, [b.extrude(ring, h * MM, sill * MM)])
            tag(op, e, "placeholder_not_from_plan")
            if host is not None:
                api.run("feature.add_feature", b.f, feature=op, element=host)
            if e["ifc_class"] != "IfcOpeningElement":
                fill = api.run("root.create_entity", b.f, ifc_class=e["ifc_class"], name=e.get("name") or e["id"])
                fill.ObjectPlacement = b.placement(rel=storey.ObjectPlacement)
                b.shape(fill, [b.extrude(ring, h * MM, sill * MM)])
                fill.OverallWidth = float((e["properties"].get("width_in") or 0) * MM) or None
                fill.OverallHeight = None
                api.run("spatial.assign_container", b.f, products=[fill], relating_structure=storey)
                api.run("feature.add_filling", b.f, opening=op, element=fill)
                tag(fill, e, "placeholder_not_from_plan")
                if e["ifc_class"] == "IfcDoor" and e["properties"].get("swing"):
                    b.pset(fill, "Pset_ORI_DoorSwing", {"OpensToNormalSide": e["properties"]["swing"].get("opens_to_normal_side"),
                                                         "RadiusIn": e["properties"]["swing"].get("radius_in")})
        for e in p["elements"]:
            if e["ifc_class"] != "IfcSpace" or not e.get("geometry_real"):
                continue
            sp = api.run("root.create_entity", b.f, ifc_class="IfcSpace", name=e.get("name") or e["id"], predefined_type="SPACE")
            sp.ObjectPlacement = b.placement(rel=storey.ObjectPlacement)
            b.shape(sp, [b.extrude(_ring_mm(e["geometry_real"], ox, oy), space_h * MM)])
            api.run("aggregate.assign_object", b.f, products=[sp], relating_object=storey)
            if e["properties"].get("use"):
                b.pset(sp, "Pset_ORI_SpaceUse", {"UseCategory": e["properties"]["use"], "UseSource": e["properties"].get("use_source") or "overlay"})
            tag(sp, e, space_src)
        for e in p["elements"]:
            if e["ifc_class"] != "IfcStair":
                continue
            s = api.run("root.create_entity", b.f, ifc_class="IfcStair", name=e.get("name") or e["id"], predefined_type="STRAIGHT_RUN_STAIR")
            s.ObjectPlacement = b.placement(rel=storey.ObjectPlacement)
            api.run("spatial.assign_container", b.f, products=[s], relating_structure=storey)
            pr = e["properties"]
            b.pset(s, "Pset_ORI_StairFromPlan", {"RiserCount": pr.get("riser_count"), "TreadCount": pr.get("tread_count"),
                                                  "TreadDepthIn": pr.get("tread_depth_in"), "RiserHeightKnown": pr.get("riser_height_in") is not None})
            tag(s, e, None)
    summary["counts"] = counts
    path = Path(path)
    b.f.write(str(path))
    summary["ifc_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return summary


def check_ifc(path: str | Path, jurisdiction: str | None = None) -> dict:
    """Run IfcOpenShell schema validation and the ORI rule units on the exported model.

    The provenance policy lives in ``ori_verify.ifc_extract.IfcFacts._takeoff_policy`` so this check and
    ``ori_verify.cli ifc`` give the same results: placeholder heights are removed (missing -> unknown) and
    unreviewed auto-extracted facts are re-labelled ``vector_extracted_unconfirmed`` (-> unknown)."""
    import ifcopenshell.validate as iv

    from ori_verify import ifc_extract, records, rules, units

    model = ifcopenshell.open(str(path))
    logger = iv.json_logger()
    iv.validate(model, logger)
    schema_issues = [str(s.get("message"))[:200] for s in logger.statements]
    jur = jurisdiction or units.VA
    eff = units.implemented_units(jur)
    fx = ifc_extract.IfcFacts(model, source_path=Path(path).name)
    subjects = fx.subjects()  # provenance policy (placeholder / unreviewed) is applied inside the extractor
    adjust = list(fx.adjustments)
    results = rules.evaluate(subjects, eff)
    artifact = {"artifact_id": f"urn:ori:artifact:sha256:{ifc_extract.sha256_file(Path(path))}", "media_type": "application/x-step",
                "schema": model.schema, "filename": Path(path).name, "sha256": ifc_extract.sha256_file(Path(path)),
                "size_bytes": Path(path).stat().st_size}
    report = records.build_report(results, eff, artifact, "ifc_model", jur, executed_at="2026-10-03T00:00:00Z")
    report["takeoff_adjustments"] = adjust
    report["schema_validation"] = {"tool": f"ifcopenshell.validate {ifcopenshell.version}", "issues": len(schema_issues),
                                   "first_issues": schema_issues[:10]}
    report["subjects_found"] = {k: sum(1 for s in subjects if s.kind == k) for k in sorted({s.kind for s in subjects})}
    return report
