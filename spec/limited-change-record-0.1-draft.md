# ORI Limited Change Record — v0.1 Draft

**Status: DRAFT.** Schema: `spec/ori-limited-change-record-0.1.schema.json`. JSON-LD context: `vocab/ori-lifecycle-records-0.1.context.json`. Conformance rule: `limited-change-record`. Label: *Reviewer evidence, not approval.*

An applicant declares that a resubmittal changes only some elements of a pinned parent revision. Reviewers see that declaration next to what a comparison actually found. The declaration is never a waiver: dependencies may extend review past it.

## Fields

| Field | Meaning |
|---|---|
| `parent_revision_ref`, `child_revision_ref`, `parent_model`, `child_model` | the two revisions and their hashed models; the child may be unrebuilt |
| `touched_elements` | map keyed by 22-character IFC GlobalId; each item repeats its `ifc_global_id` |
| `carry_forward` | applicant assertion that untouched elements carry forward from the parent; `verification` verified or unknown |
| `reviewer_scope` | `declared_scope: listed_elements_only`, plus `verified_differences` (actual diffs), `dependency_scope` (dependency-only), `verified_scope` (their union), `verified_scope_status`, `comparison_state`, `context_scope` |
| `answers_comment_refs` | review comments this change answers |

## Rules checked

1. Schema valid; pinned context; `is_approval` false; every key a canonical IFC GlobalId (`^[0-3][0-9A-Za-z_$]{21}$`) equal to its item's `ifc_global_id`.
1b. Verified carry-forward needs a complete comparison, `verified_scope_status: verified`, and no `verified_differences` outside the touched set; dependency-only IDs stay in `dependency_scope`.
2. An unrebuilt child carries unknown hashes, no after anchors, no after model version and unknown binding.
3. Added elements have no parent anchors; removed elements have no child anchors; model versions match the parent and child.
4. Declared scope is kept apart from verified scope: a verified scope or verified carry-forward needs a comparison of verified parent and child bytes; a verified scope cannot drop declared elements.
5. Element-level answered comments appear at record level; the envelope it travels with is a resubmittal.

## To finish

- No comparison or impact method is supplied here; how a comparison is run and recorded is open.
- Evidence for ambiguous GlobalId correspondence after ID churn.
