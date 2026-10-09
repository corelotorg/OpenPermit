# ORI Rule Unit — v0.1 Draft

Status: DRAFT. Schema: `ori-rule-unit-0.1.schema.json`. Worked example: `rules/irc2021/ch03/`.
Reference evaluator: `verification/`. Completion request: human review of the provisional
decisions in §9 and of the Chapter 3 class tags.

## 1. Purpose

A rule unit makes one code obligation addressable, versioned, jurisdiction-aware and
checkable, without copying the code. It answers six questions:

- Which section and edition is this?
- What does the model code say?
- What does each adopting jurisdiction change, and on what authority?
- Can the check be decided from data, from geometry, or only by judgment?
- What information does it need?
- What may an evaluator conclude?

## 2. Relationship to ORI core

A rule unit is an ORI core object with `type: "Requirement"` and
`rule_unit_profile: "ori-rule-unit-0.1"`.

- It reuses the core envelope: `id`, `version`, `effective_from`, `effective_to`,
  `jurisdiction[]`, `source[]`, `derived_from[]`, `supersedes[]`, `metadata`.
- It must validate against both the core schema and the rule-unit schema.
- Results are core `Verification` objects whose `requirements[]` names the rule-unit id.
- A human decision is a core `Decision`. It may cite Verifications as evidence.
- A machine never emits a `Decision` (core spec §7; conformance rule
  `machine-verification-not-approval`).

## 3. Fields

| Field | Meaning |
|---|---|
| `id` | `urn:ori:rule-unit:<code-family>:<section>[:<part-slug>]` |
| `title`, `paraphrase` | ORI's own words: the title describes the unit's effect (not the ICC heading); the paraphrase (20–400 characters) summarizes what the requirement does. No code text; bare numeric values only (`docs/CITATION-POLICY.md`). Required by conformance rule `no-code-text`. |
| `source_url`, `source_links` | Official link-out for the provision (ICC Digital Codes for the VRC/IRC text, law.lis.virginia.gov for Virginia regulation text, DHCD for Virginia documents). Links only; never cached text. `source_url` is required by `no-code-text`. |
| `source_section` | `{code, edition, section, subsection_part?, chapter}`. For a section a jurisdiction adds, `code` is the jurisdiction's code (e.g. `VRC`). |
| `authority_classification` | Class of the highest-precedence binding layer (`state_adopted_code`, `local_adopted_amendment`), or `model_code_not_adopted` when no layer binds. |
| `check_class` | `data_check`, `geometric_deterministic` or `judgment` (§5). |
| `classification_basis` | How the class tag was assigned. `estimate` until reviewed. |
| `single_family_applicability` | `applies`, `conditional` or `out_of_scope`. Townhouse and two-family provisions are kept only for completeness. |
| `base_model` | IRC 2021: `authority_class: model_code`, `binding: false` (constant), `status: present` or `not_in_base`, plus parameters. |
| `jurisdiction_layers[]` | Override layers (§4). |
| `required_information` | IDS 1.0 reference (`path#specification name`) plus items. Each item gives the IFC path, the declared-value key and what a PDF sheet must show. |
| `inputs[]` | Typed inputs the evaluator consumes. |
| `result_states` | Subset of `pass`, `fail`, `unknown`, `not_applicable`. |
| `unknown_policy` | `missing_information_result` is the constant `unknown`. |
| `evaluator` | `deterministic_function`, `data_lookup`, `human_reviewer`, `human_reviewer_with_machine_assist` or `not_implemented`. |
| `provenance` | Who recorded the unit, when, and which sources were checked. |
| `legal_boundary` | `machine_result_is_approval` is the constant `false`, plus a statement. |
| `interpretability` | Optional. How clearly the provision can be read: rubric score (`clear`, `ambiguous_term`, `intent_dependent`, `conflicting`), scoring status, ambiguous terms, linked public determinations (each fetched and read), local operationalizations, evidence strength and a DRAFT clarification note. Defined in `spec/interpretability-0.1-draft.md`; checked by conformance rule `interpretability-is-evidence`. Absence means not scored, not clear. |

### Parameters and value status

Each parameter has a `name`, a `comparator`, a `quantity` (US customary governs; the SI
value is informational), an optional `applies_when`, a `source`, and a `value_status`:

| value_status | Meaning |
|---|---|
| `sourced_primary` | Read from the adopting authority's own publication or regulation. |
| `sourced_secondary` | Read from a third-party publication of the text, or a jurisdiction handout. |
| `inferred_unamended` | A base value inferred to equal an adopted-code value because the adopting regulation lists no amendment to that section. |
| `estimate` | Analyst judgment, not yet verified. |

## 4. Jurisdiction layers and precedence

The base model has precedence 0. Each layer declares:
- `jurisdiction`, `code`, `edition`, `effective_from`;
- `authority_class`, `binding`;
- an integer `precedence` (higher wins);
- an `override_mode` and a `mode_status`;
- an `amendment_ref` pointing to the adopting instrument (for Virginia, 13VAC5-63-210
  §310.8 with the item number).

Override modes:

| Mode | Resolution |
|---|---|
| `adopts_base` | Base parameters apply unchanged. |
| `replaces_value` | Layer parameters replace base parameters of the same name. |
| `modifies_text` | Wording changed. Parameters, if any, replace by name. |
| `adds_exception` | An exception is added. It is expressed as an extra parameter with `applies_when`. |
| `deletes` | The unit is not applicable under this layer. |
| `adds_section` | The unit exists only in this layer (`base_model.status: not_in_base`). |
| `replaces_section` | The layer's parameters replace the base set. |

Resolution for a jurisdiction J:
1. Start from the base parameters.
2. Apply J's layers in ascending precedence.
3. A `deletes` layer clears the parameters and marks the unit not applicable.
4. Each applied parameter records which layer supplied it, and every Verification lists
   `layers_applied`.

Invariants (conformance rule `rule-unit-authority`):
- A model-code base layer is never binding.
- A unit whose authority is not `model_code_not_adopted` needs at least one binding layer.
- A binding layer must have an adopted-code authority class.
- A `judgment` unit must not have an automated evaluator.

The rule-unit graph is a slice of the ORI regulatory graph. The precedence of layers is
declared data, not an inference; see `precedence-graph-0.1-draft.md` for process
precedence.

## 5. Check classes

- **data_check**: decidable from declared or structured attributes (presence, rating,
  listing, product data, table lookup) without spatial computation.
- **geometric_deterministic**: decidable by a deterministic computation on dimensions or
  model geometry, given the required information.
- **judgment**: needs engineering or official judgment ("approved", structural adequacy,
  path continuity, installation quality). It is never auto-decided. Machine assistance
  may gather evidence.

A class tag describes the check, not the difficulty of producing the information.

## 6. Results

| ORI result_state | core Verification.outcome |
|---|---|
| pass | pass |
| fail | fail |
| unknown | indeterminate |
| not_applicable | not-applicable |

- `metadata.result_state` keeps the ORI name, and `metadata.reason_code` explains it.
- Missing, unreadable, unconfirmed or reviewer-only information yields `unknown`. It
  never yields `fail`.
- Reason codes: `missing_information`, `unconfirmed_extraction`,
  `required_element_not_found`, `exception_requires_reviewer`, `geometry_not_measurable`,
  `parameter_missing`.
- Conformance rule `missing-information-not-fail` rejects a `fail` with one of these codes,
  and rejects any outcome that does not match its `result_state`.

## 7. Information and evidence

- `required_information.ids` points to an IDS 1.0 specification. IDS states which
  properties and representations must exist. IDS cannot express geometric conditions, so
  those live in the evaluator.
- Each information item names where the value comes from in each input path:
  - an IFC path (geometry or property);
  - a declared-value key (`spec/ori-declared-values-0.1.schema.json`);
  - what a PDF plan sheet must show for a reviewer to check a declared value.
- Fact origins:
  - usable: `ifc_geometry`, `ifc_property`, `applicant_declared`, `applicant_confirmed`,
    `reviewer_confirmed`;
  - not usable until confirmed: `vector_extracted_unconfirmed`, `ai_extracted_unverified`.

## 8. Copyright boundary

- Rule units cite sections and record short numeric values.
- Titles and paraphrases are ORI's own.
- ICC model-code text is proprietary and is not reproduced. `LICENSE-SPEC.md` (the per-path licence map) covers
  ORI's specification text, not third-party code text.
- A jurisdiction's regulation (e.g. 13VAC5-63-210) is cited as public law.

## 9. Provisional decisions (pending maintainer review)

1. `unknown` is mapped to core `indeterminate`, with the ORI name and reason code in
   metadata. No new core enum value.
2. A required guard that is not modelled gives `unknown`. One explicitly declared absent
   gives `fail`.
3. IRC base values are secondary-sourced and labelled. No licensed ICC text.
4. The reference node does not index `rules/` or `verification/` yet.
5. Class tags are `estimate` pending human review.

## 10. Legal boundary

A rule unit is not the code, and a machine result is not approval. Both are evidence for a
human reviewer working under the adopted code. Federal guidance (for example HUD
best-practice material) is not local law. It may inform ORI's non-binding targets but never
becomes a rule unit's binding layer.
