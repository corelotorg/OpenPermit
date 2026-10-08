# ORI-CL: ORI Controlled Language, v0.1 Draft

Status: DRAFT. It has not been reviewed by a person or by counsel.

Files:

| What | Path |
|---|---|
| Grammar | `spec/ori-cl-0.1.ebnf` |
| Vocabulary | `vocab/ori-cl-vocab-0.1.json` |
| Reference parser, compiler and evaluator | `verification/ori_cl/` |
| Chapter 3 statements | `rules/irc2021/ch03/ori-cl/*.oricl`, compiled to `*.compiled.json` |
| Tests | `verification/tests/test_ori_cl.py` |
| Conformance rules | `ori-cl-vocabulary-provenance`, `ori-cl-statement` |

License: CC0-1.0 for this document, the grammar, the vocabulary and the statements. The code is Apache-2.0.

To finish: decide the open questions in section 12.

## 1. Purpose

ORI-CL is a small, strict language for stating building-code requirements as testable logical and geometric statements. Each statement is **ORI's own interpretation** of a provision. It cites the provision by section number and links to the official text. It is not a reproduction of that text, and it is not a translation of it.

A statement compiles to two things:

1. an ORI rule unit (`spec/ori-rule-unit-0.1.schema.json`);
2. a check plan.

Either the generic ORI-CL evaluator runs the plan, or the existing IfcOpenShell-based check function runs it. The tests show both give the same result.

## 2. Design principles

ORI-CL borrows its approach from constructed languages. Toki Pona uses a very small word set in which each word does one job. Esperanto uses a regular grammar with no exceptions to its rules.

- **Closed, small vocabulary.** ORI-CL has 58 keywords. Facts, units, subject kinds, reference geometry and IFC names come only from the vocabulary file. There are no synonyms, and every word has one role (vocabulary `keywords[].role`).
- **Regular grammar.** Every line is one clause. Its first word fixes the clause's form, so each line has exactly one parse (LL(1)). There is no inflection, no free word order and no operator precedence.
  - `and` and `or` cannot be mixed in one condition. Several `when` lines are joined by `and`.
- **One rule unit, one requirement.** Each block has at most one `require`.
- **Parametric.** Numbers live only in `param` lines. Each `param` line names its layer, value status and source. A value that has not been sourced is written `open`. It evaluates to unknown, so ORI never has to invent a number.
- **Explicit uncertainty.** Missing or unconfirmed evidence gives `unknown` and never `fail`. A model that simply lacks an element is not evidence that the element is absent.
- **Judgment stays human.** Where a provision needs judgment, the rule says `reviewer` and names the ambiguous terms, in 4 words or fewer each.
- **ORI's words only.** Strings are short labels or locators, at most 16 words. They never use model-code register, and the compiler rejects the word "shall". The unit's `paraphrase` is generated from the logic (section 8).

## 3. What a statement looks like

```
rule R311.7.5.1:riser-height-max
  cite IRC 2021 R311.7.5.1 part "maximum riser"
  adopt us-va:vrc-2021 mode replaces_value status sourced_primary by source:va:13vac5-63-210 item "310.8 item 20"
  link https://codes.iccsafe.org/content/VARC2021P1/chapter-3-building-planning
  subject stair_flight is IfcStairFlight
  measure riser_heights from tread_nosing to tread_nosing along plumb
  param max_riser_height <= 7.75 in at base status sourced_secondary source source:secondary:sma-2021-irc-visual
  param max_riser_height <= 8.25 in at us-va:vrc-2021 status sourced_primary source source:va:13vac5-63-210 locator "310.8 item 20"
  require each riser_heights <= max_riser_height
  check riser_height_max
end
```

The compiler renders this rule as the following sentence, which becomes the unit's paraphrase:

> For a stair flight: every riser height is at most max riser height. Values: max riser height 7.75 in (base model), 8.25 in (us-va:vrc-2021).

## 4. IP position summary

This section is not legal advice. It is flagged for legal review.

- **Interpretation, not reproduction.** A statement holds only these things:
  - section numbers;
  - bare numeric values with their sources;
  - ORI's own identifiers;
  - short part labels and locators;
  - named ambiguous terms of 4 words or fewer;
  - official links.
  
  It holds no sentences, headings or definitions from the code. It follows `docs/CITATION-POLICY.md`: cite, interpret and link.
- **Not a derivative of the code's expression.** ORI-CL does not follow the code's wording, headings or organization.
  - The logic is restated in a fixed grammar with ORI's vocabulary.
  - One provision may become several rule units, for example riser height and riser uniformity.
  - The generated paraphrase is produced from the logic, not from the text.
- **Defined terms by citation.** Where the law defines a term, ORI-CL names it and cites where it is defined. The vocabulary records, for example, "Habitable Space, defined at IRC R202, as adopted by VRC (R202)" with `definition_copied: false`. The definition is never stored.
  - Term presence was checked by name only against a secondary publication (UpCodes VRC 2021 Chapter 2) on 2026-09-28.
  - ICC Digital Codes returns 403 to automated fetches, so the primary check is UNVERIFIED.
- **Vocabulary from open sources.** Each term records its source and license (section 5). Restricted classifications are excluded, and the reasons are recorded.
- **Enforcement.** Four mechanisms enforce these rules:
  1. The compiler's static checks.
  2. The `ori-cl-statement` conformance rule, which compiles the statement and then runs `no-code-text` and `rule-unit-authority` on the output.
  3. `conformance/validate.py`, which compiles every `rules/**/*.oricl` file.
  4. The repository code-text lint, which now also covers `.oricl`, `.ebnf` and `vocab/`.
- **Linguistic study** (section 9). This stores statistics, section ids and SHA-256 digests only.
- **Plain names are free; expression is not** (decision `plain-names-free`). The term merger study (`docs/TERM-MERGER-METHOD-DRAFT.md`, DRAFT) sorts every vocabulary term and paraphrase clause into (a) free names, (b) technical terms used with a citation, and (c) phrasing ORI must re-express where it matches the code. It is analysis to inform counsel, not a legal conclusion.
- **Open legal questions:**
  - whether using IFC identifiers is compatible with CC BY-ND 4.0 (see below);
  - the status of the MasterFormat litigation;
  - whether per-section statistics and digests of a copyrighted text raise any issue.

## 5. Vocabulary rules and license findings

Rules, which `ori-cl-vocabulary-provenance` enforces:

1. Every term (keyword, unit, subject, fact, relation, IFC name, reference geometry, defined term, and every `maps_to` or `also` link) records a `source` and a `license`.
2. A source must be declared under `sources` with its license, license evidence (fetched URLs), use position and `allowed: true`.
3. A source that names MasterFormat, UniFormat, OmniClass, ASTM E1557 or ICC headings is rejected, even if it is marked allowed.
4. No definition text may be stored. Defined terms record `definition_copied: false`.

The license pages were fetched on 2026-09-28 (details are in `vocab/ori-cl-vocab-0.1.json`):

| Source | License found | Use in ORI-CL |
|---|---|---|
| IFC 4.3 (buildingSMART) | **CC BY-ND 4.0**, confirmed on three pages: technical.buildingsmart.org/standards/ifc, the IFC4.3.x-development repository LICENSE, and the IFC 4.3 HTML documentation footer. The repository LICENSE.md also carries a legacy notice: the documentation may be used in software development with full attribution, and changes to the specification need consent. The IDS repository is also CC BY-ND 4.0. | Entity, enumeration, Pset and Qto **names** only, as references with attribution. No definitions are copied, and the specification is not modified. **Legal review:** confirm that using identifiers is not an adaptation under ND. |
| NIST SP 330 / SP 811 | NIST web information is public information that may be copied, except material marked as copyrighted (nist.gov/oism/copyrights). | Unit names, symbols and exact factors. |
| UCUM | UCUM License 1.1: royalty-free, no-charge, **revocable**, for interoperating software; attribution conditions apply. | The UCUM code is recorded next to each unit for interoperability only. |
| QUDT | CC BY 4.0 (qudt.org). | Quantity-kind names. |
| ORI-coined words, ORI Psets | CC0 (repository). | Keywords, facts, reference geometry, `Pset_ORI_*`. |
| Law (IRC as adopted by VRC; 13VAC5-63-210) | Citation only. | Defined-term names and section citations only. |
| **MasterFormat** (CSI) | CSI's FAQ says its content is protected by copyright and used under a EULA, and that commercial use in a derivative product needs CSI contact. CSI's licensing channel says software needs a license. Trade press reports a 2026-09-01 C.D. Cal. summary judgment finding MasterFormat numbers, titles and taxonomy not protectable by copyright. The court order itself was not fetched (UNVERIFIED), and an appeal and contract terms remain. | **Excluded.** |
| **UniFormat** (CSI) | No open license; the licensing channel requires a license for digital systems. | **Excluded.** |
| **UNIFORMAT II** (ASTM E1557) | The ASTM page returned 403; ASTM sells the standard under copyright (UNVERIFIED). | **Excluded.** |
| **OmniClass** (CSI) | The single-user EULA forbids incorporating any portion into commercial software or information products, and CSI may terminate it at any time. omniclass.org did not respond. | **Excluded.** |
| Uniclass (NBS), downloaded tables | **CC BY-ND 4.0**, stated on the download page (uniclass.thenbs.com/download): anyone may share and apply the tables on any personal or commercial project, but should not adapt them or add their own codes. The CC deed allows sharing for any purpose, even commercially, with credit, a license link and an indication of changes, and bars distributing a remixed or transformed version. The **Uniclass API** is under separate, revocable NBS terms that bar derivative works and commercial distribution of API data without consent (cl. 3.7.5); the NBS website itself is all rights reserved. CC BY-ND is not on the Open Definition's conformant list. | **Candidate only** (`candidate_sources.src:uniclass`, `allowed: false`, zero terms imported). If adopted: codes and titles referenced verbatim, unmodified, with attribution and the CC BY-ND notice, in a mapping field beside ORI's own term, never through the API. **Legal review:** whether a published ORI-to-Uniclass mapping is an adaptation. |

**Recorded decisions** (Jeremiah Horstick, 2026-09-28; `decisions` in the vocabulary):

- `ifc-names-only`: keep IFC 4.3 names, names only, with attribution and no definitions. **Legal review before publication stays flagged.**
- `csi-classifications-excluded`: MasterFormat, UniFormat, OmniClass and UNIFORMAT II stay excluded until the MasterFormat appeal and the CSI contract (EULA) questions are settled. `vocab.py` rejects them as sources and as candidates.
- `uniclass-candidate`: Uniclass is recorded as a candidate with its license evidence; no terms are imported.
- `plain-names-free`: plain names of physical things are used as is, and ORI does not coin substitutes. What must not be copied is the code's expression. The term merger study (`docs/TERM-MERGER-METHOD-DRAFT.md`) sorts every term into free names, cited technical terms, and phrasing ORI must re-express. It is analysis to inform counsel, not a legal conclusion.

## 6. Grammar

The full grammar is in `spec/ori-cl-0.1.ebnf`. Clause forms:

| Need | Clause |
|---|---|
| Authority / citation | `cite <CODE> <edition> <section> [part "<label>"]`, `link <official https URL>` |
| Jurisdiction override | `context layer ...` (file header), `adopt <layer> mode <mode> status <status> by <source> [item "<locator>"]` |
| Applicability | `subject <kind> is <IfcEntity> [PREDEFINED]`, `when <condition>`, `unless <condition>` |
| Quantity constraints | `require each X <= P` (every value), `require spread X <= P` (uniformity / tolerance), `require X between P1 and P2` (range), `require X >= P [bound Y]`, `require X present` |
| Measurement method | `measure X from <geometry> to <geometry> [along <geometry>] [within P]` |
| Relationships | `encloses`, `adjacent`, `above`, `distance <IfcEntity> <cmp> P` (as a requirement or a condition) |
| Exceptions | `except when C allow P2` (relaxed), `except when C use P2 [optional]` (alternative), `except when C reviewer` |
| Judgment | `reviewer terms "<term>" ...` |
| Binding | `check <function>` (existing `rules.py` function) |
| Quantities | `param P <cmp> <number or open> <unit> at <base or layer> status <status> source <source> [locator "..."] [when F is V]`, `derive A is B times C` |

## 7. Semantics

Evaluation is deterministic. It uses three-valued logic (true, false, unknown), and for a given plan, jurisdiction and subject it always gives the same result.

### 7.1 Jurisdiction resolution

The compiler writes `base` parameters into `base_model.parameters` and layer parameters into `jurisdiction_layers[]`. Layers take precedence in the order of their `adopt` lines.

Resolution is `ori_verify.units.resolve`, the same function the existing checks use:

1. Start from the base.
2. Apply the jurisdiction's layers in ascending precedence.
3. A layer parameter replaces the base parameter with the same name.
4. `mode deletes` makes the rule not applicable.

An `open` parameter is not written as a parameter; it is listed under `ori_cl.open_parameters`. It therefore resolves as undefined and gives unknown / `parameter_missing`.

### 7.2 Evaluation order

| Step | Result when it stops |
|---|---|
| 1. Subject kind differs | not_applicable / `subject_kind_not_applicable` |
| 2. Resolved layer deletes the rule | not_applicable / `deleted_by_jurisdiction` |
| 3. A required parameter is undefined or open (`use ... optional` parameters are not required) | unknown / `parameter_missing` |
| 4. An `unless` condition is true | not_applicable / `exception_applies` |
| 5. A `when` condition is false | not_applicable / `trigger_not_met` if it compares a quantity or relation, else `use_not_covered` |
| 6. The rule has `reviewer terms` | unknown / `reviewer_determination_required` (never fail) |
| 7. `require`, with exceptions | pass, fail or unknown as below |

In steps 4 and 5, every fact the condition reads must be known. If one is absent, or present with a null value or an empty list, the result is unknown / `missing_information`. If one is present but unconfirmed (`vector_extracted_unconfirmed`, `ai_extracted_unverified`), the result is unknown / `unconfirmed_extraction`; unconfirmed wins over missing. An enumerated value outside the vocabulary's `values` also gives unknown / `missing_information`.

### 7.3 Requirement forms

The comparison tolerance is 1e-6 in the parameter's unit. It absorbs floating-point noise only and is not a construction tolerance. Comparators come from the parameter, and the compiler checks that the `require` line uses the same one.

- **`each X cmp P`**: pass when every value passes (`threshold_met`), otherwise fail (`threshold_not_met`). With `empty absent`, a usable empty list means nothing was found to measure: unknown / `required_element_not_found`.
- **`spread X cmp P`**: compares the maximum minus the minimum. Fewer than two values gives not_applicable / `single_value`.
- **`X between P1 and P2`**: an inclusive range.
- **`X cmp P`**: a single value.
  - **`derive X is A times B`**: if X is absent, it is computed from A and B with an exact unit factor taken from the SI factors. For in × in to ft2 the factor is exactly 1/144.
  - **`bound Y`**: Y is the best case for X; for example, the clear-opening bottom can only be at or above the frame bottom. If X is absent and Y already fails, the result is fail. If Y passes, the result is unknown / `missing_information`.
- **`X present`** (boolean): unknown or unusable gives unknown / `required_element_not_found`. True gives pass / `requirement_met`, and false gives fail / `requirement_not_met`.
- **Relations** read facts named `encloses:<IfcEntity>[:<PREDEFINED>]`, and likewise for `adjacent:`, `above:` and `distance:`. `encloses` means a count of at least one.
  - A count of zero, or false, from an IFC origin gives unknown / `required_element_not_found`, because absence from a model is not evidence of absence.
  - Only declared or confirmed evidence of absence gives fail.
  - `distance` is a length compared like `X cmp P`.

### 7.4 Exceptions

These apply only to `X cmp P`.

- **`except when C use P2 [optional]`**: if C is known true, P2 replaces P before the test. Otherwise P is tested.
  - If P fails but P2 would pass and C is unknown, the result is unknown (missing or unconfirmed).
  - If C is false, the result is fail.
  - With `optional`, an undefined P2 skips the exception.
- **`except when C allow P2`**: if P passes, the result is pass.
  - If P fails and P2 also fails, the result is fail.
  - If P2 passes: C true gives pass / `threshold_met_exception`, C false gives fail, and C unknown gives unknown.
- **`except when C reviewer`**: this applies only when P fails.
  - C true gives unknown / `exception_requires_reviewer`.
  - C unknown gives unknown (missing or unconfirmed).
  - C false gives fail.

### 7.5 Change to the existing checks

Writing the semantics down exposed one inconsistency in `verification/ori_verify/rules.py`:

- `ceiling_height_min` and `guard_height_min` reported `missing_information` when the condition fact (sloped ceiling, stair open side) was present but unconfirmed.
- `eero_net_clear_area` reported `unconfirmed_extraction` in the same situation.

All three now use `_condition_unknown_reason`: absent gives `missing_information`, and present but unconfirmed gives `unconfirmed_extraction`. Only the reason code changed; the state (unknown) is the same. The example reports did not change when regenerated. A test was added to `tests/test_rules.py`.

## 8. Compilation

`compile_document` checks each rule, then emits `{"unit": ..., "plan": ...}`.

Static checks (any error stops compilation and reports line numbers):

- vocabulary membership for facts, units, subjects, IFC names and geometry;
- that a fact belongs to the rule's subject kind;
- parameter declaration, comparator and unit agreement;
- that the rule-id section matches the `cite` line;
- an official link host (the same list as `no-code-text`);
- an `adopt` line for every layer used;
- no parameters at a deleting layer;
- datatype fit of each form;
- for judgment rules: no `require` or `check`, and terms of 4 words or fewer;
- no model-code register and short strings;
- that a `check` function exists and runs on the same subject kind.

The unit:

- **Schema.** It is valid against the rule-unit and core schemas. Its `check_class` is `judgment` for reviewer rules, `geometric_deterministic` when a geometric fact is used, and otherwise `data_check`.
- **Evaluator.** This is `human_reviewer` for judgment rules, `rules.py#<check>` when bound, and otherwise `verification/ori_cl/evaluator.py#evaluate_plan`.
- **Prose.** `title` and `paraphrase` are generated from the logic. `source_url` and `source_links` come from `link` lines.
- **`ori_cl` block.** This carries the rule id, a SHA-256 of the canonical statement, the open parameters and the reviewer terms.

Equivalence proof (`tests/test_ori_cl.py`) for the 14 implemented Chapter 3 checks:

1. The compiled base and VRC parameters equal the collection's: name, comparator, value, unit, value status, source, `applies_when` and locator. The compiled layers also match the collection on mode, status and item.
2. The ORI-CL evaluator and the existing function give the same `(state, reason_code)` under both Virginia and the IRC base. The subjects come from:
   - the three IfcOpenShell fixture models (pass, fail and incomplete, extracted by `ifc_extract`);
   - the declared and extracted-candidate examples;
   - a synthetic battery of 5,539 subjects covering boundaries, empty lists, missing, null and unconfirmed facts, sloped-ceiling, grade-floor and stair-side cases, and sill versus frame bottom.
   
   Across both jurisdictions this is more than 150,000 comparisons, all identical. Reverting the section 7.5 alignment makes the test fail, which shows the test is sensitive to real differences.
3. The equivalence also holds with the layer set to delete and with a required parameter removed.

## 9. Linguistic study method (no code text stored)

The tool is `python -m ori_cl.corpus_stats INPUT.txt --out stats.json`, run from `verification/`.

**Input.** A local text file that the analyst may lawfully read. It is never committed or published.

**Output.** One record per section id with:

- a SHA-256 of the whitespace-normalized section text, after the id; this lets anyone holding the same text confirm which version was counted;
- word and sentence counts;
- counts of modal verbs (shall, shall not, must, may, should, is/are permitted, is/are required, is/are not required);
- counts of ambiguity markers, from ORI's own list (approved, adequate, sufficient, suitable, reasonable, acceptable, substantial, readily, properly, equivalent, similar, as required, where required, where applicable, as necessary, or other, and/or, building official, manufacturer's instructions);
- counts of cross-references (section, table, figure, chapter, bare section ids, external standards);
- counts of ORI-CL fact labels and defined-term names.

**Never stored.** Sentences, phrases, n-grams, headings or section titles.

**Guard (strict, enforced).** `assert_no_text` compares every output string with the input and fails on **any** shared run of 6 or more words, whatever it contains (decision of 2026-09-28; no relaxed rule is used as a gate). Six words, because an allowed defined-term name can itself be 5 words long. The same strict rule gates the term merger output (`assert_output_clean`), the `term_merger scan` command and the repository-wide strict scan in the conformance suite (`verification/tests/test_strict_safeguard.py`, skipped only where the local code copies are absent). The refined classification of runs (`term_merger.shared_runs` with free terms: a run made only of category (a)/(b) terms, numbers, units and function words) is an informational report only, never a gate.

**Splitting.** A section starts at an id that is followed by a capitalized word and not preceded by a cross-reference word (Section, Table, and, of, ...). Repeated ids, such as a table of contents, are merged.

**First run.** The input was the VRC 2021 Chapter 3 text as rendered by UpCodes (analyst copy, not in the repository). The result is `research/data/vrc2021-ch03-language-stats-DRAFT.json` (DRAFT; flagged for legal review before publication).

| Measure | Result |
|---|---|
| Section ids | 416 |
| Words | 32,617 |
| shall / shall not | 805 / 97 (27.65 per 1,000 words) |
| may / must / should | 5 / 1 / 1 |
| is/are permitted | 30 |
| is/are required / is/are not required | 22 / 32 |
| Ambiguity markers | 163 (5.0 per 1,000 words) |
| Most frequent markers | approved 46, or other 30, similar 13, equivalent 12, building official 11 |
| Cross-references | 313 "Section" references, 41 table, 36 figure, 60 chapter, 149 external-standard, 376 bare section ids (the bare count includes ids inside the other forms) |

Caveats: this is a regex heuristic, and the last section (R336) also absorbs trailing page material.

**Tie to interpretability.** Marker counts per section are a screening signal for the interpretability rubric (`spec/interpretability-0.1-draft.md`). They are not a score. In 0.1, the terms in a judgment rule's `reviewer terms` must equal that unit's `interpretability.ambiguous_terms` (a test enforces this).

## 10. Examples (from `rules/irc2021/ch03/ori-cl/`)

**Uniformity (tolerance):**
```
require spread riser_heights <= max_riser_variation
```

**Applicability, and an exception that needs a reviewer (R305.1):**
```
when space_use in [habitable kitchen hallway]
require ceiling_height >= min_ceiling_height
except when sloped_ceiling is true reviewer
```

**Exclusion (R304.1):**
```
unless space_use is kitchen
when space_use is habitable
require floor_area >= min_habitable_room_area
```

**Derived quantity and relaxed threshold (R310.2.1 net clear area):**
```
derive net_clear_area is net_clear_height times net_clear_width
require net_clear_area >= min_net_clear_area
except when grade_floor_or_below_grade is true allow min_net_clear_area_grade_floor
```

**Bound (R310.2.3):** the clear opening cannot sit lower than the frame.
```
require sill_height <= max_sill_height bound frame_bottom_height
```

**Trigger with a measurement band (R312.1.1):**
```
measure drop_height from walking_surface_top to lower_surface_top along plumb within guard_trigger_horizontal_band
when drop_height > guard_trigger_drop
require guard_present present
```

**Alternative threshold (R312.1.2):**
```
except when on_stair_open_side is true use min_guard_height_stair_open_side optional
```

**Relationship data check (R314.3):**
```
subject space is IfcSpace
when sleeping_room is true
require encloses IfcSensor SMOKESENSOR
```

**Virginia override with the base not yet sourced (R324.6.2):**
```
param min_pv_ridge_setback >= open in at base status estimate source source:icc:irc-2021 locator "base value not yet sourced"
param min_pv_ridge_setback >= 18 in at us-va:vrc-2021 status sourced_primary source source:va:13vac5-63-210 locator "310.8 item 39"
require ridge_setback >= min_pv_ridge_setback
```

**Unsourced clearance (R302.14):** evaluates to unknown / `parameter_missing` in every jurisdiction.
```
param insulation_clearance >= open in at base status estimate source source:upcodes:vrc-2021-ch03 locator "value not yet recorded by ORI"
unless listed_for_insulation_contact is true
require distance IfcCovering INSULATION >= insulation_clearance
```

**Judgment (R311.1):**
```
reviewer terms "continuous and unobstructed"
```

## 11. IFC binding

`ori_verify.ifc_extract` measures the geometry for the five implemented subject kinds. `ori_cl.ifc_bind` adds three things, driven by the vocabulary:

- subjects for other kinds, one per matching element (e.g. `building` for IfcBuilding, `pv_array` for IfcSolarDevice SOLARPANEL);
- property facts from `ifc_read` (Pset and property name);
- `encloses:` counts through IfcRelContainedInSpatialStructure. For a space, this includes its child spaces; for a building, everything under it.

`adjacent`, `above` and `distance` are not measured from IFC in 0.1. They come from declared values, and without them the rule is unknown.

## 12. Open questions

1. **IFC CC BY-ND 4.0.** Decided 2026-09-28: keep IFC names (names only, attribution, no definitions). Legal review before publication remains open.
2. **MasterFormat ruling (2026-09-01, C.D. Cal., reported).** Decided 2026-09-28: all CSI classifications stay excluded until the appeal and contract questions settle.
3. **Uniclass.** License read 2026-09-28 (section 5): CC BY-ND 4.0 for the downloaded tables. It is recorded as a candidate. Open: adopt it as a mapping layer at all (it is a UK system), and have counsel confirm that a mapping is not an adaptation.
4. **Committing statistics.** Commit derived statistics for ICC-published text (`research/data/vrc2021-ch03-language-stats-DRAFT.json`), or keep them local until legal review?
5. **Evaluation order.** Parameters are checked before `unless`, which matches the existing checks. So a listed device with an unsourced clearance (R302.14) is unknown rather than not applicable. Keep this?
6. **PV setback measurement.** `along roof_plane` is ORI's reading and is UNVERIFIED. The alternative is a horizontal projection.
7. **Judgment terms.** Should `reviewer terms` be required to equal the interpretability `ambiguous_terms` (current tests), or only be a subset of them?
8. **Keyword count.** 58 keywords. Merge some (for example `unless` into `when not`), or keep them for readability?
9. **Declared relation facts.** Add `adjacent`, `above` and `distance` to the declared-values schema?

## 13. Limits of 0.1

- Exceptions apply to single compared quantities. Conditions do not nest.
- There is no arithmetic beyond `derive` (length × length to area).
- `ifc_bind` handles containment and properties only.
- The data-check and judgment samples are not wired into the Chapter 3 collection or the verification reports. They are compiled, validated and tested separately.
