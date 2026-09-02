# OpenPermit Ontology Specification Outline

This outline treats the ontology as a first-class artifact, independent of runtime or deployment assumptions. It enumerates modular domains, key classes, cross-cutting properties, domain properties, typed relationships, and the minimum normative set for v0.1.

## Machine-readable source of truth
- YAML index: [`ontology/index.yaml`](../../ontology/index.yaml) defines domains, classes, properties, and relationships with shared namespaces.
- JSON-LD context: [`contexts/ontology.jsonld`](../../contexts/ontology.jsonld) projects the ontology into linked data terms for payloads and adapters.

## 1. Modular Domains
1. Core Graph
2. Identity & Authority
3. Jurisdiction & Governance
4. Built Assets
5. Permit & Application
6. Review & Decision
7. Codes & Policy References
8. Inspection
9. Fees & Finance
10. Artifacts & Deliverables
11. Communication & Threading
12. Integration & Projection

## 2. Classes by Domain
### 2.1 Core Graph
- Node
- Identifier
- Edge
- Event
- Assertion
- State
- Status
- Version
- TimeInstant
- TimeInterval
- SpatialAnchor
- Confidence

### 2.2 Identity & Authority
- Actor
- Person
- Organization
- Department
- Role
- Authority
- Credential (non-auth semantic credential, e.g., “Inspector Level II”)

### 2.3 Jurisdiction & Governance
- Jurisdiction
- AuthorityPolicy
- ServiceArea
- Office
- GoverningBody
- RegulatoryProgram

### 2.4 Built Assets
- BuiltAsset
- Site
- Parcel
- Address
- Building
- Structure
- BuildingElement
- Space
- Zone
- System (MEP or other)
- AssetLocation (semantic location, not geometry engine)
- GeometryReference (pointer to IFC/City model IDs)

### 2.5 Permit & Application
- Permit
- PermitApplication
- PermitType
- ScopeOfWork
- WorkItem
- Project
- Applicant
- Owner
- Contractor
- Submission
- Revision
- Requirement
- ConditionOfPermit

### 2.6 Review & Decision
- Review
- ReviewPackage
- ReviewComment
- ReviewFinding
- Disposition
- Approval
- Rejection
- RequestForInformation
- CorrectionNotice
- Condition
- Task (actionable requirement derived from review)

### 2.7 Codes & Policy References
- Code
- CodeEdition
- CodeSection
- CodeCitation
- LocalAmendment
- Interpretation
- Policy
- Standard
- ReferenceDocument

### 2.8 Inspection
- Inspection
- InspectionRequest
- InspectionType
- InspectionResult
- Finding
- Deficiency
- Verification
- Reinspection

### 2.9 Fees & Finance
- FeeItem
- FeeCode
- FeeSchedule
- FeeRule
- Account
- AccountCode
- Charge
- Payment
- Refund
- Waiver
- LedgerEntry

### 2.10 Artifacts & Deliverables
- Artifact
- ArtifactType
- Document
- Model
- PlanSet
- Image
- Attachment
- Record
- Receipt
- Invoice

### 2.11 Communication & Threading
- CommunicationThread
- CommunicationMessage
- Channel
- Recipient
- MessageDelivery
- Notification

### 2.12 Integration & Projection
- ExternalSystem
- Provider
- Adapter
- Endpoint
- EventEnvelope
- Projection
- EntitySet
- FieldMapping

## 3. Core Properties (Cross-Cutting)
These apply broadly where relevant:
- `id` (string; globally unique IRI/URN recommended)
- `type` (class name / IRI)
- `label` (human-readable)
- `description` (human-readable)
- `createdAt` (datetime)
- `updatedAt` (datetime)
- `effectiveAt` (datetime)
- `expiresAt` (datetime)
- `status` (Status)
- `state` (State)
- `version` (Version)
- `confidence` (Confidence)
- `source` (Artifact | ExternalSystem | Actor)
- `identifier` (Identifier[])
- `jurisdiction` (Jurisdiction)
- `tags` (string[])
- `language` (BCP-47)

## 4. Domain Properties (Key Fields)
### 4.1 SpatialAnchor
- `anchorType` (enum: ifc_element, world_point, address_point, view_context, parcel)
- `globalId` (string; for IFC element refs)
- `modelRef` (Model | Artifact)
- `position` (x,y,z) (optional)
- `address` (Address) (optional)
- `parcel` (Parcel) (optional)
- `viewRef` (string) (optional)
- `radius` (number) (optional)

### 4.2 Permit / Application
- `permitNumber`
- `permitType` (PermitType)
- `applicationDate`
- `issuedDate`
- `closedDate`
- `scopeOfWork` (ScopeOfWork)
- `appliesTo` (BuiltAsset | Parcel | Site)
- `applicant` (Applicant)
- `owner` (Owner)
- `contractor` (Contractor)
- `requirements` (Requirement[])
- `conditions` (ConditionOfPermit[])
- `submissions` (Submission[])
- `revisions` (Revision[])

### 4.3 Review / Decision
- `reviewType`
- `reviewer` (Actor/Role)
- `reviewedArtifact` (Artifact | Revision)
- `comments` (ReviewComment[])
- `findings` (ReviewFinding[])
- `disposition` (Disposition)
- `decisionDate`
- `conditions` (Condition[])
- `tasks` (Task[])

### 4.4 CodeCitation
- `code` (Code)
- `edition` (CodeEdition)
- `section` (CodeSection)
- `citationText`
- `jurisdictionApplicability` (Jurisdiction)
- `effectiveDate`

### 4.5 Inspection
- `inspectionType` (InspectionType)
- `requestedBy` (Actor)
- `scheduledFor` (datetime)
- `performedAt` (datetime)
- `performedBy` (Actor)
- `result` (InspectionResult)
- `findings` (Finding[])
- `verifications` (Verification[])
- `reinspectionOf` (Inspection | null)

### 4.6 FeeItem / Finance
- `feeCode` (FeeCode)
- `feeSchedule` (FeeSchedule)
- `amount` (number)
- `currency` (string)
- `basis` (enum: flat, count, sqft, valuation, custom)
- `quantity` (number)
- `accountCode` (AccountCode)
- `assessedAt` (datetime)
- `assessedBy` (Jurisdiction | Actor)
- `triggeredBy` (InspectionResult | Disposition | Requirement | Event)
- `waivedBy` (Waiver | null)
- `refundedBy` (Refund | null)

### 4.7 Communication
- `threadKey`
- `topic`
- `inReplyTo` (CommunicationMessage | null)
- `sentBy` (Actor)
- `sentTo` (Recipient[])
- `channel` (Channel)
- `subject`
- `body`
- `attachments` (Artifact[])
- `deliveryStatus` (enum)
- `anchor` (SpatialAnchor)
- `targets` (Node[])

### 4.8 Integration / Projection
- `systemName`
- `providerName`
- `endpointUrl`
- `entitySetName`
- `fieldMappings` (FieldMapping[])
- `eventSchemaVersion`
- `externalId`

## 5. Typed Relationships (Edges)
Below are typed relationships (predicates) forming the golden thread.

### 5.1 Provenance & Evolution
- `derivedFrom` (Node → Node)
- `supersedes` (Node → Node)
- `versionOf` (Node → Node)
- `generatedBy` (Node → Event)
- `recordedBy` (Event → Actor | System)

### 5.2 Authority & Responsibility
- `asserts` (Actor | Authority → Assertion)
- `authorizedBy` (Assertion → Authority)
- `withinJurisdiction` (Node → Jurisdiction)
- `assignedTo` (Task → Actor | Role)

### 5.3 Targeting & Scope
- `targets` (Assertion | Event → BuiltAsset | BuildingElement | Parcel | SpatialAnchor)
- `appliesTo` (Permit | Requirement | Condition → BuiltAsset | Parcel | Project)
- `locatedAt` (Node → Address | Parcel | SpatialAnchor)
- `concerns` (CommunicationThread → Node)

### 5.4 Review, Decision, Compliance
- `reviews` (Review → Submission | Revision | Artifact)
- `hasComment` (Review → ReviewComment)
- `hasFinding` (Review → ReviewFinding)
- `resultsIn` (Review | Finding | InspectionResult → Disposition | Task | FeeItem | InspectionRequest)
- `requires` (Requirement → ArtifactType | Verification | InspectionType)
- `satisfies` (Artifact | Verification → Requirement)
- `justifiedBy` (Assertion | Finding → CodeCitation | Policy | Standard)
- `conditions` (Disposition → Condition)

### 5.5 Inspection Semantics
- `requestedFor` (InspectionRequest → Permit | BuiltAsset)
- `performedOn` (Inspection → BuiltAsset | BuildingElement | Parcel)
- `verifies` (Inspection | Verification → Requirement | Condition)
- `finds` (Inspection → Finding | Deficiency)
- `reinspectionOf` (Inspection → Inspection)

### 5.6 Finance Semantics
- `assesses` (Jurisdiction | Authority → FeeItem)
- `triggeredBy` (FeeItem → Event | Disposition | InspectionResult | Requirement)
- `mapsToAccount` (FeeItem → AccountCode | Account)
- `paidBy` (Payment → Actor | Organization)
- `pays` (Payment → FeeItem)
- `waives` (Waiver → FeeItem)
- `refunds` (Refund → FeeItem)

### 5.7 Communication Semantics
- `inThread` (CommunicationMessage → CommunicationThread)
- `repliesTo` (CommunicationMessage → CommunicationMessage)
- `sentTo` (CommunicationMessage → Recipient | Department | Organization | Role)
- `deliveredVia` (CommunicationMessage → Channel)
- `references` (CommunicationMessage → Artifact | Node)
- `notifies` (Notification → Actor | Role)

### 5.8 Integration & Projection
- `routedTo` (EventEnvelope | Message → Adapter | ExternalSystem | Provider)
- `exposedAs` (OntologyClass → EntitySet)
- `mapsFieldTo` (FieldMapping → FieldMapping)
- `hasExternalId` (Node → Identifier)

## 6. Minimum Normative Set (v0.1 Must-Have)
### Must-have Classes
- Permit, PermitApplication, Submission, Revision
- Jurisdiction, Authority, Actor, Role
- BuiltAsset, Parcel, Address, BuildingElement, SpatialAnchor
- Review, ReviewComment, Disposition
- CodeCitation
- InspectionRequest, Inspection, InspectionResult
- FeeItem, FeeCode, AccountCode
- CommunicationThread, CommunicationMessage
- Artifact

### Must-have Relationships
- `asserts`, `targets`, `justifiedBy`, `resultsIn`
- `appliesTo`, `withinJurisdiction`
- `verifies`, `triggeredBy`, `mapsToAccount`
- `inThread`, `repliesTo`, `references`
- `derivedFrom`, `supersedes`

---

Recovery provenance: copied verbatim from unmerged PR #103 head `4c91972ba51c126c1ad2f23692bfc3105e55fe78`, original path `docs/ontology/ontology-specification.md`. This file is quarantined evidence, not the current normative ORI specification.
