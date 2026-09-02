# OpenPermit recovery status — 2026-09-01

This is the current status after mining historical GitHub objects, the NGL repo, Google Drive, and the project email archive. `RECOVERY-INVENTORY-2026-09-01.md` remains the initial snapshot; this file records what was resolved afterward.

## Recovered after the initial inventory

### Cross-jurisdiction linguistic work

Recovered Drive source: `1uSx3PO7N3z6jI6T-ZqQ7cRQlk8cfb9k0EJ8-3YTYoVM` (“Scale structured lexical research.”).

It contains candidate Virginia/Texas/Washington terminology crosswalks, a Florida comparison, and an action/verb-oriented semantic-bridge hypothesis.

Disposition: **recovered as historical research, not validated authority.** The legal citations, mappings and performance claims require primary-source verification. Quarantined summary: `recovered/drive/three-state-lexical-research.md`.

### DAG and critical-path work

Recovered:

- NGL critical-path model with `precedes`, `duration`, derived `float`, and longest-duration critical-path traversal;
- 2025 email explicitly proposing a serverless DAG architecture;
- later email considering Temporal as an execution engine rather than inventing a DAG runtime.

Disposition: **resolved as a real historical design line.** ORI can make precedence/DAG semantics normative while keeping the execution engine pluggable.

### Ontology-first civic runtime

Recovered unmerged OpenPermit PR #103 head `4c91972ba51c126c1ad2f23692bfc3105e55fe78`.

Key files preserved under `recovered/pr-103/`:

- `ontology-specification.md`
- `node-relationships.md`
- `civic-runtime-stack.md`
- `ontology.jsonld`
- `ontology-index.yaml`

Disposition: **primary comparison corpus for the new ORI object model**, not automatically normative.

### Geo-attested inspection evidence

Recovered email requirements for handheld geo-attested inspection evidence, authoritative inspection communication threads, and future smart-post/drone capture, plus the current `corelot-field-collector` geolocation/media evidence pipeline.

Disposition: functional requirements are confirmed; a complete open-hardware attestation specification remains missing.

### Email archive

Source inventory added:

- `docs/EMAIL-SOURCE-MAP-2026-09-01.md`
- `recovered/email-source-index.json`

The archive confirms standards-as-nodes, JSON-LD/SHACL grounding, near-one-click container deployment, DAG/runtime exploration, geo-attested evidence, and ontology-first work.

## ORI work now started

The recovery is sufficiently strong to begin a **draft** normative core without pretending the inventory is complete.

Added:

- `spec/ori-core-0.1-draft.md`
- `spec/ori-core-0.1.schema.json`
- `conformance/fixtures/challenge-valid.json`
- `conformance/fixtures/mapping-valid.json`
- `conformance/fixtures/verification-valid.json`
- `conformance/validate.py`
- `conformance/requirements.txt`
- `.github/workflows/ori-conformance.yml`

The draft promotes **Challenge** to a first-class core object and explicitly separates source-native terms, mapping assertions, verification results, authority decisions, and challenge/disposition history.

## Still missing or incomplete

- Complete Washington authority/process/form inventory.
- Complete Texas authority/process/form inventory.
- Original quantitative linguistic measurements, if any existed beyond the recovered qualitative crosswalk.
- Complete secure geocoded open-hardware attestation specification.
- Complete third-party attestation/federated-verifier specification.
- Historical challenge/appeal/counterclaim ontology, if one existed.
- Full historical branch/commit-to-capability catalogue.
- Primary-source revalidation of standards, legal citations, licensing assumptions, and current external programs.

## Next engineering slice

1. Add negative conformance fixtures.
2. Implement graph referential-integrity validation.
3. Implement precedence-graph cycle detection/topological order/critical path.
4. Define the Challenge response/disposition state machine and invariants.
5. Define a model-interface capability document and initial MCP reference surface.
6. Package the conformance harness and a minimal local graph into the first zero-ceremony reference-node container.

**Invariant:** source evidence is preserved; normalization is challengeable; runtime is replaceable; conformance is executable.
