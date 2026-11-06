# ORI Decision Record — v0.1 Draft

**Status: DRAFT.** Schema: `spec/ori-decision-record-0.1.schema.json`. JSON-LD context: `vocab/ori-lifecycle-records-0.1.context.json`. Conformance rule: `decision-record`. Label: *Reviewer evidence, not approval.*

A Decision records a disposition made by a human building official: subject, outcome, authority, attestation, validity, conditions and evidence. It keeps the core `Decision` type (ori-core §3.14). `is_machine` is always false. `is_approval` stays false because the record is evidence of the human act; it never grants lawful approval by itself, and no machine makes it.

## Conditions are references

`conditions` is a list of Condition IRIs, as in core. Each one has a matching entry in `condition_records` with its own `@id`, `@type: Condition`, a short case note, anchors and status. The pinned context coerces `conditions` to `@id`, fixing the design-draft issue where conditions expanded as plain strings.

## Rules checked

1. Schema valid; pinned context; `is_approval` false; `is_machine` false; `decided_by_role` building official.
2. `approve_with_conditions` has at least one condition; other outcomes have none.
3. `conditions` match `condition_records` exactly; condition model versions match the Decision.
4. A known validity end is after its start; an unknown end is not treated as forever.
5. `validity_status: verified` needs verified identity, signature and a known term; until then `pre_review_status` stays `unknown`.
6. Only a `pre_review_disposition` establishes a pre-review; supersession is not self-referential or cyclic.

## To finish

- Signature format and trust-source verification are not selected.
- Full pre-review resolver (subject, authority, model and rule-set matching across records).


`pre_reviewed_design_ref` is required only when `pre_review_link_role` is `reuse_evidence` or `establishes_pre_review` (omit when `none`). Verified validity rejects unknown `signer_ref` / `signed_artifact_ref` / `signature_ref`. A deny must not establish a current pre-review. Supersession is checked for cycles over all resolved edges; unresolved predecessors are reported separately.
