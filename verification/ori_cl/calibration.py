# SPDX-License-Identifier: Apache-2.0
"""Two-reviewer calibration sample for the term merger study (DRAFT template).

Draws a fixed-seed sample of about 100 items from the study results, stratified by kind
(vocabulary term or paraphrase clause) and study category, and writes:

* research/data/ori-cl-term-calibration-sample-DRAFT.json: instructions, label set, the sample
  with empty reviewer fields, and a separate ``study_key`` (the study's own categories), which
  reviewers must not open until both have labelled;
* research/data/ori-cl-term-calibration-sheet-DRAFT.csv: the blind reviewer sheet (no study
  category).

No labels are invented: every reviewer field is empty until a human fills it. ``agreement``
computes Cohen's kappa between the two reviewers and between each reviewer and the study once
labels exist; it returns None while fields are empty.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .vocab import REPO_ROOT

SEED = 20260928
TARGET = 100
MIN_PER_STRATUM = 5
LABELS = ("a", "b", "c")
RESULTS = REPO_ROOT / "research/data/ori-cl-term-merger-DRAFT.json"
OUT_JSON = REPO_ROOT / "research/data/ori-cl-term-calibration-sample-DRAFT.json"
OUT_CSV = REPO_ROOT / "research/data/ori-cl-term-calibration-sheet-DRAFT.csv"
REVIEW_FIELDS = ("reviewer_1_label", "reviewer_1_note", "reviewer_2_label", "reviewer_2_note")

INSTRUCTIONS = [
    "Two reviewers label every item independently, without discussing it and without opening study_key.",
    "Label each item a, b or c using the definitions in label_set (docs/TERM-MERGER-METHOD-DRAFT.md section 2). "
    "Use the code copies you are licensed to read; do not paste code text into the notes.",
    "A note is optional; keep it to your own words (no quoted code text of 6 or more words).",
    "When both are done, run `python -m ori_cl.calibration agreement` for Cohen's kappa (reviewer vs reviewer, each reviewer vs study).",
    "Disagreements are adjudicated by a third person or by discussion; record the result in adjudicated_label.",
    "Thresholds (0.72 similarity, 2 alternatives, 25 Wikipedia hits) are reviewed only after agreement is measured.",
]
LABEL_SET = {
    "a": "free name: an ordinary name for a physical thing or its property, a unit, or a plain English word.",
    "b": "cite: a technical term with essentially one practical expression, including terms defined in law and IFC identifiers.",
    "c": "many expressions: a phrasing with many plausible alternatives, or a clause rather than a name.",
}


def items_from_results(results: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for kind in ("terms", "clauses"):
        for i, r in enumerate(results.get(kind, [])):
            out.append({"item_id": f"{kind[:-1]}-{i:03d}", "kind": r["kind"], "text": r["term"], "ref": r["ref"],
                        "study_category": r["category"], "study_flag": r.get("flag")})
    return out


def stratified_sample(items: list[dict[str, Any]], target: int = TARGET, seed: int = SEED) -> list[dict[str, Any]]:
    strata: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        strata[(it["kind"], it["study_category"])].append(it)
    total = len(items)
    rng = random.Random(seed)
    picked = []
    for key in sorted(strata):
        group = sorted(strata[key], key=lambda x: x["item_id"])
        n = min(len(group), max(MIN_PER_STRATUM, round(target * len(group) / total)))
        picked += rng.sample(group, n)
    rng.shuffle(picked)  # reviewers see no ordering by category
    return picked


def build(results: dict[str, Any], target: int = TARGET, seed: int = SEED) -> dict[str, Any]:
    sample = stratified_sample(items_from_results(results), target, seed)
    strata = Counter(f"{s['kind']}/{s['study_category']}" for s in sample)
    return {
        "status": "DRAFT template: no reviewer labels yet. Labels are left empty on purpose; none are invented.",
        "study_results": "research/data/ori-cl-term-merger-DRAFT.json",
        "code_inputs_sha256": results.get("code_inputs_sha256"),
        "seed": seed, "target": target, "min_per_stratum": MIN_PER_STRATUM,
        "strata": dict(sorted(strata.items())),
        "instructions": INSTRUCTIONS, "label_set": LABEL_SET,
        "items": [{"item_id": s["item_id"], "kind": s["kind"], "text": s["text"], "ref": s["ref"],
                   **{f: "" for f in REVIEW_FIELDS}, "adjudicated_label": ""} for s in sample],
        "study_key": {s["item_id"]: {"category": s["study_category"], "flag": s["study_flag"]} for s in sample},
    }


def sheet_csv(cal: dict[str, Any]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["item_id", "kind", "text", "ref", *REVIEW_FIELDS], lineterminator="\n")
    w.writeheader()
    for it in cal["items"]:
        w.writerow({k: it[k] for k in w.fieldnames})
    return buf.getvalue()


def kappa(x: list[str], y: list[str]) -> float | None:
    pairs = [(a, b) for a, b in zip(x, y) if a in LABELS and b in LABELS]
    if not pairs:
        return None
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    cx, cy = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(cx[k] * cy[k] for k in LABELS) / (n * n)
    return 1.0 if pe == 1 else round((po - pe) / (1 - pe), 4)


def agreement(cal: dict[str, Any]) -> dict[str, Any]:
    items = cal["items"]
    r1 = [i["reviewer_1_label"] for i in items]
    r2 = [i["reviewer_2_label"] for i in items]
    st = [cal["study_key"][i["item_id"]]["category"] for i in items]
    return {"labelled_by_both": sum(a in LABELS and b in LABELS for a, b in zip(r1, r2)), "items": len(items),
            "kappa_r1_r2": kappa(r1, r2), "kappa_r1_study": kappa(r1, st), "kappa_r2_study": kappa(r2, st)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ori_cl.calibration")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--results", default=str(RESULTS))
    a = sub.add_parser("agreement")
    a.add_argument("--sample", default=str(OUT_JSON))
    ns = ap.parse_args(argv)
    if ns.cmd == "build":
        cal = build(json.loads(Path(ns.results).read_text(encoding="utf-8")))
        OUT_JSON.write_text(json.dumps(cal, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        OUT_CSV.write_text(sheet_csv(cal), encoding="utf-8")
        print(f"{len(cal['items'])} items -> {OUT_JSON.name}, {OUT_CSV.name}", file=sys.stderr)
        return 0
    print(json.dumps(agreement(json.loads(Path(ns.sample).read_text(encoding="utf-8"))), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
