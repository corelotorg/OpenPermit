# SPDX-License-Identifier: Apache-2.0
"""PDF plan-set artifact manifest: hashes, versions, supersession and page anchors.

A manifest records, for each PDF in a plan-set version:
* sha256 and size of the exact bytes received (the artifact id is derived from the hash);
* page count and PDF version;
* per-page anchors: 1-based page number, page label, media box, and a sha256
  of the page's decoded content stream so a resubmittal can be diffed page by page;
* the PDF/A claim read from XMP metadata (pdfaid:part / pdfaid:conformance).
  A claim is recorded as a claim; it is not validation. Use a PDF/A validator
  such as veraPDF for conformance.
Supersession is explicit: version N+1 lists the artifact ids it supersedes.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from . import EVIDENCE_LABEL

MANIFEST_PROFILE = "ori-pdf-artifact-manifest-0.1"


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _pdfa_claim(reader: PdfReader) -> dict[str, Any]:
    claim = {"claimed": False, "part": None, "conformance": None,
             "note": "Read from XMP metadata; a claim is not validation (use a PDF/A validator such as veraPDF)."}
    try:
        root = reader.trailer["/Root"]
        meta = root.get("/Metadata")
        if meta is None:
            return claim
        xmp = meta.get_object().get_data().decode("utf-8", "replace")
    except Exception:
        return claim
    part = re.search(r"pdfaid:part(?:>|=\")\s*(\d)", xmp)
    conf = re.search(r"pdfaid:conformance(?:>|=\")\s*([ABUabu])", xmp)
    if part:
        claim.update(claimed=True, part=int(part.group(1)), conformance=(conf.group(1).upper() if conf else None))
    return claim


def describe_pdf(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    data = path.read_bytes()
    digest = _sha256_bytes(data)
    reader = PdfReader(str(path))
    labels = list(reader.page_labels) if reader.page_labels else []
    pages = []
    for i, page in enumerate(reader.pages, 1):
        contents = page.get_contents()
        content_bytes = contents.get_data() if contents is not None else b""
        mb = page.mediabox
        pages.append({
            "page": i,
            "page_label": labels[i - 1] if i - 1 < len(labels) else str(i),
            "mediabox_pt": [float(mb.left), float(mb.bottom), float(mb.right), float(mb.top)],
            "content_sha256": _sha256_bytes(content_bytes),
        })
    header = data[:8].decode("latin-1", "replace")
    m = re.match(r"%PDF-(\d\.\d)", header)
    return {
        "artifact_id": f"urn:ori:artifact:sha256:{digest}",
        "filename": path.name,
        "media_type": "application/pdf",
        "sha256": digest,
        "size_bytes": len(data),
        "pdf_version": m.group(1) if m else None,
        "page_count": len(reader.pages),
        "pdfa": _pdfa_claim(reader),
        "pages": pages,
    }


def build_manifest(pdf_paths: list[str | Path], plan_set_id: str, version: int, submitted_by: str,
                   submitted_at: str, supersedes: list[str] | None = None) -> dict[str, Any]:
    if version < 1:
        raise ValueError("version starts at 1")
    if version > 1 and not supersedes:
        raise ValueError("a version after 1 must name the artifact ids it supersedes")
    return {
        "manifest_profile": MANIFEST_PROFILE,
        "label": EVIDENCE_LABEL,
        "plan_set_id": plan_set_id,
        "version": version,
        "supersedes": list(supersedes or []),
        "submitted_by": submitted_by,
        "submitted_at": submitted_at,
        "artifacts": [describe_pdf(p) for p in pdf_paths],
    }


def evidence_objects(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """One core Evidence object per PDF artifact."""
    out = []
    for a in manifest["artifacts"]:
        out.append({
            "id": f"urn:ori:evidence:plan-set:{manifest['plan_set_id']}:v{manifest['version']}:{a['sha256'][:16]}",
            "type": "Evidence",
            "version": str(manifest["version"]),
            "effective_from": None,
            "effective_to": None,
            "jurisdiction": [],
            "source": [],
            "derived_from": [],
            "supersedes": list(manifest.get("supersedes", [])),
            "metadata": {"label": EVIDENCE_LABEL, "filename": a["filename"], "page_count": a["page_count"], "pdfa": a["pdfa"], "plan_set_id": manifest["plan_set_id"]},
            "evidence_type": "pdf_plan_set",
            "artifact": a["artifact_id"],
            "captured_by": manifest["submitted_by"],
            "captured_at": manifest["submitted_at"],
            "spatial_anchor": None,
            "integrity": {"algorithm": "sha256", "digest": a["sha256"]},
        })
    return out


def diff_manifests(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Page-level change set between two plan-set versions, keyed by page label.

    Reviewers can limit re-review to changed pages. The diff is evidence for
    targeting review, not a finding that unchanged pages still comply.
    """
    def index(m):
        return {p["page_label"]: p["content_sha256"] for a in m["artifacts"] for p in a["pages"]}
    o, n = index(old), index(new)
    return {
        "from_version": old["version"],
        "to_version": new["version"],
        "changed": sorted(k for k in n if k in o and n[k] != o[k]),
        "added": sorted(k for k in n if k not in o),
        "removed": sorted(k for k in o if k not in n),
        "unchanged": sorted(k for k in n if k in o and n[k] == o[k]),
        "note": "Content-stream hash comparison. Unchanged pages are not re-verified findings; a reviewer decides re-review scope.",
    }
