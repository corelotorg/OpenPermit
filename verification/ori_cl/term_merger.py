# SPDX-License-Identifier: Apache-2.0
"""Term merger study (DRAFT): which ORI-CL words are free names and which are code expression.

Analysis to inform counsel, not a legal conclusion. Method: docs/TERM-MERGER-METHOD-DRAFT.md.

Every ORI-CL vocabulary term and every clause of every generated paraphrase is put in one of
three categories:

* ``a``: an ordinary name for a physical thing, a property of one, a unit or a plain English
  word. It is free to use. Evidence: general dictionary (WordNet), open corpora, IFC/QUDT/NIST
  names.
* ``b``: a technical term with essentially one practical expression. Use it with a citation,
  e.g. "defined at IRC R202, as adopted by VRC", or the IFC 4.3 identifier with attribution.
* ``c``: a phrasing with many plausible alternatives. Where the same wording occurs in the code
  text, ORI must re-express it (``flag: re-express``). Where it does not, it is already ORI's own
  expression.

Signals (all numbers; see ``SIGNALS``): occurrences of the term in local code copies, n-gram
runs shared with them, semantic similarity (sentence-transformers all-MiniLM-L6-v2 when
installed, else a lexical WordNet/character-trigram measure; the output records which),
count of plausible alternative phrasings, and occurrence in open non-ICC corpora.

The code copies are read locally and never written. Output holds only counts, section ids,
SHA-256 digests, and ORI's own words (vocabulary terms, paraphrase clauses, WordNet-derived
alternatives). The enforced safeguard is STRICT: any run of 6 or more words shared with the code
copies fails (``corpus_stats.assert_no_text``, ``assert_output_clean``, ``scan`` exit status) and
marks a term or clause ``re-express``. ``shared_runs(..., free_terms)`` also classifies each run
the refined way (a run made only of category (a)/(b) terms, numbers, units and function words is
not flagged unless it reaches the arrangement limit); that is an informational report only and
never a gate.

Usage (from verification/):
  python -m ori_cl.term_merger classify --code-text CH2.txt CH3.txt --out FILE.json
  python -m ori_cl.term_merger scan PATH [PATH ...] --code-text CH2.txt CH3.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol

from .vocab import REPO_ROOT, load
from . import corpus_license
from .corpus_license import CorpusLicenseError

RESULTS_PATH = REPO_ROOT / "research" / "data" / "ori-cl-term-merger-DRAFT.json"
OPEN_CORPUS_CACHE = REPO_ROOT / "research" / "data" / "ori-cl-term-open-corpus-counts-DRAFT.json"
CORPORA_MANIFEST = REPO_ROOT / "research" / "data" / "ori-cl-open-corpora-DRAFT.json"
CORPUS_CLASSES = ("public_domain", "open_license", "locality")  # locality: cite-and-link, never strong evidence
COMPILED_GLOB = "rules/**/ori-cl/*.compiled.json"

MIN_RUN = 6            # the safeguard's run length (unchanged from corpus_stats)
ARRANGEMENT_RUN = 12   # a shared run this long is flagged even if every word is free (selection/order)
WATCH_RUN = 4          # paraphrase clauses sharing a 4-5 word run with non-free words go on a watch list
A_MAX = 2              # at most this many plausible alternatives: essentially one practical expression
PLAUSIBLE_SIM = {"embedding": 0.72, "lexical": 0.80}
MIN_ZIPF = 3.0         # an alternative's words must be common English (wordfreq Zipf >= 3) when wordfreq is present
WORD_SIM_FLOOR = 0.5   # embedding backend: a substituted word must itself be similar to the word it replaces
WIKI_MIN = 25          # Wikipedia exact-phrase hits that count as ordinary usage outside the code
ABBREVIATIONS = frozenset("min max pv ic ft in mm".split())  # never substituted

# Closed-class English words. Modals, negation and comparison words are deliberately absent:
# they carry the code's normative structure and must never make a run look harmless.
FUNCTION_WORDS = frozenset("""
a an the this that these those it its each every any all both either neither some
of in on at to from by for with within without into onto over under above below between among
along across through per via as than and or nor but if then where when which who whom whose
is are be been being was were has have had
""".split())
NORMATIVE = frozenset("""
shall must may should not no exceed exceeding less more least most minimum maximum required permitted
prohibited comply complying unless except provided approved
""".split())
CLAUSE_MARKERS = frozenset("""
is are be where when unless if not or than shall must may
""".split())
# Names of public bodies and laws are names, not expression; they are always free.
OFFICIAL_NAMES = (
    "Virginia Uniform Statewide Building Code", "Uniform Statewide Building Code", "Virginia Residential Code",
    "Virginia Construction Code", "International Residential Code", "International Code Council",
    "Virginia DHCD", "State Building Code Technical Review Board",
    "Virginia Administrative Code", "Code of Virginia", "Virginia",
    "Coastal A Zone",  # FEMA flood-zone designation
)
UNIT_WORDS = frozenset("in inch inches ft foot feet mm m metre metres meter meters in2 ft2 m2 square deg degree degrees percent ratio count".split())

SIGNALS = {
    "code_occurrences": "times the term (or its plural) occurs in the local code copies; section ids where it occurs",
    "longest_shared_run": "longest word run shared with the code copies (paraphrase clauses)",
    "strict_shared_run": "a run of >= 6 words shared with the code copies: the enforced rule; any such run means re-express",
    "refined_run_flag_info": "informational only, never a gate: shared_runs() refined verdict (a run of >= 6 words with a non-free word, or >= 12 words of any kind)",
    "semantic_backend": "embedding (sentence-transformers all-MiniLM-L6-v2) or lexical (WordNet Wu-Palmer / character trigrams)",
    "plausible_alternatives": "WordNet synonym substitutions whose similarity to the term is at or above the threshold",
    "open_corpus": "WordNet lemma, lexicon corpus count (none since the Brown Corpus was excluded), Wikipedia exact-phrase hit count (cached), IFC/QUDT/NIST name, licensed evidence corpora",
    "open_corpus_hits": "phrase counts in the public-domain, open-license and locality corpora of research/data/ori-cl-open-corpora-DRAFT.json; only public-domain/open sources count as strong evidence",
    "unconfirmed_license_hits": "phrase hits in public-domain-class sources whose licence basis is not confirmed (for example contractor-prepared or reprinted third-party parts); reported, never strong evidence",
    "nearest_code_similarity": "highest semantic similarity between a paraphrase clause and any code sentence, with its section id",
}

_WORD = re.compile(r"[a-z0-9]+(?:[.'-][a-z0-9]+)*")


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def sha(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


def _is_number(tok: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)*", tok))


def _plural_forms(toks: tuple[str, ...]) -> set[tuple[str, ...]]:
    last = toks[-1]
    forms = {toks, toks[:-1] + (last + "s",), toks[:-1] + (last + "es",)}
    if last.endswith("s"):
        forms.add(toks[:-1] + (last[:-1],))
    return forms


# ---- backends ----------------------------------------------------------------------------------
class Lexicon(Protocol):
    name: str
    def known(self, word: str) -> bool: ...
    def lemma(self, phrase: str) -> bool: ...
    def physical(self, phrase: str) -> bool: ...
    def synonyms(self, phrase: str) -> set[str]: ...
    def corpus_count(self, phrase: str) -> int: ...
    def common(self, word: str) -> bool: ...


class Similarity(Protocol):
    name: str
    def sim(self, a: str, b: str) -> float: ...
    def nearest(self, query: str, candidates: list[str]) -> tuple[int, float]: ...


class DictLexicon:
    """Small in-memory lexicon (tests and fallback). ``entries``: word or phrase -> synonyms."""

    name = "dict"

    def __init__(self, entries: dict[str, Iterable[str]] | None = None, physical: Iterable[str] = (), corpus: str = ""):
        self.entries = {k.lower(): set(v) for k, v in (entries or {}).items()}
        self._physical = {p.lower() for p in physical}
        self._corpus = Counter()
        w = words(corpus)
        for n in (1, 2, 3, 4):
            self._corpus.update(tuple(w[i:i + n]) for i in range(len(w) - n + 1))

    def known(self, word): return word.lower() in self.entries
    def lemma(self, phrase): return phrase.lower() in self.entries
    def physical(self, phrase): return phrase.lower() in self._physical
    def synonyms(self, phrase): return set(self.entries.get(phrase.lower(), ()))
    def corpus_count(self, phrase): return sum(self._corpus[f] for f in _plural_forms(tuple(words(phrase)))) if words(phrase) else 0
    def common(self, word): return True  # no frequency data: every listed synonym counts


class WordNetLexicon:
    """WordNet 3.0 through nltk and wordfreq for commonness. The Brown Corpus is not used
    (excluded 2026-09-28: conflicting non-commercial statement); phrase counts come from the
    licensed evidence corpora instead."""

    name = "wordnet+wordfreq"

    def __init__(self):
        from nltk.corpus import wordnet as wn  # optional dependency
        self.wn = wn
        self._physical_root = wn.synset("physical_entity.n.01")
        self._attr_roots = {wn.synset("attribute.n.02"), wn.synset("measure.n.02")}
        try:
            from wordfreq import zipf_frequency
            self._zipf = lambda t: zipf_frequency(t, "en")
        except ImportError:  # pragma: no cover
            self._zipf = None

    def _syn(self, phrase, pos=None):
        return self.wn.synsets(phrase.strip().lower().replace(" ", "_"), pos=pos)

    def known(self, word):
        return bool(self._syn(word)) or (self._zipf is not None and self._zipf(word) >= MIN_ZIPF)

    def lemma(self, phrase):
        return bool(self._syn(phrase, self.wn.NOUN)) if " " in phrase.strip() or "-" in phrase else bool(self._syn(phrase))

    def _closure(self, s):
        return set(s.closure(lambda x: x.hypernyms() + x.instance_hypernyms())) | {s}

    def physical(self, phrase):
        """True when the phrase (or its head noun, for a property of a thing) names something physical."""
        syns = self._syn(phrase, self.wn.NOUN)
        if syns:
            return any(self._physical_root in self._closure(s) for s in syns[:3])
        toks = words(phrase)
        if len(toks) < 2:
            return False
        head, mods = toks[-1], toks[:-1]
        head_syns = self._syn(head, self.wn.NOUN)[:3]
        head_phys = any(self._physical_root in self._closure(s) for s in head_syns)
        head_attr = any(self._attr_roots & self._closure(s) for s in head_syns)
        mod_phys = any(any(self._physical_root in self._closure(s) for s in self._syn(m, self.wn.NOUN)[:3]) for m in mods)
        return head_phys or (head_attr and mod_phys)

    def synonyms(self, phrase):
        out = set()
        for s in self._syn(phrase)[:4]:
            for l in s.lemma_names():
                l = l.replace("_", " ").lower()
                if l != phrase.lower():
                    out.add(l)
        return out

    def corpus_count(self, phrase):
        return 0  # no general corpus in the lexicon (Brown excluded); see OpenCorpora

    def contextual_synonyms(self, word, context, simb, head):
        """Synonyms from the one WordNet sense whose gloss best fits the phrase (embedding Lesk).
        A head word takes noun senses only; a modifier takes adjective, noun or verb senses."""
        wn = self.wn
        pos = {wn.NOUN} if head else {wn.ADJ, wn.ADJ_SAT, wn.NOUN, wn.VERB}
        syns = [x for x in wn.synsets(word.replace(" ", "_")) if x.pos() in pos][:8]
        if not syns:
            return set()
        best = max(syns, key=lambda x: simb.sim(context, x.definition()))
        return {l.replace("_", " ").lower() for l in best.lemma_names()} - {word.lower()}

    def common(self, word):
        return self._zipf(word) >= MIN_ZIPF if self._zipf else self.known(word)


class LexicalSimilarity:
    """Character-trigram cosine (no model). Pure Python; always available."""

    name = "lexical"

    @staticmethod
    def _grams(s):
        s = f"  {s.lower()} "
        return Counter(s[i:i + 3] for i in range(len(s) - 2))

    def sim(self, a, b):
        ga, gb = self._grams(a), self._grams(b)
        dot = sum(ga[k] * gb[k] for k in ga)
        na, nb = math.sqrt(sum(v * v for v in ga.values())), math.sqrt(sum(v * v for v in gb.values()))
        return dot / (na * nb) if na and nb else 0.0

    def nearest(self, query, candidates):
        best = max(range(len(candidates)), key=lambda i: self.sim(query, candidates[i]), default=-1)
        return (best, self.sim(query, candidates[best])) if best >= 0 else (-1, 0.0)


class WordNetSimilarity(LexicalSimilarity):
    """Lexical fallback when WordNet is present: mean best Wu-Palmer similarity of aligned words."""

    name = "lexical"

    def __init__(self, lex: WordNetLexicon):
        self.wn = lex.wn

    def sim(self, a, b):
        ta, tb = [t for t in words(a) if t not in FUNCTION_WORDS], [t for t in words(b) if t not in FUNCTION_WORDS]
        if not ta or not tb or len(ta) != len(tb):
            return super().sim(a, b)
        scores = []
        for x, y in zip(ta, tb):
            if x == y:
                scores.append(1.0)
                continue
            sx, sy = self.wn.synsets(x)[:3], self.wn.synsets(y)[:3]
            scores.append(max((p.wup_similarity(q) or 0.0 for p in sx for q in sy), default=0.0))
        return sum(scores) / len(scores)


class EmbeddingSimilarity:
    """sentence-transformers all-MiniLM-L6-v2 (Apache-2.0), run locally on CPU."""

    name = "embedding"
    MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self):
        from sentence_transformers import SentenceTransformer  # optional dependency
        self.model = SentenceTransformer(self.MODEL, device="cpu")
        self._cache: dict[str, Any] = {}

    def _emb(self, texts):
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if missing:
            for t, e in zip(missing, self.model.encode(missing, normalize_embeddings=True, batch_size=64)):
                self._cache[t] = e
        return [self._cache[t] for t in texts]

    def sim(self, a, b):
        ea, eb = self._emb([a, b])
        return float(ea @ eb)

    def nearest(self, query, candidates):
        if not candidates:
            return -1, 0.0
        import numpy as np
        q = self._emb([query])[0]
        m = np.stack(self._emb(candidates))
        s = m @ q
        i = int(s.argmax())
        return i, float(s[i])


def default_backends(prefer: str = "auto") -> tuple[Lexicon, Similarity]:
    lex: Lexicon
    try:
        lex = WordNetLexicon()
    except (ImportError, LookupError):
        lex = DictLexicon()
    if prefer in ("auto", "embedding"):
        try:
            return lex, EmbeddingSimilarity()
        except ImportError:
            if prefer == "embedding":
                raise
    return lex, (WordNetSimilarity(lex) if isinstance(lex, WordNetLexicon) else LexicalSimilarity())


# ---- code index (read locally, never written) -------------------------------------------------------
class CodeIndex:
    """n-gram counts over local code copies, with the section id of every token."""

    def __init__(self, texts: Iterable[str], max_n: int = 16):
        from .corpus_stats import split_sections
        self.tokens: list[str] = []
        self.section_of: list[str] = []
        self.sentences: list[tuple[str, str]] = []  # (section id, sentence) kept in memory only
        self.input_sha256: list[str] = []
        for text in texts:
            self.input_sha256.append(sha(text))
            parts = split_sections(text) or [("?", text)]
            for sid, body in parts:
                body = body[len(sid):] if body.startswith(sid) else body
                w = words(body)
                self.tokens += w
                self.section_of += [sid] * len(w)
                for s in re.split(r"(?<=[.;:])\s+", " ".join(body.split())):
                    if len(words(s)) >= 4:
                        self.sentences.append((sid, s))
        self.max_n = max_n
        self.grams: dict[int, dict[tuple[str, ...], list[int]]] = {}
        for n in range(1, max_n + 1):
            d: dict[tuple[str, ...], list[int]] = {}
            for i in range(len(self.tokens) - n + 1):
                d.setdefault(tuple(self.tokens[i:i + n]), []).append(i)
            self.grams[n] = d

    def occurrences(self, phrase: str) -> tuple[int, list[str]]:
        toks = tuple(words(phrase))
        if not toks or len(toks) > self.max_n:
            return 0, []
        pos = [p for f in _plural_forms(toks) for p in self.grams[len(f)].get(f, [])]
        return len(pos), sorted({self.section_of[p] for p in pos}, key=_section_key)

    def has(self, gram: tuple[str, ...]) -> bool:
        return gram in self.grams.get(len(gram), {})

    def longest_run(self, text: str) -> tuple[int, tuple[int, int] | None]:
        w = words(text)
        best, where = 0, None
        for i in range(len(w)):
            n = best + 1
            while i + n <= len(w) and n <= self.max_n and self.has(tuple(w[i:i + n])):
                best, where = n, (i, i + n)
                n += 1
        return best, where


def source_record(e: dict[str, Any]) -> dict[str, Any]:
    """What the study output cites for every source: the original source and its license."""
    return {"title": e["title"], "class": e["class"], "role": e["role"], "source_url": e["source_url"],
            "source_citation": corpus_license.citation_text(e), "license_id": e["license_id"],
            "license_url": e["license_url"], "license_local_path": e["license_local_path"],
            "license_sha256": e["license_sha256"], "license_confirmed": e["license_confirmed"]}


def require_resources(manifest: dict[str, Any], ids: list[str]) -> list[dict[str, Any]]:
    """Every lexical resource or count source the study uses needs a valid manifest record."""
    by_id = {e["id"]: e for e in manifest.get("corpora", [])}
    out = []
    for rid in ids:
        if rid not in by_id:
            raise CorpusLicenseError(f"{rid}: resource used by the study has no manifest record (license and citation required)")
        corpus_license.require(by_id[rid])
        out.append(by_id[rid])
    return out


def add_source(manifest: dict[str, Any], entry: dict[str, Any], corpus_dir: Path | None = None) -> dict[str, Any]:
    """Ingest one new source into the manifest (the full build's only way in). Refuses a source
    without license record, local license copy or citation; for a text corpus, reads the local
    file and records its SHA-256 and word count. Returns the manifest with the source added."""
    if any(e["id"] == entry.get("id") for e in manifest.get("corpora", [])):
        raise CorpusLicenseError(f"{entry.get('id')}: already in the manifest")
    e = dict(entry)
    if e.get("role") == "text_corpus":
        if corpus_dir is None or not e.get("local_file") or not (corpus_dir / e["local_file"]).is_file():
            raise CorpusLicenseError(f"{e.get('id')}: text corpus file not found in the corpus directory")
        text = (corpus_dir / e["local_file"]).read_text(encoding="utf-8", errors="ignore")
        e.update(sha256=sha(text), words=len(words(text)))
        e.setdefault("strong_evidence", e.get("class") in ("public_domain", "open_license") and e.get("license_confirmed") is True)
    corpus_license.require(e)
    return {**manifest, "corpora": list(manifest.get("corpora", [])) + [e]}


def _section_key(s: str):
    return [int(x) if x.isdigit() else x for x in re.split(r"[R.]", s) if x]


class OpenCorpora:
    """Public-domain, open-license and locality texts read locally; n-gram counts per corpus.

    ``entries``: manifest records with ``id``, ``class`` (public_domain, open_license, locality)
    and ``strong_evidence``. Only public-domain and open-license corpora count as strong evidence
    for categories (a)/(b); locality material is cite-and-link and is reported separately,
    because Virginia locality documents are not automatically public domain and often echo the
    code text."""

    MAX_N = 6

    def __init__(self, entries: list[dict[str, Any]], texts: dict[str, str] | None = None,
                 queries: set[tuple[str, ...]] | None = None, paths: dict[str, Path] | None = None):
        """``texts``: id -> text held in memory. ``paths``: id -> local file read one at a time
        (the full build: tens of millions of words). ``queries``: when given, only these n-grams
        are counted (see ``query_grams``), which keeps memory small; otherwise every n-gram up to
        MAX_N is counted (small samples and tests)."""
        texts, paths = texts or {}, paths or {}
        by_id = {e["id"]: e for e in entries}
        for cid in list(texts) + list(paths):  # refuse to ingest a source without license record, local license copy and citation
            if cid not in by_id:
                raise CorpusLicenseError(f"{cid}: no manifest record (license and citation required)")
            corpus_license.require(by_id[cid])
        self.entries = {cid: by_id[cid] for cid in list(texts) + list(paths)}
        self.grams: dict[str, Counter] = {}
        self.sha256: dict[str, str] = {}
        self.words: dict[str, int] = {}
        prefixes = {q[:k] for q in queries for k in range(1, len(q) + 1)} if queries is not None else None
        for cid in list(texts) + list(paths):
            text = texts[cid] if cid in texts else paths[cid].read_text(encoding="utf-8", errors="ignore")
            w = words(text)
            c = Counter()
            if queries is None:
                for n in range(1, self.MAX_N + 1):
                    c.update(tuple(w[i:i + n]) for i in range(len(w) - n + 1))
            else:
                for i in range(len(w)):
                    for n in range(1, min(self.MAX_N, len(w) - i) + 1):
                        g = tuple(w[i:i + n])
                        if g not in prefixes:
                            break
                        if g in queries:
                            c[g] += 1
            self.grams[cid], self.sha256[cid], self.words[cid] = c, sha(text), len(w)

    @classmethod
    def query_grams(cls, strings: Iterable[str]) -> set[tuple[str, ...]]:
        """Every n-gram (n <= MAX_N) of the given strings, plus plural forms of whole short strings:
        exactly what ``hits`` and ``longest_run`` look up."""
        q: set[tuple[str, ...]] = set()
        for s in strings:
            w = words(s)
            for i in range(len(w)):
                for n in range(1, min(cls.MAX_N, len(w) - i) + 1):
                    q.add(tuple(w[i:i + n]))
            if 0 < len(w) <= cls.MAX_N:
                q |= {f for f in _plural_forms(tuple(w)) if len(f) <= cls.MAX_N}
        return q

    @classmethod
    def from_manifest(cls, manifest: dict[str, Any], corpus_dir: Path,
                      queries: set[tuple[str, ...]] | None = None) -> "OpenCorpora":
        """Load the manifest's texts (one file at a time). Refuses the whole manifest if any source
        lacks its license record, local license copy or citation (corpus_license.manifest_errors).
        Excluded sources (``excluded`` list) are never loaded."""
        errs = corpus_license.manifest_errors(manifest)
        if errs:
            raise CorpusLicenseError("; ".join(errs))
        paths = {}
        for e in manifest["corpora"]:
            if e.get("role") != "text_corpus":
                continue
            f = corpus_dir / e["local_file"]
            if f.exists():
                paths[e["id"]] = f
        return cls(manifest["corpora"], paths=paths, queries=queries)

    def record(self, cid: str) -> dict[str, Any]:
        """Citation and license for a corpus, as cited in the study output."""
        return source_record(self.entries[cid])

    def strong(self, cid: str) -> bool:
        e = self.entries.get(cid, {})
        return e.get("class") in ("public_domain", "open_license") and e.get("strong_evidence") is True

    def hits(self, phrase: str) -> dict[str, int]:
        toks = tuple(words(phrase))
        if not toks or len(toks) > self.MAX_N:
            return {}
        out = {}
        for cid, c in self.grams.items():
            n = sum(c[f] for f in _plural_forms(toks) if len(f) <= self.MAX_N)
            if n:
                out[cid] = n
        return out

    def windows(self, n: int = MIN_RUN) -> set[tuple[str, ...]]:
        """All n-word windows of the public-domain/open corpora (strong evidence only)."""
        return {g for cid, c in self.grams.items() if self.strong(cid) for g in c if len(g) == n}

    def longest_run(self, text: str, strong_only: bool = True) -> tuple[int, str | None]:
        w = words(text)
        best, where = 0, None
        for cid, c in self.grams.items():
            if strong_only and not self.strong(cid):
                continue
            for i in range(len(w)):
                n = best + 1
                while i + n <= len(w) and n <= self.MAX_N and c[tuple(w[i:i + n])]:
                    best, where = n, cid
                    n += 1
        return best, where


# ---- refined safeguard ------------------------------------------------------------------------------
def free_mask(text: str, free_terms: Iterable[str], normative_never_free: bool = True) -> list[bool]:
    """Per word of ``text``: True if it is a function word, a number, a unit word, or part of a
    category (a)/(b) term (matched as a whole phrase, longest first)."""
    w = words(text)
    mask = [t in FUNCTION_WORDS or _is_number(t) or t in UNIT_WORDS for t in w]
    phrases = sorted({tuple(words(t)) for t in list(free_terms) + list(OFFICIAL_NAMES) if words(t)}, key=len, reverse=True)
    expanded = {f for p in phrases for f in _plural_forms(p)}
    by_len: dict[int, set[tuple[str, ...]]] = {}
    for f in expanded:
        by_len.setdefault(len(f), set()).add(f)
    for n in sorted(by_len, reverse=True):
        for i in range(len(w) - n + 1):
            if tuple(w[i:i + n]) in by_len[n]:
                for j in range(i, i + n):
                    mask[j] = True
    for i, t in enumerate(w):
        if normative_never_free and t in NORMATIVE:
            mask[i] = False  # normative words are never free, even inside a free term
    return mask


def shared_runs(strings: Iterable[str], source: str | CodeIndex, free_terms: Iterable[str] = (),
                n: int = MIN_RUN, open_windows: set[tuple[str, ...]] | None = None) -> list[dict[str, Any]]:
    """Maximal word runs (>= n words) shared between each output string and the source.

    Each run is reported with its length, the number of non-free words in it, the SHA-256 of the
    run, and ``flagged``: True when some n-word window has a non-free word (category (c) or
    normative wording), or when the run reaches ARRANGEMENT_RUN words (copied selection or order).
    ``open_windows``: n-word windows found in public-domain/open corpora; such a window is common
    usage and is not flagged for its words (the arrangement limit still applies).
    """
    idx = source if isinstance(source, CodeIndex) else None
    src_grams = None if idx else {tuple(ws[i:i + n]) for ws in [words(source)] for i in range(len(ws) - n + 1)}
    free_terms = list(free_terms)
    out = []
    for k, s in enumerate(strings):
        w = words(s)
        if len(w) < n:
            continue
        hit = [(idx.has(tuple(w[i:i + n])) if idx else tuple(w[i:i + n]) in src_grams) for i in range(len(w) - n + 1)]
        if not any(hit):
            continue
        mask = free_mask(s, free_terms)
        i = 0
        while i < len(hit):
            if not hit[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(hit) and hit[j + 1]:
                j += 1
            start, end = i, j + n
            windows_flag = any(not all(mask[p:p + n]) and not (open_windows and tuple(w[p:p + n]) in open_windows)
                               for p in range(i, j + 1))
            length = end - start
            out.append({"string": k, "start": start, "length": length, "non_free_words": sum(not m for m in mask[start:end]),
                        "sha256": sha(" ".join(w[start:end])), "flagged": windows_flag or length >= ARRANGEMENT_RUN})
            i = j + 1
    return out


def load_free_terms(path: Path | None = None) -> set[str]:
    """Category (a)/(b) vocabulary terms from the committed study. Missing file: empty (strict)."""
    p = path or RESULTS_PATH
    if not p.exists():
        return set()
    d = json.loads(p.read_text(encoding="utf-8"))
    return {t["term"] for t in d.get("terms", []) if t.get("category") in ("a", "b")}


# ---- inventory ---------------------------------------------------------------------------------------
@dataclass
class Term:
    term: str
    kind: str
    ref: str
    standard_names: list[str] = field(default_factory=list)
    defined_citation: str | None = None


def _camel_words(name: str) -> str:
    base = re.sub(r"^(Ifc|Pset_|Qto_)", "", name.split(".")[-1])
    return " ".join(re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", base)).lower()


def inventory(v=None, repo: Path = REPO_ROOT) -> tuple[list[Term], list[Term]]:
    """(vocabulary terms, paraphrase clauses). Clauses come from the compiled ORI-CL units."""
    v = v or load()
    d = v.data
    terms: list[Term] = []
    defined = {t["defined_term"].lower(): t["citation"] for t in d["defined_terms"]}
    for f in d["facts"]:
        terms.append(Term(f["label"], "fact_label", f"facts/{f['name']}", [m["name"] for m in f.get("maps_to", []) if "name" in m], defined.get(f["label"].lower())))
        for val in f.get("values", []) or []:
            terms.append(Term(val["value"], "fact_value", f"facts/{f['name']}={val['value']}", [], defined.get(val["value"].lower())))
    for s in d["subjects"]:
        terms.append(Term(s["label"], "subject_label", f"subjects/{s['kind']}", [s["ifc"]["name"]], defined.get(s["label"].lower())))
    for t in d["defined_terms"]:
        terms.append(Term(t["defined_term"], "defined_term", f"defined_terms/{t['defined_term']}", [], t["citation"]))
    for g in d["reference_geometry"]:
        terms.append(Term(g["name"].replace("_", " "), "geometry_name", f"reference_geometry/{g['name']}"))
        terms.append(Term(g["gloss"], "geometry_gloss", f"reference_geometry/{g['name']}#gloss"))
    for u in d["units"]:
        terms.append(Term(u["name"].split(" (")[0], "unit", f"units/{u['symbol']}", [u.get("ucum", "")]))
    for k in d["keywords"]:
        terms.append(Term(k["word"], "keyword", f"keywords/{k['word']}"))
    for r in d["relations"]:
        terms.append(Term(r["word"], "relation", f"relations/{r['word']}", [r["ifc_basis"]["name"]]))
    ifc = {e["name"] for e in d["ifc_terms"]} | {s["ifc"]["name"] for s in d["subjects"]}
    ifc |= {m["name"] for f in d["facts"] for m in f.get("maps_to", []) if m.get("source") == "src:ifc-4.3" and "name" in m}
    for name in sorted(ifc):
        terms.append(Term(name, "ifc_identifier", f"ifc/{name}", [name]))
    seen: set[tuple[str, str]] = set()
    uniq = []
    for t in terms:
        if (t.term.lower(), t.kind) not in seen:
            seen.add((t.term.lower(), t.kind))
            uniq.append(t)
    clauses: list[Term] = []
    params: set[str] = set()
    for p in sorted(repo.glob(COMPILED_GLOB)):
        for c in json.loads(p.read_text(encoding="utf-8")):
            u = c["unit"]
            for part in re.split(r"(?:: |; |\. |, where |Values: )", u["paraphrase"].rstrip(".")):
                part = part.strip(" ,.")
                if part and (part.lower(), "paraphrase_clause") not in seen:
                    seen.add((part.lower(), "paraphrase_clause"))
                    clauses.append(Term(part, "paraphrase_clause", u["id"]))
            plan = c.get("plan") or {}
            for key in ("params_required", "params_optional", "params_reported"):
                params.update(plan.get(key) or [])
            for term in plan.get("reviewer_terms") or []:
                if (term.lower(), "reviewer_term") not in seen:
                    seen.add((term.lower(), "reviewer_term"))
                    uniq.append(Term(term, "reviewer_term", u["id"]))
    for name in sorted(params):
        uniq.append(Term(name.replace("_", " "), "param_name", f"param/{name}"))
    return uniq, clauses


# ---- classification ------------------------------------------------------------------------------
def _head_index(toks: list[str]) -> int:
    """Head noun: the word before the first 'of', else the last content word."""
    if "of" in toks[1:]:
        return toks.index("of") - 1
    content = [i for i, t in enumerate(toks) if t not in FUNCTION_WORDS]
    return content[-1] if content else len(toks) - 1


def alternatives(term: str, lex: Lexicon, simb: Similarity) -> list[tuple[str, float]]:
    """Plausible alternative phrasings: whole-phrase synonyms and one-word substitutions.

    With WordNet, each word's synonyms come from the single sense whose gloss best fits the
    phrase; a candidate must reach the similarity threshold against the whole term and (embedding
    backend) its substituted word must reach WORD_SIM_FLOOR against the word it replaces."""
    low = term.lower()
    toks = words(term)
    ctx = getattr(lex, "contextual_synonyms", None)
    head = _head_index(toks) if toks else 0
    subs: list[tuple[str, str, str]] = []  # (candidate, old word, new word)
    whole = ctx(low, low, simb, True) if ctx and lex.lemma(low) else lex.synonyms(low)
    for syn in whole:
        subs.append((syn, low, syn))
    if len(toks) > 1:
        for i, t in enumerate(toks):
            if t in FUNCTION_WORDS or _is_number(t) or t in ABBREVIATIONS:
                continue
            syns = ctx(t, low, simb, i == head) if ctx else lex.synonyms(t)
            for syn in syns:
                subs.append((" ".join(toks[:i] + [syn] + toks[i + 1:]), t, syn))
    thr = PLAUSIBLE_SIM.get(simb.name, PLAUSIBLE_SIM["lexical"])
    out: dict[str, float] = {}
    for cand, old, new in subs:
        if cand == low or cand in out or not all(lex.common(x) for x in words(new) if x not in FUNCTION_WORDS):
            continue
        if old != low and (set(words(old)) & set(words(new))):
            continue  # 'clear' -> 'clear up', 'top' -> 'top side': the same word, not an alternative
        if simb.name == "embedding" and old != low and simb.sim(old, new) < WORD_SIM_FLOOR:
            continue
        s = simb.sim(low, cand)
        if s >= thr:
            out[cand] = round(s, 3)
    return sorted(out.items(), key=lambda x: (-x[1], x[0]))


def classify_term(t: Term, idx: CodeIndex | None, lex: Lexicon, simb: Similarity,
                  open_counts: dict[str, int] | None = None, defined_names: Iterable[str] = (),
                  corpora: OpenCorpora | None = None) -> dict[str, Any]:
    toks = words(t.term)
    content = [x for x in toks if x not in FUNCTION_WORDS and not _is_number(x)]
    code_n, code_secs = idx.occurrences(t.term) if idx else (0, [])
    alts = alternatives(t.term, lex, simb) if t.kind not in ("ifc_identifier",) else []
    dictionary = all(lex.known(x) for x in content) if content else bool(toks)
    lemma = lex.lemma(t.term)
    physical = lex.physical(t.term)
    lexc = lex.corpus_count(t.term)
    wiki = (open_counts or {}).get(t.term.lower())
    noun_phrase = len(toks) <= 4 and not (set(toks) & CLAUSE_MARKERS)
    evidence = []
    if lemma:
        evidence.append(f"WordNet lemma ({lex.name})")
    elif dictionary:
        evidence.append("every word is in the general dictionary")
    if physical:
        evidence.append("WordNet: names a physical thing or a measurable property of one")
    if lexc:
        evidence.append(f"lexicon corpus: {lexc}")
    if wiki:
        evidence.append(f"Wikipedia exact phrase: {wiki}")
    std = [s for s in t.standard_names if s]
    if std:
        evidence.append("standard data name: " + ", ".join(std[:3]))
    corpus_hits = corpora.hits(t.term) if corpora and t.kind != "ifc_identifier" else {}
    strong_sources = sorted(c for c in corpus_hits if corpora.strong(c))
    locality_hits = sum(n for c, n in corpus_hits.items() if not corpora.strong(c) and corpora.entries.get(c, {}).get("class") == "locality")
    weak_hits = sum(n for c, n in corpus_hits.items() if not corpora.strong(c) and corpora.entries.get(c, {}).get("class") != "locality")
    if strong_sources:
        evidence.append(f"public-domain/open corpora: {sum(corpus_hits[c] for c in strong_sources)} hits in {len(strong_sources)} sources ("
                        + ", ".join(strong_sources[:4]) + ")")
    if locality_hits:
        evidence.append(f"Virginia locality material (cite-and-link, not counted as strong): {locality_hits}")
    if weak_hits:
        evidence.append(f"sources with an unconfirmed licence (not counted as strong): {weak_hits}")
    open_hit = bool(lemma or lexc or (wiki or 0) >= WIKI_MIN or std or strong_sources)

    if t.kind == "ifc_identifier":
        cat, why = "b", "IFC 4.3 identifier; use the name as a reference with attribution (CC BY-ND 4.0), no definitions"
    elif t.kind == "unit":
        cat, why = "a", "unit name (NIST SP 811 / SI); plain measurement word"
    elif t.kind in ("keyword", "relation") and len(toks) == 1 and dictionary:
        cat, why = "a", "ordinary English word used as ORI-CL syntax"
    elif t.defined_citation or t.kind == "defined_term":
        if dictionary and noun_phrase and (lemma or physical) and open_hit:
            cat, why = "a", "plain name in ordinary use; the law also defines it, so cite R202 when the legal meaning matters"
        else:
            cat, why = "b", "term defined in law; use the name with its citation"
    elif dictionary and noun_phrase and len(content) <= 3 and physical and open_hit:
        cat, why = "a", "ordinary name of a physical thing or its property, in use outside the code" + (
            f" ({len(alts)} alternatives exist; a plain name stays free)" if len(alts) > A_MAX else "")
    elif t.kind != "defined_term" and len(content) > 1 and _covered_by(t.term, defined_names):
        cat, why = "b", "made only of terms defined in law; cite each definition"
    elif dictionary and noun_phrase and len(alts) <= A_MAX and open_hit:
        cat, why = "a", "ordinary words with few practical alternatives and open-source usage"
    elif dictionary and noun_phrase and len(alts) <= A_MAX and code_n:
        cat, why = "b", "technical term with essentially one practical expression; cite where the code uses it"
    elif noun_phrase and len(alts) <= A_MAX and not code_n:
        cat, why = "a", "ORI's plain descriptive name; not found in the code copies"
    elif noun_phrase and strong_sources:
        cat = "a" if dictionary else "b"
        why = f"the same phrase appears in {len(strong_sources)} public-domain/open trade sources (strong evidence of ordinary use)"
    else:
        cat, why = "c", f"phrasing with {len(alts)} plausible alternatives" + ("" if noun_phrase else "; clause, not a name")
    flag = None
    if cat == "c" and code_n:
        flag = "term-at-issue" if t.kind == "reviewer_term" else "re-express"
    elif cat == "b" and t.kind not in ("ifc_identifier",) and not t.defined_citation and t.kind != "defined_term":
        flag = "cite"
    return {
        "term": t.term, "kind": t.kind, "ref": t.ref, "category": cat, "reason": why, "flag": flag,
        "signals": {
            "code_occurrences": code_n, "code_sections": code_secs[:12], "code_sections_total": len(code_secs),
            "plausible_alternatives": len(alts), "alternatives": [a for a, _ in alts[:6]],
            "dictionary": dictionary, "wordnet_lemma": lemma, "physical": physical,
            "lexicon_corpus_count": lexc, "wikipedia_phrase_hits": wiki,
            "open_corpus_hits": corpus_hits, "public_domain_open_sources": len(strong_sources), "locality_hits": locality_hits,
            "unconfirmed_license_hits": weak_hits,
        },
        "evidence": evidence,
        **({"citation": t.defined_citation} if t.defined_citation else {}),
    }


def _covered_by(text: str, names: Iterable[str]) -> bool:
    """True when every word of ``text`` is a function word or part of one of ``names``."""
    names = [n for n in names if words(n)]
    if not names:
        return False
    mask = [m and not (x in UNIT_WORDS and x not in FUNCTION_WORDS) and not _is_number(x)
            for m, x in zip(free_mask(text, names, normative_never_free=False), words(text))]
    return all(mask)


def classify_clause(t: Term, idx: CodeIndex | None, term_cats: dict[str, str], simb: Similarity,
                    corpora: OpenCorpora | None = None) -> dict[str, Any]:
    free_terms = {k for k, v in term_cats.items() if v in ("a", "b")}
    mask = free_mask(t.term, free_terms)
    w = words(t.term)
    non_free = sum(not m for m in mask)
    run, where = idx.longest_run(t.term) if idx else (0, None)
    run_non_free = sum(not m for m in mask[where[0]:where[1]]) if where else 0
    refined = shared_runs([t.term], idx, free_terms) if idx else []
    near_sec, near_sim = None, None
    if idx and idx.sentences:
        i, s = simb.nearest(t.term, [x[1] for x in idx.sentences])
        near_sec, near_sim = idx.sentences[i][0], round(s, 3)
    cat = "a" if non_free == 0 else "c"
    b_terms = {k for k, v in term_cats.items() if v == "b"}
    if cat == "a" and b_terms and any(free_mask(t.term, b_terms)[i] and w[i] not in FUNCTION_WORDS for i in range(len(w))):
        cat = "b"
    strict = bool(refined)  # any shared run of MIN_RUN words: the enforced rule
    flag = "re-express" if strict else ("watch" if run >= WATCH_RUN and run_non_free else None)
    return {
        "term": t.term, "kind": t.kind, "ref": t.ref, "category": cat,
        "reason": "only free terms, numbers, units and function words" if cat != "c" else f"ORI's composed wording ({non_free} non-free words)",
        "flag": flag,
        "signals": {"words": len(w), "non_free_words": non_free, "longest_shared_run": run, "longest_run_non_free_words": run_non_free,
                    "strict_shared_run": strict, "refined_run_flag_info": any(r["flagged"] for r in refined),
                    "nearest_code_section": near_sec, "nearest_code_similarity": near_sim,
                    **(dict(zip(("public_domain_open_longest_run", "public_domain_open_run_source"), corpora.longest_run(t.term)))
                       if corpora else {})},
    }


def fetch_wikipedia_counts(phrases: Iterable[str], cache: dict[str, int], pause: float = 3.0) -> dict[str, int]:
    """Exact-phrase hit counts from the public Wikipedia search API (read-only GET, counts only)."""
    for p in sorted(set(x.lower() for x in phrases)):
        if p in cache:
            continue
        q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": f'"{p}"', "srlimit": 1, "srinfo": "totalhits",
                                    "srprop": "", "format": "json"})
        req = urllib.request.Request(f"https://en.wikipedia.org/w/api.php?{q}", headers={"User-Agent": "ORI-term-merger-study/0.1 (research; local)"})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    cache[p] = int(json.load(r)["query"]["searchinfo"]["totalhits"])
                break
            except Exception as e:  # rate limit or network failure: back off, then leave uncounted
                retry = getattr(getattr(e, "headers", None), "get", lambda *_: None)("Retry-After")
                wait = min(120, int(retry) if retry and str(retry).isdigit() else 15 * (attempt + 1))
                print(f"wikipedia count {p!r}: {e}; waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
        time.sleep(pause)
    return cache


def study(code_texts: list[str], lex: Lexicon, simb: Similarity, open_counts: dict[str, int] | None = None,
          v=None, repo: Path = REPO_ROOT, corpora: OpenCorpora | None = None,
          resources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """``resources``: manifest records of the lexical resources and count sources used (cited in
    the output with their licenses, like every corpus)."""
    idx = CodeIndex(code_texts) if code_texts else None
    terms, clauses = inventory(v, repo)
    defined = [t.term for t in terms if t.kind == "defined_term" and "," not in t.term]
    rows = [classify_term(t, idx, lex, simb, open_counts, defined, corpora) for t in terms]
    cats: dict[str, str] = {}
    for r in rows:  # a word listed under several kinds takes its most permissive category
        cats[r["term"]] = min(cats.get(r["term"], "c"), r["category"])
    crow = [classify_clause(c, idx, cats, simb, corpora) for c in clauses]
    def counts(rs):
        c = Counter(r["category"] for r in rs)
        return {k: c.get(k, 0) for k in ("a", "b", "c")}
    by_kind: dict[str, dict[str, int]] = {}
    for r in rows + crow:
        by_kind.setdefault(r["kind"], {"a": 0, "b": 0, "c": 0})[r["category"]] += 1
    return {
        "study": "ori-cl-term-merger-0.1",
        "status": "DRAFT",
        "legal_note": ("Analysis to inform counsel, not a legal conclusion. Stores only counts, section ids, SHA-256 digests "
                       "and ORI's own words; no code text. Flagged for legal review before publication."),
        "method": "verification/ori_cl/term_merger.py; docs/TERM-MERGER-METHOD-DRAFT.md",
        "backends": {"lexicon": lex.name, "similarity": simb.name,
                     "model": getattr(simb, "MODEL", None) if simb.name == "embedding" else None,
                     "plausible_similarity_threshold": PLAUSIBLE_SIM.get(simb.name, PLAUSIBLE_SIM["lexical"]),
                     "a_max_alternatives": A_MAX, "min_run": MIN_RUN, "arrangement_run": ARRANGEMENT_RUN, "watch_run": WATCH_RUN},
        "code_inputs_sha256": idx.input_sha256 if idx else [],
        "source_license_rule": ("Every corpus and resource below cites its original source (source_citation, source_url) and its license "
                                "(license_id, license_url, license_local_path with SHA-256); see research/data/ori-cl-open-corpora-DRAFT.json "
                                "and research/licenses/."),
        "open_corpora": ({cid: {**corpora.record(cid), "strong_evidence": corpora.strong(cid),
                                "sha256": corpora.sha256[cid], "words": corpora.words[cid]} for cid in sorted(corpora.entries)}
                         if corpora else {}),
        "lexical_resources": {e["id"]: source_record(e) for e in (resources or [])},
        "signals": SIGNALS,
        "totals": {"vocabulary_terms": len(rows), "paraphrase_clauses": len(crow),
                   "vocabulary": counts(rows), "paraphrase": counts(crow), "by_kind": by_kind,
                   "flags": dict(Counter(r["flag"] for r in rows + crow if r["flag"]))},
        "terms": rows,
        "clauses": crow,
    }


def assert_output_clean(result: dict[str, Any], code_texts: list[str]) -> None:
    """Strict check at generation time: no 6-word run of any output string is in the code copies."""
    idx = CodeIndex(code_texts, max_n=MIN_RUN)
    strings: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            for k, val in o.items():
                strings.append(str(k))
                walk(val)
        elif isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, str):
            strings.append(o)

    walk(result)
    runs = shared_runs(strings, idx, ())
    if runs:
        raise AssertionError(f"output shares {len(runs)} {MIN_RUN}-word runs with the code copies")


def scan_paths(paths: list[Path], code_texts: list[str], free_terms: set[str],
               corpora: OpenCorpora | None = None) -> list[dict[str, Any]]:
    """Strict safeguard over repository files: every shared run of >= MIN_RUN words is a violation.
    Each hit also carries ``refined_flag_info`` (informational only, never a gate). Counts and
    digests only; no text."""
    idx = CodeIndex(code_texts, max_n=MIN_RUN)
    open_windows = corpora.windows(MIN_RUN) if corpora else None
    out = []
    for p in paths:
        files = [x for x in sorted(p.rglob("*")) if x.is_file()] if p.is_dir() else [p]
        for f in files:
            try:
                lines = f.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for n, line in enumerate(lines, 1):
                for r in shared_runs([line], idx, free_terms, MIN_RUN, open_windows):
                    out.append({"file": str(f), "line": n, "length": r["length"], "non_free_words": r["non_free_words"],
                                "violation": True, "refined_flag_info": r["flagged"], "sha256": r["sha256"]})
    return out


KIND_LABELS = {
    "fact_label": "fact labels", "fact_value": "fact values", "subject_label": "subject labels", "defined_term": "defined-term names",
    "geometry_name": "reference-geometry names", "geometry_gloss": "reference-geometry glosses", "unit": "unit names",
    "keyword": "keywords", "relation": "relations", "ifc_identifier": "IFC identifiers", "reviewer_term": "reviewer terms (term at issue)",
    "param_name": "parameter names", "paraphrase_clause": "paraphrase clauses",
}


def report_markdown(result: dict[str, Any]) -> str:
    """Results tables for the method doc, from the study JSON (ORI's words and numbers only)."""
    t = result["totals"]
    lines = [f"Backends: lexicon `{result['backends']['lexicon']}`, similarity `{result['backends']['similarity']}`"
             + (f" (`{result['backends']['model']}`)" if result["backends"].get("model") else "")
             + f"; plausibility threshold {result['backends']['plausible_similarity_threshold']}.", "",
             "| Group | (a) free name | (b) cite | (c) re-express if in code | Total |", "|---|---:|---:|---:|---:|"]
    for kind, c in t["by_kind"].items():
        lines.append(f"| {KIND_LABELS.get(kind, kind)} | {c['a']} | {c['b']} | {c['c']} | {sum(c.values())} |")
    v, p = t["vocabulary"], t["paraphrase"]
    lines.append(f"| **all vocabulary terms** | **{v['a']}** | **{v['b']}** | **{v['c']}** | **{sum(v.values())}** |")
    lines.append(f"| **all paraphrase clauses** | **{p['a']}** | **{p['b']}** | **{p['c']}** | **{sum(p.values())}** |")
    lines += ["", "Flags: " + ", ".join(f"{k} {n}" for k, n in sorted(t["flags"].items())) if t["flags"] else "Flags: none", "",
              "| Flag | Term (ORI's) | Group | Category | Code occurrences | Plausible alternatives | Longest shared run | Reason |",
              "|---|---|---|---|---:|---:|---:|---|"]
    for r in result["terms"] + result["clauses"]:
        if not r["flag"]:
            continue
        s = r["signals"]
        lines.append(f"| {r['flag']} | {r['term']} | {KIND_LABELS.get(r['kind'], r['kind'])} | {r['category']} | {s.get('code_occurrences', '')} | "
                     f"{s.get('plausible_alternatives', '')} | {s.get('longest_shared_run', '')} | {r['reason']} |")
    lines += sources_markdown(result)
    return "\n".join(lines) + "\n"


def sources_markdown(result: dict[str, Any]) -> list[str]:
    """Sources and licenses table: every corpus and resource with its citation and license copy."""
    rows = [(cid, r) for cid, r in sorted(result.get("open_corpora", {}).items())]
    rows += [(rid, r) for rid, r in sorted(result.get("lexical_resources", {}).items())]
    if not rows:
        return []
    out = ["", "Sources and licenses (every corpus and resource used; texts stay outside the repository):", "",
           "| Source id | Citation | License | License copy | Confirmed |", "|---|---|---|---|---|"]
    for cid, r in rows:
        cit = r["source_citation"].replace("|", "/")
        out.append(f"| {cid} | {cit} | [{r['license_id']}]({r['license_url']}) | `{r['license_local_path']}` | "
                   f"{'yes' if r['license_confirmed'] else 'no (see manifest note)'} |")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ori_cl.term_merger", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--code-text", nargs="+", required=True, help="local code copies (read, never written)")
    c.add_argument("--out", default=str(RESULTS_PATH))
    c.add_argument("--backend", choices=("auto", "embedding", "lexical"), default="auto")
    c.add_argument("--open-corpus-cache", default=str(OPEN_CORPUS_CACHE))
    c.add_argument("--fetch-wikipedia", action="store_true", help="fill the cache from the public Wikipedia search API")
    c.add_argument("--corpora", default=str(CORPORA_MANIFEST), help="open-corpora manifest (JSON)")
    c.add_argument("--corpus-dir", default=None, help="directory holding the manifest's local_file texts (outside the repo)")
    ig = sub.add_parser("ingest", help="add one source to the manifest; refused without license record, local license copy and citation")
    ig.add_argument("record", help="JSON file with the new manifest entry")
    ig.add_argument("--corpora", default=str(CORPORA_MANIFEST))
    ig.add_argument("--corpus-dir", default=None, help="directory holding the text corpus local_file (outside the repo)")
    rp = sub.add_parser("report", help="print the results tables (markdown) from a study JSON")
    rp.add_argument("--results", default=str(RESULTS_PATH))
    s = sub.add_parser("scan")
    s.add_argument("--code-text", nargs="+", required=True)
    s.add_argument("paths", nargs="+")
    ns = ap.parse_args(argv)
    if ns.cmd == "report":
        print(report_markdown(json.loads(Path(ns.results).read_text(encoding="utf-8"))), end="")
        return 0
    if ns.cmd == "ingest":
        mpath = Path(ns.corpora)
        try:
            m = add_source(json.loads(mpath.read_text(encoding="utf-8")), json.loads(Path(ns.record).read_text(encoding="utf-8")),
                           Path(ns.corpus_dir) if ns.corpus_dir else None)
        except CorpusLicenseError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        mpath.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"ingested {m['corpora'][-1]['id']} -> {mpath}", file=sys.stderr)
        return 0
    texts = [Path(p).read_text(encoding="utf-8", errors="ignore") for p in ns.code_text]
    if ns.cmd == "scan":
        hits = scan_paths([Path(p) for p in ns.paths], texts, load_free_terms())
        for h in hits:
            print(f"{h['file']}:{h['line']}: STRICT violation: shared run of {h['length']} words sha256={h['sha256'][:12]} "
                  f"(refined info: {'flagged' if h['refined_flag_info'] else 'only free terms'})")
        info = sum(h["refined_flag_info"] for h in hits)
        print(f"strict: {len(hits)} shared runs of >= {MIN_RUN} words (each one fails); "
              f"refined report (information only, not a gate): {info} flagged, {len(hits) - info} only free terms", file=sys.stderr)
        return 1 if hits else 0
    lex, simb = default_backends(ns.backend)
    cache_path = Path(ns.open_corpus_cache)
    cache = json.loads(cache_path.read_text(encoding="utf-8"))["wikipedia_phrase_hits"] if cache_path.exists() else {}
    if ns.fetch_wikipedia:
        terms, _ = inventory()
        cache = fetch_wikipedia_counts([t.term for t in terms if t.kind != "ifc_identifier"], cache)
        cache_path.write_text(json.dumps({
            "source": "https://en.wikipedia.org/w/api.php (list=search, exact phrase, totalhits)",
            "license_note": "Counts only; no Wikipedia text stored.", "fetched": time.strftime("%Y-%m-%d"),
            "wikipedia_phrase_hits": dict(sorted(cache.items()))}, indent=1) + "\n", encoding="utf-8")
    corpora = None
    if ns.corpus_dir and Path(ns.corpora).exists():
        terms_q, clauses_q = inventory()
        queries = OpenCorpora.query_grams([t.term for t in terms_q + clauses_q])
        corpora = OpenCorpora.from_manifest(json.loads(Path(ns.corpora).read_text(encoding="utf-8")), Path(ns.corpus_dir), queries)
        for cid, e in corpora.entries.items():
            if e.get("sha256") and e["sha256"] != corpora.sha256[cid]:
                print(f"warning: corpus {cid} differs from the manifest digest", file=sys.stderr)
    manifest = json.loads(Path(ns.corpora).read_text(encoding="utf-8")) if Path(ns.corpora).exists() else {"corpora": []}
    used = []
    if isinstance(lex, WordNetLexicon):
        used += ["lex:wordnet-3.0"] + (["lex:wordfreq"] if lex._zipf else [])
    if cache:
        used.append("open:wikipedia-search-phrase-counts")
    if simb.name == "embedding":
        used.append("model:all-minilm-l6-v2")
    resources = require_resources(manifest, used)  # refuses a resource without license record and citation
    result = study(texts, lex, simb, cache, corpora=corpora, resources=resources)
    assert_output_clean(result, texts)
    Path(ns.out).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    t = result["totals"]
    print(f"vocabulary {t['vocabulary']} paraphrase {t['paraphrase']} flags {t['flags']} ({lex.name}; {simb.name}) -> {ns.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
