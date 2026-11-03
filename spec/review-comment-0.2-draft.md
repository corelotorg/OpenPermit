# ORI Review Comment — v0.2 Draft

**Status: DRAFT (issue #140, item A2).** Schemas: `spec/ori-review-comment-0.2.schema.json` (the comment) and `spec/ori-review-comment-event-0.2.schema.json` (the event envelope). Conformance rule: `review-comment-record`. Label: *Reviewer evidence, not approval.* v0.2 replaces the unpublished v0.1 draft.

A review comment is one item in the conversation about a submitted design. Only a formal correction can hold up a review; every other kind is informal. A comment points at a requirement by reference (a rule unit or a code section number). It never states the requirement in its own words and never carries code text.

## Kinds

| Kind | Formal | Notes |
|---|---|---|
| `correction` | yes | needs a rule unit (or `unknown`), a model version and a specific anchor; note up to 280 characters; the only kind that can be `resolved` |
| `suggestion`, `recommendation` | no | may carry a `suggested_change` to one model property, by reference; not binding |
| `question`, `discussion` | no | |
| `answer` | no | must reply to another comment (`in_reply_to`) |
| `navigation` | no | must carry a `view` anchor |
| `x-…` | no | open extension kinds; a receiver that does not know one reads it as `discussion` |

Informal items end as `closed`. They never pause a review clock or block a decision.

## Anchors

A comment has 1 to 32 anchors, in any mix:

- `element`: an IFC GlobalId or an ORI element key;
- `spatial`: a point or box in the model's own coordinates and length unit, with an optional storey;
- `sheet`: a document hash and page, with an optional region given as fractions of the page;
- `discipline`: building, structural, energy and so on, or an `x-` discipline;
- `code_section`: an edition id plus a section number, or an ORI rule unit; no titles, headings or text;
- `view`: a saved camera, isolated elements and an optional section box, for live navigation of the hosted model.

An element, spatial or view anchor requires the comment's `model_version`.

**A formal correction needs a specific anchor**: an element, a model-space point or box, a sheet region, or a code section reference. A whole sheet, a discipline or a view on its own is not enough.

## Roles

`author_role` and `resolution.by_role` use one shared role list (`$defs/role` in the schema, mirrored by `ROLES` in `conformance/records_140.py`): plan reviewer, building official, fire reviewer, zoning reviewer, third-party reviewer, inspector, applicant, design professional, other. Roles, never personal names.

## Status changes as events

Each comment travels as the data of a CloudEvents 1.0 structured JSON event. Event types are `dev.openpermit.review.comment.created`, `.updated` and `.statuschanged`. The event `subject` is the comment id, and the extension attributes `oriapplication` and `orikind` repeat the application and kind. Where an application also has a status record (a separate draft, proposed separately), issued corrections are also listed on its core `comments_issued` events through `comment_refs`. Naming CloudEvents is attribution only; no affiliation with the CNCF or the CloudEvents project is implied. Source: CloudEvents specification v1.0.2, https://raw.githubusercontent.com/cloudevents/spec/v1.0.2/cloudevents/spec.md (fetched 2026-10-30).

## Rules checked

1. The comment and any event envelope pass their schemas; `is_approval` is always `false`.
2. A note may not restate a requirement in code register.
3. A formal correction has a specific anchor (see above).
4. A comment cannot reply to or supersede itself; a reply is not in an earlier round than its parent; a superseding comment is in a later round.
5. Only a reviewer role resolves a correction. The applicant answers.
6. Resolving needs a real rule unit; `unknown` stays open and is never turned into a result.
7. A resolution cites a model version different from the one the correction was raised on.
8. An event's `subject` is the id of the comment it carries, and `orikind` matches its kind.

A resolved comment is reviewer evidence. It is not a permit decision; the authority's core `Decision` (ori-core §3.14) is.

## To finish

- Map to at least one existing plan-review or issue-exchange format (for example a BCF topic and viewpoint), by field name only.
- Decide whether `inspector` comments from field visits belong in this record or in a separate inspection record.
