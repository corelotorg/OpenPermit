# Plan takeoff and plan overlays — v0.1 DRAFT

Status: DRAFT. Implemented by `verification/ori_takeoff/` with tests (`verification/tests/test_takeoff.py`),
a conformance rule (`plan-overlay-training-gate`) and examples (`verification/examples/takeoff/`).
To finish: accuracy on real third-party plans (none has a verified license yet, see §9), raster
tracing, multi-storey alignment beyond the sample, and the open questions in §11.

> Every overlay element is a **proposal**. Auto-extracted elements are unreviewed until a person
> confirms them, and they give `unknown` in ORI checks until then. An overlay is reviewer evidence
> and candidate training data. It is not a measurement anyone has certified and it is not approval.

## 1. What this is for

Most single-family submissions are PDF plan sets (docs/PDF-PATH-0.1-DRAFT.md). The takeoff tool
turns a vector plan page into a labeled vector overlay:

1. **Reviewer evidence**: walls, doors, windows, rooms, stairs and dimensions anchored to a page, with
   takeoff quantities (wall length, room areas, opening counts and widths, stair riser and tread counts).
2. **Training data**: each traced and reviewed page becomes a labeled example (overlay JSON, COCO,
   GeoJSON), but only through the licensing gate (§8). Training data is secured and held out: it is
   not published in this repository (docs/GOVERNANCE-BOUNDARY.md §4). The overlay format, the tools and
   the synthetic CC0 sample are public.
3. **2D-to-IFC**: the overlay becomes a simple IFC 4.3 model that the existing ORI checker reads (§7).

The route follows the 2D-to-IFC finding of ORI's 2026-09-28 adjacent open-source survey: no mature
permissive tool exists, so ORI uses pdfplumber / ezdxf, its own rule-based reconstruction (Apache-2.0) and
ifcopenshell.api, and labels everything derived as unconfirmed.

## 2. Format: `spec/ori-plan-overlay-0.1.schema.json`

One document per source file (PDF or DXF). Top level:

| Field | Meaning |
|---|---|
| `overlay_profile`, `label`, `status` | `ori-plan-overlay-0.1`, the evidence label, `DRAFT` |
| `overlay_id` | `urn:ori:overlay:...` |
| `source` | `artifact_id` = `urn:ori:artifact:sha256:<hex>` of the exact bytes, filename, media type, size, page count (same content addressing as the PDF manifest) |
| `license_record` | License basis, local license copy, citation, `training_use` (§8) |
| `dataset_role` | `candidate`, `ground_truth`, `training`, `evaluation`, `reviewer_only`. The schema requires `training_use: allowed` and a person-confirmed license for the three dataset roles |
| `tool` | Tool name, version and dependency licenses |
| `pages[]` | One entry per page (below) |

Page: `page`, `page_label` (sheet id from PDF page labels), `sheet_title`, `kind`
(`vector`, `raster`, `mixed`, `empty`, `dxf`), `status` (`extracted`, `needs_tracing`, `traced`,
`corrected`, `ground_truth`), `size_page_units`, `page_units`, `scale`, `storey`, `elements[]`,
`takeoff`, `detection` (counts and which hints were used), `notes`.

### 2.1 Coordinates

* `geometry_page`: PDF points with the origin at the **bottom-left** of the media box, the same convention
  as `region_pt` anchors in the PDF path. For DXF: drawing units in model space.
* `geometry_real`: inches on the drawing plane, `page × scale.real_in_per_page_unit`, from the page origin.
  Not georeferenced and not aligned between pages (the IFC step aligns floors, §7).
* All geometry objects are GeoJSON geometry objects: `Point`, `LineString`, `Polygon` (holes allowed).
* Walls, doors, windows and openings also carry `axis_page` / `axis_real` (centreline).

### 2.2 Scale: unknown stays unknown

`scale.status` is one of:

| Status | When | Real-world values |
|---|---|---|
| `stated_confirmed` | A scale note (e.g. `1/4" = 1'-0"`) and dimension strings agree within 2 % | yes |
| `stated` | Scale note only | yes |
| `calibrated` | No usable note; at least 2 dimension strings measured against their dimension lines agree within 2 % | yes |
| `drawing_units` | DXF with `$INSUNITS` | yes |
| `conflict` | Note and dimensions disagree, or several different notes with nothing to decide | **null** |
| `not_to_scale` | Marked NTS | **null** |
| `unknown` | Nothing usable | **null** |

When the scale is not usable, every `geometry_real`, every real-world property and every real-world
takeoff total is `null`. Counts and page-unit geometry are still produced. The schema enforces
`real_in_per_page_unit: null` for the three unusable states.

### 2.3 Element classes (IFC entity names)

| `ifc_class` | Plan meaning | Key properties |
|---|---|---|
| `IfcWall` | Wall between two parallel faces | `thickness_in`, `length_in` (centreline), `exterior` |
| `IfcDoor` | Opening with a swing arc | `width_in`, `swing` (hinge, radius, arc, side), `relations.host_wall` |
| `IfcWindow` | Opening with glazing lines | `width_in`, `relations.host_wall` |
| `IfcOpeningElement` | Gap in a wall with no door or window symbol | `width_in`, `relations.host_wall` |
| `IfcSpace` | Room: a closed region bounded by walls and openings | `area_ft2` (clear, to wall faces), `label`, `use`, `noted_size_in`, `area_matches_note` |
| `IfcStair` | Run of uniform parallel tread lines | `riser_count`, `tread_count`, `tread_depth_in`, `width_in`, `direction`, `noted_riser_count`, `riser_height_in: null` |
| `IfcAnnotation` | `annotation_type`: `dimension`, `text_label`, `room_label`, `scale_note`, `sheet_title` | dimension: `text`, `value_in`, `measured_in`, `agrees` |

A stair's riser height cannot be seen on a plan view. It stays `null`, even when a sheet note states it.

### 2.4 Provenance on every element

`provenance`: `method` (`authored_ground_truth`, `auto_extracted`, `human_traced`, `human_corrected`),
`tool`, `tool_version`, `confidence`, `rule` (which heuristic), `by`, `at`, `review_status`
(`unreviewed`, `confirmed`, `corrected`, `rejected`) and `derived_from` (id of the element a correction
replaces). Confidences are **uncalibrated heuristic scores**, not probabilities.

### 2.5 Exports for ML

* **COCO** (`overlay.to_coco`): one image per page in raster pixels (y down) at a chosen dpi; the
  categories are the 7 IFC class names; polygons become `segmentation`, lines and points become padded boxes;
  `attributes` keep the ORI id, method and review status; the license comes from the license record.
* **GeoJSON** (`overlay.to_geojson`): one FeatureCollection per page in real inches (or page units), with
  the class, method, review status, confidence and scalar properties per feature.

## 3. Inputs

| Input | Reader | Notes |
|---|---|---|
| Vector PDF | pdfplumber (MIT): lines, rects, curves with path commands, characters | Bézier runs are fitted to circles (door swings). Characters are grouped into text runs along their writing direction, so rotated dimension text works |
| DXF | ezdxf (MIT): LINE, LWPOLYLINE, POLYLINE, ARC, TEXT, MTEXT, DIMENSION, INSERT (exploded) | Units from `$INSUNITS`. Layer names matching `WALL` mark wall candidates |
| Raster PDF / images | none | Page `kind: raster`, `status: needs_tracing`, no elements. Out of scope for v0.1 |
| DWG | none | Needs a converter; the common one is proprietary (survey §6) |

PyMuPDF (AGPL) is not used. No GPL floor-plan code and no NonCommercial data is used.

## 4. Running it

From `verification/` with the ORI venv:

```
python -m ori_takeoff.cli extract PLAN.pdf --out plan.overlay.json --preview-dir previews/
python -m ori_takeoff.cli evaluate GROUND_TRUTH.json plan.overlay.json --out accuracy.json
python -m ori_takeoff.cli ifc plan.overlay.json --out plan.ifc --check plan.ifc-check.json
python -m ori_takeoff.cli export plan.overlay.json --coco plan.coco.json --geojson-dir geojson/
python -m ori_takeoff.cli gate plan.overlay.json        # exit 1 unless admissible to the training set
python -m ori_takeoff.cli sample OUTDIR                  # the CC0 sample plan, DXF and ground truth
```

`verification/examples/takeoff/build_takeoff_examples.py` regenerates every example file.

## 5. Detection heuristics (v0.1)

All thresholds are real inches converted with the page scale.

1. **Wall candidates.** If the page has at least two clearly different line weights (max/min ≥ 1.8), the
   heavier cluster is the candidate set (`weight_source: lineweight`). In DXF, a `WALL` layer is used if
   present. Otherwise every segment is a candidate, and the page notes say so.
2. **Wall pieces.** Parallel candidate segments (within 1°) 3 to 12 in apart, overlapping by at least 2 in,
   with no other parallel line between them, form a piece. With no scale, the thickness range comes from
   the most common close spacing of heavy lines.
3. **Walls.** Collinear pieces of the same thickness merge across gaps up to 120 in. Each gap of 18 in or more
   that no crossing wall fills is an opening. L corners extend both axes to their intersection.
4. **Openings.** A circular arc centred near a jamb corner with radius within 15 % of the gap width means a
   **door** (also arcs rebuilt from short polyline chains, common in CAD exports). Two or more thin lines
   parallel to the wall and spanning 80 % of the gap mean a **window**. Otherwise **IfcOpeningElement**.
5. **Rooms.** The union of wall bodies plus opening rectangles is closed morphologically (square structuring
   element of half the maximum wall thickness, so rectangles keep their corners). Its holes of at least 10 ft²
   are rooms. Text runs inside a room become its label; a `W X D` size note becomes `noted_size_in` and is
   compared with the measured area. Use is inferred from the label (e.g. BEDROOM → habitable).
6. **Stairs.** Four or more thin parallel lines of equal length (28 to 72 in) with uniform spacing of 8 to
   14 in, inside the building footprint. `riser_count` = number of lines, assuming one line per riser,
   including the first and last. `UP`/`DN` and `nnR` text nearby give direction and the noted riser count.
7. **Dimensions.** A text run that parses completely as feet-inches, centred on a thin parallel segment
   within 3 text heights, is a dimension; its value is compared with the measured segment length.
8. **Storey.** `FIRST`/`SECOND` in the sheet title gives the storey name; a `FLOOR TO FLOOR` note gives a
   noted height (text, unconfirmed). Elevations stay unknown unless known from the overlay.

## 6. Takeoff quantities

Per page (`page.takeoff`): wall count and centreline length (total, exterior, interior; exterior axes
meet at centreline corners, interior walls end at the face they meet), door and window counts and widths,
unclassified openings, room areas (clear) and their total, gross footprint, stair counts and tread depth,
and dimension strings with their agreement against geometry. Real totals are null without a usable scale.

Example (clean sample PDF, sheet A-101, auto-extracted and unreviewed; file `takeoff-sample.json`):
walls 8, centreline 2247.0 in (exterior 1416.0, interior 831.0); doors 7 (28, 32 ×4, 36 ×2 in);
windows 7 (24, 48 ×3, 60 ×3 in); rooms 5, 811.03 ft² net (KITCHEN / DINING 211.875, POWDER LAUNDRY
38.266, FOYER 121.578, LIVING 272.25, DEN 167.063); gross footprint 896.0 ft²; stair 14 risers,
13 treads at 10.0 in, riser height unknown; 6 of 6 dimensions agree with geometry.

## 7. Overlay to IFC 4.3, then ORI checks

`to_ifc.overlay_to_ifc` writes IFC4X3 (millimetres) with ifcopenshell.api: one storey per page with a usable
scale; walls (axis plus extruded body); openings voiding their host wall and filled by IfcDoor/IfcWindow
(`OverallWidth` from the plan, `OverallHeight` empty); spaces (extruded footprint, `Pset_ORI_SpaceUse`);
IfcStair with `Pset_ORI_StairFromPlan` (no flight geometry, because riser heights are unknown). Every element
carries `Pset_ORI_Takeoff` (method, review status, confidence, overlay id, tool, height source).

Heights are not on a plan. A body without a known height gets a placeholder height for viewing only and
`HeightSource = placeholder_not_from_plan`. `to_ifc.check_ifc` runs IfcOpenShell schema validation and the
implemented ORI rule units through `ori_verify.ifc_extract`, then:
* drops every fact derived from a placeholder height (so it becomes missing and gives `unknown`);
* relabels facts from auto-extracted, unreviewed elements as `vector_extracted_unconfirmed` (gives `unknown`).

Results on the sample (`verification/examples/takeoff/*.ifc-check.json`):

| Model | Schema issues | pass | fail | unknown | not applicable |
|---|---|---|---|---|---|
| Ground truth (authored, confirmed, design heights) | 0 | 15 | 0 | 0 | 15 |
| Auto-extracted, unreviewed | 0 | 0 | 0 | 30 | 0 |

Only space-based units run, because a plan gives no stair flight profile, guard or escape-opening
properties. Stair, guard and escape-opening units are not evaluated; this is reported, not hidden.

## 8. Licensing gate (training data)

This applies the corpus license rule (`verification/ori_cl/corpus_license.py`) to plans. **No plan enters the
training set without a license basis, a local copy of the license evidence and a citation.**
`overlay.training_gate_errors(doc)` refuses an overlay unless:

1. `license_record` has `license_id`, `license_basis`, `license_url` (https), `license_local_path` and a matching
   `license_sha256`, `license_fetched_at` (date), `license_confirmed: true`, `source_url` (https) and a full
   `source_citation` (author, title, year, publisher, identifier, archive URL, accessed date);
2. the license is a training-set license: CC0-1.0, a US federal-work or public-domain statement, CC-BY-4.0,
   Apache-2.0 or ORI-written-permission. NonCommercial and NoDerivatives terms are refused (overlays are
   derived works, and the gate keeps every admitted plan free of use restrictions);
3. `training_use` is `allowed`;
4. no page is `needs_tracing`, and no auto-extracted label is unreviewed or rejected.

**Passing the gate makes a plan admissible for training, not publishable.** Overlay labels built from donor or
third-party plans are training data. They are secured, held out of this repository and outside share-alike
(docs/GOVERNANCE-BOUNDARY.md §4). Only the overlay format, the tools and the ORI-authored synthetic CC0 sample
(§9) are published.

The conformance rule `plan-overlay-training-gate` runs the same check on fixtures and on every example overlay
with a dataset role (`conformance/positive/plan-overlay-training-gate.json`, two negative fixtures). A plan
with unknown rights can still be extracted for a reviewer (`dataset_role: reviewer_only` or `candidate`,
`license_id: UNKNOWN`, `training_use: not_allowed`).

## 9. Test data and measured accuracy

**Sample plan** (`ori_takeoff/sample_plan.py`, CC0, ORI-authored, synthetic, not for construction): a
two-storey 32'-0" × 28'-0" house, 6 in exterior and 4 1/2 in interior walls, 14-riser straight stair, five
rooms per floor, 11 doors and 15 windows in total, overall and chain dimensions, room size notes, a scale note,
and plumbing and kitchen fixtures as distractors. Outputs: `ori-sample-house.pdf` (ARCH C, 1/4" = 1'-0"), a
variant with export noise (`ori-sample-house-noisy.pdf`: sheet rotated 0.4°, wall outlines as loose segments
with ends trimmed by up to 0.4 in, every second door swing as a polyline, wall hatching, dashed distractors),
two DXF floors, and ground truth generated from the design data (not from the extractor).

Measured on these files (`accuracy-sample.json`, sheets A-101 / A-102):

| Run | Wall length recall / precision | Openings located + class F1 | Rooms F1 | Stairs (risers, treads) | Dimensions |
|---|---|---|---|---|---|
| Clean PDF | 1.000 / 1.000 | 1.000 / 1.000 | 1.0 / 1.0 (max area error 0.001 ft²) | 14 / 13 correct | 6/6 |
| Noisy PDF | 1.000 / 1.000 | 1.000 / 1.000 (width error ≤ 0.733 in) | 1.0 / 1.0 | correct | 6/6 |
| DXF | 1.000 / 1.000 | 1.000 / 1.000 | 1.0 / 1.0 | correct | 6/6 |
| Clean PDF, line weight ignored | 0.994 / 0.831 and 0.998 / 0.811 | 0.824 / 0.923 | 0.6 / 0.6 | correct | 6/6 |

**Read this carefully.** The sample and the noise were written by the same project that wrote the extractor,
and the polyline-arc recovery was added after the noisy variant first showed 4 of 7 doors on A-101 as
unclassified openings. Perfect scores here show that the pipeline is internally consistent. They say
**nothing** about accuracy on real plan sets. The run that ignores line weight is the closest proxy for a
plan whose line weights are uninformative: fixtures, glazing and stair lines then pair up as walls (38 and 42
walls found against 8 true), and only 3 of 5 rooms per floor are recovered.

Third-party candidate plan sources are tracked outside this repository. None was ingested.

## 10. Limitations

* Vector input only. Raster pages are recorded as needing tracing.
* Line weight (or a wall layer) carries much of the result. Without it, precision drops sharply (§9).
* Walls are straight. Curved walls, angled bays, and walls drawn as a single line are not handled.
  Hatched or solid-filled walls without outlines are not handled.
* Doors need a circular swing (arc or polyline). Pocket, sliding and bifold doors become unclassified openings.
  Windows need glazing lines inside the wall gap.
* Openings at a wall end (no wall piece on one side) are not found.
* Stair counting assumes one line per riser including both ends. Winders, landings and break lines are not handled.
* Rooms open to each other without an opening in a wall merge into one space (e.g. the foyer includes the
  stair; the hall includes the stair well).
* Room labels are text inside the polygon. Leader-line labels and labels outside rooms are missed.
* Floors are aligned only by a shared lower-left wall corner in the IFC step. There is no cross-page registration.
* Confidences are uncalibrated.
* DXF output from the sample writer is not byte-stable (ezdxf writes handles and timestamps); the PDFs are.

## 11. Open questions (provisional choices in this draft)

1. **Training-set licenses.** Allowed: CC0-1.0, US federal-work / public-domain statement, CC-BY-4.0,
   Apache-2.0, ORI written permission. Refused: NonCommercial, NoDerivatives, unknown. CC-BY-SA-4.0 is
   currently refused because share-alike terms would carry over to derived labels.
2. **Training labels need human review.** Unreviewed auto-extracted labels are refused by the gate. A
   "silver" set (`allow_unreviewed=True`) exists in code for experiments only.
3. **Wall length convention.** Centreline, with exterior corners at centreline intersections and interior walls
   ending at faces. Some estimators use outside faces instead.
4. **Placeholder heights in IFC.** Bodies without a known height get a 96 in placeholder for viewing. Checks drop
   facts from it. An alternative is 2D-only representations.
5. **Third-party plans.** No third-party plan is used until its reuse terms are verified and recorded (§8).

## 12. Files

* `spec/ori-plan-overlay-0.1.schema.json`
* `verification/ori_takeoff/`: `sources.py` (PDF/DXF readers), `detect.py`, `extract.py`, `takeoff.py`,
  `overlay.py` (builder, schema check, licensing gate, COCO/GeoJSON), `preview.py`, `evaluate.py`,
  `to_ifc.py`, `sample_plan.py`, `units.py`, `cli.py`, `editor/index.html`
* `verification/tests/test_takeoff.py`; `conformance/positive/plan-overlay-training-gate.json`,
  `conformance/negative/plan-overlay-noncommercial-license.json`, `conformance/negative/plan-overlay-unreviewed-unlicensed.json`
* `verification/examples/takeoff/` (sample plan, ground truth, overlays, previews, accuracy, IFC, check reports, COCO, GeoJSON)
* `docs/PLAN-TRAINING-SET-WORKFLOW-DRAFT.md`
