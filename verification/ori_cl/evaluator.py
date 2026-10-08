# SPDX-License-Identifier: Apache-2.0
"""Deterministic evaluator for compiled ORI-CL check plans.

``evaluate_plan(plan, unit, subject)`` returns an ``ori_verify.rules.Result``
with the same states and reason codes as the hand-written rule functions.
Evaluation order (spec/ori-cl-0.1-draft.md, section 7):

1. subject kind           -> not_applicable / subject_kind_not_applicable
2. jurisdiction deletes   -> not_applicable / deleted_by_jurisdiction
3. required parameters    -> unknown / parameter_missing
4. unless conditions      -> not_applicable / exception_applies
5. when conditions        -> not_applicable / use_not_covered | trigger_not_met
6. reviewer rules         -> unknown / reviewer_determination_required
7. require (+ except)     -> pass | fail | unknown

Missing or unconfirmed facts give unknown, never fail. Enumerated facts whose
value is outside the vocabulary give unknown / missing_information.
"""

from __future__ import annotations

from typing import Any

from ori_verify.facts import Fact, Subject
from ori_verify.rules import FAIL, NA, PASS, UNKNOWN, Result, _base, _cmp, _req
from ori_verify.units import EffectiveUnit

from .vocab import Vocabulary, load

EPS = 1e-6  # float-noise tolerance only (same value as rules.EPS_IN / EPS_FT2)
DECLARED_ORIGINS = frozenset({"applicant_declared", "applicant_confirmed", "reviewer_confirmed"})

T, F, U = True, False, None  # three-valued logic


class _Stop(Exception):
    def __init__(self, result: Result):
        self.result = result


def _present(f: Fact | None) -> bool:
    return f is not None and f.value is not None


def _missing(f: Fact | None) -> bool:
    return f is None or f.value is None or (isinstance(f.value, list) and not f.value)


class _Run:
    def __init__(self, plan: dict[str, Any], unit: EffectiveUnit, subject: Subject, vocab: Vocabulary):
        self.p, self.u, self.s, self.v = plan, unit, subject, vocab
        self.used: dict[str, Any] = {}

    def stop(self, state: str, reason: str, message: str, **kw):
        raise _Stop(_base(self.u, self.s, state, reason, message, facts_used=dict(self.used), **kw))

    def need(self, names: list[str]) -> dict[str, Fact]:
        """Like rules._need: unconfirmed beats missing; both give unknown."""
        missing, unconfirmed, out = [], [], {}
        for n in names:
            f = self.s.get(n)
            if f is not None:
                self.used[n] = f.as_record()
            if _missing(f):
                missing.append(n)
            elif not f.usable:
                unconfirmed.append(n)
            else:
                out[n] = f
        if unconfirmed:
            self.stop(UNKNOWN, "unconfirmed_extraction", f"Extracted but unconfirmed: {', '.join(unconfirmed)}; not used for pass/fail.")
        if missing:
            self.stop(UNKNOWN, "missing_information", f"Required information not available: {', '.join(missing)}.")
        return out

    def value(self, name: str) -> Any:
        f = self.need([name])[name]
        vals = self.v.enum_values(name)
        if vals is not None and f.value not in vals:
            self.stop(UNKNOWN, "missing_information", f"{name} value {f.value!r} is not an ORI-CL vocabulary value.")
        return f.value

    def param(self, name: str) -> dict[str, Any]:
        return _req(self.u, name)

    # conditions (three-valued) ----------------------------------------------------------------
    def soft(self, name: str) -> tuple[Any, str | None]:
        """Value of a condition fact without stopping: (value, None) or (None, reason)."""
        f = self.s.get(name)
        if f is not None:
            self.used[name] = f.as_record()
        if _missing(f):
            return None, "missing_information"
        if not f.usable:
            return None, "unconfirmed_extraction"
        vals = self.v.enum_values(name)
        if vals is not None and f.value not in vals:
            return None, "missing_information"
        return f.value, None

    def atom(self, a: dict[str, Any]) -> tuple[bool | None, str | None]:
        val, why = self.soft(a["fact"])
        if why:
            return U, why
        k = a["kind"]
        if k == "is":
            res = val == a["value"]
            return (not res if a.get("negated") else res), None
        if k == "in":
            return val in a["values"], None
        if k == "rel":
            return (val > 0 if isinstance(val, (int, float)) and not isinstance(val, bool) else bool(val)), None
        req = self.param(a["param"])
        return _cmp(float(val), a["cmp"], req["value"], EPS), None

    def cond(self, c: dict[str, Any]) -> tuple[bool | None, str | None]:
        results = [self.atom(a) for a in c["atoms"]]
        vals = [r for r, _ in results]
        reasons = [w for _, w in results if w]
        if c["op"] == "and":
            if F in vals:
                return F, None
            if U in vals:
                return U, ("unconfirmed_extraction" if "unconfirmed_extraction" in reasons else "missing_information")
            return T, None
        if T in vals:
            return T, None
        if U in vals:
            return U, ("unconfirmed_extraction" if "unconfirmed_extraction" in reasons else "missing_information")
        return F, None

    def hard_cond(self, c: dict[str, Any]) -> bool:
        """Condition that must be known to continue (unless/when)."""
        # Enumerated facts in the condition are read strictly: unconfirmed/missing stop the run,
        # an out-of-vocabulary value stops with missing_information.
        for a in c["atoms"]:
            self.value(a["fact"])
        res, _ = self.cond(c)
        return bool(res)

    # main --------------------------------------------------------------------------------
    def run(self) -> Result:
        p, u, s = self.p, self.u, self.s
        if s.kind != p["subject"]:
            self.stop(NA, "subject_kind_not_applicable", f"Applies to {p['subject']} subjects only.")
        if u.deleted:
            self.stop(NA, "deleted_by_jurisdiction", "The jurisdiction layer deletes this provision.")
        for name in p["params_required"]:
            if u.param(name) is None:
                self.stop(UNKNOWN, "parameter_missing", f"Rule-unit parameter {name} is not defined (or not yet sourced) for this jurisdiction.")
        for c in p["unless"]:
            if self.hard_cond(c):
                self.stop(NA, "exception_applies", "An exclusion in this rule applies to the subject.")
        for c in p["when"]:
            if not self.hard_cond(c):
                trigger = any(a["kind"] in ("cmp", "rel") for a in c["atoms"])
                self.stop(NA, "trigger_not_met" if trigger else "use_not_covered", "The rule's applicability condition is not met.")
        if p["reviewer_terms"]:
            self.stop(UNKNOWN, "reviewer_determination_required",
                      "Reviewer determination required; ambiguous terms: " + "; ".join(p["reviewer_terms"]) + ".")
        q = p["require"]
        form = q["form"]
        if form in ("each", "spread"):
            return self.list_form(q)
        if form == "present":
            return self.present(q["fact"], declared_absence_fails=True)
        if form == "relation" and q["relation"] in ("encloses", "adjacent", "above"):
            return self.relation(q)
        if form == "between":
            v = float(self.need([q["fact"]])[q["fact"]].value)
            lo, hi = self.param(q["param"]), self.param(q["upper"])
            kw = dict(measured={q["fact"]: v}, required=[lo, hi])
            if _cmp(v, ">=", lo["value"], EPS) and _cmp(v, "<=", hi["value"], EPS):
                self.stop(PASS, "threshold_met", f"{q['fact']} {v} within [{lo['value']}, {hi['value']}].", **kw)
            self.stop(FAIL, "threshold_not_met", f"{q['fact']} {v} outside [{lo['value']}, {hi['value']}].", **kw)
        return self.compare(q)

    def list_form(self, q: dict[str, Any]) -> Result:
        name = q["fact"]
        f = self.s.get(name)
        req = self.param(q["param"])
        if q.get("empty_absent") and f is not None and f.usable and f.value == []:
            self.used[name] = f.as_record()
            self.stop(UNKNOWN, "required_element_not_found", f"No element found to measure {name}; absence in the model is not evidence.")
        values = [float(x) for x in self.need([name])[name].value]
        if q["form"] == "spread":
            if len(values) < 2:
                self.stop(NA, "single_value", f"Fewer than two {name}; spread does not arise.", measured={name: values}, required=[req])
            spread = max(values) - min(values)
            kw = dict(measured={name: values, "spread": spread}, required=[req])
            if _cmp(spread, q["cmp"], req["value"], EPS):
                self.stop(PASS, "threshold_met", f"Spread {spread:.3f} {req['unit']} is {q['cmp']} {req['value']}.", **kw)
            self.stop(FAIL, "threshold_not_met", f"Spread {spread:.3f} {req['unit']} is not {q['cmp']} {req['value']}.", **kw)
        bad = [i for i, x in enumerate(values) if not _cmp(x, q["cmp"], req["value"], EPS)]
        kw = dict(measured={name: values, "offending_indices": bad}, required=[req])
        if bad:
            self.stop(FAIL, "threshold_not_met", f"{len(bad)} of {len(values)} {name} values are not {q['cmp']} {req['value']} {req['unit']}.", **kw)
        self.stop(PASS, "threshold_met", f"All {len(values)} {name} values are {q['cmp']} {req['value']} {req['unit']}.", **kw)

    def present(self, name: str, declared_absence_fails: bool) -> Result:
        f = self.s.get(name)
        if f is not None:
            self.used[name] = f.as_record()
        if not _present(f) or not f.usable:
            self.stop(UNKNOWN, "required_element_not_found", f"{name}: required element could not be identified; absence in the model is not evidence of absence.")
        if f.value:
            self.stop(PASS, "requirement_met", f"{name} is established.")
        self.stop(FAIL, "requirement_not_met", f"The evidence declares {name} is not met.")

    def relation(self, q: dict[str, Any]) -> Result:
        name = q["fact"]
        f = self.s.get(name)
        if f is not None:
            self.used[name] = f.as_record()
        if not _present(f) or not f.usable:
            self.stop(UNKNOWN, "required_element_not_found", f"{name}: relationship not established from usable evidence.")
        v = f.value
        ok = v > 0 if isinstance(v, (int, float)) and not isinstance(v, bool) else bool(v)
        if ok:
            self.stop(PASS, "requirement_met", f"{name} holds ({v}).", measured={name: v})
        # A model that simply lacks the element is not evidence of absence; only a declared
        # or confirmed statement of absence can fail.
        if f.origin in DECLARED_ORIGINS:
            self.stop(FAIL, "requirement_not_met", f"{name}: declared evidence shows the relationship does not hold.", measured={name: v})
        self.stop(UNKNOWN, "required_element_not_found", f"{name}: not found in the model; absence in a model is not evidence of absence.", measured={name: v})

    def quantity(self, q: dict[str, Any]) -> float:
        name = q["fact"]
        d = self.p.get("derive")
        if d and d["target"] == name and not _present(self.s.get(name)):
            fs = self.need([d["a"], d["b"]])
            return float(fs[d["a"]].value) * float(fs[d["b"]].value) * d["num"] / d["den"]
        if q.get("bound") and not _present(self.s.get(name)):
            b = q["bound"]
            bv = float(self.need([b])[b].value)
            req = self.param(q["param"])
            kw = dict(measured={b: bv}, required=[req])
            # the bound is the best case for the quantity: failing it means the quantity fails too
            if not _cmp(bv, q["cmp"], req["value"], EPS):
                self.stop(FAIL, "threshold_not_met", f"Bound {b} {bv:.2f} already fails {q['cmp']} {req['value']}; {name} can only be worse.", **kw)
            self.stop(UNKNOWN, "missing_information", f"Bound {b} {bv:.2f} meets the limit, but {name} itself is not established.", **kw)
        return float(self.need([name])[name].value)

    def compare(self, q: dict[str, Any]) -> Result:
        name = q["fact"]  # a plain fact, or a distance:<IfcEntity> relation fact
        val = self.quantity(q)
        main = self.param(q["param"])
        excepts = [e for e in self.p["excepts"] if not (e["mode"] == "use" and e["optional"] and self.u.param(e["param"]) is None)]
        # 'use' with a known-true condition replaces the requirement before it is tested
        for e in excepts:
            if e["mode"] == "use":
                known, _ = self.cond(e["when"])
                if known is T:
                    alt = self.param(e["param"])
                    kw = dict(measured={name: val}, required=[alt])
                    if _cmp(val, q["cmp"], alt["value"], EPS):
                        self.stop(PASS, "threshold_met", f"{name} {val:.2f} meets the alternative {alt['value']} {alt['unit']}.", **kw)
                    self.stop(FAIL, "threshold_not_met", f"{name} {val:.2f} fails the alternative {alt['value']} {alt['unit']}.", **kw)
        kw = dict(measured={name: round(val, 6)}, required=[main])
        if _cmp(val, q["cmp"], main["value"], EPS):
            self.stop(PASS, "threshold_met", f"{name} {val:.2f} is {q['cmp']} {main['value']} {main['unit']}.", **kw)
        for e in excepts:
            known, why = self.cond(e["when"])
            if e["mode"] == "reviewer":
                if known is U:
                    self.stop(UNKNOWN, why, f"{name} {val:.2f} fails {main['value']}, and whether the exception applies is not established.", **kw)
                if known is T:
                    self.stop(UNKNOWN, "exception_requires_reviewer", f"{name} {val:.2f} fails {main['value']}; an exception needing reviewer judgment applies.", **kw)
                continue
            alt = self.param(e["param"])
            kw2 = dict(measured={name: round(val, 6)}, required=[main, alt])
            if not _cmp(val, q["cmp"], alt["value"], EPS):
                if e["mode"] == "allow":
                    self.stop(FAIL, "threshold_not_met", f"{name} {val:.2f} fails both {main['value']} and {alt['value']}.", **kw2)
                continue
            if known is U:
                self.stop(UNKNOWN, why, f"{name} {val:.2f} meets only the exception value {alt['value']}; the exception condition is not established.", **kw2)
            if known is T:  # only 'allow' reaches here with T ('use' + T returned above)
                self.stop(PASS, "threshold_met_exception", f"{name} {val:.2f} meets the exception value {alt['value']}.", **kw2)
        self.stop(FAIL, "threshold_not_met", f"{name} {val:.2f} is not {q['cmp']} {main['value']} {main['unit']}.", **kw)


def evaluate_plan(plan: dict[str, Any], unit: EffectiveUnit, subject: Subject, vocab: Vocabulary | None = None) -> Result:
    try:
        _Run(plan, unit, subject, vocab or load()).run()
    except _Stop as s:
        return s.result
    raise AssertionError("evaluator ended without a result")  # every path above stops


def evaluate(compiled: list[dict[str, Any]], subjects: list[Subject], jurisdiction: str | None) -> list[Result]:
    """Run every compiled rule against every subject of its kind (like rules.evaluate)."""
    from ori_verify.units import resolve
    out = []
    for c in compiled:
        eff = resolve(c["unit"], jurisdiction)
        for s in subjects:
            if s.kind == c["plan"]["subject"]:
                out.append(evaluate_plan(c["plan"], eff, s))
    return out
