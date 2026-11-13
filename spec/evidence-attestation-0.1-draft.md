# ORI Evidence & Attestation — v0.1 Draft

Machine schema (DRAFT): `spec/ori-evidence-attestation-0.1.schema.json`. Conformance fixtures: `conformance/positive/evidence-*.json` and `conformance/negative/evidence-*.json` (rule `evidence-attestation-record`). Every Evidence and Attestation record carries `is_approval: false` and the label "Reviewer evidence, not approval".

ORI evidence is portable proof offered in support of an Assertion, Requirement, Verification, Decision or Challenge. This profile defines an open envelope for artifacts captured by humans, mobile devices, drones, sensors, BIM tools, laboratories, inspectors, engineers or other systems.

The protocol does not trust evidence merely because it is digitally signed, geolocated, produced by special hardware, or submitted by a credentialed actor. Those are separately verifiable properties.

## Evidence envelope

```yaml
id: urn:ori:evidence:...
type: Evidence
artifact: artifact id or content-addressed locator | unknown
captured_at: datetime | unknown
captured_by: actor/device/system id | unknown
spatial_anchor:
  type: parcel | address | world_point | ifc_element | model_object | document_page | region | route | view
  value: per-type value (see Spatial anchor values)
integrity:
  algorithm: sha256 | profile-defined
  digest: string (64 lowercase hex for sha256) | unknown
provenance:
  device: optional device identity
  software: optional software identity/version
  sensor: optional sensor identity/calibration record
  acquisition_method: photo | scan | measurement | model | document | attestation | other
  transformation_chain: [event ids]
attestations: [attestation ids]
source: [source ids]
geo_attestation: optional (see Geo-attestation)
element_location_match: optional (see Matching a world location to a model element)
```

### Spatial anchor values

| `type` | `value` |
|---|---|
| `ifc_element` | `ifc_global_id` (canonical 22-character IFC GlobalId, first character 0-3, the same pattern as review-comment and lifecycle records) and `model_version.sha256` (required; never `unknown`). An element is only meaningful inside one hosted model version. |
| `world_point` | `coordinates` (2 or 3 numbers, in the axis order of the stated CRS, as captured) and `crs` (identifier as given, or `unknown`). |
| `model_object` | `object_ref` and `model_version.sha256`. |
| `view` | `view_ref` and `model_version.sha256`. |
| `document_page` | `artifact_ref` and `page` (1-based). |
| `parcel` | `parcel_ref`, exactly as the jurisdiction states it. |
| `address` | `address_ref`. |
| `region`, `route` | profile-defined object. |

The core schema (`spec/ori-core-0.1.schema.json`) accepts the same typed object for `evidence.spatial_anchor` and still accepts a plain string as an opaque legacy reference.

## Geo-attestation

A geo-attested artifact SHOULD distinguish the following. The optional `geo_attestation` object carries them as fields:

| What | Field |
|---|---|
| claimed location | `claimed_location.coordinates` |
| observed device/sensor location | `observed_location.coordinates` |
| the coordinate system both are in | `crs`: an identifier exactly as the capturing system states it, or `unknown` |
| resolved parcel | `resolved_parcel_ref`, or `unknown` |
| location accuracy/uncertainty | `horizontal_accuracy_m`, `vertical_accuracy_m` (metres, or `unknown`) |
| capture time and time source | `captured_at`; `time_source`: `trusted_hardware`, `gnss`, `network`, `os`, `user_entry`, `unknown` |
| where the location came from | `location_source`: `trusted_hardware`, `os`, `network`, `user_entry`, `unknown` |
| transformation history after capture | `provenance.transformation_chain` |

`crs`, `horizontal_accuracy_m`, `location_source` and `time_source` are required whenever `geo_attestation` is present, and at least one location must be given. Each may be `unknown`. Coordinates are kept as captured; ORI does not reorder, reproject or round them.

The envelope MUST NOT serialize a low-confidence geolocation as exact merely because a coordinate exists. A location whose accuracy is `unknown` is kept, but it cannot be matched to a model element.

Resolving a parcel, address or jurisdiction from coordinates is itself a claim. Record the result in `resolved_parcel_ref` only when it was actually resolved, and otherwise leave it `unknown`.

## Matching a world location to a model element

Inspection evidence often needs to say which model element a photo or measurement shows. When the evidence links a world location to an IFC element, it carries `element_location_match`:

```yaml
element_location_match:
  ifc_global_id: canonical GlobalId
  model_version: {sha256: ...}
  model_georeference:            # omitted if no georeference was available
    ref: urn:ori:model-georeference:...
    status: crs_identified | local_only | none | unknown
    model_version: {sha256: ...}
  location_used: observed_location | claimed_location | unknown
  crs_transformation_ref: optional, see rule 4
  tolerance_m: number, required for a computed result
  method: computed | not_attempted
  match: consistent | inconsistent | unknown
  basis: [reasons], required when match is unknown
```

The georeference belongs to the hosted model for review, not to the evidence and not to any one exporter. It is described by a separate read-only record, `ModelGeoreference` (`spec/ori-model-georeference-0.1.schema.json`), for one hosted model version. See the Hosted model georeference section of `spec/model-interface-0.1-draft.md`.

Rules:

1. **Only an identified georeference supports a computed match.** `match` may be `consistent` or `inconsistent` only when `model_georeference.status` is `crs_identified`, `method` is `computed`, a `tolerance_m` is stated, and the referenced `ModelGeoreference` record can be checked.
2. **Everything else is `unknown`, never a failure.** If the georeference is `local_only`, `none`, `unknown` or missing, or the evidence `crs` is `unknown`, or its horizontal accuracy is `unknown`, then `match` is `unknown`. `basis` says why: `model_georeference_missing`, `model_georeference_local_only`, `model_georeference_none`, `model_georeference_unknown`, `evidence_crs_unknown`, `accuracy_unknown`, `location_missing`, `crs_differs_no_transformation` or `not_attempted`. The vocabulary has no `fail` value.
3. **One model version throughout.** The element, the `ifc_element` anchor (if used) and the georeference all name the same `model_version.sha256`. A georeference never carries over to another model version on its own, even if the geometry looks unchanged.
4. **CRS identifiers are compared as given.** If the evidence `crs` and the georeference CRS identifier are different strings, a computed match needs a stated `crs_transformation_ref`. ORI never rewrites an identifier into another authority, code or form to make them agree.
5. **No upgrade.** The inline `model_georeference.status` must equal the referenced record's status.
6. **Evidence, not a decision.** `consistent` is not approval and `inconsistent` is not a failure or a correction. Both are evidence for the reviewer or inspector, and the building official decides.

## Device and open-hardware profile

An open hardware implementation MAY publish:

- hardware/firmware identifiers and versions;
- secure-element/TPM attestation where available;
- sensor model and calibration state;
- boot/software measurement evidence;
- device public key or certificate chain;
- capture-event signature;
- monotonic counter or anti-replay data;
- environmental/sensor metadata;
- privacy-preserving location proof methods.

No specific vendor, secure element, TPM, phone, drone or sensor is required by ORI.

## Attestation object

```yaml
id: urn:ori:attestation:...
type: Attestation
subject: evidence/artifact/device/credential id
attested_by: actor/system/authority id
claim: {claim_type: snake_case name, value: optional}
method: signature | certificate | measurement | witness | professional_seal | other
issued_at: datetime
expires_at: datetime|null
evidence: [supporting ids]
verification_method: profile-defined
status: valid | invalid | expired | revoked | unverified
```

An attestation is a claim with provenance. Its legal or professional effect depends on the authority, credential, jurisdiction and applicable process.

## Third-party inspection use

Third-party inspection profiles SHOULD connect:

`credential → issuer → authorized scope → inspector → inspection event → geo-attested evidence → verification → authority acceptance/decision`

This allows portable inspection evidence without assuming that every jurisdiction accepts every credential or inspection provider.

## Privacy and minimization

Evidence profiles SHOULD collect only the precision and metadata required for the regulatory purpose. Public publication of exact residential location, biometric, device or credential metadata is not required by ORI. Implementations may separate public proofs from protected underlying evidence while preserving addressable provenance and verification status.
