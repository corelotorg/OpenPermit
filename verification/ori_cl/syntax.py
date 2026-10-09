# SPDX-License-Identifier: Apache-2.0
"""ORI-CL tokenizer and parser (grammar: spec/ori-cl-0.1.ebnf).

ORI-CL is line oriented. Every line starts with a keyword that fixes its
clause form, so the grammar is LL(1) and every statement has one parse.
Blank lines and ``#`` comments are ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

CMPS = ("<=", ">=", "<", ">", "=")
_TOKEN = re.compile(r'\s*(?:(?P<str>"[^"\n]*")|(?P<cmp><=|>=|<|>|=)|(?P<lb>\[)|(?P<rb>\])|(?P<word>[^\s"\[\]<>=]+))')
_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")
IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
RULE_ID = re.compile(r"^R[0-9]{3}(?:\.[0-9]+)*:[a-z0-9][a-z0-9\-]*$")
IFC_NAME = re.compile(r"^Ifc[A-Z][A-Za-z]+$")
PREDEF = re.compile(r"^[A-Z][A-Z_]+$")
SECTION = re.compile(r"^R[0-9]{3}(?:\.[0-9]+)*$")
MODES = ("adopts_base", "replaces_value", "modifies_text", "adds_exception", "deletes", "adds_section", "replaces_section")
STATUSES = ("sourced_primary", "sourced_secondary", "inferred_unamended", "estimate")
RELATIONS = ("encloses", "adjacent", "above", "distance")


class OriClSyntaxError(ValueError):
    def __init__(self, line: int, msg: str):
        super().__init__(f"line {line}: {msg}")
        self.line = line


@dataclass
class Tok:
    kind: str  # str | cmp | lb | rb | word | num
    text: str

    @property
    def value(self) -> Any:
        if self.kind == "str":
            return self.text[1:-1]
        if self.kind == "num":
            v = float(self.text)
            return int(v) if v.is_integer() and "." not in self.text else v
        return self.text


def tokenize(line: str, n: int) -> list[Tok]:
    # strip a comment that is not inside a string
    out, i, instr = [], 0, False
    for i, ch in enumerate(line):
        if ch == '"':
            instr = not instr
        if ch == "#" and not instr:
            line = line[:i]
            break
    toks: list[Tok] = []
    pos = 0
    line = line.rstrip()
    while pos < len(line):
        m = _TOKEN.match(line, pos)
        if not m or m.end() == pos:
            raise OriClSyntaxError(n, f"cannot read text at column {pos + 1}")
        pos = m.end()
        kind = m.lastgroup
        text = m.group(kind)
        if kind == "word" and _NUMBER.match(text):
            kind = "num"
        toks.append(Tok(kind, text))
    return toks


# ---- AST -------------------------------------------------------------------------------
@dataclass
class Atom:
    kind: str  # is | in | cmp | rel
    fact: str | None = None
    negated: bool = False
    value: Any = None  # literal for 'is'; list for 'in'
    cmp: str | None = None
    param: str | None = None
    relation: str | None = None
    entity: str | None = None
    predef: str | None = None


@dataclass
class Condition:
    op: str | None  # and | or | None (single atom)
    atoms: list[Atom]


@dataclass
class Param:
    name: str
    cmp: str
    value: float | int | None  # None = open (not yet sourced)
    unit: str
    layer: str
    status: str
    source: str
    locator: str | None = None
    applies_when: tuple[str, Any] | None = None
    line: int = 0


@dataclass
class Requirement:
    form: str  # each | spread | between | compare | present | relation
    fact: str | None = None
    cmp: str | None = None
    param: str | None = None
    upper: str | None = None
    empty_absent: bool = False
    bound: str | None = None
    relation: str | None = None
    entity: str | None = None
    predef: str | None = None


@dataclass
class Exception_:
    condition: Condition
    mode: str  # allow | use | reviewer
    param: str | None = None
    optional: bool = False


@dataclass
class Measure:
    fact: str
    start: str
    end: str
    along: str | None = None
    within: str | None = None


@dataclass
class Adopt:
    layer: str
    mode: str
    status: str
    source: str
    item: str | None = None


@dataclass
class Rule:
    rule_id: str
    line: int
    cite: dict[str, Any] | None = None
    adopts: list[Adopt] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    subject: tuple[str, str, str | None] | None = None  # kind, IFC entity, predefined type
    measures: list[Measure] = field(default_factory=list)
    params: list[Param] = field(default_factory=list)
    check: str | None = None
    derive: tuple[str, str, str] | None = None  # target, a, b
    when: list[Condition] = field(default_factory=list)
    unless: list[Condition] = field(default_factory=list)
    require: Requirement | None = None
    excepts: list[Exception_] = field(default_factory=list)
    reviewer_terms: list[str] = field(default_factory=list)


@dataclass
class LayerContext:
    layer_id: str
    jurisdiction: str
    code: str
    edition: str
    effective_from: str
    authority_class: str


@dataclass
class Document:
    base: dict[str, str] | None
    layers: dict[str, LayerContext]
    rules: list[Rule]


# ---- parser ----------------------------------------------------------------------------
class _Line:
    def __init__(self, toks: list[Tok], n: int):
        self.t, self.i, self.n = toks, 0, n

    def peek(self, k: int = 0) -> Tok | None:
        j = self.i + k
        return self.t[j] if j < len(self.t) else None

    def more(self) -> bool:
        return self.i < len(self.t)

    def take(self, kind: str | None = None, text: str | None = None, what: str = "") -> Tok:
        tok = self.peek()
        if tok is None:
            raise OriClSyntaxError(self.n, f"expected {what or text or kind}, found end of line")
        if (kind and tok.kind != kind) or (text and tok.text != text):
            raise OriClSyntaxError(self.n, f"expected {what or text or kind}, found {tok.text!r}")
        self.i += 1
        return tok

    def accept(self, text: str) -> bool:
        tok = self.peek()
        if tok is not None and tok.kind == "word" and tok.text == text:
            self.i += 1
            return True
        return False

    def word(self, what: str, pattern: re.Pattern | None = None) -> str:
        tok = self.take("word", what=what)
        if pattern and not pattern.match(tok.text):
            raise OriClSyntaxError(self.n, f"{what} {tok.text!r} is not well formed")
        return tok.text

    def ident(self, what: str) -> str:
        return self.word(what, IDENT)

    def done(self):
        if self.more():
            raise OriClSyntaxError(self.n, f"unexpected {self.peek().text!r}")


def _literal(ln: _Line) -> Any:
    tok = ln.take(what="value")
    if tok.kind == "word" and tok.text in ("true", "false"):
        return tok.text == "true"
    if tok.kind == "num":
        return tok.value
    if tok.kind == "word" and IDENT.match(tok.text):
        return tok.text
    raise OriClSyntaxError(ln.n, f"bad value {tok.text!r}")


def _relation_target(ln: _Line) -> tuple[str, str | None]:
    entity = ln.word("IFC entity", IFC_NAME)
    tok = ln.peek()
    predef = None
    if tok is not None and tok.kind == "word" and PREDEF.match(tok.text):
        predef = ln.take().text
    return entity, predef


def _atom(ln: _Line) -> Atom:
    tok = ln.peek()
    if tok is not None and tok.kind == "word" and tok.text in RELATIONS:
        rel = ln.take().text
        entity, predef = _relation_target(ln)
        if rel == "distance":
            cmp = ln.take("cmp", what="comparator").text
            return Atom("rel", relation=rel, entity=entity, predef=predef, cmp=cmp, param=ln.ident("parameter"))
        return Atom("rel", relation=rel, entity=entity, predef=predef)
    fact = ln.ident("fact")
    if ln.accept("is"):
        neg = ln.accept("not")
        return Atom("is", fact=fact, negated=neg, value=_literal(ln))
    if ln.accept("in"):
        ln.take("lb", what="[")
        vals = []
        while ln.peek() is not None and ln.peek().kind != "rb":
            vals.append(_literal(ln))
        ln.take("rb", what="]")
        if not vals:
            raise OriClSyntaxError(ln.n, "empty set")
        return Atom("in", fact=fact, value=vals)
    tok = ln.peek()
    if tok is not None and tok.kind == "cmp":
        cmp = ln.take().text
        return Atom("cmp", fact=fact, cmp=cmp, param=ln.ident("parameter"))
    raise OriClSyntaxError(ln.n, f"expected 'is', 'in' or a comparator after {fact!r}")


def _condition(ln: _Line, stop: tuple[str, ...] = ()) -> Condition:
    atoms = [_atom(ln)]
    op = None
    while ln.more():
        tok = ln.peek()
        if tok.kind == "word" and tok.text in stop:
            break
        if tok.kind == "word" and tok.text in ("and", "or"):
            if op is not None and tok.text != op:
                raise OriClSyntaxError(ln.n, "mixing 'and' with 'or' in one condition is not allowed; split into separate when lines")
            op = ln.take().text
            atoms.append(_atom(ln))
            continue
        raise OriClSyntaxError(ln.n, f"unexpected {tok.text!r} in condition")
    return Condition(op, atoms)


def _require(ln: _Line) -> Requirement:
    tok = ln.peek()
    if tok is None:
        raise OriClSyntaxError(ln.n, "empty requirement")
    if tok.kind == "word" and tok.text == "each":
        ln.take()
        fact = ln.ident("fact")
        cmp = ln.take("cmp", what="comparator").text
        param = ln.ident("parameter")
        empty = False
        if ln.accept("empty"):
            ln.take("word", "absent")
            empty = True
        ln.done()
        return Requirement("each", fact=fact, cmp=cmp, param=param, empty_absent=empty)
    if tok.kind == "word" and tok.text == "spread":
        ln.take()
        fact = ln.ident("fact")
        cmp = ln.take("cmp", what="comparator").text
        param = ln.ident("parameter")
        ln.done()
        return Requirement("spread", fact=fact, cmp=cmp, param=param)
    if tok.kind == "word" and tok.text in RELATIONS:
        a = _atom(ln)
        ln.done()
        return Requirement("relation", relation=a.relation, entity=a.entity, predef=a.predef, cmp=a.cmp, param=a.param)
    fact = ln.ident("fact")
    if ln.accept("present"):
        ln.done()
        return Requirement("present", fact=fact)
    if ln.accept("between"):
        lo = ln.ident("parameter")
        ln.take("word", "and")
        hi = ln.ident("parameter")
        ln.done()
        return Requirement("between", fact=fact, param=lo, upper=hi)
    cmp = ln.take("cmp", what="comparator").text
    param = ln.ident("parameter")
    bound = None
    if ln.accept("bound"):
        bound = ln.ident("fact")
    ln.done()
    return Requirement("compare", fact=fact, cmp=cmp, param=param, bound=bound)


def parse(text: str) -> Document:
    base: dict[str, str] | None = None
    layers: dict[str, LayerContext] = {}
    rules: list[Rule] = []
    cur: Rule | None = None
    for n, raw in enumerate(text.splitlines(), 1):
        toks = tokenize(raw, n)
        if not toks:
            continue
        ln = _Line(toks, n)
        head = ln.take("word", what="keyword").text
        if cur is None:
            if head == "context":
                what = ln.take("word").text
                if what == "base":
                    code = ln.word("code")
                    edition = ln.take("num", what="edition").text
                    ln.take("word", "by")
                    base = {"code": code, "edition": edition, "source": ln.word("source")}
                    ln.take("word", "publisher")
                    base["publisher"] = ln.take("str", what="publisher").value
                    ln.done()
                elif what == "layer":
                    lid = ln.word("layer id")
                    ln.take("word", "for")
                    jur = ln.word("jurisdiction")
                    ln.take("word", "code")
                    code = ln.word("code")
                    edition = ln.take("num", what="edition").text
                    ln.take("word", "from")
                    eff = ln.word("date", re.compile(r"^\d{4}-\d{2}-\d{2}$"))
                    ln.take("word", "class")
                    cls = ln.word("authority class", re.compile(r"^(state_adopted_code|local_adopted_amendment)$"))
                    ln.done()
                    layers[lid] = LayerContext(lid, jur, code, edition, eff, cls)
                else:
                    raise OriClSyntaxError(n, "context must be 'base' or 'layer'")
                continue
            if head != "rule":
                raise OriClSyntaxError(n, f"expected 'rule' or 'context', found {head!r}")
            cur = Rule(rule_id=ln.word("rule id", RULE_ID), line=n)
            ln.done()
            continue
        if head == "rule":
            raise OriClSyntaxError(n, "rule blocks cannot nest; close the previous rule with 'end'")
        if head == "end":
            ln.done()
            rules.append(cur)
            cur = None
            continue
        if head == "cite":
            code = ln.word("code")
            edition = ln.take("num", what="edition").text
            section = ln.word("section", SECTION)
            part = ln.take("str", what="part name").value if ln.accept("part") else None
            ln.done()
            if cur.cite:
                raise OriClSyntaxError(n, "one cite per rule")
            cur.cite = {"code": code, "edition": edition, "section": section, "part": part}
        elif head == "adopt":
            lid = ln.word("layer id")
            ln.take("word", "mode")
            mode = ln.word("mode")
            if mode not in MODES:
                raise OriClSyntaxError(n, f"unknown mode {mode!r}")
            ln.take("word", "status")
            status = ln.word("status")
            if status not in STATUSES:
                raise OriClSyntaxError(n, f"unknown status {status!r}")
            ln.take("word", "by")
            src = ln.word("source")
            item = ln.take("str", what="item").value if ln.accept("item") else None
            ln.done()
            cur.adopts.append(Adopt(lid, mode, status, src, item))
        elif head == "link":
            cur.links.append(ln.word("url", re.compile(r"^https://\S+$")))
            ln.done()
        elif head == "subject":
            kind = ln.ident("subject kind")
            ln.take("word", "is")
            entity, predef = _relation_target(ln)
            ln.done()
            cur.subject = (kind, entity, predef)
        elif head == "measure":
            fact = ln.ident("fact")
            ln.take("word", "from")
            start = ln.ident("reference geometry")
            ln.take("word", "to")
            end = ln.ident("reference geometry")
            along = ln.ident("reference geometry") if ln.accept("along") else None
            within = ln.ident("parameter") if ln.accept("within") else None
            ln.done()
            cur.measures.append(Measure(fact, start, end, along, within))
        elif head == "param":
            name = ln.ident("parameter")
            cmp = ln.take("cmp", what="comparator").text
            if ln.accept("open"):
                value = None
            else:
                value = ln.take("num", what="number or 'open'").value
            unit = ln.word("unit")
            ln.take("word", "at")
            layer = ln.word("layer")
            ln.take("word", "status")
            status = ln.word("status")
            if status not in STATUSES:
                raise OriClSyntaxError(n, f"unknown status {status!r}")
            ln.take("word", "source")
            src = ln.word("source")
            locator = ln.take("str", what="locator").value if ln.accept("locator") else None
            applies = None
            if ln.accept("when"):
                f = ln.ident("fact")
                ln.take("word", "is")
                applies = (f, _literal(ln))
            ln.done()
            cur.params.append(Param(name, cmp, value, unit, layer, status, src, locator, applies, n))
        elif head == "check":
            cur.check = ln.ident("check function")
            ln.done()
        elif head == "derive":
            target = ln.ident("fact")
            ln.take("word", "is")
            a = ln.ident("fact")
            ln.take("word", "times")
            b = ln.ident("fact")
            ln.done()
            cur.derive = (target, a, b)
        elif head == "when":
            cur.when.append(_condition(ln))
        elif head == "unless":
            cur.unless.append(_condition(ln))
        elif head == "require":
            if cur.require is not None:
                raise OriClSyntaxError(n, "one require per rule (one rule unit states one requirement)")
            cur.require = _require(ln)
        elif head == "except":
            ln.take("word", "when")
            cond = _condition(ln, stop=("allow", "use", "reviewer"))
            mode = ln.take("word", what="allow, use or reviewer").text
            if mode not in ("allow", "use", "reviewer"):
                raise OriClSyntaxError(n, f"unknown exception mode {mode!r}")
            param = ln.ident("parameter") if mode in ("allow", "use") else None
            optional = ln.accept("optional") if mode == "use" else False
            ln.done()
            cur.excepts.append(Exception_(cond, mode, param, optional))
        elif head == "reviewer":
            ln.take("word", "terms")
            terms = []
            while ln.more():
                terms.append(ln.take("str", what="quoted term").value)
            if not terms:
                raise OriClSyntaxError(n, "reviewer terms needs at least one quoted term")
            cur.reviewer_terms = terms
        else:
            raise OriClSyntaxError(n, f"unknown keyword {head!r}")
    if cur is not None:
        raise OriClSyntaxError(cur.line, f"rule {cur.rule_id} is not closed with 'end'")
    return Document(base, layers, rules)


# Every word the parser treats as a keyword. Must equal the vocabulary's keyword list.
PARSER_KEYWORDS = frozenset(
    """rule end context base layer code for publisher from class cite part adopt mode status by item link
    subject is measure to along within param at source locator open check derive times when unless require
    each spread between and or not in present empty absent bound except allow use optional reviewer terms
    encloses adjacent above distance true false""".split()
)
