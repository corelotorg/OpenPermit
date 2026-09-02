# ORI Evidence & Attestation — v0.1 Draft

ORI evidence is portable proof offered in support of an Assertion, Requirement, Verification, Decision or Challenge. This profile defines an open envelope for artifacts captured by humans, mobile devices, drones, sensors, BIM tools, laboratories, inspectors, engineers or other systems.

The protocol does not trust evidence merely because it is digitally signed, geolocated, produced by special hardware, or submitted by a credentialed actor. Those are separately verifiable properties.

## Evidence envelope

```yaml
id: stable identifier
type: Evidence
artifact: artifact id or content-addressed locator
captured_at: datetime
captured_by: actor/device/system id
spatial_anchor:
  type: parcel | address | world_point | ifc_element | model_object | region | route | view
  value: profile-defined value
integrity:
  algorithm: sha256 | profile-defined
  digest: string
provenance:
  device: optional device identity
  software: optional software identity/version
  sensor: optional sensor identity/calibration record
  acquisition_method: photo | scan | measurement | model | document | attestation | other
  transformation_chain: [event ids]
attestations: [attestation ids]
source: [source ids]
```

## Geo-attestation

A geo-attested artifact SHOULD distinguish:

- claimed location;
- observed device/sensor location;
- resolved parcel/address/jurisdiction;
- location accuracy/uncertainty;
- capture time and time source;
- whether the location was available from trusted hardware, operating system, network inference or user entry;
- transformation history after capture.

The envelope MUST NOT serialize a low-confidence geolocation as exact merely because a coordinate exists.

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
id: stable identifier
type: Attestation
subject: evidence/artifact/device/credential id
attested_by: actor/system/authority id
claim: typed claim
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
