# Open Regulatory Infrastructure (ORI) Core — v0.1 Draft

Status: **recovery-derived working draft; not released**

OpenPermit is the reference implementation. ORI is the independently implementable standard.

This draft intentionally separates:

- **source-native regulatory meaning** from normalized mappings;
- **graph semantics** from execution runtimes;
- **verification** from assertion;
- **challenge** from mutation;
- **the standard** from any particular website, model provider, cloud, database, workflow engine, or permitting vendor.

## 1. Normative design principles

A conforming ORI implementation MUST be:

1. **Addressable** — every material object has a stable identifier.
2. **Provenance-first** — authority, source, version, and evidence remain traversable.
3. **Jurisdiction-aware** — applicability is explicit, never inferred from a global vocabulary alone.
4. **Versioned in time** — effective and superseded states can be reconstructed.
5. **Challengeable** — machine or human conclusions can be challenged with evidence and receive an explicit disposition.
6. **Testable** — conformance and verification behavior is executable and reproducible.
7. **Implementation-neutral** — graph semantics do not depend on one runtime or vendor.
8. **Open to inspection** — authoritative interchange data can be viewed, validated, and audited without a proprietary runtime.
9. **Extensible without forks** — jurisdiction and domain profiles add namespaced terms while preserving the core contract.
10. **Source-preserving** — normalization never silently replaces the source term, source text, source authority, or legal effect.

## 2. Core object envelope

Every ORI object MUST support the following envelope:

```yaml
id: string                  # stable IRI/URN/URI recommended
type: string                # ORI core type or namespaced profile type
version: string             # object version
effective_from: datetime|null
effective_to: datetime|null
jurisdiction: [id...]        # zero or more explicit jurisdiction references
source: [id...]              # zero or more source/provenance references
derived_from: [id...]        # zero or more lineage references
supersedes: [id...]          # zero or more prior object versions
metadata: object             # extension-safe non-normative metadata
```

Profiles MAY add properties. They MUST NOT redefine the semantics of core properties.

## 3. Core types

### 3.1 Authority

An entity with legal, delegated, professional, organizational, or standards authority.

Examples: legislature, agency, department, code official, licensed professional, standards body.

Required semantics:

- identity;
- authority basis or source;
- scope/jurisdiction where applicable.

### 3.2 Jurisdiction

A geographic, governmental, organizational, or programmatic scope in which a rule or authority applies.

Jurisdiction hierarchy MUST be represented by relationships, not encoded only in strings.

### 3.3 Source

An addressable provenance object for authoritative or evidentiary material.

A Source SHOULD record:

- canonical locator;
- title/label;
- publisher/issuer;
- publication/effective date when known;
- version/edition;
- checksum where a retrievable artifact exists;
- license/access status;
- retrieval timestamp;
- authority classification.

### 3.4 RegulatoryInstrument

A law, regulation, code, ordinance, policy, adopted standard, permit condition, official interpretation, or other instrument capable of creating or modifying an obligation.

### 3.5 Provision

An addressable portion of a RegulatoryInstrument.

A Provision preserves source-native identifiers and citations. Derived semantic interpretation belongs in Assertions or Mappings, not in the Provision itself.

### 3.6 Requirement

A structured representation of something required, prohibited, permitted, conditional, or subject to verification.

A Requirement MUST point to the Provision(s), authority, or other source that justify it.

### 3.7 Action

An observable or executable regulatory/process action.

Examples: submit, review, verify, inspect, issue, notify, pay, record, authorize.

Action names are semantic concepts, not a replacement for jurisdiction-native terms.

### 3.8 Artifact

A document, model, plan set, image, form, dataset, certificate, receipt, message packet, or other durable evidence-bearing resource.

### 3.9 SpatialAnchor

A stable spatial reference associated with an object or evidence item.

Profiles MAY support parcel, address, world coordinate, IFC element, model object, region, route, or view context anchors.

### 3.10 Evidence

An Artifact, observation, measurement, attestation, test result, signed statement, model element, sensor output, or other resource offered in support of an Assertion, Verification, Decision, or Challenge.

Evidence SHOULD expose capture provenance and integrity information appropriate to its source.

### 3.11 Assertion

A claim made by an Actor, Authority, model, validator, mapping process, or implementation.

Assertions are not automatically facts. They remain attributable and challengeable.

Required properties:

- `subject`;
- `predicate`;
- `object` or value;
- `asserted_by`;
- provenance/source;
- optional confidence;
- optional evidence.

### 3.12 MappingAssertion

A specialized Assertion mapping one source-native term/object to another concept, vocabulary, standard, or jurisdiction representation.

Mappings MUST preserve:

- source object;
- target object;
- mapping type;
- mapper;
- evidence/rationale;
- version;
- status;
- confidence when used;
- challenge state.

A mapping is never authoritative merely because it exists.

### 3.13 Verification

A reproducible evaluation of inputs against one or more Requirements, tests, rules, schemas, or conformance conditions.

A Verification MUST identify:

- validator/implementation;
- validator version;
- input objects/artifacts;
- rule/requirement references;
- outcome;
- generated evidence or report;
- execution time;
- deterministic/non-deterministic mode where relevant.

### 3.14 Decision

A disposition by an authorized actor or process.

Examples: approved, rejected, conditionally approved, waived, accepted, denied, superseded.

A Decision MUST remain linked to its authority, subject, rationale/source, and effective time.

### 3.15 Condition

A condition attached to applicability, approval, authorization, verification, or decision.

### 3.16 Exception

An explicit exception, waiver, variance, exemption, alternate method, or other departure from a default Requirement.

An Exception MUST identify its authority and scope.

### 3.17 Challenge

A first-class objection to an Assertion, MappingAssertion, Verification, Requirement interpretation, Decision, Evidence item, or other challengeable object.

A Challenge MUST contain:

- `subject` — object being challenged;
- `challenged_by` — Actor/Authority/Agent identifier;
- `grounds` — typed or namespaced challenge basis;
- `statement` — machine/human-readable challenge statement;
- `evidence` — zero or more supporting Evidence references;
- `status` — open, answered, sustained, rejected, withdrawn, superseded;
- `created_at`;
- optional `response_to` for nested rebuttal/challenge graphs.

A challenge MUST NOT mutate or erase the challenged object. Resolution is represented by a new Disposition/Decision and graph edges.

### 3.18 Event

An immutable occurrence in the lifecycle of an ORI object or process.

Events SHOULD be append-only. Current state MAY be materialized from event history but MUST remain traceable to source events where auditability is required.

## 4. Core relationship semantics

Implementations MAY serialize edges as embedded properties or standalone Edge objects, but the following meanings are stable.

### Authority and applicability

- `issuedBy`: Instrument/Decision → Authority
- `authorizedBy`: Assertion/Decision/Exception → Authority
- `withinJurisdiction`: Object → Jurisdiction
- `appliesTo`: Requirement/Provision/Condition/Instrument → Object/Jurisdiction/Profile target

### Structure and lineage

- `contains`: Object → Object
- `derivedFrom`: Object → Source/Object
- `supersedes`: Object → prior Object
- `versionOf`: Object → canonical/version family

### Requirement and process

- `requires`: Requirement/Action → Artifact/Verification/Action/Condition
- `precedes`: Action → Action
- `blocks`: Action/Requirement → Action/Decision
- `satisfies`: Evidence/Artifact/Verification → Requirement

### Evidence and reasoning

- `asserts`: Actor/Authority/Agent → Assertion
- `supportedBy`: Assertion/Verification/Challenge/Decision → Evidence
- `justifiedBy`: Requirement/Assertion/Decision/Exception → Provision/Policy/Standard/Source
- `verifies`: Verification/Evidence → Requirement/Condition/Assertion
- `resultsIn`: Event/Verification/Review/Challenge → Decision/Action/Condition/Event

### Mapping and interoperability

- `mapsTo`: MappingAssertion → target Object
- `mapsFrom`: MappingAssertion → source Object
- `alignsWith`: Object → Object
- `exposedAs`: ORI concept → external projection/schema entity

### Challenge and governance

- `challenges`: Challenge → challengeable Object
- `respondsTo`: Challenge/Assertion/Decision → Challenge
- `resolvedBy`: Challenge → Decision/Disposition
- `sustains`: Decision → Challenge
- `rejectsChallenge`: Decision → Challenge
- `amends`: Decision/Instrument → Object

## 5. DAG and critical-path profile

ORI is a graph standard. It does **not** require the full regulatory graph to be acyclic.

A graph slice MAY declare itself a `PrecedenceGraph` when its `precedes` edges are acyclic. A conforming PrecedenceGraph implementation MUST be able to:

- detect cycles;
- produce a topological ordering;
- identify unsatisfied prerequisites;
- identify blocking nodes;
- expose parallel branches;
- when durations are supplied, compute critical path and float without authoring those derived values as source facts.

Challenge, citation, amendment, authority, mapping, and reference subgraphs MAY contain cycles.

## 6. Source-native language and semantic mappings

ORI MUST preserve source-native vocabulary. A jurisdiction term MUST NOT be replaced by a normalized term without a MappingAssertion.

Recommended chain:

```text
Source → SourceTerm/Provision → MappingAssertion → Concept/Action → Requirement/Process Edge
```

This allows two jurisdictions to interoperate without pretending that similar words have identical legal effect.

## 7. Verification versus authority

A passing automated Verification means only that the declared inputs passed the declared checks under the declared validator/version.

It MUST NOT be serialized as legal approval unless a separately addressable authorized Decision creates that effect.

Similarly, a model-generated interpretation is an Assertion until accepted by a relevant authority or otherwise given effect by applicable law/process.

## 8. Challenge protocol

A conforming implementation MUST support at least these operations semantically, regardless of transport:

1. retrieve the challenged object;
2. retrieve its provenance, authority, source and effective version;
3. retrieve evidence and prior verifications;
4. create a Challenge without altering the source object;
5. attach counter-evidence or alternative MappingAssertions;
6. issue a response or Decision;
7. preserve the full thread/history;
8. query unresolved challenges affecting an object.

## 9. Conformance levels

### ORI-Core

- parse and emit the core object envelope;
- preserve unknown namespaced extensions;
- stable identifiers;
- provenance/source relationships;
- jurisdiction/effective-time semantics;
- Assertion, Verification, Decision, Challenge;
- JSON representation conforming to the published schema.

### ORI-Graph

Includes ORI-Core plus:

- typed edge traversal;
- cycle-safe traversal;
- lineage and supersession queries;
- challenge traversal;
- precedence-graph cycle detection and topological order.

### ORI-Model Interface

Includes ORI-Graph plus machine-discoverable operations for:

- inspect/get;
- traverse;
- verify;
- challenge;
- list capabilities/profiles;
- retrieve provenance;
- retrieve conformance metadata.

MCP is the initial reference model transport, not the ontology itself.

### ORI-Reference Node

Includes ORI-Model Interface plus a runnable local reference implementation with useful defaults and no mandatory third-party SaaS account.

## 10. Governance boundary

The core specification is governed through public version history, conformance fixtures, reproducible tests, challenge/issues, and transparent provenance.

No implementation, certification provider, cloud, standards body, model provider, municipality, or OpenPermit deployment is the exclusive source of truth for ORI itself.

## 11. Recovery lineage

This draft draws from recovered OpenPermit/NFL/NGL work including:

- 2025 domain ontology and typed relationships;
- standards grounding and JSON-LD/SHACL work;
- OpenPermit edge-logic model;
- legal/IFC crosswalks;
- NIEM and BLDS alignment;
- append-only audit and remote inspection work;
- historical seven-verb NFL work;
- NGL critical-path semantics;
- 2025 PR #103 ontology-first civic runtime;
- geo-attested inspection evidence work;
- Virginia system/authority inventory;
- recovered Virginia/Texas/Washington lexical crosswalk research.

The **Challenge** core type and challenge-governance requirements are promoted explicitly in this reboot because challengeability is a required property of open regulatory infrastructure.
