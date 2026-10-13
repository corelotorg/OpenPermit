#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the ORI Chapter 6 worked example (2021 IRC base + 2021 Virginia VRC layer).

DRAFT. Single source of truth for ``va-vrc-2021-ch06.units.json`` and
``CHAPTER-6-TABLE.md``; ``rules/test_rules_data.py`` fails if the committed outputs
drift from what this script produces. Unit shape follows ``rules/irc2021/ch03``.

What is sourced and what is an estimate
---------------------------------------
* Virginia override layer: 13VAC5-63-210 section 310.8 items 62-64, fetched from
  law.lis.virginia.gov on 2026-10-12 (sourced_primary). Virginia restates R602.10,
  adds an exception to R602.10.9 and replaces R602.12 with "practical wall bracing".
  Numeric thresholds on the Virginia R602.12 units are read from that regulation and
  are the only ch06 values ORI treats as verified.
* IRC 2021 base values (stud spacing and height, top plates, bored holes, notches) are
  UNVERIFIED (value_status ``estimate``). ICC Digital Codes serves a script-only page to
  automated fetches (2026-10-12). Most of these values agree with a Virginia county
  handout of 2018 VRC Chapter 6 pages (source:secondary:louisa-2018-vrc-ch6-handout),
  but that is a different edition, so they stay estimates. The rule functions return
  ``unknown`` (reason ``threshold_unverified``) for any estimate value and never pass or
  fail on one.
* Table data (owner decision PENDING): only the specific cells a rule or test needs are
  encoded, never whole tables or their layout. See docs/CH6-FRAMING-DRAFT.md.
* Section list: UNVERIFIED against the 2021 official text (see catalogue_ch06.py).
* check_class tags and interpretability scores are ORI ESTIMATES.

Citation policy (docs/CITATION-POLICY.md): cite, paraphrase, link; never reproduce.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue_ch06 import UNITS, VA_AMENDMENTS, VA_REPLACED_CHILD_PREFIX

HERE = Path(__file__).resolve().parent
OUT_JSON = HERE / "va-vrc-2021-ch06.units.json"
OUT_MD = HERE / "CHAPTER-6-TABLE.md"
INTERP_JSON = HERE / "interpretability-ch06.json"
PARA_JSON = HERE / "paraphrases-ch06.json"

VRC_CH6_URL = "https://codes.iccsafe.org/content/VARC2021P1/chapter-6-wall-construction"
IRC_CH6_URL = "https://codes.iccsafe.org/content/IRC2021P2/chapter-6-wall-construction"
VAC_210_URL = "https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section210/"
LOUISA_URL = "https://www.louisacounty.gov/DocumentCenter/View/7243/Louisa-County-Wall-Charts-and-Figures"

RECORDED_AT = "2026-10-12"
RECORDED_BY = "ORI automated drafting agent (DRAFT, not yet human-reviewed)"
VA_JURISDICTION = "urn:ori:jurisdiction:us-va"
VA_EFFECTIVE = "2024-01-18"
VA = "source:va:13vac5-63-210"
LOU = "source:secondary:louisa-2018-vrc-ch6-handout"
EST = "estimate"
PRI = "sourced_primary"

SOURCES = [
    {"id": "source:icc:irc-2021", "type": "Source", "version": "1", "title": "2021 International Residential Code (model code), Chapter 6",
     "publisher": "International Code Council", "locator": IRC_CH6_URL, "edition": "2021", "authority_class": "model_code",
     "license_status": "ICC copyright; ORI cites section numbers, paraphrases and bare numeric values only and links to ICC Digital Codes",
     "retrieved_at": None,
     "metadata": {"note": "Automated fetch on 2026-10-12 returned only the page title (script-rendered). Base values are therefore estimates."}},
    {"id": "source:icc:vrc-2021", "type": "Source", "version": "1", "title": "2021 Virginia Residential Code (IRC 2021 with Virginia amendments), ICC Digital Codes, Chapter 6",
     "publisher": "International Code Council (for the Commonwealth of Virginia)", "locator": VRC_CH6_URL, "edition": "2021 VRC",
     "authority_class": "state_official_source", "license_status": "ICC copyright in the IRC text; link only", "retrieved_at": None,
     "metadata": {"note": "Link-out target for every unit's source_url. URL follows the pattern of the Chapter 3 link; not fetched (UNVERIFIED link)."}},
    {"id": VA, "type": "Source", "version": "1",
     "title": "13VAC5-63-210, Virginia Construction Code Section 310 (Virginia Residential Code), including 310.8 Amendments to the IRC",
     "publisher": "Virginia Administrative Code (Code of Virginia via law.lis.virginia.gov)", "locator": VAC_210_URL,
     "edition": "2021 Virginia codes", "authority_class": "state_official_source", "license_status": "public law",
     "retrieved_at": "2026-10-12T20:00:00-04:00", "metadata": {"note": "Items 62-64 read for Chapter 6 on 2026-10-12."}},
    {"id": LOU, "type": "Source", "version": "1",
     "title": "Louisa County (Virginia) wall charts and figures handout: scanned 2018 VRC Chapter 6 pages",
     "publisher": "Louisa County, Virginia (public document center)", "locator": LOUISA_URL, "edition": "2018 VRC (not 2021)", "authority_class": "local_official_source",
     "license_status": "Notice seen on the pages: ICC copyright, single-user licence, no further reproduction. ORI keeps only the URL, date and SHA-256; no text or image is committed. ORI makes no legal determination.",
     "retrieved_at": "2026-10-12T20:03:00-04:00",
     "metadata": {"sha256": "83d8a9c2cb50617c08b4cf1ee889620de564bdf3b51dca2277dc0d6d9e51e67d",
                  "note": "Used only to cross-check that estimate values and R602 numbering agree with an earlier edition. Not a 2021 source; nothing here is treated as verified. Source attribution only; no affiliation."}},
    {"id": "source:va:codes-2021-effective", "type": "Source", "version": "1", "title": "Virginia Codes: 2021 codes effective January 18, 2024",
     "publisher": "Virginia DHCD", "locator": "https://www.dhcd.virginia.gov/codes", "authority_class": "state_official_source", "retrieved_at": "2026-09-28T00:00:00-04:00"},
]


def P(name, comparator, value, unit, status, source, applies_when=None, detail=None):
    p = {"name": name, "comparator": comparator, "quantity": {"value": value, "unit": unit}, "value_status": status, "source": source}
    if applies_when:
        p["applies_when"] = applies_when
    if detail:
        p["locator_detail"] = detail
    return p


ESTD = "UNVERIFIED for 2021: not fetched from the official 2021 text; agrees with a 2018 VRC handout"
ESTM = "UNVERIFIED: ORI recollection only; not found in any fetched source"
I64 = "310.8 item 64"

# Framing information items (Pset_ORI_Framing on IfcWall), reused by several units.
FR = "rules/irc2021/ch06/ids/ori-ch06-framing.ids"
INFO_WALL = [
    ("wall.stud_size", "Nominal stud size", "Pset_ORI_Framing.StudNominalSize", "walls[].stud_size", "Wall section or framing note"),
    ("wall.bearing", "Whether the wall is load bearing", "Pset_WallCommon.LoadBearing", "walls[].bearing", "Framing plan"),
]

IMPLEMENTED = {
    ("R602.3.1", "stud spacing"): dict(
        fn="framing_stud_spacing_max", slug="stud-spacing-max", subject="framed_wall",
        base=[P("max_stud_spacing_2x4_roof_only", "<=", 24, "in", EST, LOU, "stud_size == 2x4 and floors_supported == 0", ESTD),
              P("max_stud_spacing_2x4_one_floor", "<=", 16, "in", EST, LOU, "stud_size == 2x4 and floors_supported == 1", ESTD),
              P("max_stud_spacing_2x6_one_floor", "<=", 24, "in", EST, LOU, "stud_size == 2x6 and floors_supported == 1", ESTD),
              P("max_stud_spacing_2x6_two_floors", "<=", 16, "in", EST, LOU, "stud_size == 2x6 and floors_supported == 2", ESTD)],
        inputs=[("stud_size", "enum", None, True), ("stud_spacing", "length", "in", True), ("bearing", "boolean", None, True), ("floors_supported", "count", None, True)],
        info=INFO_WALL + [("wall.stud_spacing", "Stud spacing on center", "Pset_ORI_Framing.StudSpacing", "walls[].stud_spacing_in", "Wall section"),
                          ("wall.floors_supported", "Floors carried above (0 = roof and ceiling only)", "Pset_ORI_Framing.FloorsSupported", "walls[].floors_supported", "Building section")],
        ids=FR + "#Framed walls declare stud size and spacing", entity="IfcWall"),
    ("R602.3.1", "stud height"): dict(
        fn="framing_bearing_stud_height_max", slug="bearing-stud-height-max", subject="framed_wall",
        base=[P("max_bearing_stud_height", "<=", 10, "ft", EST, LOU, None, ESTD)],
        inputs=[("stud_height", "length", "in", True), ("bearing", "boolean", None, True)],
        info=INFO_WALL + [("wall.stud_height", "Laterally unsupported stud height", "Pset_ORI_Framing.StudHeight (or wall body height)", "walls[].stud_height_in", "Wall section")],
        ids=FR + "#Framed walls declare stud size and spacing", entity="IfcWall"),
    ("R602.3.2", "plate count"): dict(
        fn="framing_top_plate_count_min", slug="top-plate-count-min", subject="framed_wall",
        base=[P("min_top_plate_count", ">=", 2, "count", EST, "source:icc:irc-2021", None, ESTM)],
        inputs=[("top_plate_count", "count", None, True), ("bearing", "boolean", None, True)],
        info=INFO_WALL + [("wall.top_plate_count", "Number of top plates", "Pset_ORI_Framing.TopPlateCount", "walls[].top_plate_count", "Wall section")],
        ids=FR + "#Framed walls declare plates", entity="IfcWall"),
    ("R602.3.2", "splice offset"): dict(
        fn="framing_top_plate_splice_offset_min", slug="top-plate-splice-offset-min", subject="framed_wall",
        base=[P("min_top_plate_splice_offset", ">=", 24, "in", EST, "source:icc:irc-2021", None, ESTM)],
        inputs=[("top_plate_splice_offset", "length", "in", True)],
        info=[("wall.top_plate_splice_offset", "Offset between end joints of upper and lower top plates", "Pset_ORI_Framing.TopPlateSpliceOffset", "walls[].top_plate_splice_offset_in", "Framing detail")],
        ids=FR + "#Framed walls declare plates", entity="IfcWall"),
    ("R602.6", "bored holes"): dict(
        fn="framing_bored_hole_ratio_max", slug="bored-hole-ratio-max", subject="framed_wall",
        base=[P("max_bored_hole_ratio_bearing", "<=", 0.40, "ratio", EST, LOU, "bearing == true and stud_doubled == false", ESTD),
              P("max_bored_hole_ratio_bearing_doubled", "<=", 0.60, "ratio", EST, LOU, "bearing == true and stud_doubled == true", ESTD),
              P("max_bored_hole_ratio_nonbearing", "<=", 0.60, "ratio", EST, LOU, "bearing == false", ESTD)],
        inputs=[("max_bored_hole_diameter", "length", "in", True), ("stud_depth", "length", "in", True), ("bearing", "boolean", None, True)],
        info=INFO_WALL + [("wall.max_bored_hole_diameter", "Largest bored hole diameter in any stud", "Pset_ORI_Framing.MaxBoredHoleDiameter", "walls[].max_bored_hole_diameter_in", "Framing or MEP penetration detail")],
        ids=FR + "#Framed walls declare stud size and spacing", entity="IfcWall"),
    ("R602.6", "notches"): dict(
        fn="framing_notch_ratio_max", slug="notch-ratio-max", subject="framed_wall",
        base=[P("max_notch_ratio_bearing", "<=", 0.25, "ratio", EST, LOU, "bearing == true", ESTD),
              P("max_notch_ratio_nonbearing", "<=", 0.40, "ratio", EST, LOU, "bearing == false", ESTD)],
        inputs=[("max_notch_depth", "length", "in", True), ("stud_depth", "length", "in", True), ("bearing", "boolean", None, True)],
        info=INFO_WALL + [("wall.max_notch_depth", "Deepest notch in any stud", "Pset_ORI_Framing.MaxNotchDepth", "walls[].max_notch_depth_in", "Framing detail")],
        ids=FR + "#Framed walls declare stud size and spacing", entity="IfcWall"),
    # --- Virginia practical wall bracing (13VAC5-63-210 item 64), sourced_primary ---
    ("R602.12.1", None): dict(
        fn="practical_bracing_sheathing", slug="practical-bracing-sheathing", subject="braced_wall_panel", va_only=True,
        va=[P("min_thickness_wood_structural_panel", ">=", 0.4375, "in", PRI, VA, "sheathing_material == wood_structural_panel", I64),
            P("min_thickness_structural_fiberboard", ">=", 0.5, "in", PRI, VA, "sheathing_material == structural_fiberboard", I64),
            P("min_thickness_gypsum_board", ">=", 0.5, "in", PRI, VA, "sheathing_material == gypsum_board and location == interior", I64)],
        inputs=[("sheathing_material", "enum", None, True), ("sheathing_thickness", "length", "in", True), ("panel_location", "enum", None, True)],
        info=[("panel.sheathing_material", "Bracing sheathing material", "Pset_ORI_BracedWallPanel.SheathingMaterial", "panels[].sheathing_material", "Bracing plan or wall section"),
              ("panel.sheathing_thickness", "Sheathing thickness", "Pset_ORI_BracedWallPanel.SheathingThickness", "panels[].sheathing_thickness_in", "Wall section"),
              ("panel.location", "Exterior or interior panel", "Pset_ORI_BracedWallPanel.Location", "panels[].location", "Bracing plan")],
        ids=FR + "#Braced wall panels declare method and sheathing", entity="IfcPlate"),
    ("R602.12.2", "exterior panel length"): dict(
        fn="practical_bracing_exterior_panel_length", slug="practical-bracing-exterior-panel-length", subject="braced_wall_panel", va_only=True,
        va=[P("min_panel_length_8ft_garage_one_story", ">=", 24, "in", PRI, VA, "wall_height_ft == 8 and adjacent_opening == one_story_garage_door", I64 + "; one cell of the panel-length table"),
            P("min_panel_length_8ft_opening_le_64", ">=", 24, "in", PRI, VA, "wall_height_ft == 8 and opening_clear_height_in <= 64", I64 + "; one cell"),
            P("min_panel_length_8ft_opening_le_72", ">=", 27, "in", PRI, VA, "wall_height_ft == 8 and 64 < opening_clear_height_in <= 72", I64 + "; one cell"),
            P("min_panel_length_8ft_opening_le_80", ">=", 30, "in", PRI, VA, "wall_height_ft == 8 and 72 < opening_clear_height_in <= 80", I64 + "; one cell"),
            P("min_panel_length_8ft_opening_gt_80", ">=", 36, "in", PRI, VA, "wall_height_ft == 8 and opening_clear_height_in > 80", I64 + "; one cell")],
        inputs=[("panel_length", "length", "in", True), ("wall_height", "length", "in", True), ("adjacent_opening_clear_height", "length", "in", True)],
        info=[("panel.length", "Braced wall panel length", "IfcPlate body geometry (horizontal extent)", "panels[].length_in", "Bracing plan"),
              ("panel.wall_height", "Wall height at the panel", "IfcPlate body geometry (vertical extent) or Pset_ORI_BracedWallPanel.WallHeight", "panels[].wall_height_in", "Wall section"),
              ("panel.adjacent_opening_clear_height", "Clear height of the taller adjacent opening", "Pset_ORI_BracedWallPanel.AdjacentOpeningClearHeight", "panels[].adjacent_opening_clear_height_in", "Door and window schedule")],
        ids=FR + "#Braced wall panels declare method and sheathing", entity="IfcPlate"),
    ("R602.12.2", "interior panel length"): dict(
        fn="practical_bracing_interior_panel_length", slug="practical-bracing-interior-panel-length", subject="braced_wall_panel", va_only=True,
        va=[P("min_interior_panel_length", ">=", 48, "in", PRI, VA, "location == interior", I64)],
        inputs=[("panel_length", "length", "in", True), ("panel_location", "enum", None, True)],
        info=[("panel.length", "Braced wall panel length", "IfcPlate body geometry (horizontal extent)", "panels[].length_in", "Bracing plan")],
        ids=FR + "#Braced wall panels declare method and sheathing", entity="IfcPlate"),
    ("R602.12.3", None): dict(
        fn="practical_bracing_rectangle_limits", slug="practical-bracing-rectangle-limits", subject="bracing_rectangle", va_only=True,
        va=[P("max_rectangle_side", "<=", 80, "ft", PRI, VA, None, I64), P("max_rectangle_aspect_ratio", "<=", 3, "ratio", PRI, VA, None, I64)],
        inputs=[("rectangle_sides", "length_list", "ft", True)],
        info=[("rectangle.sides", "Side lengths of each circumscribed rectangle", "Pset_ORI_BracingRectangle.LengthX / LengthY", "bracing_rectangles[].sides_ft", "Bracing plan")],
        ids=FR + "#Bracing rectangles declare extent and required length", entity="IfcAnnotation"),
    ("R602.12.4.2", None): dict(
        fn="practical_bracing_contributing_length", slug="practical-bracing-contributing-length", subject="bracing_rectangle_side", va_only=True,
        va=[P("exterior_panel_contribution", "==", 1.0, "ratio", PRI, VA, "location == exterior", I64),
            P("interior_panel_contribution", "==", 0.5, "ratio", PRI, VA, "location == interior", I64),
            P("max_interior_panel_assignment_distance", "<=", 4, "ft", PRI, VA, "location == interior", I64 + " (R602.12.4.1)")],
        inputs=[("required_bracing_length", "length", "ft", True), ("assigned_panel_lengths", "length_list", "ft", True)],
        info=[("rectangle.required_bracing_length", "Required bracing length for the side, as the applicant computed it from the bracing table", "Pset_ORI_BracingRectangle.RequiredBracingFrontRear / RequiredBracingLeftRight", "bracing_rectangles[].required_ft", "Bracing calculation sheet"),
              ("panel.location", "Exterior or interior panel", "Pset_ORI_BracedWallPanel.Location", "panels[].location", "Bracing plan")],
        ids=FR + "#Bracing rectangles declare extent and required length", entity="IfcAnnotation"),
    ("R602.12.6", "corner distance"): dict(
        fn="practical_bracing_corner_distance", slug="practical-bracing-corner-distance", subject="bracing_rectangle_side", va_only=True,
        va=[P("max_panel_edge_to_corner", "<=", 12, "ft", PRI, VA, None, I64)],
        inputs=[("assigned_panel_lengths", "length_list", "ft", True)],
        info=[("panel.position", "Panel position along the rectangle side", "IfcPlate body geometry", "panels[].start_ft / end_ft", "Bracing plan")],
        ids=FR + "#Bracing rectangles declare extent and required length", entity="IfcAnnotation"),
    ("R602.12.6", "panel gap"): dict(
        fn="practical_bracing_panel_gap", slug="practical-bracing-panel-gap", subject="bracing_rectangle_side", va_only=True,
        va=[P("max_panel_edge_gap", "<=", 20, "ft", PRI, VA, None, I64)],
        inputs=[("assigned_panel_lengths", "length_list", "ft", True)],
        info=[("panel.position", "Panel position along the rectangle side", "IfcPlate body geometry", "panels[].start_ft / end_ft", "Bracing plan")],
        ids=FR + "#Bracing rectangles declare extent and required length", entity="IfcAnnotation"),
}

CLASS = {"D": "data_check", "G": "geometric_deterministic", "J": "judgment"}


def unit_id(section, part, slug=None):
    tail = section + (":" + slug if slug else (":" + "".join(c if c.isalnum() else "-" for c in part.lower()).strip("-") if part else ""))
    return f"urn:ori:rule-unit:irc2021-va:{tail}"


def va_amendment(section):
    if section in VA_AMENDMENTS:
        return VA_AMENDMENTS[section]
    if section.startswith(VA_REPLACED_CHILD_PREFIX):
        return ("replaces_section", "64", "Virginia practical wall bracing subsection (R602.12 replaced in full by item 64). The IRC base has differently worded R602.12 subsections (simplified bracing) that are not catalogued here.")
    return None


def va_layer(section):
    amend = va_amendment(section)
    if amend is None:
        mode, item, note = "adopts_base", None, "No amendment to this section is listed in 13VAC5-63-210 section 310.8 (fetched 2026-10-12); the VRC adopts the IRC base."
    else:
        mode, item, note = amend
    return {"layer_id": "us-va:vrc-2021", "jurisdiction": VA_JURISDICTION, "code": "VRC", "edition": "2021", "effective_from": VA_EFFECTIVE,
            "authority_class": "state_adopted_code", "binding": True, "precedence": 1, "override_mode": mode, "mode_status": PRI,
            "amendment_ref": {"source": VA, "item": f"310.8 item {item}" if item else None, "note": note}}


PARAPHRASES = json.loads(PARA_JSON.read_text(encoding="utf-8"))["paraphrases"]


def build_unit(section, part, title, cls, sf):
    impl = IMPLEMENTED.get((section, part))
    layer = va_layer(section)
    va_child = section.startswith(VA_REPLACED_CHILD_PREFIX)
    base = {"code": "IRC", "edition": "2021", "publisher": "International Code Council", "authority_class": "model_code", "binding": False,
            "source": "source:icc:irc-2021", "status": "not_in_base" if va_child else "present"}
    if impl:
        if impl.get("va_only"):
            layer["parameters"] = impl["va"]
        else:
            base["parameters"] = impl["base"]
            layer["parameters"] = impl["base"]  # adopts_base: same values, same (estimate) status
    check_class = CLASS[cls]
    if check_class == "judgment":
        evaluator = {"kind": "human_reviewer", "implementation": None, "implementation_version": None}
    elif impl:
        evaluator = {"kind": "deterministic_function", "implementation": f"verification/ori_verify/rules_ch06.py#{impl['fn']}", "implementation_version": "0.1.0"}
    else:
        evaluator = {"kind": "not_implemented", "implementation": None, "implementation_version": None}
    checked = [VA, LOU]
    unit = {
        "id": unit_id(section, part, impl["slug"] if impl else None),
        "type": "Requirement", "version": "0.1.0", "effective_from": "2024-01-18T00:00:00-05:00", "effective_to": None,
        "jurisdiction": [VA_JURISDICTION],
        "source": ["source:icc:vrc-2021", VA, "source:va:codes-2021-effective"] if va_child else ["source:icc:vrc-2021", "source:icc:irc-2021", VA, "source:va:codes-2021-effective"],
        "derived_from": [], "supersedes": [],
        "metadata": {"authority_classification": "state_adopted_code", "status": "DRAFT"},
        "rule_unit_profile": "ori-rule-unit-0.1",
        "title": title,
        "source_section": {"code": "VRC" if va_child else "IRC", "edition": "2021", "section": section, "chapter": 6},
        "authority_classification": "state_adopted_code",
        "check_class": check_class, "classification_basis": "estimate", "single_family_applicability": sf,
        "base_model": base, "jurisdiction_layers": [layer],
        "required_information": {"ids": None, "items": []}, "inputs": [],
        "result_states": ["pass", "fail", "unknown", "not_applicable"],
        "unknown_policy": {"missing_information_result": "unknown", "statement": "Missing, unreadable or unconfirmed information, or an unverified threshold, yields unknown, never fail."},
        "evaluator": evaluator,
        "provenance": {"recorded_by": RECORDED_BY, "recorded_at": RECORDED_AT, "sources_checked": checked},
        "legal_boundary": {"machine_result_is_approval": False, "statement": "Any machine result for this unit is reviewer evidence, not approval. Only the building official's decision under the USBC is lawful approval."},
    }
    if part:
        unit["source_section"]["subsection_part"] = part
    if impl:
        unit["inputs"] = [{"name": n, "datatype": d, **({"unit": u} if u else {}), "required": r} for n, d, u, r in impl["inputs"]]
        unit["required_information"] = {
            "ids": {"ids_version": "1.0", "specification_ref": impl["ids"], "applicability_entity": impl["entity"]},
            "items": [{"key": k, "description": d, "ifc_path": ip, "declared_value_key": dk, "pdf_evidence": pe} for k, d, ip, dk, pe in impl["info"]],
        }
    unit["paraphrase"] = PARAPHRASES[f"{section}|{part}" if part else section]
    unit["source_url"] = VRC_CH6_URL
    links = [{"label": f"2021 VRC Chapter 6, section {section} (ICC Digital Codes)", "url": VRC_CH6_URL}]
    if layer["override_mode"] != "adopts_base":
        links.append({"label": "13VAC5-63-210 section 310.8 (Virginia amendments to the IRC)", "url": VAC_210_URL})
    if not va_child:
        links.append({"label": "2021 IRC Chapter 6 model code (ICC Digital Codes; comparison only)", "url": IRC_CH6_URL})
    unit["source_links"] = links
    return unit


def load_interpretability():
    return json.loads(INTERP_JSON.read_text(encoding="utf-8"))


def apply_interpretability(units, data):
    by_id = {u["id"]: u for u in units}
    unknown = sorted(set(data["scores"]) - set(by_id))
    assert not unknown, f"interpretability scores for unknown units: {unknown}"
    for uid, e in data["scores"].items():
        rec = {"rubric_version": data["rubric_version"], "score": e["score"], "scoring_status": data["scoring_status_default"], "rationale": e["rationale"]}
        for k in ("ambiguous_terms", "intent_questions"):
            if e.get(k):
                rec[k] = e[k]
        rec["evidence_strength"] = "none_found"
        rec["reviewers"] = [{"reviewer": data["pre_scorer"], "score": e["score"], "date": data["scored_at"], "independent": True, "role": "pre_scorer"}]
        rec["scored_text_source"] = data["scored_text_source"]
        rec["scored_at"] = data["scored_at"]
        by_id[uid]["interpretability"] = rec


def build():
    units = [build_unit(*u) for u in UNITS]
    ids = [u["id"] for u in units]
    assert len(ids) == len(set(ids)), "duplicate rule-unit ids"
    assert set(IMPLEMENTED) <= {(s, p) for s, p, *_ in UNITS}
    apply_interpretability(units, load_interpretability())
    return units


def split(units):
    c = Counter(u["check_class"] for u in units)
    return {k: c.get(k, 0) for k in ("data_check", "geometric_deterministic", "judgment")}


def collection(units):
    impl = [u for u in units if u["evaluator"]["kind"] == "deterministic_function"]
    return {
        "collection_id": "urn:ori:rule-unit-collection:irc2021-va:ch06",
        "rule_unit_profile": "ori-rule-unit-0.1",
        "title": "2021 IRC Chapter 6 (R601-R610) Wall Construction with the 2021 Virginia Residential Code override layer: worked example",
        "status": "DRAFT",
        "draft_completion_request": "Needs a human reviewer to (1) verify the section list and every estimate value against the official 2021 IRC/VRC text, then raise value_status (rules stay unknown until then), (2) confirm check_class estimates, (3) split R603-R610 into subsection units, (4) run two-reviewer interpretability scoring, and (5) record the owner's decision on encoding table cells (pending; only cells the tests need are encoded).",
        "generated_by": "rules/irc2021/ch06/build_units.py",
        "scope": {
            "occupancy": "detached single-family dwelling",
            "base_model": "2021 IRC (model code; not binding by itself)",
            "override_layers": ["2021 Virginia Residential Code (13VAC5-63-210), effective 2024-01-18"],
            "range": "R601-R610; R602 at subsection level, R603-R610 at section level",
            "granularity": "One unit per checkable obligation in R602; some sections split into parts (R602.3.1, R602.3.2, R602.6, R602.12.2, R602.12.6).",
            "section_list_status": "UNVERIFIED against the official 2021 text; R602 numbering cross-checked against 2018 VRC pages only.",
            "table_data_policy": "PENDING owner decision: only the specific table cells a rule or test needs are encoded, as bare values with applies_when conditions.",
            "not_a_pilot": "Example built from public sources; not a pilot or partner of any jurisdiction.",
        },
        "classification_method": {
            "data_check": "Can be decided from declared or structured attributes with no spatial computation.",
            "geometric_deterministic": "Can be decided by a deterministic computation on dimensions or model geometry, given the required information.",
            "judgment": "Needs engineering or official judgment and is never auto-decided.",
            "basis": "All check_class tags are ORI estimates (classification_basis=estimate).",
        },
        "class_split": split(units),
        "unit_count": len(units),
        "executable_unit_count": len(impl),
        "executable_with_verified_thresholds": sum(1 for u in impl if all(p["value_status"] != EST for p in u["jurisdiction_layers"][0].get("parameters", []))),
        "sources": SOURCES,
        "legal_boundary": {"machine_result_is_approval": False, "statement": "Rule units and machine results are reviewer evidence. They are not approval and are not the code."},
        "units": units,
    }


def table_md(col):
    units = col["units"]
    s = col["class_split"]
    n = col["unit_count"]
    impl = [u for u in units if u["evaluator"]["kind"] == "deterministic_function"]
    L = [
        "# 2021 IRC Chapter 6 (R601–R610) rule units with the 2021 VRC override layer (DRAFT)",
        "",
        "> **DRAFT.** Generated by `rules/irc2021/ch06/build_units.py`; do not edit by hand.",
        "> Example built from public sources; not a pilot or partner. Every machine result is reviewer evidence, not approval.",
        "> Source attribution only; no named source endorses or is affiliated with ORI.",
        "",
        "## What is sourced and what is an estimate",
        "",
        "- **Sourced (primary):** the Virginia layer, read from [13VAC5-63-210](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section210/) §310.8 items 62–64 on 2026-10-12, including every value on the Virginia practical-bracing units (R602.12.x).",
        "- **UNVERIFIED:** the section list and every IRC base value (`value_status: estimate`). ICC Digital Codes did not return the chapter text to an automated fetch. Rules return `unknown` (`threshold_unverified`) when the governing value is an estimate.",
        "- **Pending owner decision:** encoding table data. Only single cells needed by rules and tests are encoded.",
        "- **No code text:** descriptions are ORI labels; paraphrases are ORI summaries. Read the official text on [ICC Digital Codes](" + VRC_CH6_URL + ").",
        "",
        f"## Class split ({n} units, estimate)",
        "",
        "| class | units |",
        "|---|---:|",
    ]
    for k in ("data_check", "geometric_deterministic", "judgment"):
        L.append(f"| {k} | {s[k]} |")
    L += ["", f"Executable units: {len(impl)} (of which {col['executable_with_verified_thresholds']} rest on verified thresholds and can return pass or fail).", "",
          "## Executable units", "", "| unit | parameters (VA layer) | value status |", "|---|---|---|"]
    for u in impl:
        ps = u["jurisdiction_layers"][0].get("parameters", [])
        L.append(f"| {u['source_section']['section']} {u['source_section'].get('subsection_part', '')} | "
                 + "; ".join(f"{p['name']} {p['comparator']} {p['quantity']['value']} {p['quantity']['unit']}" for p in ps)
                 + f" | {', '.join(sorted({p['value_status'] for p in ps}))} |")
    L += ["", "## All units", "", "| # | section | part | ORI description | class | SF | VA mode | VA item | evaluator | interpretability |", "|---:|---|---|---|---|---|---|---|---|---|"]
    for i, u in enumerate(units, 1):
        l = u["jurisdiction_layers"][0]
        L.append(f"| {i} | {u['source_section']['section']} | {u['source_section'].get('subsection_part', '')} | {u['title']} | {u['check_class']} | "
                 f"{u['single_family_applicability']} | {l['override_mode']} | {(l['amendment_ref']['item'] or '').replace('310.8 ', '')} | {u['evaluator']['kind']} | "
                 f"{u.get('interpretability', {}).get('score', 'not scored')} |")
    L.append("")
    return "\n".join(L)


def render():
    col = collection(build())
    return json.dumps(col, indent=2, ensure_ascii=False) + "\n", table_md(col)


def main():
    j, m = render()
    OUT_JSON.write_text(j, encoding="utf-8")
    OUT_MD.write_text(m, encoding="utf-8")
    col = json.loads(j)
    print("units:", col["unit_count"], "split:", col["class_split"], "executable:", col["executable_unit_count"], "verified:", col["executable_with_verified_thresholds"])


if __name__ == "__main__":
    main()
