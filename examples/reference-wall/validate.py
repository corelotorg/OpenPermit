#!/usr/bin/env python3
"""Small deterministic fixture gate. Geometry only; no legal or code assessment."""
import json
import pathlib
import sys

FILE = pathlib.Path(__file__).with_name("fixture.json")

def check(d):
    errors = []
    if d.get("schema_version") != "openpermit.reference-wall/0.1" or d.get("units") != "in":
        errors.append("schema/units")
    w = d.get("wall", {})
    if (w.get("width"),w.get("height"),w.get("stud_centers"),w.get("stud_spacing_oc"),w.get("nominal_lumber")) != (48,96,[0,16,32,48],16,"2x4"):
        errors.append("wall/stud geometry")
    if w.get("bottom_plate") != {"z":0,"height":1.5} or w.get("top_plate") != {"z":94.5,"height":1.5}:
        errors.append("plates")
    if w.get("sheathing") != {"material":"OSB","thickness":0.4375,"width":48,"height":96}:
        errors.append("sheathing")
    f=d.get("fastener_candidates",{})
    expected={(f"wsp-edge-{x}-{z}",x,z,"edge") for x in (0,48) for z in range(0,97,6)}
    expected|={(f"wsp-field-{x}-{z}",x,z,"field") for x in (16,32) for z in range(0,97,12)}
    try:
        actual=[(p["id"],p["x"],p["z"],p["role"]) for p in f["points"]]
        if f.get("verified_as_installable") is not False or f.get("expected_count")!=52 or len(actual)!=52 or set(actual)!=expected:
            errors.append("fastener candidates")
    except (TypeError,KeyError,ValueError):
        errors.append("malformed fastener points")
    if d.get("gates") != {"geometry":"TESTABLE","code_applicability":"OPEN","connection_fastening":"OPEN","regulatory_approval":"OPEN"}:
        errors.append("authority/gates")
    if d.get("deliverables") != {"ifc":"NOT_INCLUDED","glb":"NOT_INCLUDED","png":"NOT_INCLUDED","independent_ifc_receipt":"NOT_INCLUDED"}:
        errors.append("projection claims")
    return errors

if __name__ == "__main__":
    data=json.loads((pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else FILE).read_text(encoding="utf-8"))
    failures=check(data)
    print(("FAIL: "+", ".join(failures)) if failures else "PASS: synthetic geometry, 52 candidates, OPEN authority and projection gates")
    sys.exit(bool(failures))
