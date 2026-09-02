# Contributing to OpenPermit / ORI

OpenPermit is built as an open regulatory substrate, not a closed permitting product. Contributions are welcome from public agencies, jurisdictions, standards bodies, maintainers, practitioners, universities, civic-tech groups, AI/model providers, cloud providers, permitting vendors, manufacturers, inspectors, engineers, builders, and specialist validators.

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
- Invite challenge from affected domain experts.

## Ecosystem activation

Organizations do not need to build “our product.” The goal is to implement a shared substrate. Useful independent work includes:

- publish an ORI-compatible jurisdiction manifest;
- publish an adapter from an existing permitting or regulatory system;
- contribute a standards/vocabulary mapping;
- publish an open validator with declared capabilities;
- contribute compute to an interoperable validator network;
- publish conformance results;
- teach models to inspect provenance, traverse dependencies, verify evidence, and create challenge records.

## Licensing

By contributing, you agree that software contributions are provided under the repository's Apache-2.0 license unless otherwise marked, and original specification/schema/profile/documentation contributions are provided under the public-use notice in `LICENSE-SPEC.md`. Third-party material remains subject to its own terms.
