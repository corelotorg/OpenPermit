# Assembly rule evidence interface — v0.1 draft

**Status:** non-normative ORI profile design. A rule definition, candidate design, and permit decision are different objects.

## Addressable example

```json
{
  "id": "ori:example:rule:wsp-sheathing-fasteners",
  "kind": "CandidateRequirement",
  "authority": "UNRESOLVED",
  "jurisdiction": null,
  "source": {
    "document_id": "UNRESOLVED",
    "edition": null,
    "effective_date": null,
    "citation": null,
    "license": "NOT_REVIEWED"
  },
  "target": {
    "assembly_id": "openpermit.reference-wall/0.1",
    "framing_nominal": "2x4",
    "sheathing": "OSB"
  },
  "applicability": {
    "status": "OPEN",
    "reason": "No authority/adoption basis and no verified matching fastening option"
  },
  "geometry_test": "TESTABLE",
  "regulatory_compliance": "NOT_DETERMINED",
  "decision": null
}
```

This example contains no proprietary fastening prescription and must never be interpreted as a compliant schedule. Even if a stored example mentions another framing size (e.g., 2x6), a 2x4 target does not inherit it by similarity.

## Verification contract

- Resolve **source rights** and document identity before copying any text; store citation, section/table ID, adopted edition, amendment, effective date, retrieval timestamp and cryptographic digest where lawful.
- Preserve **rule alternatives** instead of letting a classifier silently choose one. Each selected connection must have material, member, orientation, fastener, spacing and geometric evidence.
- Preserve exact **target conditions**: site/jurisdiction, building type, fire/wind/seismic/snow assumptions, material/species/grade, member size, layout and relevant exceptions.
- Record two distinct check types: (a) physical/parametric checks and (b) legal/code applicability determination. Unknown is `OPEN`, never a fabricated `PASS`.
- Store each check's input hashes, checker, independent reviewer, negative tests and status. Accepted media cannot replace a semantic or authority check.
- Allow explicit `challenge` and `disposition` edges that do not edit the original source or asserted result.

## Assembly grammar / IFC mapping candidates

| Canonical object | Potential IFC projection | Essential check |
|---|---|---|
| Wall host | `IfcWall` | Stable identity, containment |
| Studs, plates, headers | `IfcMember` | Individual dimensions, relation to host |
| Sheathing | `IfcCovering` | Exact extents, cutouts, supporting members |
| Opening | `IfcOpeningElement` | Correct host void / size / location |
| Materialized nails/screws | `IfcMechanicalFastener` | Position, size, source, identity and connection context |
| Connected member pair | `IfcRelConnectsWithRealizingElements` candidate | Stable participants and realizing fasteners |
| Evidence record | ORI Verification / Evidence | Check version, input hash, result and challenger |

Class mapping must be confirmed against the actual schema, exporter and an **independent** receiver. STEP part-21 encoding is not a substitute for a conforming IFC model. OpenCascade and general STEP solids are separate CAD transport/kernel choices.

The public example does not materialize the IFC row mappings above. Later code should be required to preserve IDs and relationships across canonical source, IFC reread, GLB and PNG evidence. False-pass tests must tamper with IDs, geometry, positions and source references.
