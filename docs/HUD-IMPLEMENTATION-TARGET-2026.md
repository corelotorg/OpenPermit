# HUD 2026 State and Local Best Practices — ORI implementation target

Status: **federal guidance profile; not a statement of binding local law**

## Source

- U.S. Department of Housing and Urban Development, **State and Local Best Practices for Home Construction**: https://www.hud.gov/hud-partners/state-and-local-best-practices
- HUD report PDF: https://www.hud.gov/sites/default/files/Main/documents/State-and-Local-Best-Practices-for-Home-Construction.pdf
- Executive Order 14394, **Removing Regulatory Barriers to Affordable Home Construction**, March 13, 2026: https://www.whitehouse.gov/presidential-actions/2026/03/removing-regulatory-barriers-to-affordable-home-construction/

HUD organizes the recommendations under **Cost**, **Land**, and **Time** and tells state and local governments to review residential construction processes, reduce administrative and technology barriers, publish key requirements and fees, and accelerate permitting.

OpenPermit/ORI treats this as a concrete federal implementation target: a jurisdiction should be able to inventory its current process in machine-readable form, attach evidence, measure performance, and calculate an evidence-backed delta from each HUD best practice.

## Legal boundary

The HUD best practices are guidance. They do not, by themselves, replace state or local law, local adoption, delegated authority, code-official decisions, appeal rights, or other binding legal requirements.

EO 14394 also states that it does not create an independently enforceable private right or benefit.

Therefore an ORI implementation MUST distinguish:

- `source_authority = federal_guidance` from `source_authority = binding_law`;
- a HUD recommendation from a jurisdiction's adopted requirement;
- an evidence-backed alignment result from legal compliance;
- an automated verification result from an authorized governmental decision.

OpenPermit should say:

> HUD Best Practice X recommends this. Here is the jurisdiction's documented implementation, evidence, measured performance, and delta.

It should not say:

> HUD requires this jurisdiction to do X.

## Computable pattern

```text
HUD Best Practice
  -> implementation control
  -> jurisdiction object(s)
  -> evidence
  -> measurement
  -> alignment result
  -> challenge / disposition
```

The underlying permitting process remains a graph:

```text
jurisdiction
  -> approval
  -> authority
  -> requirement
  -> evidence
  -> reviewer
  -> deadline
  -> fee
  -> status
  -> decision
```

## Initial practice-to-control mapping

| HUD best-practice theme | ORI implementation control | Minimum machine evidence | Derived measurement |
|---|---|---|---|
| Publish required inspections, permits, and approvals | `hud.land.regulatory_transparency` | jurisdiction manifest of required approval objects with authority/source | coverage %, unresolved/unknown approvals |
| Publish development fees | `hud.cost.fee_transparency` | machine-readable fee schedule linked to fee authority and applicability | fee coverage, stale schedules, estimated fee stack |
| End unnecessary multiple reviews | `hud.time.no_duplicate_reviews` | review/requirement DAG with reviewer, authority and evidence dependencies | duplicate/redundant review candidates, blocking branches |
| Permit-review fast lane | `hud.time.fast_lane` | explicit eligibility rule, queue/routing action and service target | eligible volume, actual cycle time, fall-out rate |
| Binding timelines / shot clocks | `hud.time.shot_clock` | event timestamps, deadline objects and pause/toll events | elapsed time, active time, breach count, p50/p95 |
| AI / technology for expedited approval | `hud.time.technology_acceleration` | declared validator/model version, deterministic checks, review handoff and decision authority | automated-check coverage, override rate, review-time delta |
| Third-party inspections | `hud.time.third_party_inspection` | inspector credential, scope, evidence package, attestation and accepting authority | third-party usage, acceptance/rejection, reinspection rate |
| State-certified engineers for specified reviews | `hud.time.certified_engineer_review` | engineer credential, review scope, signed/attested result and authority acceptance | review cycle time, acceptance rate, challenge rate |
| Unified development ordinance | `hud.time.unified_development_ordinance` | address/parcel-resolved authoritative requirement graph | source coverage, conflicts, unmapped provisions |
| Objective treatment of construction means/methods | `hud.cost.objective_construction_standards` | requirement mappings separated from construction-method labels | method-dependent deltas, exception/challenge rate |
| Swift dispute resolution | `hud.time.swift_dispute_resolution` | first-class Challenge, response, evidence, disposition and timestamps | open age, resolution time, sustained/rejected/withdrawn |

## Shot-clock profile

HUD recommends cumulative timelines of **less than 60 days for right-to-build** and **less than 30 days for construction permitting and inspections**.

ORI does not hard-code these values into the universal core. They belong in the HUD guidance profile so another jurisdiction, law, program, or future guidance can declare different targets without changing ORI semantics.

A timer MUST preserve enough state to distinguish at least:

- start event;
- deadline/target;
- completion event;
- active elapsed time;
- any lawful pause/toll event and its authority;
- missed target;
- challenge/dispute over the clock;
- the governing source for the target.

## Technology and AI boundary

HUD's technology recommendation maps cleanly to ORI's separation between Verification and Decision:

1. deterministic/schema/rule checks first where available;
2. model-assisted interpretation or triage as attributable Assertions;
3. human or otherwise authorized governmental Decision where the law/process requires it;
4. preserved evidence, provenance, version and challenge path throughout.

A model result MUST NOT silently become an approval.

## Third-party evidence model

Third-party inspections and certified-engineer reviews require portable trust without making a private provider authoritative by default.

Minimum ORI evidence should include:

- actor identity;
- credential issuer and credential identifier;
- credential status/validity interval;
- authorized scope;
- artifact/evidence IDs;
- capture time and spatial anchor where relevant;
- integrity hash/signature/attestation where available;
- requirement(s) evaluated;
- result;
- accepting/rejecting Authority and Decision;
- challenges and dispositions.

This is the bridge to the still-needed open geo-attested evidence and third-party-attestation profiles.

## Copyright and authority boundary

The open corpus should not redistribute licensed model-code text merely to make the graph convenient.

Store and expose, where lawful:

- citations and stable identifiers;
- jurisdiction adoption/version data;
- source locators;
- requirements/assertions derived with provenance;
- mappings;
- test definitions;
- evidence requirements;
- verification outputs;
- deltas and challenges.

Authoritative copyrighted source text remains at its authorized source unless distribution rights permit otherwise.

## Product boundary

OpenPermit is **not another permitting portal**.

It is the reference implementation of an open regulatory interface underneath portals, permitting vendors, jurisdiction systems, models, inspectors, engineers, builders, and public data systems.

The HUD profile provides a first nationally relevant, measurable reference implementation of that interface without claiming federal endorsement or legal preemption.