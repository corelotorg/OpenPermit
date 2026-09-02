#!/usr/bin/env python3
"""Validate ORI schemas, profiles, jurisdiction inventories and semantic negatives."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from semantic import semantic_errors

ROOT = Path(__file__).resolve().parents[1]
CORE_SCHEMA_PATH = ROOT / "spec" / "ori-core-0.1.schema.json"
GUIDANCE_SCHEMA_PATH = ROOT / "spec" / "ori-guidance-profile-0.1.schema.json"
JURISDICTION_SCHEMA_PATH = ROOT / "spec" / "ori-jurisdiction-inventory-0.1.schema.json"
FIXTURE_DIR = ROOT / "conformance" / "fixtures"
NEGATIVE_DIR = ROOT / "conformance" / "negative"
GUIDANCE_PROFILE_DIR = ROOT / "profiles" / "federal"
JURISDICTION_PROFILE_DIR = ROOT / "profiles" / "jurisdictions"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_paths(schema_path: Path, paths: list[Path]) -> bool:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failed = False

    for path in paths:
        instance = load_json(path)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        if errors:
            failed = True
            print(f"FAIL {path.relative_to(ROOT)}")
            for error in errors:
                location = "/".join(str(p) for p in error.path) or "<root>"
                print(f"  {location}: {error.message}")
        else:
            print(f"PASS {path.relative_to(ROOT)}")

    return failed


def validate_semantic_cases(paths: list[Path]) -> bool:
    failed = False
    for path in paths:
        case = load_json(path)
        expected = case.get("expected")
        errors = semantic_errors(case)
        rejected = bool(errors)

        if expected == "fail" and rejected:
            print(f"PASS {path.relative_to(ROOT)} (correctly rejected)")
            for error in errors:
                print(f"  REJECT: {error}")
        elif expected == "pass" and not rejected:
            print(f"PASS {path.relative_to(ROOT)}")
        else:
            failed = True
            print(f"FAIL {path.relative_to(ROOT)}")
            if expected == "fail":
                print("  expected semantic rejection, but case was accepted")
            elif expected == "pass":
                for error in errors:
                    print(f"  unexpected rejection: {error}")
            else:
                print(f"  invalid expected value: {expected!r}")
    return failed


def main() -> int:
    fixtures = sorted(FIXTURE_DIR.glob("*.json"))
    negatives = sorted(NEGATIVE_DIR.glob("*.json"))
    guidance_profiles = sorted(GUIDANCE_PROFILE_DIR.glob("*.json"))
    jurisdiction_profiles = sorted(JURISDICTION_PROFILE_DIR.rglob("*.json"))

    if not fixtures:
        print("ERROR: no core fixtures found", file=sys.stderr)
        return 2
    if not negatives:
        print("ERROR: no negative semantic fixtures found", file=sys.stderr)
        return 2
    if not guidance_profiles:
        print("ERROR: no guidance profiles found", file=sys.stderr)
        return 2
    if not jurisdiction_profiles:
        print("ERROR: no jurisdiction inventories found", file=sys.stderr)
        return 2

    failed = False
    failed |= validate_paths(CORE_SCHEMA_PATH, fixtures)
    failed |= validate_paths(GUIDANCE_SCHEMA_PATH, guidance_profiles)
    failed |= validate_paths(JURISDICTION_SCHEMA_PATH, jurisdiction_profiles)
    failed |= validate_semantic_cases(negatives)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
