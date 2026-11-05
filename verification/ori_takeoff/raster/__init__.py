# SPDX-License-Identifier: Apache-2.0
"""ORI raster / scanned-plan track (DRAFT 0.1).

Separate from the vector extractor and from the IFC validators on purpose:
nothing here writes IFC or feeds ori_verify. Every recognised item is
``ai_extracted_unverified`` and its value status is ``unknown`` until a person
confirms it. Accuracy numbers come from ORI's own synthetic sheets only.

Local, licence-compatible dependencies only: OpenCV (Apache-2.0), Tesseract
(Apache-2.0) via pytesseract (Apache-2.0), pypdfium2 (Apache-2.0 / BSD-3-Clause),
numpy (BSD-3-Clause). No network, no cloud OCR.
"""
ORIGIN = "ai_extracted_unverified"
VALUE_STATUS = "unknown"
VERSION = "0.1.0"
