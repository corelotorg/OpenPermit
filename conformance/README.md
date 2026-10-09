# ORI draft conformance

This directory contains the first executable conformance surface for the recovery-derived ORI core draft.

## Run

From the repository root:

```bash
python -m pip install -r conformance/requirements.txt
python conformance/validate.py
```

Expected result:

```text
PASS conformance/fixtures/challenge-valid.json
PASS conformance/fixtures/mapping-valid.json
PASS conformance/fixtures/verification-valid.json
```

## Positive semantic cases

`conformance/positive/` holds semantic cases that MUST be accepted. `project-target-non-binding.json` records ORI's 24-hour single-family review target as a non-binding Assertion. Its counterpart, `conformance/negative/project-target-promoted-to-requirement.json`, serializes the same target as a binding `Requirement` and MUST be rejected.

Interpretability (rule `interpretability-is-evidence`, spec `spec/interpretability-0.1-draft.md`): `positive/interpretability-r302-7-interpretation.json` links a fetched-and-read Review Board interpretation and MUST be accepted. Three negative cases MUST be rejected: `negative/interpretability-unverified-citation.json` (a linked record not marked fetched and read), `negative/interpretability-prescore-as-two-reviewer.json` (an ORI pre-score counted as one of two reviewers) and `negative/interpretability-local-policy-as-determination.json` (a county policy filed as a determination). The rule also runs on every unit in the Chapter 3 collection.

No code text (rule `no-code-text`, policy `docs/CITATION-POLICY.md`): `positive/no-code-text-paraphrased-unit.json` MUST be accepted. `negative/no-code-text-missing-paraphrase-and-link.json` (no paraphrase, no official link), `negative/no-code-text-verbatim-quote.json` (a long quoted sentence in code register; the sentence is fictional) and `negative/no-code-text-unofficial-source.json` (a link to an unofficial mirror) MUST be rejected. The rule runs on every collection unit, and `validate.py` also runs a repo-wide lint for quoted code-register text.

ORI-CL (rules `ori-cl-vocabulary-provenance` and `ori-cl-statement`, spec `spec/ori-cl-0.1-draft.md`): `positive/ori-cl-vocabulary-provenance.json` and `positive/ori-cl-statement-riser.json` MUST be accepted. `negative/ori-cl-vocabulary-restricted-source.json` (a term from a MasterFormat-style classification), `negative/ori-cl-vocabulary-missing-license.json` (a term without a license, and a defined term storing definition text), `negative/ori-cl-statement-code-register.json` (a note in code register), `negative/ori-cl-statement-unofficial-link.json` and `negative/ori-cl-statement-long-reviewer-term.json` (a sentence where a term name belongs) MUST be rejected. `validate.py` also checks the vocabulary file and compiles every `rules/**/*.oricl` file; the compiled units must pass the rule-unit schema, `no-code-text` and `rule-unit-authority`.

## What this proves

The current harness proves only that fixture objects conform to `spec/ori-core-0.1.schema.json` under JSON Schema Draft 2020-12.

It does **not** prove legal correctness, jurisdictional applicability, factual truth, or regulatory approval.

## Next conformance layers

1. negative fixtures that MUST fail;
2. graph-edge referential integrity;
3. supersession/effective-time tests;
4. challenge immutability/history tests;
5. precedence DAG cycle detection and topological ordering;
6. derived critical-path/float tests;
7. JSON-LD round-trip tests;
8. source/provenance integrity fixtures;
9. profile tests for Virginia permitting and other jurisdictions;
10. model-interface capability discovery and MCP reference transport tests.

A future reference-node container SHOULD run this conformance suite as its startup smoke test.
