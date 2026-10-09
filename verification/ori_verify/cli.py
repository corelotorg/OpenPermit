# SPDX-License-Identifier: Apache-2.0
"""Command line: run implemented rule units on an IFC model or on declared values.

  python -m ori_verify.cli ifc MODEL.ifc --out report.json [--bcf issues.bcf] [--jurisdiction base]
  python -m ori_verify.cli declared VALUES.json [--manifest MANIFEST.json] --out report.json [--bcf issues.bcf]
  python -m ori_verify.cli manifest PLANS.pdf [...] --plan-set ID --version N --by WHO --at ISO [--supersedes ID ...] --out manifest.json
  python -m ori_verify.cli fixtures OUTDIR     # write the synthetic pass/fail/incomplete IFC models

All outputs are labeled reviewer evidence, not approval.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import EVIDENCE_LABEL
from . import bcf as bcfmod
from . import declared as dec
from . import ifc_extract, ifc_fixtures, pdf_manifest, records, rules, units


def _jur(value: str) -> str | None:
    return None if value == "base" else value


def run_ifc(path, jurisdiction=units.VA, executed_at=None):
    eff = units.implemented_units(_jur(jurisdiction))
    band = eff and next((u.param("guard_trigger_horizontal_band") for u in eff if u.param("guard_trigger_horizontal_band")), None)
    subjects, artifact = ifc_extract.extract(path, guard_band_in=band["quantity"]["value"] if band else 36.0)
    results = rules.evaluate(subjects, eff)
    return records.build_report(results, eff, artifact, "ifc_model", jurisdiction, executed_at)


def run_declared(doc, manifest=None, jurisdiction=None, executed_at=None, path=None):
    jurisdiction = jurisdiction or doc["jurisdiction"]
    eff = units.implemented_units(_jur(jurisdiction))
    subjects = dec.subjects_from_declared(doc, manifest)
    results = rules.evaluate(subjects, eff)
    report = records.build_report(results, eff, dec.artifact_for(doc, path), "declared_values", jurisdiction, executed_at,
                                  captured_by=doc.get("declared_by", records.VALIDATOR_ID))
    report["anchor_problems"] = dec.anchor_problems(doc, manifest)
    if manifest:
        report["evidence"].extend(pdf_manifest.evidence_objects(manifest))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ori_verify", description=f"ORI reference evaluator. {EVIDENCE_LABEL}.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ifc"); a.add_argument("model"); a.add_argument("--out", required=True); a.add_argument("--bcf"); a.add_argument("--jurisdiction", default=units.VA)
    d = sub.add_parser("declared"); d.add_argument("values"); d.add_argument("--manifest"); d.add_argument("--out", required=True); d.add_argument("--bcf")
    m = sub.add_parser("manifest"); m.add_argument("pdfs", nargs="+"); m.add_argument("--plan-set", required=True); m.add_argument("--version", type=int, required=True)
    m.add_argument("--by", required=True); m.add_argument("--at", required=True); m.add_argument("--supersedes", nargs="*", default=[]); m.add_argument("--out", required=True)
    f = sub.add_parser("fixtures"); f.add_argument("outdir")
    ns = ap.parse_args(argv)
    if ns.cmd == "ifc":
        report = run_ifc(ns.model, ns.jurisdiction)
    elif ns.cmd == "declared":
        manifest = json.loads(Path(ns.manifest).read_text()) if ns.manifest else None
        report = run_declared(dec.load(ns.values), manifest, path=ns.values)
    elif ns.cmd == "manifest":
        man = pdf_manifest.build_manifest(ns.pdfs, ns.plan_set, ns.version, ns.by, ns.at, ns.supersedes)
        Path(ns.out).write_text(json.dumps(man, indent=2) + "\n")
        print(f"wrote {ns.out} ({len(man['artifacts'])} artifacts)")
        return 0
    else:
        out = Path(ns.outdir)
        for name, spec in (("pass", ifc_fixtures.passing_spec()), ("fail", ifc_fixtures.failing_spec()), ("incomplete", ifc_fixtures.incomplete_spec())):
            print(ifc_fixtures.write_fixture(spec, out / f"ori-ch03-{name}.ifc"))
        return 0
    Path(ns.out).write_text(records.dumps(report))
    print(f"{EVIDENCE_LABEL}: {report['counts']} -> {ns.out}")
    if ns.bcf:
        _, n = bcfmod.write_bcf(report, ns.bcf)
        print(f"BCF topics (fail + unknown): {n} -> {ns.bcf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
