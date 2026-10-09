# ORI rule units (DRAFT)

A **rule unit** is one checkable obligation, for example the maximum stair riser height,
cited by code section and edition. It carries:
- a model-code base value;
- each jurisdiction override layer, with its own authority and provenance;
- a check class;
- the information it needs;
- the result states an evaluator may emit.

Schema: `spec/ori-rule-unit-0.1.schema.json`. Prose: `spec/rule-unit-0.1-draft.md`.

Every rule unit is also a valid ORI core `Requirement` (`spec/ori-core-0.1.schema.json`).
`conformance/validate.py` checks both schemas plus the `rule-unit-authority` semantic rule.

> Rule units and any machine result computed from them are reviewer evidence, not approval.
> They are not the code. ORI cites, paraphrases and links; it never reproduces code text
> (`docs/CITATION-POLICY.md`). Titles are ORI descriptions of effect (not ICC headings),
> paraphrases are ORI's own words, values are bare numbers, and every unit links to the
> official text (`source_url`, `source_links`). Conformance rule `no-code-text` enforces the
> structural part of this.

## Contents

| Path | What |
|---|---|
| `irc2021/ch03/build_units.py` | Single source of truth for the Chapter 3 worked example. Edit here, then run it. |
| `irc2021/ch03/va-vrc-2021-ch03.units.json` | Generated collection: 199 units for R301–R327, plus 6 for the Virginia-added R331–R336. |
| `irc2021/ch03/CHAPTER-3-TABLE.md` | Generated readable table: class split, implemented values, all units. |
| `irc2021/ch03/ids/*.ids` | IDS 1.0 information requirements for the implemented units (stairs, spaces, EERO, guards). |
| `irc2021/ch03/paraphrases-ch03.json` | ORI paraphrase of every unit's effect (205 entries), merged by `build_units.py`. ORI text only (CC0). |
| `irc2021/ch03/interpretability-ch03.json` | Hand-maintained interpretability pre-scores and linked public records; merged into units by `build_units.py`. |
| `irc2021/ch03/ori-cl/ch03-geometric.oricl` | The 14 implemented checks restated in ORI-CL (`spec/ori-cl-0.1-draft.md`); compiled to `ch03-geometric.compiled.json`. |
| `irc2021/ch03/ori-cl/ch03-samples.oricl` | ORI-CL samples: data checks (R314.3, R314.4, R306.2, R302.14), a VRC override with an unsourced base (R324.6.2) and judgment units (R302.7, R311.1, R309.1); compiled to `ch03-samples.compiled.json`. |
| `test_rules_data.py` | Generator in sync; schema validity; every section R301–R327 covered; source ids resolve; IDS refs resolve; judgment units all scored; linked records verified and consistent; reviewer pack in sync where the maintainers' reviewer-pack generator is present (skipped otherwise). |

## Scope

- Detached single-family dwellings only.
- The base model is the 2021 IRC, which is not binding by itself.
- The first override layer is the 2021 Virginia Residential Code, adopted through
  13VAC5-63-210 (Virginia Construction Code §310), effective 2024-01-18. The 2024 IRC is
  comparative only and not used here.
- This is an example built from public sources. No jurisdiction has reviewed or endorsed it.

## Chapter 3 class split (estimate, pending human review)

| class | units | share |
|---|---:|---:|
| data_check | 112 | 56% |
| geometric_deterministic | 72 | 36% |
| judgment | 15 | 8% |

Virginia-added R331–R336: 3 data_check, 1 geometric_deterministic, 2 judgment.
R328–R330 are outside the requested range and are not classified.

These tags are ORI analyst estimates (`classification_basis: estimate`). No published
classification of the IRC exists. The nearest published analogue is a sentence-level
study of the IBC (Zhang & El-Gohary 2021), which is not IRC data and not comparable
unit-for-unit.

## What is sourced and what is not

| Item | Status | Source |
|---|---|---|
| Section list (numbers only) | sourced (secondary publication of the VRC) | UpCodes, "Virginia Residential Code 2021 based on the IRC 2021", Ch. 3, fetched 2026-09-27 |
| Virginia override mode per section | sourced primary | 13VAC5-63-210 §310.8 "Amendments to the IRC", fetched 2026-09-27. A section missing from the list is recorded as `adopts_base`. |
| §310.8 item numbers | **ORI's own count** of the list entries | should be checked against the regulation before citation |
| R322 items 35–38 | mapped per unit (R322.1: item 35; R322.2: items 35–36; R322.3: items 37–38); **new, needs human check** | 13VAC5-63-210 §310.8, read 2026-09-28 |
| Interpretability scores | **ORI pre-scores** (`scoring_status: estimate`), 29 units | `irc2021/ch03/interpretability-ch03.json`; rubric `spec/interpretability-0.1-draft.md` |
| Linked determinations and local policies | each fetched and read, with SHA-256 | `research/va-code-interpretations-sources-2026-09-28.md` |
| VA numeric values on implemented units | sourced primary | 13VAC5-63-210 (riser 8-1/4 in, tread 9 in, EERO 5.7/5.0 ft², 24 in, 20 in) |
| IRC base values for VA-amended sections | sourced secondary | SMA 2021 IRC Visual Interpretation (riser 7-3/4 in, tread 10 in); Roy City UT 2021 IRC egress handout (EERO), read via search index |
| IRC base values for unamended sections | `inferred_unamended` | Taken to equal the VRC value because §310.8 lists no amendment (headroom 6 ft 8 in, ceiling 7 ft and 6 ft 8 in, room area 70 ft², sill 44 in, guard trigger 30 in and 36 in band, guard height 36 in / 34 in) |
| check_class tags | **estimate** | ORI analyst judgment |

ICC's own viewer blocked automated retrieval on 2026-09-27. No licensed ICC text is used
(provisional decision).

## Regenerate and test

```bash
python rules/irc2021/ch03/build_units.py
python -m pytest -q rules
python conformance/validate.py
(cd verification && python -m ori_cl compile ../rules/irc2021/ch03/ori-cl/ch03-geometric.oricl --out ../rules/irc2021/ch03/ori-cl/ch03-geometric.compiled.json)
(cd verification && python -m ori_cl compile ../rules/irc2021/ch03/ori-cl/ch03-samples.oricl --out ../rules/irc2021/ch03/ori-cl/ch03-samples.compiled.json)
```

## Completion request (DRAFT)

A human reviewer should:
1. confirm or correct each `check_class` estimate;
2. check the §310.8 item numbers against the regulation text;
3. check the new R322 item-to-unit mapping;
4. score the interpretability units independently (two reviewers, spec §4);
5. decide whether primary ICC base text should be licensed.
