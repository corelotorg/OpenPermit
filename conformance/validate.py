#!/usr/bin/env python3
"""Validate ORI conformance fixtures against the draft core JSON Schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "spec" / "ori-core-0.1.schema.json"
FIXTURE_DIR = ROOT / "conformance" / "fixtures"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    fixtures = sorted(FIXTURE_DIR.glob("*.json"))
    if not fixtures:
        print("ERROR: no fixtures found", file=sys.stderr)
        return 2

    failed = False
    for fixture in fixtures:
        instance = load_json(fixture)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        if errors:
            failed = True
            print(f"FAIL {fixture.relative_to(ROOT)}")
            for error in errors:
                path = "/".join(str(p) for p in error.path) or "<root>"
                print(f"  {path}: {error.message}")
        else:
            print(f"PASS {fixture.relative_to(ROOT)}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
