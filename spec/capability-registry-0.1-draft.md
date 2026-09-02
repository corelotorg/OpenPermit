# ORI Capability Registry — v0.1 Draft

ORI supports permissionless discovery of specialist validators, adapters, data providers and compute capabilities. Registration means **discoverable**, not trusted, certified, authorized or endorsed.

## Capability declaration

```yaml
id: stable identifier
type: Capability
provider: provider/actor id
capability_type: validator | mapper | adapter | evidence_capture | model | compute | registry | other
version: semantic or provider version
status: active | experimental | deprecated | withdrawn
inputs: [media/schema/profile identifiers]
outputs: [media/schema identifiers]
profiles: [supported ORI profile ids]
mode: deterministic | probabilistic | mixed
runtime:
  interface: MCP | REST | local | container | wasm | other
  endpoint: optional endpoint
  image: optional immutable container reference
provenance:
  source_repository: optional URI
  build_attestation: optional evidence id
  software_or_model: identifier/version
conformance:
  suite: ORI conformance version
  results: [evidence/result ids]
security:
  isolation: description/profile
  data_retention: description/profile
  authorization: description/profile
challenge_endpoint: URI or ORI capability
```

## Selection

A client selecting outside compute SHOULD be able to filter or rank by:

- input/output compatibility;
- jurisdiction/profile support;
- deterministic vs probabilistic mode;
- source/validator versions;
- current conformance results;
- provenance/attestation;
- cost and latency where declared;
- data handling/security requirements;
- open challenges, revocations or deprecation status.

## Trust boundary

A registry MUST NOT infer trust from presence, popularity, vendor identity, model provider, cloud provider, government affiliation or payment status.

An authorized jurisdiction or user MAY establish its own allowlist or policy for which capabilities may produce evidence considered in a decision. That policy is separate from ORI's open registry semantics.

## Federated registries

Registries may federate by exchanging signed/versioned capability declarations and challenge/revocation state. No global central registry is required.

A conforming client should preserve the registry/source from which a declaration was learned so discovery itself remains attributable.

## Open compute

Universities, cloud providers, model providers, civic-tech maintainers, standards groups, practitioners and private vendors may expose specialized compute through the same declaration format. Implementations may run a capability locally, remotely, in a container, via WASM, or through MCP/HTTP as long as inputs, outputs, provenance and conformance are inspectable.
