# Chapter 6 wall framing and Virginia practical bracing (DRAFT 0.1)

> **DRAFT, 2026-10-12.** Licence: CC BY-SA 4.0 (docs). The rule data it describes is CC0
> (`rules/irc2021/ch06/`). Every machine result is reviewer evidence, never approval. The building
> official decides. This example is built from public sources. It is not a pilot or a partnership with
> any jurisdiction, and the sources named here are attribution only: none of them endorses ORI or is
> affiliated with it.

## Why Chapter 6 next

After Chapter 3 (building planning), Chapter 6 covers the most plan-review questions on almost every
single-family permit: stud size and spacing, plates, holes and notches, headers and wall bracing.
Virginia changes this chapter in three places (13VAC5-63-210 §310.8 items 62–64). The largest change
replaces R602.12 with "practical wall bracing", which has bare numeric rules that a model can check.
Those Virginia values could be read from the official regulation today, so Chapter 6 yields rules
that are both executable and verified. Chapter 4 (foundations) and Chapter 8 (roofs) depend more on
site data and span tables, which would be harder to check from drawings.

## What is in `rules/irc2021/ch06/`

| file | content |
|---|---|
| `catalogue_ch06.py` | 88 catalogued units: R601, R602 (subsection level), Virginia R602.12.x, and R603–R610 (section level only) |
| `paraphrases-ch06.json` | ORI paraphrase for every unit (CC0) |
| `build_units.py` | generator for `va-vrc-2021-ch06.units.json` and `CHAPTER-6-TABLE.md` |
| `interpretability-ch06.json` | 5 pre-scores (estimates) for Virginia units whose text ORI fetched |
| `ids/ori-ch06-framing.ids` | IDS 1.0 information requirements for framing, panels and bracing rectangles |

There is no ORI-CL restatement for Chapter 6 yet. It needs new vocabulary entries (framed wall, braced
wall panel, bracing rectangle, with their facts) in `vocab/ori-cl-vocab-0.1.json`. **To finish:** add
those entries and a `ch06-framing.oricl` file.

## Sourcing status

- **Verified (sourced_primary):** the Virginia layer for R602.10 (item 62), R602.10.9 (item 63) and
  R602.12 (item 64). It was read on 2026-10-12 from
  [13VAC5-63-210](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section210/).
  The values on the 7 Virginia practical-bracing units come from that regulation.
- **UNVERIFIED (value_status `estimate`):** every IRC 2021 base value. These are stud spacing and
  height, top plate count and splice offset, and bored-hole and notch ratios.
  [ICC Digital Codes](https://codes.iccsafe.org/content/IRC2021P2/chapter-6-wall-construction)
  returned only the page title to an automated fetch.
  - Most of these values match a Virginia county handout of **2018** VRC Chapter 6 pages. That
    handout carries an ICC copyright and single-user notice. ORI keeps only its URL, the fetch date
    and its SHA-256; no text or image from it is committed.
  - The top plate splice offset value was not found in any fetched source.
  - Rules **never pass or fail on an estimate value**. They report the comparison and return
    `unknown` with reason `threshold_unverified`.
- **UNVERIFIED:** the Chapter 6 section list, and the link pattern for the 2021 VRC Chapter 6 page.

## Pending owner decision: table data

Jeremiah has not yet decided whether ORI may encode whole numeric tables, such as the stud table,
header spans and bracing lengths. Until he does, ORI encodes only the cells a rule or test needs, as
bare values with an `applies_when` condition:

- 4 stud-spacing cells;
- the 8 ft wall-height column (5 cells) of the Virginia panel-length table.

Any case outside the encoded cells returns `unknown` with reason `threshold_not_encoded`. Header
spans (R602.7), required bracing length (R602.10.3 and the Virginia R602.12.4 table) and jack and
full-height stud counts (R602.7.5) are catalogued but not executable. For R602.12.4.2, the applicant
declares the required length, and ORI checks that the contributing length meets it.

## Executable units (13 of 88)

| unit | what is checked | thresholds |
|---|---|---|
| R602.3.1 stud spacing | spacing for size and floors carried | estimate → unknown |
| R602.3.1 stud height | bearing stud unsupported height | estimate → unknown |
| R602.3.2 plate count | two top plates on bearing/exterior walls | estimate → unknown |
| R602.3.2 splice offset | top plate joint offset | estimate → unknown |
| R602.6 bored holes | hole diameter / stud depth | estimate → unknown |
| R602.6 notches | notch depth / stud depth | estimate → unknown |
| R602.12.1 (VA) | sheathing material and minimum thickness | verified |
| R602.12.2 exterior (VA) | exterior panel length vs opening height (8 ft walls) | verified |
| R602.12.2 interior (VA) | interior panel minimum length | verified |
| R602.12.3 (VA) | rectangle side limit and aspect ratio | verified |
| R602.12.4.2 (VA) | contributing length (exterior full, interior half, 4 ft limit) ≥ declared required | verified |
| R602.12.6 corner (VA) | panel edge to rectangle corner | verified |
| R602.12.6 gap (VA) | gap between adjacent exterior panels | verified |

Missing information never produces `fail`. Two safeguards also hold:

- **Absent panels:** a missing panel counts only when the model declares
  `Pset_ORI_BracingRectangle.BracingPlanComplete = true`. Otherwise the rule returns `unknown`
  (`required_element_not_found`).
- **Building corners:** a corner-distance pass is downgraded to `unknown` unless the model declares
  that the building outline matches the rectangle, because building corners inside the rectangle are
  not yet measured.

Under `--jurisdiction base` (IRC only), the Virginia practical-bracing units have no parameters and
return `unknown`.

## IFC representation

The representation is generic on purpose: a detailed stud-level assembly can supply the same facts.

- **`IfcWall` + `Pset_ORI_Framing`:**
  - StudNominalSize, StudSpacing, StudHeight;
  - FloorsSupported, TopPlateCount, TopPlateSpliceOffset;
  - MaxBoredHoleDiameter, MaxNotchDepth, StudsDoubledAtHoles;
  - StudGrade and StudSpecies (recorded, not checked);
  - bearing and exterior status from `Pset_WallCommon`.
- **`IfcPlate` (SHEET) + `Pset_ORI_BracedWallPanel`:**
  - Method (`VA-R602.12`), Location, SheathingMaterial, SheathingThickness;
  - AdjacentOpeningClearHeight, AdjacentOneStoryGarageDoor, WallHeight (optional).
  - Panel length and position are measured from the plate geometry.
- **`IfcAnnotation` + `Pset_ORI_BracingRectangle`:**
  - OriginX/Y and LengthX/Y (axis-aligned only);
  - RequiredBracingAlongX/Y (the applicant's table lookup);
  - BuildingMatchesRectangle, BracingPlanComplete.
- `Pset_ORI_Takeoff` provenance applies to all of these: unreviewed takeoff values become unconfirmed
  and give `unknown`.

**Reference wall assembly:** Jeremiah built a verifiable reference wall assembly separately, and it
will be added to the repository on its own. When it lands, these rules should consume its framing
facts through the same `Pset_ORI_Framing` / `framed_wall` subject, so ORI does not grow a second wall
model. Integration is pending.

## Fixtures and results (SYNTHETIC)

`verification/examples/ch06/ori-ch06-{pass,fail,incomplete}.ifc` (CC0); reports are in
`verification/examples/reports/ifc-ch06-*.report.json`. All records, from the committed reports:

| fixture | pass | fail | unknown | not applicable |
|---|---:|---:|---:|---:|
| pass | 39 | 0 | 26 | 17 |
| fail | 4 | 14 | 20 | 11 |
| incomplete | 0 | 0 | 32 | 2 |

In the pass fixture, the 26 unknowns are the IRC base checks held back as `threshold_unverified`. In
the fail fixture, every verified Virginia rule fails at least once. The base-value violations are
reported as "would not meet" an UNVERIFIED value, not as failures.

## To finish (DRAFT)

1. Fetch and verify the 2021 IRC Chapter 6 values and section list, then raise `value_status`.
2. Get the owner's decision on table data.
3. Add ORI-CL vocabulary and a restatement.
4. Split R603–R610 into subsections.
5. Have two human reviewers score interpretability.
6. Integrate the reference wall assembly when it lands.
