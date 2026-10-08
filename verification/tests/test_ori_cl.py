# SPDX-License-Identifier: Apache-2.0
"""ORI-CL 0.1: vocabulary provenance, grammar, compiler checks, and equivalence with the
hand-written Chapter 3 checks (same state and reason code on every subject)."""
import copy
import itertools
import json
import re
import sys
from pathlib import Path

import pytest

from ori_cl import compiler, corpus_stats, evaluator, ifc_bind, syntax, vocab
from ori_cl.__main__ import compiled_json
from ori_verify import declared as dec
from ori_verify import ifc_extract, rules, units
from ori_verify.facts import Fact, Subject

REPO = Path(__file__).resolve().parents[2]
ORICL = REPO / "rules" / "irc2021" / "ch03" / "ori-cl"
GEOMETRIC = ORICL / "ch03-geometric.oricl"
SAMPLES = ORICL / "ch03-samples.oricl"
VA, BASE = units.VA, None
sys.path.insert(0, str(REPO / "conformance"))
import semantic  # noqa: E402

GEO = compiler.compile_text(GEOMETRIC.read_text())
SAMP = compiler.compile_text(SAMPLES.read_text())
COLLECTION = {u["id"]: u for u in units.all_units(units.load_collection())}
V = vocab.load()
HEADER = GEOMETRIC.read_text().split("\nrule ", 1)[0]


def S(kind, **facts):
    s = Subject(kind=kind, subject_id=f"test:{kind}", label=kind)
    for k, v in facts.items():
        if v is not None:
            s.facts[k] = v if isinstance(v, Fact) else Fact(v, "applicant_declared", {"artifact_id": "x", "page": 1})
    return s


def unconf(v):
    return Fact(v, "vector_extracted_unconfirmed", {"artifact_id": "x", "page": 2})


# ---- vocabulary ------------------------------------------------------------------------------
def test_vocabulary_provenance_is_complete():
    assert vocab.provenance_errors(V.data) == []


def test_parser_keywords_equal_vocabulary_keywords():
    assert syntax.PARSER_KEYWORDS == V.keywords


def test_restricted_classifications_recorded_and_excluded():
    names = {r["name"]: r for r in V.data["restricted_sources"]}
    for n in ("MasterFormat", "UniFormat (CSI)", "UNIFORMAT II (ASTM E1557)", "OmniClass"):
        assert names[n]["allowed"] is False and names[n]["findings"], n
    assert V.data["sources"]["src:ifc-4.3"]["license"] == "CC-BY-ND-4.0"
    assert V.data["sources"]["src:ifc-4.3"]["legal_review"] is True
    decisions = {d["id"]: d for d in V.data["decisions"]}
    assert "csi-classifications-excluded" in decisions and decisions["ifc-names-only"]["legal_review"] is True
    for n in ("MasterFormat", "UniFormat (CSI)", "UNIFORMAT II (ASTM E1557)", "OmniClass"):
        assert names[n]["decision_ref"] == "decisions/csi-classifications-excluded"


def test_uniclass_is_a_candidate_with_evidence_and_no_terms():
    u = V.data["candidate_sources"]["src:uniclass"]
    assert u["license"] == "CC-BY-ND-4.0" and u["allowed"] is False and u["terms_imported"] == 0 and u["legal_review"] is True
    urls = {e["url"] for e in u["license_evidence"]}
    assert {"https://uniclass.thenbs.com/download", "https://www.thenbs.com/legal/uniclass-api-terms-and-conditions"} <= urls
    assert "src:uniclass" not in V.data["sources"]
    assert not [n for s, n, r in vocab._term_records(V.data) if r.get("source") == "src:uniclass"]


@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d["candidate_sources"]["src:uniclass"].update(allowed=True), "must be allowed: false"),
    (lambda d: d["candidate_sources"]["src:uniclass"].update(terms_imported=5), "supplies no terms"),
    (lambda d: d["candidate_sources"].update({"src:omni": {"name": "OmniClass", "license": "x", "license_evidence": [{}], "allowed": False}}), "cannot be a candidate"),
    (lambda d: d["decisions"][0].pop("decided_by"), "missing decided_by"),
])
def test_candidate_and_decision_rules(mutate, msg):
    d = copy.deepcopy(V.data)
    mutate(d)
    assert any(msg in e for e in vocab.provenance_errors(d))
    blob = json.dumps({k: V.data[k] for k in ("keywords", "units", "subjects", "facts", "relations", "ifc_terms", "reference_geometry")}).lower()
    for marker in ("masterformat", "omniclass", "uniformat", "src:csi"):
        assert marker not in blob


@pytest.mark.parametrize("mutate,expect", [
    (lambda d: d["facts"][0].pop("license"), "needs source and license"),
    (lambda d: d["facts"][0].update(source="src:masterformat"), "not a declared, allowed source"),
    (lambda d: d["sources"].update({"src:mf": {**d["sources"]["src:ori"], "name": "MasterFormat 2020 numbers"}}), "restricted source"),
    (lambda d: d["restricted_sources"][0].update(allowed=True), "cannot be marked allowed"),
    (lambda d: d["defined_terms"][0].update(definition="copied words"), "definition text is not stored"),
])
def test_vocabulary_provenance_negative(mutate, expect):
    d = copy.deepcopy(V.data)
    mutate(d)
    assert any(expect in e for e in vocab.provenance_errors(d))


def test_defined_terms_are_citations_only():
    for t in V.data["defined_terms"]:
        assert t["definition_copied"] is False and "R202" in t["citation"] and len(t["defined_term"].split()) <= 5


# ---- grammar ----------------------------------------------------------------------------------
def test_parse_is_deterministic_and_complete():
    a, b = syntax.parse(GEOMETRIC.read_text()), syntax.parse(GEOMETRIC.read_text())
    assert a == b and len(a.rules) == 14
    assert len(syntax.parse(SAMPLES.read_text()).rules) == 8


@pytest.mark.parametrize("text,msg", [
    ("rule R304.1:x\n  cite IRC 2021 R304.1\n", "not closed"),
    ("rule R304.1:x\nrule R304.1:y\nend\n", "cannot nest"),
    ("rule R304.1:x\n  frobnicate\nend\n", "unknown keyword"),
    ("rule R304.1:x\n  when space_use is kitchen and floor_area > a or sloped_ceiling is true\nend\n", "mixing"),
    ("rule bad-id\nend\n", "not well formed"),
    ("rule R304.1:x\n  require floor_area >= a\n  require floor_area >= b\nend\n", "one require"),
    ("rule R304.1:x\n  cite IRC 2021 R304.1 part \"a\" extra\nend\n", "unexpected"),
])
def test_syntax_errors(text, msg):
    with pytest.raises(syntax.OriClSyntaxError, match=msg):
        syntax.parse(text)


RULE_OK = """
rule R304.1:room-area-min
  cite IRC 2021 R304.1
  adopt us-va:vrc-2021 mode adopts_base status sourced_primary by source:va:13vac5-63-210
  link https://codes.iccsafe.org/content/VARC2021P1/chapter-3-building-planning
  subject space is IfcSpace
  param min_habitable_room_area >= 70 ft2 at base status inferred_unamended source source:upcodes:vrc-2021-ch03
  unless space_use is kitchen
  when space_use is habitable
  require floor_area >= min_habitable_room_area
end
"""


def _compile(rule_text):
    return compiler.compile_text(HEADER + rule_text)


def test_minimal_rule_compiles():
    assert _compile(RULE_OK)[0]["unit"]["id"].endswith("R304.1:room-area-min")


@pytest.mark.parametrize("old,new,msg", [
    ("require floor_area", "require floor_areas", "not in the vocabulary"),
    ("70 ft2", "70 in", "does not match the quantity unit"),
    ("require floor_area >= min", "require floor_area > min", "declared with >= but used with >"),
    ("https://codes.iccsafe.org/content/VARC2021P1/chapter-3-building-planning", "https://example.com/code", "not an official source"),
    ("  cite IRC 2021 R304.1\n", "", "missing cite"),
    ("space_use is kitchen", "space_use is garage", "not a vocabulary value"),
    ("at base status", "at us-va:local status", "without an adopt line"),
    ("subject space is IfcSpace", "subject space is IfcWall", "maps to IfcSpace"),
    ("require floor_area >= min_habitable_room_area", "require floor_area >= min_habitable_room_area\n  check riser_height_max", "runs on stair_flight"),
    ("status inferred_unamended source source:upcodes:vrc-2021-ch03", "status inferred_unamended source source:upcodes:vrc-2021-ch03 locator \"the room shall have\"", "code register"),
    ("require floor_area >= min_habitable_room_area", "require ceiling_height >= min_habitable_room_area", "does not match"),
    ("mode adopts_base", "mode deletes", "deletes the rule") ,
])
def test_compile_errors(old, new, msg):
    text = RULE_OK.replace(old, new)
    if msg == "deletes the rule":
        text = text.replace("at base status", "at us-va:vrc-2021 status")
    assert text != RULE_OK
    with pytest.raises((compiler.OriClCompileError, syntax.OriClSyntaxError), match=msg):
        _compile(text)


def test_reviewer_terms_are_short_names():
    bad = """
rule R311.1:egress
  cite IRC 2021 R311.1
  adopt us-va:vrc-2021 mode adopts_base status sourced_primary by source:va:13vac5-63-210
  link https://codes.iccsafe.org/content/VARC2021P1/chapter-3-building-planning
  subject building is IfcBuilding
  reviewer terms "a path that runs from all parts of the house"
end
"""
    with pytest.raises(compiler.OriClCompileError, match="longer than 4 words"):
        _compile(bad)


# ---- compiled units ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def unit_validator():
    from jsonschema import Draft202012Validator, FormatChecker
    return Draft202012Validator(json.loads((REPO / "spec" / "ori-rule-unit-0.1.schema.json").read_text()), format_checker=FormatChecker())


def test_compiled_units_are_schema_valid_and_pass_conformance(unit_validator, core_validator):
    for c in GEO + SAMP:
        u = c["unit"]
        assert [e.message for e in unit_validator.iter_errors(u)] == [], u["id"]
        assert [e.message for e in core_validator.iter_errors(u)] == [], u["id"]
    objs = [c["unit"] for c in GEO + SAMP]
    for rule in ("no-code-text", "rule-unit-authority"):
        assert semantic.semantic_errors({"rule": rule, "objects": objs}) == [], rule


def test_official_hosts_match_conformance():
    assert compiler.OFFICIAL_SOURCE_HOSTS == semantic.OFFICIAL_SOURCE_HOSTS


def test_committed_compiled_files_are_current():
    for src in (GEOMETRIC, SAMPLES):
        out = src.with_suffix(".compiled.json")
        assert out.read_text() == compiled_json(src), f"regenerate: python -m ori_cl compile {src.name} --out {out.name}"


def _pkey(p):
    return {k: p.get(k) for k in ("name", "comparator", "quantity", "value_status", "source", "applies_when", "locator_detail")} | \
           {"quantity": {"value": p["quantity"]["value"], "unit": p["quantity"]["unit"]}}


@pytest.mark.parametrize("c", GEO, ids=lambda c: c["plan"]["rule_id"])
def test_compiled_parameters_and_layers_equal_collection(c):
    cu = c["unit"]
    ref = COLLECTION[cu["id"]]
    assert [_pkey(p) for p in cu["base_model"]["parameters"]] == [_pkey(p) for p in ref["base_model"]["parameters"]]
    assert len(cu["jurisdiction_layers"]) == len(ref["jurisdiction_layers"]) == 1
    a, b = cu["jurisdiction_layers"][0], ref["jurisdiction_layers"][0]
    for k in ("layer_id", "jurisdiction", "code", "edition", "effective_from", "authority_class", "binding", "precedence", "override_mode", "mode_status"):
        assert a[k] == b[k], k
    assert a["amendment_ref"]["source"] == b["amendment_ref"]["source"] and a["amendment_ref"]["item"] == b["amendment_ref"]["item"]
    assert [_pkey(p) for p in a.get("parameters", [])] == [_pkey(p) for p in b.get("parameters", [])]
    assert cu["source_section"]["section"] == ref["source_section"]["section"]
    assert cu["source_section"].get("subsection_part") == ref["source_section"].get("subsection_part")
    assert cu["evaluator"]["implementation"] == ref["evaluator"]["implementation"]
    assert cu["check_class"] == ref["check_class"] == "geometric_deterministic"
    assert cu["source_url"] == ref["source_url"]


# ---- equivalence ------------------------------------------------------------------------------
def _battery():
    out = []
    for r in [[7.5, 8.25], [7.5, 8.26], [7.0] * 3, [7.75], [], unconf([9.0]), [7.75, 8.125], [7.5, 7.9], [7.5, 7.875], None]:
        for t in [[9.0, 9.0], [8.99], [10.0, 10.375], [10.0, 10.4], [], unconf([12.0]), None]:
            out.append(S("stair_flight", riser_heights=r, tread_depths=t))
    for h in [[], [80.0], [79.9, 90.0], unconf([]), unconf([70.0]), Fact(None, "ifc_geometry"), None]:
        out.append(S("stair_flight", headroom_clearances=h))
    for use, ch, sl, area in itertools.product(
            ["habitable", "kitchen", "hallway", "bathroom", "toilet", "laundry", "other", "garage", unconf("habitable"), None],
            [84.0, 83.9, 80.0, 79.0, unconf(90.0), None], [True, False, unconf(True), Fact(None, "applicant_declared"), None],
            [70.0, 69.9, unconf(80.0), None]):
        out.append(S("space", space_use=use, ceiling_height=ch, sloped_ceiling=sl, floor_area=area))
    sill_frame = [(None, None), (44.0, None), (44.1, None), (unconf(40.0), None), (None, 43.0), (None, 45.0), (None, unconf(45.0))]
    for a, h, w, g, (sill, frame) in itertools.product(
            [None, 5.7, 5.69, 5.0, 4.99, unconf(6.0)], [None, 24.0, 23.9, 34.2, unconf(30.0)], [None, 20.0, 19.9, 24.0],
            [None, True, False, unconf(True), Fact(None, "ifc_property")], sill_frame):
        out.append(S("eero", net_clear_area=a, net_clear_height=h, net_clear_width=w, grade_floor_or_below_grade=g,
                     sill_height=sill, frame_bottom_height=frame))
    for d, gp in itertools.product([None, 30.0, 30.01, 48.0, unconf(48.0)], [None, True, False, unconf(True), Fact(None, "ifc_geometry")]):
        out.append(S("walking_surface", drop_height=d, guard_present=gp))
    for h, st in itertools.product([None, 36.0, 35.9, 34.0, 33.9, unconf(40.0)], [None, True, False, unconf(True), unconf(False), Fact(None, "ifc_geometry")]):
        out.append(S("guard", guard_height=h, on_stair_open_side=st))
    out.append(S("other_kind"))
    return out


@pytest.fixture(scope="module")
def ifc_subjects(tmp_path_factory):
    from ori_verify import ifc_fixtures
    d = tmp_path_factory.mktemp("oricl-ifc")
    subs = []
    for name, spec in (("pass", ifc_fixtures.passing_spec()), ("fail", ifc_fixtures.failing_spec()), ("incomplete", ifc_fixtures.incomplete_spec())):
        subs += ifc_extract.extract(ifc_fixtures.write_fixture(spec, d / f"{name}.ifc"))[0]
    ex = REPO / "verification" / "examples" / "declared"
    for f in ("declared-values-v1.json", "extracted-candidates-v1.json"):
        subs += dec.subjects_from_declared(json.loads((ex / f).read_text()))
    return subs


def _pairs(jur):
    for c in GEO:
        ref = units.resolve(COLLECTION[c["unit"]["id"]], jur)
        mine = units.resolve(c["unit"], jur)
        yield c, ref, mine


@pytest.mark.parametrize("jur", [VA, BASE], ids=["va", "irc-base"])
def test_ori_cl_equals_existing_checks(jur, ifc_subjects):
    subjects = _battery() + ifc_subjects
    n = 0
    mismatches = []
    for c, ref, mine in _pairs(jur):
        fn = rules.RULES[c["plan"]["check"]]
        for s in subjects:
            a, b = fn(s, ref), evaluator.evaluate_plan(c["plan"], mine, s)
            n += 1
            if (a.state, a.reason_code) != (b.state, b.reason_code):
                mismatches.append((c["plan"]["rule_id"], s.kind, {k: f.value for k, f in s.facts.items()}, (a.state, a.reason_code), (b.state, b.reason_code)))
    assert not mismatches, mismatches[:5]
    assert n > 20000


def test_ifc_models_give_all_outcomes(ifc_subjects):
    states = {evaluator.evaluate_plan(c["plan"], mine, s).state for c, _, mine in _pairs(VA) for s in ifc_subjects}
    assert states == {"pass", "fail", "unknown", "not_applicable"}


@pytest.mark.parametrize("change", ["deleted", "param_missing"])
def test_equivalence_under_deleted_and_missing_parameters(change):
    for c, ref, mine in _pairs(VA):
        for eff in (ref, mine):
            if change == "deleted":
                eff.deleted = True
            else:
                eff.params.pop(c["plan"]["params_required"][0])
        s = S(c["plan"]["subject"])
        a, b = rules.RULES[c["plan"]["check"]](s, ref), evaluator.evaluate_plan(c["plan"], mine, s)
        assert (a.state, a.reason_code) == (b.state, b.reason_code)
        assert b.reason_code == ("deleted_by_jurisdiction" if change == "deleted" else "parameter_missing")


def test_same_stair_va_pass_irc_fail():
    stair = S("stair_flight", riser_heights=[8.0] * 13)
    c = GEO[0]
    assert evaluator.evaluate_plan(c["plan"], units.resolve(c["unit"], VA), stair).state == "pass"
    assert evaluator.evaluate_plan(c["plan"], units.resolve(c["unit"], None), stair).state == "fail"


# ---- samples: data checks, override, judgment ----------------------------------------------------
SAMPLE = {c["plan"]["rule_id"]: c for c in SAMP}


def run(rule_id, subject, jur=VA):
    c = SAMPLE[rule_id]
    return evaluator.evaluate_plan(c["plan"], units.resolve(c["unit"], jur), subject)


def test_encloses_relation_semantics():
    k = "encloses:IfcSensor:SMOKESENSOR"
    rid = "R314.3:smoke-alarm-in-sleeping-room"
    assert run(rid, S("space", sleeping_room=False)).reason_code == "use_not_covered"
    assert run(rid, S("space", sleeping_room=True)).reason_code == "required_element_not_found"
    assert run(rid, S("space", sleeping_room=True, **{k: 1})).state == "pass"
    assert run(rid, S("space", sleeping_room=True, **{k: 0})).state == "fail"  # declared absence
    r = run(rid, S("space", sleeping_room=True, **{k: Fact(0, "ifc_property")}))
    assert (r.state, r.reason_code) == ("unknown", "required_element_not_found")  # absent from model: not evidence


def test_present_and_open_parameter_and_override():
    rid = "R314.4:smoke-alarms-interconnected"
    assert run(rid, S("building", multiple_smoke_alarms=True, smoke_alarms_interconnected=True)).state == "pass"
    assert run(rid, S("building", multiple_smoke_alarms=True, smoke_alarms_interconnected=False)).state == "fail"
    assert run(rid, S("building", multiple_smoke_alarms=False)).state == "not_applicable"
    for jur in (VA, BASE):
        r = run("R302.14:insulation-clearance", S("heat_source_device", **{"distance:IfcCovering:INSULATION": 6.0}), jur)
        assert (r.state, r.reason_code) == ("unknown", "parameter_missing")
    pv = "R324.6.2:pv-ridge-setback"
    assert run(pv, S("pv_array", ridge_setback=18.0)).state == "pass"
    assert run(pv, S("pv_array", ridge_setback=12.0)).state == "fail"
    assert run(pv, S("pv_array", ridge_setback=12.0), BASE).reason_code == "parameter_missing"
    assert SAMPLE[pv]["unit"]["ori_cl"]["open_parameters"][0]["layer"] == "base"
    assert [p["quantity"]["value"] for p in SAMPLE[pv]["unit"]["jurisdiction_layers"][0]["parameters"]] == [18]


def _norm_term(t):
    return re.sub(r"\s*\(.*?\)", "", t).strip().lower()


@pytest.mark.parametrize("rid", ["R302.7:under-stair-protection", "R311.1:egress-path", "R309.1:garage-floor"])
def test_judgment_units_name_the_interpretability_terms(rid):
    c = SAMPLE[rid]
    u = c["unit"]
    assert u["check_class"] == "judgment" and u["evaluator"]["kind"] == "human_reviewer"
    r = run(rid, S(c["plan"]["subject"]))
    assert (r.state, r.reason_code) == ("unknown", "reviewer_determination_required")
    ref = next(x for x in COLLECTION.values() if x["source_section"]["section"] == u["source_section"]["section"])
    expected = {_norm_term(t["term"]) for t in ref["interpretability"]["ambiguous_terms"]}
    assert {_norm_term(t) for t in u["ori_cl"]["reviewer_terms"]} == expected


def test_deletes_override_and_between_form():
    text = HEADER + """
rule R302.13:demo-deleted
  cite IRC 2021 R302.13
  adopt us-va:vrc-2021 mode deletes status sourced_primary by source:va:13vac5-63-210 item "310.8 item 9"
  link https://codes.iccsafe.org/content/VARC2021P1/chapter-3-building-planning
  subject space is IfcSpace
  param band_low >= 70 in at base status estimate source source:ori:test
  param band_high <= 90 in at base status estimate source source:ori:test
  require ceiling_height between band_low and band_high
end
"""
    c = compiler.compile_text(text)[0]
    assert evaluator.evaluate_plan(c["plan"], units.resolve(c["unit"], VA), S("space", ceiling_height=80.0)).reason_code == "deleted_by_jurisdiction"
    base = units.resolve(c["unit"], None)
    assert [evaluator.evaluate_plan(c["plan"], base, S("space", ceiling_height=h)).state for h in (69.0, 70.0, 90.0, 90.5)] == ["fail", "pass", "pass", "fail"]


def test_ifc_binding_encloses_and_property_facts(tmp_path):
    from ori_verify.ifc_fixtures import _Builder
    import ifcopenshell.api as api
    b = _Builder("oricl-bind")
    rooms = {}
    for name, sleeping in (("Bedroom A", True), ("Bedroom B", True), ("Kitchen", False)):
        sp = api.run("root.create_entity", b.f, ifc_class="IfcSpace", name=name)
        api.run("aggregate.assign_object", b.f, products=[sp], relating_object=b.storey)
        b.pset(sp, "Pset_ORI_SpaceUse", {"UseCategory": "kitchen" if name == "Kitchen" else "habitable", "SleepingRoom": sleeping})
        rooms[name] = sp
    sensor = api.run("root.create_entity", b.f, ifc_class="IfcSensor", name="SA-1", predefined_type="SMOKESENSOR")
    api.run("spatial.assign_container", b.f, products=[sensor], relating_structure=rooms["Bedroom A"])
    sink = api.run("root.create_entity", b.f, ifc_class="IfcSanitaryTerminal", name="Sink", predefined_type="SINK")
    api.run("spatial.assign_container", b.f, products=[sink], relating_structure=rooms["Kitchen"])
    b.pset(b.building, "Pset_ORI_LifeSafety", {"MultipleSmokeAlarms": True, "SmokeAlarmsInterconnected": True})
    path = tmp_path / "bind.ifc"
    b.f.write(str(path))
    subjects, _ = ifc_extract.extract(path)
    subjects = ifc_bind.bind(path, subjects, [c["plan"] for c in SAMP])
    got = {(r.unit_id.split(":")[-1], r.subject.label): (r.state, r.reason_code) for r in evaluator.evaluate(SAMP, subjects, VA)}
    assert got[("smoke-alarm-in-sleeping-room", "Bedroom A")] == ("pass", "requirement_met")
    assert got[("smoke-alarm-in-sleeping-room", "Bedroom B")] == ("unknown", "required_element_not_found")
    assert got[("smoke-alarm-in-sleeping-room", "Kitchen")] == ("not_applicable", "use_not_covered")
    assert got[("kitchen-sink", "Kitchen")] == ("pass", "requirement_met")
    assert got[("smoke-alarms-interconnected", "Synthetic single-family dwelling")] == ("pass", "requirement_met")
    assert got[("egress-path", "Synthetic single-family dwelling")] == ("unknown", "reviewer_determination_required")


@pytest.mark.parametrize("c", GEO + SAMP, ids=lambda c: c["plan"]["rule_id"])
def test_missing_information_never_fails(c):
    r = evaluator.evaluate_plan(c["plan"], units.resolve(c["unit"], VA), S(c["plan"]["subject"]))
    assert r.state == "unknown"


# ---- no code text ----------------------------------------------------------------------------------
def test_ori_cl_sources_hold_no_code_text():
    shall = re.compile(r"\bshall\b", re.IGNORECASE)
    for src in (GEOMETRIC, SAMPLES):
        for n, line in enumerate(src.read_text().splitlines(), 1):
            assert not shall.search(line), f"{src.name}:{n}"
            for q in re.findall(r'"([^"]*)"', line):
                limit = 4 if line.strip().startswith("reviewer") or " part " in line else compiler.MAX_NOTE_WORDS
                assert len(q.split()) <= limit, f"{src.name}:{n}: {q!r}"


FICTION = """R901 Lanterns
R901.1 General. Every lantern post shall stand upright and shall be approved by the harbor warden. See Section R901.2.
R901.2 Height. Lantern posts shall not exceed 9 feet where required by Table R901.2, and adequate spacing is permitted.
R902 Moorings
R902.1 Ropes. Mooring ropes must be sufficient for the vessel and meet ASTM D1234 or other approved standards.
"""


def test_corpus_stats_store_counts_not_text():
    stats = corpus_stats.analyze(FICTION, "fiction")
    corpus_stats.assert_no_text(stats, FICTION)
    ids = [s["section"] for s in stats["sections"]]
    assert ids == ["R901", "R901.1", "R901.2", "R902", "R902.1"]
    s1 = stats["sections"][1]
    assert s1["modals"] == {"shall": 2} and s1["ambiguity_markers"] == {"approved": 1} and s1["cross_references"]["section"] == 1
    assert stats["sections"][2]["modals"] == {"shall not": 1, "is/are permitted": 1}
    assert stats["sections"][4]["cross_references"]["external_standard"] == 1
    assert len(s1["sha256"]) == 64
    blob = json.dumps(stats)
    for w in ("lantern", "harbor", "warden", "mooring", "vessel", "upright"):
        assert w not in blob.lower()
    leaked = copy.deepcopy(stats)
    leaked["sections"][1]["note"] = " ".join(FICTION.split("\n")[1].split()[3:10])  # a 7-word run of the source
    with pytest.raises(AssertionError, match="shares"):
        corpus_stats.assert_no_text(leaked, FICTION)


def test_committed_language_stats_are_derived_only():
    p = REPO / "research" / "data" / "vrc2021-ch03-language-stats-DRAFT.json"
    if not p.is_file():
        pytest.skip("language-stats study file is not part of this tree")
    d = json.loads(p.read_text())
    allowed_keys = {"section", "sha256", "words", "sentences", "modals", "ambiguity_markers", "cross_references", "vocabulary_hits", "defined_term_hits", "segments"}
    for s in d["sections"]:
        assert set(s) <= allowed_keys and re.fullmatch(r"R\d{3}(\.\d+)*", s["section"])
        assert set(s["modals"]) <= set(corpus_stats.MODALS) and set(s["ambiguity_markers"]) <= set(corpus_stats.AMBIGUITY_MARKERS)
    assert d["status"] == "DRAFT" and "legal review" in d["legal_note"]


def test_ebnf_keywords_match_parser():
    ebnf = (REPO / "spec" / "ori-cl-0.1.ebnf").read_text()
    body = re.sub(r"\(\*.*?\*\)", "", ebnf, flags=re.S)
    quoted = {w for w in re.findall(r'"([a-z][a-z_]*)"', body)}
    enums = set(syntax.MODES) | set(syntax.STATUSES) | {"state_adopted_code", "local_adopted_amendment"}
    assert quoted - enums == set(syntax.PARSER_KEYWORDS)
    assert len(syntax.PARSER_KEYWORDS) == 58
