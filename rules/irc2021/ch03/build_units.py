#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the ORI Chapter 3 worked example (2021 IRC base + 2021 Virginia VRC layer).

DRAFT. This script is the single source of truth for
``va-vrc-2021-ch03.units.json`` and ``CHAPTER-3-TABLE.md``. Run it after editing
the tables below; ``rules/test_rules_data.py`` fails if the committed outputs
drift from what this script produces.

What is sourced and what is an estimate
---------------------------------------
* Section list: the 2021 VRC Chapter 3 section numbers as published by
  UpCodes ("Virginia Residential Code 2021 based on the IRC 2021"), fetched
  2026-09-27 (source:upcodes:vrc-2021-ch03).
* Virginia override mode: 13VAC5-63-210 (VCC section 310.8, "Amendments to the
  IRC"), fetched 2026-09-27 (source:va:13vac5-63-210). A section not in that
  list is recorded as ``adopts_base``, and that status is primary because the
  regulation is the official amendment list. Item numbers are ORI's count of
  the list entries in the order printed and should be checked against the
  regulation before citation.
* check_class tags: ORI analyst ESTIMATES (classification_basis=estimate).
  No published classification of the IRC exists (see
  research/geometric-verification-survey-2026-09-27.md).
* Numeric values appear only on the units that the reference evaluator
  implements. Each value has its own value_status.

* Interpretability (optional per unit): merged from the hand-maintained
  ``interpretability-ch03.json`` (rubric: spec/interpretability-0.1-draft.md).
  Scores are ORI PRE-SCORES (scoring_status=estimate) pending two independent
  human reviewers. Linked determinations are only records ORI fetched and read
  on 2026-09-28 (research/va-code-interpretations-sources-2026-09-28.md).

Citation policy (docs/CITATION-POLICY.md): ORI cites, paraphrases and links;
it never reproduces code text. Titles are ORI descriptions of each unit's
effect, not ICC section headings. Paraphrases are ORI's own words, kept in
``paraphrases-ch03.json``. Every unit carries ``source_url`` (the official
ICC Digital Codes page for the 2021 VRC chapter) and ``source_links`` (plus the
Virginia regulation on law.lis.virginia.gov where Virginia changes or adds the
section). Numeric thresholds are bare values only.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_JSON = HERE / "va-vrc-2021-ch03.units.json"
OUT_MD = HERE / "CHAPTER-3-TABLE.md"
INTERP_JSON = HERE / "interpretability-ch03.json"
PARA_JSON = HERE / "paraphrases-ch03.json"

# Official link-out targets (docs/CITATION-POLICY.md). ICC Digital Codes returns 403 to
# automated fetches; these chapter URLs were confirmed through a search index on 2026-09-28.
VRC_CH3_URL = "https://codes.iccsafe.org/content/VARC2021P1/chapter-3-building-planning"
IRC_CH3_URL = "https://codes.iccsafe.org/content/IRC2021P1/chapter-3-building-planning"
VAC_210_URL = "https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section210/"

RECORDED_AT = "2026-09-27"
RECORDED_BY = "ORI automated drafting agent (DRAFT, not yet human-reviewed)"
VA_JURISDICTION = "urn:ori:jurisdiction:us-va"
VA_EFFECTIVE = "2024-01-18"

SOURCES = [
    {
        "id": "source:icc:irc-2021",
        "type": "Source",
        "version": "1",
        "title": "2021 International Residential Code (model code)",
        "publisher": "International Code Council",
        "locator": IRC_CH3_URL,
        "edition": "2021",
        "authority_class": "model_code",
        "license_status": "ICC copyright; ORI cites section numbers, paraphrases and bare numeric values only and links to ICC Digital Codes",
        "retrieved_at": None,
        "metadata": {"note": "ICC Digital Codes returned 403 to automated fetches (2026-09-27 and 2026-09-28); the chapter URL was confirmed through a search index. Base values come from the secondary or inferred sources recorded per parameter."},
    },
    {
        "id": "source:icc:vrc-2021",
        "type": "Source",
        "version": "1",
        "title": "2021 Virginia Residential Code (IRC 2021 with Virginia amendments), ICC Digital Codes",
        "publisher": "International Code Council (for the Commonwealth of Virginia)",
        "locator": VRC_CH3_URL,
        "edition": "2021 VRC",
        "authority_class": "state_official_source",
        "license_status": "ICC copyright in the IRC text; link only",
        "retrieved_at": None,
        "metadata": {"note": "Official free-view link target for every unit's source_url. Direct fetch returned 403 on 2026-09-28; URL confirmed through a search index."},
    },
    {
        "id": "source:va:13vac5-63-210",
        "type": "Source",
        "version": "1",
        "title": "13VAC5-63-210, Virginia Construction Code Section 310 (Virginia Residential Code), including 310.8 Amendments to the IRC",
        "publisher": "Virginia Administrative Code (Code of Virginia via law.lis.virginia.gov)",
        "locator": "https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section210/",
        "edition": "2021 Virginia codes",
        "authority_class": "state_official_source",
        "license_status": "public law",
        "retrieved_at": "2026-09-27T00:00:00-04:00",
    },
    {
        "id": "source:va:codes-2021-effective",
        "type": "Source",
        "version": "1",
        "title": "Virginia Codes: 2021 codes effective January 18, 2024",
        "publisher": "Virginia DHCD",
        "locator": "https://www.dhcd.virginia.gov/codes",
        "edition": "2021",
        "authority_class": "state_official_source",
        "license_status": "public information",
        "retrieved_at": None,
        "metadata": {"reused_from": "ORI Fredericksburg public-source inventory (kept outside the public release)"},
    },
    {
        "id": "source:upcodes:vrc-2021-ch03",
        "type": "Source",
        "version": "1",
        "title": "Virginia Residential Code 2021 based on the IRC 2021, Chapter 3 Building Planning (UpCodes viewer)",
        "publisher": "UpCodes (third-party publisher)",
        "locator": "https://up.codes/viewer/virginia/irc-2021/chapter/3/building-planning",
        "edition": "2021 VRC",
        "authority_class": "secondary_publication",
        "license_status": "third-party publication; used for section list and short numeric values only",
        "retrieved_at": "2026-09-27T00:00:00-04:00",
    },
    {
        "id": "source:secondary:sma-2021-irc-visual",
        "type": "Source",
        "version": "1",
        "title": "Stairway Manufacturers' Association, 2021 IRC Visual Interpretation (hosted by Viewrail)",
        "publisher": "Stairway Manufacturers' Association",
        "locator": "https://www.viewrail.com/wp-content/uploads/2025/04/2021-International-Residential-Code-Visual-Interpretation.pdf",
        "edition": "2021 IRC",
        "authority_class": "secondary_publication",
        "license_status": "third-party publication; short numeric values only",
        "retrieved_at": "2026-09-27T00:00:00-04:00",
    },
    {
        "id": "source:secondary:roy-city-egress-2021",
        "type": "Source",
        "version": "1",
        "title": "Roy City, Utah: 2021 IRC Building Code Overview, Egress Windows (handout)",
        "publisher": "Roy City, Utah",
        "locator": "https://cms7files1.revize.com/roycityut/Departments/building%20permits%20inspections/handouts/IRC%20Egress%20windows%202021.pdf",
        "edition": "2021 IRC",
        "authority_class": "local_official_source",
        "license_status": "public handout; short numeric values only",
        "retrieved_at": "2026-09-27T00:00:00-04:00",
        "metadata": {"note": "Text read through the search index; the PDF is image-based."},
    },
    {
        "id": "source:va:sbctrb-decisions",
        "type": "Source",
        "version": "1",
        "title": "Virginia State Building Code Technical Review Board: appeal decisions (SBCTRB Decisions page and linked final orders)",
        "publisher": "Virginia DHCD",
        "locator": "https://www.dhcd.virginia.gov/sbctrb-decisions",
        "edition": "decisions 2004-2026 as listed",
        "authority_class": "state_official_source",
        "license_status": "public records",
        "retrieved_at": "2026-09-28T00:00:00-04:00",
    },
    {
        "id": "source:va:sbctrb-interpretations-2021",
        "type": "Source",
        "version": "1",
        "title": "SBCTRB Interpretation Booklet: interpretations applicable to the 2021 editions of the USBC and SFPC (September 2026)",
        "publisher": "Virginia DHCD",
        "locator": "https://www.dhcd.virginia.gov/sites/default/files/DocX/sbctrb/interpretations-booklets/trb-2021-interpretation-booklet.pdf",
        "edition": "2021 USBC",
        "authority_class": "state_official_source",
        "license_status": "public records",
        "retrieved_at": "2026-09-28T00:00:00-04:00",
    },
    {
        "id": "source:va:dhcd-informational-documents",
        "type": "Source",
        "version": "1",
        "title": "DHCD informational documents and publications (technical memos, SBCO code opinions)",
        "publisher": "Virginia DHCD",
        "locator": "https://www.dhcd.virginia.gov/informational-documents-and-publications",
        "edition": "various",
        "authority_class": "state_official_source",
        "license_status": "public information; staff opinions are not binding",
        "retrieved_at": "2026-09-28T00:00:00-04:00",
    },
    {
        "id": "source:va:pwc-bdd-policies",
        "type": "Source",
        "version": "1",
        "title": "Prince William County Building Development Division: Policies and Procedures",
        "publisher": "Prince William County, Virginia",
        "locator": "https://www.pwcva.gov/department/building-development-division/policies-procedures",
        "edition": "policies as posted",
        "authority_class": "local_official_source",
        "license_status": "public information; binding only in Prince William County",
        "retrieved_at": "2026-09-28T00:00:00-04:00",
    },
]

DET_SOURCE = {
    "state_review_board_interpretation": "source:va:sbctrb-interpretations-2021",
    "state_review_board_appeal_decision": "source:va:sbctrb-decisions",
    "state_agency_staff_opinion": "source:va:dhcd-informational-documents",
    "local_building_official_policy": "source:va:pwc-bdd-policies",
}

# Virginia amendment items for Chapter 3 in 13VAC5-63-210 section 310.8.
# key: section (optionally "section|part"), value: (override_mode, item, note)
VA_AMENDMENTS = {
    "R301.2.1": ("modifies_text", "3", "Adds a Virginia paragraph on special wind regions."),
    "R302.1": ("adds_exception", "4", "Adds Exception 6 (decks and open porches) and Exception 7 (lots where setbacks bar walls closer than 10 ft)."),
    "R302.1|Table R302.1(1) Projections row": ("replaces_value", "5", "Changes the Projections row of Table R302.1(1)."),
    "R302.2.6": ("adds_exception", "6", "Adds Exception 6 on townhouse sprinkler penetrations."),
    "R302.3": ("modifies_text", "7", "Changes two-family separation; Exception 3 relates to accessory dwelling units (outside ORI scope)."),
    "R302.5.1": ("modifies_text", "8", "Changes garage opening protection (door ratings)."),
    "R302.13": ("deletes", "9", "Virginia deletes this section."),
    "R303.10": ("adds_exception", "10", "Adds an exception to required heating."),
    "R303.10.1": ("adds_section", "11", "Adds a Virginia subsection to required heating."),
    "R303.11": ("adds_section", "12", "Adds insect screens."),
    "R306.5": ("adds_section", "13", "Adds a subsection on water sources and sewage disposal."),
    "R308.4.5": ("modifies_text", "14", "Changes glazing and wet surfaces (60 in value)."),
    "R310.1": ("modifies_text", "15", "Changes EERO-required text (basements, habitable attics, sleeping rooms; 36 in yard or court)."),
    "R310.2.1": ("replaces_section", "16", "Rewrites R310.2.1 to carry the area, height and width minimums and the grade-floor or below-grade exception."),
    "R310.2.2": ("deletes", "16", "Deleted; its dimensions move into R310.2.1."),
    "R311.1": ("modifies_text", "17", "Changes the means of egress general text."),
    "R311.3.1": ("adds_exception", "18", "Exception using 8-1/4 in."),
    "R311.3.2": ("replaces_value", "19", "Uses 8-1/4 in."),
    "R311.7.5.1": ("replaces_value", "20", "Maximum riser 8-1/4 in (base model 7-3/4 in)."),
    "R311.7.5.2": ("replaces_value", "21", "Minimum tread 9 in (base model 10 in)."),
    "R312.2.1": ("modifies_text", "22", "Changes window sill fall-protection text (18 in / 72 in values)."),
    "R313": ("replaces_section", "23", "Replaces R313: sprinklers are not required; the provisions apply only where a system is installed."),
    "R314.2.2": ("deletes", "24", "Deletes smoke alarms in alterations."),
    "R314.6": ("modifies_text", "25", "Changes smoke alarm power source."),
    "R314.7": ("modifies_text", "26", "Changes fire alarm systems."),
    "R314.7.3": ("modifies_text", "27", "Changes R314.7.3."),
    "R315.1.1": ("modifies_text", "28", "Changes CO alarm listing."),
    "R315.2": ("modifies_text", "29", "Changes where CO alarms are required."),
    "R315.2.2": ("deletes", "30", "Deletes CO alarms in alterations."),
    "R315.5": ("modifies_text", "31", "Changes CO interconnectivity."),
    "R315.6": ("deletes", "32", "Deletes R315.6."),
    "R315.7.3": ("modifies_text", "33", "Changes R315.7.3."),
    "R320.3": ("adds_section", "34", "Adds universal design features."),
    "R322.1": ("modifies_text", "35", "Item 35 changes R322.1.5 (lowest floor) and R322.1.8 (flood-resistant materials; FEMA TB-2 and ASCE 24). Mapping read from 13VAC5-63-210 on 2026-09-28."),
    "R322.2": ("modifies_text", "35-36", "Item 35 changes R322.2 (Coastal A / V zone designation at 1-1/2 ft wave height); item 36 changes item 4.2 of R322.2.1 (enclosed garages and carports). Mapping read from 13VAC5-63-210 on 2026-09-28."),
    "R322.3": ("modifies_text", "37-38", "Item 37 changes R322.3.1 (location and site preparation); item 38 changes R322.3.6 (bars enclosures below the design flood elevation in Coastal A and V zones) and R322.3.10 (tanks). Mapping read from 13VAC5-63-210 on 2026-09-28."),
    "R324.6.2": ("replaces_value", "39", "Ridge setback 18 in."),
    "R326.3": ("modifies_text", "40", "Changes habitable attic story classification."),
}

# (section, part-or-None, short ORI title, class, single-family applicability)
# D=data_check  G=geometric_deterministic  J=judgment
UNITS = [
    ("R301.1", None, "Structure must carry all loads to the foundation", "J", "applies"),
    ("R301.1.3", None, "Engineering required beyond prescriptive limits", "J", "conditional"),
    ("R301.2", None, "Local climatic and geographic design data", "D", "applies"),
    ("R301.2.1", None, "Wind design speed and wind-design triggers", "D", "applies"),
    ("R301.2.1.4", None, "Choosing the wind exposure category", "J", "applies"),
    ("R301.2.2", None, "Seismic design category limits", "D", "applies"),
    ("R301.2.3", None, "Ground snow load basis", "D", "applies"),
    ("R301.2.4", None, "Flood hazard areas trigger flood provisions", "D", "conditional"),
    ("R301.3", None, "Limits on story height", "G", "applies"),
    ("R301.4", None, "Dead loads counted in design", "J", "applies"),
    ("R301.5", None, "Minimum live loads by space use", "D", "applies"),
    ("R301.6", None, "Minimum roof live loads", "D", "applies"),
    ("R301.7", None, "Allowable deflection of members", "J", "applies"),
    ("R301.8", None, "Dimensions are nominal unless stated", "D", "applies"),
    ("R302.1", None, "Exterior wall fire rating by distance to lot line", "G", "applies"),
    ("R302.1", "Table R302.1(1) Projections row", "Eave and projection limits near the lot line", "G", "applies"),
    ("R302.2", None, "Separation between townhouse units", "D", "out_of_scope"),
    ("R302.2.6", None, "Townhouse structural independence", "D", "out_of_scope"),
    ("R302.3", None, "Separation between two-family units", "D", "out_of_scope"),
    ("R302.4", None, "Penetrations of unit separations", "D", "out_of_scope"),
    ("R302.5.1", None, "Door between garage and house", "D", "applies"),
    ("R302.5.2", None, "Ducts that pass through garage separations", "D", "applies"),
    ("R302.5.3", None, "Sealing other openings in garage separations", "J", "applies"),
    ("R302.6", None, "Garage-to-house fire separation", "D", "applies"),
    ("R302.7", None, "Gypsum protection under enclosed stairs", "D", "applies"),
    ("R302.8", None, "Foam plastic cross-reference", "D", "applies"),
    ("R302.9", None, "Interior finish flame spread limits", "D", "applies"),
    ("R302.10", None, "Insulation flame spread limits", "D", "applies"),
    ("R302.11", None, "Fireblocking of concealed draft paths", "J", "applies"),
    ("R302.12", None, "Draftstopping in floor-ceiling spaces", "G", "applies"),
    ("R302.13", None, "Membrane protection of floors (deleted in Virginia)", "D", "applies"),
    ("R302.14", None, "Keeping insulation away from heat sources", "D", "applies"),
    ("R303.1", None, "Daylight and fresh air for habitable rooms", "G", "applies"),
    ("R303.2", None, "Borrowing light and air from an adjoining room", "G", "applies"),
    ("R303.3", None, "Bathroom window or exhaust fan", "G", "applies"),
    ("R303.4", None, "When whole-house ventilation is required", "D", "applies"),
    ("R303.5", None, "Separation of air intakes from contaminant sources", "G", "applies"),
    ("R303.6", None, "Screens on air intake and exhaust openings", "D", "applies"),
    ("R303.7", None, "Lighting for interior stairs", "D", "applies"),
    ("R303.8", None, "Lighting for exterior stairs", "D", "applies"),
    ("R303.9", None, "Glazing that faces a yard or court", "G", "applies"),
    ("R303.10", None, "Heating to a minimum indoor temperature", "D", "applies"),
    ("R303.10.1", None, "Heat in rented dwellings during the heating season (Virginia)", "D", "applies"),
    ("R303.11", None, "Insect screens on ventilation openings (Virginia)", "D", "applies"),
    ("R304.1", None, "Minimum floor area of habitable rooms", "G", "applies"),
    ("R304.2", None, "Minimum width of habitable rooms", "G", "applies"),
    ("R304.3", None, "Low-ceiling floor area not counted", "G", "applies"),
    ("R305.1", "habitable", "Ceiling height in living spaces and halls", "G", "applies"),
    ("R305.1", "bath-toilet-laundry", "Ceiling height in bathrooms and laundries", "G", "applies"),
    ("R305.1", "Exception 1 sloped ceilings", "Sloped ceilings: partial-height allowance", "G", "conditional"),
    ("R305.1", "Exception 2 fixtures and showers", "Headroom at fixtures and showers", "G", "applies"),
    ("R305.1", "Exception 3 beams and obstructions", "Allowance for beams and ducts below ceilings", "G", "conditional"),
    ("R305.1.1", None, "Ceiling height in basements", "G", "conditional"),
    ("R306.1", None, "A toilet, lavatory and tub or shower required", "D", "applies"),
    ("R306.2", None, "A kitchen sink required", "D", "applies"),
    ("R306.3", None, "Fixtures connected to sewage disposal", "D", "applies"),
    ("R306.4", None, "Hot and cold water to fixtures", "D", "applies"),
    ("R306.5", None, "Connection to water and sewer; health-department approval (Virginia)", "D", "applies"),
    ("R307.1", None, "Clear space around plumbing fixtures", "G", "applies"),
    ("R307.2", None, "Water-resistant walls at tubs and showers", "D", "applies"),
    ("R308.1", None, "Marking of safety glazing", "D", "applies"),
    ("R308.2", None, "Louvered and jalousie glass limits", "D", "applies"),
    ("R308.3", None, "Impact test standard for safety glazing", "D", "applies"),
    ("R308.4.1", None, "Safety glazing in doors", "D", "applies"),
    ("R308.4.2", None, "Safety glazing beside doors", "G", "applies"),
    ("R308.4.3", None, "Safety glazing in large low windows", "G", "applies"),
    ("R308.4.4", None, "Safety glazing used in guards", "D", "applies"),
    ("R308.4.5", None, "Safety glazing near tubs, pools and wet areas", "G", "applies"),
    ("R308.4.6", None, "Safety glazing near stairs and ramps", "G", "applies"),
    ("R308.4.7", None, "Safety glazing by the lowest stair landing", "G", "applies"),
    ("R308.5", None, "Site-built window design", "J", "conditional"),
    ("R308.6", None, "Skylight and sloped glass requirements", "D", "conditional"),
    ("R309.1", None, "Garage floor material and slope", "D", "applies"),
    ("R309.2", None, "Carports open on sides", "D", "conditional"),
    ("R309.3", None, "Garages in flood areas", "D", "conditional"),
    ("R309.4", None, "Garage door opener safety listing", "D", "conditional"),
    ("R309.5", None, "Sprinklers in garages (where installed)", "D", "conditional"),
    ("R310.1", None, "Where emergency escape openings are required", "D", "applies"),
    ("R310.1", "yard or court width", "Escape openings must reach a wide enough yard or court", "G", "applies"),
    ("R310.2.1", "net clear area", "Escape opening: minimum clear area", "G", "applies"),
    ("R310.2.1", "net clear height", "Escape opening: minimum clear height", "G", "applies"),
    ("R310.2.1", "net clear width", "Escape opening: minimum clear width", "G", "applies"),
    ("R310.2.2", None, "Escape opening dimensions (moved in Virginia)", "G", "applies"),
    ("R310.2.3", None, "Escape opening: maximum sill height", "G", "applies"),
    ("R310.2.4", None, "Escape path from openings beneath decks", "G", "conditional"),
    ("R310.2.5", None, "Escape openings must open without special effort", "D", "applies"),
    ("R310.3", None, "Doors used as escape openings", "D", "conditional"),
    ("R310.4.1", None, "Minimum size of an area well", "G", "conditional"),
    ("R310.4.2", None, "Ladder or steps in deep area wells", "G", "conditional"),
    ("R310.4.3", None, "Drainage of area wells", "J", "conditional"),
    ("R310.4.4", None, "Covers and grates over area wells", "D", "conditional"),
    ("R310.5", None, "Replacing windows that serve as escape openings", "D", "conditional"),
    ("R310.6", None, "Additions and escape openings", "D", "conditional"),
    ("R310.7", None, "Existing basements: when escape openings are required", "D", "conditional"),
    ("R311.1", None, "Continuous exit path to the outside", "J", "applies"),
    ("R311.2", None, "Required exit door size and type", "G", "applies"),
    ("R311.3", None, "Exterior door landings: size and slope", "G", "applies"),
    ("R311.3.1", None, "Landing drop at the required exit door", "G", "applies"),
    ("R311.3.2", None, "Landing drop at other exterior doors", "G", "applies"),
    ("R311.3.3", None, "Storm and screen doors over landings", "D", "applies"),
    ("R311.4", None, "Egress from upper and lower floors", "D", "applies"),
    ("R311.5", None, "Anchoring exterior landings, decks and stairs", "J", "conditional"),
    ("R311.6", None, "Hallway width", "G", "applies"),
    ("R311.7.1", None, "Stair width", "G", "applies"),
    ("R311.7.2", None, "Stair headroom", "G", "applies"),
    ("R311.7.3", None, "Maximum rise of one stair flight", "G", "applies"),
    ("R311.7.4", None, "Where stair walkline is measured", "G", "conditional"),
    ("R311.7.5.1", "maximum riser", "Stair riser height maximum", "G", "applies"),
    ("R311.7.5.1", "riser uniformity", "Stair riser height uniformity within a flight", "G", "applies"),
    ("R311.7.5.2", "minimum tread", "Stair tread depth minimum", "G", "applies"),
    ("R311.7.5.2", "tread uniformity", "Stair tread depth uniformity within a flight", "G", "applies"),
    ("R311.7.5.2.1", None, "Winder tread depth limits", "G", "conditional"),
    ("R311.7.5.3", None, "Nosing projection and uniformity", "G", "applies"),
    ("R311.7.5.4", None, "Plastic composite exterior treads", "D", "conditional"),
    ("R311.7.6", None, "Stair landings (top and foot)", "G", "applies"),
    ("R311.7.7", None, "Slope of stair treads and landings", "G", "applies"),
    ("R311.7.8", None, "Handrails: where needed and how high", "G", "applies"),
    ("R311.7.8.3", None, "Handrail grip size", "G", "applies"),
    ("R311.7.8.4", None, "Handrail continuity along the flight", "G", "applies"),
    ("R311.7.9", None, "Stair lighting cross-reference", "D", "applies"),
    ("R311.7.10", None, "Spiral and bulkhead stairs", "G", "conditional"),
    ("R311.7.11", None, "Alternating-tread stairs (limited use)", "G", "conditional"),
    ("R311.7.12", None, "Ships ladders", "G", "conditional"),
    ("R311.8", None, "Ramps: slope and landings", "G", "conditional"),
    ("R311.8.3", None, "Handrails on ramps", "G", "conditional"),
    ("R312.1.1", None, "When a guard is required", "G", "applies"),
    ("R312.1.2", "general", "Guard minimum height", "G", "applies"),
    ("R312.1.2", "Exceptions stairs", "Guard height along open stair sides", "G", "applies"),
    ("R312.1.3", None, "Guard opening limits", "G", "applies"),
    ("R312.1.4", None, "Plastic composite exterior guards", "D", "conditional"),
    ("R312.2.1", None, "Window fall protection trigger", "G", "applies"),
    ("R312.2.2", None, "Window opening control devices", "D", "conditional"),
    ("R313.1", None, "Townhouse sprinklers (not required in Virginia)", "D", "out_of_scope"),
    ("R313.2", None, "House sprinklers (not required in Virginia)", "D", "applies"),
    ("R314.1", None, "Smoke alarms must be listed", "D", "applies"),
    ("R314.2", None, "When smoke alarms are required", "D", "applies"),
    ("R314.2.2", None, "Smoke alarms after alterations (deleted in Virginia)", "D", "conditional"),
    ("R314.3", None, "Smoke alarm locations", "D", "applies"),
    ("R314.3.1", None, "Smoke alarm distance from kitchens and baths", "G", "applies"),
    ("R314.4", None, "Interconnected smoke alarms", "D", "applies"),
    ("R314.5", None, "Combination smoke and CO alarms", "D", "conditional"),
    ("R314.6", None, "Smoke alarm power supply", "D", "applies"),
    ("R314.7", None, "Fire alarm systems in place of alarms", "D", "conditional"),
    ("R314.7.3", None, "Installed fire alarm system stays with the house (Virginia)", "D", "conditional"),
    ("R315.1", None, "Carbon monoxide alarms: general", "D", "conditional"),
    ("R315.1.1", None, "CO alarm listing standard", "D", "conditional"),
    ("R315.2", None, "When CO alarms are required", "D", "applies"),
    ("R315.2.2", None, "CO alarms after alterations (deleted in Virginia)", "D", "conditional"),
    ("R315.3", None, "CO alarm locations", "D", "conditional"),
    ("R315.4", None, "Combination CO and smoke alarms", "D", "conditional"),
    ("R315.5", None, "CO alarm interconnection", "D", "conditional"),
    ("R315.6", None, "CO alarm power (deleted in Virginia)", "D", "conditional"),
    ("R315.7", None, "CO detection systems in place of alarms", "D", "conditional"),
    ("R315.7.3", None, "Installed CO detection system stays with the house (Virginia)", "D", "conditional"),
    ("R316.1", None, "Foam plastic: scope", "D", "conditional"),
    ("R316.2", None, "Foam plastic labels", "D", "conditional"),
    ("R316.3", None, "Foam plastic flame spread limits", "D", "conditional"),
    ("R316.4", None, "Thermal barrier over foam plastic", "D", "conditional"),
    ("R316.5", None, "Cases where foam may omit the barrier", "D", "conditional"),
    ("R316.6", None, "Foam accepted by special testing", "J", "conditional"),
    ("R316.7", None, "Termite protection for foam plastic", "D", "conditional"),
    ("R316.8", None, "Foam sheathing wind resistance", "D", "conditional"),
    ("R317.1", None, "Where decay-resistant wood is required", "G", "applies"),
    ("R317.2", None, "Quality mark on treated wood", "D", "applies"),
    ("R317.3", None, "Fasteners in treated wood", "D", "applies"),
    ("R317.4", None, "Plastic composite decking and trim", "D", "conditional"),
    ("R318.1", None, "Termite protection methods", "D", "conditional"),
    ("R318.2", None, "Chemical soil treatment for termites", "D", "conditional"),
    ("R318.3", None, "Physical termite barriers", "D", "conditional"),
    ("R318.4", None, "Foam plastic in heavy termite areas", "D", "conditional"),
    ("R319.1", None, "House numbers visible from the street", "D", "applies"),
    ("R320.1", None, "Accessibility scope", "D", "conditional"),
    ("R320.2", None, "Live/work units (outside ORI scope)", "D", "out_of_scope"),
    ("R320.3", None, "Optional universal design features (Virginia)", "D", "conditional"),
    ("R321.1", None, "Residential elevators", "D", "conditional"),
    ("R321.2", None, "Platform lifts", "D", "conditional"),
    ("R321.3", None, "Accessible elevators and lifts", "D", "conditional"),
    ("R322.1", None, "Flood-resistant construction: basis", "D", "conditional"),
    ("R322.2", None, "Flood zone elevation (A zones)", "G", "conditional"),
    ("R322.3", None, "Coastal high-hazard (V zone) construction", "J", "conditional"),
    ("R323.1", None, "Storm shelters", "J", "conditional"),
    ("R324.1", None, "Solar energy systems: scope", "D", "conditional"),
    ("R324.2", None, "Solar thermal system installation", "D", "conditional"),
    ("R324.3", None, "Listed photovoltaic equipment", "D", "conditional"),
    ("R324.4", None, "Roof structure for rooftop PV", "J", "conditional"),
    ("R324.5", None, "PV built into the roof", "D", "conditional"),
    ("R324.6", None, "Roof access paths around PV arrays", "G", "conditional"),
    ("R324.6.2", None, "PV setback from the ridge", "G", "conditional"),
    ("R324.7", None, "Ground-mounted PV", "D", "conditional"),
    ("R325.1", None, "Mezzanines: scope", "D", "conditional"),
    ("R325.2", None, "Headroom above and below mezzanines", "G", "conditional"),
    ("R325.3", None, "Mezzanine area limit", "G", "conditional"),
    ("R325.4", None, "Egress from mezzanines", "D", "conditional"),
    ("R325.5", None, "Mezzanine must be open", "G", "conditional"),
    ("R326.1", None, "Habitable attics: scope", "D", "conditional"),
    ("R326.2", None, "Habitable attic size and height", "G", "conditional"),
    ("R326.3", None, "When a habitable attic counts as a story", "D", "conditional"),
    ("R326.4", None, "Egress from habitable attics", "D", "conditional"),
    ("R327.1", None, "Pools, spas and hot tubs", "D", "conditional"),
]

# Virginia-added sections outside the R301-R327 range (13VAC5-63-210 items 41-53).
VA_ADDED_SECTIONS = [
    ("R331", "Radon-resistant construction where a locality adopts it (Virginia)", "D"),
    ("R332", "Patio covers (Virginia)", "J"),
    ("R333", "Sound isolation between units; airport noise zones (Virginia)", "D"),
    ("R334", "Kitchen fire extinguisher unless sprinklered (Virginia)", "D"),
    ("R335", "Interior passage width to kitchen, living area and bath (Virginia)", "G"),
    ("R336", "Tiny houses (Virginia)", "J"),
]

CLASS = {"D": "data_check", "G": "geometric_deterministic", "J": "judgment"}

# Parameters for the units the reference evaluator implements.
# key: (section, part) -> dict(fn, base=[...], va=[...] or None, inputs, info, ids)
def P(name, comparator, value, unit, status, source, si=None, applies_when=None, detail=None):
    q = {"value": value, "unit": unit}
    if si:
        q["si_informational"] = si
    p = {"name": name, "comparator": comparator, "quantity": q, "value_status": status, "source": source}
    if applies_when:
        p["applies_when"] = applies_when
    if detail:
        p["locator_detail"] = detail
    return p

UP = "source:upcodes:vrc-2021-ch03"
VA = "source:va:13vac5-63-210"
SMA = "source:secondary:sma-2021-irc-visual"
ROY = "source:secondary:roy-city-egress-2021"
INF = "inferred_unamended"

IMPLEMENTED = {
    ("R311.7.5.1", "maximum riser"): dict(
        fn="riser_height_max", slug="riser-height-max",
        base=[P("max_riser_height", "<=", 7.75, "in", "sourced_secondary", SMA, "196 mm")],
        va=[P("max_riser_height", "<=", 8.25, "in", "sourced_primary", VA, "210 mm", detail="310.8 item 20")],
        inputs=[("riser_heights", "length_list", "in", True)],
        info=[("stair.flight.riser_heights", "Individual riser heights of each flight", "IfcStairFlight body profile (stepped extrusion) or Pset_StairFlightCommon.RiserHeight", "stairs[].riser_heights_in", "Stair section or detail sheet with riser dimension")],
        ids="rules/irc2021/ch03/ids/ori-ch03-stairs.ids#Stair flights carry measurable geometry", entity="IfcStairFlight"),
    ("R311.7.5.1", "riser uniformity"): dict(
        fn="riser_uniformity", slug="riser-uniformity",
        base=[P("max_riser_variation", "<=", 0.375, "in", "sourced_secondary", SMA, "9.5 mm")],
        va=[P("max_riser_variation", "<=", 0.375, "in", "sourced_primary", VA, "9.5 mm", detail="310.8 item 20")],
        inputs=[("riser_heights", "length_list", "in", True)],
        info=[("stair.flight.riser_heights", "Individual riser heights of each flight", "IfcStairFlight body profile", "stairs[].riser_heights_in", "Stair section with every riser dimensioned or a uniform-riser note")],
        ids="rules/irc2021/ch03/ids/ori-ch03-stairs.ids#Stair flights carry measurable geometry", entity="IfcStairFlight"),
    ("R311.7.5.2", "minimum tread"): dict(
        fn="tread_depth_min", slug="tread-depth-min",
        base=[P("min_tread_depth", ">=", 10, "in", "sourced_secondary", SMA, "254 mm")],
        va=[P("min_tread_depth", ">=", 9, "in", "sourced_primary", VA, "229 mm", detail="310.8 item 21")],
        inputs=[("tread_depths", "length_list", "in", True)],
        info=[("stair.flight.tread_depths", "Individual tread depths of each flight", "IfcStairFlight body profile or Pset_StairFlightCommon.TreadLength", "stairs[].tread_depths_in", "Stair section or detail sheet with tread dimension")],
        ids="rules/irc2021/ch03/ids/ori-ch03-stairs.ids#Stair flights carry measurable geometry", entity="IfcStairFlight"),
    ("R311.7.5.2", "tread uniformity"): dict(
        fn="tread_uniformity", slug="tread-uniformity",
        base=[P("max_tread_variation", "<=", 0.375, "in", "sourced_secondary", SMA, "9.5 mm")],
        va=[P("max_tread_variation", "<=", 0.375, "in", "sourced_primary", VA, "9.5 mm", detail="310.8 item 21")],
        inputs=[("tread_depths", "length_list", "in", True)],
        info=[("stair.flight.tread_depths", "Individual tread depths of each flight", "IfcStairFlight body profile", "stairs[].tread_depths_in", "Stair section with every tread dimensioned or a uniform-tread note")],
        ids="rules/irc2021/ch03/ids/ori-ch03-stairs.ids#Stair flights carry measurable geometry", entity="IfcStairFlight"),
    ("R311.7.2", None): dict(
        fn="stair_headroom_min", slug="stair-headroom-min",
        base=[P("min_headroom", ">=", 80, "in", INF, UP, "2032 mm", detail="6 ft 8 in; VRC text unamended, so equal to the IRC base")],
        va=None,
        inputs=[("headroom_clearances", "length_list", "in", True)],
        info=[("stair.flight.headroom", "Vertical clearance from nosing line to the lowest overhead element", "IfcStairFlight nosing points versus IfcSlab/IfcCovering underside overlapping in plan", "stairs[].min_headroom_in", "Building section through the stair showing headroom dimension")],
        ids="rules/irc2021/ch03/ids/ori-ch03-stairs.ids#Stair flights carry measurable geometry", entity="IfcStairFlight"),
    ("R305.1", "habitable"): dict(
        fn="ceiling_height_min", slug="ceiling-height-habitable",
        base=[P("min_ceiling_height", ">=", 84, "in", INF, UP, "2134 mm", detail="7 ft; VRC text unamended")],
        va=None,
        inputs=[("ceiling_height", "length", "in", True), ("space_use", "enum", None, True), ("sloped_ceiling", "boolean", None, False)],
        info=[("space.ceiling_height", "Finished floor to finished ceiling height", "IfcSpace body extrusion (top minus bottom elevation)", "spaces[].ceiling_height_in", "Building section or room schedule with ceiling height"),
              ("space.use", "Room use category (habitable, bathroom, toilet, laundry, kitchen, hallway, other)", "Pset_ORI_SpaceUse.UseCategory", "spaces[].use", "Floor plan room labels")],
        ids="rules/irc2021/ch03/ids/ori-ch03-spaces.ids#Spaces declare ORI use category", entity="IfcSpace"),
    ("R305.1", "bath-toilet-laundry"): dict(
        fn="ceiling_height_min", slug="ceiling-height-bath-toilet-laundry",
        base=[P("min_ceiling_height", ">=", 80, "in", INF, UP, "2032 mm", detail="6 ft 8 in; VRC text unamended")],
        va=None,
        inputs=[("ceiling_height", "length", "in", True), ("space_use", "enum", None, True), ("sloped_ceiling", "boolean", None, False)],
        info=[("space.ceiling_height", "Finished floor to finished ceiling height", "IfcSpace body extrusion", "spaces[].ceiling_height_in", "Building section or room schedule"),
              ("space.use", "Room use category", "Pset_ORI_SpaceUse.UseCategory", "spaces[].use", "Floor plan room labels")],
        ids="rules/irc2021/ch03/ids/ori-ch03-spaces.ids#Spaces declare ORI use category", entity="IfcSpace"),
    ("R304.1", None): dict(
        fn="room_area_min", slug="room-area-min",
        base=[P("min_habitable_room_area", ">=", 70, "ft2", INF, UP, "6.5 m2", detail="VRC text unamended; kitchens excepted")],
        va=None,
        inputs=[("floor_area", "area", "ft2", True), ("space_use", "enum", None, True)],
        info=[("space.floor_area", "Net floor area of the room", "IfcSpace footprint area from geometry", "spaces[].floor_area_ft2", "Floor plan with room dimensions or area schedule"),
              ("space.use", "Room use category", "Pset_ORI_SpaceUse.UseCategory", "spaces[].use", "Floor plan room labels")],
        ids="rules/irc2021/ch03/ids/ori-ch03-spaces.ids#Spaces declare ORI use category", entity="IfcSpace"),
    ("R310.2.1", "net clear area"): dict(
        fn="eero_net_clear_area", slug="eero-net-clear-area",
        base=[P("min_net_clear_area", ">=", 5.7, "ft2", "sourced_secondary", ROY, "0.530 m2"),
              P("min_net_clear_area_grade_floor", ">=", 5.0, "ft2", "sourced_secondary", ROY, "0.465 m2", applies_when="grade_floor_or_below_grade == true")],
        va=[P("min_net_clear_area", ">=", 5.7, "ft2", "sourced_primary", VA, "0.530 m2", detail="310.8 item 16"),
            P("min_net_clear_area_grade_floor", ">=", 5.0, "ft2", "sourced_primary", VA, "0.465 m2", applies_when="grade_floor_or_below_grade == true", detail="310.8 item 16")],
        inputs=[("net_clear_height", "length", "in", True), ("net_clear_width", "length", "in", True), ("net_clear_area", "area", "ft2", False), ("grade_floor_or_below_grade", "boolean", None, True)],
        info=[("eero.net_clear", "Net clear opening height and width (or area) in normal operation, not rough or overall size", "Pset_ORI_EscapeOpening.NetClearHeight/NetClearWidth/NetClearArea", "eeros[].net_clear_*", "Window schedule with net clear opening (manufacturer data)"),
              ("eero.grade_floor", "Whether the opening is at grade floor or below grade", "Pset_ORI_EscapeOpening.GradeFloorOrBelowGrade", "eeros[].grade_floor_or_below_grade", "Elevations or window schedule")],
        ids="rules/irc2021/ch03/ids/ori-ch03-eero.ids#Escape openings declare net clear dimensions", entity="IfcWindow"),
    ("R310.2.1", "net clear height"): dict(
        fn="eero_net_clear_height", slug="eero-net-clear-height",
        base=[P("min_net_clear_height", ">=", 24, "in", "sourced_secondary", ROY, "610 mm", detail="base model carries this in R310.2.2")],
        va=[P("min_net_clear_height", ">=", 24, "in", "sourced_primary", VA, "610 mm", detail="310.8 item 16 (moved into R310.2.1)")],
        inputs=[("net_clear_height", "length", "in", True)],
        info=[("eero.net_clear", "Net clear opening height in normal operation", "Pset_ORI_EscapeOpening.NetClearHeight", "eeros[].net_clear_height_in", "Window schedule")],
        ids="rules/irc2021/ch03/ids/ori-ch03-eero.ids#Escape openings declare net clear dimensions", entity="IfcWindow"),
    ("R310.2.1", "net clear width"): dict(
        fn="eero_net_clear_width", slug="eero-net-clear-width",
        base=[P("min_net_clear_width", ">=", 20, "in", "sourced_secondary", ROY, "508 mm", detail="base model carries this in R310.2.2")],
        va=[P("min_net_clear_width", ">=", 20, "in", "sourced_primary", VA, "508 mm", detail="310.8 item 16 (moved into R310.2.1)")],
        inputs=[("net_clear_width", "length", "in", True)],
        info=[("eero.net_clear", "Net clear opening width in normal operation", "Pset_ORI_EscapeOpening.NetClearWidth", "eeros[].net_clear_width_in", "Window schedule")],
        ids="rules/irc2021/ch03/ids/ori-ch03-eero.ids#Escape openings declare net clear dimensions", entity="IfcWindow"),
    ("R310.2.3", None): dict(
        fn="eero_sill_height_max", slug="eero-sill-height-max",
        base=[P("max_sill_height", "<=", 44, "in", INF, UP, "1118 mm", detail="VRC text unamended")],
        va=None,
        inputs=[("sill_height", "length", "in", True)],
        info=[("eero.sill_height", "Sill height: finished floor up to the lowest point of the clear opening", "IfcWindow placement elevation minus containing storey or space floor elevation, plus Pset_ORI_EscapeOpening.SillToClearOpeningOffset if the frame raises the clear opening", "eeros[].sill_height_in", "Elevation or window schedule with sill height")],
        ids="rules/irc2021/ch03/ids/ori-ch03-eero.ids#Escape openings declare net clear dimensions", entity="IfcWindow"),
    ("R312.1.1", None): dict(
        fn="guard_required", slug="guard-required",
        base=[P("guard_trigger_drop", ">", 30, "in", INF, UP, "762 mm", detail="drop measured within 36 in horizontally of the open edge; VRC text unamended"),
              P("guard_trigger_horizontal_band", "<=", 36, "in", INF, UP, "914 mm")],
        va=None,
        inputs=[("drop_height", "length", "in", True), ("guard_present", "boolean", None, False)],
        info=[("walking_surface.drop", "Vertical drop from the walking surface to floor or grade within the 36 in band", "Deck IfcSlab top versus other IfcSlab tops intersecting the 36 in band", "walking_surfaces[].drop_height_in", "Section or elevation showing deck height above grade")],
        ids="rules/irc2021/ch03/ids/ori-ch03-guards.ids#Walking surfaces and guards are modeled", entity="IfcSlab"),
    ("R312.1.2", "general"): dict(
        fn="guard_height_min", slug="guard-height-min",
        base=[P("min_guard_height", ">=", 36, "in", INF, UP, "914 mm", detail="VRC text unamended"),
              P("min_guard_height_stair_open_side", ">=", 34, "in", INF, UP, "864 mm", applies_when="on_stair_open_side == true", detail="exception, measured from nosing line")],
        va=None,
        inputs=[("guard_height", "length", "in", True), ("on_stair_open_side", "boolean", None, False)],
        info=[("guard.height", "Guard top height, measured from the walking surface or nosing line next to it", "IfcRailing (GUARDRAIL) top elevation minus walking-surface top elevation", "guards[].height_in", "Guard detail or section")],
        ids="rules/irc2021/ch03/ids/ori-ch03-guards.ids#Walking surfaces and guards are modeled", entity="IfcRailing"),
}


def unit_id(section: str, part: str | None, slug: str | None = None) -> str:
    tail = section
    if slug:
        tail += ":" + slug
    elif part:
        tail += ":" + "".join(c if c.isalnum() else "-" for c in part.lower()).strip("-").replace("--", "-")
    return f"urn:ori:rule-unit:irc2021-va:{tail}"


def va_layer(section: str, part: str | None):
    key = f"{section}|{part}" if part and f"{section}|{part}" in VA_AMENDMENTS else section
    amend = VA_AMENDMENTS.get(key)
    if amend is None:
        # Section-level amendments to a parent apply to listed children (R313).
        for parent in ("R313",):
            if section.startswith(parent + ".") and parent in VA_AMENDMENTS:
                amend = VA_AMENDMENTS[parent]
                break
    if amend is None:
        mode, item, note = "adopts_base", None, "No amendment to this section is listed in 13VAC5-63-210 section 310.8 (fetched 2026-09-27); the VRC adopts the IRC base."
    else:
        mode, item, note = amend
    return {
        "layer_id": "us-va:vrc-2021",
        "jurisdiction": VA_JURISDICTION,
        "code": "VRC",
        "edition": "2021",
        "effective_from": VA_EFFECTIVE,
        "authority_class": "state_adopted_code",
        "binding": True,
        "precedence": 1,
        "override_mode": mode,
        "mode_status": "sourced_primary",
        "amendment_ref": {"source": VA, "item": ((f"310.8 items {item}" if "-" in item else f"310.8 item {item}") if item else None), "note": note},
    }


def build_unit(section, part, title, cls, sf, *, va_only=False):
    impl = IMPLEMENTED.get((section, part))
    slug = impl["slug"] if impl else None
    chapter = 3
    layer = va_layer(section, part)
    base_present = not va_only and layer["override_mode"] != "adds_section"
    base = {
        "code": "IRC",
        "edition": "2021",
        "publisher": "International Code Council",
        "authority_class": "model_code",
        "binding": False,
        "source": "source:icc:irc-2021",
        "status": "present" if base_present else "not_in_base",
    }
    if impl:
        base["parameters"] = impl["base"]
        layer["parameters"] = impl["va"] if impl["va"] else [dict(p, value_status="sourced_secondary", source=UP) for p in impl["base"]]
    check_class = CLASS[cls]
    if check_class == "judgment":
        evaluator = {"kind": "human_reviewer", "implementation": None, "implementation_version": None}
    elif impl:
        evaluator = {"kind": "deterministic_function", "implementation": f"verification/ori_verify/rules.py#{impl['fn']}", "implementation_version": "0.1.0"}
    else:
        evaluator = {"kind": "not_implemented", "implementation": None, "implementation_version": None}
    sources_checked = ["source:va:13vac5-63-210", "source:upcodes:vrc-2021-ch03"]
    if impl:
        for p in impl["base"] + (impl["va"] or []):
            if p["source"] not in sources_checked:
                sources_checked.append(p["source"])
    unit = {
        "id": unit_id(section, part, slug),
        "type": "Requirement",
        "version": "0.1.0",
        "effective_from": "2024-01-18T00:00:00-05:00",
        "effective_to": None,
        "jurisdiction": [VA_JURISDICTION],
        "source": ["source:icc:vrc-2021", "source:icc:irc-2021", VA, "source:va:codes-2021-effective"],
        "derived_from": [],
        "supersedes": [],
        "metadata": {"authority_classification": "state_adopted_code", "status": "DRAFT"},
        "rule_unit_profile": "ori-rule-unit-0.1",
        "title": title,
        "source_section": {"code": "IRC", "edition": "2021", "section": section, "chapter": chapter},
        "authority_classification": "state_adopted_code",
        "check_class": check_class,
        "classification_basis": "estimate",
        "single_family_applicability": sf,
        "base_model": base,
        "jurisdiction_layers": [layer],
        "required_information": {"ids": None, "items": []},
        "inputs": [],
        "result_states": ["pass", "fail", "unknown", "not_applicable"],
        "unknown_policy": {"missing_information_result": "unknown", "statement": "Missing, unreadable or unconfirmed information yields unknown, never fail."},
        "evaluator": evaluator,
        "provenance": {"recorded_by": RECORDED_BY, "recorded_at": RECORDED_AT, "sources_checked": sources_checked},
        "legal_boundary": {"machine_result_is_approval": False, "statement": "Any machine result for this unit is reviewer evidence, not approval. Only the building official's decision under the USBC is lawful approval."},
    }
    if part:
        unit["source_section"]["subsection_part"] = part
    if impl:
        unit["inputs"] = [{"name": n, "datatype": d, **({"unit": u} if u else {}), "required": r} for n, d, u, r in impl["inputs"]]
        unit["required_information"] = {
            "ids": {"ids_version": "1.0", "specification_ref": impl["ids"], "applicability_entity": impl["entity"]},
            "items": [
                {"key": k, "description": d, "ifc_path": ip, "declared_value_key": dk, "pdf_evidence": pe}
                for k, d, ip, dk, pe in impl["info"]
            ],
        }
    if not base_present:
        unit["source_section"] = {"code": "VRC", "edition": "2021", "section": section, "chapter": chapter}
        unit["source"] = ["source:icc:vrc-2021", VA, "source:va:codes-2021-effective"]
    key = f"{section}|{part}" if part else section
    unit["paraphrase"] = PARAPHRASES[key]
    unit["source_url"] = VRC_CH3_URL
    links = [{"label": f"2021 VRC Chapter 3, section {section} (ICC Digital Codes)", "url": VRC_CH3_URL}]
    if layer["override_mode"] != "adopts_base" or va_only:
        links.append({"label": "13VAC5-63-210 section 310.8 (Virginia amendments to the IRC)", "url": VAC_210_URL})
    if base_present:
        links.append({"label": "2021 IRC Chapter 3 model code (ICC Digital Codes; comparison only)", "url": IRC_CH3_URL})
    unit["source_links"] = links
    return unit


PARAPHRASES = json.loads(PARA_JSON.read_text(encoding="utf-8"))["paraphrases"]


def load_interpretability():
    return json.loads(INTERP_JSON.read_text(encoding="utf-8"))


def interpretability_record(entry, data):
    reg = data["determinations"]
    # A record's relevance can differ per unit (one appeal may resolve wording for one
    # section and merely apply another), so a unit may override it.
    over = entry.get("relevance_overrides", {})
    def rec_for(i):
        d = dict({"id": i}, **reg[i])
        if i in over:
            d["relevance"] = over[i]
        return d
    dets = [rec_for(i) for i in entry.get("determination_ids", [])]
    local = [rec_for(i) for i in entry.get("local_operationalization_ids", [])]
    rel = {d["relevance"] for d in dets + local}
    rec = {
        "rubric_version": data["rubric_version"],
        "score": entry["score"],
        "scoring_status": data["scoring_status_default"],
        "rationale": entry["rationale"],
    }
    for k in ("ambiguous_terms", "intent_questions", "conflicts_with"):
        if entry.get(k):
            rec[k] = entry[k]
    if dets:
        rec["determinations"] = dets
    if local:
        rec["local_operationalizations"] = local
    rec["evidence_strength"] = "direct" if "direct" in rel else ("indirect" if rel else "none_found")
    if entry.get("candidate_clarification"):
        rec["candidate_clarification"] = entry["candidate_clarification"]
    rec["reviewers"] = [{"reviewer": data["pre_scorer"], "score": entry["score"], "date": data["scored_at"], "independent": True, "role": "pre_scorer"}]
    rec["scored_text_source"] = data["scored_text_source"]
    rec["scored_at"] = data["scored_at"]
    return rec


def apply_interpretability(units, data):
    by_id = {u["id"]: u for u in units}
    unknown = sorted(set(data["scores"]) - set(by_id))
    assert not unknown, f"interpretability scores for unknown units: {unknown}"
    for uid, entry in data["scores"].items():
        u = by_id[uid]
        rec = interpretability_record(entry, data)
        u["interpretability"] = rec
        for d in rec.get("determinations", []) + rec.get("local_operationalizations", []):
            src = DET_SOURCE[d["body_class"]]
            if src not in u["provenance"]["sources_checked"]:
                u["provenance"]["sources_checked"].append(src)


def interpretability_summary(units):
    scored = [u for u in units if "interpretability" in u]
    c = Counter(u["interpretability"]["score"] for u in scored)
    e = Counter(u["interpretability"]["evidence_strength"] for u in scored)
    return {
        "rubric": "spec/interpretability-0.1-draft.md",
        "scoring_status": "estimate (ORI pre-score; two-reviewer scoring not yet done)",
        "units_scored": len(scored),
        "judgment_units_scored": sum(1 for u in scored if u["check_class"] == "judgment"),
        "score_counts": {k: c.get(k, 0) for k in ("clear", "ambiguous_term", "intent_dependent", "conflicting")},
        "evidence_strength_counts": {k: e.get(k, 0) for k in ("direct", "indirect", "none_found")},
        "note": "Units without an interpretability record have not been scored; that is not a finding that they are clear.",
    }


def build():
    units = [build_unit(*u) for u in UNITS]
    added = []
    for sec, title, cls in VA_ADDED_SECTIONS:
        u = build_unit(sec, None, title, cls, "conditional" if sec != "R334" else "applies", va_only=True)
        u["jurisdiction_layers"][0]["override_mode"] = "adds_section"
        u["jurisdiction_layers"][0]["amendment_ref"] = {"source": VA, "item": "310.8 items 41-53", "note": "Virginia-added section; not part of the IRC R301-R327 range."}
        added.append(u)
    ids = [u["id"] for u in units + added]
    assert len(ids) == len(set(ids)), "duplicate rule-unit ids"
    apply_interpretability(units + added, load_interpretability())
    return units, added


def split(units):
    c = Counter(u["check_class"] for u in units)
    return {k: c.get(k, 0) for k in ("data_check", "geometric_deterministic", "judgment")}


def collection(units, added):
    return {
        "collection_id": "urn:ori:rule-unit-collection:irc2021-va:ch03",
        "rule_unit_profile": "ori-rule-unit-0.1",
        "title": "2021 IRC Chapter 3 (R301-R327) Building Planning with the 2021 Virginia Residential Code override layer: worked example",
        "status": "DRAFT",
        "draft_completion_request": "Needs a human reviewer to (1) confirm each check_class estimate, (2) check the 13VAC5-63-210 item numbers against the regulation (R322 items 35-38 were mapped to subsections on 2026-09-28 and need the same check), (3) confirm the interpretability pre-scores with two independent reviewers, and (4) replace secondary base-model values with ICC primary text under a licence, if ORI wants primary base values.",
        "generated_by": "rules/irc2021/ch03/build_units.py",
        "scope": {
            "occupancy": "detached single-family dwelling",
            "base_model": "2021 IRC (model code; not binding by itself)",
            "override_layers": ["2021 Virginia Residential Code (13VAC5-63-210), effective 2024-01-18"],
            "range": "R301-R327, plus Virginia-added R331-R336 reported separately",
            "excluded": "R328-R330 (energy storage, generators, fuel cells) are outside the requested range and are not classified here.",
            "granularity": "One unit per checkable obligation, at section or subsection level. Some sections split into several units (for example R305.1 and R310.2.1).",
            "not_a_pilot": "Example built from public sources; not a pilot or partner of any jurisdiction.",
        },
        "classification_method": {
            "data_check": "Can be decided from declared or structured attributes (presence, rating, listing, product data, table lookups) with no spatial computation.",
            "geometric_deterministic": "Can be decided by a deterministic computation on dimensions or model geometry, given the required information.",
            "judgment": "Needs engineering or official judgment ('approved', structural adequacy, continuity of path, installation quality) and is never auto-decided.",
            "basis": "All check_class tags are ORI estimates (classification_basis=estimate). No published IRC classification exists; the nearest published analogue is an IBC sentence-level study (Zhang and El-Gohary 2021), which is not IRC data.",
        },
        "class_split_r301_r327": split(units),
        "class_split_va_added": split(added),
        "unit_count_r301_r327": len(units),
        "interpretability_summary": interpretability_summary(units + added),
        "sources": SOURCES,
        "legal_boundary": {"machine_result_is_approval": False, "statement": "Rule units and machine results are reviewer evidence. They are not approval and are not the code."},
        "units": units,
        "va_added_units": added,
    }


def table_md(col):
    units, added = col["units"], col["va_added_units"]
    s = col["class_split_r301_r327"]
    n = col["unit_count_r301_r327"]
    pct = {k: f"{100 * v / n:.0f}%" for k, v in s.items()}
    impl = [u for u in units if u["evaluator"]["kind"] == "deterministic_function"]
    lines = [
        "# 2021 IRC Chapter 3 (R301–R327) rule units with the 2021 VRC override layer (DRAFT)",
        "",
        "> **DRAFT.** Generated by `rules/irc2021/ch03/build_units.py` from `va-vrc-2021-ch03.units.json`; do not edit by hand.",
        "> Example built from public sources; not a pilot or partner. Every machine result is reviewer evidence, not approval.",
        "> Completion request: a human reviewer should confirm the class tags, check the 13VAC5-63-210 item numbers (including the R322 item 35–38 mapping made 2026-09-28), and run the two-reviewer interpretability scoring.",
        "",
        "## What is sourced and what is an estimate",
        "",
        "- **Sourced:** the section list (2021 VRC Chapter 3 via UpCodes, fetched 2026-09-27) and the Virginia override mode (13VAC5-63-210 §310.8, fetched 2026-09-27; a section missing from that list is recorded as `adopts_base`).",
        "- **Estimate:** every `class` tag. These are ORI analyst judgments, not a published classification.",
        "- **No code text:** the descriptions below are ORI's own labels, not ICC section headings, and each unit's paraphrase (in the JSON) is ORI's summary of effect. Read the official text on [ICC Digital Codes (2021 VRC Chapter 3)](https://codes.iccsafe.org/content/VARC2021P1/chapter-3-building-planning) and the Virginia changes in [13VAC5-63-210](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section210/). Policy: `docs/CITATION-POLICY.md`.",
        "- **Values:** only the implemented units carry numbers, and each number has its own status: `sourced_primary`, `sourced_secondary`, `inferred_unamended` or `estimate`.",
        "",
        f"## Class split (R301–R327, {n} units, estimate)",
        "",
        "| class | units | share |",
        "|---|---:|---:|",
    ]
    for k in ("data_check", "geometric_deterministic", "judgment"):
        lines.append(f"| {k} | {s[k]} | {pct[k]} |")
    sa = col["class_split_va_added"]
    lines += [
        "",
        f"Virginia-added sections R331–R336 (outside the range, {len(added)} units): data_check {sa['data_check']}, geometric_deterministic {sa['geometric_deterministic']}, judgment {sa['judgment']}.",
        "",
        f"Units with a working reference evaluator: {len(impl)} (see `verification/`).",
        "",
        "## Implemented units: base value vs Virginia value",
        "",
        "| unit | IRC 2021 base | status | VRC 2021 | status | VA mode |",
        "|---|---|---|---|---|---|",
    ]
    def fmt(params):
        return "; ".join(f"{p['name']} {p['comparator']} {p['quantity']['value']} {p['quantity']['unit']}" + (f" (when {p['applies_when']})" if p.get("applies_when") else "") for p in params)
    for u in impl:
        b = u["base_model"]["parameters"]; l = u["jurisdiction_layers"][0]
        lines.append(f"| {u['source_section']['section']} {u['source_section'].get('subsection_part','')} | {fmt(b)} | {', '.join(sorted({p['value_status'] for p in b}))} | {fmt(l['parameters'])} | {', '.join(sorted({p['value_status'] for p in l['parameters']}))} | {l['override_mode']} |")
    isum = col["interpretability_summary"]
    lines += [
        "",
        f"## Interpretability pre-scores ({isum['units_scored']} units, estimate)",
        "",
        "Rubric: `spec/interpretability-0.1-draft.md`. Scores are ORI pre-scores awaiting two independent human reviewers. "
        "Records are only those ORI fetched and read on 2026-09-28. A unit without a score has not been scored.",
        "",
        "| score | units |",
        "|---|---:|",
    ]
    for k, v in isum["score_counts"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "| section | part | class | score | evidence | records |", "|---|---|---|---|---|---|"]
    for u in units + added:
        it = u.get("interpretability")
        if not it:
            continue
        recs = [d["citation"] for d in it.get("determinations", []) + it.get("local_operationalizations", [])]
        lines.append(f"| {u['source_section']['section']} | {u['source_section'].get('subsection_part', '')} | {u['check_class']} | {it['score']} | {it['evidence_strength']} | {'; '.join(recs)} |")
    lines += [
        "",
        "## All units",
        "",
        "SF = single-family applicability. VA mode is the VRC layer's override mode; `item` is ORI's count of the 13VAC5-63-210 §310.8 list entries.",
        "",
        "| # | section | part | ORI description | class | SF | VA mode | VA item | evaluator | interpretability |",
        "|---:|---|---|---|---|---|---|---|---|---|",
    ]
    for i, u in enumerate(units + added, 1):
        l = u["jurisdiction_layers"][0]
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            i, u["source_section"]["section"], u["source_section"].get("subsection_part", ""), u["title"], u["check_class"],
            u["single_family_applicability"], l["override_mode"], (l["amendment_ref"]["item"] or "").replace("310.8 ", ""), u["evaluator"]["kind"],
            u.get("interpretability", {}).get("score", "not scored")))
    lines.append("")
    return "\n".join(lines)


def render():
    units, added = build()
    col = collection(units, added)
    return json.dumps(col, indent=2, ensure_ascii=False) + "\n", table_md(col)


def main():
    j, m = render()
    OUT_JSON.write_text(j, encoding="utf-8")
    OUT_MD.write_text(m, encoding="utf-8")
    col = json.loads(j)
    print("units:", col["unit_count_r301_r327"], "split:", col["class_split_r301_r327"], "va-added:", col["class_split_va_added"])


if __name__ == "__main__":
    main()
