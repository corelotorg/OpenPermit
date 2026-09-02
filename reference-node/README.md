# OpenPermit ORI Reference Node

A minimal, local-first implementation of the ORI Model Interface using the current MCP Python SDK and Streamable HTTP.

## 30-second run

```bash
python -m pip install -r conformance/requirements.txt -r reference-node/requirements.txt
python conformance/validate.py
python reference-node/smoke.py
python reference-node/server.py
```

Then inspect:

- MCP: `http://127.0.0.1:8000/mcp`
- Health: `http://127.0.0.1:8000/health`
- Discovery: `http://127.0.0.1:8000/.well-known/ori.json`
- State: append-only challenge/disposition events at `reference-node/state/events.jsonl`

## Run with Docker

```bash
docker build -f reference-node/Dockerfile -t openpermit-ori .
docker run --rm -p 8000:8000 openpermit-ori
```

No SaaS account, database, API key, model provider, or external service is required for reference mode.

## Public hostname

The MCP SDK protects Streamable HTTP deployments against DNS rebinding. For a real hostname, declare it explicitly:

```bash
docker run --rm -p 8000:8000 \
  -e ORI_PUBLIC_HOST=mcp.example.org \
  openpermit-ori
```

Optional browser origins can be supplied as a comma-separated `ORI_ALLOWED_ORIGINS` value.

## Implemented MCP tools

The source and smoke test currently enforce this exact tool surface:

- `ori_capabilities` — versions, endpoints, profiles, operations, legal-effect boundary.
- `ori_get` — retrieve an addressable object plus open challenges/dispositions.
- `ori_traverse` — cycle-safe traversal of ID-valued relationships.
- `ori_provenance` — source, jurisdiction, version and lineage context.
- `ori_verify` — structural schema verification; never legal approval by protocol.
- `ori_analyze_precedence` — DAG validation, topological order, float and critical path.
- `ori_challenge` — append a first-class challenge without editing the target.
- `ori_resolve_challenge` — append a disposition without deleting challenge history.
- `ori_list_profiles` — list published guidance profiles exposed by the reference node.

The node indexes machine-readable public profiles, jurisdiction inventories and conformance fixtures from the repository for `ori_get`/traversal. `ori_list_profiles` is intentionally narrower today and lists guidance profiles; inventory discovery is also available through the static corpus.

## Tests

```bash
python conformance/validate.py
python -m pytest -q reference-node/test_graph.py
python reference-node/smoke.py
```

The conformance harness includes positive schema fixtures and negative semantic fixtures proving rejection of mapping-as-fact, guidance promoted to a binding Requirement, challenge mutation of its target, and cyclic graphs declared as `PrecedenceGraph`.

## Legal and authority boundary

The node demonstrates ORI interfaces and conformance behavior. It does not determine legal applicability, create government approval, replace code officials, certify professional credentials, or convert guidance into binding law.
