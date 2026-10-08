# SPDX-License-Identifier: Apache-2.0
import pytest

from ori_verify import rules, units
from ori_verify.facts import Fact, Subject

VA = {u.function + (":" + (u.unit["source_section"].get("subsection_part") or "")): u for u in units.implemented_units()}
BASE = {u.function + (":" + (u.unit["source_section"].get("subsection_part") or "")): u for u in units.implemented_units(None)}


def S(kind, **facts):
    s = Subject(kind=kind, subject_id=f"test:{kind}", label=kind)
    for k, v in facts.items():
        s.facts[k] = v if isinstance(v, Fact) else Fact(v, "applicant_declared", {"artifact_id": "x", "page": 1})
    return s


def run(key, subject, table=VA):
    u = table[key]
    return rules.RULES[u.function](subject, u)


@pytest.mark.parametrize("value,state", [(8.25, "pass"), (8.26, "fail"), (7.0, "pass")])
def test_riser_boundary_va(value, state):
    assert run("riser_height_max:maximum riser", S("stair_flight", riser_heights=[7.5, value])).state == state


def test_same_stair_passes_va_but_fails_irc_base():
    stair = S("stair_flight", riser_heights=[8.0] * 13, tread_depths=[9.5] * 12)
    assert run("riser_height_max:maximum riser", stair).state == "pass"
    assert run("tread_depth_min:minimum tread", stair).state == "pass"
    assert run("riser_height_max:maximum riser", stair, BASE).state == "fail"
    assert run("tread_depth_min:minimum tread", stair, BASE).state == "fail"


def test_uniformity():
    assert run("riser_uniformity:riser uniformity", S("stair_flight", riser_heights=[7.5, 7.875])).state == "pass"
    assert run("riser_uniformity:riser uniformity", S("stair_flight", riser_heights=[7.5, 7.9])).state == "fail"
    assert run("tread_uniformity:tread uniformity", S("stair_flight", tread_depths=[10.0])).state == "not_applicable"


KINDS = {"riser_height_max": "stair_flight", "riser_uniformity": "stair_flight", "tread_depth_min": "stair_flight",
         "tread_uniformity": "stair_flight", "stair_headroom_min": "stair_flight", "ceiling_height_min": "space",
         "room_area_min": "space", "eero_net_clear_area": "eero", "eero_net_clear_height": "eero",
         "eero_net_clear_width": "eero", "eero_sill_height_max": "eero", "guard_required": "walking_surface",
         "guard_height_min": "guard"}


@pytest.mark.parametrize("key", sorted(VA))
def test_missing_information_is_unknown_never_fail(key):
    u = VA[key]
    r = rules.RULES[u.function](S(KINDS[u.function]), u)
    assert r.state == "unknown", (key, r.state, r.message)
    assert r.reason_code in rules.MISSING_INFORMATION_REASONS
    assert r.core_outcome == "indeterminate"


@pytest.mark.parametrize("origin", ["vector_extracted_unconfirmed", "ai_extracted_unverified"])
def test_unconfirmed_extraction_is_unknown_even_when_it_would_fail(origin):
    bad = Fact([9.0], origin, {"artifact_id": "x", "page": 2})
    r = run("riser_height_max:maximum riser", S("stair_flight", riser_heights=bad))
    assert r.state == "unknown" and r.reason_code == "unconfirmed_extraction"


def test_fail_with_missing_information_reason_is_impossible():
    with pytest.raises(AssertionError):
        rules.Result("u", "R1", None, S("space"), "fail", "missing_information", "x")


@pytest.mark.parametrize("area_facts,grade,state", [
    ({"net_clear_area": 6.0}, None, "pass"),
    ({"net_clear_area": 5.2}, None, "unknown"),
    ({"net_clear_area": 5.2}, True, "pass"),
    ({"net_clear_area": 5.2}, False, "fail"),
    ({"net_clear_area": 4.9}, None, "fail"),
    ({"net_clear_height": 41.04, "net_clear_width": 20.0}, None, "pass"),
])
def test_eero_area_logic(area_facts, grade, state):
    facts = dict(area_facts)
    if grade is not None:
        facts["grade_floor_or_below_grade"] = grade
    assert run("eero_net_clear_area:net clear area", S("eero", **facts)).state == state


def test_eero_sill_frame_bottom_logic():
    assert run("eero_sill_height_max:", S("eero", frame_bottom_height=46.0)).state == "fail"
    assert run("eero_sill_height_max:", S("eero", frame_bottom_height=40.0)).state == "unknown"
    assert run("eero_sill_height_max:", S("eero", sill_height=44.0)).state == "pass"


def test_ceiling_height_exceptions_go_to_reviewer():
    k = "ceiling_height_min:habitable"
    assert run(k, S("space", space_use="habitable", ceiling_height=80.0, sloped_ceiling=True)).reason_code == "exception_requires_reviewer"
    assert run(k, S("space", space_use="habitable", ceiling_height=80.0)).state == "unknown"
    assert run(k, S("space", space_use="habitable", ceiling_height=80.0, sloped_ceiling=False)).state == "fail"
    assert run(k, S("space", space_use="bathroom", ceiling_height=80.0)).state == "not_applicable"
    assert run("ceiling_height_min:bath-toilet-laundry", S("space", space_use="laundry", ceiling_height=80.0)).state == "pass"


def test_room_area_kitchen_exception():
    assert run("room_area_min:", S("space", space_use="kitchen", floor_area=40.0)).state == "not_applicable"
    assert run("room_area_min:", S("space", space_use="habitable", floor_area=69.9)).state == "fail"


def test_guard_logic():
    assert run("guard_required:", S("walking_surface", drop_height=30.0)).state == "not_applicable"
    assert run("guard_required:", S("walking_surface", drop_height=31.0)).state == "unknown"
    assert run("guard_required:", S("walking_surface", drop_height=31.0, guard_present=False)).state == "fail"
    assert run("guard_required:", S("walking_surface", drop_height=31.0, guard_present=True)).state == "pass"
    assert run("guard_height_min:general", S("guard", guard_height=35.0)).state == "unknown"
    assert run("guard_height_min:general", S("guard", guard_height=33.0)).state == "fail"
    assert run("guard_height_min:general", S("guard", guard_height=34.0, on_stair_open_side=True)).state == "pass"
    assert run("guard_height_min:general", S("guard", guard_height=35.0, on_stair_open_side=False)).state == "fail"


@pytest.mark.parametrize("key,subject", [
    ("ceiling_height_min:habitable", lambda f: S("space", space_use="habitable", ceiling_height=80.0, sloped_ceiling=f)),
    ("guard_height_min:general", lambda f: S("guard", guard_height=35.0, on_stair_open_side=f)),
    ("eero_net_clear_area:net clear area", lambda f: S("eero", net_clear_area=5.2, grade_floor_or_below_grade=f)),
])
def test_condition_fact_unknown_reason_is_consistent(key, subject):
    """A condition fact that is absent gives missing_information; one that is present but
    unconfirmed gives unconfirmed_extraction (same rule in all three functions and in ORI-CL)."""
    assert run(key, subject(None)).reason_code == "missing_information"
    assert run(key, subject(Fact(True, "vector_extracted_unconfirmed", {"artifact_id": "x", "page": 2}))).reason_code == "unconfirmed_extraction"
