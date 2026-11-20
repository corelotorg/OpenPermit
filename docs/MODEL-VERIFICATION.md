# OpenPermit Model Verification

This is the project name for our assembly geometry and evidence work. CraftBot is Luka Piskorec's upstream research project; it appears only in attribution, not as our product name. See [credits](../CREDITS.md#architectural-research).

The intended source is a versioned assembly graph with stable element identities, dimensions, material, connection rules, provenance and explicit verification state. Geometry, takeoffs, sections, sheets, IFC/STEP exchange and GLB views are projections of that revision.

OpenCascade is a proposed solid-geometry kernel, not a dependency already implemented by this release. IFC is semantic exchange; STEP is CAD exchange; GLB is a viewing projection. Adoption of a kernel does not itself establish element completeness, engineering adequacy, code applicability or approval.

Reference-wall acceptance requires element completeness; framing, sheathing, fastener and section views; independent count/dimension checks; external IFC and STEP fidelity checks; and a controlled parameter change that regenerates all outputs. Missing evidence remains OPEN. Net geometry quantities and procurement quantities have separate rules for waste, stock, cutting and labor.

The public release contains synthetic single-family benchmark files. Internal project models and private production tooling are not copied into this repository. A reference-wall production acceptance or an OpenCascade integration is not claimed here.

## Reproducible reference-wall review

Run `python site/reference_wall_check.py --out _site/model-verification/review` (Node.js is required), or run the normal static-site build. The [review page](../model-verification/review/index.html) links baseline and controlled-change cases rendered by the same viewer, their exact parameter JSON, and expected/actual results with viewer/checker/probe SHA-256 hashes. Generated case pages are build artifacts, not independently maintained viewer implementations.

The checker executes the actual viewer JavaScript through a minimal DOM adapter, takes its actual JSON export, and compares every element against separately specified Python geometry tables. It checks identities, box coordinates/dimensions, projection vertices at 0% and 100%, selection metadata, and model preservation under layer filtering. It is independent of the viewer's geometry-generation implementation, but it is not an external professional attestation. Browser screenshots and human inspection supplement these numerical checks; the DOM adapter does not prove browser layout or rendering.

The controlled case changes the wall from 96 × 96 to 120 × 108 inches; changes seven stud centers to six at 0.75, 24, 48, 72, 96 and 119.25 inches; and changes two 48-inch panels to three 40-inch panels. Expected stud length changes from 91.5 to 103.5 inches and illustrative marker count from 56 to 48. These are synthetic test inputs, not a fastening or code design.

Automated results cover only the named software checks. Review the two viewer cases, move from elevation to isometric, select each element type, and compare the visible counts/layout against the report. Record the reviewer's explicit decision with the case revision and artifact hashes; an empty decision remains pending. Fastening specifications, IFC/STEP exchange, and code applicability retain their separate unresolved gates. A successful geometry check or favorable visual review does not authorize construction.
