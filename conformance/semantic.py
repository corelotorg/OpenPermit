#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Semantic conformance checks that JSON Schema alone cannot express.

These checks intentionally target ORI invariants called out by the public
specification: mappings remain assertions, guidance is not silently promoted to
binding requirements, challenges do not mutate their targets, and declared
precedence graphs are acyclic.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "reference-node" / "graph.py"

_spec = importlib.util.spec_from_file_location("ori_graph", GRAPH_PATH)
assert _spec and _spec.loader
_graph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_graph)


def _authority_classification(obj: dict[str, Any]) -> str | None:
    direct = obj.get("authority_classification")
    if isinstance(direct, str):
        return direct
    metadata = obj.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("authority_classification")
        if isinstance(value, str):
            return value
    return None


def _mapping_requires_assertion(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    mapping_keys = {"maps_from", "maps_to", "mapping_type", "mapped_by"}
    for obj in case.get("objects", []):
        if not isinstance(obj, dict):
            continue
        present = mapping_keys.intersection(obj)
        if present and obj.get("type") != "MappingAssertion":
            errors.append(
                f"{obj.get('id', '<anonymous>')}: mapping semantics {sorted(present)} "
                "must be represented by a MappingAssertion"
            )
    return errors


# Authority classes that can never back a binding Requirement.
STATIC_NON_BINDING_CLASSES = frozenset(
    {
        "federal_guidance",
        "state_guidance",
        "local_guidance",
        "guidance",
        "federal_executive_policy_context",
        "project_self_declared_target",
    }
)
PROFILE_DIRS = (ROOT / "profiles" / "federal", ROOT / "profiles" / "project")


def _profile_declared_non_binding_classes() -> set[str]:
    """Classes declared by published profiles whose legal_boundary is non-binding.

    Any profile that states is_binding_local_law=false makes its
    authority_classification non-binding, so a class added in a new profile is
    covered without editing this file.
    """
    classes: set[str] = set()
    for base in PROFILE_DIRS:
        for path in sorted(base.glob("*.json")) if base.exists() else []:
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(doc, dict):
                continue
            boundary = doc.get("legal_boundary")
            cls = doc.get("authority_classification")
            if isinstance(cls, str) and isinstance(boundary, dict) and boundary.get("is_binding_local_law") is False:
                classes.add(cls)
    return classes


def non_binding_classes() -> set[str]:
    return set(STATIC_NON_BINDING_CLASSES) | _profile_declared_non_binding_classes()


def _guidance_not_requirement(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    guidance_classes = non_binding_classes()
    for obj in case.get("objects", []):
        if not isinstance(obj, dict) or obj.get("type") != "Requirement":
            continue
        authority_class = _authority_classification(obj)
        if authority_class in guidance_classes:
            errors.append(
                f"{obj.get('id', '<anonymous>')}: non-binding authority class "
                f"{authority_class!r} cannot be serialized as a binding Requirement"
            )
    return errors


def _challenge_target_immutable(case: dict[str, Any]) -> list[str]:
    before = case.get("target_before")
    after = case.get("target_after")
    challenge = case.get("challenge")
    errors: list[str] = []
    if not isinstance(before, dict) or not isinstance(after, dict):
        return ["challenge immutability case requires target_before and target_after objects"]
    if before != after:
        errors.append("challenged target changed; challenge/disposition history must be append-only")
    if isinstance(challenge, dict) and challenge.get("subject") != before.get("id"):
        errors.append("challenge subject does not reference the challenged target id")
    return errors


def _precedence_graph_acyclic(case: dict[str, Any]) -> list[str]:
    graph = case.get("graph")
    if not isinstance(graph, dict):
        return ["precedence case requires graph object"]
    if graph.get("type") != "PrecedenceGraph":
        return ["precedence case must explicitly declare type=PrecedenceGraph"]
    try:
        result = _graph.analyze_precedence(graph)
    except ValueError as exc:
        return [f"invalid precedence graph: {exc}"]
    if not result.get("is_dag"):
        return ["declared PrecedenceGraph contains a cycle"]
    return []


# Reason codes that describe missing, unconfirmed or reviewer-only information.
# A Verification carrying one of these may never have outcome "fail"
# (mirrors verification/ori_verify/rules.py MISSING_INFORMATION_REASONS).
MISSING_INFORMATION_REASONS = frozenset(
    {
        "missing_information",
        "unconfirmed_extraction",
        "required_element_not_found",
        "exception_requires_reviewer",
        "geometry_not_measurable",
        "parameter_missing",
    }
)
# ORI rule-unit result states and the core Verification.outcome each must use.
# Provisional mapping: unknown -> indeterminate.
RESULT_STATE_TO_OUTCOME = {"pass": "pass", "fail": "fail", "unknown": "indeterminate", "not_applicable": "not-applicable"}


def _missing_information_not_fail(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for obj in case.get("objects", []):
        if not isinstance(obj, dict) or obj.get("type") != "Verification":
            continue
        md = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
        reason, state, outcome = md.get("reason_code"), md.get("result_state"), obj.get("outcome")
        oid = obj.get("id", "<anonymous>")
        if outcome == "fail" and reason in MISSING_INFORMATION_REASONS:
            errors.append(f"{oid}: missing information ({reason}) must yield indeterminate, never fail")
        if state in RESULT_STATE_TO_OUTCOME and outcome != RESULT_STATE_TO_OUTCOME[state]:
            errors.append(f"{oid}: result_state {state!r} must serialize as outcome {RESULT_STATE_TO_OUTCOME[state]!r}, not {outcome!r}")
    return errors


APPROVAL_DECISION_TYPES = frozenset(
    {"approval", "approve", "approved", "permit_approval", "permit_issued", "permit_issuance", "plan_approval"}
)


def _machine_verification_not_approval(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for obj in case.get("objects", []):
        if not isinstance(obj, dict):
            continue
        oid = obj.get("id", "<anonymous>")
        md = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
        if obj.get("type") == "Verification" and (
            md.get("is_approval") is True or md.get("decision_type") in APPROVAL_DECISION_TYPES
        ):
            errors.append(f"{oid}: a Verification is reviewer evidence and cannot be serialized as approval")
        if obj.get("type") == "Decision" and str(obj.get("decision_type", "")).lower() in APPROVAL_DECISION_TYPES:
            decided_by = str(obj.get("decided_by", ""))
            if decided_by.startswith("urn:ori:validator:"):
                errors.append(f"{oid}: approval decisions must be made by an accountable official, not by validator {decided_by}")
    return errors


def _rule_unit_authority(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for obj in case.get("objects", []):
        if not isinstance(obj, dict) or obj.get("rule_unit_profile") != "ori-rule-unit-0.1":
            continue
        oid = obj.get("id", "<anonymous>")
        evaluator = obj.get("evaluator") if isinstance(obj.get("evaluator"), dict) else {}
        if obj.get("check_class") == "judgment" and evaluator.get("kind") in ("deterministic_function", "data_lookup"):
            errors.append(f"{oid}: judgment-class rule units cannot have an automated evaluator ({evaluator.get('kind')})")
        base = obj.get("base_model") if isinstance(obj.get("base_model"), dict) else {}
        if base.get("binding") is True:
            errors.append(f"{oid}: a model-code base layer is not binding by itself")
        layers = [l for l in obj.get("jurisdiction_layers", []) if isinstance(l, dict)]
        binding = [l for l in layers if l.get("binding") is True]
        if obj.get("authority_classification") != "model_code_not_adopted" and not binding:
            errors.append(f"{oid}: authority {obj.get('authority_classification')!r} requires at least one binding jurisdiction layer")
        for l in binding:
            if l.get("authority_class") not in ("state_adopted_code", "local_adopted_amendment"):
                errors.append(f"{oid}: binding layer {l.get('layer_id')} has non-adopted authority class {l.get('authority_class')!r}")
    return errors


LOCAL_ONLY_BODY_CLASSES = frozenset({"local_building_official_policy"})


def _interpretability_is_evidence(case: dict[str, Any]) -> list[str]:
    """Interpretability records are analysis, not law. Linked records must be fetched and read,
    local policies stay local, clarifications stay drafts, and two-reviewer status needs two
    independent human reviewers (an ORI pre-score does not count)."""
    errors: list[str] = []
    for obj in case.get("objects", []):
        if not isinstance(obj, dict) or not isinstance(obj.get("interpretability"), dict):
            continue
        oid = obj.get("id", "<anonymous>")
        it = obj["interpretability"]
        dets = [d for d in it.get("determinations", []) if isinstance(d, dict)]
        local = [d for d in it.get("local_operationalizations", []) if isinstance(d, dict)]
        for d in dets + local:
            ver = d.get("verification") if isinstance(d.get("verification"), dict) else {}
            if ver.get("status") != "fetched_and_read" or not str(d.get("url", "")).startswith("https://"):
                errors.append(f"{oid}: linked record {d.get('citation')!r} must be fetched and read from an https URL; nothing is cited from memory")
        for d in dets:
            if d.get("body_class") in LOCAL_ONLY_BODY_CLASSES:
                errors.append(f"{oid}: local policy {d.get('citation')!r} binds one jurisdiction; list it under local_operationalizations, not determinations")
        clar = it.get("candidate_clarification")
        if isinstance(clar, dict) and clar.get("status") != "DRAFT_not_submitted":
            errors.append(f"{oid}: candidate clarifications stay DRAFT_not_submitted until the owner decides to submit")
        humans = [r for r in it.get("reviewers", []) if isinstance(r, dict) and r.get("role", "reviewer") == "reviewer" and r.get("independent") is True]
        if it.get("scoring_status") in ("two_reviewer_agreed", "adjudicated"):
            if len(humans) < 2:
                errors.append(f"{oid}: {it.get('scoring_status')} needs two independent human reviewers; pre-scores do not count")
            elif it.get("scoring_status") == "two_reviewer_agreed" and len({r.get("score") for r in humans}) != 1:
                errors.append(f"{oid}: two_reviewer_agreed but the reviewers' scores differ; use adjudicated")
        rel = {d.get("relevance") for d in dets + local}
        strength = it.get("evidence_strength")
        if strength == "none_found" and (dets or local):
            errors.append(f"{oid}: evidence_strength none_found but records are linked")
        if strength == "direct" and "direct" not in rel:
            errors.append(f"{oid}: evidence_strength direct needs at least one direct record")
    return errors


# --- no-code-text (docs/CITATION-POLICY.md) ---------------------------------------------
# ORI cites, paraphrases and links; it never reproduces code text. This lint cannot hold the
# ICC text to compare against (that would itself store the text), so it checks structure and
# the tell-tale signs of copied wording instead.
OFFICIAL_SOURCE_HOSTS = frozenset(
    {
        "codes.iccsafe.org",
        "law.lis.virginia.gov",
        "www.dhcd.virginia.gov",
        "dhcd.virginia.gov",
    }
)
MAX_QUOTED_WORDS = 4
MAX_PARAPHRASE_CHARS = 400
# Normative register typical of model-code sentences. ORI paraphrases use plain verbs
# ("must", "may not"); "shall" in ORI's own text is a sign of copied wording.
_CODE_REGISTER = __import__("re").compile(r"\bshall\b(?:\s+not)?\s+(?:be|have|comply|provide|extend|not|consist|conform|meet|project)?", __import__("re").IGNORECASE)
_QUOTED = __import__("re").compile(r"[\"\u201c]([^\"\u201d]+)[\"\u201d]|(?<![A-Za-z])'([^']+)'(?![A-Za-z])")
# Unit fields that hold ORI prose. Evidence URLs, ids and numeric parameters are not prose.
_PROSE_PATHS = (
    ("title",),
    ("paraphrase",),
    ("jurisdiction_layers", "*", "amendment_ref", "note"),
    ("interpretability", "rationale"),
    ("interpretability", "ambiguous_terms", "*", "term"),
    ("interpretability", "ambiguous_terms", "*", "issue"),
    ("interpretability", "intent_questions", "*"),
    ("interpretability", "candidate_clarification", "note"),
    ("interpretability", "determinations", "*", "holding_summary"),
    ("interpretability", "local_operationalizations", "*", "holding_summary"),
)


def _walk(obj: Any, path: tuple[str, ...], trail: str = "") -> list[tuple[str, str]]:
    if not path:
        return [(trail, obj)] if isinstance(obj, str) else []
    head, rest = path[0], path[1:]
    if head == "*":
        if not isinstance(obj, list):
            return []
        out: list[tuple[str, str]] = []
        for i, item in enumerate(obj):
            out += _walk(item, rest, f"{trail}[{i}]")
        return out
    if not isinstance(obj, dict) or head not in obj:
        return []
    return _walk(obj[head], rest, f"{trail}.{head}" if trail else head)


def _host(url: str) -> str:
    rest = url.split("://", 1)[1] if "://" in url else ""
    return rest.split("/", 1)[0].lower()


def _no_code_text(case: dict[str, Any]) -> list[str]:
    """Rule units must paraphrase and link, never reproduce code text."""
    errors: list[str] = []
    for obj in case.get("objects", []):
        if not isinstance(obj, dict) or obj.get("rule_unit_profile") != "ori-rule-unit-0.1":
            continue
        oid = obj.get("id", "<anonymous>")
        para = obj.get("paraphrase")
        if not isinstance(para, str) or len(para.strip()) < 20:
            errors.append(f"{oid}: every rule unit needs an ORI paraphrase of the requirement's effect (paraphrase field)")
        elif len(para) > MAX_PARAPHRASE_CHARS:
            errors.append(f"{oid}: paraphrase exceeds {MAX_PARAPHRASE_CHARS} characters; summarize, do not transcribe")
        url = obj.get("source_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            errors.append(f"{oid}: every rule unit needs an https source_url linking to the official text")
        elif _host(url) not in OFFICIAL_SOURCE_HOSTS:
            errors.append(f"{oid}: source_url host {_host(url)!r} is not an official source (allowed: {sorted(OFFICIAL_SOURCE_HOSTS)})")
        for link in obj.get("source_links", []) or []:
            if isinstance(link, dict) and _host(str(link.get("url", ""))) not in OFFICIAL_SOURCE_HOSTS:
                errors.append(f"{oid}: source_links entry {link.get('url')!r} is not an official source")
        for path in _PROSE_PATHS:
            for where, text in _walk(obj, path):
                for m in _QUOTED.finditer(text):
                    quoted = m.group(1) or m.group(2) or ""
                    if len(quoted.split()) > MAX_QUOTED_WORDS:
                        errors.append(f"{oid}: {where} quotes {len(quoted.split())} words; quote at most {MAX_QUOTED_WORDS} (a term name) and paraphrase the rest")
                if _CODE_REGISTER.search(text):
                    errors.append(f"{oid}: {where} uses code register ('shall'); paraphrase in ORI's own words")
                if where.endswith("term") and len(text.split()) > MAX_QUOTED_WORDS + 3:
                    errors.append(f"{oid}: {where} is longer than a term name; use a short label")
    return errors


# --- ORI-CL (spec/ori-cl-0.1-draft.md) ---------------------------------------------------
VERIFICATION_DIR = ROOT / "verification"


def _ori_cl():
    """Import the ORI-CL package from verification/ (it depends on ori_verify)."""
    import sys

    if str(VERIFICATION_DIR) not in sys.path:
        sys.path.insert(0, str(VERIFICATION_DIR))
    import ori_cl  # noqa: PLC0415
    from ori_cl import vocab  # noqa: PLC0415

    return ori_cl, vocab


def _ori_cl_vocabulary_provenance(case: dict[str, Any]) -> list[str]:
    """Every ORI-CL vocabulary term records an allowed source and its license; restricted
    classifications (MasterFormat, UniFormat, OmniClass) and code text never supply terms."""
    _, vocab = _ori_cl()
    errors: list[str] = []
    for obj in case.get("objects", []):
        if isinstance(obj, dict) and "vocabulary_id" in obj:
            errors += [f"{obj['vocabulary_id']}: {e}" for e in vocab.provenance_errors(obj)]
    return errors


def _ori_cl_statement(case: dict[str, Any]) -> list[str]:
    """ORI-CL source must parse, pass the compiler's static checks, and compile to rule units
    that pass no-code-text and rule-unit-authority."""
    ori_cl, _ = _ori_cl()
    errors: list[str] = []
    for obj in case.get("objects", []):
        src = obj.get("ori_cl_source") if isinstance(obj, dict) else None
        if not isinstance(src, str):
            continue
        try:
            compiled = ori_cl.compile_text(src)
        except (ori_cl.OriClSyntaxError, ori_cl.OriClCompileError) as e:
            errors.append(f"{obj.get('id', '<ori-cl>')}: {e}")
            continue
        units = [c["unit"] for c in compiled]
        errors += _no_code_text({"objects": units})
        errors += _rule_unit_authority({"objects": units})
    return errors


def _open_corpora_manifest(case: dict[str, Any]) -> list[str]:
    """Every term merger study corpus source records a license or public-domain basis, a local
    copy of the license evidence with SHA-256, and a full citation of the original source."""
    _ori_cl()
    from ori_cl import corpus_license  # noqa: PLC0415

    errors: list[str] = []
    for obj in case.get("objects", []):
        if isinstance(obj, dict) and "corpora" in obj:
            errors += corpus_license.manifest_errors(obj)
    return errors


def _plan_overlay_training_gate(case: dict[str, Any]) -> list[str]:
    """A plan overlay used as training, ground-truth or evaluation data passes the overlay schema and
    the licensing gate: license basis, local license copy with SHA-256, citation, a training-set
    license (no NonCommercial or NoDerivatives terms), and no unreviewed auto-extracted labels.
    Overlays for reviewer use only must still pass the schema."""
    import sys

    if str(VERIFICATION_DIR) not in sys.path:
        sys.path.insert(0, str(VERIFICATION_DIR))
    from ori_takeoff import overlay as ov  # noqa: PLC0415

    errors: list[str] = []
    for obj in case.get("objects", []):
        if not isinstance(obj, dict) or obj.get("overlay_profile") != "ori-plan-overlay-0.1":
            continue
        errors += [f"{obj.get('overlay_id')}: schema: {e}" for e in ov.schema_errors(obj)]
        if obj.get("dataset_role") in ("training", "ground_truth", "evaluation"):
            errors += [f"{obj.get('overlay_id')}: training gate: {e}" for e in ov.training_gate_errors(obj)]
    return errors


RULES = {
    "plan-overlay-training-gate": _plan_overlay_training_gate,
    "open-corpora-manifest": _open_corpora_manifest,
    "ori-cl-vocabulary-provenance": _ori_cl_vocabulary_provenance,
    "ori-cl-statement": _ori_cl_statement,
    "no-code-text": _no_code_text,
    "interpretability-is-evidence": _interpretability_is_evidence,
    "missing-information-not-fail": _missing_information_not_fail,
    "machine-verification-not-approval": _machine_verification_not_approval,
    "rule-unit-authority": _rule_unit_authority,
    "mapping-requires-assertion": _mapping_requires_assertion,
    "guidance-not-requirement": _guidance_not_requirement,
    "challenge-target-immutable": _challenge_target_immutable,
    "precedence-graph-acyclic": _precedence_graph_acyclic,
}


def semantic_errors(case: dict[str, Any]) -> list[str]:
    rule = case.get("rule")
    if rule not in RULES:
        return [f"unknown semantic rule: {rule!r}"]
    return RULES[rule](case)
