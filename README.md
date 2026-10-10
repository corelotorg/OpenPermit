# OpenPermit: Open Regulatory Infrastructure (ORI)

**ORI is open infrastructure for checking single-family home plans against the building code, with
every result traceable to its source and challengeable by anyone. OpenPermit is its reference
implementation.**

ORI turns the code requirements that apply to a new single-family home into testable, cited rule
units, checks IFC models and PDF plan sets against them, and reports evidence a reviewer can act
on. It also models the permitting process itself (authorities, requirements, evidence, deadlines,
fees, decisions and challenges) as an open, machine-readable graph.

- **Project:** [openpermit.io](https://openpermit.io)
- **Developers, specification and benchmark:** [openpermit.dev](https://openpermit.dev)
- **Source:** [corelotorg/OpenPermit](https://github.com/corelotorg/OpenPermit), branch `test`

The public ORI site is moving to this repository. Until openpermit.io and openpermit.dev are
pointed here, read everything from the repository itself; schema `$id` values on openpermit.dev are
stable identifiers, not yet live URLs.

## Guardrails

1. **A machine check is never approval.** Every ORI result is evidence for a human reviewer. The
   building official decides under the adopted code.
2. **Unknown is not fail.** Missing, unreadable or unconfirmed information gives `unknown`, never
   `fail`. A `fail` needs usable evidence that the requirement is unmet.
3. **No building-code text.** ORI cites sections, links the official source and writes its own
   paraphrases. CI runs the no-code-text lint, and before each release the maintainers run the strict
   check against local licensed copies: no run of six or more consecutive words shared with the code
   ([`docs/CITATION-POLICY.md`](docs/CITATION-POLICY.md)).
4. **Guidance is not law.** HUD's 2026 best-practices guidance and ORI's own 24-hour review target
   are context and comparison lines, never binding requirements.
5. **No endorsement implied.** No government, standards body or company has endorsed ORI. Named
   jurisdictions appear only as labeled public-source examples.

## Scope

- **Buildings:** detached single-family new homes.
- **Code:** the 2021 International Residential Code (IRC) as the base model, with the 2021 Virginia
  Residential Code under the Virginia USBC (13VAC5-63) as the first override layer.
- **Inputs:** IFC 4.3 models (the IFC schema is a public input), and PDF plan sets through
  sheet-anchored declared values and vector plan takeoff.
- **Outputs:** per-rule results (`pass`, `fail`, `unknown`, `not_applicable`) with reason codes and
  evidence, BCF issues for model viewers, and machine-readable reports.
- **Process layer:** jurisdiction inventories, precedence graphs, shot clocks and challenge records.

ORI publishes its mechanics and benchmark. Permit data, donor red-line markup, training data,
municipal permit data and per-municipality HUD rubric scores are secured and never enter this
repository ([`docs/GOVERNANCE-BOUNDARY.md`](docs/GOVERNANCE-BOUNDARY.md)).

## Quick start

Python 3.12 or later (CI uses 3.12).

```bash
git clone https://github.com/corelotorg/OpenPermit.git
cd OpenPermit
python -m pip install -r conformance/requirements.txt -r reference-node/requirements.txt -r verification/requirements.txt

python conformance/validate.py            # schemas, positive and negative fixtures, no-code-text rule
python -m pytest -q reference-node/test_graph.py adapters/blds rules verification/tests
python reference-node/smoke.py
```

Check the synthetic Chapter 3 benchmark models:

```bash
cd verification
python -m ori_verify.cli ifc examples/ifc/ori-ch03-fail.ifc --out /tmp/fail.json --bcf /tmp/fail.bcf
python -m ori_verify.cli ifc examples/ifc/ori-ch03-incomplete.ifc --out /tmp/incomplete.json   # unknowns, not fails
```

Run the reference node (MCP Streamable HTTP and plain HTTP, no account or API key):

```bash
python reference-node/server.py           # http://127.0.0.1:8000/health
docker build -f reference-node/Dockerfile -t openpermit-ori . && docker run --rm -p 8000:8000 openpermit-ori
```

## Repository map

| Path | What it holds |
|---|---|
| [`spec/`](spec/) | ORI specifications and JSON Schemas: core, rule units, ORI-CL rule language, interpretability, plan overlays, model interface, precedence graphs, challenges, evidence, capability registry |
| [`vocab/`](vocab/) | ORI-CL vocabulary |
| [`rules/`](rules/) | Rule units for IRC 2021 Chapter 3 with the Virginia layer: paraphrases, IDS files, ORI-CL sources |
| [`verification/`](verification/) | Geometric verifier (`ori_verify`), ORI-CL compiler (`ori_cl`), plan takeoff (`ori_takeoff`), tests and the public benchmark examples |
| [`conformance/`](conformance/) | Conformance harness with positive and negative fixtures |
| [`reference-node/`](reference-node/) | Zero-ceremony MCP/HTTP reference node and container |
| [`adapters/blds/`](adapters/blds/) | BLDS interchange adapter (not part of ORI Core) |
| [`profiles/`](profiles/) | HUD 2026 guidance profile, federal regulatory-inventory context, ORI's 24-hour single-family target, and a synthetic example jurisdiction inventory |
| [`docs/`](docs/) | Citation policy, governance boundary, PDF path, plan takeoff, training-set workflow, term-merger method, ecosystem |
| [`research/`](research/) | Licence and provenance records for every external source used |
| [`.well-known/ori.json`](.well-known/ori.json), [`llms.txt`](llms.txt) | Machine discovery and a model-facing map |

## Examples

The public conformance suite runs on a **synthetic** jurisdiction,
[`profiles/examples/example-city/`](profiles/examples/example-city/), so it needs no real
jurisdiction's data. All IFC models and PDF plan sets in `verification/examples/` are ORI-authored
and synthetic.

No municipality is a pilot, partner or reviewer of ORI, and no real jurisdiction's inventory is
published. Public locality pages appear only as cite-and-link research sources.

## Core model

```text
jurisdiction -> approval -> authority -> requirement -> evidence
             -> reviewer -> deadline -> fee -> status -> decision

source -> provision -> mapping assertion -> rule unit -> verification -> reviewer decision
                                                            |
                                                            +-> challenge -> evidence -> disposition
```

A normalized mapping is not authoritative merely because it exists. Source-native terms, authority,
versions, evidence, alternatives and challenges stay traversable. Conformance proves schema and
interface behaviour, not legal correctness or approval.

## Licences

| Material | Licence |
|---|---|
| Code | [Apache-2.0](LICENSE) |
| Prose specifications and documentation, public benchmark cases, attribution material | [CC BY-SA 4.0](LICENSES/CC-BY-SA-4.0.txt) |
| Machine-readable schemas, ORI-CL grammar and vocabulary, rule data, profiles, fixtures | [CC0 1.0](LICENSES/CC0-1.0.txt) |

Files previously dedicated to CC0 stay CC0. The per-path map is in
[`LICENSE-SPEC.md`](LICENSE-SPEC.md). Training data and the secured side are outside this repository
and outside share-alike.

## Credits and lineage

ORI builds on earlier work and credits it in [`NOTICE.md`](NOTICE.md) and
[`CREDITS.md`](CREDITS.md): the 2014–2016 OpenPermit project (specification CC BY 3.0, OpenPermit.NET
MIT), SheetPros/OpenPermit, Corelot (corelotorg/OpenPermit), buildingSMART's IFC, IDS and BCF,
IfcOpenShell and the other open-source projects ORI uses. This repository is the current
ORI/OpenPermit project. It is not the legacy 2016 OpenPermit API and claims no endorsement from it.

## Related work

[BIMvoice/openpermitting](https://github.com/BIMvoice/openpermitting) (Petru Conduraru) defines an
open process for pre-checking IFC submissions for completeness before review. It explicitly excludes
automated code compliance. ORI covers code compliance, so the two are complementary. ORI adapts
openpermitting's four-way report categories, its pairing of plain language with IDS rules, and the
idea behind its IFCpluck extraction tool, with credit in [`CREDITS.md`](CREDITS.md#related-work).

## Contributing, conduct and security

- [`CONTRIBUTING.md`](CONTRIBUTING.md): provenance and licence rules, DCO sign-off.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- [`SECURITY.md`](SECURITY.md): private vulnerability reporting.
- [`GOVERNANCE.md`](GOVERNANCE.md) and [`CHARTER.md`](CHARTER.md)

## Status

v0.1 public working draft. Rule-unit classifications and interpretability scores are estimates until
two human reviewers score them. Accuracy figures for plan takeoff are measured on ORI's synthetic
sample only and say nothing about real plan sets. Problems, counterexamples and disagreements are
welcome as issues or machine-readable challenge records.

## Public site and model verification

The release includes reproducible site routes into the same repository: `/docs/`, `/spec/`, `/benchmark/`, `/contribute/`, and `/model-verification/`. On GitHub project Pages these live beneath `/OpenPermit/`. Run `python site/build.py --out _site` and `python site/check.py _site`. See [site deployment](docs/PUBLIC-SITE.md) and [release readiness](docs/RELEASE-READINESS-2026-10-07.md).

Our geometry and evidence work is called **OpenPermit Model Verification**. Upstream research is credited in [CREDITS.md](CREDITS.md). Reference wall geometry, code applicability, independent exchange validation, and certification remain separate acceptance claims.
