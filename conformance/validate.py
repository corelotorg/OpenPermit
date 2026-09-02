#!/usr/bin/env python3
"""Validate ORI core fixtures and machine-readable guidance profiles."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CORE_SCHEMA_PATH = ROOT / "spec" / "ori-core-0.1.schema.json"
GUIDANCE_SCHEMA_PATH = ROOT / "spec" / "ori-guidance-profile-0.1.schema.json"
FIXTURE_DIR = ROOT / "conformance" / "fixtures"
GUIDANCE_PROFILE_DIR = ROOT / "profiles" / "federal"


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


def main() -> int:
    fixtures = sorted(FIXTURE_DIR.glob("*.json"))
    profiles = sorted(GUIDANCE_PROFILE_DIR.glob("*.json"))

    if not fixtures:
        print("ERROR: no core fixtures found", file=sys.stderr)
        return 2
    if not profiles:
        print("ERROR: no guidance profiles found", file=sys.stderr)
        return 2

    failed = False
    failed |= validate_paths(CORE_SCHEMA_PATH, fixtures)
    failed |= validate_paths(GUIDANCE_SCHEMA_PATH, profiles)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
