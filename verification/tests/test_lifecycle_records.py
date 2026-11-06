# SPDX-License-Identifier: Apache-2.0
"""Tests for the four lifecycle records (v0.1 drafts): schema validation, JSON-LD expansion and
compaction round-trip with the pinned inline context, and regression tests for key invariants.
Every fixture is synthetic; no remote context is ever fetched."""
from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest
from pyld import jsonld

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ori_records_lifecycle_t", ROOT / "conformance" / "records_lifecycle.py")
rl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rl)
VOCAB = json.loads((ROOT / "vocab" / "ori-lifecycle-records-vocab-0.1.json").read_text(encoding="utf-8"))
CTX = rl.pinned_context()
RULES = {"transmission-envelope-record": rl.transmission_envelope_record, "completeness-report-record": rl.completeness_report_record,
         "limited-change-record": rl.limited_change_record, "decision-record": rl.decision_record}
POS = sorted((ROOT / "conformance" / "positive").glob("lifecycle-*.json"))
NEG = sorted((ROOT / "conformance" / "negative").glob("lifecycle-*.json"))
NS = "https://openpermit.dev/ns/"


def _no_remote(url, options=None):  # inline contexts only
    raise jsonld.JsonLdError(f"remote context fetch refused: {url}", "loading document failed")


OPTS = {"documentLoader": _no_remote}


def _case(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _records():
    for p in POS:
        for o in _case(p)["objects"]:
            if o.get("record_profile") in rl.PROFILES:
                yield pytest.param(o, id=f"{p.stem}:{o['record_profile']}")


def _strip(doc):
    d = copy.deepcopy(doc); d.pop("@context"); return d


def test_fixture_sets_cover_all_four_profiles():
    for kind, files in (("positive", POS), ("negative", NEG)):
        rules = {_case(p)["rule"] for p in files}
        assert rules == set(RULES), f"{kind} fixtures must cover all four rules"
    assert [t["profile"] for t in VOCAB["types"] if t["profile"]] == list(rl.PROFILES)


@pytest.mark.parametrize("path", POS, ids=lambda p: p.stem)
def test_positive_fixtures_pass(path):
    case = _case(path)
    assert case["expected"] == "pass"
    assert RULES[case["rule"]](case) == []


# Each negative must fail for its stated reason, not for an incidental one.
NEG_REASON = {
    "envelope-receipt-is-approval-true": "is_approval must be false",
    "envelope-unrebuilt-fabricated-hash": "no fabricated hash",
    "envelope-unrebuilt-content-address": "content-addressed",
    "envelope-received-unknown-time": "known received_at",
    "envelope-change-record-unlinked": "does not link it",
    "completeness-missing-info-fail": "must give result unknown, not fail",
    "completeness-accepted-blocking-unknown": "cannot accept while blocking_status is unknown",
    "completeness-blocking-unknown-clock-started": "starts the clock but this report is not accepted",
    "completeness-overall-overclaimed": "overall 'complete' does not match",
    "completeness-is-approval-true": "is_approval must be false",
    "completeness-blocking-items-dropped": "blocking_items must list exactly",
    "change-globalid-key-short": "does not match '^[0-9A-Za-z_$]{22}$'",
    "change-globalid-key-mismatch": "does not match its ifc_global_id",
    "change-unrebuilt-child-after-anchor": "child model is not built",
    "change-unrebuilt-child-fabricated-hash": "no fabricated hash",
    "change-verified-scope-copies-declaration": "verified_scope given without a comparison",
    "change-carry-forward-verified-uncompared": "carry_forward cannot be verified",
    "change-is-approval-true": "is_approval must be false",
    "decision-is-machine-true": "is_machine must be false",
    "decision-is-machine-missing": "is_machine must be false",
    "decision-is-approval-true": "is_approval must be false",
    "decision-conditions-without-records": "conditions must reference exactly",
    "decision-conditional-without-conditions": "needs at least one condition",
    "decision-validity-inverted": "valid_until must be after valid_from",
    "decision-pre-review-current-unverified": "pre_review_status stays unknown",
    "decision-unpinned-context-conditions-literal": "@context must equal the pinned context",
}


def test_negative_reason_table_matches_files():
    assert sorted(NEG_REASON) == sorted(p.stem.removeprefix("lifecycle-") for p in NEG)


@pytest.mark.parametrize("path", NEG, ids=lambda p: p.stem)
def test_negative_fixtures_fail_for_stated_reason(path):
    case = _case(path)
    assert case["expected"] == "fail"
    errors = RULES[case["rule"]](case)
    reason = NEG_REASON[path.stem.removeprefix("lifecycle-")]
    assert any(reason in e for e in errors), errors


# ---- JSON Schema alone (independent of semantic checks) ----
@pytest.mark.parametrize("rec", list(_records()))
def test_schema_accepts_valid_records(rec):
    assert rl._schema_errors(rec, rec["record_profile"]) == []


@pytest.mark.parametrize("profile,field,bad", [
    ("ori-transmission-envelope-0.1", "is_approval", True),
    ("ori-completeness-report-0.1", "is_approval", True),
    ("ori-limited-change-record-0.1", "is_approval", True),
    ("ori-decision-record-0.1", "is_approval", True),
    ("ori-decision-record-0.1", "is_machine", True),
    ("ori-decision-record-0.1", "decided_by_role", "system"),
    ("ori-decision-record-0.1", "conditions", ["unknown"]),
    ("ori-completeness-report-0.1", "envelope_ref", "unknown"),
])
def test_schema_rejects(profile, field, bad):
    rec = next(r.values[0] for r in _records() if r.values[0]["record_profile"] == profile)
    rec = copy.deepcopy(rec); rec[field] = bad
    assert rl._schema_errors(rec, profile)


# ---- JSON-LD ----
def test_context_fix_conditions_and_iri_terms_coerced():
    # Regression for design CHECKS.md: Decision conditions must be IRI references, not literals.
    assert CTX["conditions"]["@type"] == "@id"
    assert "id" not in CTX and "type" not in CTX
    coerced = sorted(k for k, v in CTX.items() if isinstance(v, dict) and v.get("@type") == "@id")
    assert coerced == VOCAB["iri_terms"]
    assert not set(VOCAB["iri_or_unknown_terms"]["terms"]) & set(coerced)


@pytest.mark.parametrize("rec", list(_records()))
def test_expansion_types_references_as_iris(rec):
    expanded = jsonld.expand(rec, OPTS)
    assert len(expanded) == 1
    node = expanded[0]
    assert node["@id"] == rec["@id"]
    assert node["@type"] == [NS + rec["@type"]]
    # Every coerced reference expands to a node reference, never a literal; unknown is never an IRI.
    def walk(n):
        if isinstance(n, dict):
            if n.get("@id") == "unknown":
                raise AssertionError("unknown became an IRI")
            for k, v in n.items():
                term = k.removeprefix(NS)
                if term in VOCAB["iri_terms"] and k.startswith(NS):
                    for x in v:
                        assert "@id" in x and "@value" not in x, (term, x)
                walk(v)
        elif isinstance(n, list):
            for x in n:
                walk(x)
    walk(expanded)
    if rec["@type"] == "Decision" and rec["conditions"]:
        assert [c["@id"] for c in node[NS + "conditions"]] == rec["conditions"]


@pytest.mark.parametrize("rec", list(_records()))
def test_every_array_term_is_a_set(rec):
    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(v, list) and not k.startswith("@"):
                    assert isinstance(CTX.get(k), dict) and CTX[k].get("@container") in ("@set", "@list"), k
                walk(v)
        elif isinstance(n, list):
            for x in n:
                walk(x)
    walk(_strip(rec))


@pytest.mark.parametrize("rec", list(_records()))
def test_compaction_round_trip(rec):
    expanded = jsonld.expand(rec, OPTS)
    compacted = jsonld.compact(expanded, CTX, OPTS)
    assert compacted["@context"] == CTX
    assert _strip(compacted) == _strip(rec)
    # Graph-level: expansion of the compacted form is identical, and canonical RDF matches.
    assert jsonld.expand(compacted, OPTS) == expanded
    nq = {"algorithm": "URDNA2015", "format": "application/n-quads", **OPTS}
    assert jsonld.normalize(rec, nq) == jsonld.normalize(compacted, nq)


def test_touched_elements_index_preserved_through_expansion():
    rec = next(r.values[0] for r in _records() if r.values[0]["@type"] == "LimitedChangeRecord")
    node = jsonld.expand(rec, OPTS)[0]
    idx = sorted(x["@index"] for x in node[NS + "touched_elements"])
    assert idx == sorted(rec["touched_elements"])
    assert all(rl.GLOBAL_ID.match(k) for k in idx)


def test_design_draft_context_had_literal_conditions():
    """The design-draft context (no @id on conditions) is what the fix removes; prove the bug is real."""
    rec = next(r.values[0] for r in _records() if r.values[0]["@type"] == "Decision" and r.values[0]["conditions"])
    bad = copy.deepcopy(rec); bad["@context"] = copy.deepcopy(CTX)
    bad["@context"]["conditions"] = {"@id": "dev.openpermit:conditions", "@container": "@set"}
    node = jsonld.expand(bad, OPTS)[0]
    assert all("@value" in c for c in node[NS + "conditions"])


# ---- invariant regressions on mutated copies ----
_BASE = {"TransmissionEnvelope": "lifecycle-envelope-resubmittal-unrebuilt-view",
         "CompletenessReport": "lifecycle-completeness-blocking-unknown-indeterminate",
         "LimitedChangeRecord": "lifecycle-change-unrebuilt-child", "Decision": "lifecycle-decision-conditions-unknown-validity"}


def _first(t):
    case = _case(ROOT / "conformance" / "positive" / f"{_BASE[t]}.json")
    return copy.deepcopy(next(o for o in case["objects"] if o.get("@type") == t))


def test_unrebuilt_artifacts_never_carry_a_hash():
    for t in ("TransmissionEnvelope", "LimitedChangeRecord"):
        rec = _first(t)
        hashrefs = list(rl._hashrefs(rec))
        unrebuilt = [h for _, h in hashrefs if h["artifact_state"] == "unrebuilt"]
        assert unrebuilt, t
        assert all(h["sha256"] == "unknown" and h["hash_status"] == "unknown" for h in unrebuilt)
        unrebuilt[0]["sha256"] = "0" * 64
        assert any("no fabricated hash" in e for e in rl._hashref_errors(rec))


def test_missing_information_is_unknown_never_fail():
    rec = _first("CompletenessReport")
    for basis in ("missing_information", "unsupported", "unverifiable", "applicability_unknown"):
        r = copy.deepcopy(rec); r["items"][1].update(basis=basis, result="fail", evidence_refs=["urn:ori:x:1"])
        assert any("must give result unknown" in e for e in rl.completeness_report_record({"objects": [r]}))


def test_blocking_unknown_prevents_acceptance_and_clock():
    rec = _first("CompletenessReport")
    overall, bstatus, blocking, _ = rl._derive(rec["items"], rec["requirement_sets"])
    assert (overall, bstatus, blocking) == ("indeterminate", "unknown", ["window-metadata"])
    # Advisory uncertainty alone does not block; a blocking unknown always does.
    items = copy.deepcopy(rec["items"]); items[1]["effect"] = "advisory"
    sets = [dict(rec["requirement_sets"][0], coverage="complete")]
    assert rl._derive(items, sets)[:2] == ("indeterminate", "satisfied")


def test_carry_forward_declared_scope_distinct_from_verified_scope():
    rec = _first("LimitedChangeRecord")
    assert rec["reviewer_scope"]["declared_scope"] == "listed_elements_only"
    assert rec["reviewer_scope"]["verified_scope_status"] == "unknown" and rec["reviewer_scope"]["verified_scope"] == []
    r = copy.deepcopy(rec)
    r["reviewer_scope"].update(verified_scope=sorted(r["touched_elements"]), verified_scope_status="verified")
    assert any("verified_scope given without a comparison" in e for e in rl.limited_change_record({"objects": [r]}))


# ---- dialect mappings (HUD forms, NAICS-based categories) ----
MAPS = json.loads((ROOT / "vocab" / "ori-lifecycle-dialect-mappings-0.1.json").read_text(encoding="utf-8"))


def _schema_has(profile, pointer):
    s = json.loads((ROOT / "spec" / f"{profile}.schema.json").read_text(encoding="utf-8"))
    node = s
    for part in pointer.strip("/").split("/"):
        props = node.get("properties", {})
        if part not in props:
            return False
        node = props[part]
        if "$ref" in node and node["$ref"].startswith("#/$defs/"):
            node = s["$defs"][node["$ref"].split("/")[-1]]
    return True


def _entries():
    for d in MAPS["dialects"]:
        for f in d.get("forms", []):
            yield from f["fields"]
        yield from d.get("categories", [])


def test_dialect_targets_exist_and_labels_are_short():
    entries = list(_entries())
    assert entries
    for m in entries:
        assert m["mapping_type"] in MAPS["mapping_types"]
        assert len(m["source_label"].split()) <= 4, m["source_label"]
        if m["mapping_type"] != "no_neutral_target":
            assert _schema_has(m["record"], m["target"]), m


def test_outcome_mappings_are_never_exact():
    # A source label about acceptance never becomes a Decision outcome automatically.
    for m in _entries():
        if m.get("target") == "/outcome":
            assert m["mapping_type"] == "related_pending_review"


def test_naics_categories_match_fixture_classification():
    cats = [c for d in MAPS["dialects"] for c in d.get("categories", [])]
    assert all(re.fullmatch(r"[0-9]{2,6}", c["naics_code"]) for c in cats)
    rec = _first("TransmissionEnvelope")
    codes = {c["code"] for c in rec["sender"]["classifications"]}
    assert codes <= {c["naics_code"] for c in cats}
    bad = copy.deepcopy(rec); bad["sender"]["classifications"][0]["code"] = "23611X"
    assert rl._schema_errors(bad, "ori-transmission-envelope-0.1")
