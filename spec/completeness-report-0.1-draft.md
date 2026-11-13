# ORI Completeness Report — v0.1 Draft

**Status: DRAFT.** Schema: `spec/ori-completeness-report-0.1.schema.json`. JSON-LD context: `vocab/ori-lifecycle-records-0.1.context.json`. Conformance rule: `completeness-report-record`. Label: *Reviewer evidence, not approval.*

A completeness report checks one exact transmitted package against identified information expectations. It says whether information is there to review, not whether the design complies. Accepting the package is a separate intake act, and only that act may start a review clock.

## Results are three-valued

Each item has a `result` (`pass`, `fail`, `unknown`), an `effect` (`blocking`, `advisory`, `unknown`) and a `basis`. Missing, unreadable, unsupported or not-applicable-yet information gives `unknown`, never `fail`. A `fail` needs observed evidence.

Aggregation, computed by the checker and compared with the record:

- `overall`: any partial or unknown coverage, or any unknown result, effect or applicability, gives `indeterminate`; otherwise any fail gives `incomplete`; otherwise `complete`.
- `blocking_status`: unknown coverage, an unknown effect or a blocking unknown gives `unknown`; otherwise a blocking fail gives `unsatisfied`; otherwise `satisfied`.
- `blocking_items` and `advisory_items` list exactly the non-pass items of each effect.

## Rules checked

1. Schema valid; pinned context; `is_approval` false everywhere; unique item IDs that name a listed requirement set.
2. A non-observed basis gives `unknown`; a fail cites evidence.
3. `overall`, `blocking_status` and the item lists match the aggregation above.
4. Acceptance needs an identified intake actor, a known time and `blocking_status: satisfied`. It derives from resolved blocking coverage plus that explicit intake act, not from the overall aggregate (advisory unknowns must not change acceptance eligibility). Blocking uncertainty prevents acceptance, so it prevents the clock start.
5. If the linked status record is in the case, it starts the clock only after such an acceptance.
6. Element and other model anchors carry a known model version.

## To finish

- An association ledger from status-record events to reports (status-clock events stay closed).
- Requirement-set `artifact_ref` is omitted when unknown (`artifact_ref_status`); known refs stay IRI-coerced.
- Pinned `required_item_ids` must appear when coverage is complete.
- Proof that adding an advisory unknown does not change acceptance eligibility when blockers are satisfied.
