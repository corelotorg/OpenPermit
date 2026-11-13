# SPDX-License-Identifier: Apache-2.0
"""Deterministic rule functions for implemented Chapter 6 (wall construction) rule units.

Same contract as ``rules.py``: ``fn(subject, unit) -> Result``; thresholds come from
rule-unit data; missing or unconfirmed facts give ``unknown``, never ``fail``.

Extra safeguard for Chapter 6: a parameter whose ``value_status`` is ``estimate``
(UNVERIFIED against an official source) is never used for pass or fail. The function
still computes the comparison and reports it, but returns ``unknown`` with reason
``threshold_unverified`` so a reviewer checks the official value.

Results are reviewer evidence, not approval.
"""

from __future__ import annotations

from typing import Any

from .facts import Subject
from .rules import (EPS_IN, FAIL, NA, PASS, UNKNOWN, Result, _base, _cmp, _deleted_or_unparam, _need, _req)
from .units import EffectiveUnit

EPS_FT = EPS_IN / 12
UNVERIFIED = "estimate"
PRACTICAL_METHOD = "VA-R602.12"


def _kind(unit, subject, kind, what):
    if subject.kind != kind:
        return _base(unit, subject, NA, "subject_kind_not_applicable", f"Applies to {what} only.")
    return None


def _verdict(unit, subject, ok: bool, req: dict, label: str, measured: dict, facts_used: dict, detail: str) -> Result:
    kw = dict(measured=measured, required=[req], facts_used=facts_used)
    if req["value_status"] == UNVERIFIED:
        would = "meet" if ok else "not meet"
        return _base(unit, subject, UNKNOWN, "threshold_unverified",
                     f"{label}: {detail}; this would {would} {req['comparator']} {req['value']} {req['unit']}, but that value is UNVERIFIED "
                     "(not yet checked against the official 2021 text). Reviewer to confirm.", **kw)
    if ok:
        return _base(unit, subject, PASS, "threshold_met", f"{label}: {detail} {req['comparator']} {req['value']} {req['unit']}.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"{label}: {detail} does not satisfy {req['comparator']} {req['value']} {req['unit']}.", **kw)


def _used(facts) -> dict[str, Any]:
    return {k: f.as_record() for k, f in facts.items()}


# -- framed walls (IRC base values: currently all UNVERIFIED) ---------------------------
def framing_stud_spacing_max(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _kind(unit, subject, "framed_wall", "framed walls")
    if r:
        return r
    facts, r = _need(unit, subject, ["bearing"])
    if r:
        return r
    if not facts["bearing"].value:
        return _base(unit, subject, NA, "nonbearing_wall", "Nonbearing wall; this unit covers bearing-wall stud spacing only.")
    facts2, r = _need(unit, subject, ["stud_size", "floors_supported", "stud_spacing"])
    if r:
        return r
    facts.update(facts2)
    size, floors = facts["stud_size"].value, facts["floors_supported"].value
    key = {("2x4", 0): "max_stud_spacing_2x4_roof_only", ("2x4", 1): "max_stud_spacing_2x4_one_floor",
           ("2x6", 1): "max_stud_spacing_2x6_one_floor", ("2x6", 2): "max_stud_spacing_2x6_two_floors"}.get((size, floors))
    if key is None or unit.param(key) is None:
        return _base(unit, subject, UNKNOWN, "threshold_not_encoded",
                     f"No encoded threshold for {size} studs carrying {floors} floor(s); ORI encodes only the table cells its tests need (owner decision pending). Reviewer to check the stud table.",
                     facts_used=_used(facts))
    req = _req(unit, key)
    sp = float(facts["stud_spacing"].value)
    return _verdict(unit, subject, _cmp(sp, req["comparator"], req["value"], EPS_IN), req, "Stud spacing",
                    {"stud_spacing": sp, "unit": "in", "stud_size": size, "floors_supported": floors}, _used(facts), f"{sp:g} in on center")


def framing_bearing_stud_height_max(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _kind(unit, subject, "framed_wall", "framed walls") or _deleted_or_unparam(unit, subject, ["max_bearing_stud_height"])
    if r:
        return r
    facts, r = _need(unit, subject, ["bearing"])
    if r:
        return r
    if not facts["bearing"].value:
        return _base(unit, subject, NA, "nonbearing_wall", "Nonbearing wall; this unit covers bearing studs.")
    req = _req(unit, "max_bearing_stud_height")
    limit_in = req["value"] * 12
    sh = subject.get("stud_height")
    if sh is not None and sh.usable:
        h = float(sh.value)
        facts["stud_height"] = sh
    else:
        wh = subject.get("wall_height")
        if sh is None and wh is not None and wh.usable and float(wh.value) <= limit_in + EPS_IN:
            # Stud height cannot exceed the wall body height, so the body height bounds it from above.
            h = float(wh.value)
            facts["wall_height"] = wh
        else:
            _, r = _need(unit, subject, ["stud_height"])
            return r
    return _verdict(unit, subject, _cmp(h / 12, req["comparator"], req["value"], EPS_IN / 12), req, "Bearing stud height",
                    {"stud_height_in": h, "unit": "in"}, _used(facts), f"{h:g} in ({h / 12:.2f} ft)")


def framing_top_plate_count_min(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _kind(unit, subject, "framed_wall", "framed walls") or _deleted_or_unparam(unit, subject, ["min_top_plate_count"])
    if r:
        return r
    facts, r = _need(unit, subject, ["bearing"])
    if r:
        return r
    ext = subject.get("exterior")
    if not facts["bearing"].value and not (ext is not None and ext.usable and ext.value):
        return _base(unit, subject, NA, "nonbearing_wall", "Interior nonbearing wall; R602.5 governs its plates.")
    facts2, r = _need(unit, subject, ["top_plate_count"])
    if r:
        return r
    facts.update(facts2)
    n = int(facts["top_plate_count"].value)
    req = _req(unit, "min_top_plate_count")
    res = _verdict(unit, subject, n >= req["value"], req, "Top plates", {"top_plate_count": n}, _used(facts), f"{n} top plate(s)")
    if res.state == FAIL:  # single plate is allowed with ties; that needs a reviewer
        return _base(unit, subject, UNKNOWN, "exception_requires_reviewer",
                     f"Top plates: {n}; a single plate is allowed with ties at joints and corners, which a reviewer must confirm.",
                     measured=res.measured, required=res.required, facts_used=res.facts_used)
    return res


def framing_top_plate_splice_offset_min(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _kind(unit, subject, "framed_wall", "framed walls") or _deleted_or_unparam(unit, subject, ["min_top_plate_splice_offset"])
    if r:
        return r
    pc = subject.get("top_plate_count")
    if pc is not None and pc.usable and int(pc.value) < 2:
        return _base(unit, subject, NA, "single_top_plate", "Single top plate; splice offset between plates does not arise.")
    facts, r = _need(unit, subject, ["top_plate_splice_offset"])
    if r:
        return r
    v = float(facts["top_plate_splice_offset"].value)
    req = _req(unit, "min_top_plate_splice_offset")
    return _verdict(unit, subject, _cmp(v, req["comparator"], req["value"], EPS_IN), req, "Top plate splice offset",
                    {"top_plate_splice_offset": v, "unit": "in"}, _used(facts), f"{v:g} in")


def _ratio_rule(subject, unit, fact, label, keys):
    r = _kind(unit, subject, "framed_wall", "framed walls")
    if r:
        return r
    facts, r = _need(unit, subject, ["bearing", "stud_depth", fact])
    if r:
        return r
    bearing = bool(facts["bearing"].value)
    key = keys(bearing, subject)
    if isinstance(key, Result):
        return key
    if unit.param(key) is None:
        return _base(unit, subject, UNKNOWN, "parameter_missing", f"Rule-unit parameter {key} is not defined for this jurisdiction.")
    ratio = float(facts[fact].value) / float(facts["stud_depth"].value)
    req = _req(unit, key)
    return _verdict(unit, subject, _cmp(ratio, req["comparator"], req["value"], 1e-9), req, label,
                    {fact: facts[fact].value, "stud_depth": facts["stud_depth"].value, "ratio": round(ratio, 6)}, _used(facts),
                    f"{facts[fact].value:g} in of {facts['stud_depth'].value:g} in stud depth (ratio {ratio:.3f})")


def framing_bored_hole_ratio_max(subject: Subject, unit: EffectiveUnit) -> Result:
    def keys(bearing, s):
        if not bearing:
            return "max_bored_hole_ratio_nonbearing"
        d = s.get("stud_doubled")
        if d is None or not d.usable:
            # Undoubled limit is the stricter one; use it only if it passes, else ask.
            return "max_bored_hole_ratio_bearing"
        return "max_bored_hole_ratio_bearing_doubled" if d.value else "max_bored_hole_ratio_bearing"
    return _ratio_rule(subject, unit, "max_bored_hole_diameter", "Bored hole", keys)


def framing_notch_ratio_max(subject: Subject, unit: EffectiveUnit) -> Result:
    return _ratio_rule(subject, unit, "max_notch_depth", "Stud notch",
                       lambda bearing, s: "max_notch_ratio_bearing" if bearing else "max_notch_ratio_nonbearing")


# -- Virginia practical wall bracing (13VAC5-63-210 item 64; values sourced_primary) ----
def _practical(unit, subject, kind, what):
    r = _kind(unit, subject, kind, what)
    if r:
        return r
    if unit.deleted:
        return _base(unit, subject, NA, "deleted_by_jurisdiction", "The jurisdiction layer deletes this provision.")
    if not unit.params:
        return _base(unit, subject, UNKNOWN, "parameter_missing",
                     "No parameters for this jurisdiction: Virginia practical wall bracing (R602.12 as replaced by 13VAC5-63-210) is not part of the IRC base.")
    if kind == "braced_wall_panel":
        m = subject.get("bracing_method")
        if m is None or not m.usable:
            return _base(unit, subject, UNKNOWN, "missing_information" if m is None else "unconfirmed_extraction",
                         "Bracing method not declared; practical-bracing rules apply only to panels declared under Virginia R602.12.")
        if m.value != PRACTICAL_METHOD:
            return _base(unit, subject, NA, "other_bracing_method", f"Panel declares bracing method {m.value!r}, not {PRACTICAL_METHOD}.")
    return None


def practical_bracing_sheathing(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _practical(unit, subject, "braced_wall_panel", "braced wall panels")
    if r:
        return r
    facts, r = _need(unit, subject, ["sheathing_material", "panel_location"])
    if r:
        return r
    mat, loc = facts["sheathing_material"].value, facts["panel_location"].value
    if mat == "gypsum_board" and loc == "exterior":
        return _base(unit, subject, FAIL, "material_not_permitted", "Gypsum board counts as practical bracing on interior walls only; this panel is exterior.",
                     measured={"sheathing_material": mat, "panel_location": loc}, facts_used=_used(facts))
    key = {"wood_structural_panel": "min_thickness_wood_structural_panel", "structural_fiberboard": "min_thickness_structural_fiberboard",
           "gypsum_board": "min_thickness_gypsum_board"}.get(mat)
    if key is None:
        return _base(unit, subject, UNKNOWN, "exception_requires_reviewer",
                     f"Sheathing material {mat!r} is not one of the practical-bracing materials; a reviewer decides whether another method applies.",
                     facts_used=_used(facts))
    facts2, r = _need(unit, subject, ["sheathing_thickness"])
    if r:
        return r
    facts.update(facts2)
    t = float(facts["sheathing_thickness"].value)
    req = _req(unit, key)
    return _verdict(unit, subject, _cmp(t, req["comparator"], req["value"], EPS_IN), req, "Bracing sheathing thickness",
                    {"sheathing_thickness": t, "unit": "in", "sheathing_material": mat}, _used(facts), f"{t:g} in {mat}")


def practical_bracing_exterior_panel_length(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _practical(unit, subject, "braced_wall_panel", "braced wall panels")
    if r:
        return r
    facts, r = _need(unit, subject, ["panel_location"])
    if r:
        return r
    if facts["panel_location"].value != "exterior":
        return _base(unit, subject, NA, "interior_panel", "Interior panel; the exterior panel-length table does not apply.")
    facts2, r = _need(unit, subject, ["panel_length", "wall_height"])
    if r:
        return r
    facts.update(facts2)
    wh_ft = float(facts["wall_height"].value) / 12
    if abs(wh_ft - 8) > 1e-3:
        return _base(unit, subject, UNKNOWN, "threshold_not_encoded",
                     f"Wall height {wh_ft:.2f} ft: only the 8 ft column of the panel-length table is encoded (owner decision pending). Reviewer to check.",
                     facts_used=_used(facts))
    garage = subject.get("adjacent_one_story_garage_door")
    if garage is not None and garage.usable and garage.value:
        key = "min_panel_length_8ft_garage_one_story"
    else:
        f3, r = _need(unit, subject, ["adjacent_opening_clear_height"])
        if r:
            return r
        facts.update(f3)
        oh = float(facts["adjacent_opening_clear_height"].value)
        key = ("min_panel_length_8ft_opening_le_64" if oh <= 64 + EPS_IN else "min_panel_length_8ft_opening_le_72" if oh <= 72 + EPS_IN
               else "min_panel_length_8ft_opening_le_80" if oh <= 80 + EPS_IN else "min_panel_length_8ft_opening_gt_80")
    req = _req(unit, key)
    L = float(facts["panel_length"].value)
    return _verdict(unit, subject, _cmp(L, req["comparator"], req["value"], EPS_IN), req, "Exterior braced panel length",
                    {"panel_length": L, "unit": "in", "wall_height_ft": round(wh_ft, 4)}, _used(facts), f"{L:g} in")


def practical_bracing_interior_panel_length(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _practical(unit, subject, "braced_wall_panel", "braced wall panels")
    if r:
        return r
    facts, r = _need(unit, subject, ["panel_location"])
    if r:
        return r
    if facts["panel_location"].value != "interior":
        return _base(unit, subject, NA, "exterior_panel", "Exterior panel; the interior minimum does not apply.")
    f2, r = _need(unit, subject, ["panel_length"])
    if r:
        return r
    facts.update(f2)
    L = float(facts["panel_length"].value)
    req = _req(unit, "min_interior_panel_length")
    return _verdict(unit, subject, _cmp(L, req["comparator"], req["value"], EPS_IN), req, "Interior braced panel length",
                    {"panel_length": L, "unit": "in"}, _used(facts), f"{L:g} in")


def practical_bracing_rectangle_limits(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _practical(unit, subject, "bracing_rectangle", "bracing rectangles")
    if r:
        return r
    facts, r = _need(unit, subject, ["rectangle_sides"])
    if r:
        return r
    a, b = (float(v) for v in facts["rectangle_sides"].value)
    side_req, ar_req = _req(unit, "max_rectangle_side"), _req(unit, "max_rectangle_aspect_ratio")
    longest, ratio = max(a, b), max(a, b) / min(a, b) if min(a, b) > 0 else float("inf")
    ok_side = _cmp(longest, side_req["comparator"], side_req["value"], EPS_FT)
    ok_ratio = _cmp(ratio, ar_req["comparator"], ar_req["value"], 1e-9)
    kw = dict(measured={"sides_ft": [a, b], "longest_ft": longest, "aspect_ratio": round(ratio, 6)}, required=[side_req, ar_req], facts_used=_used(facts))
    if ok_side and ok_ratio:
        return _base(unit, subject, PASS, "threshold_met", f"Rectangle {a:g} x {b:g} ft: longest side and aspect ratio within limits.", **kw)
    why = []
    if not ok_side:
        why.append(f"longest side {longest:g} ft > {side_req['value']} ft")
    if not ok_ratio:
        why.append(f"aspect ratio {ratio:.2f} > {ar_req['value']}")
    return _base(unit, subject, FAIL, "threshold_not_met", f"Rectangle {a:g} x {b:g} ft: " + "; ".join(why) + ".", **kw)


def _plan_complete(subject) -> bool:
    f = subject.get("bracing_plan_complete")
    return f is not None and f.usable and bool(f.value)


def _absence_unknown(unit, subject, msg, **kw):
    return _base(unit, subject, UNKNOWN, "required_element_not_found",
                 msg + " The model does not declare its bracing plan complete (Pset_ORI_BracingRectangle.BracingPlanComplete), so missing panels are not evidence of absence.", **kw)


def _side_panels(subject):
    ap = subject.get("assigned_panels")
    if ap is None:
        return None, "missing_information"
    if not ap.usable and ap.value is not None:
        return None, "unconfirmed_extraction"
    return list(ap.value or []), None


def practical_bracing_contributing_length(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _practical(unit, subject, "bracing_rectangle_side", "bracing rectangle sides")
    if r:
        return r
    facts, r = _need(unit, subject, ["required_bracing_length"])
    if r:
        return r
    panels, why = _side_panels(subject)
    if why:
        return _base(unit, subject, UNKNOWN, why, "Panels on this side are not available or not confirmed.", facts_used=_used(facts))
    ext_f = _req(unit, "exterior_panel_contribution")
    int_f = _req(unit, "interior_panel_contribution")
    dist = _req(unit, "max_interior_panel_assignment_distance")
    total, counted, excluded, unknown_loc = 0.0, [], [], []
    for p in panels:
        if p["location"] == "exterior":
            c = p["length_ft"] * ext_f["value"]
        elif p["location"] == "interior":
            if not _cmp(p["distance_from_side_ft"], dist["comparator"], dist["value"], EPS_FT):
                excluded.append(p["panel"])
                continue
            c = p["length_ft"] * int_f["value"]
        else:
            unknown_loc.append(p["panel"])
            continue
        total += c
        counted.append({"panel": p["panel"], "contributes_ft": round(c, 6)})
    need = float(facts["required_bracing_length"].value)
    kw = dict(measured={"contributing_ft": round(total, 6), "required_ft": need, "counted": counted, "excluded_beyond_4ft": excluded},
              required=[ext_f, int_f, dist], facts_used=dict(_used(facts), assigned_panels=subject.get("assigned_panels").as_record()))
    if total + EPS_FT < need and not unknown_loc and not _plan_complete(subject):
        return _absence_unknown(unit, subject, f"Contributing bracing {total:.2f} ft < required {need:.2f} ft.", **kw)
    if total + EPS_FT >= need:
        return _base(unit, subject, PASS, "threshold_met", f"Contributing bracing {total:.2f} ft >= required {need:.2f} ft (required length as declared by the applicant).", **kw)
    if unknown_loc:
        return _base(unit, subject, UNKNOWN, "missing_information", f"Contributing {total:.2f} ft < required {need:.2f} ft, but panels {unknown_loc} do not declare exterior or interior.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"Contributing bracing {total:.2f} ft < required {need:.2f} ft.", **kw)


def practical_bracing_corner_distance(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _practical(unit, subject, "bracing_rectangle_side", "bracing rectangle sides")
    if r:
        return r
    facts, r = _need(unit, subject, ["side_length"])
    if r:
        return r
    panels, why = _side_panels(subject)
    if why:
        return _base(unit, subject, UNKNOWN, why, "Panels on this side are not available or not confirmed.", facts_used=_used(facts))
    ext = [p for p in panels if p["location"] == "exterior"]
    req = _req(unit, "max_panel_edge_to_corner")
    L = float(facts["side_length"].value)
    if not ext and not _plan_complete(subject):
        return _absence_unknown(unit, subject, f"No exterior braced panel found on this {L:g} ft side.", required=[req], facts_used=_used(facts))
    if not ext:
        return _base(unit, subject, FAIL, "threshold_not_met", f"No exterior braced panel on this {L:g} ft side, so no panel edge is within {req['value']} ft of its corners.",
                     measured={"side_length_ft": L, "panels": 0}, required=[req], facts_used=_used(facts))
    d_start, d_end = max(0.0, ext[0]["start_ft"]), max(0.0, L - ext[-1]["end_ft"])
    worst = max(d_start, d_end)
    kw = dict(measured={"side_length_ft": L, "edge_to_start_corner_ft": d_start, "edge_to_end_corner_ft": d_end}, required=[req], facts_used=_used(facts))
    if not _cmp(worst, req["comparator"], req["value"], EPS_FT) and not _plan_complete(subject):
        return _absence_unknown(unit, subject, f"Nearest modelled panel edge is {worst:.2f} ft from a rectangle corner (> {req['value']} ft).", **kw)
    if not _cmp(worst, req["comparator"], req["value"], EPS_FT):
        return _base(unit, subject, FAIL, "threshold_not_met", f"Nearest panel edge is {worst:.2f} ft from a rectangle corner (> {req['value']} ft).", **kw)
    bm = subject.get("building_matches_rectangle")
    if bm is None or not bm.usable or not bm.value:
        return _base(unit, subject, UNKNOWN, "missing_information" if (bm is None or not bm.usable) else "exception_requires_reviewer",
                     f"Panel edges are within {req['value']} ft of the rectangle corners, but building corners inside the rectangle are not evaluated.", **kw)
    return _base(unit, subject, PASS, "threshold_met", f"Panel edges within {req['value']} ft of both corners (worst {worst:.2f} ft).", **kw)


def practical_bracing_panel_gap(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _practical(unit, subject, "bracing_rectangle_side", "bracing rectangle sides")
    if r:
        return r
    panels, why = _side_panels(subject)
    if why:
        return _base(unit, subject, UNKNOWN, why, "Panels on this side are not available or not confirmed.")
    req = _req(unit, "max_panel_edge_gap")
    ext = [p for p in panels if p["location"] == "exterior"]
    if len(ext) < 2:
        return _base(unit, subject, NA, "fewer_than_two_panels", "Fewer than two exterior panels on this side; the corner-distance unit governs.", required=[req])
    gaps = [max(0.0, b["start_ft"] - a["end_ft"]) for a, b in zip(ext, ext[1:])]
    worst = max(gaps)
    kw = dict(measured={"gaps_ft": gaps, "worst_ft": worst}, required=[req])
    if _cmp(worst, req["comparator"], req["value"], EPS_FT):
        return _base(unit, subject, PASS, "threshold_met", f"Largest gap between adjacent exterior panels {worst:.2f} ft <= {req['value']} ft.", **kw)
    with_int = sorted(panels, key=lambda p: p["start_ft"])
    gi = [max(0.0, b["start_ft"] - a["end_ft"]) for a, b in zip(with_int, with_int[1:])] if len(with_int) > 1 else [worst]
    if len(with_int) > len(ext) and max(gi) <= req["value"] + EPS_FT:
        return _base(unit, subject, UNKNOWN, "exception_requires_reviewer", f"Exterior panels leave a {worst:.2f} ft gap; interior panels near this side would close it. Reviewer to decide.", **kw)
    if not _plan_complete(subject):
        return _absence_unknown(unit, subject, f"Modelled exterior panels leave a {worst:.2f} ft gap.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"Gap of {worst:.2f} ft between adjacent panel edges exceeds {req['value']} ft.", **kw)


RULES = {
    "framing_stud_spacing_max": framing_stud_spacing_max,
    "framing_bearing_stud_height_max": framing_bearing_stud_height_max,
    "framing_top_plate_count_min": framing_top_plate_count_min,
    "framing_top_plate_splice_offset_min": framing_top_plate_splice_offset_min,
    "framing_bored_hole_ratio_max": framing_bored_hole_ratio_max,
    "framing_notch_ratio_max": framing_notch_ratio_max,
    "practical_bracing_sheathing": practical_bracing_sheathing,
    "practical_bracing_exterior_panel_length": practical_bracing_exterior_panel_length,
    "practical_bracing_interior_panel_length": practical_bracing_interior_panel_length,
    "practical_bracing_rectangle_limits": practical_bracing_rectangle_limits,
    "practical_bracing_contributing_length": practical_bracing_contributing_length,
    "practical_bracing_corner_distance": practical_bracing_corner_distance,
    "practical_bracing_panel_gap": practical_bracing_panel_gap,
}
SUBJECT_KINDS = {k: ("framed_wall" if k.startswith("framing_") else "bracing_rectangle" if k == "practical_bracing_rectangle_limits"
                     else "bracing_rectangle_side" if k in ("practical_bracing_contributing_length", "practical_bracing_corner_distance", "practical_bracing_panel_gap")
                     else "braced_wall_panel") for k in RULES}
