# OpenPermit / ORI — October 2026 scope and evidence ledger

**Status:** candidate release *review* document, dated 2026-10-08. The publication boundary is intentional: public reusable abstractions and synthetic examples only. Research, experimental results and prior conversations do not by themselves constitute a deployed or independently accepted public implementation.

## What is in this candidate branch

- [Synthetic reference wall and evidence contract](REFERENCE-WALL-EVIDENCE-0.1.md), with a 48 × 96-inch fixture, 52 addressable candidate locations and deliberate OPEN code/authority gates.
- A portable local validator and negative tests (no external packages or proprietary runtime).
- [Assembly rule and provenance interface draft](ASSEMBLY-RULES-0.1.md).
- Public-site reference-wall route and discoverability links.

These are the newly added public pieces. The more advanced wall implementer, evidence packet generator and research corpus have **not** been copied to this branch.

## Reconciled Oct 1–8 workstreams

| Workstream | Established work or decision | Public status / condition |
|---|---|---|
| ORI Core | Source-native terms, mapping assertions, authority, jurisdiction, effective time, challenge, evidence; initial schema, conformance and reference node already in public repository | Existing draft; update without conflating automated checks and legal authority |
| Wall geometry | Small tested wall cell; extended prototypes for openings, connection and fastener relationships, more elaborate review geometries | Public **synthetic cell only** here; no unreviewed production code or private client geometry |
| Rule library | Fastener families, applicability and source pointers developed in internal tooling; 2x6 source wording conflicts with 2x4 synthetic examples | Publish interface and OPEN applicability example, not project-specific rule tables or copyrighted code text |
| IFC / GLB | Internal deterministic IFC4X3/STEP serialization, identity maps, opening relations, semantic connection relationships, GLB projections and adversarial checks | Independent external-parser acceptance and publishable source/receipts required before conformance claim |
| Evidence views | Internal front/back/isometric/cutaway/fastener inspection plates and corrected non-overlapping text layouts | Do not assert independent inspection, provide media, or publish private PNGs without rights/receipt review |
| Exact geometry | OpenCascade kernel + STEP considered for deterministic solids, takeoff and exchange, with IFC retaining building semantics | Design direction, **not implemented** in this candidate |
| Fast Footing | Minimum single-footing permit / rule-encoded rebar and photo evidence hypothesis; accelerated review as measurable experiment | Research/pilot proposal, not a claimed 24-hour approval pathway |
| Photos and detection | Camera ingestion/callback, on-device/local object classifier and stud identification contemplated as evidence collection | Not implemented or validated here; identity/evidence/false-positive gates needed |
| Virginia research | Recent locality permit-source inventory, licence classification and VA/TX/WA lexical/verb comparison reconstructed | Internal traceability and research; corpus/text not redistributed; source rights must be checked row-by-row |
| Public site | Need direct public access to reference assemblies, rules and evidence status from repository-backed pages | Adds reference-wall route; any vanity domain routing requires separate DNS/HTTPS verification |
| Readiness | Separate project-evidence checker patch with negative tests developed offline in another workstream | Not integrated here; no fresh independent readiness/CI receipt and no project-wide pass assertion |

## Research traceability and rights

The October 3 internal source catalog described **3,274** entries, with **3,146** marked permission-free for the recorded internal use and **128** excluded. Its detailed review also reported **1,538** blank/unclear licence classifications, **860** missing byte hashes and **26** missing URLs. These are differently scoped, partly overlapping quality observations; permission-free is **not** a licence to republish third-party source text. A prior 60-document study remains a referenced but unlocated predecessor; the newer linguistic analysis is a separate research output. No raw catalog, underlying corpus, municipality forms, licensed model-code text, or personal Drive URLs are included.

Public promotion requires per-entry provenance (jurisdiction/issuer, URL, retrieval/effective dates, edition, content hash if captured, licence class, allowed use, reviewer). Counts are historical inventory observations, not a statement that all sources were audited for worldwide redistribution.

## Required independent release checks

1. **Disclose no secrets/IP**: source ownership, rights, licence and security scan; public versus private boundary reviewed by a different person.
2. **Reproduce**: run this fixture validator + negative tests and existing `conformance/validate.py`, reference-node tests and smoke on the candidate commit.
3. **Verify scope**: compare all changed files with last public `test` HEAD; don't silently import a separate working tree or abandon uncommitted work.
4. **Promote carefully**: independently review and port clean, standalone code and evidence from the advanced wall implementation in a later reviewed change. External IFC validation is not established by this lightweight fixture.
5. **Publish receipts**: CI job URL, tree SHA, test suite versions, reviewer, evidence manifest SHA, public-site route response and negative cases.
6. **Regulatory separation**: geometry PASS ≠ rule applicable ≠ engineering approval ≠ permit issuance.

## Explicit exclusions

No commercial/proprietary models, building-specific permit packages, third-party standard prose, private credential/signal records, private working-tree paths, unvetted AI-derived field photographs, or fabricated evidence outputs. Experimental algorithm designs and NSF/grant ideas are not represented as delivered software. The former working name used for the wall research is not adopted as a product name.

## Subsequent release lanes

**Lane A:** this narrow, reproducible public ORI assembly-interface/example change.

**Lane B:** independent exporter/parser interoperability, IFC↔canonical↔GLB identity and viewport evidence with formal receipts, once the original working tree is reconciled.

**Lane C:** source-licensed, addressable Virginia rule/corpus metadata and Fast Footing pilot with applicability, jurisdiction and human decision gates.

**Lane D:** production deployment / site routing / adoption telemetry after hardening, without weakening estate stability priorities.

All lanes retain ordinary source control, independent checks and explicit human merge approval. This is a release ledger, not proof that lanes B–D shipped.
