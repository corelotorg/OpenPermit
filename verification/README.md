# ORI geometric verification layer (DRAFT 0.1)

> **Every output here is reviewer evidence, not approval.** A `pass` approves nothing.
> Lawful approval is the building official's decision under the adopted code, which in
> Virginia is the 2021 Virginia Residential Code under the USBC, effective 2024-01-18.
> All models and PDFs in `examples/` are synthetic. They describe no real building and
> real jurisdiction's submission.

This is a reference evaluator for the *deterministic* rule units in
`rules/irc2021/ch03/va-vrc-2021-ch03.units.json`. The same rule functions run on two
kinds of input:

1. **IFC models.** Facts are measured with IfcOpenShell (`ori_verify/ifc_extract.py`).
2. **Declared values tied to PDF sheets and pages** (`ori_verify/declared.py`). This is the
   PDF path; see `docs/PDF-PATH-0.1-DRAFT.md`.

Thresholds are read from the rule-unit data, with the Virginia layer applied over the
IRC base (`ori_verify/units.py`). None are hard-coded in the rules.

## Implemented rule units (14)

| Section | Unit | Measured from IFC as |
|---|---|---|
| R311.7.5.1 | riser height max; riser uniformity | stepped extrusion profile of `IfcStairFlight`, in world coordinates |
| R311.7.5.2 | tread depth min; tread uniformity | same profile |
| R311.7.2 | stair headroom | nosing line vs. underside of `IfcSlab`/`IfcCovering`/`IfcBeam` overlapping in plan |
| R305.1 | ceiling height (habitable/hallway/kitchen; bath/toilet/laundry) | `IfcSpace` body top minus bottom; use from `Pset_ORI_SpaceUse.UseCategory` |
| R304.1 | minimum habitable room area (kitchens excepted) | `IfcSpace` footprint area |
| R310.2.1 | EERO net clear area, height, width | `Pset_ORI_EscapeOpening` (never inferred from overall window size) |
| R310.2.3 | EERO sill height | window placement above storey + declared frame-to-clear-opening offset |
| R312.1.1 | guard required (drop > trigger within the horizontal band) | deck top vs. lowest slab top in the band beyond the edge |
| R312.1.2 | guard height (stair open-side exception) | `IfcRailing` GUARDRAIL top minus deck top |

Effective values with the VA layer: riser ≤ 8.25 in and tread ≥ 9 in, sourced primary from
13VAC5-63-210 §310.8. The IRC base values are 7.75 in and 10 in, sourced secondary. The
table in `rules/irc2021/ch03/CHAPTER-3-TABLE.md` gives every value with its status.

## Result states

| ORI result_state | core `Verification.outcome` |
|---|---|
| pass | pass |
| fail | fail |
| unknown | indeterminate |
| not_applicable | not-applicable |

Each record keeps the ORI name in `metadata.result_state` and a `metadata.reason_code`.

**Missing information never gives `fail`.** Missing, unreadable, unconfirmed (extracted)
or reviewer-only information gives `unknown` with a reason code: `missing_information`,
`unconfirmed_extraction`, `required_element_not_found`, `exception_requires_reviewer`,
`geometry_not_measurable` or `parameter_missing`. The `Result` constructor refuses a
`fail` that carries one of these codes. The conformance rule
`missing-information-not-fail` rejects such records in any ORI data.

A `fail` requires usable evidence that the requirement is unmet *whatever the missing facts
turn out to be*. Two examples:
- An EERO area below both the standard and the grade-floor minimum fails even if
  grade-floor status is unknown.
- A window frame bottom already above 44 in fails the sill check even without the
  clear-opening offset.

## Provisional decisions

1. `unknown` is mapped to core `indeterminate`, with the ORI name and a reason code in
   metadata. No new core enum value is added.
2. A guard that is required but not modelled gives `unknown`
   (`required_element_not_found`), because absence from a model is not evidence of
   absence. A guard that the applicant explicitly declares absent (`guard_present: false`)
   gives `fail`.
3. IRC base values stay secondary-sourced and clearly labelled. No licensed ICC text is used.
4. The reference node does not index `rules/` or `verification/` yet.
5. Rule-unit `check_class` tags are estimates pending human review.

## Outputs

- **ORI report JSON** (`records.py`):
  - One core `Verification` per result. It includes `inputs` (the artifact id, which is a
    sha256), `requirements` (the rule-unit id), measured and required values, the facts
    used with their origin and anchor, and the layers applied.
  - One core `Evidence` object per input artifact, with a sha256 integrity block.
  - No `Decision` is ever emitted.
  - Reports are reproducible for a fixed `executed_at`.
- **BCF 3.0** (`bcf.py`):
  - Only `fail` and `unknown` results become topics, each titled
    "[Reviewer evidence, not approval] …".
  - IFC subjects get a viewpoint that selects the element by IfcGuid. PDF subjects carry
    their sheet/page anchor in the description.
  - On 2026-09-27, `examples/reports/ifc-fail.bcf` was validated once, outside CI, against
    the buildingSMART BCF-XML `release_3_0` XSDs (markup, visinfo, version, extensions,
    shared-types): 28 files, 0 errors. The XSDs are not vendored, and CI checks structure
    only.
  - On 2026-09-28 the committed reports and BCF were regenerated because rule-unit titles
    changed to ORI descriptions (`docs/CITATION-POLICY.md`). The external XSD validation was
    not repeated for the regenerated BCF.

## IDS

`rules/irc2021/ch03/ids/*.ids` (IDS 1.0) state the *information* each rule needs: property
sets, use categories, body representations. IDS cannot express geometry, so geometry
stays in this evaluator. The tests run IfcTester: the pass model meets all four IDS files,
and the incomplete model fails the spaces and EERO specifications.

## Running

```bash
python -m pip install -r verification/requirements.txt
cd verification
python -m ori_verify.cli fixtures /tmp/ori     # synthetic pass/fail/incomplete IFC models
python -m ori_verify.cli ifc /tmp/ori/ori-ch03-fail.ifc --out /tmp/fail.json --bcf /tmp/fail.bcf
python -m ori_verify.cli ifc MODEL.ifc --jurisdiction base --out base.json   # IRC base only, no VA layer
python -m ori_verify.cli manifest plans.pdf --plan-set PS --version 1 --by applicant --at 2026-09-27T12:00:00Z --out manifest.json
python -m ori_verify.cli declared examples/declared/declared-values-v1.json --manifest examples/pdf/manifest-v1.json --out r.json
python examples/build_examples.py              # rebuild committed reports (IFC files kept unless --regen-ifc)
python -m pytest -q tests                      # all verification tests (incl. ORI-CL)
python -m ori_cl compile ../rules/irc2021/ch03/ori-cl/ch03-geometric.oricl   # ORI-CL -> rule units + check plans
python -m ori_cl ifc ../rules/irc2021/ch03/ori-cl/ch03-geometric.oricl examples/ifc/ori-ch03-fail.ifc
python -m ori_cl.corpus_stats LOCAL.txt --out stats.json   # derived statistics only; never commit LOCAL.txt
python -m ori_cl.term_merger classify --code-text LOCAL-CH2.txt LOCAL-CH3.txt   # term merger study (optional deps below)
python -m ori_cl.term_merger report                          # results tables (markdown)
python -m ori_cl.term_merger scan ../docs --code-text LOCAL-CH2.txt LOCAL-CH3.txt   # refined 6-word-run scan; digests only
```

## ORI-CL (DRAFT 0.1)

`ori_cl/` is the parser (`syntax.py`), compiler (`compiler.py`), evaluator (`evaluator.py`),
vocabulary loader and provenance check (`vocab.py`), IFC binding (`ifc_bind.py`) and
linguistic-study tool (`corpus_stats.py`) and term merger study (`term_merger.py`, DRAFT,
`docs/TERM-MERGER-METHOD-DRAFT.md`: free names vs cited terms vs code expression; analysis to
inform counsel, not a legal conclusion) for ORI's controlled rule language. Spec:
`spec/ori-cl-0.1-draft.md`. `tests/test_ori_cl.py` proves the ORI-CL form of each of the 14
checks compiles to the same parameters and gives the same state and reason code as
`ori_verify/rules.py` on the IFC fixtures, the declared examples and a synthetic battery,
under both the VA layer and the IRC base.

Reason-code alignment (2026-09-28): a condition fact (sloped ceiling, stair open side,
grade floor) that is present but unconfirmed now gives `unconfirmed_extraction` in all three
functions (it was `missing_information` in two). States are unchanged.

## Dependencies and licences

This package's code is Apache-2.0, like the rest of the repository. Dependencies are used,
not vendored:
- ifcopenshell 0.8.5 and ifctester 0.8.5: LGPL-3.0-or-later
- pypdf: BSD-3-Clause
- jsonschema: MIT

Optional, only for regenerating the term merger study (not needed by tests or the suite):
sentence-transformers (Apache-2.0) with the all-MiniLM-L6-v2 model (Apache-2.0), torch
(BSD-3-Clause), nltk (Apache-2.0) with WordNet 3.0 (Princeton licence) and the Brown corpus,
and wordfreq (code Apache-2.0, data CC BY-SA 4.0, read locally for frequencies only).

## Limits (DRAFT)

- Straight flights only: one extruded stepped profile per `IfcStairFlight`. Winders,
  spirals and landings are not measured, and such flights give `unknown`.
- Stair clear width (R311.7.1) is not implemented. Flight width is not clear width, and
  guessing would risk false passes.
- Ceiling-height exceptions (sloped ceilings, beams) go to the reviewer as `unknown`.
- The guard-band test and the railing association use axis-aligned bounding boxes. That is
  correct for axis-aligned rectangular decks like the synthetic ones. For rotated or
  irregular decks, band membership can be wrong in either direction; that case is not yet
  handled and needs reviewer attention.
- The sleeping-room EERO presence check (R310.1) and every data_check unit are not yet
  implemented.

## Plan takeoff (DRAFT 0.1)

`ori_takeoff/` turns vector PDF pages and DXF drawings into an `ori-plan-overlay-0.1` overlay (walls,
doors, windows, rooms, stairs, dimensions, labels) with takeoff quantities, previews, COCO/GeoJSON exports and
a simple IFC 4.3 model checked by `ori_verify`. Auto-extracted elements stay unconfirmed and give `unknown`.
Training use goes through a licensing gate. See `docs/PLAN-TAKEOFF-0.1-DRAFT.md` and
`docs/PLAN-TRAINING-SET-WORKFLOW-DRAFT.md`; examples in `examples/takeoff/` (ORI-authored CC0 sample plan).
