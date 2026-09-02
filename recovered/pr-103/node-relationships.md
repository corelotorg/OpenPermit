# Spatial-Located Chat Anchors

Every chat entry is a domain event anchored to:
- an IFC element (`anchor.type = ifc_element`, `anchor.globalId`)
- a world point (`anchor.type = world_point`, `anchor.position`)
- a view context (`anchor.type = view`, `anchor.camera`)

Threads are derived by `threadKey`:
- `ifc:{GlobalId}`
- `wp:{rounded_position_hash}`
- `view:{camera_hash}`

The chat timeline is not the record—the record is the set of emitted artifacts:
- IFC annotations (IfcComment + IfcApproval)
- JSON-LD event packets
- append-only local log (JSONL)

# Node Types and Typed Edges (Golden Thread)

## Node Types (minimum set)
- **Asset nodes:** `IfcElement`, `IfcSpace`, `Parcel`, `Address`
- **Authority nodes:** `Reviewer`, `PermitTech`, `Inspector`, `Builder`, `Jurisdiction`
- **Assertion nodes:** `ReviewComment`, `Approval/Disposition`, `InspectionRequest`, `InspectionResult`, `FeeItem`
- **Reference nodes:** `CodeCitation`, `Policy`, `Standard`
- **Document nodes:** `PermitApplication`, `PlanSet`, `ModelRevision`, `Invoice/Receipt`

## Typed Edges (minimum set)
- `asserts` (Authority → Assertion)
- `targets` (Assertion → Asset / Location)
- `justifiedBy` (Assertion → CodeCitation / Policy)
- `resultsIn` (Assertion → InspectionRequest / FeeItem / Task)
- `mapsTo` (FeeItem → FeeCode / AccountCode)
- `supersedes` (ModelRevision → ModelRevision)
- `derivedFrom` (Any → Source Artifact)
- `routedTo` (Event → ProviderNode / BuilderNode)

**The ontology defines reality. The viewer is disposable.**

---

Recovery provenance: copied from unmerged PR #103 head `4c91972ba51c126c1ad2f23692bfc3105e55fe78`, original path `docs/ontology/node-relationships.md`. Quarantined evidence; not automatically normative.
