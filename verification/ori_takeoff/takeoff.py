# SPDX-License-Identifier: Apache-2.0
"""Takeoff quantities from overlay page elements. Real-world totals are null when the scale is unknown."""

from __future__ import annotations


def _sum(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals), 3) if vals else None


def page_takeoff(page: dict, footprint=None, k: float | None = None) -> dict:
    els = page["elements"]
    by = lambda c: [e for e in els if e["ifc_class"] == c]  # noqa: E731
    walls, doors, wins, opens, spaces, stairs = (by("IfcWall"), by("IfcDoor"), by("IfcWindow"), by("IfcOpeningElement"),
                                                 by("IfcSpace"), by("IfcStair"))
    dims = [e for e in by("IfcAnnotation") if e.get("annotation_type") == "dimension"]
    known = k is not None
    t = {
        "units": {"length": "in", "area": "ft2"},
        "scale_status": page["scale"]["status"],
        "walls": {"count": len(walls),
                  "total_length_in": _sum(e["properties"].get("length_in") for e in walls) if known else None,
                  "exterior_length_in": _sum(e["properties"].get("length_in") for e in walls if e["properties"].get("exterior")) if known else None,
                  "interior_length_in": _sum(e["properties"].get("length_in") for e in walls if not e["properties"].get("exterior")) if known else None,
                  "length_convention": "centreline; exterior walls meet at centreline corners, interior walls end at the face they meet"},
        "doors": {"count": len(doors), "widths_in": sorted(e["properties"].get("width_in") for e in doors) if known else None},
        "windows": {"count": len(wins), "widths_in": sorted(e["properties"].get("width_in") for e in wins) if known else None},
        "unclassified_openings": {"count": len(opens)},
        "spaces": {"count": len(spaces), "total_net_area_ft2": _sum(e["properties"].get("area_ft2") for e in spaces) if known else None,
                   "items": [{"id": e["id"], "label": e["properties"].get("label"), "area_ft2": e["properties"].get("area_ft2")} for e in spaces]},
        "gross_footprint_ft2": round(footprint.area * k * k / 144, 3) if (known and footprint is not None) else None,
        "stairs": [{"id": e["id"], "riser_count": e["properties"].get("riser_count"), "tread_count": e["properties"].get("tread_count"),
                    "tread_depth_in": e["properties"].get("tread_depth_in"), "riser_height_in": None} for e in stairs],
        "dimensions": {"count": len(dims), "agreeing_with_geometry": sum(1 for e in dims if e["properties"].get("agrees") is True)},
        "label": "Takeoff from auto-extracted, unreviewed elements. Not a measurement certified by anyone.",
    }
    return t
