# ORI JurisdictionInventory → BLDS companion CSV field map

**Status:** complete for `export_blds_companion.py` v0.1 (interchange adapter).
**Input:** ORI `JurisdictionInventory` 0.1 (`spec/ori-jurisdiction-inventory-0.1.schema.json`).
**BLDS:** permitdata.org vocabulary, used for column names only; BLDS is not actively maintained.

One output row per `approvals[]`, `fees[]`, and `inspections[]` item, in that order.

## BLDS-shaped columns

| Column | Value |
| --- | --- |
| `PermitNum` | `ORI:{item.id}` |
| `Description` | `item.label` |
| `IssuedDate` | empty (inventory rows are not issued permits) |
| `StatusCurrent` | profile `status` (e.g. `public-working-draft`) |
| `StatusMapped` | empty (no BLDS status enum applies to inventory rows) |
| `PermitClass` | profile `scope.domain` |
| `PermitClassMapped` | `Residential` when `scope.domain` starts with `residential`, else empty |
| `WorkClass` | profile `scope.project_type` |
| `WorkClassMapped` | `New` when `scope.project_type` starts with `new_`, else empty |
| `PermitType` | `approval_requirement` / `fee_schedule_item` / `inspection_requirement` |
| `PermitTypeMapped` | `ApprovalRequirement` / `FeeScheduleItem` / `InspectionRequirement` |
| `PermitTypeDesc` | `item.label` |
| `Fee` | fee `amount` when present; empty for rate-based fees and non-fee rows |
| `Link` | `locator` of the item's first cited source |
| `Publisher` | `publisher` of the item's first cited source |
| `LastUpdated` | profile `as_of` |
| `OriginalCity` | `jurisdiction.name` |
| `OriginalState` | `jurisdiction.state` (as written in the profile) |

## ORI provenance columns

| Column | Value |
| --- | --- |
| `ORI_Id` | `item.id` |
| `ORI_InventoryId` | profile `id` |
| `ORI_InventoryType` | same as `PermitType` |
| `ORI_Jurisdiction` | `jurisdiction.id` |
| `ORI_AuthorityId` | `item.authority` (approvals) |
| `ORI_SourceIds` | all cited source ids, `;`-separated |
| `ORI_SourceLocators` | locators for those ids, same order |
| `ORI_EffectiveFrom` | `item.effective_from`, else first source `effective_from` |
| `ORI_Amount` | fee `amount` |
| `ORI_Rate` / `ORI_RateUnit` / `ORI_Minimum` | fee `rate` / `rate_unit` / `minimum` |
| `ORI_Currency` | fee `currency` |
| `ORI_ProfileStatus` | profile `status` |
| `ORI_Completeness` | `scope.completeness` |
| `ORI_LegalDetermination` | `scope.legal_determination` (`true`/`false`) |
