# SPDX-License-Identifier: Apache-2.0
"""Bind ORI-CL facts to an IFC model with IfcOpenShell.

``ori_verify.ifc_extract`` measures the geometric facts of the five implemented
subject kinds. This module adds, driven only by the vocabulary:

* subjects for other vocabulary kinds (e.g. ``building`` -> IfcBuilding), one
  per matching element;
* ``ifc_read`` facts: a property read from a named property set;
* ``encloses:<IfcEntity>[:<PREDEFINED>]`` relation facts for spaces and
  buildings: the number of matching elements contained in the spatial element
  through IfcRelContainedInSpatialStructure (spaces also count elements
  contained in their child spaces). A count of zero is evidence from the model
  only; the evaluator never fails on it (absence from a model is not evidence
  of absence).

``adjacent``, ``above`` and ``distance`` relation facts are not measured from
IFC in 0.1; they come from declared values, so without them those rules give
unknown.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.util.element as uel

from ori_verify.facts import Fact, Subject

from .vocab import Vocabulary, load


def _predef(el) -> str | None:
    p = getattr(el, "PredefinedType", None)
    if p in (None, "NOTDEFINED"):
        t = uel.get_type(el)
        p = getattr(t, "PredefinedType", None) if t is not None else None
    if p == "USERDEFINED":
        return getattr(el, "ObjectType", None)
    return p


def _matches(el, entity: str, predef: str | None) -> bool:
    return el.is_a(entity) and (predef is None or _predef(el) == predef)


def _contained(model, spatial) -> list:
    out = []
    for rel in getattr(spatial, "ContainsElements", []) or []:
        out += list(rel.RelatedElements)
    for rel in getattr(spatial, "IsDecomposedBy", []) or []:
        for child in rel.RelatedObjects:
            if child.is_a("IfcSpace"):
                out += _contained(model, child)
    return out


def _all_contained(model, building) -> list:
    """Every element contained anywhere under a building (storeys, spaces)."""
    out, stack = [], [building]
    while stack:
        s = stack.pop()
        for rel in getattr(s, "ContainsElements", []) or []:
            out += list(rel.RelatedElements)
        for rel in getattr(s, "IsDecomposedBy", []) or []:
            stack += [o for o in rel.RelatedObjects if o.is_a("IfcSpatialStructureElement") or o.is_a("IfcSpatialElement")]
    return out


def _anchor(el, path: Path) -> dict[str, Any]:
    return {"type": "ifc_element", "ifc_guid": el.GlobalId, "ifc_class": el.is_a(), "name": getattr(el, "Name", None), "model": path.name}


def relation_facts_needed(plans: list[dict[str, Any]]) -> dict[str, set[str]]:
    """subject kind -> relation fact names used by the plans."""
    need: dict[str, set[str]] = {}
    for p in plans:
        names = [a["fact"] for c in p["when"] + p["unless"] for a in c["atoms"] if a["fact"].startswith("encloses:")]
        q = p.get("require") or {}
        if q.get("form") == "relation" and q.get("relation") == "encloses":
            names.append(q["fact"])
        need.setdefault(p["subject"], set()).update(names)
    return need


def bind(path: str | Path, subjects: list[Subject], plans: list[dict[str, Any]], vocab: Vocabulary | None = None) -> list[Subject]:
    """Return subjects plus new ones, with vocabulary-driven IFC facts added (never overwritten)."""
    v = vocab or load()
    path = Path(path)
    model = ifcopenshell.open(str(path))
    by_guid = {s.anchor.get("ifc_guid"): s for s in subjects if s.anchor and s.anchor.get("ifc_guid")}
    kinds = {p["subject"] for p in plans}
    out = list(subjects)
    rel_need = relation_facts_needed(plans)
    for kind in sorted(kinds):
        spec = v.subjects[kind]["ifc"]
        existing_kind = any(s.kind == kind for s in subjects)
        for el in model.by_type(spec["name"]):
            if not _matches(el, spec["name"], spec.get("predefined_type")):
                continue
            s = by_guid.get(el.GlobalId)
            if s is None or s.kind != kind:
                if existing_kind:
                    continue  # ifc_extract already chose which elements are subjects of this kind
                s = Subject(kind=kind, subject_id=f"ifc:{el.GlobalId}", label=getattr(el, "Name", None) or el.GlobalId, anchor=_anchor(el, path))
                out.append(s)
            a = _anchor(el, path)
            for f in v.data["facts"]:
                rd = f.get("ifc_read")
                if f["subject"] != kind or not rd or f["name"] in s.facts:
                    continue
                props = uel.get_pset(el, rd["pset"]) or {}
                if rd["property"] in props and props[rd["property"]] is not None:
                    s.facts[f["name"]] = Fact(props[rd["property"]], "ifc_property", a, f"{rd['pset']}.{rd['property']}")
            for name in sorted(rel_need.get(kind, ())):
                if name in s.facts:
                    continue
                _, entity, *pre = name.split(":")
                predef = pre[0] if pre else None
                pool = _all_contained(model, el) if el.is_a("IfcBuilding") else _contained(model, el)
                n = sum(1 for e in pool if _matches(e, entity, predef))
                s.facts[name] = Fact(n, "ifc_property", a, "count via IfcRelContainedInSpatialStructure")
    return out
