# How PDF plan sets enter ORI — v0.1 DRAFT

Status: DRAFT. It is implemented in part by `verification/ori_verify/` (the manifest,
declared values, vector-text extraction and extraction gating), with tests. Completion
request: the provisional decisions in §9 await maintainer confirmation. A PDF/A validator
(e.g. veraPDF) and a page-region annotation UI are not yet integrated.

> Every output of this path is **reviewer evidence, not approval.** Applicant-declared values
> are the applicant's statements. Extracted values are unverified until confirmed. Only
> the building official's decision under the adopted code is lawful approval.

## 1. Why PDF needs a first-class path

Most single-family permit submissions are PDF plan sets, not IFC models. ORI therefore
cannot make building models a precondition. The PDF path lets the same rule units that
run on IFC geometry run on values tied to specific sheets and pages. Every value stays
traceable to the exact bytes the applicant submitted.

## 2. The plan set is an evidence artifact

Each submitted PDF is recorded in a **plan-set artifact manifest**
(`spec/ori-pdf-artifact-manifest-0.1.schema.json`, `pdf_manifest.py`):

| Field | Purpose |
|---|---|
| `artifact_id` = `urn:ori:artifact:sha256:<hex>` | Content address of the exact bytes received. Any change produces a new id. |
| `sha256`, `size_bytes`, `pdf_version`, `page_count` | Integrity and basic description. |
| `pages[]`: `page`, `page_label`, `mediabox_pt`, `content_sha256` | Page anchors. The page label usually carries the sheet id (e.g. A-301). The per-page content hash supports page-level comparison between versions. |
| `pdfa` | The PDF/A claim read from XMP (`pdfaid:part`, `pdfaid:conformance`). **A claim is not validation.** |
| `plan_set_id`, `version`, `supersedes[]` | Versioning. Version ≥ 2 must name the artifact ids it supersedes (enforced by the schema and the code). |
| `submitted_by`, `submitted_at` | Who submitted and when. The event feeds the review clock (§8). |

Each artifact also becomes a core `Evidence` object with
`evidence_type: "pdf_plan_set"` and an `integrity` block (sha256). It carries
`supersedes[]` from the manifest.

Superseded versions are never deleted or edited; history is append-only (as in the
challenge protocol). A resubmittal is a new version.

### Page-level diff for resubmittals

`diff_manifests(old, new)` compares per-page content hashes by page label and lists
changed, added, removed and unchanged sheets. A reviewer can use this to target
re-review. **An unchanged page is not a re-verified finding**, and the reviewer decides
re-review scope.

Limitation: the hash covers the page's decoded content stream only. A change made only
through shared resources (for example a replaced image XObject with the same name) would
not show. Treat the diff as a hint, not proof.

## 3. PDF/A and archival

- ORI records whether each file *claims* PDF/A. It does not validate the claim.
- Before relying on PDF/A for archival, a jurisdiction should run a validator such as
  veraPDF and attach the report as further Evidence.
- ORI does not require PDF/A at intake. The original bytes are the evidence, and
  converting them would change the hash. If a jurisdiction archives a PDF/A copy, that
  copy is a new artifact with `derived_from` pointing to the original.

## 4. Page-level anchoring for review comments

- A value, comment or finding points to a page with an anchor:
  `{artifact_id, page, sheet?, region_pt?, detail?}`.
- `region_pt` is `[x0, y0, x1, y1]` in PDF points, with the origin at the bottom-left of
  the page's media box.
- In the evidence profile this is the `document_page` spatial-anchor type
  (`spec/evidence-attestation-0.1-draft.md`).
- An anchor into version N stays valid after version N+1 arrives, because it names N's
  artifact id. A comment carried forward to N+1 is a new anchor, with `derived_from`
  pointing to the old one.
- In BCF output, PDF-sourced topics carry the sheet/page anchor in the description and
  have no 3D viewpoint (`bcf.py`).

## 5. Applicant-declared values

The applicant (or their designer) declares the values a rule unit needs, in
`spec/ori-declared-values-0.1.schema.json`.

- **Every value must carry an anchor** to a page of an artifact listed in `plan_set.artifact_ids`.
- `declared.anchor_problems()` checks each anchor against the manifest: the artifact must
  exist and the page must be in range.
- A value whose anchor does not resolve is not used, so the rule gives `unknown`, and the
  problem is listed in the report.
- The declared-values document is itself an artifact. It is hashed over canonical JSON
  (sorted keys, no whitespace) and recorded as `Evidence` of type `declared_values`.

Groups and keys (inches, ft²) as of v0.1:

| Group | Keys |
|---|---|
| `stairs` | `riser_heights_in`, `tread_depths_in`, `min_headroom_in` |
| `spaces` | `use`, `ceiling_height_in`, `floor_area_ft2`, `sloped_ceiling` |
| `eeros` | `net_clear_height_in`, `net_clear_width_in`, `net_clear_area_ft2`, `grade_floor_or_below_grade`, `sill_height_in` |
| `walking_surfaces` | `drop_height_in`, `guard_present` |
| `guards` | `height_in`, `on_stair_open_side` |

## 6. The same rule units run on declared values

- `declared.subjects_from_declared()` produces the same `Subject`/`Fact` structures that
  the IFC extractor produces.
- `rules.evaluate()` then runs the identical rule functions, with thresholds resolved
  from the rule-unit data and the Virginia layer applied.
- The test `test_declared_values_run_the_same_rules_as_ifc` shows that declared values
  matching the synthetic IFC pass model give the same result for every rule unit.
- Declared values are the applicant's statements. A `pass` on declared values means *the
  declared values meet the threshold*. It does not mean the drawings, or the building,
  do. The reviewer checks the value against the anchored sheet. This is the main reason
  anchors are mandatory.

## 7. Optional extraction: vector text and AI

Extraction proposes values. It never supplies usable facts on its own.

- **Vector text** (`pdf_extract.py`):
  - A conservative, keyword-anchored parser for dimension callouts already present as
    text in a vector PDF (e.g. `RISER 7 3/4"`, `CLG HT 8'-0"`).
  - It maps typographic feet and inch marks to ASCII.
  - No OCR, no geometry inference, no AI.
  - Output has origin `vector_extracted_unconfirmed`, a page anchor, and the sheet id
    taken from the page label.
- **AI or ML extraction** (not implemented) must use origin `ai_extracted_unverified`.
- **Gating:**
  - Both unconfirmed origins yield `unknown` (`unconfirmed_extraction`), even where the
    value would fail.
  - `declared.confirm(doc, group, id, key, by="applicant"|"reviewer")` changes the origin
    to `applicant_confirmed` or `reviewer_confirmed`, optionally correcting the value.
  - Only then does the value count for pass/fail.
  - Tests cover both origins and the confirm step.
- Extraction output is never labelled as the applicant's declaration, and never as a
  reviewer finding.

## 8. Events and the review clock

- Plan-set submission, declaration, confirmation and resubmittal are events.
- ORI's non-binding 24-hour single-family review target
  (`profiles/project/ori-sf-review-target-24h-2026.json`):
  - measures active review hours from the complete-submission event to the
    review-decision event;
  - pauses the clock while waiting on the applicant (for example, waiting for
    confirmation of extracted values, or for a corrected sheet);
  - reports raw elapsed hours alongside.
- Confirmation requests to the applicant therefore start a pause interval, and the
  applicant's response ends it.

## 9. Provisional decisions (pending maintainer review)

1. `unknown` maps to core `indeterminate`, with the ORI name and reason code in metadata.
2. A required guard that is not modelled gives `unknown`. A guard explicitly declared
   absent (`guard_present: false`) gives `fail`.
3. IRC base values are secondary-sourced and labelled. No licensed ICC text.
4. The reference node does not index `rules/` or `verification/` yet.
5. Rule-unit class tags are estimates pending human review.

Specific to PDF (DRAFT proposals):
- Anchors are mandatory for declared values.
- PDF/A is recorded as a claim, not required at intake.
- Vector-extracted values need confirmation, like AI-extracted ones.

## 10. Files

- `spec/ori-pdf-artifact-manifest-0.1.schema.json`, `spec/ori-declared-values-0.1.schema.json`
- `verification/ori_verify/pdf_manifest.py`, `declared.py`, `pdf_extract.py`, `synthetic_pdf.py` (synthetic test PDFs)
- `verification/tests/test_declared_pdf.py`, `test_examples.py`
- `verification/examples/pdf/` (synthetic v1 and v2 plan sets, manifests, diff),
  `verification/examples/declared/`, `verification/examples/reports/declared-v1.report.json`,
  `extracted-v1.report.json`
