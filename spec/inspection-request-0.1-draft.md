# ORI Inspection Request 0.1 (DRAFT)

Status: DRAFT. Request, not approval. Schema: `spec/ori-inspection-request-0.1.schema.json`. Fixtures: `verification/examples/inspection/`. Tests: `verification/tests/test_inspection_request.py`.

## 1. Problem

ORI already describes which inspections a permit requires (`inspection_requirement`, BLDS adapter) and how third-party inspection evidence is attested (`spec/evidence-attestation-0.1-draft.md`). It does not describe how a permit holder *asks* for an inspection or how the jurisdiction answers.

Today that request is re-keyed by hand into a portal, a phone line or a text message, one jurisdiction at a time. Each system has its own inspection codes, cut-off times and status words. A builder working in four jurisdictions keeps four sets of rules in their head.

## 2. What exists (survey, 2026-11-04)

Only two vendors publish a documented, public interface for an outside party to book an inspection.

| System | Public request interface | Notes |
|---|---|---|
| Accela Construct API v4 | Yes | Available dates, schedule and cancel open to citizen apps; update and result limited to agency apps. OAuth 2 user token plus app credentials. No documented result notification. [dates](https://developer.accela.com/docs/api_reference/v4.get.inspections.availableDates.html), [schedule](https://developer.accela.com/docs/api_reference/v4.put.inspections.id.schedule.html), [cancel](https://developer.accela.com/docs/api_reference/v4.delete.inspections.ids.cancel.html) |
| Oracle Public Sector Permitting | Yes, per customer | Three methods: preferred date, ready-by date, or a chosen slot. [create inspection](https://docs.oracle.com/en/cloud/saas/public-sector-compliance-regulation-common/25d/psrst/op-publicsectorinspections-post.html) |
| CentralSquare NaviLine | Phone-line interface, agency hosted | Permit, inspection code, date, AM/PM. Third-party access unclear. [CreateInspection](https://fusion.centralsquare.com/Fusion/Suite/NaviLine/Method/FusionServices.Controllers.IVRController.PostCreateInspection(System.Net.Http.Formatting.FormDataCollection)) |
| Tyler EnerGov | Licensed or partner access (unconfirmed) | [integration note](https://www.civicplus.help/seeclickfix/docs/tyler-enterprise-permitting-and-licensing-integration) |
| Cloudpermit | Inspector side only, no request booking, no webhooks | [public APIs](https://support.cloudpermit.com/support/solutions/articles/67000739679-getting-started-with-cloudpermit-public-apis) |
| OpenGov, Clariti, Salesforce Public Sector, Citizenserve, SmartGov, iWorQ, CityView | None documented publicly | Portal, phone or text |

Jurisdiction practice shows the same core fields everywhere: permit number, a short inspection code, a requested day, a cut-off time, and a rule that an unready inspection counts against the builder (for example [Spotsylvania County, VA](https://www.spotsylvania.va.us/DocumentCenter/View/34328/Residential-Scheduling-Instructions), [Prince William County, VA](https://www.pwcva.gov/department/development-services/schedule-inspection), [Austin, TX](https://www.austintexas.gov/page/schedule-building-inspection)).

No standard covers booking. BLDS publishes inspection *results* as open data and is no longer actively maintained ([repository](https://www.github.com/open-data-standards/permitdata.org)). Open311 GeoReport v2 is the closest request pattern: a list of request codes, a definition per code, a submit call ([GeoReport v2](https://webarchive.library.unt.edu/web/20170118233000mp_/http://wiki.open311.org/GeoReport_v2)). ICC 1205 and ANSI/RESNET/ICC 1450 cover how remote inspections are performed, not how they are booked.

## 3. Objects

**InspectionRequest** — what the permit holder asks for.

- `permit.authority_permit_number` and `inspection_type.native` exactly as the jurisdiction states them. A shared concept is attached only through a `MappingAssertion` (`inspection_type.native.mapping`), never by replacing the native code.
- `requested_window` with `method`: `request` (preferred date), `ready_by` (authority picks), or `slot` (a slot the authority offered).
- `readiness`: the requester's attestation that work is ready, with optional evidence and prior inspections. It is an Assertion, not a fact.
- `site_access`: contact and instructions. Lockbox or gate codes are never carried; `access_secret_ref` points to a secured channel.
- `modality`: `in_person`, `remote_virtual` or `third_party`. Third party requires the credential chain from the evidence-attestation profile.
- `idempotency_key`: the same request sent twice books once.
- `reinspection_of`, `callback_url`: optional.

**InspectionEvent** — what happens next, recorded by whoever observed it.

- `status`: `requested`, `acknowledged`, `scheduled`, `rescheduled`, `declined`, `cancelled`, `completed`, `unknown`.
- `native_status` is required: the jurisdiction's own word is kept beside the mapped one.
- On `completed`: `result` (`approved`, `approved_with_conditions`, `disapproved`, `partial`, `not_ready`, `not_performed`) and `native_result`, both required. Anything short of approval requires `corrections`.
- `final` marks the inspection that closes that type for the permit.
- Events are append-only; a correction `supersedes` an earlier event.

## 4. Projections

A REST projection, kept small on purpose:

| Call | Purpose |
|---|---|
| `GET /permits/{authority_permit_number}/inspection-options` | Inspection types open on this permit, cut-off rules, available dates |
| `POST /inspection-requests` | Submit an InspectionRequest; same `idempotency_key` returns the original |
| `GET /inspection-requests/{request_id}/events` | Event history |
| `POST /inspection-requests/{request_id}/cancel` | Cancel, with a reason |
| Callback to `callback_url` | The jurisdiction posts each InspectionEvent |

An MCP projection exposes the same four operations as tools. Adapters map Accela, Oracle and NaviLine calls onto these objects; they are evidence of mapping, not endorsements.

## 5. Rules

1. A request never schedules anything by itself. The jurisdiction's system remains the authority for availability, scheduling and results.
2. Missing information yields `unknown`, never a failure.
3. Native codes and statuses are always preserved.
4. No secrets in payloads.
5. Machine output is evidence for a human reviewer, never approval.

## 6. Open questions

- Should `inspection-options` publish cut-off times as data, so a client can warn before a late request?
- How a jurisdiction authenticates a requester across systems (contractor licence, permit PIN, or an ORI credential).
- Whether `not_ready` should carry a fee reference, since many jurisdictions charge for it.
