# OpenPermit recovery inventory — 2026-09-01

Status: evidence inventory before redesign.

## Reboot position

**OpenPermit is open regulatory infrastructure.** Permitting is a reference application of a broader, vendor-neutral substrate for representing, traversing, verifying, challenging, and governing regulatory requirements.

The public surface should be permissionless, model-native, standards-based, maximally discoverable, challengeable, testable, and runnable with minimal configuration. Human websites are documentation and inspection surfaces; models and programmatic interfaces are first-class delivery mechanisms.

## Recovered foundations

The repository was heavily reduced on the current `test` branch, but substantial earlier work remains reachable through historical branch refs and commit objects. Do not rewrite these ideas from memory; recover, test, and promote what survives.

| Recovered capability | Evidence | Disposition |
|---|---|---|
| Domain ontology with `Regulation`, `Agency`, `Permit`, `Inspection`, `Condition`, `Stakeholder`, `Location`, `Project`, and permit dependency relationships | blob `0a8873dfffd4e65c6a15ec682b39bf0fb7536840` reachable from commit `afc139ff02e34d71218caf446af40c1819ccb87a` | **KEEP / normalize** |
| Graph nodes with typed relationships and duplicate-edge prevention | commit `b2e5f00f95f225ac7e1d0cd39b39c7b4cda7540b`, `src/core/node.js` | **KEEP concept / reimplement tests-first** |
| Standards crosswalk: BLDS, IFC, GeoJSON, ISO 20022, CityJSON, InfraGML, JSON-LD, OData, RDF/OWL, SHACL | blob `a64c57f56d5e3d876113d8944564c63e6702970e` | **KEEP / revalidate current standards** |
| Jurisdiction profile expressed as JSON-LD with permit types, required documents, and property fields | `Virginia/spotsylvania.json`, blob `a3108c4389d878909aea1a20a701cde3fb606a93` | **KEEP as profile precedent** |
| Legal requirement → IFC entity/property → executable model check crosswalk | commit `afc139ff02e34d71218caf446af40c1819ccb87a`, `docs/legal_standards_mapping.md` | **KEEP / strengthen provenance** |
| IFC schema, geometry, rule, and local-code validation workflow | blob `7d030ec735d39140e0f129e7ae0338bd43ed14ae`, `docs/ifc_approval.md` | **KEEP / move under verification profile** |
| NIEM 6.0 mapping with augmentation while preserving original NIEM tags for round-tripping | commit `13eed65e2fb5ed264c5e84c7b8a079adc587fc8c`, `docs/niem-alignment-6.0.md` | **KEEP / revalidate current NIEM** |
| JSON-LD workflow tied to BLDS and IFC | commit `0294aa7f5aa9686a11d4d0c45514af02d1307b06`, `workflow/workflow.jsonld` | **KEEP concept / convert sequence to graph semantics** |
| Append-only audit trail integrated with submissions and validation | commit `7fb046263694922666e34f3d1e9605249411d5ba` | **KEEP principle / replace prototype implementation** |
| Geo-tagged remote inspection evidence with validation and AI hook | commit `54496caf7a6d3aaf42095b536d9124964a6168e2` | **KEEP concept / expand to attestation** |
| Earlier architecture already separated workflow, validation, ontology DB, event store, agency APIs, GIS/BIM clients, NIST controls, audit and encryption | blob `1e5db92aad7f441ad8a4880c9616b4d43e367d71` | **MINE concepts / do not revive service sprawl blindly** |
| Actor inventory covering consumer, builder, specialty contractor, municipal reviewer/inspector | blob `46227973997488402024d60bf2059d79a3874c18` | **KEEP actors / generalize beyond permitting** |

## Historical refs still reachable

The current repo still exposes a large set of old branch heads, including branches for legal standards mapping, NIEM integration, ontology generation, IFC validation, open-data scaffolding, audit trails, remote inspection, CKAN bridging, JSON-LD workflow work, EPA import, and graph relationship validation. These branch tips are recovery sources even where the corresponding files no longer exist on `test`.

The `master` branch is a separate one-commit root from 2025-12-12 and is **not** a substitute for the older May–June 2025 branch history. The current default `test` branch is intentionally minimal (`index.html`, `.gitignore`, `.github/`).

## Not yet recovered

These were discussed in prior work but have **not yet been proven from reachable GitHub evidence in this pass**:

- Washington State regulatory-structure inventory.
- Texas regulatory-structure inventory.
- Full linguistic/verb study across jurisdictions.
- A formal proof or implementation of approval as a directed acyclic graph with critical-path properties.
- The secure open-hardware specification for geocoded artifact generation.
- A complete third-party attestation-layer specification.

Search local clones, forks, CI artifacts, Drive research, archived exports, and other repositories before recreating them.

## Direction established in this reboot

### 1. Stable normative core; extensible domain profiles

Define only the contracts that must remain stable across jurisdictions and implementations:

- identity and canonical addressing;
- authority and jurisdiction;
- source/provenance and version;
- regulatory object semantics;
- actor/role semantics;
- evidence and attestation;
- dependency and applicability edges;
- verification result semantics;
- challenge/counterclaim semantics;
- supersession and effective-time semantics;
- conformance behavior.

Everything domain-specific belongs in profiles and mappings. Do not force every agency or jurisdiction into one giant vocabulary.

### 2. Regulations and approvals are traversable graphs

The system must represent regulatory obligations, evidence, dependencies, approvals, conditions, exceptions, challenges, counterclaims, and decisions as addressable graph objects.

A permit is one traversal through that infrastructure, not the infrastructure itself.

Where an approval process is acyclic, expose DAG properties including prerequisites, independent branches, blocking nodes, topological order, and critical path. Do not assume every regulatory relationship is acyclic; challenge, amendment, precedent, and cross-reference graphs may contain cycles and need explicit semantics.

### 3. Challengeability is part of verification

Every machine conclusion must be challengeable. A model or practitioner must be able to ask:

- What authority supports this requirement?
- Which version and jurisdiction apply?
- What evidence satisfied it?
- What assumptions were used?
- What alternative interpretation exists?
- What counter-evidence or exception applies?
- What would change the outcome?

Challenges are first-class graph objects with provenance and disposition, not comments outside the model.

### 4. Models are a primary interface

Expose one canonical graph through multiple equivalent interfaces:

- MCP as a first-class model interface;
- REST/HTTP for general clients;
- JSON-LD/RDF-compatible object representations;
- graph query/traversal surfaces;
- static, crawlable human documentation;
- downloadable conformance fixtures.

No interface may become the proprietary source of truth.

### 5. Runnable, low-friction reference node

A conforming OpenPermit node should run locally from a container with useful defaults and no mandatory SaaS account. Configuration may specialize jurisdiction, sources, persistence, identity, or compute, but the node must boot into a functional reference mode without a configuration ceremony.

### 6. Open compute federation is optional but operational

Specialists, jurisdictions, vendors, universities, cloud providers, and model providers should be able to register specialized validators or compute capabilities. The network must not require centralized permission to participate. Registry, capability description, provenance, isolation, and conformance tests are required so outside compute can be used without becoming trusted by default.

### 7. Jurisdictional sovereignty is preserved

The infrastructure maps and verifies what an authority actually adopted. It does not silently replace law, code officials, agencies, departments, or appeal rights. Jurisdictions can publish native profiles, adopt shared profiles, or map existing systems through adapters.

### 8. Reference standards; do not counterfeit authority

Where standards or codes are copyrighted or licensed, store identifiers, mappings, transforms, tests, derived facts where lawful, and links/provenance to authorized sources. Do not make OpenPermit's convenience representation masquerade as authoritative legal text.

### 9. Governance is open and evidence-driven

No certification cartel and no ownership gate. Governance should operate through public versions, test vectors, issue/challenge records, transparent provenance, and reproducible conformance results. Implementations can disagree while remaining interoperable.

### 10. OpenPermit is the reference implementation

The standard must be implementable independently. OpenPermit demonstrates that the interfaces, graph semantics, profiles, challenge system, and conformance suite actually run.

## Federal policy anchors for this reboot

These are policy context, **not a claim that OpenPermit is endorsed by Treasury or the White House**.

- U.S. Treasury, Secretary Scott Bessent, *Remarks before the American Bankers Association* (2025-04-09): regulation should derive from clear statutory mandate, balance costs and benefits, be fair and consistently applied, and regulators themselves should be efficient. https://home.treasury.gov/news/press-releases/sb0078
- OIRA Memorandum M-25-28, *Guidance Implementing the President's Memorandum Directing the Repeal of Unlawful Regulations* (2025-05-07): agency review of regulatory inventories against statutory authority and controlling legal precedent. https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-28-Guidance-Implementing-the-Presidents-Memorandum-Directing-the-Repeal-of-Unlawful-Regulations.pdf
- Presidential Memorandum, *Directing the Repeal of Unlawful Regulations* (2025-04-09): review and reasoned disposition of existing regulations under statutory and constitutional authority. https://www.whitehouse.gov/presidential-actions/2025/04/directing-the-repeal-of-unlawful-regulations/

## Immediate next recovery pass

1. Enumerate every historical branch head and classify by concept, not agent/branch name.
2. Build a commit-to-capability index with source SHA, files, date, and survival status.
3. Search other CORELOT repositories for `OpenPermit`, `NFL`, `NIEM`, `BLDS`, `regulation`, `jurisdiction`, `approval`, `DAG`, `attestation`, `geocode`, `challenge`, and `prescriptive`.
4. Search persistent documents/Drive for the Washington, Texas, linguistic, legal-structure, and hardware research.
5. Recover only source artifacts into a quarantined `recovered/` tree; do not merge prototype code into the new core yet.
6. From that inventory, draft the normative ORI object model and conformance tests.

**Rule: mine first; normalize second; implement third.**
