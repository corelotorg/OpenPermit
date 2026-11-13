# SPDX-License-Identifier: Apache-2.0
"""Chapter 6 catalogue data for build_units.py (DRAFT).

UNITS rows: (section, part-or-None, ORI description, class, single-family applicability).
Class: D=data_check, G=geometric_deterministic, J=judgment (ORI estimates).

Section list status: UNVERIFIED against the official 2021 IRC text. ICC Digital Codes
returns a script-only page to automated fetches (2026-10-12). The R602 numbering was
cross-checked against a Virginia county handout of 2018 VRC Chapter 6 pages
(source:secondary:louisa-2018-vrc-ch6-handout, fetched 2026-10-12); the 2018 and 2021
numbering may differ. R603-R610 are catalogued at section level only, pending the
official text. Titles are ORI descriptions, not ICC headings.
"""

UNITS = [
    # R601 general
    ("R601.1", None, "Chapter scope: wall construction", "D", "applies"),
    ("R601.2", None, "Walls carry their loads with listed materials and methods", "J", "applies"),
    ("R601.2.1", None, "Compressible floor coverings under walls", "J", "applies"),
    # R602 wood wall framing
    ("R602.1", None, "Wood members carry a grade mark or certificate", "D", "applies"),
    ("R602.1.1", None, "Sawn lumber identification", "D", "applies"),
    ("R602.1.2", None, "End-jointed lumber identification and use", "D", "applies"),
    ("R602.1.3", None, "Glued-laminated timber standards", "D", "conditional"),
    ("R602.1.4", None, "Structural log members", "D", "conditional"),
    ("R602.1.5", None, "Structural composite lumber", "D", "conditional"),
    ("R602.1.6", None, "Cross-laminated timber", "D", "conditional"),
    ("R602.1.7", None, "Engineered wood rim board", "D", "conditional"),
    ("R602.1.8", None, "Wood structural panel standards", "D", "applies"),
    ("R602.1.9", None, "Particleboard standard", "D", "conditional"),
    ("R602.1.10", None, "Fiberboard standard", "D", "conditional"),
    ("R602.2", None, "Minimum stud grade", "D", "applies"),
    ("R602.3", None, "Framing and fastening per the fastener schedules", "D", "applies"),
    ("R602.3.1", "stud spacing", "Stud size and spacing for what the wall supports", "G", "applies"),
    ("R602.3.1", "stud height", "Laterally unsupported height of bearing studs", "G", "applies"),
    ("R602.3.1", "exceptions", "Utility-grade and tall-wall stud alternatives", "J", "conditional"),
    ("R602.3.2", "plate count", "Double top plate on bearing walls", "G", "applies"),
    ("R602.3.2", "splice offset", "Top plate end joints offset and lapped", "G", "applies"),
    ("R602.3.3", None, "Bearing studs aligned under joists and rafters", "J", "applies"),
    ("R602.3.4", None, "Bottom plate width and bearing", "G", "applies"),
    ("R602.3.5", None, "Uplift load path at braced wall panels", "J", "conditional"),
    ("R602.4", None, "Interior bearing walls framed like exterior walls", "D", "applies"),
    ("R602.5", None, "Interior nonbearing wall framing", "D", "applies"),
    ("R602.6", "bored holes", "Bored hole size limits in studs", "G", "applies"),
    ("R602.6", "notches", "Notch depth limits in studs", "G", "applies"),
    ("R602.6.1", None, "Tie across cut or notched top plates", "G", "applies"),
    ("R602.7", None, "Header size and span by load", "G", "applies"),
    ("R602.7.1", None, "Single-member headers", "G", "applies"),
    ("R602.7.2", None, "Rim board headers", "G", "conditional"),
    ("R602.7.3", None, "Wood structural panel box headers", "G", "conditional"),
    ("R602.7.4", None, "Headers in nonbearing walls", "D", "applies"),
    ("R602.7.5", None, "Jack and full-height studs at header ends", "G", "applies"),
    ("R602.8", None, "Fireblocking in framed walls", "J", "applies"),
    ("R602.9", None, "Cripple wall framing", "G", "conditional"),
    ("R602.10", None, "Wall bracing method and documentation", "D", "applies"),
    ("R602.10.1", None, "Braced wall lines defined", "G", "applies"),
    ("R602.10.1.1", None, "Length of a braced wall line", "G", "applies"),
    ("R602.10.1.2", None, "Offsets along a braced wall line", "G", "applies"),
    ("R602.10.1.3", None, "Spacing of braced wall lines", "G", "applies"),
    ("R602.10.1.4", None, "Angled walls in a braced wall line", "G", "conditional"),
    ("R602.10.2", None, "Braced wall panel placement", "G", "applies"),
    ("R602.10.2.1", None, "Braced wall panel uplift load path", "J", "conditional"),
    ("R602.10.2.2", None, "Panel locations and end distances", "G", "applies"),
    ("R602.10.2.3", None, "Minimum number of panels per line", "G", "applies"),
    ("R602.10.3", None, "Required bracing length from wind and seismic", "G", "applies"),
    ("R602.10.4", None, "Bracing construction methods", "D", "applies"),
    ("R602.10.4.1", None, "Mixing bracing methods", "D", "applies"),
    ("R602.10.4.2", None, "Continuous sheathing methods", "D", "applies"),
    ("R602.10.4.3", None, "Interior finish on braced panels", "D", "applies"),
    ("R602.10.4.4", None, "Panel joint blocking", "D", "applies"),
    ("R602.10.5", None, "Minimum braced panel length", "G", "applies"),
    ("R602.10.5.1", None, "Contributing length of panels", "G", "applies"),
    ("R602.10.5.2", None, "Partial credit for short panels", "G", "applies"),
    ("R602.10.6", None, "Construction of alternate and portal-frame methods", "D", "conditional"),
    ("R602.10.7", None, "Ends of continuously sheathed lines", "G", "conditional"),
    ("R602.10.8", None, "Braced panel connections to floors and roof", "J", "applies"),
    ("R602.10.9", None, "Braced panel support on foundations", "J", "applies"),
    ("R602.10.10", None, "Cripple wall bracing", "G", "conditional"),
    ("R602.10.11", None, "Bracing in high seismic categories", "G", "conditional"),
    ("R602.11", None, "Wall anchorage to foundations", "D", "applies"),
    ("R602.12", None, "Alternative bracing path (simplified or practical)", "D", "applies"),
    # Virginia R602.12 practical wall bracing subsections (13VAC5-63-210 item 64)
    ("R602.12.1", None, "Practical bracing: sheathing materials and thickness", "D", "applies"),
    ("R602.12.2", "exterior panel length", "Practical bracing: exterior panel length by opening height", "G", "applies"),
    ("R602.12.2", "interior panel length", "Practical bracing: interior panel minimum length", "G", "applies"),
    ("R602.12.2", "panel construction", "Practical bracing: panel finish and joint rules", "D", "applies"),
    ("R602.12.3", None, "Practical bracing: circumscribed rectangle limits", "G", "applies"),
    ("R602.12.4", None, "Practical bracing: required length per rectangle side", "G", "applies"),
    ("R602.12.4.1", None, "Practical bracing: assign panels to rectangle sides", "G", "applies"),
    ("R602.12.4.2", None, "Practical bracing: contributing length meets required", "G", "applies"),
    ("R602.12.4.3", None, "Practical bracing: skewed rectangles sharing a side", "G", "conditional"),
    ("R602.12.5", None, "Practical bracing: cripple and walk-out basement walls", "G", "conditional"),
    ("R602.12.6", "corner distance", "Practical bracing: panel near each corner", "G", "applies"),
    ("R602.12.6", "panel gap", "Practical bracing: gap between adjacent panels", "G", "applies"),
    ("R602.12.6", "segment rule", "Practical bracing: long wall segments need a panel", "G", "applies"),
    ("R602.12.6.1", None, "Practical bracing: panels beside balloon-framed walls", "G", "conditional"),
    ("R602.12.7", None, "Practical bracing: panel connections", "J", "applies"),
    ("R602.12.8", None, "Practical bracing: panel support", "J", "applies"),
    # R603-R610 at section level (subsection split pending official text)
    ("R603", None, "Cold-formed steel wall framing (prescriptive limits)", "D", "conditional"),
    ("R604", None, "Wood structural panel sheathing grade and spans", "D", "applies"),
    ("R605", None, "Particleboard wall sheathing", "D", "conditional"),
    ("R606", None, "General masonry wall construction", "D", "conditional"),
    ("R607", None, "Glass unit masonry", "D", "conditional"),
    ("R608", None, "Exterior concrete wall construction", "D", "conditional"),
    ("R609", None, "Exterior windows and doors: performance and labels", "D", "applies"),
    ("R610", None, "Structural insulated panel walls", "D", "conditional"),
]

# Virginia amendment items for Chapter 6 in 13VAC5-63-210 section 310.8 (fetched 2026-10-12).
VA_AMENDMENTS = {
    "R602.10": ("modifies_text", "62", "Virginia restates R602.10: bracing per R602.10 or R602.12; the building official may require braced wall lines and panels on the construction documents with analysis, and may waive upper-floor analysis when upper openings do not exceed those below."),
    "R602.10.9": ("adds_exception", "63", "Adds an exception allowing post-installed adhesive anchors for masonry stem walls."),
    "R602.12": ("replaces_section", "64", "Replaces R602.12 and all subsections with Virginia practical wall bracing (SDC A and B, and detached SDC C)."),
}
VA_REPLACED_CHILD_PREFIX = "R602.12."
