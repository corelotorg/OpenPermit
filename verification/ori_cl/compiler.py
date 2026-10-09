# SPDX-License-Identifier: Apache-2.0
"""Check and compile ORI-CL rules into ORI rule units and check plans.

``compile_document`` returns, for each rule block:

* ``unit``: an ORI rule unit (spec/ori-rule-unit-0.1.schema.json). Its
  ``paraphrase`` and ``title`` are generated from the ORI-CL statement, so the
  prose is ORI's rendering of the logic and never code text.
* ``plan``: a JSON check plan run by ``ori_cl.evaluator``. If the rule has a
  ``check`` line, the unit's evaluator points at the existing function in
  ``verification/ori_verify/rules.py``; the tests prove the plan and the
  function give the same state and reason code.

Static checks run first. Any error stops compilation with line numbers.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from fractions import Fraction
from typing import Any

from . import syntax
from .syntax import Atom, Condition, Document, Rule
from .vocab import Vocabulary, load

UNIT_ID_PREFIX = "urn:ori:rule-unit:irc2021-va:"
EVALUATOR_IMPL = "verification/ori_cl/evaluator.py#evaluate_plan"
RULES_IMPL = "verification/ori_verify/rules.py#"
RECORDED_AT = "2026-09-28"
# Same list as conformance/semantic.py OFFICIAL_SOURCE_HOSTS (a test keeps them equal).
OFFICIAL_SOURCE_HOSTS = frozenset({"codes.iccsafe.org", "law.lis.virginia.gov", "www.dhcd.virginia.gov", "dhcd.virginia.gov"})
_SHALL = re.compile(r"\bshall\b", re.IGNORECASE)
MAX_TERM_WORDS = 4
MAX_NOTE_WORDS = 16
CMP_WORDS = {"<=": "at most", ">=": "at least", "<": "less than", ">": "more than", "=": "equal to"}
LIST_TYPES = {"length_list"}
QUANTITY_TYPES = {"length", "area", "count", "ratio"}
REL_TYPES = {"encloses": "count", "adjacent": "boolean", "above": "boolean", "distance": "length"}
LAYER_BASE = "base"


class OriClCompileError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _host(url: str) -> str:
    return url.split("://", 1)[1].split("/", 1)[0].lower() if "://" in url else ""


def _label(name: str) -> str:
    return name.replace("_", " ")


class _Checker:
    def __init__(self, doc: Document, rule: Rule, vocab: Vocabulary):
        self.doc, self.r, self.v = doc, rule, vocab
        self.errors: list[str] = []
        self.facts = vocab.facts

    def err(self, msg: str, line: int | None = None):
        self.errors.append(f"{self.r.rule_id} (line {line or self.r.line}): {msg}")

    # facts ------------------------------------------------------------------------------
    def fact_type(self, name: str) -> tuple[str, str | None] | None:
        r = self.r
        if r.derive and name == r.derive[0] and name in self.facts:
            f = self.facts[name]
            return f["datatype"], f.get("unit")
        f = self.facts.get(name)
        if f is None:
            self.err(f"fact {name!r} is not in the vocabulary")
            return None
        if r.subject and f["subject"] != r.subject[0]:
            self.err(f"fact {name!r} belongs to subject {f['subject']!r}, not {r.subject[0]!r}")
        return f["datatype"], f.get("unit")

    def rel_type(self, rel: str, entity: str, predef: str | None) -> tuple[str, str | None]:
        names = self.v.ifc_names
        if entity not in names:
            self.err(f"IFC entity {entity} is not in the vocabulary (ifc_terms)")
        elif predef not in names[entity]:
            self.err(f"predefined type {predef} of {entity} is not in the vocabulary")
        dt = REL_TYPES[rel]
        return dt, ("in" if dt == "length" else None)

    # params -----------------------------------------------------------------------------
    def decls(self, name: str) -> list[syntax.Param]:
        return [p for p in self.r.params if p.name == name]

    def param_ref(self, name: str, cmp: str | None, unit: str | None):
        ds = self.decls(name)
        if not ds:
            self.err(f"parameter {name!r} is used but never declared with a param line")
            return
        for p in ds:
            if cmp is not None and p.cmp != cmp:
                self.err(f"parameter {name!r} is declared with {p.cmp} but used with {cmp}", p.line)
            if unit is not None and p.unit != unit:
                self.err(f"parameter {name!r} unit {p.unit} does not match the quantity unit {unit}", p.line)

    def literal_ok(self, fact: str, dt: str, value: Any):
        if dt == "boolean" and not isinstance(value, bool):
            self.err(f"{fact} is boolean; compare with true or false")
        elif dt == "enum":
            vals = self.v.enum_values(fact) or []
            if value not in vals:
                self.err(f"{value!r} is not a vocabulary value of {fact} ({vals})")
        elif dt not in ("boolean", "enum"):
            self.err(f"'is' needs a boolean or enumerated fact; {fact} is {dt}")

    def atom(self, a: Atom):
        if a.kind == "rel":
            dt, unit = self.rel_type(a.relation, a.entity, a.predef)
            if a.relation == "distance":
                self.param_ref(a.param, a.cmp, unit)
            return
        t = self.fact_type(a.fact)
        if t is None:
            return
        dt, unit = t
        if a.kind == "is":
            self.literal_ok(a.fact, dt, a.value)
        elif a.kind == "in":
            for v in a.value:
                self.literal_ok(a.fact, dt, v)
        elif a.kind == "cmp":
            if dt not in QUANTITY_TYPES:
                self.err(f"comparator needs a quantity; {a.fact} is {dt}")
            self.param_ref(a.param, a.cmp, unit)

    def check(self) -> list[str]:
        r, v = self.r, self.v
        if r.subject is None:
            self.err("missing subject line")
        else:
            kind, entity, predef = r.subject
            s = v.subjects.get(kind)
            if s is None:
                self.err(f"subject kind {kind!r} is not in the vocabulary")
            elif s["ifc"]["name"] != entity or s["ifc"].get("predefined_type") != predef:
                self.err(f"subject {kind} maps to {s['ifc']['name']} {s['ifc'].get('predefined_type') or ''}".rstrip() + f", not {entity} {predef or ''}".rstrip())
        if r.cite is None:
            self.err("missing cite line (authority)")
        elif r.rule_id.split(":", 1)[0] != r.cite["section"]:
            self.err(f"rule id section {r.rule_id.split(':', 1)[0]} does not match cite {r.cite['section']}")
        if not r.links:
            self.err("missing link line (official text)")
        for url in r.links:
            if _host(url) not in OFFICIAL_SOURCE_HOSTS:
                self.err(f"link host {_host(url)!r} is not an official source")
        if not r.adopts:
            self.err("missing adopt line; say how the adopting jurisdiction treats this rule")
        for a in r.adopts:
            if a.layer not in self.doc.layers:
                self.err(f"adopt names layer {a.layer!r}, which has no context layer line")
        if self.doc.base is None:
            self.err("the file has no 'context base' line")
        adopted = {a.layer for a in r.adopts}
        deleted = {a.layer for a in r.adopts if a.mode == "deletes"}
        for p in r.params:
            if p.layer != LAYER_BASE and p.layer not in adopted:
                self.err(f"parameter {p.name} is placed at layer {p.layer!r} without an adopt line for it", p.line)
            if p.layer in deleted:
                self.err(f"parameter {p.name} is placed at a layer that deletes the rule", p.line)
            if p.unit not in v.units:
                self.err(f"unit {p.unit!r} is not in the vocabulary", p.line)
            if p.locator is not None:
                self.note_text(p.locator, "locator", p.line)
            if p.applies_when is not None:
                t = self.fact_type(p.applies_when[0])
                if t:
                    self.literal_ok(p.applies_when[0], t[0], p.applies_when[1])
        seen = {}
        for p in r.params:
            key = (p.name, p.layer)
            if key in seen:
                self.err(f"parameter {p.name} is declared twice at {p.layer}", p.line)
            seen[key] = p
        for m in r.measures:
            self.fact_type(m.fact)
            for g in (m.start, m.end, m.along):
                if g is not None and g not in v.geometry:
                    self.err(f"reference geometry {g!r} is not in the vocabulary")
            if m.within:
                self.param_ref(m.within, None, None)
        if r.check is not None:
            from ori_verify import rules as _rules  # local import keeps the parser usable alone
            if r.check not in _rules.RULES:
                self.err(f"check {r.check!r} is not an ORI rule function")
            elif r.subject and _rules.SUBJECT_KINDS[r.check] != r.subject[0]:
                self.err(f"check {r.check} runs on {_rules.SUBJECT_KINDS[r.check]}, not {r.subject[0]}")
        if r.derive is not None:
            target, a, b = r.derive
            tt, ta, tb = self.fact_type(target), self.fact_type(a), self.fact_type(b)
            if tt and ta and tb:
                try:
                    _derive_factor(v, ta[1], tb[1], tt[1])
                except ValueError as e:
                    self.err(str(e))
        for c in r.when + r.unless:
            for a in c.atoms:
                self.atom(a)
        if r.reviewer_terms:
            if r.require is not None or r.check is not None:
                self.err("a reviewer rule states no automated requirement or check")
            for t in r.reviewer_terms:
                if len(t.split()) > MAX_TERM_WORDS:
                    self.err(f"reviewer term {t!r} is longer than {MAX_TERM_WORDS} words; name the term, do not quote text")
                self.note_text(t, "term")
            if any(e.mode != "reviewer" for e in r.excepts):
                self.err("a reviewer rule cannot carry allow or use exceptions")
        elif r.require is None:
            self.err("missing require line (or reviewer terms for a judgment rule)")
        if r.require is not None:
            self.require(r.require)
        for e in r.excepts:
            for a in e.condition.atoms:
                self.atom(a)
            if e.mode in ("allow", "use"):
                if r.require is None or r.require.form != "compare":
                    self.err(f"'{e.mode}' exceptions apply to a single compared quantity (require <fact> <cmp> <param>)")
                else:
                    unit = self.quantity_unit(r.require.fact)
                    self.param_ref(e.param, r.require.cmp, unit)
            elif r.require is not None and r.require.form not in ("compare", "each"):
                self.err("'reviewer' exceptions apply to compared quantities")
        return self.errors

    def quantity_unit(self, fact: str) -> str | None:
        t = self.fact_type(fact)
        return t[1] if t else None

    def require(self, q: syntax.Requirement):
        if q.form == "relation":
            dt, unit = self.rel_type(q.relation, q.entity, q.predef)
            if q.relation == "distance":
                self.param_ref(q.param, q.cmp, unit)
            return
        t = self.fact_type(q.fact)
        if t is None:
            return
        dt, unit = t
        if q.form in ("each", "spread"):
            if dt not in LIST_TYPES:
                self.err(f"'{q.form}' needs a list of values; {q.fact} is {dt}")
            self.param_ref(q.param, q.cmp, unit)
        elif q.form in ("compare", "between"):
            if dt not in QUANTITY_TYPES:
                self.err(f"'{q.form}' needs a quantity; {q.fact} is {dt}")
            if q.form == "compare":
                self.param_ref(q.param, q.cmp, unit)
                if q.bound:
                    bt = self.fact_type(q.bound)
                    if bt and bt[1] != unit:
                        self.err(f"bound {q.bound} unit {bt[1]} differs from {unit}")
            else:
                self.param_ref(q.param, None, unit)
                self.param_ref(q.upper, None, unit)
        elif q.form == "present":
            if dt != "boolean":
                self.err(f"'present' needs a boolean fact; {q.fact} is {dt}")

    def note_text(self, text: str, what: str, line: int | None = None):
        if _SHALL.search(text):
            self.err(f"{what} {text!r} uses model-code register; ORI-CL text is ORI's own", line)
        if len(text.split()) > MAX_NOTE_WORDS:
            self.err(f"{what} is longer than {MAX_NOTE_WORDS} words", line)


def _derive_factor(v: Vocabulary, ua: str | None, ub: str | None, ut: str | None) -> Fraction:
    units = v.units
    for u in (ua, ub, ut):
        if u not in units or units[u]["si_factor"] is None:
            raise ValueError(f"derive needs units with SI factors; got {u!r}")
    if not (units[ua]["quantity_kind"] == units[ub]["quantity_kind"] == "length" and units[ut]["quantity_kind"] == "area"):
        raise ValueError("derive supports length times length giving area")
    return Fraction(str(units[ua]["si_factor"])) * Fraction(str(units[ub]["si_factor"])) / Fraction(str(units[ut]["si_factor"]))


# ---- compile ---------------------------------------------------------------------------------
def _atom_plan(v: Vocabulary, a: Atom) -> dict[str, Any]:
    if a.kind == "rel":
        d = {"kind": "rel", "relation": a.relation, "fact": v.fact_for_relation(a.relation, a.entity, a.predef)}
        if a.relation == "distance":
            d.update(kind="cmp", cmp=a.cmp, param=a.param)
        return d
    d = {"kind": a.kind, "fact": a.fact}
    if a.kind == "is":
        d.update(value=a.value, negated=a.negated)
    elif a.kind == "in":
        d.update(values=list(a.value))
    else:
        d.update(cmp=a.cmp, param=a.param)
    return d


def _cond_plan(v: Vocabulary, c: Condition) -> dict[str, Any]:
    return {"op": c.op or "and", "atoms": [_atom_plan(v, a) for a in c.atoms]}


def _param_record(p: syntax.Param) -> dict[str, Any]:
    d: dict[str, Any] = {"name": p.name, "comparator": p.cmp if p.cmp != "=" else "==", "quantity": {"value": p.value, "unit": p.unit},
                         "value_status": p.status, "source": p.source}
    if p.applies_when is not None:
        f, val = p.applies_when
        d["applies_when"] = f"{f} == {str(val).lower() if isinstance(val, bool) else val}"
    if p.locator is not None:
        d["locator_detail"] = p.locator
    return d


def _canonical(rule: Rule) -> str:
    return json.dumps(asdict(rule) | {"line": 0}, sort_keys=True, default=str)


def _plan(rule: Rule, v: Vocabulary) -> dict[str, Any]:
    req = rule.require
    plan: dict[str, Any] = {
        "ori_cl": "0.1",
        "rule_id": rule.rule_id,
        "subject": rule.subject[0],
        "ifc": {"entity": rule.subject[1], "predefined_type": rule.subject[2]},
        "check": rule.check,
        "unless": [_cond_plan(v, c) for c in rule.unless],
        "when": [_cond_plan(v, c) for c in rule.when],
        "require": None,
        "excepts": [],
        "reviewer_terms": list(rule.reviewer_terms),
        "derive": None,
        "measures": [asdict(m) for m in rule.measures],
    }
    if rule.derive:
        t, a, b = rule.derive
        f = _derive_factor(v, v.facts[a]["unit"], v.facts[b]["unit"], v.facts[t]["unit"])
        plan["derive"] = {"target": t, "a": a, "b": b, "num": f.numerator, "den": f.denominator}
    if req is not None:
        d = {k: val for k, val in asdict(req).items() if val not in (None, False)}
        if req.form == "relation":
            d["fact"] = v.fact_for_relation(req.relation, req.entity, req.predef)
        plan["require"] = d
    for e in rule.excepts:
        plan["excepts"].append({"when": _cond_plan(v, e.condition), "mode": e.mode, "param": e.param, "optional": e.optional})
    required = []
    if req is not None:
        required += [p for p in (req.param, req.upper) if p]
    for c in rule.when + rule.unless:
        required += [a.param for a in c.atoms if a.param]
    required += [e.param for e in rule.excepts if e.param and not e.optional]
    plan["params_required"] = list(dict.fromkeys(required))
    plan["params_optional"] = [e.param for e in rule.excepts if e.param and e.optional]
    plan["params_reported"] = [m.within for m in rule.measures if m.within]
    return plan


def _facts_used(rule: Rule, v: Vocabulary) -> list[tuple[str, str, str | None, bool]]:
    """(name, datatype, unit, required) in first-use order."""
    out: dict[str, tuple[str, str, str | None, bool]] = {}

    def add(name, required, dt=None, unit=None):
        if name in out:
            if required and not out[name][3]:
                out[name] = (*out[name][:3], True)
            return
        f = v.facts.get(name)
        out[name] = (name, dt or f["datatype"], unit if dt else f.get("unit"), required)

    req = rule.require
    for c in rule.unless + rule.when:
        for a in c.atoms:
            if a.kind == "rel":
                add(v.fact_for_relation(a.relation, a.entity, a.predef), True, REL_TYPES[a.relation], "in" if a.relation == "distance" else None)
            else:
                add(a.fact, True)
    if req is not None:
        if req.form == "relation":
            add(v.fact_for_relation(req.relation, req.entity, req.predef), True, REL_TYPES[req.relation], "in" if req.relation == "distance" else None)
        else:
            add(req.fact, not (rule.derive and rule.derive[0] == req.fact) and not req.bound)
            if req.bound:
                add(req.bound, False)
    if rule.derive:
        add(rule.derive[1], False)
        add(rule.derive[2], False)
    for e in rule.excepts:
        for a in e.condition.atoms:
            if a.kind != "rel":
                add(a.fact, False)
    return list(out.values())


def _input_key(kind: str, name: str) -> str:
    return f"{kind}.{re.sub(r'[^a-z0-9_]+', '_', name.lower()).strip('_')}"


def gloss(rule: Rule, v: Vocabulary) -> str:
    """Deterministic English rendering of the rule (used as the unit's paraphrase)."""
    subj = v.subjects[rule.subject[0]]["label"] if rule.subject and rule.subject[0] in v.subjects else "subject"

    def fl(name):
        f = v.facts.get(name)
        return f["label"] if f else _label(name)

    def atom(a: Atom) -> str:
        if a.kind == "rel":
            tgt = f"{a.entity}{' ' + a.predef if a.predef else ''}"
            if a.relation == "distance":
                return f"the distance to {tgt} is {CMP_WORDS[a.cmp]} {_label(a.param)}"
            return {"encloses": f"it contains {tgt}", "adjacent": f"it touches {tgt}", "above": f"it is above {tgt}"}[a.relation]
        if a.kind == "is":
            val = a.value if not isinstance(a.value, bool) else ("yes" if a.value else "no")
            return f"{fl(a.fact)} is {'not ' if a.negated else ''}{val}"
        if a.kind == "in":
            return f"{fl(a.fact)} is one of {', '.join(map(str, a.value))}"
        return f"{fl(a.fact)} is {CMP_WORDS[a.cmp]} {_label(a.param)}"

    def cond(c: Condition) -> str:
        return f" {c.op} ".join(atom(a) for a in c.atoms)

    parts = [f"For {'an' if subj[:1] in 'aeiou' else 'a'} {subj}"]
    if rule.when:
        parts.append(", where " + " and ".join(cond(c) for c in rule.when))
    parts.append(": ")
    q = rule.require
    if rule.reviewer_terms:
        parts.append("a reviewer decides whether it complies; terms at issue: " + "; ".join(rule.reviewer_terms))
    elif q.form == "each":
        parts.append(f"every {fl(q.fact)} is {CMP_WORDS[q.cmp]} {_label(q.param)}")
    elif q.form == "spread":
        parts.append(f"the largest minus the smallest {fl(q.fact)} is {CMP_WORDS[q.cmp]} {_label(q.param)}")
    elif q.form == "between":
        parts.append(f"{fl(q.fact)} is between {_label(q.param)} and {_label(q.upper)}")
    elif q.form == "compare":
        parts.append(f"{fl(q.fact)} is {CMP_WORDS[q.cmp]} {_label(q.param)}")
    elif q.form == "present":
        parts.append(f"{fl(q.fact)} is required")
    elif q.form == "relation":
        tgt = f"{q.entity}{' ' + q.predef if q.predef else ''}"
        parts.append({"encloses": f"it contains at least one {tgt}", "adjacent": f"it touches {tgt}", "above": f"it is above {tgt}",
                      "distance": f"the distance to {tgt} is {CMP_WORDS.get(q.cmp or '', '')} {_label(q.param or '')}"}[q.relation])
    for c in rule.unless:
        parts.append(f"; not applied when {cond(c)}")
    for e in rule.excepts:
        if e.mode == "reviewer":
            parts.append(f"; if not met and {cond(e.condition)}, a reviewer decides")
        elif e.mode == "allow":
            parts.append(f"; if {cond(e.condition)}, {_label(e.param)} is accepted instead")
        else:
            parts.append(f"; if {cond(e.condition)}, {_label(e.param)} applies instead")
    grouped: dict[str, list[str]] = {}
    for p in rule.params:
        where = "base model" if p.layer == LAYER_BASE else p.layer
        grouped.setdefault(p.name, []).append(f"{'not yet sourced' if p.value is None else f'{p.value} {p.unit}'} ({where})")
    vals = [f"{_label(n)} {', '.join(v)}" for n, v in grouped.items()]
    text = "".join(parts) + "."
    if vals:
        text += " Values: " + "; ".join(vals) + "."
    return text


def compile_rule(doc: Document, rule: Rule, v: Vocabulary | None = None, prefix: str = UNIT_ID_PREFIX) -> dict[str, Any]:
    v = v or load()
    errors = _Checker(doc, rule, v).check()
    if errors:
        raise OriClCompileError(errors)
    kind = rule.subject[0]
    base_params = [_param_record(p) for p in rule.params if p.layer == LAYER_BASE and p.value is not None]
    layers = []
    for i, a in enumerate(rule.adopts, 1):
        ctx = doc.layers[a.layer]
        layer = {
            "layer_id": a.layer, "jurisdiction": ctx.jurisdiction, "code": ctx.code, "edition": ctx.edition,
            "effective_from": ctx.effective_from, "authority_class": ctx.authority_class, "binding": True,
            "precedence": i, "override_mode": a.mode, "mode_status": a.status,
            "amendment_ref": {"source": a.source, "item": a.item},
        }
        ps = [_param_record(p) for p in rule.params if p.layer == a.layer and p.value is not None]
        if ps:
            layer["parameters"] = ps
        layers.append(layer)
    facts = _facts_used(rule, v)
    uses_geometry = any((v.facts.get(n) or {}).get("nature") == "geometric" or n.startswith(("distance:", "above:")) for n, *_ in facts)
    check_class = "judgment" if rule.reviewer_terms else ("geometric_deterministic" if uses_geometry else "data_check")
    if rule.reviewer_terms:
        evaluator = {"kind": "human_reviewer", "implementation": None, "implementation_version": None}
    elif rule.check:
        evaluator = {"kind": "deterministic_function", "implementation": RULES_IMPL + rule.check, "implementation_version": "0.1.0"}
    else:
        evaluator = {"kind": "deterministic_function", "implementation": EVALUATOR_IMPL, "implementation_version": "0.1.0"}
    binding = any(l["binding"] for l in layers)
    text = gloss(rule, v)
    title = text.split(": ", 1)[1].split(";")[0].split(". Values")[0].rstrip(".")
    title = (title[:1].upper() + title[1:])[:120]
    sources = [doc.base["source"]] + [a.source for a in rule.adopts] + [p.source for p in rule.params]
    items = []
    for n, dt, unit, req in facts:
        f = v.facts.get(n)
        item = {"key": _input_key(kind, n), "description": (f["label"] if f else _label(n.replace(":", " ")))}
        maps = [m["name"] for m in (f or {}).get("maps_to", []) if m.get("source") in ("src:ifc-4.3", "src:ori-pset")]
        if maps:
            item["ifc_path"] = " / ".join(maps)
        items.append(item)
    unit = {
        "id": prefix + rule.rule_id,
        "type": "Requirement",
        "version": "0.1.0",
        "jurisdiction": list(dict.fromkeys(l["jurisdiction"] for l in layers)),
        "source": list(dict.fromkeys(sources)),
        "derived_from": [],
        "supersedes": [],
        "metadata": {"authority_classification": "state_adopted_code" if binding else "model_code_not_adopted", "status": "DRAFT", "generated_by": "ori-cl-0.1"},
        "rule_unit_profile": "ori-rule-unit-0.1",
        "title": title,
        "paraphrase": text,
        "source_url": rule.links[0],
        "source_links": [{"label": f"Official text ({_host(u)})", "url": u} for u in rule.links],
        "source_section": {"code": rule.cite["code"], "edition": rule.cite["edition"], "section": rule.cite["section"],
                           "chapter": int(rule.cite["section"][1]) if rule.cite["section"][1:2].isdigit() else 3,
                           **({"subsection_part": rule.cite["part"]} if rule.cite["part"] else {})},
        "authority_classification": "state_adopted_code" if binding else "model_code_not_adopted",
        "check_class": check_class,
        "classification_basis": "estimate",
        "base_model": {"code": doc.base["code"], "edition": doc.base["edition"], "publisher": doc.base["publisher"],
                       "authority_class": "model_code", "binding": False, "source": doc.base["source"],
                       "status": "present", "parameters": base_params},
        "jurisdiction_layers": layers,
        "required_information": {"ids": None, "items": items},
        "inputs": [{"name": re.sub(r"[^a-z0-9_]+", "_", n.lower()).strip("_"), "datatype": dt, **({"unit": u} if u else {}), "required": r}
                   for n, dt, u, r in facts],
        "result_states": ["unknown", "not_applicable"] if rule.reviewer_terms else ["pass", "fail", "unknown", "not_applicable"],
        "unknown_policy": {"missing_information_result": "unknown", "statement": "Missing, unreadable or unconfirmed information yields unknown, never fail."},
        "evaluator": evaluator,
        "provenance": {"recorded_by": "ORI-CL compiler 0.1 (DRAFT; generated from ORI-CL source, not human-reviewed)",
                       "recorded_at": RECORDED_AT, "sources_checked": list(dict.fromkeys([a.source for a in rule.adopts] + [p.source for p in rule.params])) or [doc.base["source"]]},
        "legal_boundary": {"machine_result_is_approval": False,
                           "statement": "Any machine result for this unit is reviewer evidence, not approval. Only the building official's decision is lawful approval."},
        "ori_cl": {
            "version": "0.1",
            "rule_id": rule.rule_id,
            "statement_sha256": hashlib.sha256(_canonical(rule).encode()).hexdigest(),
            "open_parameters": [{"name": p.name, "layer": p.layer, "comparator": p.cmp, "unit": p.unit, "value_status": p.status, "source": p.source}
                                for p in rule.params if p.value is None],
            "reviewer_terms": list(rule.reviewer_terms),
        },
    }
    if check_class == "judgment":
        unit["interpretability_link"] = {"ambiguous_terms": list(rule.reviewer_terms), "result": "reviewer_determination_required"}
    return {"unit": unit, "plan": _plan(rule, v)}


def compile_document(doc: Document, v: Vocabulary | None = None, prefix: str = UNIT_ID_PREFIX) -> list[dict[str, Any]]:
    v = v or load()
    errors: list[str] = []
    out = []
    ids = set()
    for rule in doc.rules:
        if rule.rule_id in ids:
            errors.append(f"{rule.rule_id}: duplicate rule id")
        ids.add(rule.rule_id)
        try:
            out.append(compile_rule(doc, rule, v, prefix))
        except OriClCompileError as e:
            errors += e.errors
    if errors:
        raise OriClCompileError(errors)
    return out


def compile_text(text: str, v: Vocabulary | None = None) -> list[dict[str, Any]]:
    return compile_document(syntax.parse(text), v)
