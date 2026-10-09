# SPDX-License-Identifier: Apache-2.0
"""Serialize evaluator results as ORI core objects.

Each Result becomes a core ``Verification`` (spec/ori-core-0.1.schema.json):
* ``outcome`` uses the core enum: unknown -> indeterminate, not_applicable -> not-applicable;
* ``metadata.result_state`` keeps the ORI rule-unit state name;
* ``metadata.label`` and ``metadata.legal_boundary`` mark the record as reviewer evidence, not approval.

The input artifact becomes a core ``Evidence`` object with a sha256 integrity
block. No record here is a ``Decision``: a machine never emits a permit decision.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from . import EVIDENCE_LABEL, LEGAL_BOUNDARY, __version__
from .rules import Result
from .units import EffectiveUnit

VALIDATOR_ID = "urn:ori:validator:ori-verify"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_id_for(artifact_sha256: str, jurisdiction: str, extra: str = "") -> str:
    h = hashlib.sha256(f"{artifact_sha256}|{jurisdiction}|{__version__}|{extra}".encode()).hexdigest()
    return h[:16]


def evidence_object(run_id: str, artifact: dict[str, Any], evidence_type: str, captured_at: str, captured_by: str) -> dict[str, Any]:
    return {
        "id": f"urn:ori:evidence:{run_id}:input",
        "type": "Evidence",
        "version": "1",
        "effective_from": None,
        "effective_to": None,
        "jurisdiction": [],
        "source": [],
        "derived_from": [],
        "supersedes": list(artifact.get("supersedes", [])),
        "metadata": {"label": EVIDENCE_LABEL, "artifact": artifact},
        "evidence_type": evidence_type,
        "artifact": artifact["artifact_id"],
        "captured_by": captured_by,
        "captured_at": captured_at,
        "spatial_anchor": None,
        "integrity": {"algorithm": "sha256", "digest": artifact["sha256"]},
    }


def verification_record(run_id: str, n: int, result: Result, unit: EffectiveUnit, artifact_id: str, evidence_id: str, executed_at: str) -> dict[str, Any]:
    s = result.subject
    return {
        "id": f"urn:ori:verification:{run_id}:{n:04d}",
        "type": "Verification",
        "version": "1",
        "effective_from": None,
        "effective_to": None,
        "jurisdiction": [result.jurisdiction] if result.jurisdiction.startswith("urn:") else [],
        "source": list(unit.unit.get("source", [])),
        "derived_from": [],
        "supersedes": [],
        "metadata": {
            "label": EVIDENCE_LABEL,
            "legal_boundary": LEGAL_BOUNDARY,
            "is_approval": False,
            "result_state": result.state,
            "reason_code": result.reason_code,
            "message": result.message,
            "section": result.section,
            "subsection_part": result.part,
            "rule_unit_title": unit.unit["title"],
            "check_class": unit.unit["check_class"],
            "subject": {"kind": s.kind, "id": s.subject_id, "label": s.label, "anchor": s.anchor},
            "measured": result.measured,
            "required": result.required,
            "facts_used": result.facts_used,
            "layers_applied": result.layers_applied,
            "run_id": run_id,
        },
        "validator": VALIDATOR_ID,
        "validator_version": __version__,
        "inputs": [artifact_id],
        "requirements": [result.unit_id],
        "outcome": result.core_outcome,
        "evidence": [evidence_id],
        "executed_at": executed_at,
        "determinism": "deterministic",
    }


def build_report(results: list[Result], units: list[EffectiveUnit], artifact: dict[str, Any], evidence_type: str,
                 jurisdiction: str, executed_at: str | None = None, captured_by: str = VALIDATOR_ID) -> dict[str, Any]:
    executed_at = executed_at or now_utc()
    by_id = {u.id: u for u in units}
    run_id = run_id_for(artifact["sha256"], jurisdiction, evidence_type)
    ev = evidence_object(run_id, artifact, evidence_type, executed_at, captured_by)
    records = [verification_record(run_id, i, r, by_id[r.unit_id], artifact["artifact_id"], ev["id"], executed_at)
               for i, r in enumerate(results, 1)]
    counts = Counter(r.state for r in results)
    return {
        "report_type": "ori-verification-run",
        "report_version": "0.1-draft",
        "label": EVIDENCE_LABEL,
        "legal_boundary": LEGAL_BOUNDARY,
        "is_approval": False,
        "run_id": run_id,
        "jurisdiction": jurisdiction,
        "validator": VALIDATOR_ID,
        "validator_version": __version__,
        "executed_at": executed_at,
        "artifact": artifact,
        "counts": {k: counts.get(k, 0) for k in ("pass", "fail", "unknown", "not_applicable")},
        "evidence": [ev],
        "records": records,
    }


def dumps(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
