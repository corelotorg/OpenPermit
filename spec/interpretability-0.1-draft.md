# ORI Interpretability — v0.1 Draft

Status: DRAFT. Schema: the optional `interpretability` object in
`ori-rule-unit-0.1.schema.json` (`$defs/interpretability`). Conformance rule:
`interpretability-is-evidence`. Worked example: `rules/irc2021/ch03/interpretability-ch03.json`,
merged into the Chapter 3 collection by `build_units.py`.

To finish: two independent human reviewers score the Chapter 3
units using §4. They should also confirm or change the provisional decisions in §8. Until
then, every score in the repository is an ORI **pre-score** (`scoring_status: estimate`).

> An interpretability record is analysis for code development and plan review. It never
> changes what a provision requires, and it is not an official interpretation. Only the
> building official, the local board of appeals and the State Building Code Technical Review
> Board decide what the USBC means for a given case. A candidate clarification is ORI's
> suggestion, not proposed code text, and nothing is submitted to a code body without the
> owner's decision.

## 1. The idea

Some provisions can be read only one way. Others need a reader to decide what a word means,
what the provision is for, or which of two provisions controls. That interpretive load is a
property of the text, and it can be measured. Two signals measure it:

1. **A rubric score.** Reviewers read the provision and answer four fixed questions.
2. **Evidence of real disputes.** These are published interpretations, appeal decisions,
   staff opinions and local policies that had to settle or operationalize the provision.

A provision with a high score and direct evidence is a candidate for a clarity report to the
code development cycle.

Interpretability is independent of `check_class`, which asks whether a check can be computed.
The two cross:

- A geometric rule can hide an ambiguous term. R312.1.1 computes a 30 in drop at 36 in, but
  "open-sided walking surfaces" is undefined.
- A judgment rule can be perfectly clear. R301.7 gives numeric deflection limits, and the
  judgment lies in the structural analysis.

## 2. Rubric (ori-interpretability-0.1)

Ask the questions in order. The first "yes" sets the score.

| Order | Question | If yes, score |
|---|---|---|
| Q1 | Do two provisions that apply to the same condition point to incompatible outcomes? This includes a state amendment and the base text it leaves in place, or a section and the standard it references. | `conflicting` |
| Q2 | Does compliance turn on purpose, adequacy, or an official's judgment that the text leaves open? Examples: "approved", "accepted engineering practice", performance outcomes with no stated test, or a rule the text implies but never states. | `intent_dependent` |
| Q3 | Does an undefined or loosely defined term change the outcome for a realistic single-family case? | `ambiguous_term` |
| — | None of the above. | `clear` |

Rules for answering:

- **Read the adopted text.** For Virginia, that is the 2021 VRC: the IRC base with the
  13VAC5-63-210 amendments, effective 2024-01-18. Record the text source in
  `scored_text_source`. Do not score the 2024 IRC; it is comparative only.
- **Check definitions before calling a term ambiguous.** Look in IRC Chapter 2 and, for
  administrative terms, VCC Chapter 2. Set `defined_in_code` to true or false, or to null if
  you did not check. A defined term can still be ambiguous (Q3) if the definition does not
  settle the case. A term whose definition leaves acceptance to the building official
  (such as "approved", R202) points to Q2.
- **"Realistic" means a condition that occurs in ordinary detached single-family work.** A
  reviewer should be able to name the case.
- **Score only the provision in front of you.** A referenced standard gets its own record if
  it needs one.
- **Record the reasoning.** `rationale` names the deciding question. `ambiguous_terms[]`
  lists short terms (60 characters or fewer, never long quotations). `intent_questions[]`
  lists what a reviewer must decide. `conflicts_with[]` lists the competing provisions.

The ordinal order `clear < ambiguous_term < intent_dependent < conflicting` is used only to
compute agreement statistics (§4.4). It is not a severity ranking. Some provisions are
intent-dependent on purpose; for example, performance-based structural rules need
engineering judgment.

## 3. Evidence

### 3.1 What may be linked

Link only records that ORI **fetched and read**. The schema requires
`verification.status = fetched_and_read`, an https URL and the fetch date. The Chapter 3
records also carry the file's SHA-256. Nothing is cited from memory. Every record states:

| Field | Meaning |
|---|---|
| `citation`, `date`, `body`, `url` | As printed on the record. |
| `body_class` | `state_review_board_interpretation`, `state_review_board_appeal_decision`, `state_agency_staff_opinion`, `local_building_official_policy`, `local_board_of_appeals_decision`, `model_code_publisher_staff_opinion`, `model_code_committee_interpretation`, `court_decision`. |
| `binding_effect` | Plain statement of its legal weight. In Virginia, the Review Board's formal interpretations are published for statewide use. Appeal decisions are case-specific final orders. SBCO staff opinions are informal. A local policy binds one jurisdiction. |
| `code_at_issue`, `section_at_issue` | The code and edition the record applied, which is often older than 2021. |
| `edition_carryover` | `same_section_verified`, `renumbered_verified` or `not_verified`. Use `not_verified` unless the older text was actually compared. |
| `holding_summary` | ORI's own short summary (600 characters or fewer). |
| `relevance` | `direct` if the record resolves a wording question about this provision. `indirect` if it applies the provision, or a neighbouring one, without resolving wording. |

### 3.2 Where records go

- **`determinations[]`**: state-level and board records.
- **`local_operationalizations[]`**: local policies that turn an open provision into a fixed
  local method. They show interpretive load, but they bind only one jurisdiction, and the
  conformance rule rejects them under `determinations[]`.

### 3.3 Evidence strength

`evidence_strength` is the strongest `relevance` among the linked records. `none_found`
means ORI searched the sources in `research/va-code-interpretations-sources-2026-09-28.md`
and found nothing. It is **not** evidence that the provision is clear or that no dispute has
ever occurred.

### 3.4 Evidence does not change the score

A score comes from the text. Evidence supports the score or prompts a re-read; it never sets
the score by count. A provision can score `clear` and still have linked records. For
example, R311.4 has a 2018 dispute that the model code has since fixed.

## 4. Two-reviewer scoring method

### 4.1 Roles

| Role | Who | Counts toward agreement |
|---|---|---|
| `pre_scorer` | ORI (agent or analyst). Produces the pre-score, rationale and evidence links. | No |
| `reviewer` | A person with code-enforcement, design or code-development experience. Two per unit. | Yes |
| `adjudicator` | A third person, used only when the two reviewers disagree. | Resolves |

### 4.2 Procedure

1. **Freeze the packet.** For each unit, export:
   - section and edition;
   - a link to the adopted text (reviewers read it in their own licensed or public copy;
     ORI does not redistribute ICC text);
   - the Virginia amendment item, if any;
   - the linked records, with holdings.

   Leave out the ORI pre-score and the other reviewer's score. The maintainers' reviewer pack
   (generated from the Chapter 3 collection, kept outside the public release) has everything needed,
   and reviewers should cover the score column when they score blind.
2. **Score independently.** Each reviewer applies §2 and records:
   - the score;
   - the deciding question (Q1, Q2, Q3 or none);
   - the terms or questions;
   - their time spent.

   Reviewers must not confer before submitting.
3. **Record.** Add both reviewers to `reviewers[]` with `independent: true` and
   `role: reviewer`.
4. **Compare.**
   - Same score: set `scoring_status: two_reviewer_agreed`.
   - Different scores: a third person reads both rationales and the text and records a
     score. Set `scoring_status: adjudicated` and keep all three entries.
5. **Report agreement per batch** (§4.4) before any clarity report cites the scores.
6. **Re-score when the text changes.** This covers a new Virginia amendment, a new edition,
   or a Review Board interpretation that changes how a term is read. Keep the old record in
   git history.

### 4.3 Reproducibility

The inputs (unit id, text source, edition) and outputs (scores, rationales, reviewers) are
stored in the repository. Anyone with access to the adopted text can re-run the procedure on
the same units and compare. The rubric version is recorded so that later rubric changes do
not silently alter old scores.

### 4.4 Agreement statistics

For each batch (for example, one chapter), report:

- the number of units scored;
- raw agreement (the share of units where both reviewers agree);
- Cohen's kappa over the four categories, and linearly weighted kappa using the ordinal
  order in §2;
- the confusion matrix.

Working threshold, **provisional**: if weighted kappa is below 0.6, revise the rubric wording
or the reviewer guidance and re-score a sample before publishing scores for that batch. The
0.6 value is a common rule of thumb for "substantial" agreement. It is an ORI working choice,
not a sourced standard for this task.

## 5. Candidate clarification

`candidate_clarification` holds ORI's suggested direction in its own words, not proposed code
text. It has two more fields:

- **`status`**: always `DRAFT_not_submitted`.
- **`venue`**:
  - `virginia_code_development_cycle` for Virginia-written text (a 13VAC5-63 amendment) or a
    Virginia-specific need. Virginia runs its cycle through cdpVA and DHCD workgroups; the
    2024 cycle page shows stakeholder workgroups in 2025–2026.
  - `icc_code_development_cycle` for unamended model-code text.
  - `local_policy` where the right fix is a local method.
  - `none`.

A clarity report may cite these notes only after two-reviewer scoring (§4) and the owner's
decision.

## 6. Conformance

The rule `interpretability-is-evidence` (`conformance/semantic.py`) enforces the following.
It runs on every rule-unit collection in `validate.py` and has one positive and three
negative cases:

- Every linked record is `fetched_and_read` from an https URL.
- Local policies appear only under `local_operationalizations[]`.
- Candidate clarifications stay `DRAFT_not_submitted`.
- `two_reviewer_agreed` needs two independent reviewers with the same score, and
  `adjudicated` needs at least two. Pre-scores never count.
- `evidence_strength` is consistent with the linked records.

The schema adds that `ambiguous_term` needs at least one term, `intent_dependent` needs at
least one question, and `conflicting` needs at least one competing provision.

## 7. Backward compatibility

`interpretability` is optional. Existing rule units and collections stay valid, and a unit
without it is **not scored**. Unscored does not mean clear.

## 8. Provisional decisions (pending maintainer review)

1. **Four categories with first-yes precedence.** An alternative is multi-label scoring
   (a provision can be both ambiguous and intent-dependent). The first-yes rule keeps
   agreement statistics simple.
2. **Evidence never sets the score.** It is linked and summarized, but not counted into it.
3. **Weighted-kappa threshold of 0.6** before scores are published (§4.4).
4. **Venue split.** Virginia-written text goes to the Virginia cycle; unamended IRC text
   goes to the ICC cycle. This is noted per candidate clarification.
5. **Older-edition records are linked with `edition_carryover: not_verified`** rather than
   excluded. The evidence is useful even when the section has been renumbered.
