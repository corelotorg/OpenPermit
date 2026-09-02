#!/usr/bin/env python3
"""Semantic conformance checks that JSON Schema alone cannot express.

These checks intentionally target ORI invariants called out by the public
specification: mappings remain assertions, guidance is not silently promoted to
binding requirements, challenges do not mutate their targets, and declared
precedence graphs are acyclic.
"""

from __future__ import annotations

import importlib.util
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


def _guidance_not_requirement(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    guidance_classes = {"federal_guidance", "state_guidance", "local_guidance", "guidance"}
    for obj in case.get("objects", []):
        if not isinstance(obj, dict) or obj.get("type") != "Requirement":
            continue
        authority_class = _authority_classification(obj)
        if authority_class in guidance_classes:
            errors.append(
                f"{obj.get('id', '<anonymous>')}: guidance authority class "
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


RULES = {
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
