#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Export ORI JurisdictionInventory profiles as a BLDS-shaped companion CSV.

This is an **interchange adapter**. BLDS (Building & Land Development
Specification, permitdata.org) is a useful permit open-data vocabulary but is
not actively maintained. ORI's model is the authority- and evidence-bearing
regulatory graph; this adapter only projects inventory rows (fees, inspection
requirements, approvals) into BLDS column names so systems that already ingest
BLDS-shaped data can join against ORI. It does not claim BLDS certification.

Inventory rows are not permit instances: a fee-schedule row is not a fee
collected, an inspection requirement is not an inspection result, and an
approval row is not an issued approval.

Before exporting, each profile is validated against
spec/ori-jurisdiction-inventory-0.1.schema.json and every exported row must
resolve its source id(s) to a declared source with a locator. The export is
refused otherwise.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "spec" / "ori-jurisdiction-inventory-0.1.schema.json"
PROFILE_DIR = ROOT / "profiles" / "jurisdictions"
EXAMPLE_DIR = ROOT / "profiles" / "examples"

BLDS_COLUMNS = [
    "PermitNum",
    "Description",
    "IssuedDate",
    "StatusCurrent",
    "StatusMapped",
    "PermitClass",
    "PermitClassMapped",
    "WorkClass",
    "WorkClassMapped",
    "PermitType",
    "PermitTypeMapped",
    "PermitTypeDesc",
    "Fee",
    "Link",
    "Publisher",
    "LastUpdated",
    "OriginalCity",
    "OriginalState",
]
ORI_COLUMNS = [
    "ORI_Id",
    "ORI_InventoryId",
    "ORI_InventoryType",
    "ORI_Jurisdiction",
    "ORI_AuthorityId",
    "ORI_SourceIds",
    "ORI_SourceLocators",
    "ORI_EffectiveFrom",
    "ORI_Amount",
    "ORI_Rate",
    "ORI_RateUnit",
    "ORI_Minimum",
    "ORI_Currency",
    "ORI_ProfileStatus",
    "ORI_Completeness",
    "ORI_LegalDetermination",
]
FIELDNAMES = BLDS_COLUMNS + ORI_COLUMNS

ROW_KINDS = (
    ("approvals", "approval_requirement", "ApprovalRequirement"),
    ("fees", "fee_schedule_item", "FeeScheduleItem"),
    ("inspections", "inspection_requirement", "InspectionRequirement"),
)


class ProvenanceError(ValueError):
    """Raised when a profile cannot be exported with complete provenance."""


def _s(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)]


def schema_errors(profile: dict[str, Any]) -> list[str]:
    from jsonschema import Draft202012Validator, FormatChecker

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(profile), key=lambda e: list(e.path))
    ]


def permit_class_mapped(domain: str) -> str:
    # Only map what the profile states; do not guess.
    return "Residential" if domain.startswith("residential") else ""


def work_class_mapped(project_type: str) -> str:
    return "New" if project_type.startswith("new_") else ""


def rows_for_profile(profile: dict[str, Any]) -> list[dict[str, str]]:
    sources = {s["id"]: s for s in profile.get("sources", []) if isinstance(s, dict) and s.get("id")}
    jurisdiction = profile.get("jurisdiction") or {}
    scope = profile.get("scope") or {}
    domain = _s(scope.get("domain"))
    project_type = _s(scope.get("project_type"))
    errors: list[str] = []
    out: list[dict[str, str]] = []

    for key, inventory_type, type_mapped in ROW_KINDS:
        for item in profile.get(key) or []:
            if not isinstance(item, dict):
                errors.append(f"{key}: non-object item")
                continue
            item_id = _s(item.get("id"))
            source_ids = _as_list(item.get("source"))
            if not item_id:
                errors.append(f"{key}: item without id")
            if not source_ids:
                errors.append(f"{item_id or key}: no source id")
            missing = [sid for sid in source_ids if sid not in sources or not sources[sid].get("locator")]
            if missing:
                errors.append(f"{item_id}: source id(s) not declared with a locator: {', '.join(missing)}")
                continue
            first = sources[source_ids[0]] if source_ids else {}
            label = _s(item.get("label"))
            row = {k: "" for k in FIELDNAMES}
            row.update(
                {
                    "PermitNum": f"ORI:{item_id}",
                    "Description": label,
                    # Inventory rows have no issuance date; effective dates go to ORI_EffectiveFrom.
                    "IssuedDate": "",
                    "StatusCurrent": _s(profile.get("status")),
                    # Inventory rows are not permit instances; no BLDS status enum applies.
                    "StatusMapped": "",
                    "PermitClass": domain,
                    "PermitClassMapped": permit_class_mapped(domain),
                    "WorkClass": project_type,
                    "WorkClassMapped": work_class_mapped(project_type),
                    "PermitType": inventory_type,
                    "PermitTypeMapped": type_mapped,
                    "PermitTypeDesc": label,
                    "Fee": _s(item.get("amount")) if key == "fees" else "",
                    "Link": _s(first.get("locator")),
                    "Publisher": _s(first.get("publisher")),
                    "LastUpdated": _s(profile.get("as_of")),
                    "OriginalCity": _s(jurisdiction.get("name")),
                    "OriginalState": _s(jurisdiction.get("state")),
                    "ORI_Id": item_id,
                    "ORI_InventoryId": _s(profile.get("id")),
                    "ORI_InventoryType": inventory_type,
                    "ORI_Jurisdiction": _s(jurisdiction.get("id")),
                    "ORI_AuthorityId": _s(item.get("authority")),
                    "ORI_SourceIds": ";".join(source_ids),
                    "ORI_SourceLocators": ";".join(_s(sources[sid].get("locator")) for sid in source_ids),
                    "ORI_EffectiveFrom": _s(item.get("effective_from") or first.get("effective_from")),
                    "ORI_Amount": _s(item.get("amount")),
                    "ORI_Rate": _s(item.get("rate")),
                    "ORI_RateUnit": _s(item.get("rate_unit")),
                    "ORI_Minimum": _s(item.get("minimum")),
                    "ORI_Currency": _s(item.get("currency")),
                    "ORI_ProfileStatus": _s(profile.get("status")),
                    "ORI_Completeness": _s(scope.get("completeness")),
                    "ORI_LegalDetermination": _s(scope.get("legal_determination")),
                }
            )
            out.append(row)

    if errors:
        raise ProvenanceError("; ".join(errors))
    return out


def export(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        profile = json.loads(path.read_text(encoding="utf-8"))
        errs = schema_errors(profile)
        if errs:
            raise ProvenanceError(f"{path}: schema invalid: {'; '.join(errs)}")
        try:
            rows.extend(rows_for_profile(profile))
        except ProvenanceError as exc:
            raise ProvenanceError(f"{path}: {exc}") from None
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export ORI JurisdictionInventory profiles as BLDS-shaped companion CSV.")
    ap.add_argument("profiles", nargs="*", type=Path, help="JurisdictionInventory JSON files (default: all under profiles/jurisdictions and profiles/examples)")
    ap.add_argument("--out", type=Path, help="CSV output path (default: stdout)")
    args = ap.parse_args(argv)

    paths = args.profiles or sorted(PROFILE_DIR.rglob("*.json")) + sorted(EXAMPLE_DIR.rglob("*.json"))
    if not paths:
        print("ERROR: no JurisdictionInventory profiles found", file=sys.stderr)
        return 2
    try:
        rows = export(paths)
    except ProvenanceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("export refused: provenance or schema check failed", file=sys.stderr)
        return 1

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        fh = args.out.open("w", newline="", encoding="utf-8")
    else:
        fh = sys.stdout
    try:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.out:
            fh.close()
    print(f"exported {len(rows)} row(s) from {len(paths)} profile(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
