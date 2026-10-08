# SPDX-License-Identifier: Apache-2.0
from ori_verify import rules, units


def _unit(section, part, jur=units.VA):
    col = units.load_collection()
    for u in units.all_units(col):
        s = u["source_section"]
        if s["section"] == section and s.get("subsection_part") == part:
            return units.resolve(u, jur)
    raise KeyError(section)


def test_va_layer_overrides_riser_and_tread():
    assert _unit("R311.7.5.1", "maximum riser").param("max_riser_height")["quantity"]["value"] == 8.25
    assert _unit("R311.7.5.1", "maximum riser", None).param("max_riser_height")["quantity"]["value"] == 7.75
    assert _unit("R311.7.5.2", "minimum tread").param("min_tread_depth")["quantity"]["value"] == 9
    assert _unit("R311.7.5.2", "minimum tread", None).param("min_tread_depth")["quantity"]["value"] == 10


def test_va_values_are_primary_sourced_and_base_values_are_labeled():
    va = _unit("R311.7.5.1", "maximum riser").param("max_riser_height")
    assert va["value_status"] == "sourced_primary" and va["source"] == "source:va:13vac5-63-210"
    base = _unit("R311.7.5.1", "maximum riser", None).param("max_riser_height")
    assert base["value_status"] == "sourced_secondary"
    head = _unit("R311.7.2", None, None).param("min_headroom")
    assert head["value_status"] == "inferred_unamended"


def test_va_deletion_makes_unit_not_applicable():
    assert _unit("R310.2.2", None).deleted is True
    assert _unit("R310.2.2", None, None).deleted is False
    assert _unit("R302.13", None).deleted is True


def test_every_implemented_unit_has_a_rule_function():
    eff = units.implemented_units()
    assert len(eff) == 14  # R305.1 has two units (habitable; bath-toilet-laundry)
    for u in eff:
        assert u.function in rules.RULES, u.id
        assert u.unit["check_class"] == "geometric_deterministic"


def test_no_judgment_unit_is_automated():
    for u in units.all_units(units.load_collection()):
        if u["check_class"] == "judgment":
            assert u["evaluator"]["kind"] in ("human_reviewer", "human_reviewer_with_machine_assist")
