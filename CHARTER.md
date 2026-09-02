# OpenPermit / Open Regulatory Infrastructure

Status: **working charter — recovery branch**

## Mission

Build an open, machine-readable regulatory interface that lets governments, practitioners, software, and models inventory, publish, traverse, verify, measure, challenge, and govern regulatory processes without requiring a proprietary portal, model provider, database, or workflow engine.

OpenPermit is the reference implementation. The Open Regulatory Infrastructure (ORI) contract must be independently implementable.

## Federal implementation target: HUD 2026 home-construction best practices

HUD's 2026 **State and Local Best Practices for Home Construction** provides a concrete federal implementation target for the first public ORI profile. HUD organizes its recommendations around **Cost, Land, and Time**, encourages state and local governments to review the residential construction process, publish requirements and fees, eliminate administrative and technology barriers, accelerate permitting, use technology including AI, support certified third-party review, and provide timely dispute resolution.

OpenPermit does **not** treat this guidance as local law or federal endorsement of OpenPermit.

The implementation proposition is narrower and testable:

> Provide an open, machine-readable layer in which a state or local government can inventory its residential construction process, publish the evidence for how it operates, measure performance, and calculate a challengeable delta against HUD's stated best practices.

Machine pattern:

```text
jurisdiction -> approval -> authority -> requirement -> evidence
             -> reviewer -> deadline -> fee -> status -> decision

HUD practice -> implementation control -> evidence -> measurement -> alignment result
```

The machine-readable HUD profile lives at `profiles/federal/hud-home-construction-best-practices-2026.json` and the implementation note at `docs/HUD-IMPLEMENTATION-TARGET-2026.md`.

### Legal boundary

A HUD recommendation is represented as federal guidance, not silently promoted to a binding Requirement for a jurisdiction. EO 14394 states that the order does not create an independently enforceable private right or benefit.

Therefore OpenPermit reports:

> HUD Best Practice X recommends this. Here is the jurisdiction's documented implementation, evidence, performance, and delta.

It does not report:

> HUD requires this county to do X.

## Core principles

1. **Permissionless** — no exclusive ownership or certification gate is required to implement the standard.
2. **Source-preserving** — normalized terms never erase source-native language, authority, version, or legal effect.
3. **Addressable** — material regulatory objects and evidence have stable identifiers.
4. **Jurisdiction-aware** — applicability is explicit and traceable.
5. **Graph-native** — dependencies, approvals, evidence, decisions, exceptions, and challenges are traversable relationships.
6. **Challengeable** — assertions and machine conclusions can be challenged with evidence and receive a durable disposition.
7. **Testable** — schema and behavior have executable conformance fixtures.
8. **Model-native** — MCP and equivalent machine interfaces are first-class delivery surfaces.
9. **Vendor-neutral** — portals and runtimes are replaceable; the open contract is not.
10. **Runnable** — the reference node boots locally with useful defaults and no mandatory SaaS account.
11. **Authority-preserving** — automated verification does not silently become legal approval.
12. **Open at the seams** — jurisdictions, standards bodies, universities, practitioners, cloud providers, model providers, and specialist validators can contribute profiles, mappings, evidence, and compute through open interfaces.

## Regulatory inventory as a public primitive

ORI treats regulatory inventory as a first-class data product rather than a static report.

A jurisdiction inventory should answer, with provenance:

- What approvals can apply?
- Which authority owns each approval?
- Which provisions create each requirement?
- Which evidence satisfies it?
- Who may review or attest it?
- What fees apply and why?
- What deadlines or clocks apply?
- Which actions depend on which prior actions?
- Where are reviews duplicated or serial when they could be parallel?
- What exceptions, alternative methods, appeal rights, and challenge paths exist?
- What is known, unknown, disputed, stale, or unverified?

## Permitting is the first traversal, not the boundary

The core ontology is regulatory infrastructure. Residential permitting is the first high-value reference profile because it exercises authority, jurisdiction, requirements, evidence, deadlines, fees, inspections, decisions, third-party credentials, spatial anchors, and disputes in one process.

The same core should support additional regulatory domains through namespaced profiles rather than forks.

## Copyright and standards boundary

OpenPermit will not counterfeit authority by republishing licensed model-code text without rights.

The open layer can store source identifiers, adoption/version data, citations, mappings, derived assertions, lawful test definitions, evidence requirements, verification results, deltas, and challenges while keeping authoritative licensed text at its authorized source.

## Governance

Governance is exercised through public version history, source provenance, test vectors, conformance results, issue/challenge records, and reproducible evidence.

Implementations may disagree and still interoperate. A mapping is not authoritative merely because it exists. A verifier is not trusted merely because it registers. A model output is an Assertion until authority or applicable process gives it greater effect.

## Release rule

**Problem. Method. Evidence. Tests.**

No grievance narrative. No vendor war. No claim of government endorsement.

Publish the work and make it independently reproducible.