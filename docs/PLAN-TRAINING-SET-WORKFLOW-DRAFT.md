# Plan overlay training set: workflow, labeling guidelines, dataset card, licensing gate — DRAFT

Status: DRAFT, for the ORI plan takeoff (docs/PLAN-TAKEOFF-0.1-DRAFT.md). The tooling exists
(`verification/ori_takeoff/`, `editor/index.html`, `overlay.training_gate_errors`); no training set has been
assembled. To finish: two human reviewers per page on real licensed plans, and the open questions in
PLAN-TAKEOFF §11.

> **Training data is secured.** Overlay labels built from donor or third-party plans are training data: they
> are held out, kept in controlled storage outside this repository, carry no public licence and sit outside
> share-alike (docs/GOVERNANCE-BOUNDARY.md §4). What is public is the overlay format
> (`spec/ori-plan-overlay-0.1.schema.json`), the tools (`verification/ori_takeoff/`, `editor/index.html`) and the
> ORI-authored synthetic CC0 sample (`verification/examples/takeoff/`).

> Labels describe what a drawing shows. They are not findings about the building and not approval.

## 1. Workflow

```
license check ──► extract ──► review / correct / trace ──► second review ──► gate ──► export
 (record)       (auto)        (person, editor)            (person)          (code)    (COCO, GeoJSON)
```

1. **License first.** Before anything is extracted for training, fill the overlay `license_record`: license id
   and basis, license URL, a local copy of the license evidence with SHA-256 (redistributable copies under
   `research/licenses/`, other terms pages outside the repository with path, URL and SHA-256 only), the date
   fetched, a full citation, and `training_use`. A person confirms it (`license_confirmed: true`). If any of
   this is missing, the plan may be extracted for a reviewer only (`dataset_role: reviewer_only`).
2. **Extract.** `python -m ori_takeoff.cli extract PLAN.pdf --out x.overlay.json --preview-dir prev/
   --license-record license.json`. Every element is `auto_extracted`, `unreviewed`. Raster pages come out as
   `needs_tracing`.
3. **Review and correct** in the editor (`verification/ori_takeoff/editor/index.html`, open the file in a browser,
   no server, no network):
   * load the overlay and a full-page image of the page (e.g. the PNG the extractor rendered, uncropped, or any
     page render at the page's aspect ratio);
   * for each element: **Confirm** (correct as is), **Apply correction** (class or name changed; the element
     becomes `human_corrected`, `review_status: corrected`, `derived_from` = original id) or **Reject** (wrong;
     kept with `review_status: rejected` so the error is visible for evaluation);
   * **Trace** missing elements (click vertices, double-click to finish). They are `human_traced`, `confirmed`.
     Doors, windows and openings ask for their host wall id;
   * set the reviewer id; every action records `by` and `at`; download the corrected overlay.
   Geometry vertex editing is not in the v0.1 editor: to fix geometry, reject the element and trace it again.
4. **Second review.** A second person opens the corrected overlay and confirms or rejects. Record both reviewer
   ids in the dataset card. (The overlay keeps the last reviewer per element; keep each reviewer's file.)
5. **Gate.** `python -m ori_takeoff.cli gate x.overlay.json` must print `ADMIT`. It refuses any overlay with an
   incomplete or unconfirmed license record, a license copy whose SHA-256 does not match, a license outside the
   training-set list (no NonCommercial or NoDerivatives terms), `training_use` other than `allowed`, a page still
   `needs_tracing`, or an unreviewed or rejected auto-extracted label. Set `dataset_role` to `training` or
   `evaluation` only after the gate admits it; the schema and the conformance rule `plan-overlay-training-gate`
   enforce it again.
6. **Export.** `python -m ori_takeoff.cli export x.overlay.json --coco x.coco.json --geojson-dir geojson/`.
   Rejected elements should be dropped from training exports and kept for error analysis.
7. **Evaluate.** Keep a held-out set (separate sources, not just separate pages of one set) and measure with
   `python -m ori_takeoff.cli evaluate GT.json PRED.json --out acc.json`.

## 2. Labeling guidelines (v0.1)

General
* Label what is drawn on the page, not what you know about the building.
* One element per physical thing per page. Do not label the same wall twice on one page.
* Use the IFC class names exactly. If unsure between door, window and opening, use `IfcOpeningElement`.
* Do not label title blocks, borders, north arrows, keys or details at other scales.

Walls (`IfcWall`)
* Polygon covering the wall body between its two faces, through openings (the openings are separate elements).
* Exterior walls run to the outside corner; interior walls stop at the face of the wall they meet.
* Do not label furniture, cabinets, counters, fixtures or hatching as walls. Low walls and half walls: label as
  walls and say so in `name`.

Doors (`IfcDoor`) and windows (`IfcWindow`)
* Polygon = the wall gap (jamb to jamb, face to face). Width = clear gap shown on the drawing.
* Door: a swing arc or a leaf is drawn. Sliding, pocket and bifold doors are doors too (name them).
* Window: glazing lines in the wall gap. Set `host_wall`.
* A gap with neither symbol (cased opening) is `IfcOpeningElement`.

Rooms (`IfcSpace`)
* Polygon = clear floor area to wall faces, closing across door and opening gaps at the wall centreline.
* Name = the room label as printed. Do not invent names. Leave `use` empty if the label is ambiguous.
* An open area containing a stair stays one space; the stair is labeled separately.
* Closets: label as spaces only if they have their own label on the drawing.

Stairs (`IfcStair`)
* Polygon = the run of treads as drawn, one per flight on the page. Record riser and tread counts as drawn.
  Leave `riser_height_in` null unless a person reads it from a dimension on that page (then `human_corrected`).

Dimensions and text (`IfcAnnotation`)
* `dimension`: a LineString along the dimension line between extension lines, with the text as printed.
* `scale_note`, `sheet_title`, `text_label`: a Point at the text centre with the text as printed.
* Code-related notes on sheets: record the location only. Do not transcribe code text (docs/CITATION-POLICY.md).

Ambiguity
* If two reviewers disagree, keep both files, mark the element `rejected` in the training copy, and record the
  case in the dataset card.

## 3. Dataset card template

```
# ORI plan overlay dataset: <name> (<version>)
Status: DRAFT | released
Maintainer: <who>       Created: <YYYY-MM-DD>      Overlay profile: ori-plan-overlay-0.1
Purpose: training / evaluation of plan element recognition for ORI reviewer evidence. Not for approval.

## Sources
| Source id | Title, publisher, year | URL | License id and basis | Local license copy (path, SHA-256) | Pages used | Accessed |
(one row per source; every row passes `ori_takeoff gate`)

## Composition
Pages: <n> (vector <n>, traced raster <n>)    Elements by class: IfcWall <n>, IfcDoor <n>, ...
Building types: single-family detached only (ORI scope). Jurisdictions and eras represented: <...>
Splits: train / validation / test by **source**, not by page. Held-out sources: <...>

## Labeling
Guidelines: docs/PLAN-TRAINING-SET-WORKFLOW-DRAFT.md §2 (<version>)
Tool: ori_takeoff <version>; editor <version>
Reviewers: <ids>; two reviews per page: yes/no; agreement measured: <metric and value, or "not measured">
Share of labels auto-extracted then confirmed vs corrected vs traced: <...>

## Known gaps and biases
<e.g. one drafting style dominates; no curved walls; no raster scans; sample plan is synthetic>

## License of the dataset
Overlay labels: secured training data, held out; not published and not publicly licensed (docs/GOVERNANCE-BOUNDARY.md §4).
Underlying plans: per-source license above; attribution required for CC-BY sources.
Exception: labels for the ORI-authored synthetic sample are CC0-1.0 and public.
Exports: COCO / GeoJSON carry the license id per file.

## Measured results (if any)
Only results measured on the held-out sources, with the file names of the accuracy reports.
```

## 4. What is in the repository now

* One ORI-authored CC0 synthetic sample (two sheets, plus a noisy variant and two DXF floors) with ground truth.
  It passes the gate. It is a test fixture, not a training set: one house cannot teach a model anything general.
* No third-party plan. Candidate sources are tracked outside this repository; none was ingested.
