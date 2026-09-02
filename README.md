# OpenPermit

**OpenPermit is the reference implementation of Open Regulatory Infrastructure (ORI): an open, machine-readable substrate for regulatory inventory, provenance, traversal, verification, measurement, challenge, and governance.**

Permitting is the first reference application. ORI is designed to be independently implementable across jurisdictions, regulatory domains, vendors, cloud providers, model providers, and workflow engines.

## What is live

- `CHARTER.md` — mission, governance boundary, federal implementation target, and release principles.
- `spec/ori-core-0.1-draft.md` — recovery-derived ORI Core v0.1 working specification.
- `spec/ori-core-0.1.schema.json` — executable JSON Schema surface.
- `profiles/federal/hud-home-construction-best-practices-2026.json` — first machine-readable guidance profile.
- `conformance/` — fixtures and executable conformance harness.
- `recovered/` — quarantined historical source material retained for provenance and comparison.
- `.well-known/ori.json` — machine discovery document.
- `llms.txt` — concise model-facing map of the public corpus.

## Core model

```text
jurisdiction -> approval -> authority -> requirement -> evidence
             -> reviewer -> deadline -> fee -> status -> decision

source -> provision -> mapping assertion -> concept/action
       -> requirement -> verification -> decision
                           |
                           +-> challenge -> evidence -> disposition
```

A passing automated verification is not legal approval. A normalized mapping is not authoritative merely because it exists. Source-native terms, authority, versions, evidence, and challenges remain traversable.

## Federal implementation target

The first public profile maps HUD's 2026 *State and Local Best Practices for Home Construction* into computable implementation controls and measurable evidence. The profile treats HUD recommendations as federal guidance, not binding local law and not an endorsement of OpenPermit.

Pattern:

```text
HUD practice -> implementation control -> evidence -> measurement -> alignment result
```

This supports transparent questions such as:

- Are all required permits, approvals, inspections, and fees published?
- Which reviews appear duplicated or serial when they could be parallel?
- What deadlines and tolling events exist, and how does actual performance compare?
- Which third-party credentials and attestations are accepted?
- What is the documented dispute path and how long does resolution take?

## Conformance

```bash
python -m pip install -r conformance/requirements.txt
python conformance/validate.py
```

Schema conformance proves only that an object satisfies the declared ORI structural contract. It does **not** prove legal correctness, jurisdictional applicability, factual truth, or regulatory approval.

## Design rules

1. Permissionless implementation.
2. Stable, addressable objects.
3. Source-preserving mappings.
4. Explicit authority and jurisdiction.
5. Effective-time and supersession history.
6. Graph-native dependencies and evidence.
7. First-class challenges and counter-evidence.
8. Deterministic verification where possible; assisted interpretation where necessary.
9. Human authority preserved where law/process requires it.
10. Model-native interfaces, with MCP as the initial reference transport.
11. REST/JSON-LD/graph interfaces remain equivalent public surfaces.
12. No proprietary runtime is required to view, validate, or audit authoritative interchange data.

## Open ecosystem

Participation is open to jurisdictions, agencies, standards bodies, code officials, builders, engineers, inspectors, universities, maintainers, civic-tech groups, AI/model providers, cloud providers, permitting vendors, material/manufacturing suppliers, and specialist validators.

Contributors do not need permission to implement ORI. Specialized validators and compute providers are not trusted by default; capability descriptions, provenance, isolation, and conformance evidence are part of the contract.

See `CONTRIBUTING.md` and `GOVERNANCE.md`.

## Licensing

Software code is released under Apache-2.0. Original ORI specifications, schemas, profiles, examples, and documentation are intended for unrestricted public reuse under the notice in `LICENSE-SPEC.md`. Third-party standards, regulations, model codes, and referenced source materials retain their own legal status and licenses; OpenPermit does not redistribute copyrighted model-code text without rights.

## Status

This is a public working standard and reference implementation. The v0.1 core is intentionally draft and challengeable. Provenance is preserved, tests are executable, and incompatible assumptions should be surfaced as issues or machine-readable challenges rather than hidden in implementation code.
