# SPDX-License-Identifier: Apache-2.0
"""Deterministic rule functions for implemented Chapter 3 rule units.

Contract for every function: ``fn(subject, unit) -> Result``.

* Thresholds come from ``unit`` (an EffectiveUnit resolved from rule-unit
  data with the jurisdiction layer applied), never from constants here.
* Missing, unusable or unconfirmed facts give ``unknown`` with a reason code.
  They never give ``fail``. A ``fail`` needs usable evidence that the
  requirement is not met whatever the missing facts turn out to be.
* Results are reviewer evidence, not approval.

US customary values govern. Comparisons use a small tolerance (EPS_IN) that
absorbs floating-point error from mm/inch conversion only. It is not a
construction tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .facts import Fact, Subject
from .units import EffectiveUnit

EPS_IN = 1e-6
EPS_FT2 = 1e-6

PASS, FAIL, UNKNOWN, NA = "pass", "fail", "unknown", "not_applicable"
CORE_OUTCOME = {PASS: "pass", FAIL: "fail", UNKNOWN: "indeterminate", NA: "not-applicable"}

# Reason codes. Codes in MISSING_INFORMATION_REASONS may never pair with fail.
MISSING_INFORMATION_REASONS = frozenset(
    {
        "missing_information",
        "unconfirmed_extraction",
        "required_element_not_found",
        "exception_requires_reviewer",
        "geometry_not_measurable",
        "parameter_missing",
    }
)


@dataclass
class Result:
    unit_id: str
    section: str
    part: str | None
    subject: Subject
    state: str
    reason_code: str
    message: str
    measured: dict[str, Any] = field(default_factory=dict)
    required: list[dict[str, Any]] = field(default_factory=list)
    facts_used: dict[str, Any] = field(default_factory=dict)
    jurisdiction: str = ""
    layers_applied: list[str] = field(default_factory=list)

    @property
    def core_outcome(self) -> str:
        return CORE_OUTCOME[self.state]

    def __post_init__(self):
        if self.state == FAIL and self.reason_code in MISSING_INFORMATION_REASONS:
            raise AssertionError("missing information must never produce fail")


def _cmp(measured: float, comparator: str, limit: float, eps: float) -> bool:
    if comparator == "<=":
        return measured <= limit + eps
    if comparator == "<":
        return measured < limit - eps
    if comparator == ">=":
        return measured >= limit - eps
    if comparator == ">":
        return measured > limit + eps
    if comparator == "==":
        return abs(measured - limit) <= eps
    raise ValueError(f"unsupported comparator {comparator}")


def _req(unit: EffectiveUnit, name: str) -> dict[str, Any]:
    p = unit.param(name)
    if p is None:
        raise KeyError(name)
    return {
        "parameter": name,
        "comparator": p["comparator"],
        "value": p["quantity"]["value"],
        "unit": p["quantity"]["unit"],
        "layer": unit.param_layer.get(name),
        "value_status": p["value_status"],
        "source": p["source"],
        **({"applies_when": p["applies_when"]} if p.get("applies_when") else {}),
    }


def _base(unit: EffectiveUnit, subject: Subject, state: str, reason: str, message: str, **kw) -> Result:
    sec = unit.unit["source_section"]
    return Result(
        unit_id=unit.id,
        section=sec["section"],
        part=sec.get("subsection_part"),
        subject=subject,
        state=state,
        reason_code=reason,
        message=message,
        jurisdiction=unit.jurisdiction,
        layers_applied=list(unit.layers_applied),
        **kw,
    )


def _need(unit: EffectiveUnit, subject: Subject, names: list[str]) -> tuple[dict[str, Fact], Result | None]:
    """Return usable facts, or an unknown Result naming what is missing/unconfirmed."""
    facts: dict[str, Fact] = {}
    missing, unconfirmed = [], []
    for n in names:
        f = subject.get(n)
        if f is None or f.value is None or (isinstance(f.value, list) and not f.value):
            missing.append(n)
        elif not f.usable:
            unconfirmed.append(n)
        else:
            facts[n] = f
    used = {n: subject.get(n).as_record() for n in names if subject.get(n) is not None}
    if unconfirmed:
        return facts, _base(unit, subject, UNKNOWN, "unconfirmed_extraction",
                            f"Values for {', '.join(unconfirmed)} are extracted but not confirmed by applicant or reviewer; they are not used for pass/fail.",
                            facts_used=used)
    if missing:
        return facts, _base(unit, subject, UNKNOWN, "missing_information",
                            f"Required information not available: {', '.join(missing)}.", facts_used=used)
    return facts, None


def _condition_unknown_reason(f: Fact | None) -> str:
    """Reason code when a condition fact cannot be used: absent vs. present but unconfirmed."""
    return "missing_information" if (f is None or f.value is None) else "unconfirmed_extraction"


def _deleted_or_unparam(unit: EffectiveUnit, subject: Subject, names: list[str]) -> Result | None:
    if unit.deleted:
        return _base(unit, subject, NA, "deleted_by_jurisdiction", "The jurisdiction layer deletes this provision.")
    for n in names:
        if unit.param(n) is None:
            return _base(unit, subject, UNKNOWN, "parameter_missing", f"Rule-unit parameter {n} is not defined for this jurisdiction.")
    return None


def _list_rule(subject: Subject, unit: EffectiveUnit, fact: str, param: str, label: str) -> Result:
    if subject.kind != "stair_flight":
        return _base(unit, subject, NA, "subject_kind_not_applicable", "Applies to stair flights only.")
    r = _deleted_or_unparam(unit, subject, [param])
    if r:
        return r
    facts, r = _need(unit, subject, [fact])
    if r:
        return r
    values = [float(v) for v in facts[fact].value]
    req = _req(unit, param)
    bad = [i for i, v in enumerate(values) if not _cmp(v, req["comparator"], req["value"], EPS_IN)]
    worst = max(values) if req["comparator"] in ("<=", "<") else min(values)
    kw = dict(measured={fact: values, "governing": worst, "unit": "in", "offending_indices": bad},
              required=[req], facts_used={fact: facts[fact].as_record()})
    if bad:
        return _base(unit, subject, FAIL, "threshold_not_met",
                     f"{label}: {len(bad)} of {len(values)} values outside {req['comparator']} {req['value']} in (governing {worst:.3f} in).", **kw)
    return _base(unit, subject, PASS, "threshold_met",
                 f"{label}: all {len(values)} values {req['comparator']} {req['value']} in (governing {worst:.3f} in).", **kw)


def _variation_rule(subject: Subject, unit: EffectiveUnit, fact: str, param: str, label: str) -> Result:
    if subject.kind != "stair_flight":
        return _base(unit, subject, NA, "subject_kind_not_applicable", "Applies to stair flights only.")
    r = _deleted_or_unparam(unit, subject, [param])
    if r:
        return r
    facts, r = _need(unit, subject, [fact])
    if r:
        return r
    values = [float(v) for v in facts[fact].value]
    req = _req(unit, param)
    if len(values) < 2:
        return _base(unit, subject, NA, "single_value", f"{label}: fewer than two values; variation does not arise.",
                     measured={fact: values}, required=[req])
    variation = max(values) - min(values)
    kw = dict(measured={fact: values, "variation": variation, "unit": "in"}, required=[req], facts_used={fact: facts[fact].as_record()})
    if _cmp(variation, req["comparator"], req["value"], EPS_IN):
        return _base(unit, subject, PASS, "threshold_met", f"{label}: variation {variation:.3f} in within {req['value']} in.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"{label}: variation {variation:.3f} in exceeds {req['value']} in.", **kw)


def riser_height_max(subject: Subject, unit: EffectiveUnit) -> Result:
    return _list_rule(subject, unit, "riser_heights", "max_riser_height", "Riser height")


def riser_uniformity(subject: Subject, unit: EffectiveUnit) -> Result:
    return _variation_rule(subject, unit, "riser_heights", "max_riser_variation", "Riser uniformity")


def tread_depth_min(subject: Subject, unit: EffectiveUnit) -> Result:
    return _list_rule(subject, unit, "tread_depths", "min_tread_depth", "Tread depth")


def tread_uniformity(subject: Subject, unit: EffectiveUnit) -> Result:
    return _variation_rule(subject, unit, "tread_depths", "max_tread_variation", "Tread uniformity")


def stair_headroom_min(subject: Subject, unit: EffectiveUnit) -> Result:
    if subject.kind != "stair_flight":
        return _base(unit, subject, NA, "subject_kind_not_applicable", "Applies to stair flights only.")
    r = _deleted_or_unparam(unit, subject, ["min_headroom"])
    if r:
        return r
    f = subject.get("headroom_clearances")
    if f is not None and f.usable and f.value == []:
        return _base(unit, subject, UNKNOWN, "required_element_not_found",
                     "No overhead element found above the stair; headroom cannot be measured from the model.",
                     facts_used={"headroom_clearances": f.as_record()})
    facts, r = _need(unit, subject, ["headroom_clearances"])
    if r:
        return r
    values = [float(v) for v in facts["headroom_clearances"].value]
    req = _req(unit, "min_headroom")
    worst = min(values)
    kw = dict(measured={"headroom_clearances": values, "governing": worst, "unit": "in"}, required=[req],
              facts_used={"headroom_clearances": facts["headroom_clearances"].as_record()})
    if _cmp(worst, req["comparator"], req["value"], EPS_IN):
        return _base(unit, subject, PASS, "threshold_met", f"Headroom: minimum {worst:.2f} in >= {req['value']} in.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"Headroom: minimum {worst:.2f} in < {req['value']} in.", **kw)


HABITABLE_CEILING_USES = {"habitable", "kitchen", "hallway"}
REDUCED_CEILING_USES = {"bathroom", "toilet", "laundry"}
ALL_USES = HABITABLE_CEILING_USES | REDUCED_CEILING_USES | {"other"}


def ceiling_height_min(subject: Subject, unit: EffectiveUnit) -> Result:
    if subject.kind != "space":
        return _base(unit, subject, NA, "subject_kind_not_applicable", "Applies to spaces only.")
    r = _deleted_or_unparam(unit, subject, ["min_ceiling_height"])
    if r:
        return r
    part = unit.unit["source_section"].get("subsection_part")
    applies_to = HABITABLE_CEILING_USES if part == "habitable" else REDUCED_CEILING_USES
    facts, r = _need(unit, subject, ["space_use"])
    if r:
        return r
    use = facts["space_use"].value
    if use not in ALL_USES:
        return _base(unit, subject, UNKNOWN, "missing_information", f"Space use {use!r} is not an ORI use category.")
    if use not in applies_to:
        return _base(unit, subject, NA, "use_not_covered", f"Space use {use!r} is not covered by this unit.")
    facts2, r = _need(unit, subject, ["ceiling_height"])
    if r:
        return r
    h = float(facts2["ceiling_height"].value)
    req = _req(unit, "min_ceiling_height")
    kw = dict(measured={"ceiling_height": h, "unit": "in", "space_use": use}, required=[req],
              facts_used={"ceiling_height": facts2["ceiling_height"].as_record(), "space_use": facts["space_use"].as_record()})
    if _cmp(h, req["comparator"], req["value"], EPS_IN):
        return _base(unit, subject, PASS, "threshold_met", f"Ceiling height {h:.2f} in >= {req['value']} in.", **kw)
    sloped = subject.get("sloped_ceiling")
    if sloped is None or not sloped.usable:
        return _base(unit, subject, UNKNOWN, _condition_unknown_reason(sloped),
                     f"Ceiling height {h:.2f} in is below {req['value']} in, but whether the sloped-ceiling or beam exceptions apply is not declared.", **kw)
    if sloped.value:
        return _base(unit, subject, UNKNOWN, "exception_requires_reviewer",
                     f"Ceiling height {h:.2f} in is below {req['value']} in on a sloped ceiling; the R305.1 sloped-ceiling exception needs area-weighted review.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"Ceiling height {h:.2f} in < {req['value']} in (flat ceiling declared).", **kw)


def room_area_min(subject: Subject, unit: EffectiveUnit) -> Result:
    if subject.kind != "space":
        return _base(unit, subject, NA, "subject_kind_not_applicable", "Applies to spaces only.")
    r = _deleted_or_unparam(unit, subject, ["min_habitable_room_area"])
    if r:
        return r
    facts, r = _need(unit, subject, ["space_use"])
    if r:
        return r
    use = facts["space_use"].value
    if use == "kitchen":
        return _base(unit, subject, NA, "exception_applies", "Kitchens are excepted from the minimum room area.")
    if use not in ALL_USES:
        return _base(unit, subject, UNKNOWN, "missing_information", f"Space use {use!r} is not an ORI use category.")
    if use != "habitable":
        return _base(unit, subject, NA, "use_not_covered", f"Space use {use!r} is not a habitable room.")
    facts2, r = _need(unit, subject, ["floor_area"])
    if r:
        return r
    a = float(facts2["floor_area"].value)
    req = _req(unit, "min_habitable_room_area")
    kw = dict(measured={"floor_area": a, "unit": "ft2"}, required=[req], facts_used={"floor_area": facts2["floor_area"].as_record()})
    if _cmp(a, req["comparator"], req["value"], EPS_FT2):
        return _base(unit, subject, PASS, "threshold_met", f"Room area {a:.2f} ft2 >= {req['value']} ft2.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"Room area {a:.2f} ft2 < {req['value']} ft2.", **kw)


def _eero_guard(subject: Subject, unit: EffectiveUnit) -> Result | None:
    if subject.kind != "eero":
        return _base(unit, subject, NA, "subject_kind_not_applicable", "Applies to emergency escape and rescue openings only.")
    return None


def eero_net_clear_area(subject: Subject, unit: EffectiveUnit) -> Result:
    r = _eero_guard(subject, unit) or _deleted_or_unparam(unit, subject, ["min_net_clear_area", "min_net_clear_area_grade_floor"])
    if r:
        return r
    std, grade = _req(unit, "min_net_clear_area"), _req(unit, "min_net_clear_area_grade_floor")
    area_f = subject.get("net_clear_area")
    note = None
    if area_f is not None and area_f.value is not None:
        facts, r = _need(unit, subject, ["net_clear_area"])
        if r:
            return r
        area = float(facts["net_clear_area"].value)
        used = {"net_clear_area": facts["net_clear_area"].as_record()}
    else:
        facts, r = _need(unit, subject, ["net_clear_height", "net_clear_width"])
        if r:
            return r
        area = float(facts["net_clear_height"].value) * float(facts["net_clear_width"].value) / 144.0
        note = "Area computed as net clear height x net clear width (rectangular clear opening assumed)."
        used = {k: facts[k].as_record() for k in ("net_clear_height", "net_clear_width")}
    measured = {"net_clear_area": round(area, 6), "unit": "ft2", **({"note": note} if note else {})}
    kw = dict(measured=measured, required=[std, grade], facts_used=used)
    if _cmp(area, ">=", std["value"], EPS_FT2):
        return _base(unit, subject, PASS, "threshold_met", f"Net clear area {area:.2f} ft2 >= {std['value']} ft2.", **kw)
    if not _cmp(area, ">=", grade["value"], EPS_FT2):
        return _base(unit, subject, FAIL, "threshold_not_met", f"Net clear area {area:.2f} ft2 is below both {std['value']} and {grade['value']} ft2.", **kw)
    gf = subject.get("grade_floor_or_below_grade")
    if gf is None or not gf.usable:
        kw["facts_used"]["grade_floor_or_below_grade"] = gf.as_record() if gf else None
        return _base(unit, subject, UNKNOWN, _condition_unknown_reason(gf),
                     f"Net clear area {area:.2f} ft2 meets only the grade-floor minimum; grade-floor or below-grade status is not established.", **kw)
    kw["facts_used"]["grade_floor_or_below_grade"] = gf.as_record()
    if gf.value:
        return _base(unit, subject, PASS, "threshold_met_exception", f"Net clear area {area:.2f} ft2 >= {grade['value']} ft2 (grade-floor or below-grade opening).", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"Net clear area {area:.2f} ft2 < {std['value']} ft2 and the opening is not at grade floor or below grade.", **kw)


def _eero_dim(subject: Subject, unit: EffectiveUnit, fact: str, param: str, label: str) -> Result:
    r = _eero_guard(subject, unit) or _deleted_or_unparam(unit, subject, [param])
    if r:
        return r
    facts, r = _need(unit, subject, [fact])
    if r:
        return r
    v = float(facts[fact].value)
    req = _req(unit, param)
    kw = dict(measured={fact: v, "unit": "in"}, required=[req], facts_used={fact: facts[fact].as_record()})
    if _cmp(v, req["comparator"], req["value"], EPS_IN):
        return _base(unit, subject, PASS, "threshold_met", f"{label} {v:.2f} in {req['comparator']} {req['value']} in.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"{label} {v:.2f} in does not satisfy {req['comparator']} {req['value']} in.", **kw)


def eero_net_clear_height(subject: Subject, unit: EffectiveUnit) -> Result:
    return _eero_dim(subject, unit, "net_clear_height", "min_net_clear_height", "Net clear height")


def eero_net_clear_width(subject: Subject, unit: EffectiveUnit) -> Result:
    return _eero_dim(subject, unit, "net_clear_width", "min_net_clear_width", "Net clear width")


def eero_sill_height_max(subject: Subject, unit: EffectiveUnit) -> Result:
    """Sill = bottom of the clear opening above the floor.

    If only the frame bottom is known (clear-opening offset not declared), a
    frame bottom already above the maximum is a fail, because the clear opening
    can only sit higher. A frame bottom at or below the maximum is unknown.
    """
    r = _eero_guard(subject, unit) or _deleted_or_unparam(unit, subject, ["max_sill_height"])
    if r:
        return r
    req = _req(unit, "max_sill_height")
    sill = subject.get("sill_height")
    if sill is not None and sill.value is not None:
        return _eero_dim(subject, unit, "sill_height", "max_sill_height", "Sill height")
    facts, r = _need(unit, subject, ["frame_bottom_height"])
    if r:
        return r
    fb = float(facts["frame_bottom_height"].value)
    kw = dict(measured={"frame_bottom_height": fb, "unit": "in"}, required=[req], facts_used={"frame_bottom_height": facts["frame_bottom_height"].as_record()})
    if not _cmp(fb, req["comparator"], req["value"], EPS_IN):
        return _base(unit, subject, FAIL, "threshold_not_met", f"Frame bottom {fb:.2f} in is already above {req['value']} in; the clear opening cannot be lower.", **kw)
    return _base(unit, subject, UNKNOWN, "missing_information",
                 f"Frame bottom {fb:.2f} in is within {req['value']} in, but the offset from frame bottom to clear-opening bottom is not declared.", **kw)


def guard_required(subject: Subject, unit: EffectiveUnit) -> Result:
    if subject.kind != "walking_surface":
        return _base(unit, subject, NA, "subject_kind_not_applicable", "Applies to open-sided walking surfaces only.")
    r = _deleted_or_unparam(unit, subject, ["guard_trigger_drop"])
    if r:
        return r
    facts, r = _need(unit, subject, ["drop_height"])
    if r:
        return r
    drop = float(facts["drop_height"].value)
    req = _req(unit, "guard_trigger_drop")
    reqs = [req] + ([_req(unit, "guard_trigger_horizontal_band")] if unit.param("guard_trigger_horizontal_band") else [])
    kw = dict(measured={"drop_height": drop, "unit": "in"}, required=reqs, facts_used={"drop_height": facts["drop_height"].as_record()})
    if not _cmp(drop, req["comparator"], req["value"], EPS_IN):
        return _base(unit, subject, NA, "trigger_not_met", f"Drop {drop:.2f} in does not exceed {req['value']} in; no guard required by this unit.", **kw)
    gp = subject.get("guard_present")
    if gp is None or gp.value is None or not gp.usable:
        return _base(unit, subject, UNKNOWN, "required_element_not_found",
                     f"Drop {drop:.2f} in exceeds {req['value']} in, so a guard is required; no guard could be identified. Absence from a model is not treated as evidence of absence.", **kw)
    kw["facts_used"]["guard_present"] = gp.as_record()
    if gp.value:
        return _base(unit, subject, PASS, "requirement_met", f"Drop {drop:.2f} in exceeds {req['value']} in and a guard is present (height checked by R312.1.2).", **kw)
    return _base(unit, subject, FAIL, "requirement_not_met", f"Drop {drop:.2f} in exceeds {req['value']} in and the evidence declares no guard.", **kw)


def guard_height_min(subject: Subject, unit: EffectiveUnit) -> Result:
    if subject.kind != "guard":
        return _base(unit, subject, NA, "subject_kind_not_applicable", "Applies to guards only.")
    r = _deleted_or_unparam(unit, subject, ["min_guard_height"])
    if r:
        return r
    facts, r = _need(unit, subject, ["guard_height"])
    if r:
        return r
    h = float(facts["guard_height"].value)
    stair = subject.get("on_stair_open_side")
    general = _req(unit, "min_guard_height")
    param = general
    if stair is not None and stair.usable and stair.value and unit.param("min_guard_height_stair_open_side"):
        param = _req(unit, "min_guard_height_stair_open_side")
    kw = dict(measured={"guard_height": h, "unit": "in"}, required=[param], facts_used={"guard_height": facts["guard_height"].as_record()})
    if _cmp(h, ">=", param["value"], EPS_IN):
        return _base(unit, subject, PASS, "threshold_met", f"Guard height {h:.2f} in >= {param['value']} in.", **kw)
    if param is general and (stair is None or not stair.usable) and unit.param("min_guard_height_stair_open_side"):
        low = _req(unit, "min_guard_height_stair_open_side")
        if _cmp(h, ">=", low["value"], EPS_IN):
            return _base(unit, subject, UNKNOWN, _condition_unknown_reason(stair),
                         f"Guard height {h:.2f} in meets the stair open-side minimum but not the general minimum; whether it is on a stair open side is not established.", **kw)
    return _base(unit, subject, FAIL, "threshold_not_met", f"Guard height {h:.2f} in < {param['value']} in.", **kw)


RULES: dict[str, Callable[[Subject, EffectiveUnit], Result]] = {
    "riser_height_max": riser_height_max,
    "riser_uniformity": riser_uniformity,
    "tread_depth_min": tread_depth_min,
    "tread_uniformity": tread_uniformity,
    "stair_headroom_min": stair_headroom_min,
    "ceiling_height_min": ceiling_height_min,
    "room_area_min": room_area_min,
    "eero_net_clear_area": eero_net_clear_area,
    "eero_net_clear_height": eero_net_clear_height,
    "eero_net_clear_width": eero_net_clear_width,
    "eero_sill_height_max": eero_sill_height_max,
    "guard_required": guard_required,
    "guard_height_min": guard_height_min,
}

SUBJECT_KINDS = {
    "riser_height_max": "stair_flight", "riser_uniformity": "stair_flight", "tread_depth_min": "stair_flight",
    "tread_uniformity": "stair_flight", "stair_headroom_min": "stair_flight", "ceiling_height_min": "space",
    "room_area_min": "space", "eero_net_clear_area": "eero", "eero_net_clear_height": "eero",
    "eero_net_clear_width": "eero", "eero_sill_height_max": "eero", "guard_required": "walking_surface",
    "guard_height_min": "guard",
}


def evaluate(subjects: list[Subject], units: list[EffectiveUnit]) -> list[Result]:
    """Run each implemented unit against each subject of the matching kind."""
    results: list[Result] = []
    for unit in units:
        fn_name = unit.function
        if fn_name not in RULES:
            continue
        kind = SUBJECT_KINDS[fn_name]
        for s in subjects:
            if s.kind == kind:
                results.append(RULES[fn_name](s, unit))
    return results
