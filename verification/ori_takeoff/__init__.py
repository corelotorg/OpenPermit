# SPDX-License-Identifier: Apache-2.0
"""ORI plan takeoff (DRAFT 0.1): vector plan pages to a labeled overlay, takeoff quantities and IFC.

Reads vector PDF pages (pdfplumber) and DXF drawings (ezdxf), detects walls, openings, door
swings, rooms, stairs, dimension strings and labels, and writes an ``ori-plan-overlay-0.1``
document (spec/ori-plan-overlay-0.1.schema.json). Raster pages are recorded as needing tracing.

Every element this package proposes is ``auto_extracted`` and unconfirmed. It is reviewer
evidence and candidate training data, not a measurement of the building and not approval.
See docs/PLAN-TAKEOFF-0.1-DRAFT.md.
"""

__version__ = "0.1.0"
TOOL_NAME = "ori_takeoff"
TOOL_ID = f"{TOOL_NAME} {__version__}"
OVERLAY_PROFILE = "ori-plan-overlay-0.1"
EVIDENCE_LABEL = "Reviewer evidence, not approval"
