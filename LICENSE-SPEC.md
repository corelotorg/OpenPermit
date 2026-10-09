# ORI licensing: specifications, documentation, data and the per-path licence map

This file sets out how the Open Regulatory Infrastructure (ORI) material in this repository is
licensed. Full licence texts are in [`LICENSES/`](LICENSES/). Attribution for upstream and
adjacent work is in [`NOTICE.md`](NOTICE.md) and [`CREDITS.md`](CREDITS.md).

## The split

| Material | Licence | Full text |
|---|---|---|
| Software source code (Python, shell, Dockerfile, CI workflows, the browser editor) | **Apache-2.0** | [`LICENSE`](LICENSE), [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt) |
| Prose specifications and documentation, the public benchmark cases, and attribution material | **CC BY-SA 4.0** | [`LICENSES/CC-BY-SA-4.0.txt`](LICENSES/CC-BY-SA-4.0.txt) |
| Machine-readable schemas, the ORI-CL grammar and vocabulary, conformance fixtures, synthetic sample data | **CC0 1.0** (public-domain dedication) | [`LICENSES/CC0-1.0.txt`](LICENSES/CC0-1.0.txt) |

Two standing rules:

1. **Anything previously dedicated to CC0 stays CC0.** Files that were published under the earlier
   CC0 notice, or that carry an in-file CC0 dedication, keep it. The map below lists them.
2. **Training data and the secured side are outside this repository and outside share-alike.**
   Permit data, donor red-line markup, training data, municipal permit data and per-municipality
   HUD rubric scores are not published here and are not licensed by this file
   ([`docs/GOVERNANCE-BOUNDARY.md`](docs/GOVERNANCE-BOUNDARY.md)).

Code files carry an `SPDX-License-Identifier` header. JSON cannot carry comments, so data files
take their licence from the map below. Where a file states its own licence, the file wins.

## Per-path licence map

Patterns use `*` for one path segment and `**` for any depth. The first matching row applies.

| Path | Licence | Note |
|---|---|---|
| `**/*.py`, `**/*.sh`, `reference-node/Dockerfile`, `.github/workflows/*.yml`, `verification/ori_takeoff/editor/index.html` | Apache-2.0 | code |
| `LICENSE`, `LICENSES/**`, `research/licenses/*` except `*.md` | each text's own terms | licence texts and third-party rights records, kept verbatim |
| `README.md`, `CHARTER.md`, `GOVERNANCE.md`, `CONTRIBUTING.md`, `LICENSE-SPEC.md`, `docs/ECOSYSTEM.md`, `conformance/README.md`, `reference-node/README.md`, `index.html`, `llms.txt`, `robots.txt`, `sitemap.xml`, `.well-known/ori.json` | CC0-1.0 | previously published under the CC0 notice; stays CC0 |
| `spec/ori-core-0.1-draft.md`, `spec/model-interface-0.1-draft.md`, `spec/precedence-graph-0.1-draft.md`, `spec/challenge-protocol-0.1-draft.md`, `spec/evidence-attestation-0.1-draft.md`, `spec/capability-registry-0.1-draft.md` | CC0-1.0 | previously published under the CC0 notice; stays CC0 |
| `spec/ori-cl-0.1-draft.md`, `docs/CITATION-POLICY.md` | CC0-1.0 | carry their own CC0 dedication |
| `spec/*.schema.json`, `spec/ori-cl-0.1.ebnf`, `vocab/**` | CC0-1.0 | schemas, ORI-CL grammar and vocabulary |
| `conformance/fixtures/**`, `conformance/positive/**`, `conformance/negative/**` | CC0-1.0 | conformance fixtures |
| `profiles/**` | CC0-1.0 | machine-readable profiles (federal guidance profiles previously published under CC0; the synthetic example inventory) |
| `rules/irc2021/ch03/paraphrases-ch03.json`, `rules/irc2021/ch03/ids/**`, `rules/irc2021/ch03/ori-cl/**` | CC0-1.0 | carry their own CC0 dedication |
| `rules/irc2021/ch03/va-vrc-2021-ch03.units.json`, `rules/irc2021/ch03/CHAPTER-3-TABLE.md`, `rules/irc2021/ch03/interpretability-ch03.json` | CC0-1.0 | machine-readable rule data generated from the CC0 paraphrases |
| `verification/examples/takeoff/**` | CC0-1.0 | ORI-authored synthetic sample plan, dedicated CC0 in each file |
| `verification/examples/ifc/**`, `verification/examples/pdf/**`, `verification/examples/declared/**`, `verification/examples/reports/**` | CC BY-SA 4.0 | public benchmark cases: synthetic inputs and expected outcomes |
| `research/data/*.json` | CC0-1.0 | machine-readable research records (licence and citation facts, counts) |
| `.github/PULL_REQUEST_TEMPLATE.md`, `.gitignore`, `.nojekyll`, `.gitleaks.toml`, `**/requirements*.txt` | CC0-1.0 | templates and configuration |
| everything else (`NOTICE.md`, `CREDITS.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `docs/**`, `spec/interpretability-0.1-draft.md`, `spec/rule-unit-0.1-draft.md`, `rules/README.md`, `verification/*.md`, `adapters/blds/*.md`, `research/licenses/*.md`) | CC BY-SA 4.0 | prose specifications, documentation and attribution material |

Attribution for CC BY-SA 4.0 material: "Open Regulatory Infrastructure (ORI), OpenPermit project,
https://github.com/corelotorg/OpenPermit, CC BY-SA 4.0", with a note of any changes.

## Boundary

These licences cover only original ORI material that its contributors have the right to license.
They do not change the status of third-party material: statutes, regulations, model codes,
standards, vendor documentation, external datasets, trademarks or source publications that ORI
cites. ORI's machine-readable records may hold identifiers, citations, mappings, adoption and
version metadata, derived assertions, test definitions, evidence requirements, verification
results and deltas about those sources. They grant no right to reproduce the underlying text.
ORI does not reproduce building-code text ([`docs/CITATION-POLICY.md`](docs/CITATION-POLICY.md)).

buildingSMART's IFC, IDS and BCF specifications are CC BY-ND 4.0. ORI implements them and uses
entity, property-set and quantity names only. It does not redistribute or adapt the specification
documents.

No licence or dedication here creates government endorsement, legal authority, professional
certification, or a warranty that a representation is legally correct or applies to a particular
jurisdiction. Machine verification is evidence for a reviewer, never an approval.
