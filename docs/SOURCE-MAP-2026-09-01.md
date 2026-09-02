# OpenPermit source map — 2026-09-01

This file links the reboot to source material recovered outside the reduced GitHub default branch. It is an inventory, not a declaration that every historical statement remains current.

## High-value recovered documents

### NGL ontology extension — Standard + Critical Path

Source: https://docs.google.com/document/d/1Y7xEEqgN5xoCuYaLhnKTGzz58bilCUQ-gsS3h8fLKms/edit

Recovered concepts:

- NGL is the normalization target for the earlier NFL / Node Form Language work.
- A `Standard` is a frozen, versioned, citable artifact extracted from graph/loop work rather than the operational loop itself.
- Standard properties already proposed: issued date, semantic version, provenance, executable conformance suite, IP provenance, and jurisdictional adoption.
- Critical path is treated as a graph traversal result rather than a separate scheduling system.
- Recovered scheduling semantics:
  - `precedes`: directed finish-to-start dependency edge, optional lag weight;
  - `duration`: action-node duration;
  - `float`: derived by forward/backward pass;
  - `criticalPath(Project)`: longest-duration path through `precedes` edges;
  - `isCritical`: derived when float is zero.
- The source explicitly says derived values should be computed rather than authored.

**Reboot use:** this resolves the earlier question of whether critical-path/DAG work existed. It did. Preserve the mathematics, but do not force the entire regulatory graph to be acyclic. Use DAG semantics for precedence/approval subgraphs and general graph semantics for authority, challenge, cross-reference, amendment, and provenance.

### Esperanto / NFL peer-review meeting — 2025-05-22

Source: https://docs.google.com/document/d/13kEGwIfpA6GrfPpK9iQXBNglHDFWDCmKp2EdTiEQnhU/edit

Recovered concepts:

- NFL was explicitly framed as a universal, graph-native orchestration layer originating in OpenPermit and OpenTax.
- The design intent was a distilled seven-verb lexicon plus abstract relationships across domains.
- The method was to crosswalk existing standards rather than invent a closed replacement vocabulary.
- OpenPermit was described as deep research across municipal schemas to produce a universal but jurisdiction-aware interoperable layer.
- Key doctrine: **central standard, decentralized operations, with jurisdictional awareness**.
- Policy/API changes were expected to be handled through domain knowledge packs.
- Physical and digital representations were intended to coexist, including BIM/IFC objects.
- The application layer was deliberately separate from the interoperable standard.
- The same substrate was expected to support broader regulatory domains beyond building permits.
- Minimalism and model-leader iteration were already stated goals.

**Reboot use:** keep the core idea; remove product-pitch narrative. Recover the exact seven verbs from the original NFL/NGL source before freezing a new vocabulary.

### OpenPermit API Research — market endpoint inventory

Source: https://drive.google.com/file/d/1BxGUjRZIS5XzSezL-oqbiP5MGAAx_oa9/view

Recovered concepts:

- Cross-vendor inventory covered Accela, OpenGov, Tyler EnerGov, Trimble, Cloudpermit, PermitFlow, and BLDS.
- Common application lifecycle operations were reduced to a small interoperable set.
- The prior proposed permit-facing actions were `SUBMIT`, `STATUS`, `ATTACH`, `RESPOND`, `SCHEDULE`, `RESULT`, `PAY`, and `ISSUE`.
- Design principles already included platform neutrality, lifecycle alignment, JSON-LD readiness, and mapping to incumbent systems.

**Reboot use:** retain this as a **permit application profile**, not the ORI core ontology. ORI must support regulatory infrastructure well beyond permit CRUD/workflow.

### OpenPermit Implementation Playbook — January 2026

Source: https://docs.google.com/document/d/165ukYnIzSH8geyK1n-entSj3xg30Elpe/edit

Recovered concepts:

- Explicit vendor-neutral standard positioning.
- National/state/local interoperability strategy.
- Virginia, Texas, and Washington statutory anchors were named.
- A conformance harness was already proposed.
- Municipal deployment was conceived as a replicable template rather than one vendor system.

**Reboot use:** retain the multi-jurisdiction and conformance ideas. Retire the committee/certification/revenue program as core governance. The reboot is permissionless and must not require paid certification or organizational endorsement.

### GitHub historical branch corpus

Repository: https://github.com/corelotorg/OpenPermit

Recovered capability anchors are indexed in `recovered/recovery-index.json` and `docs/RECOVERY-INVENTORY-2026-09-01.md`.

Notable recovered Git objects include:

- domain ontology: `0a8873dfffd4e65c6a15ec682b39bf0fb7536840`;
- legal-to-IFC mapping: commit `afc139ff02e34d71218caf446af40c1819ccb87a`;
- typed graph relationships: commit `b2e5f00f95f225ac7e1d0cd39b39c7b4cda7540b`;
- NIEM alignment: commit `13eed65e2fb5ed264c5e84c7b8a079adc587fc8c`;
- JSON-LD workflow: commit `0294aa7f5aa9686a11d4d0c45514af02d1307b06`;
- audit trail: commit `7fb046263694922666e34f3d1e9605249411d5ba`;
- geo-tagged remote inspection: commit `54496caf7a6d3aaf42095b536d9124964a6168e2`.

## What the recovered work changes now

The reboot is not starting at zero. The historical work already establishes four strong invariants:

1. **Graph-native:** relationships and precedence are part of the data model, not UI workflow glue.
2. **Standards-crosswalking:** map authoritative and incumbent vocabularies at the seams instead of replacing them.
3. **Jurisdiction-aware:** a common standard coexists with local authority and local extensions.
4. **Conformance-driven:** standards are real when independently testable.

The new contribution from the 2026-09-01 reboot is to make **challenge and governance first-class** and to make **models a primary interface**, with MCP alongside REST, JSON-LD, graph traversal, and crawlable static documentation.

## Still to recover before core vocabulary freeze

- the exact original seven-verb NFL/NGL lexicon and its definitions;
- full Washington regulatory inventory, beyond statutory anchor references;
- full Texas regulatory inventory, beyond statutory anchor references;
- the cross-jurisdiction linguistic study and verb-frequency/semantic analysis;
- secure geocoded open-hardware artifact specification;
- third-party attestation layer specification;
- any prior challenge/appeal/counterclaim ontology work.

Do not invent replacements until these sources are searched.
