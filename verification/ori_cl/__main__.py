# SPDX-License-Identifier: Apache-2.0
"""ORI-CL command line.

  python -m ori_cl compile FILE.oricl [--out compiled.json]
  python -m ori_cl ifc FILE.oricl MODEL.ifc [--jurisdiction urn:ori:jurisdiction:us-va|base]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ori_verify import ifc_extract, units

from . import compile_text, evaluator, ifc_bind


def compiled_json(path: str | Path) -> str:
    return json.dumps(compile_text(Path(path).read_text(encoding="utf-8")), indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ori_cl", description="ORI-CL 0.1 compiler and evaluator. Results are reviewer evidence, not approval.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile"); c.add_argument("source"); c.add_argument("--out")
    i = sub.add_parser("ifc"); i.add_argument("source"); i.add_argument("model"); i.add_argument("--jurisdiction", default=units.VA)
    ns = ap.parse_args(argv)
    if ns.cmd == "compile":
        text = compiled_json(ns.source)
        if ns.out:
            Path(ns.out).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    compiled = compile_text(Path(ns.source).read_text(encoding="utf-8"))
    jur = None if ns.jurisdiction == "base" else ns.jurisdiction
    subjects, _ = ifc_extract.extract(ns.model)
    subjects = ifc_bind.bind(ns.model, subjects, [x["plan"] for x in compiled])
    for r in evaluator.evaluate(compiled, subjects, jur):
        print(f"{r.unit_id}\t{r.subject.label}\t{r.state}\t{r.reason_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
