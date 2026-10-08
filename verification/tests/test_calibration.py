# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

from ori_cl import calibration as cal

REPO = Path(__file__).resolve().parents[2]


def _results(n_terms=60, n_clauses=30):
    cats = "aaabbc"
    return {"code_inputs_sha256": ["x"],
            "terms": [{"term": f"t{i}", "kind": "fact_label", "ref": "r", "category": cats[i % 6], "flag": None} for i in range(n_terms)],
            "clauses": [{"term": f"c{i}", "kind": "paraphrase_clause", "ref": "r", "category": "c" if i % 3 else "a", "flag": None}
                        for i in range(n_clauses)]}


def test_sample_is_deterministic_stratified_and_unlabelled():
    a, b = cal.build(_results(), target=40), cal.build(_results(), target=40)
    assert a == b
    assert all(n >= min(cal.MIN_PER_STRATUM, 1) for n in a["strata"].values()) and len(a["strata"]) == 5
    assert all(it[f] == "" for it in a["items"] for f in (*cal.REVIEW_FIELDS, "adjudicated_label"))
    assert set(a["study_key"]) == {it["item_id"] for it in a["items"]}
    assert "study_category" not in cal.sheet_csv(a).splitlines()[0]


def test_kappa_none_until_labelled_and_correct_when_labelled():
    assert cal.kappa(["", ""], ["", ""]) is None
    assert cal.kappa(list("aabbcc"), list("aabbcc")) == 1.0
    assert cal.kappa(list("abab"), list("baba")) < 0


def test_committed_calibration_template_has_no_labels():
    p = REPO / "research/data/ori-cl-term-calibration-sample-DRAFT.json"
    if not p.exists():
        return
    c = json.loads(p.read_text())
    assert "DRAFT" in c["status"] and 80 <= len(c["items"]) <= 130
    assert all(it[f] == "" for it in c["items"] for f in (*cal.REVIEW_FIELDS, "adjudicated_label"))
    assert cal.agreement(c)["kappa_r1_r2"] is None
