# Credits

ORI stands on other people's work. This file names it: where ORI came from, what it runs on, what
it implements, which ideas it adapts, and which projects shaped it. Licence facts were read from each
project's own LICENSE file or official page on 2026-10-03 unless a row says otherwise. A credit here
states a fact about ORI's use of the work. It implies no endorsement of ORI by anyone named.

Short form for redistribution: [`NOTICE.md`](NOTICE.md). Licences for ORI's own material:
[`LICENSE-SPEC.md`](LICENSE-SPEC.md).

## Lineage and provenance

| Stage | Repository or source | Licence | What came from it |
|---|---|---|---|
| OpenPermit specification, 2014-2016 | [openpermit/openpermit.github.io](https://github.com/openpermit/openpermit.github.io) (OpenPermit Foundation; site www.openpermit.org, now dormant) | Specification: Creative Commons Attribution 3.0 (stated in its README; no LICENSE file) | Lineage: an earlier open permitting specification under the OpenPermit name. ORI copies no text from it. |
| OpenPermit reference implementations, 2015-2016 | [openpermit/OpenPermit.NET](https://github.com/openpermit/OpenPermit.NET) and siblings (OpenPermit.Node, openpermit.js, OpenPermit.Apps, openpermit-search) | MIT, copyright 2015 The OpenPermit Foundation Inc. | Lineage only. ORI copies no code from them. |
| Sheet Pros, 2025 | [SheetPros/OpenPermit](https://github.com/SheetPros/OpenPermit), created 2025-04-16 | No licence file | The root of this repository's GitHub fork network. Credited; no content copied. |
| Corelot, 2025-2026 | [corelotorg/OpenPermit](https://github.com/corelotorg/OpenPermit), created 2025-05-18 | Apache-2.0 (LICENSE) and a CC0 notice for specifications | ORI's earlier public drafts (charter, core specification drafts, schemas, conformance suite, reference node), continued here. |
| Jeremiah Horstick, 2025- | [jeremiahhorstick/OpenPermit](https://github.com/jeremiahhorstick/OpenPermit), created 2025-04-20 | Historical fork | Target named in the October 3 candidate packet; this release continues in corelotorg/OpenPermit. |

**The chain as Jeremiah Horstick states it:** Sheet Pros, then Corelot, then his fork.

**What GitHub's fork graph records:** SheetPros/OpenPermit is not a fork. Both
corelotorg/OpenPermit and jeremiahhorstick/OpenPermit are listed as direct forks of
SheetPros/OpenPermit, and the Jeremiah Horstick fork was created about four weeks before the Corelot
fork. The fork graph records where each repository was forked from; it does not by itself show the
order in which the work developed. Both the stated chain and the graph facts are recorded here.

The October 3 candidate was prepared for the Jeremiah Horstick fork. This release adapts that candidate to the established Corelot repository and preserves its existing history and CI. Historical recovery material remains non-normative.

## Software ORI uses

These are dependencies, installed from their own distributions and not vendored.

| Project | Licence | Use in ORI |
|---|---|---|
| [IfcOpenShell](https://ifcopenshell.org) (ifcopenshell-python, ifcopenshell.api) and [IfcTester](https://docs.ifcopenshell.org/ifctester.html) | LGPL-3.0-or-later | Reads and writes IFC; geometric verification of IFC fixtures; IDS checks; IFC 4.3 export of plan takeoffs |
| [pdfplumber](https://github.com/jsvine/pdfplumber) and [pdfminer.six](https://github.com/pdfminer/pdfminer.six) | MIT | Vector text, lines and curves from plan PDFs (plan takeoff, PDF path) |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) / PDFium | Apache-2.0 or BSD-3-Clause; PDFium BSD-3-Clause | Page rendering (through pdfplumber) for previews and the markup editor |
| [pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause | PDF page manifests and metadata |
| [ezdxf](https://ezdxf.mozman.at) | MIT | DXF intake for plan takeoff |
| [Shapely](https://shapely.readthedocs.io) on [GEOS](https://libgeos.org) | BSD-3-Clause; GEOS LGPL-2.1 | 2D geometry: areas, clearances, wall and room reconstruction |
| [ReportLab](https://www.reportlab.com/opensource/) | BSD | Writes the ORI-authored synthetic sample plan |
| [Pillow](https://python-pillow.org) | MIT-CMU | PNG previews |
| [NumPy](https://numpy.org) | BSD-3-Clause | Numeric support for geometry |
| [jsonschema](https://github.com/python-jsonschema/jsonschema) | MIT | Schema validation in the conformance suite |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), [Starlette](https://www.starlette.io), [Uvicorn](https://www.uvicorn.org) | MIT; BSD-3-Clause; BSD-3-Clause | The reference node's MCP and HTTP surfaces |
| [pytest](https://pytest.org) | MIT | Test runner |

The term-merger study's corpora and lexical resources are credited one source at a time, with
licence records and citations, in `research/data/ori-cl-open-corpora-DRAFT.json` and
`research/licenses/`.

## Standards and public sources ORI implements or cites

| Source | Licence or status | Use in ORI |
|---|---|---|
| [buildingSMART International](https://www.buildingsmart.org): IFC 4.3, IDS 1.0, BCF 3.0 | CC BY-ND 4.0 (specification repositories) | IFC is a public input to the benchmark; ORI writes IDS files for Chapter 3 information requirements and exports BCF issues. Names only; no specification text is copied or adapted. ORI makes no buildingSMART certification or trademark claim. |
| [buildingSMART Validation Service](https://github.com/buildingSMART/validate) and [ifc-gherkin-rules](https://github.com/buildingSMART/ifc-gherkin-rules) | MIT | The model for ORI's conformance pattern: normative checks written as rules with passing and failing fixtures. Idea adapted; no code copied. |
| [BLDS (Building and Land Development Specification)](https://permitdata.org) | No licence found | Field names only, in the BLDS interchange adapter (`adapters/blds/`). |
| International Code Council, 2021 IRC; Virginia 2021 USBC and VRC (13VAC5-63) | Copyrighted model code; state regulation | Cited, interpreted and linked, never reproduced ([`docs/CITATION-POLICY.md`](docs/CITATION-POLICY.md)). |
| [HUD, State and Local Best Practices for Home Construction (2026)](https://www.hud.gov/hud-partners/state-and-local-best-practices) | U.S. federal work; guidance, not law | Criteria source for ORI's HUD guidance profile (`profiles/federal/`). Per-municipality scores are secured, not published. |
| [Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | U.S. federal work | The planned public base layer for jurisdiction boundaries. |

## Adjacent projects whose ideas shaped ORI

None of these projects' code or text is copied into ORI, and none is a runtime dependency. Each one is
credited for an idea, a pattern or a design choice ORI took from studying it in its 2026-10-03 survey
of adjacent open-source work.

| Project | Licence | What ORI takes from it |
|---|---|---|
| [IFClite](https://github.com/LTplus-AG/ifc-lite) (LTplus AG) | MPL-2.0 | Browser-side IFC handling as the model for ORI's reviewer viewer (IFCpluck builds on it) |
| [Docling](https://github.com/docling-project/docling) | MIT (model weights per model) | Layout and table extraction from plan-set PDFs, as a candidate optional extractor |
| [NetworkX](https://networkx.org) | BSD-3-Clause | Graph analysis patterns for room adjacency, egress paths and precedence slices |
| [pySHACL](https://github.com/RDFLib/pySHACL) and [RDFLib](https://github.com/RDFLib/rdflib) | Apache-2.0; BSD-3-Clause | Shape-based validation as a pattern for checking the regulatory graph |
| [Frictionless Data Package](https://datapackage.org) and [frictionless-py](https://github.com/frictionlessdata/frictionless-py) | Unlicense; MIT | Packaging and validating a benchmark as self-describing data |
| [Catala](https://catala-lang.org) | Apache-2.0 | Default-and-exception semantics for a base model code with state override layers |
| [ODK](https://getodk.org) (Central, Collect, pyxform) | Apache-2.0; BSD-2-Clause | Offline field evidence capture as a pattern for inspection evidence |
| [OpenStudio-HPXML](https://github.com/NatLabRockies/OpenStudio-HPXML) | BSD-3-Clause-style with a name clause | Structured home descriptions as a pattern for residential energy evidence |
| [BC Building Permit Hub](https://github.com/bcgov/HOUS-permit-portal) (Province of British Columbia) | Apache-2.0 | A government-run, open-source housing permit service |
| [UK Open Digital Planning](https://opendigitalplanning.org): [BOPS](https://github.com/unboxed/bops) and [PlanX](https://github.com/theopensystemslab/planx-new) | MIT; MPL-2.0 | Council-run, schema-first planning applications and back-office review |
| [HUD best-practices guidance](https://www.hud.gov/hud-partners/state-and-local-best-practices) | U.S. federal work | Cost, Land and Time framing for measuring local permitting practice |
| [BIMvoice/openpermitting](https://github.com/BIMvoice/openpermitting) (Petru Conduraru) | Documents CC BY 4.0; software MPL-2.0 planned (README) | See below |

### BIMvoice/openpermitting

OpenPermitting, by Petru Conduraru (BIMvoice), is an open toolset for digital permit pre-checking:
an IFC model goes in, an evidence report comes out, and people make the decisions. Its manifest
(version 0.1 draft, 16 September 2026) is licensed CC BY 4.0. ORI adapts three of its ideas, with
credit:

1. **Four report categories.** OpenPermitting's report separates facts, warnings, matters for
   judgement and blockers. ORI's mapping onto its own outcomes:

   | OpenPermitting category | ORI outcome |
   |---|---|
   | Fact | `pass` or `not_applicable`, with the evidence that supports it |
   | Warning | `fail`, reported as a likely code failure for the reviewer to confirm, never a rejection |
   | Matter for judgement | `judgment` units, routed to the building official |
   | Blocker | `unknown` (indeterminate): required information is missing, so no finding is made |

2. **Plain language paired with IDS.** Each information requirement is written once in plain
   language and once as an IDS rule that says the same thing. ORI pairs each rule unit's
   plain-language paraphrase with an IDS specification wherever the unit needs model information
   (`rules/irc2021/ch03/ids/`).
3. **IFCpluck.** [BIMvoice/ifcpluck](https://github.com/BIMvoice/ifcpluck) (MPL-2.0) extracts the
   elements behind a finding into a small standalone IFC file for review or dispute. ORI adopts the
   idea as a design target for its evidence packages, so that a finding can carry the model elements
   it rests on. This is not yet implemented in ORI.

## Related work

**OpenPermitting** focuses on IFC submission pre-checking: it checks that a submitted model carries
the information a public client requires, and it excludes building-code compliance automation (its
manifest places setbacks, egress, fire separation and similar rules out of scope). **ORI covers code
compliance.** It encodes the 2021 IRC with the Virginia amendment layer as cited rule units and
checks plans against them, with every result labeled as evidence for the reviewer. The two projects
share a stance (software checks, people decide) and the same open standards (IFC, IDS, BCF).

## People

Jeremiah Horstick leads ORI. Contributors are recorded in this repository's commit history from this
release onward.

## Architectural research

[CraftBot](https://github.com/lukapiskorec/craftbot), by Luka Piskorec, is credited for research into executable architectural geometry and separate building/inspection roles. Its root LICENSE was checked on 2026-10-07: MIT, copyright 2026 Luka Piskorec. No upstream code or reference-manual content is vendored in this release. Copied code or substantial documentation must retain the upstream copyright and permission notice; third-party references require their own rights review. Our project name is **OpenPermit Model Verification**. Attribution does not imply endorsement or rights to the upstream brand.
