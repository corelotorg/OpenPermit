# OpenPermit Model Verification

This is the project name for our assembly geometry and evidence work. CraftBot is Luka Piskorec's upstream research project; it appears only in attribution, not as our product name. See [credits](../CREDITS.md#architectural-research).

The intended source is a versioned assembly graph with stable element identities, dimensions, material, connection rules, provenance and explicit verification state. Geometry, takeoffs, sections, sheets, IFC/STEP exchange and GLB views are projections of that revision.

OpenCascade is a proposed solid-geometry kernel, not a dependency already implemented by this release. IFC is semantic exchange; STEP is CAD exchange; GLB is a viewing projection. Adoption of a kernel does not itself establish element completeness, engineering adequacy, code applicability or approval.

Reference-wall acceptance requires element completeness; framing, sheathing, fastener and section views; independent count/dimension checks; external IFC and STEP fidelity checks; and a controlled parameter change that regenerates all outputs. Missing evidence remains OPEN. Net geometry quantities and procurement quantities have separate rules for waste, stock, cutting and labor.

The public release contains synthetic single-family benchmark files. Internal project models and private production tooling are not copied into this repository. A reference-wall production acceptance or an OpenCascade integration is not claimed here.
