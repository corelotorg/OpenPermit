# ORI governance boundary: what is public and what is secured

Version 1.0, 2026-10-03. Licence: CC BY-SA 4.0 ([`LICENSE-SPEC.md`](../LICENSE-SPEC.md)).

ORI (Open Regulatory Infrastructure) is open infrastructure with permitting as its first
application. Its benchmark is public and testable. The data that donors, applicants and
municipalities hand to ORI is not. This document draws that line.

## 1. Principles

1. **Mechanics and benchmark are public.** Anyone can read how ORI works, run it, and check its
   results without asking anyone.
2. **Donor material is secured.** Plans, markup and permit records that people give ORI for
   evaluation or training stay under the terms they were given on.
3. **Machine output is evidence, never approval.** Every ORI result is labeled as evidence for the
   reviewer. The building official decides.
4. **Unknown is not fail.** Missing information gives `unknown` (indeterminate), never `fail`.
5. **Unclassified means secured.** Anything not yet classified in section 3 is treated as secured
   until it is classified.

## 2. The line

### Public (in this repository)

- **ORI mechanics:** the specifications and JSON schemas, the ORI-CL controlled rule language with its
  grammar and vocabulary, the regulatory graph model (authority, precedence, evidence), the
  conformance suite, the reference node, and the verification and takeoff tools.
- **The testable benchmark:** rule units with paraphrases and official source links, task
  definitions, metrics, the harness and scoring code, and a public development set built from
  ORI-authored synthetic plans, models and declared values with ground truth.
- **The IFC schema as a public input.** IFC is the input format the benchmark reads. ORI does not
  own it. buildingSMART publishes IFC, IDS and BCF under CC BY-ND 4.0; ORI implements them and uses
  their names only.
- **Licences and attribution:** [`LICENSE`](../LICENSE), [`LICENSE-SPEC.md`](../LICENSE-SPEC.md),
  [`LICENSES/`](../LICENSES/), [`NOTICE.md`](../NOTICE.md), [`CREDITS.md`](../CREDITS.md).
- **Public-source examples:** inventories or rule data built only from what a jurisdiction already
  publishes, each labeled as a public-source example. Labeling a jurisdiction this way states where
  the data came from. It does not make the jurisdiction a pilot, partner or participant.

### Secured (never in this repository)

- **Permit data** given to ORI by applicants, builders, designers or municipalities.
- **Donor red-line markup:** reviewer comments and corrections on plan sheets.
- **Training data:** overlays, labels and exports built from donor or third-party plans.
- **Municipal permit data** that a municipality provides to ORI.
- **Per-municipality HUD rubric scores.** HUD's 2026 *State and Local Best Practices for Home
  Construction* is guidance, not a scoring rubric and not local law. Any rubric ORI applies is
  ORI's own instrument derived from that guidance. The method may be published; scores for a named
  municipality are held securely and released only by decision.

Public records that a municipality already publishes stay public at their source. ORI links to them,
records their terms, URL, date and SHA-256, and stores only derived facts where the source terms
limit redistribution. ORI does not re-license them.

## 3. Classification table

| Artifact | Side | Licence | Where it lives |
|---|---|---|---|
| Specifications (prose) | public | CC BY-SA 4.0, or CC0 where previously dedicated | `spec/*.md` |
| JSON schemas, ORI-CL grammar and vocabulary | public | CC0 1.0 | `spec/*.schema.json`, `spec/ori-cl-0.1.ebnf`, `vocab/` |
| Conformance suite and fixtures | public | Apache-2.0 (code), CC0 1.0 (fixtures) | `conformance/` |
| Reference node, verification and takeoff tools | public | Apache-2.0 | `reference-node/`, `verification/`, `adapters/` |
| Rule units, paraphrases, IDS files, ORI-CL sources | public | CC0 1.0 | `rules/` |
| Public benchmark cases (synthetic inputs and expected outcomes) | public | CC BY-SA 4.0 | `verification/examples/{ifc,pdf,declared,reports}/` |
| Plan overlay format, takeoff tools, synthetic sample plan | public | CC0 1.0 (format, sample), Apache-2.0 (tools) | `spec/ori-plan-overlay-0.1.schema.json`, `verification/ori_takeoff/`, `verification/examples/takeoff/` |
| Synthetic example jurisdiction inventory | public | CC0 1.0 | `profiles/examples/` |
| Federal guidance profiles and the project's 24-hour target | public | CC0 1.0 | `profiles/federal/`, `profiles/project/` |
| Permit data, donor red-lines, training data, municipal permit data | secured | none (donor terms govern) | controlled storage outside the repository |
| Per-municipality HUD rubric scores | secured | none | controlled storage outside the repository |
| Held-out benchmark test labels | secured | none | evaluation host outside the repository |

## 4. Plan overlays: public format, secured training data

The plan overlay **format** (`spec/ori-plan-overlay-0.1.schema.json`), the takeoff **tools**
(`verification/ori_takeoff/`) and the ORI-authored **synthetic CC0 sample** with its ground truth
(`verification/examples/takeoff/`) are public.

Overlay labels made from donor or third-party plans are **training data. They are secured and held
out.** They are not published in this repository, they carry no public licence, and share-alike
does not reach them. The open-licence training gate (`overlay.training_gate_errors`, conformance
rule `plan-overlay-training-gate`) still decides which third-party plans may be used at all; passing
the gate makes a plan admissible for training, not publishable.

## 5. Public benchmark, held-out labels

- **Public:** task definitions, schemas, metrics, the harness and scoring code, and the public
  development set (ORI-authored synthetic material, plus openly licensed material that passes the
  training gate).
- **Held out:** test labels drawn from donor red-lines and reviewer findings, kept on an evaluation
  host. Participants submit outputs; the host returns scores. Labels are refreshed over time to
  limit leakage.
- **Scoring:** pass, fail and unknown are reported separately. `unknown` is a scored outcome, never
  counted as a fail.
- **Publication:** results built on donor data are published only as aggregate metrics, never as the
  underlying markup.

## 6. Donor terms (principles)

A donor lets ORI use material for evaluation and, only if the donor opts in, for training. ORI does
not redistribute or publish it, keeps it in controlled storage, records who gave what under which
terms, keeps access logs, minimizes personal data, and deletes on withdrawal where the law allows.
Material a municipality gives ORI may be subject to public-records law; ORI promises confidentiality
only to the extent the law allows.

## 7. Contributions and provenance

- Code contributions are Apache-2.0; prose contributions are CC BY-SA 4.0; schema, grammar,
  vocabulary and fixture contributions are CC0 1.0 ([`CONTRIBUTING.md`](../CONTRIBUTING.md)).
- Every external source carries a provenance record: licence, URL, date fetched and SHA-256.
- No donor material, permit data or training data in any pull request, issue or commit.
- Building-code text is cited, interpreted and linked, never reproduced
  ([`docs/CITATION-POLICY.md`](CITATION-POLICY.md)). CI runs `conformance/validate.py`, including the
  no-code-text rule.

## 8. Geography and examples

- ORI's scope is single-family new homes under the 2021 IRC, with the 2021 Virginia USBC and VRC
  (13VAC5-63) as an override layer.
- Fredericksburg, Virginia appears only as a **public-source example; not a pilot or partner**.
- Spotsylvania County, Virginia appears, where it appears at all, only as a labeled public-source
  example. It is not a pilot, partner or participant.
- The public conformance suite runs on a **synthetic** example jurisdiction (`profiles/examples/`),
  so it needs no real jurisdiction's data.

## 9. Domains and repository

- **openpermit.io**: the project: what ORI is and who it serves.
- **openpermit.dev**: developers: specifications, schema `$id` host, benchmark.
- **github.com/corelotorg/OpenPermit**: the source repository.

The public site moves to this repository. Until the domains serve it with path-preserving HTTPS,
schema `$id` values on openpermit.dev are identifiers, not live URLs.

## 10. Changing the boundary

A change to this document is a normative change under [`GOVERNANCE.md`](../GOVERNANCE.md): a public
proposal, the reasoning, and an opportunity for challenge before it takes effect. Moving anything
from secured to public also needs the consent of whoever provided it.
