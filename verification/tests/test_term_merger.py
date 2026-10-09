# SPDX-License-Identifier: Apache-2.0
"""Term merger study (DRAFT): category rules, the refined 6-word-run safeguard, and the committed
results. Code-like wording here is made up (a fictional harbor code); no ICC text is used."""
import json
import re
from pathlib import Path

import pytest

from ori_cl import corpus_license as cl, corpus_stats, term_merger as tm, vocab

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "research" / "data" / "ori-cl-term-merger-DRAFT.json"

# Fictional code text: plain names (lantern post, mooring rope) and one distinctive phrasing.
FICTION = """R901 Lanterns
R901.1 General. Every lantern post must be steadfastly and conspicuously affixed to the quay wall in a manner satisfactory to the harbor warden.
R901.2 Height. The lantern post height at the quay wall must not exceed 9 feet.
R902 Moorings
R902.1 Ropes. Each mooring rope at the quay wall of the dock must be sound.
"""
FREE = {"lantern post", "lantern post height", "quay wall", "mooring rope", "dock", "harbor warden"}


def lex():
    return tm.DictLexicon(
        entries={"lantern": [], "post": ["pole", "stake"], "quay": ["wharf"], "wall": [], "mooring": [], "rope": ["line", "cord"],
                 "height": [], "dock": ["pier"], "steadfastly": ["firmly"], "conspicuously": ["visibly", "prominently"],
                 "affixed": ["attached", "fastened", "fixed", "mounted"], "manner": ["way"], "satisfactory": ["acceptable"],
                 "lantern post": [], "quay wall": [], "mooring rope": ["mooring line"],
                 "visibly": ["conspicuously", "prominently"], "attached": ["affixed", "fastened", "mounted"]},
        physical={"lantern post", "quay wall", "mooring rope", "dock"},
        corpus="the old lantern post by the quay wall; a mooring rope; lantern post height",
    )


class Same:
    """Similarity stub: every candidate is plausible (the lexical fallback's coarsest case)."""
    name = "lexical"
    def sim(self, a, b): return 1.0
    def nearest(self, q, c): return (0, 1.0) if c else (-1, 0.0)


# ---- refined safeguard ------------------------------------------------------------------------
def test_run_of_free_terms_is_not_flagged():
    out = ["Each mooring rope at the quay wall of the dock"]  # 10 shared words, all free or function words
    runs = tm.shared_runs(out, FICTION, FREE)
    assert runs and runs[0]["length"] >= 6 and not runs[0]["flagged"] and runs[0]["non_free_words"] == 0
    assert tm.shared_runs(out, FICTION, ())[0]["flagged"]  # the old strict check would flag it


def test_distinctive_phrasing_is_flagged():
    out = ["post must be steadfastly and conspicuously affixed"]
    runs = tm.shared_runs(out, FICTION, FREE)
    assert runs and runs[0]["flagged"] and runs[0]["non_free_words"] >= 4


def test_normative_words_are_never_free():
    out = ["The lantern post height at the quay wall must not exceed 9 feet"]
    runs = tm.shared_runs(out, FICTION, FREE | {"must not exceed"})
    assert runs and runs[0]["flagged"]


def test_long_arrangement_of_free_terms_is_flagged():
    src = "the dock the quay wall the mooring rope the lantern post the dock the quay wall the mooring rope"
    runs = tm.shared_runs([src], src, FREE)
    assert runs[0]["length"] >= tm.ARRANGEMENT_RUN and runs[0]["flagged"]


def test_runs_carry_digests_not_text():
    runs = tm.shared_runs(["post must be steadfastly and conspicuously affixed"], FICTION, FREE)
    blob = json.dumps(runs)
    assert "steadfastly" not in blob and len(runs[0]["sha256"]) == 64


def test_corpus_stats_guard_is_strict_even_for_free_terms():
    # Project decision 2026-09-28: the strict 6-word check is the enforced rule; the refined verdict is information only.
    stats = {"note": "Each mooring rope at the quay wall of the dock"}
    assert tm.shared_runs([stats["note"]], FICTION, FREE)[0]["flagged"] is False  # refined report: only free terms
    with pytest.raises(AssertionError, match="strict"):
        corpus_stats.assert_no_text(stats, FICTION)
    with pytest.raises(AssertionError, match="strict"):
        corpus_stats.assert_no_text({"note": "post must be steadfastly and conspicuously affixed"}, FICTION)
    corpus_stats.assert_no_text({"note": "Each rope is tied at the dock"}, FICTION)  # 5 or fewer shared words pass


def test_scan_fails_on_any_shared_run_refined_is_information_only(tmp_path, capsys):
    code = tmp_path / "code.txt"
    code.write_text(FICTION)
    doc = tmp_path / "doc.md"
    doc.write_text("Each mooring rope at the quay wall of the dock\n")  # only free terms: refined would pass
    assert tm.main(["scan", str(doc), "--code-text", str(code)]) == 1
    err = capsys.readouterr()
    assert "STRICT violation" in err.out and "information only" in err.err
    doc.write_text("Ropes are tied to the quay.\n")
    assert tm.main(["scan", str(doc), "--code-text", str(code)]) == 0


def test_free_mask_matches_whole_phrases():
    m = tm.free_mask("the lantern post must stand", {"lantern post"})
    assert m == [True, True, True, False, False]
    assert tm.free_mask("lantern posts", {"lantern post"}) == [True, True]  # plural form


# ---- classification ----------------------------------------------------------------------------
def test_categories_on_fictional_terms():
    idx = tm.CodeIndex([FICTION])
    L = lex()
    a = tm.classify_term(tm.Term("mooring rope", "fact_label", "x", ["Pset_Fiction.Rope"]), idx, L, Same())
    assert a["category"] == "a" and a["signals"]["code_occurrences"] == 1 and a["signals"]["code_sections"] == ["R902.1"]
    b = tm.classify_term(tm.Term("Harbor Warden", "defined_term", "x", [], "defined at H201 (fiction)"), idx, L, Same())
    assert b["category"] == "b" and b["citation"].startswith("defined at")
    c = tm.classify_term(tm.Term("conspicuously affixed", "fact_label", "x"), idx, L, Same())
    assert c["category"] == "c" and c["flag"] == "re-express" and c["signals"]["plausible_alternatives"] > tm.A_MAX
    own = tm.classify_term(tm.Term("visibly attached", "fact_label", "x"), idx, L, Same())
    assert own["category"] == "c" and own["flag"] is None  # ORI's own wording: not in the code text
    ifc = tm.classify_term(tm.Term("IfcWindow", "ifc_identifier", "x", ["IfcWindow"]), idx, L, Same())
    assert ifc["category"] == "b"


def test_clause_classification_and_nearest_section():
    idx = tm.CodeIndex([FICTION])
    r = tm.classify_clause(tm.Term("the lantern post at the quay wall", "paraphrase_clause", "u1"), idx, dict.fromkeys(FREE, "a"), Same())
    assert r["category"] == "a" and r["flag"] is None and re.fullmatch(r"R\d{3}(\.\d+)*", r["signals"]["nearest_code_section"])
    r = tm.classify_clause(tm.Term("each post must be steadfastly and conspicuously affixed", "paraphrase_clause", "u2"), idx, dict.fromkeys(FREE, "a"), Same())
    assert r["category"] == "c" and r["flag"] == "re-express" and r["signals"]["strict_shared_run"]


def test_composition_of_defined_terms_and_term_at_issue():
    idx = tm.CodeIndex([FICTION])
    L = lex()
    r = tm.classify_term(tm.Term("harbor warden quay wall", "reviewer_term", "x"), idx, L, Same(), None, ["Harbor Warden", "Quay Wall"])
    assert r["category"] == "b"
    r = tm.classify_term(tm.Term("conspicuously affixed", "reviewer_term", "x"), idx, L, Same())
    assert r["category"] == "c" and r["flag"] == "term-at-issue"  # quoted on purpose (4 words or fewer), cited


def test_alternatives_skip_the_same_word():
    L = tm.DictLexicon({"top": ["top side", "summit"], "guard": []})
    alts = [a for a, _ in tm.alternatives("guard top", L, Same())]
    assert alts == ["guard summit"]


def _licensed(sid: str, cls: str, **kw) -> dict:
    """A made-up corpus record with a valid license record, in-repo license copy and citation."""
    lic = "research/licenses/usc-17-105.txt" if cls != "locality" else "research/licenses/va-locality-pwc-no-license-found.md"
    e = {"id": sid, "title": f"Test source {sid}", "class": cls, "role": "text_corpus", "strong_evidence": cls != "locality",
         "source_url": "https://example.org/source", "local_file": f"{sid.replace(':', '-')}.txt", "sha256": "0" * 64, "words": 8,
         "source_citation": {"author": "Test Agency", "title": "Test Manual", "year": "1990", "publisher": "Test Press",
                             "identifier": "TM 0-000", "archive_url": "https://example.org/archive", "accessed": "2026-09-28"},
         "license_id": "US-PD-federal-work", "license_basis": "test basis", "license_url": "https://example.org/license",
         "license_local_path": lic, "license_sha256": cl.file_sha256(REPO / lic), "license_fetched_at": "2026-09-28",
         "license_confirmed": cls != "locality"}
    if cls == "locality":
        e["license_note"] = "no license found; cite-and-link"
    e.update(kw)
    return e


def test_public_domain_corpus_is_strong_evidence_and_locality_is_not():
    entries = [_licensed("pd:manual", "public_domain"), _licensed("loc:county", "locality")]
    corpora = tm.OpenCorpora(entries, {"pd:manual": "Fix the gangway cleat to the pier.",
                                       "loc:county": "The gangway cleat is inspected. A bollard ring too."})
    assert corpora.strong("pd:manual") and not corpora.strong("loc:county")
    idx = tm.CodeIndex([FICTION + "\nR903.1 Cleats. A gangway cleat must be galvanized. A bollard ring must be sound.\n"])
    L = tm.DictLexicon({"gangway": ["ramp", "walkway", "bridge"], "cleat": ["chock", "block"], "bollard": ["post"], "ring": ["hoop", "loop"]})
    r = tm.classify_term(tm.Term("gangway cleat", "fact_label", "x"), idx, L, Same(), corpora=corpora)
    assert r["category"] == "a" and r["signals"]["public_domain_open_sources"] == 1 and r["signals"]["locality_hits"] == 1
    r = tm.classify_term(tm.Term("bollard ring", "fact_label", "x"), idx, L, Same(), corpora=corpora)
    assert r["category"] == "c" and r["flag"] == "re-express"  # a locality hit alone is not strong evidence


def test_committed_corpora_manifest_records_license_copy_and_citation():
    m = json.loads((REPO / "research" / "data" / "ori-cl-open-corpora-DRAFT.json").read_text())
    assert m["method_only"] and "no text" in m["method_only"][0]["use"]
    assert cl.manifest_errors(m) == []
    for e in m["corpora"]:
        assert e["class"] in cl.CLASSES and e["source_url"].startswith("https://") and e["license_basis"]
        assert (REPO / e["license_local_path"]).is_file() or e["license_local_path"].startswith(cl.EXTERNAL_LICENSE_DIR)
        if e["role"] == "text_corpus":
            assert len(e["sha256"]) == 64
            assert e["strong_evidence"] is (e["class"] != "locality" and e["license_confirmed"] is True)
        if e["class"] == "locality":
            assert "Cite-and-link" in e["license_basis"] and e["license_confirmed"] is False
    ids = {e["id"] for e in m["corpora"]}
    assert {"lex:wordnet-3.0", "lex:wordfreq", "open:wikipedia-search-phrase-counts", "cand:uniclass"} <= ids
    assert "lex:brown-corpus" not in ids  # excluded 2026-09-28 (conflicting non-commercial statement)
    assert m["excluded"][0]["id"] == "lex:brown-corpus" and "non-commercial" in m["excluded"][0]["excluded_reason"]
    assert all(x["excluded_reason"] and x["excluded_on"] for x in m["excluded"]) and not ids & {x["id"] for x in m["excluded"]}


def test_corpus_tool_refuses_source_without_license_copy_or_citation(tmp_path):
    good = _licensed("pd:manual", "public_domain")
    for broken in ({k: v for k, v in good.items() if k != "license_id"},
                   {**good, "license_local_path": "research/licenses/missing.txt"},
                   {**good, "license_sha256": "f" * 64},
                   {**good, "source_citation": {"title": "Test Manual"}},
                   {**good, "license_confirmed": False, "license_note": "contractor-prepared", "strong_evidence": True}):
        with pytest.raises(cl.CorpusLicenseError):
            tm.OpenCorpora([broken], {"pd:manual": "Fix the gangway cleat to the pier."})
        with pytest.raises(cl.CorpusLicenseError):
            tm.OpenCorpora.from_manifest({"corpora": [broken]}, tmp_path)
    with pytest.raises(cl.CorpusLicenseError):  # a text with no manifest record at all
        tm.OpenCorpora([], {"pd:other": "Fix the gangway cleat."})
    (tmp_path / "pd-manual.txt").write_text("Fix the gangway cleat to the pier.")
    with pytest.raises(cl.CorpusLicenseError):
        tm.add_source({"corpora": []}, {k: v for k, v in good.items() if k != "source_citation"}, tmp_path)
    m = tm.add_source({"corpora": []}, good, tmp_path)
    assert m["corpora"][0]["words"] == 7 and m["corpora"][0]["sha256"] == tm.sha("Fix the gangway cleat to the pier.")
    with pytest.raises(cl.CorpusLicenseError):
        tm.add_source(m, good, tmp_path)  # duplicate id
    with pytest.raises(cl.CorpusLicenseError):
        tm.require_resources({"corpora": []}, ["lex:wordnet-3.0"])


def test_study_output_cites_source_and_license_for_every_corpus():
    corpora = tm.OpenCorpora([_licensed("pd:manual", "public_domain")], {"pd:manual": "Fix the gangway cleat to the pier."})
    r = tm.study([], tm.DictLexicon({}), tm.LexicalSimilarity(), {}, corpora=corpora,
                 resources=[_licensed("lex:test", "open_license", role="lexical_resource")])
    for rec in list(r["open_corpora"].values()) + list(r["lexical_resources"].values()):
        assert rec["source_citation"].startswith("Test Agency. Test Manual. 1990.") and "accessed 2026-09-28" in rec["source_citation"]
        assert rec["license_id"] and rec["license_url"] and rec["license_local_path"].startswith("research/licenses/")
    md = tm.report_markdown(r)
    assert "Sources and licenses" in md and "pd:manual" in md and "lex:test" in md and "usc-17-105.txt" in md


def test_committed_results_cite_source_and_license():
    r = json.loads((REPO / "research" / "data" / "ori-cl-term-merger-DRAFT.json").read_text())
    assert r["open_corpora"] and r["lexical_resources"]
    for rec in list(r["open_corpora"].values()) + list(r["lexical_resources"].values()):
        assert rec["source_citation"] and rec["license_id"] and rec["license_local_path"] and rec["license_url"].startswith("https://")


def test_lexical_similarity_is_deterministic():
    s = tm.LexicalSimilarity()
    assert s.sim("riser height", "riser height") == pytest.approx(1.0)
    assert 0 < s.sim("riser height", "riser rise") < 1
    assert s.nearest("smoke alarm", ["bench", "smoke alarms"])[0] == 1


def test_inventory_covers_every_vocabulary_term():
    terms, clauses = tm.inventory()
    names = {(t.kind, t.term) for t in terms}
    v = vocab.load().data
    assert all(("fact_label", f["label"]) in names for f in v["facts"])
    assert all(("defined_term", d["defined_term"]) in names for d in v["defined_terms"])
    assert all(("keyword", k["word"]) in names for k in v["keywords"])
    assert clauses and all(c.kind == "paraphrase_clause" for c in clauses)


# ---- committed results --------------------------------------------------------------------------
def test_committed_results_are_current_and_derived_only():
    d = json.loads(RESULTS.read_text())
    assert d["status"] == "DRAFT" and "not a legal conclusion" in d["legal_note"]
    terms, clauses = tm.inventory()
    got = {(r["kind"], r["term"]) for r in d["terms"]}
    assert {(t.kind, t.term) for t in terms} == got, "re-run python -m ori_cl.term_merger classify"
    assert {c.term for c in clauses} == {r["term"] for r in d["clauses"]}
    ori_words = {t.term for t in terms} | {c.term for c in clauses}
    for r in d["terms"] + d["clauses"]:
        assert r["category"] in ("a", "b", "c") and r["term"] in ori_words
        secs = r["signals"].get("code_sections", []) + [r["signals"].get("nearest_code_section")]
        assert all(s is None or re.fullmatch(r"R\d{3}(\.\d+)*|\?", s) for s in secs)
        for alt in r["signals"].get("alternatives", []):
            assert len(alt.split()) <= len(r["term"].split()) + 3  # one-word substitutions of ORI's own term
    t = d["totals"]
    assert sum(t["vocabulary"].values()) == len(d["terms"]) and sum(t["paraphrase"].values()) == len(d["clauses"])


def test_free_terms_exclude_category_c():
    d = json.loads(RESULTS.read_text())
    free = tm.load_free_terms()
    assert free and not any(r["term"] in free for r in d["terms"] if r["category"] == "c" and
                            not any(x["term"] == r["term"] and x["category"] != "c" for x in d["terms"]))


def test_no_committed_paraphrase_clause_is_flagged_for_re_expression():
    d = json.loads(RESULTS.read_text())
    assert not [r["term"] for r in d["clauses"] if r["flag"] == "re-express"]


def test_query_grams_streaming_matches_full_counts(tmp_path):
    text = "Fix the gangway cleat to the pier. Gangway cleats rust. The pier has a gangway cleat."
    f = tmp_path / "t.txt"
    f.write_text(text)
    e = _licensed("pd:manual", "public_domain")
    full = tm.OpenCorpora([e], {"pd:manual": text})
    q = tm.OpenCorpora.query_grams(["gangway cleat", "the pier has a gangway"])
    lazy = tm.OpenCorpora([e], paths={"pd:manual": f}, queries=q)
    for p in ("gangway cleat", "the pier has a gangway"):
        assert lazy.hits(p) == full.hits(p) and lazy.longest_run(p) == full.longest_run(p)
    assert lazy.words == full.words and lazy.sha256 == full.sha256
    assert len(lazy.grams["pd:manual"]) < len(full.grams["pd:manual"])
