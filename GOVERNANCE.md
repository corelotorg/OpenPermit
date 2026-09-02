# ORI Governance

Open Regulatory Infrastructure (ORI) is governed as a public technical commons. OpenPermit is a reference implementation, not the owner of regulatory truth and not an exclusive implementation.

## Governance invariants

1. **Public evidence over private authority.** Normative changes must be reviewable from public source, rationale, fixtures, tests, and version history.
2. **No exclusive implementation gate.** Anyone may implement the published ORI contract.
3. **No exclusive certification gate.** Conformance is demonstrated by reproducible tests and declared profiles. Third parties may offer certification services, but no provider is privileged by the standard.
4. **Source-native meaning is preserved.** A mapping or normalization never silently replaces the source term, authority, version, or legal effect.
5. **Challenges are durable.** Disagreement is represented as evidence-bearing challenge records and dispositions; historical assertions are not silently rewritten.
6. **Authority is explicit.** Models, validators, vendors, contributors, and maintainers do not acquire governmental or professional authority merely by participating.
7. **Profiles preserve sovereignty.** Jurisdictions may publish native profiles, adopt shared profiles, or map existing systems through adapters.
8. **Runtime neutrality.** No cloud, model, database, portal, workflow engine, or proprietary client is required to inspect or implement the standard.
9. **Copyright boundaries are respected.** Third-party standards and model codes retain their own legal status and licenses.
10. **Security and provenance are part of interoperability.** Outside validators and compute providers are not trusted by default.

## Change classes

### Editorial
Clarifications that do not change machine semantics. These may be accepted with review and must not alter conformance behavior.

### Compatible extension
New namespaced profiles, mappings, fixtures, optional capabilities, or implementation guidance that preserve the core contract.

### Normative core change
Changes to core types, required properties, relationship semantics, challenge behavior, conformance levels, or interoperability guarantees. These require:

- a public issue or proposal;
- source/rationale;
- backward-compatibility analysis;
- positive and negative test vectors where applicable;
- versioning decision;
- opportunity for challenge before release.

## Decisions

Maintainers merge changes based on evidence, interoperability, testability, source preservation, security, and compatibility—not organizational affiliation or commercial status.

When consensus is absent, the project may preserve competing mappings or profiles rather than force a false single answer. A standard version must remain internally coherent and testable.

## Challenges

A challenge may target a requirement interpretation, mapping assertion, verification method, profile control, source classification, conformance behavior, or governance decision.

A challenge should identify:

- the challenged object or proposal;
- grounds;
- supporting source/evidence;
- proposed disposition or alternative when known.

Challenges remain visible after disposition. Sustained challenges should result in an explicit amendment, supersession, withdrawal, or versioned correction rather than silent mutation.

## Release discipline

Public releases follow:

**Problem → Method → Evidence → Tests.**

Release notes must distinguish recovered historical material, normative current decisions, experimental profiles, and externally sourced guidance.

No release may imply endorsement by a government, standards body, vendor, cloud provider, model provider, association, or contributor unless that endorsement is explicit and independently verifiable.
