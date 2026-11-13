# ORI Transmission Envelope — v0.1 Draft

**Status: DRAFT.** Schema: `spec/ori-transmission-envelope-0.1.schema.json`. JSON-LD context: `vocab/ori-lifecycle-records-0.1.context.json`. Vocabulary: `vocab/ori-lifecycle-records-vocab-0.1.json`. Conformance rule: `transmission-envelope-record`. Label: *Reviewer evidence, not approval.*

An envelope says who sent which exact files to whom, for which application and why. Its receipt is the receiver's separate statement that the files arrived. Arrival is delivery evidence only: it is not completeness and not approval. The record is a JSON-LD document with `@id` and `@type: TransmissionEnvelope`.

## Fields

| Field | Meaning |
|---|---|
| `sender`, `receiver` | agent IRI and role (applicant, design professional, intake, authority, system, other) |
| `correlation_id`, `idempotency_key` | shared across rounds; one key plus one manifest gives one receipt |
| `purpose` | `initial_submission`, `resubmittal`, `evidence_transfer` |
| `manifest` | hashed artifacts: source model, view model, document, requirement set, evidence, change record |
| `privacy` | handling metadata only; unknown classification never means public |
| `receipt` | `state`, `received_at`, `manifest_verification`, `application_intake_status`, `is_approval: false` |
| `change_record_ref` | the limited change record for a declared limited resubmittal |

## Rules checked

1. Schema valid; the `@context` equals the pinned context; every `is_approval` anywhere is false.
2. An unrebuilt, unavailable or unknown artifact has `sha256: unknown`, `hash_status: unknown`, unknown bytes and no content-addressed ID. A hash is never made up.
3. A content-addressed artifact ID matches its hash; only available bytes can be hash-verified.
4. A received receipt has a known time; a verified manifest means every available artifact is hash-verified.
5. A view model (GLB) names its source IFC; a schema identifier is verified only from verified bytes.
6. A change record in the same case that names this envelope is linked by `change_record_ref`.

## To finish

- A pinned manifest comparison contract for idempotent replays.
- A CloudEvents profile for `submission.received`; the review-comment 0.2 event schema is left unchanged.
- Projection to status-clock `submitted` and `resubmitted` (never `accepted_complete` or `clock_started`).

## Classifications and dialects

A party may carry `classifications`: external code-list references such as NAICS (scheme, version, code, source URL, status). Only the code is recorded; titles and tables are not reproduced. A code describes economic activity; it is not a licence and grants no authority. Source-native labels from forms (for example HUD single-family forms) and local NAICS-based categories map to these records in `vocab/ori-lifecycle-dialect-mappings-0.1.json`, as assertions for human review.
