# Canonical Civic Runtime (No Lock-in)

To prevent proprietary lock-in at the optimization/runtime stage, OpenPermit’s canonical civic deployment model is explicitly open, Linux-friendly, container-friendly, and browser-native.

**Canonical formats**
- IFC / CityGML (legal geometry + semantics)
- OpenUSD (scene graph interchange bridge)
- glTF 2.0 (browser delivery)
- JSON-LD (linked data events + provenance)
- XBRL mapping (financial facts where applicable)

**Canonical tooling**
- Headless conversion (Blender/BPY or VTK)
- Optimization (meshoptimizer / Draco)
- Web runtime (Xeokit / IFC.js for BIM)
- Geospatial runtime (CesiumJS with 3D Tiles)

Unity is permitted as a *reference authoring client*, but may never be required to view, validate, or audit permit data.

## Anti-Lock-In Policy
**Anti-Lock-In Principle:**  
No OpenPermit implementation may require a proprietary runtime, optimizer, or operating system to *view*, *validate*, or *audit* permit data. Proprietary tools may be used as optional reference clients, but all authoritative outputs must be exportable to open, royalty-free formats suitable for browser-based inspection.

---

Recovery provenance: copied from unmerged PR #103 head `4c91972ba51c126c1ad2f23692bfc3105e55fe78`, original path `docs/architecture/civic-runtime-stack.md`. Quarantined evidence; formats/tool choices require current revalidation before promotion.
