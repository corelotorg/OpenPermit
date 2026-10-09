#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate ORI schemas, profiles, jurisdiction inventories, rule units, verification examples and semantic cases."""

from __future__ import annotations

import json
import re
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
POSITIVE_SEMANTIC_DIR = ROOT / "conformance" / "positive"
GUIDANCE_PROFILE_DIR = ROOT / "profiles" / "federal"
PROJECT_TARGET_PROFILE_DIR = ROOT / "profiles" / "project"
JURISDICTION_PROFILE_DIR = ROOT / "profiles" / "jurisdictions"
# Synthetic example inventories (CC0) let the public tree validate without any real jurisdiction file.
EXAMPLE_PROFILE_DIR = ROOT / "profiles" / "examples"
RULE_UNIT_SCHEMA_PATH = ROOT / "spec" / "ori-rule-unit-0.1.schema.json"
DECLARED_SCHEMA_PATH = ROOT / "spec" / "ori-declared-values-0.1.schema.json"
MANIFEST_SCHEMA_PATH = ROOT / "spec" / "ori-pdf-artifact-manifest-0.1.schema.json"
RULES_DIR = ROOT / "rules"
VERIFICATION_EXAMPLES = ROOT / "verification" / "examples"
EVIDENCE_LABEL = "Reviewer evidence, not approval"


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


def _errors(validator, instance) -> list[str]:
    return [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in validator.iter_errors(instance)]


def validate_rule_unit_collections(paths: list[Path]) -> bool:
    """Collection header + every unit (rule-unit schema and core schema) + sources (core)."""
    rule_schema = load_json(RULE_UNIT_SCHEMA_PATH)
    unit_v = Draft202012Validator(rule_schema, format_checker=FormatChecker())
    header_v = Draft202012Validator({"$defs": rule_schema["$defs"], "$ref": "#/$defs/collectionHeader"})
    core_v = Draft202012Validator(load_json(CORE_SCHEMA_PATH), format_checker=FormatChecker())
    failed = False
    for path in paths:
        col = load_json(path)
        problems = [f"<header> {m}" for m in _errors(header_v, col)]
        units = col.get("units", []) + col.get("va_added_units", [])
        for u in units:
            problems += [f"{u.get('id')}: {m}" for m in _errors(unit_v, u)]
            problems += [f"{u.get('id')} (core): {m}" for m in _errors(core_v, u)]
        problems += semantic_errors({"rule": "rule-unit-authority", "objects": units})
        problems += semantic_errors({"rule": "interpretability-is-evidence", "objects": units})
        problems += semantic_errors({"rule": "no-code-text", "objects": units})
        for src in col.get("sources", []):
            problems += [f"{src.get('id')} (core): {m}" for m in _errors(core_v, src)]
        if problems:
            failed = True
            print(f"FAIL {path.relative_to(ROOT)}")
            for m in problems:
                print(f"  {m}")
        else:
            print(f"PASS {path.relative_to(ROOT)} ({len(units)} rule units)")
    return failed


def validate_verification_reports(paths: list[Path]) -> bool:
    """Every record and evidence object is core-valid and labeled reviewer evidence, never approval."""
    core_v = Draft202012Validator(load_json(CORE_SCHEMA_PATH), format_checker=FormatChecker())
    failed = False
    for path in paths:
        rep = load_json(path)
        problems = []
        if rep.get("label") != EVIDENCE_LABEL or rep.get("is_approval") is not False:
            problems.append("report must carry the reviewer-evidence label and is_approval=false")
        for obj in rep.get("records", []) + rep.get("evidence", []):
            problems += [f"{obj.get('id')}: {m}" for m in _errors(core_v, obj)]
            if obj.get("type") == "Decision":
                problems.append(f"{obj.get('id')}: a verification report may not contain a Decision")
        for rec in rep.get("records", []):
            md = rec.get("metadata", {})
            if md.get("label") != EVIDENCE_LABEL or md.get("is_approval") is not False:
                problems.append(f"{rec.get('id')}: record must be labeled reviewer evidence with is_approval=false")
        sem = semantic_errors({"rule": "missing-information-not-fail", "objects": rep.get("records", [])})
        sem += semantic_errors({"rule": "machine-verification-not-approval", "objects": rep.get("records", [])})
        problems += sem
        if problems:
            failed = True
            print(f"FAIL {path.relative_to(ROOT)}")
            for m in problems:
                print(f"  {m}")
        else:
            print(f"PASS {path.relative_to(ROOT)} ({len(rep.get('records', []))} verification records)")
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


# Text files where ORI writes about codes. history/ and recovered/ hold archived material and
# are covered by the maintainers' code-text audit, not linted.
CODE_TEXT_LINT_DIRS = ("docs", "research", "rules", "spec", "verification", "profiles", "reference-node", "conformance", "vocab")
CODE_TEXT_LINT_SUFFIXES = (".md", ".json", ".py", ".ids", ".txt", ".html", ".oricl", ".ebnf")
CODE_TEXT_LINT_ROOT_FILES = ("README.md", "index.html", "llms.txt")
_LONG_SHALL_QUOTE = re.compile(r"[\"\u201c]([^\"\u201d\n]{20,})[\"\u201d]")
# Files that must mention the pattern to explain or test it.
CODE_TEXT_LINT_ALLOW = {
    "docs/CITATION-POLICY.md",
    "docs/CODE-TEXT-AUDIT-2026-09-28.md",
    "conformance/semantic.py",
    "conformance/validate.py",
    "conformance/negative/no-code-text-verbatim-quote.json",
    "conformance/negative/ori-cl-statement-code-register.json",
}


def lint_code_text() -> bool:
    """Repo-wide lint: a quoted span of 6+ words in normative 'shall' register is treated as
    reproduced code text (docs/CITATION-POLICY.md). Returns True on failure."""
    failed = False
    paths = [ROOT / f for f in CODE_TEXT_LINT_ROOT_FILES if (ROOT / f).exists()]
    for d in CODE_TEXT_LINT_DIRS:
        paths += [p for p in sorted((ROOT / d).rglob("*")) if p.is_file() and p.suffix in CODE_TEXT_LINT_SUFFIXES and "__pycache__" not in p.parts]
    hits = []
    for p in paths:
        rel = p.relative_to(ROOT).as_posix()
        if rel in CODE_TEXT_LINT_ALLOW:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in _LONG_SHALL_QUOTE.finditer(line):
                q = m.group(1)
                if len(q.split()) >= 6 and re.search(r"\bshall\b", q, re.IGNORECASE):
                    hits.append(f"{rel}:{n}: quoted code-register text ({len(q.split())} words)")
    if hits:
        failed = True
        print("FAIL code-text lint (docs/CITATION-POLICY.md):")
        for h in hits:
            print(f"  {h}")
    else:
        print(f"PASS code-text lint ({len(paths)} files; no quoted code-register text)")
    return failed


ORI_CL_VOCAB = ROOT / "vocab" / "ori-cl-vocab-0.1.json"
OPEN_CORPORA_MANIFEST = ROOT / "research" / "data" / "ori-cl-open-corpora-DRAFT.json"
OPEN_CORPORA_SCHEMA = ROOT / "spec" / "ori-open-corpora-manifest-0.1.schema.json"


def validate_open_corpora() -> bool:
    """The term merger study corpora manifest passes its schema and the open-corpora-manifest rule:
    every source has a license record, a local license copy (SHA-256 checked for in-repo copies)
    and a full citation. Returns True on failure."""
    m = load_json(OPEN_CORPORA_MANIFEST)
    problems = _errors(Draft202012Validator(load_json(OPEN_CORPORA_SCHEMA), format_checker=FormatChecker()), m)
    problems += semantic_errors({"rule": "open-corpora-manifest", "objects": [m]})
    if problems:
        print(f"FAIL {OPEN_CORPORA_MANIFEST.relative_to(ROOT)}")
        for p in problems:
            print(f"  {p}")
        return True
    print(f"PASS {OPEN_CORPORA_MANIFEST.relative_to(ROOT)} ({len(m['corpora'])} sources; each has license record, local license copy and citation)")
    return False


def validate_ori_cl() -> bool:
    """ORI-CL vocabulary provenance, and every rules/**/*.oricl file compiles to rule units that
    pass the rule-unit schema, no-code-text and rule-unit-authority. Returns True on failure."""
    failed = False
    errs = semantic_errors({"rule": "ori-cl-vocabulary-provenance", "objects": [load_json(ORI_CL_VOCAB)]})
    if errs:
        failed = True
        print(f"FAIL {ORI_CL_VOCAB.relative_to(ROOT)}")
        for e in errs:
            print(f"  {e}")
    else:
        print(f"PASS {ORI_CL_VOCAB.relative_to(ROOT)} (every term has source and license)")
    unit_v = Draft202012Validator(load_json(RULE_UNIT_SCHEMA_PATH), format_checker=FormatChecker())
    for src in sorted(RULES_DIR.rglob("*.oricl")):
        text = src.read_text(encoding="utf-8")
        problems = semantic_errors({"rule": "ori-cl-statement", "objects": [{"id": src.name, "ori_cl_source": text}]})
        if not problems:
            import ori_cl  # importable after the semantic rule put verification/ on sys.path
            for c in ori_cl.compile_text(text):
                problems += [f"{c['unit']['id']}: {m}" for m in _errors(unit_v, c["unit"])]
        if problems:
            failed = True
            print(f"FAIL {src.relative_to(ROOT)}")
            for m in problems:
                print(f"  {m}")
        else:
            print(f"PASS {src.relative_to(ROOT)} (ORI-CL compiles; units pass schema, no-code-text, authority)")
    return failed


PLAN_OVERLAY_SCHEMA = ROOT / "spec" / "ori-plan-overlay-0.1.schema.json"


def validate_plan_overlays() -> bool:
    """Plan-takeoff example overlays pass the overlay schema; ground-truth overlays also pass the
    licensing gate (rule plan-overlay-training-gate). Returns True on failure."""
    failed = False
    for path in sorted((VERIFICATION_EXAMPLES / "takeoff").glob("*.overlay.json")):
        doc = load_json(path)
        errs = semantic_errors({"rule": "plan-overlay-training-gate", "objects": [doc]})
        if errs:
            failed = True
            print(f"FAIL {path.relative_to(ROOT)}")
            for e in errs[:20]:
                print(f"  {e}")
        else:
            print(f"PASS {path.relative_to(ROOT)} (plan overlay schema; role {doc['dataset_role']})")
    return failed


def main() -> int:
    fixtures = sorted(FIXTURE_DIR.glob("*.json"))
    negatives = sorted(NEGATIVE_DIR.glob("*.json"))
    guidance_profiles = sorted(GUIDANCE_PROFILE_DIR.glob("*.json")) + sorted(PROJECT_TARGET_PROFILE_DIR.glob("*.json"))
    positives = sorted(POSITIVE_SEMANTIC_DIR.glob("*.json"))
    jurisdiction_profiles = sorted(JURISDICTION_PROFILE_DIR.rglob("*.json")) + sorted(EXAMPLE_PROFILE_DIR.rglob("*.json"))

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
    rule_collections = sorted(RULES_DIR.rglob("*.units.json"))
    if not rule_collections:
        print("ERROR: no rule-unit collections found", file=sys.stderr)
        return 2
    failed |= validate_rule_unit_collections(rule_collections)
    failed |= validate_paths(DECLARED_SCHEMA_PATH, sorted((VERIFICATION_EXAMPLES / "declared").glob("*.json")))
    failed |= validate_paths(MANIFEST_SCHEMA_PATH, sorted((VERIFICATION_EXAMPLES / "pdf").glob("manifest-*.json")))
    failed |= validate_verification_reports(sorted((VERIFICATION_EXAMPLES / "reports").glob("*.report.json")))
    failed |= validate_semantic_cases(negatives)
    failed |= validate_semantic_cases(positives)
    failed |= validate_ori_cl()
    failed |= validate_open_corpora()
    failed |= validate_plan_overlays()
    failed |= lint_code_text()

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
