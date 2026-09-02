# OpenPermit email source map — 2026-09-01

Status: recovery evidence. This document records architectural and research artifacts found in the project email archive. It intentionally omits recipient addresses and personal contact data.

## Why this matters

The email archive confirms that the current Open Regulatory Infrastructure (ORI) direction is not a clean-room redesign. Several of the ideas now being normalized were already explored, circulated, attached, or implemented in 2025–2026. The correct move is to recover and reconcile them before freezing a new core.

## High-value recovered email sources

### 1. CORELOT Security & NFL Implementation — 2025-06-30

Gmail message: `197c127358a17369`

Recovered attachments:

- `Nfl Open Permit Edge Logic Whitepaper.pdf`
- `Nfl Roll-out Plan – Corelot.pdf`
- `Nfl Standards Grounding Plan.pdf`
- `Corelot Security Policy V1.pdf`

Recovered architectural direction:

- NFL/OpenPermit was already being packaged toward near-one-click container execution.
- OpenPermit and OpenTax were reference applications on a shared graph/standards substrate.
- Standards were proposed as first-class nodes with source, version, checksum, licensing, and provenance.
- Standards relationships included `supersedes`, `extends`, `alignsWith`, `implements`, and `references`.
- JSON-LD was the canonical linked-data representation; SHACL was proposed for deterministic conformance validation.
- The deck-permit workflow was explicitly proposed as the first end-to-end standards-grounding exemplar.
- AI/model assistance could help map rules, but deterministic validation remained the verifier.
- Runtime direction included Docker/Kubernetes, WASM, CI/CD, relational + graph storage, SBOM/SLSA provenance, and a plugin/extension model.

**ORI disposition:** preserve standards-as-nodes, provenance, executable conformance, and low-friction packaging. Re-evaluate implementation dependencies before making any runtime normative.

### 2. Open Permit lifecycle — 2025-06-12

Gmail message: `19762473c922e3d1`

Recovered lifecycle:

1. submit a single structured package containing forms, documents, IFC and GIS data, or interact through an AI interface;
2. schema-first validation using shared vocabularies;
3. IFC/model verification with machine-readable results;
4. permit-by-rule for eligible low-risk paths;
5. remote inspections using geotagged evidence and model comparison;
6. standards-based interoperability and open APIs;
7. containerized reference deployment with role-aware security.

**ORI disposition:** retain the data/evidence/validation chain. Treat the old hosted-application framing as historical; the reboot standard is permissionless and implementation-neutral.

### 3. Virginia Permitting Deep Research 2025

Gmail message: `199bf6a5df4a3aa0`
Attachment: `Virginia_Permitting_Deep_Research_2025_fixed.pdf`

Recovered inventory:

- authority/system inventory across DHCD, DEQ, VMRC, USACE and representative local permitting systems;
- cross-agency Joint Permit Application flow for state/federal water impacts;
- BLDS-oriented common permit fields plus local enhancements;
- jurisdictional and geospatial fields;
- IFC entity references;
- environmental/JPA-specific fields;
- explicit recommendation to normalize local form fields, map all locality portals, publish reusable datasets, and harmonize vendor APIs.

**ORI disposition:** this is concrete precedent for an **authority inventory + jurisdiction profile + source-system adapter** model. Do not encode one Virginia super-schema into the core; encode the mapping machinery and retain Virginia as a profile/corpus.

### 4. NFL / OpenPermit edge logic — 2025-06-27

Recovered through the 2025-06-30 email attachment set and Drive copy.

The edge model already treated relationships as executable first-class assets with:

- source and target;
- edge type;
- attributes;
- validity interval;
- provenance and evidence;
- access-control metadata;
- machine-readable schema and tests;
- namespaced jurisdictional extension.

Representative relationships included `contains`, `part_of`, `issued_by`, `governed_by_standard`, `applies_for`, `reviews`, `approves`, `requires_document`, `requires_inspection`, `scheduled_for`, `supersedes`, `charges_fee`, `pays`, `derived_from`, and `version_of`.

**ORI disposition:** this is a direct predecessor of the ORI edge contract. Add challenge, counterclaim, authority, applicability and conformance semantics rather than starting over.

### 5. Serverless DAG / workflow-engine discussion — 2025-10-17 and 2025-10-31

Gmail messages:

- `199f26ce6b508ee9` — explicit proposal: “Serverless DAG architecture”.
- `19a3ba1a0d415558` — consideration of Temporal as an open-source workflow engine instead of building a DAG executor from scratch.

**ORI disposition:** the DAG idea is historically grounded. Keep precedence/approval DAG semantics in the standard while keeping the execution engine pluggable. Temporal, serverless functions, Kubernetes jobs, WASM, or another runtime may execute a conforming graph; none should define the graph.

### 6. Inspection communications + geo-attested evidence — 2025-11-21 through 2025-11-24

Gmail messages:

- `19aa7ada99c3a4d1` — inspection communications memo.
- `19ab81ad239bcc8f` — follow-up proposing geo-located erosion/sediment evidence and future autonomous capture.

Recovered concepts:

- one authoritative inspection communication/event thread;
- correction notes, approvals, follow-ups, fees, scheduling and attestation bound to that thread;
- JSON-LD metadata for permit, inspection type, location, reviewer and required action;
- handheld geo-attested devices as evidence collectors;
- future field capture using smart-post/drone hardware and on-device inference.

**ORI disposition:** evidence collection is a first-class profile. A full open-hardware attestation specification has not yet been recovered, but the functional requirements are no longer speculative.

### 7. Ontology-first civic runtime PR trail — December 2025

GitHub notification email: `19b486a48dde097c`
Related unmerged PR: `corelotorg/OpenPermit#103`, head `4c91972ba51c126c1ad2f23692bfc3105e55fe78`.

Recovered design includes:

- modular ontology domains for authority, jurisdiction, built assets, permit/application, review/decision, codes/policies, inspections, finance, artifacts, communication and integration;
- explicit `Assertion`, `Event`, `SpatialAnchor`, `Confidence`, `Authority`, `Jurisdiction`, `Requirement`, `Verification`, `Standard`, `CommunicationThread`, `Adapter` and related classes;
- typed provenance, authority, targeting, review, inspection, finance, communication and integration edges;
- JSON-LD context + YAML ontology source;
- anti-lock-in civic runtime policy;
- dynamic documentation derived from ontology/OpenAPI/MCP surfaces.

**ORI disposition:** this is the strongest near-term source for the new normative object model. Recovered source files are quarantined under `recovered/pr-103/` for comparison, not automatically promoted to the new core.

### 8. Linguistic / regulatory-language precursor

Gmail message: `197c8a30b49dfc11`
Related issue: `SheetPros/OpenTax#4`, “Treasury Workflow Language”.

Recovered design themes:

- an Esperanto-style cross-domain vocabulary;
- minimal composable semantic primitives;
- formal grammar for unambiguous regulatory statements;
- regulatory lexicon crosswalks;
- NGL as the graph substrate.

Separately, historical NGL commit `b23c7788d039f07b65ef05b96432ecbc8b7ffd39` exposes the earlier seven-verb NFL vocabulary: `node`, `edge`, `trait`, `pack`, `fn`, `impl`, `@call`.

**ORI disposition:** linguistic work exists and must be reconciled before freezing ORI predicates. Do not assume the historical seven verbs are themselves the regulatory vocabulary; distinguish graph-language syntax from regulatory-domain predicates.

### 9. Outreach / ecosystem inventory — November 2025

Gmail message: `19a3f87d2e629f1f`
Attachment: `OpenPermit_RoundRobin_Matrix_Full (1).pdf`

Recovered landscape categories:

- government-led permitting modernization;
- nonprofit and policy organizations;
- open-source projects;
- incumbent/private permitting platforms;
- individual practitioners and reform leaders.

**ORI disposition:** use this as an ecosystem/source registry seed, not as an endorsement list. Revalidate every organization/program before current outreach.

## Historical concepts now confirmed

The following are no longer “memory-only” concepts:

- graph-native permitting/regulatory modeling;
- typed edges with provenance and validity;
- executable validation and conformance tests;
- standards as first-class nodes;
- jurisdiction-aware extension without forks;
- DAG/critical-path workflow thinking;
- model/AI interfaces separated from deterministic verification;
- geolocated/attested inspection evidence;
- open, containerized reference deployment;
- authority/jurisdiction/code citation ontology;
- communication threads as event streams rather than the legal record itself;
- anti-lock-in/open-format policy;
- linguistic/semantic distillation as a cross-domain research track.

## Still incomplete

Continue recovery before freezing the normative core:

- full Texas regulatory inventory;
- full Washington regulatory inventory;
- original cross-jurisdiction linguistic study and measurements;
- complete secure open-hardware attestation specification;
- complete challenge/appeal/counterclaim ontology, if one existed;
- definitive reconciliation of NFL v0 seven verbs, current NGL/NFL grammar, and ORI domain predicates.

## Recovery rule

**Recover evidence → classify source authority → normalize semantics → write conformance tests → promote into the standard.**
