# Contributing to OpenPermit / ORI

OpenPermit is built as an open regulatory substrate, not a closed permitting product. Anyone may read, fork, implement and challenge ORI; no permission is needed. Pull requests from anyone are reviewed on evidence, testability and provenance, not affiliation.

ORI's scope is single-family new homes. Machine output is evidence for a human reviewer, never approval, and missing information yields `unknown`, never `fail`.

## High-value contributions

- **Jurisdiction inventories:** approvals, authorities, requirements, fees, deadlines, review/inspection paths, exceptions, and dispute mechanisms.
- **Source mappings:** source-native terminology mapped through explicit `MappingAssertion` objects.
- **Regulatory profiles:** housing, environmental, zoning, building, infrastructure, licensing, finance, or other domains.
- **Verification rules:** deterministic checks with declared inputs, source citations, versions, outputs, and reproducible fixtures.
- **Evidence formats:** documents, BIM/IFC references, geospatial anchors, images, measurements, sensor outputs, credentials, attestations, and inspection records.
- **Challenge cases:** counterexamples, ambiguous provisions, competing interpretations, stale mappings, contradictory sources, or test vectors that expose a failure.
- **Adapters:** mappings for existing government systems, permitting vendors, standards vocabularies, APIs, and data formats.
- **Model interfaces:** MCP tools/resources, REST projections, JSON-LD contexts, graph query surfaces, and model traversal tests.
- **Compute capabilities:** specialized validators or inference services with explicit provenance, isolation, versioning, and conformance metadata.
- **Open hardware:** secure capture/attestation designs for geo-located regulatory evidence.

## Contribution rules

1. Preserve the source. Do not replace source-native terms with normalized terms without an explicit mapping.
2. Cite authority and version. Regulatory claims need an addressable source and applicability context.
3. Separate fact from interpretation. Model output and derived mappings are assertions until supported or accepted by the relevant authority/process.
4. Add tests for normative behavior. If a contribution changes machine semantics, include positive and negative fixtures.
5. Keep challengeability. A contribution must not remove the ability to inspect provenance, alternatives, counter-evidence, or history.
6. Do not redistribute licensed model-code or third-party standards text without rights.
7. Do not imply endorsement. Participation or compatibility does not mean a government, standards body, vendor, cloud, or model provider endorses OpenPermit.
8. Keep the core small. Domain-specific semantics belong in namespaced profiles unless they are genuinely cross-domain invariants.

## Suggested workflow

- Open an issue describing the problem and source evidence.
- Add or update a machine-readable object/profile.
- Add conformance fixtures or validation tests.
- Explain compatibility and provenance.
- Name who is affected, so domain experts can challenge the change.
- Fill in the pull request template (`.github/PULL_REQUEST_TEMPLATE.md`).

## Independent work

No one needs to build "our product". ORI is a shared substrate, and independent work interoperates through it:

- an ORI-compatible jurisdiction manifest;
- an adapter from an existing permitting or regulatory system;
- a standards or vocabulary mapping;
- an open validator with declared capabilities;
- published conformance results;
- model tooling that inspects provenance, traverses dependencies, verifies evidence and creates challenge records.

## Provenance rules

1. **No building-code text.** Cite the section, link the official source, and write an original paraphrase. CI runs the no-code-text lint (`conformance/validate.py`). Before each release the maintainers also run the strict check against local licensed copies kept outside the repository: no run of six or more consecutive words shared with the code (`docs/CITATION-POLICY.md`, `verification/tests/test_strict_safeguard.py`).
2. **Every external source carries a provenance record:** licence or public-domain basis, URL, date fetched and SHA-256, and a local copy of the licence evidence when it is redistributable (`research/licenses/`).
3. **Cite only what you fetched.** A claim you could not check against a fetched source is marked UNVERIFIED.
4. **No secured material.** Permit data, donor red-line markup, training data (including overlay labels from donor or third-party plans), municipal permit data and per-municipality HUD rubric scores never enter this repository, an issue or a pull request (`docs/GOVERNANCE-BOUNDARY.md`).
5. **Public-source examples are labeled.** A jurisdiction example built from published material says so and does not describe the jurisdiction as a pilot, partner or participant.
6. **Synthetic first.** Benchmark cases and fixtures are ORI-authored and synthetic unless a third-party source passes the licence gate.
7. **No `.docx`.** Documentation is Markdown.

## Licensing

| What you contribute | Licence |
|---|---|
| Code (Python, shell, workflows, HTML/JS tools) | Apache-2.0 (`LICENSE`); add an `SPDX-License-Identifier: Apache-2.0` header to new source files |
| Prose specifications, documentation, public benchmark cases, attribution material | CC BY-SA 4.0 |
| Machine-readable schemas, the ORI-CL grammar and vocabulary, rule data, profiles, fixtures | CC0 1.0 |
| Edits to a file previously dedicated to CC0 | CC0 1.0 (the file stays CC0) |

The per-path map is in `LICENSE-SPEC.md`; full texts are in `LICENSES/`. Third-party material keeps its own terms.

### Developer Certificate of Origin

Sign off each commit (`git commit -s`), certifying the [Developer Certificate of Origin 1.1](https://developercertificate.org/): you wrote the contribution or otherwise have the right to submit it under the licence that applies to its path.
