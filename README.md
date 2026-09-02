# OpenPermit — Open Regulatory Infrastructure

**OpenPermit is the reference implementation of Open Regulatory Infrastructure (ORI): an open, machine-readable substrate for regulatory inventory, provenance, traversal, verification, measurement, challenge, and governance.**

This repository is the current ORI/OpenPermit project. It is not the legacy 2016 OpenPermit API, a municipal open-data project with a similar name, or the real-estate phrase “open permit.”

Permitting is the first reference application. ORI is independently implementable across jurisdictions, regulatory domains, vendors, cloud providers, model providers, databases, workflow engines and clients.

**Live public corpus:** https://corelotorg.github.io/OpenPermit/

## 30-second cold-clone path

```bash
git clone https://github.com/corelotorg/OpenPermit.git
cd OpenPermit
python -m pip install -r conformance/requirements.txt -r reference-node/requirements.txt
python conformance/validate.py
python -m pytest -q reference-node/test_graph.py
python reference-node/smoke.py
```

Run the local reference node:

```bash
python reference-node/server.py
```

Or containerize it:

```bash
docker build -f reference-node/Dockerfile -t openpermit-ori .
docker run --rm -p 8000:8000 openpermit-ori
```

Reference mode requires no SaaS account, database, API key or model provider.

## Public v0.1 working corpus

- `CHARTER.md` — mission, legal/governance boundaries, federal implementation targets and release principles.
- `spec/ori-core-0.1-draft.md` — recovery-derived ORI Core semantics.
- `spec/ori-core-0.1.schema.json` — executable core JSON Schema.
- `spec/ori-guidance-profile-0.1.schema.json` — executable policy/guidance-profile schema.
- `spec/ori-jurisdiction-inventory-0.1.schema.json` — executable jurisdiction-inventory schema.
- `spec/model-interface-0.1-draft.md` — model-native operations; MCP is the initial reference transport.
- `spec/precedence-graph-0.1-draft.md` — acyclic process slices, topological order, blocking, critical path and float.
- `spec/challenge-protocol-0.1-draft.md` — first-class challenges and append-only dispositions.
- `spec/evidence-attestation-0.1-draft.md` — portable evidence, geo-attestation and open-hardware semantics.
- `spec/capability-registry-0.1-draft.md` — permissionless validator/adapter/model/compute discovery; registration is not trust.
- `profiles/federal/hud-home-construction-best-practices-2026.json` — HUD home-construction best-practices implementation profile.
- `profiles/federal/regulatory-inventory-2025.json` — federal regulatory-inventory/review policy-context profile.
- `profiles/jurisdictions/us/va/fredericksburg/residential-new-construction-2026.json` — first source-cited real-jurisdiction inventory.
- `reference-node/` — zero-ceremony MCP/HTTP reference implementation and container.
- `conformance/` — positive schema fixtures, negative semantic fixtures and executable conformance harness.
- `recovered/` — quarantined historical source material retained for provenance and comparison, not normative authority.
- `.well-known/ori.json` — machine discovery document.
- `llms.txt` — concise model-facing map of the public corpus.
- `docs/ECOSYSTEM.md` — open ecosystem and compute activation.

## Core model

```text
jurisdiction -> approval -> authority -> requirement -> evidence
             -> reviewer -> deadline -> fee -> status -> decision

source -> provision -> mapping assertion -> concept/action
       -> requirement -> verification -> decision
                           |
                           +-> challenge -> evidence -> disposition
```

A passing automated verification is not legal approval. A normalized mapping is not authoritative merely because it exists. Source-native terms, authority, versions, evidence, alternatives and challenges remain traversable.

## First real jurisdiction inventory

The Fredericksburg, Virginia residential-new-construction profile demonstrates the inventory primitive against current official City and Virginia sources. It records published authority, application inputs, selected fees, a non-exhaustive inspection slice, appeal context and a simplified precedence graph while explicitly listing what remains unknown or project-specific.

It intentionally does **not** claim to be a complete parcel-specific legal determination.

## Federal implementation targets

### HUD 2026 home construction

The first federal guidance profile maps HUD’s 2026 *State and Local Best Practices for Home Construction* into computable implementation controls and measurable evidence. It treats HUD recommendations as federal guidance, not binding local law and not an endorsement of OpenPermit.

```text
HUD practice -> implementation control -> evidence -> measurement -> alignment result
```

### Federal regulatory inventory and review

A separate policy-context profile captures the inventory/review pattern from Executive Order 14219, the April 9, 2025 Presidential Memorandum, OIRA M-25-28, and Secretary Bessent’s April 9, 2025 financial-regulation principles. Those federal executive-branch and Treasury contexts are not converted into state/local legal mandates.

## Model interface

The reference node exposes semantic equivalents of:

- `ori.capabilities`
- `ori.get`
- `ori.traverse`
- `ori.provenance`
- `ori.verify`
- `ori.analyze_precedence`
- `ori.challenge`
- `ori.resolve_challenge`
- `ori.list_profiles`

MCP Streamable HTTP is the initial reference transport. Static HTTP, JSON, JSON-LD-compatible representations, REST-compatible projections and graph traversal remain equivalent public surfaces.

## Conformance

```bash
python conformance/validate.py
python -m pytest -q reference-node/test_graph.py
python reference-node/smoke.py
```

The harness now proves both acceptance and rejection behavior. Negative fixtures must reject at least these violations:

- mapping semantics serialized as source fact rather than `MappingAssertion`;
- guidance silently promoted to a binding `Requirement`;
- a challenge mutating the object it challenges;
- a cyclic graph declared as a `PrecedenceGraph`.

Schema and interface conformance do **not** prove legal correctness, jurisdictional applicability, factual truth, professional authority or regulatory approval.

## Design rules

1. Permissionless implementation.
2. Stable, addressable objects.
3. Source-preserving mappings.
4. Explicit authority and jurisdiction.
5. Effective-time and supersession history.
6. Graph-native dependencies and evidence.
7. First-class challenges and counter-evidence.
8. Deterministic verification where possible; assisted interpretation where necessary.
9. Human/legal authority preserved where applicable process requires it.
10. Model-native interfaces without model-provider lock-in.
11. No proprietary runtime is required to view, validate or audit authoritative interchange data.
12. Outside validators/compute are discoverable but not trusted by default.

## Open ecosystem

Participation is open to jurisdictions, agencies, standards bodies, code officials, builders, engineers, inspectors, universities, civic-tech maintainers, AI/model providers, cloud providers, permitting vendors, manufacturers, suppliers and specialist validators.

Contributors do not need permission to implement ORI. See `CONTRIBUTING.md`, `GOVERNANCE.md` and `docs/ECOSYSTEM.md`.

## Licensing

Software code is released under Apache-2.0. Original ORI specifications, schemas, profiles, examples, fixtures and documentation are dedicated for public reuse under `LICENSE-SPEC.md` (CC0 1.0 Universal intent), subject to third-party rights. OpenPermit does not redistribute copyrighted model-code or third-party standards text without rights.

## Status

This is a **public working draft and reference implementation**, not a claim of interchange maturity or government endorsement. v0.1 is intentionally challengeable. Provenance is preserved, tests are executable, and incompatible assumptions should be surfaced as issues or machine-readable challenges rather than hidden in implementation code.
