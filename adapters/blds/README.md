# BLDS interchange adapter

**Status:** working adapter, v0.1 draft. **Role:** interchange adapter — not part of ORI Core.

This directory projects ORI `JurisdictionInventory` profiles (`profiles/jurisdictions/**` and the synthetic `profiles/examples/**`) into a BLDS-shaped companion CSV. It is here so systems that already ingest BLDS-shaped permit open data can join against ORI inventory without learning the ORI graph first.

- **BLDS** (Building & Land Development Specification, [permitdata.org](https://permitdata.org), `open-data-standards/permitdata.org`) is a useful permit open-data vocabulary. Its repository states it is **not actively maintained**. ORI maps to it; ORI is not a BLDS implementation and makes no BLDS certification claim.
- **Lineage:** the 2016 OpenPermit project published a BLDS-aligned permitting API specification (CC BY 3.0) and a .NET reference implementation (MIT). This adapter keeps that BLDS-mapping intent. That is lineage, not endorsement.
- **ORI's distinct value** is the authority- and evidence-bearing regulatory graph (sources, authorities, approvals, requirements, evidence, precedence, challenges). BLDS columns carry only part of that. The `ORI_*` columns keep the provenance BLDS cannot.

## Run

```bash
python -m pip install -r conformance/requirements.txt
python adapters/blds/export_blds_companion.py --out /tmp/ori-blds-companion.csv   # all profiles
python adapters/blds/export_blds_companion.py profiles/examples/example-city/residential-new-construction-example.json
python -m pytest -q adapters/blds
```

For the synthetic example jurisdiction the export writes 10 rows. Real-jurisdiction inventories, where present under `profiles/jurisdictions/`, are exported the same way.

## Refusal rules

The export is refused (exit 1) when:

1. a profile fails `spec/ori-jurisdiction-inventory-0.1.schema.json`; or
2. any approval, fee, or inspection row has no `source`, or cites a source id that is not declared in `sources[]` with a `locator`.

Rule 2 matters because the inventory schema leaves `fees[]` and `inspections[]` open (`additionalProperties: true`). The adapter will not emit an unsourced row.

## Honesty limits

- A fee-schedule row is not a fee collected on a permit. An inspection requirement is not an inspection result. An approval row is not an issued approval.
- `IssuedDate` and `StatusMapped` stay empty: inventory rows are not permit instances, and no BLDS status enumeration applies. Effective dates go to `ORI_EffectiveFrom`.
- Rates are copied, never computed into a `Fee` amount.
- No timing or shot-clock values are derived.
- Export output is not a legal determination (`ORI_LegalDetermination` carries the profile's `scope.legal_determination`).

Column-by-column mapping: [`FIELD_MAP.md`](FIELD_MAP.md).
