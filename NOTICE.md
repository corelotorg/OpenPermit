# NOTICE

Open Regulatory Infrastructure (ORI), OpenPermit project
https://github.com/corelotorg/OpenPermit

Copyright 2025-2026 Jeremiah Horstick and ORI contributors.

- Software code: Apache License 2.0 ([`LICENSE`](LICENSE)).
- Prose specifications, documentation, public benchmark cases and attribution material:
  Creative Commons Attribution-ShareAlike 4.0 International.
- Machine-readable schemas, the ORI-CL grammar and vocabulary, fixtures and synthetic sample data:
  CC0 1.0 Universal. Material previously dedicated to CC0 stays CC0.

The per-path licence map is in [`LICENSE-SPEC.md`](LICENSE-SPEC.md); full texts are in
[`LICENSES/`](LICENSES/). Training data and secured material are not in this repository.

## Lineage

- **OpenPermit (2014-2016)**, the OpenPermit Foundation's permitting API specification
  (github.com/openpermit/openpermit.github.io; specification released under Creative Commons
  Attribution 3.0, CC BY 3.0) and its reference implementations (OpenPermit.NET and siblings, MIT License,
  copyright 2015 The OpenPermit Foundation Inc.). ORI credits it as lineage. ORI copies no text or
  code from it and claims no endorsement.
- **SheetPros/OpenPermit** (2025), the root of the GitHub fork network this repository belongs to.
  It carries no licence file. ORI credits it and copies none of its content.
- **corelotorg/OpenPermit** (Corelot, 2025-2026), the canonical repository, where ORI's public drafts are published
  under Apache-2.0 (code) and a CC0 notice (specifications).
- **jeremiahhorstick/OpenPermit** (Jeremiah Horstick, 2025-), a historical fork and the target named in the October 3 candidate packet. This release continues in corelotorg/OpenPermit.

As Jeremiah Horstick states it, the chain runs Sheet Pros, then Corelot, then his fork. GitHub's
fork graph lists both the Corelot and the Jeremiah Horstick repositories as direct forks of
SheetPros/OpenPermit. Details: [`CREDITS.md`](CREDITS.md#lineage-and-provenance).

## Third-party software used, not vendored

ORI depends on these packages at run time or test time and redistributes none of them:
IfcOpenShell and IfcTester (LGPL-3.0-or-later), pdfplumber and pdfminer.six (MIT), pypdfium2
(Apache-2.0 or BSD-3-Clause; PDFium BSD-3-Clause), pypdf (BSD-3-Clause), ezdxf (MIT), Shapely
(BSD-3-Clause; GEOS LGPL-2.1), ReportLab (BSD), Pillow (MIT-CMU), NumPy (BSD-3-Clause),
jsonschema (MIT), the MCP Python SDK (MIT), Starlette and Uvicorn (BSD-3-Clause), pytest (MIT).
LGPL libraries are used unmodified as separate packages.

## Standards implemented

buildingSMART International's IFC 4.3, IDS 1.0 and BCF 3.0 specifications are licensed CC BY-ND 4.0.
ORI implements them and uses their entity, property-set and quantity names; it does not redistribute
or adapt the specification documents. ORI makes no claim to buildingSMART certification or to any
buildingSMART trademark.

## Building codes

ORI cites, interprets and links model codes and Virginia amendments. It does not reproduce their
text. ICC model codes remain the property of the International Code Council; Virginia regulations
are published by the Commonwealth of Virginia.

Full credits, including adjacent projects and related work: [`CREDITS.md`](CREDITS.md).
