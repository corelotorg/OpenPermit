# ORI draft conformance

This directory contains the first executable conformance surface for the recovery-derived ORI core draft.

## Run

From the repository root:

```bash
python -m pip install -r conformance/requirements.txt
python conformance/validate.py
```

Expected result:

```text
PASS conformance/fixtures/challenge-valid.json
PASS conformance/fixtures/mapping-valid.json
PASS conformance/fixtures/verification-valid.json
```

## What this proves

The current harness proves only that fixture objects conform to `spec/ori-core-0.1.schema.json` under JSON Schema Draft 2020-12.

It does **not** prove legal correctness, jurisdictional applicability, factual truth, or regulatory approval.

## Next conformance layers

1. negative fixtures that MUST fail;
2. graph-edge referential integrity;
3. supersession/effective-time tests;
4. challenge immutability/history tests;
5. precedence DAG cycle detection and topological ordering;
6. derived critical-path/float tests;
7. JSON-LD round-trip tests;
8. source/provenance integrity fixtures;
9. profile tests for Virginia permitting and other jurisdictions;
10. model-interface capability discovery and MCP reference transport tests.

A future reference-node container SHOULD run this conformance suite as its startup smoke test.
