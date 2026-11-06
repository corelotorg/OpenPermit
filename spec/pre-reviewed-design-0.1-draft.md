# ORI Pre-Reviewed Design — v0.1 Draft

**Status: DRAFT (issue #140, item A6).** Schema: `spec/ori-pre-reviewed-design-0.1.schema.json`. Conformance rule: `pre-reviewed-design-record`. Label: *Reviewer evidence, not approval.*

Some authorities review a design once and accept it for reuse on many lots. This record says which authority did that, under which rule set and editions, for how long, and what still has to be reviewed on each site. The authority's act is the linked core `Decision` (ori-core §3.14); this record is evidence about it. The record is device-neutral: it covers any design, however it is built.

## Fields

| Field | Meaning |
|---|---|
| `design.model_version.sha256` | the exact model version that was pre-reviewed |
| `reviewed_by_authority` | `urn:ori:authority:…` |
| `decision_ref` | the authority's core Decision |
| `rule_set.jurisdiction`, `rule_set.editions`, `rule_set.local_amendments` | which rules and editions applied; amendments may be `unknown` |
| `validity.valid_from`, `validity.valid_until` | the term; the end may be `unknown` |
| `site_specific_review_remaining` | at least one item, e.g. siting, foundation and soils, utilities; or `unknown` |
| `status`, `as_of` | `current`, `expired`, `withdrawn`, `superseded`, `unknown`, as of a date |
| `uses` | applications that reuse the design, each with its model version |

## Rules checked

1. Schema valid; a Decision link and at least one remaining site item are required.
2. `valid_until` is after `valid_from`.
3. `current` only when `as_of` is inside a known term; an unknown end means status `unknown`.
4. A reuse must cite the same model version hash; a changed model is not pre-reviewed.
5. If the Decision is in the same case, it was made by `reviewed_by_authority`.

Pre-review never stands in for a site approval. Each reuse still needs its own review of the listed items and its own Decision.

## To finish

- Shared vocabulary for remaining site-review items, per jurisdiction profile.
- How a new code edition ends or narrows a term (supersession rules).
- Cross-jurisdiction reuse: out of scope for v0.1.
