# Scanned and raster plan recognition — v0.1 DRAFT

> **DRAFT, 2026-10-12.** Licence: CC BY-SA 4.0 (docs). Code under
> `verification/ori_takeoff/raster/` is Apache-2.0; the benchmark file
> `verification/examples/takeoff/raster-accuracy-sample.json` is CC0-1.0.
> Machine output is reviewer evidence, never approval.

## What it is

A separate track for plans that arrive as pixels (scans, faxes, phone photos of sheets) rather
than vector PDF or DXF. It is kept apart from the vector extractor and from the IFC validators:

* it writes no IFC and does not import `ori_verify`, `ifcopenshell` or `to_ifc`
  (`tests/test_raster.py` checks this);
* every recognised item has `origin: ai_extracted_unverified` and `value_status: unknown`;
* a scale read by OCR is `ocr_scale_note_unconfirmed`, never confirmed.

None of it can produce a pass or fail. A person must trace or confirm items in the overlay editor
before anything reaches a check.

## Pipeline

1. `degrade.py`: render ORI's own synthetic CC0 sheet (`ori-sample-house.pdf`) with pypdfium2 and
   degrade it (resolution, skew, Gaussian noise, blur, JPEG loss). The page-to-pixel transform is kept
   for scoring only; the recogniser never sees it.
2. `recognise.py`:
   * skew is estimated from long Hough lines and removed;
   * walls are found as thick filled bands (morphological opening along each axis);
   * text is read with Tesseract, both upright and rotated 90°, with two binarisations;
   * OCR foot and inch marks are normalised (° ” ’). Digits are never guessed, and a
     12-inch-or-more remainder is rejected as a misread;
   * the scale comes from an OCR'd `SCALE` note plus the resolution the scanner declared, otherwise
     it is unknown.
3. `evaluate.py`: scores recognition against the vector ground truth.
   * Walls: centreline length recall and precision within 6 pt (4 in at 1/4" = 1'-0"). Door and
     window openings are excluded from the recall base.
   * Thickness: absolute error.
   * Room labels: found inside their room.
   * Dimension strings: exact value read near the dimension line.

Run it with `python -m ori_takeoff.raster.cli benchmark --out FILE` or
`python -m ori_takeoff.raster.cli recognise IMAGE --dpi N --out FILE`.

Dependencies are local and licence-compatible: OpenCV (Apache-2.0), Tesseract 5 (Apache-2.0),
pytesseract (Apache-2.0), pypdfium2 and numpy. See `verification/requirements-raster.txt`.

## Measured accuracy (synthetic sample only)

Measured with Tesseract 5.5.0 and OpenCV 5.0.0 on both sheets of ORI's own synthetic sample, after
ORI degraded them. **This is not a general accuracy claim, and nothing has been tested on a real
scanned plan.**

| Level | dpi / skew / noise σ / blur / JPEG q | Wall recall | Wall precision | Room labels | Dimension values | Scale |
|---|---|---|---|---|---|---|
| clean_300dpi | 300 / 0° / 0 / 0 / – | 0.997, 0.996 | 1.000, 1.000 | 4/5, 5/5 | 6/6, 6/6 | read |
| scan_200dpi | 200 / 1.2° / 6 / 0.8 / – | 0.997, 0.996 | 0.998, 0.998 | 4/5, 5/5 | 3/6, 2/6 | read |
| scan_150dpi_skew3 | 150 / −3° / 12 / 1.0 / 60 | 0.997, 0.996 | 0.956, 0.983 | 4/5, 4/5 | 0/6, 0/6 | read |
| fax_100dpi | 100 / 2° / 18 / 1.2 / 40 | 0.997, 0.997 | 0.767, 0.797 | 0/5, 0/5 | 0/6, 0/6 | unknown |
| poor_72dpi | 72 / −1.5° / 22 / 1.5 / 30 | 0.991, 0.997 | 0.747, 0.741 | 0/5, 0/5 | 0/6, 0/6 | unknown |

The two values in each cell are sheet A-101 and sheet A-102.

Other results:

* **Skew** was estimated within 0.12° at every level.
* **Wall thickness**, where the scale was read, is overestimated by 1.4 to 2.0 in on average (max
  3.6 in). This is mostly because the heavy outline stroke is counted as wall; it is not corrected
  for.
* **Text below about 150 dpi** is effectively unreadable to Tesseract at these 6 to 9 pt sizes. The
  wall geometry survives, but room names, dimensions and the scale do not. Wall lengths are then
  in pixels only, and scale stays unknown.

## Limitations and what is needed

* Tested only on ORI's own synthetic, axis-aligned sheet. Rotated or curved walls, hatching styles,
  stamps, handwriting, folds and photo perspective are not handled.
* Openings (doors and windows), stairs and room boundaries are not recognised yet on raster pages.
* The tests' accuracy floors guard against regressions only.
* **Blocked/needed:** a real scanned residential plan with a licence that allows this use. ORI did
  not fetch any copyrighted real plan. Until one is supplied, accuracy on real scans is UNVERIFIED.

## Vector track change in this round

Typical-ceiling notes are now read from vector sheets: `CEILING HEIGHT 8'-0"`, `CLG HT 8'-0"` and
`8'-0" CLG`. The value is stored as `storey.noted_ceiling_height_in`.

The IFC export uses this value for space heights, with `HeightSource = sheet_note_unconfirmed`.
The extractor policy still treats it as unconfirmed, so checks that depend on it stay unknown until
a person reviews it.
