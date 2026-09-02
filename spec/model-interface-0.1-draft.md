# ORI Model Interface — v0.1 Draft

Status: public working draft.

The ORI Model Interface defines the minimum model-facing capabilities required to inspect and traverse Open Regulatory Infrastructure without tying the ontology to a particular model provider or transport.

MCP Streamable HTTP is the initial reference transport. Equivalent transports may implement the same semantics.

## Required capabilities

### `ori.capabilities`
Return server identity, ORI versions, supported profiles, transports, conformance metadata, mutability, and security/authorization requirements.

### `ori.get`
Retrieve one addressable ORI object by stable identifier with provenance, jurisdiction, version/effective time, source links, and open challenges when available.

### `ori.traverse`
Traverse typed relationships from one or more start objects. Requests should support relationship filters, direction, maximum depth, profile scope, effective-time scope, and cycle-safe traversal.

### `ori.provenance`
Return source lineage, authority classification, version/supersession chain, retrieval metadata, and mapping/assertion boundaries for an object.

### `ori.verify`
Run or retrieve a declared verification against explicit inputs, requirements/rules and validator version. A verification result MUST NOT be represented as legal approval unless an authorized Decision separately creates that effect.

### `ori.analyze_precedence`
Analyze a declared precedence-graph slice. A conforming implementation must detect cycles; for acyclic slices it may return topological order, blocking/prerequisite information, parallel branches, and derived critical-path/float values when duration evidence is supplied. Derived schedule analysis does not alter source authority or statutory sequencing.

### `ori.challenge`
Create or return a first-class Challenge targeting an Assertion, MappingAssertion, Requirement interpretation, Verification, Evidence item, Decision or other declared challengeable object. Challenge creation must not mutate or erase the challenged object.

### `ori.resolve_challenge`
Append a response/disposition to a Challenge while preserving the target, original Challenge, evidence and prior responses. Protocol representation does not create legal authority for the actor issuing the disposition.

### `ori.list_profiles`
List available jurisdiction, regulatory, guidance, conformance and interoperability profiles with status, source authority and versions. Implementations may expose jurisdiction inventories through this operation or through separately discoverable inventory collections, but discovery behavior must be explicit.

## Response envelope

Model-facing operations SHOULD return a compact envelope:

```json
{
  "ok": true,
  "operation": "ori.get",
  "data": {},
  "provenance": [],
  "challenges": [],
  "warnings": [],
  "conformance": {
    "ori_version": "0.1.0-draft",
    "implementation": "openpermit-reference-node",
    "implementation_version": "0.1.0"
  }
}
```

Warnings are first-class. Missing, stale, disputed, low-confidence or source-inaccessible data should be reported rather than silently inferred.

## Model traversal rules

A conforming model client should:

1. retrieve source/authority context before presenting a regulatory claim as applicable;
2. preserve jurisdiction and effective version;
3. distinguish source-native objects from MappingAssertions and model-generated Assertions;
4. retrieve open challenges affecting a conclusion;
5. prefer deterministic verification when an applicable deterministic rule exists;
6. distinguish verification from authorized Decision;
7. preserve alternative interpretations and counter-evidence;
8. state when the graph is incomplete or when a requested fact is not represented;
9. treat GuidanceProfile controls as guidance unless a separate applicable legal source creates a Requirement;
10. treat jurisdiction inventories marked partial as evidence maps, not complete legal determinations.

## Discovery

Public ORI implementations SHOULD expose a static discovery document at:

`/.well-known/ori.json`

The document should identify:

- implementation identity and ORI version;
- model transport endpoints;
- REST/static surfaces;
- guidance profiles and jurisdiction inventories;
- schema/conformance locations;
- authorization requirements;
- capability registry location where supported.

## MCP reference tool names

The reference node currently exposes these transport-specific names without changing semantic operation names:

- `ori_capabilities`
- `ori_get`
- `ori_traverse`
- `ori_provenance`
- `ori_verify`
- `ori_analyze_precedence`
- `ori_challenge`
- `ori_resolve_challenge`
- `ori_list_profiles`

The reference-node README and smoke test must stay synchronized with this list. Tool descriptions and output schemas should be sufficient for models to understand the result shape without relying on hidden prompt instructions.

## Security boundary

Discovery may be public. Mutating or sensitive operations may require authorization. A public implementation MUST NOT assume that model identity equals legal authority or user authorization.

MCP deployments must implement transport security appropriate to the current MCP specification, including host/origin controls for Streamable HTTP deployments.
