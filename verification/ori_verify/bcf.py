# SPDX-License-Identifier: Apache-2.0
"""Write fail and unknown results as a BCF 3.0 zip for reviewer triage.

Pass and not_applicable results do not become topics. Every topic title
starts with "[Reviewer evidence, not approval]", and the description repeats
the legal boundary. For IFC subjects the viewpoint selects the element by
IfcGuid. For declared-value (PDF) subjects the description carries the sheet
and page anchor, and there is no 3D viewpoint.

Structure follows buildingSMART BCF-XML 3.0 (bcf.version, extensions.xml,
<topic-guid>/markup.bcf, <topic-guid>/viewpoint.bcfv). The test suite checks
structure only. The example output was validated once, outside CI, against the
official BCF-XML release_3_0 XSDs (2026-09-27); those XSDs are not vendored
(see verification/README.md).
"""

from __future__ import annotations

import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from . import EVIDENCE_LABEL, LEGAL_BOUNDARY

TITLE_PREFIX = "[Reviewer evidence, not approval]"


def _uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "urn:ori:bcf:" + seed))


def _xml(el: ET.Element) -> bytes:
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(el, encoding="utf-8")


def write_bcf(report: dict, path: str | Path, author: str = "ori-verify@example.org") -> tuple[Path, int]:
    path = Path(path)
    topics = [r for r in report["records"] if r["metadata"]["result_state"] in ("fail", "unknown")]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        v = ET.Element("Version", {"VersionId": "3.0"})
        z.writestr("bcf.version", _xml(v))
        ext = ET.Element("Extensions")
        for tag, child, values in (
            ("TopicTypes", "TopicType", ["Issue", "Clarification"]),
            ("TopicStatuses", "TopicStatus", ["Open"]),
            ("TopicLabels", "TopicLabel", ["ORI", "reviewer-evidence", "fail", "unknown"]),
        ):
            t = ET.SubElement(ext, tag)
            for val in values:
                ET.SubElement(t, child).text = val
        z.writestr("extensions.xml", _xml(ext))
        for rec in topics:
            md = rec["metadata"]
            tguid = _uuid(rec["id"])
            state = md["result_state"]
            markup = ET.Element("Markup")
            topic = ET.SubElement(markup, "Topic", {"Guid": tguid, "TopicType": "Issue" if state == "fail" else "Clarification", "TopicStatus": "Open"})
            ET.SubElement(topic, "ReferenceLinks").append(ET.Element("ReferenceLink"))
            topic.find("ReferenceLinks/ReferenceLink").text = rec["id"]
            ET.SubElement(topic, "Title").text = f"{TITLE_PREFIX} {state.upper()} {md['section']} {md.get('subsection_part') or ''} {md['subject']['label']}".replace("  ", " ").strip()
            ET.SubElement(topic, "Labels").extend([_label("ORI"), _label("reviewer-evidence"), _label(state)])
            ET.SubElement(topic, "CreationDate").text = rec["executed_at"]
            ET.SubElement(topic, "CreationAuthor").text = author
            anchor = md["subject"].get("anchor") or {}
            where = ""
            if anchor.get("type") == "pdf_page":
                where = f" Anchor: sheet {anchor.get('sheet')} page {anchor.get('page')} of {anchor.get('artifact_id')}."
            ET.SubElement(topic, "Description").text = (
                f"{EVIDENCE_LABEL}. {md['message']} Rule unit {rec['requirements'][0]}; reason {md['reason_code']}.{where} {LEGAL_BOUNDARY}"
            )
            if anchor.get("type") == "ifc_element" and anchor.get("ifc_guid"):
                vguid = _uuid(rec["id"] + ":vp")
                vps = ET.SubElement(topic, "Viewpoints")
                vp = ET.SubElement(vps, "ViewPoint", {"Guid": vguid})
                ET.SubElement(vp, "Viewpoint").text = "viewpoint.bcfv"
                vis = ET.Element("VisualizationInfo", {"Guid": vguid})
                comps = ET.SubElement(vis, "Components")
                sel = ET.SubElement(comps, "Selection")
                ET.SubElement(sel, "Component", {"IfcGuid": anchor["ifc_guid"]})
                ET.SubElement(comps, "Visibility", {"DefaultVisibility": "true"})
                vis.append(_camera(anchor.get("centroid_m") or [0.0, 0.0, 0.0]))
                z.writestr(f"{tguid}/viewpoint.bcfv", _xml(vis))
            z.writestr(f"{tguid}/markup.bcf", _xml(markup))
    return path, len(topics)


def _xyz(parent: ET.Element, tag: str, v) -> None:
    e = ET.SubElement(parent, tag)
    for axis, val in zip("XYZ", v):
        ET.SubElement(e, axis).text = repr(float(val))


def _camera(target) -> ET.Element:
    """Perspective camera 6 m out on a (1, -1, 0.8) diagonal, looking at the element centroid (metres)."""
    offset = (6.0, -6.0, 4.8)
    eye = [t + o for t, o in zip(target, offset)]
    n = sum(o * o for o in offset) ** 0.5
    direction = [-o / n for o in offset]
    cam = ET.Element("PerspectiveCamera")
    _xyz(cam, "CameraViewPoint", eye)
    _xyz(cam, "CameraDirection", direction)
    _xyz(cam, "CameraUpVector", (0.0, 0.0, 1.0))
    ET.SubElement(cam, "FieldOfView").text = "60.0"
    ET.SubElement(cam, "AspectRatio").text = "1.7777777778"
    return cam


def _label(text: str) -> ET.Element:
    e = ET.Element("Label")
    e.text = text
    return e
