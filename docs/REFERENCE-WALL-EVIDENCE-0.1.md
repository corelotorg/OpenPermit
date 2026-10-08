# Synthetic reference wall — geometry and evidence boundary (v0.1 draft)

**Public example, not an approved wall design.** This document and the companion fixture define an independently runnable *geometry-contract demonstration*, not a permit application, code determination or engineering certification. No private CORELOT project plans or internal runtime files are included.

## Minimal semantic chain

```text
source / effective authority / licensing -> candidate requirement + applicability gate
                                        -> canonical typed assembly + dimensions
                                        -> deterministic geometry checks + negative cases
                                        -> IFC semantic exchange projection and independent reread
                                        -> GLB runtime projection -> evidence views -> hash receipt
                                        -> independent checker -> disposition / challenge
```

A passing geometry check does **not** pass a regulatory requirement. Geometry truth, IFC exchange identity, renderer fidelity, source rights, code applicability and human authorization are separate assertions with separate evidence.

## Synthetic v0.1 fixture

The checked-in [fixture](../examples/reference-wall/fixture.json) describes a 48 × 96 inch specimen with nominal 2x4 framing, four 16-inch-on-center stud positions, two plate envelopes, 7/16-inch OSB and 52 addressable *placement candidates*. It is a **mathematical example** for demonstrating repeatability and rejection of edits, not a realistic, published fastening schedule. The absolute sheathing-edge coordinates in this initial exercise are geometry reference points only, not authorized nail installation points.

Run:

```sh
python examples/reference-wall/validate.py
python -m unittest discover -s examples/reference-wall -p 'test_*.py' -v
```

The example validates cell geometry, coordinate identities, and the fact that authority and projection gates remain OPEN. It rejects a missing or shifted point and false resolution of regulatory approval. It does not run, generate, or claim to validate IFC, GLB, an inspection PNG or an independent professional judgment.

## Promotion evidence required for a larger assembly

| Gate | Required evidence | Present in this public example |
|---|---|---|
| Source and licensing | Source ID, jurisdiction, edition, version, retrieval timestamp, re-use rights | OPEN |
| Parametric geometry | Typed members/relationships, dimensions and repeatable hashes | Minimal synthetic input |
| Rules/applicability | Explicit applicability to species, member size, fastening, loads and edition; negative tests | OPEN |
| Connection grammar | Header, jack, sill, cripple, sheathing and fastener interactions | NOT INCLUDED |
| IFC interoperability | Stable IDs/GlobalIds, exact relationship endpoints, external parser and independent reread | NOT INCLUDED |
| GLB/render | Geometric correspondence, front/back/isometric/cutaway plates with unobscured evidence | NOT INCLUDED |
| Checker independence | Maker/checker identity, reproducible receipts, conflicting/negative cases | NOT INCLUDED |
| Authority | Licensed/authorized decision; separate from machine checks | OPEN |

### Representation boundaries

- **Canonical assembly**: owns dimensions, identities and relations.
- **IFC (STEP-encoded IFC)**: semantic BIM interchange; transfer of selected canonical semantics must be independently validated.
- **STEP / OpenCascade**: potential exact CAD geometry exchange/kernel, *not included in this example* and not a substitute for IFC's construction semantics.
- **GLB**: runtime visualization projection; PNG evidence is never a geometry or code authority.
- **ORI**: provenance, applicability, verification and challenge layer. An IFC model, render, or AI classifier cannot independently issue a permit.

## Next public promotion criteria

1. Choose a rights-cleared, standalone synthetic assembly with *no* client or proprietary production content.
2. Publish actual exporter/validator source and pinned dependencies only after a clean public-code review.
3. Run independent IFC implementation parsing, geometry/identity/dimension comparison and negative cases in CI.
4. Publish a reproducible, fully hashed evidence packet and trace it from exact source version to checks and inspection results.
5. Retain every unresolved framing/fastening/code applicability rule as OPEN.
6. Add practical access from the public site and machine-readable document index.

**Copyright boundary:** statutory citations, source links and original test definitions can be published subject to applicable rights; this document does not redistribute copyrighted ICC model-code text, vendor reports or client material.
