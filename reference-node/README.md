# OpenPermit ORI Reference Node

A minimal, local-first implementation of the ORI Model Interface using the current MCP Python SDK and Streamable HTTP.

## Run with Python

```bash
python -m pip install -r reference-node/requirements.txt
python reference-node/server.py
```

Defaults:

- MCP: `http://127.0.0.1:8000/mcp`
- Health: `http://127.0.0.1:8000/health`
- Discovery: `http://127.0.0.1:8000/.well-known/ori.json`
- State: append-only challenges at `reference-node/state/challenges.jsonl`

## Run with Docker

```bash
docker build -f reference-node/Dockerfile -t openpermit-ori .
docker run --rm -p 8000:8000 openpermit-ori
```

No SaaS account, database, API key, model provider, or external service is required for the reference mode.

## Public hostname

The MCP SDK protects Streamable HTTP deployments against DNS rebinding. For a real hostname, declare it explicitly:

```bash
docker run --rm -p 8000:8000 \
  -e ORI_PUBLIC_HOST=mcp.example.org \
  openpermit-ori
```

Optional browser origins can be supplied as a comma-separated `ORI_ALLOWED_ORIGINS` value.

## Tools

- `ori_capabilities`
- `ori_get`
- `ori_traverse`
- `ori_provenance`
- `ori_verify`
- `ori_challenge`
- `ori_list_profiles`

The node indexes machine-readable public profiles and conformance fixtures from the repository. It is intentionally small: runtime convenience must not become the ontology.

## Legal and authority boundary

The node demonstrates ORI interfaces and conformance behavior. It does not determine legal applicability, create government approval, replace code officials, certify professional credentials, or convert guidance into binding law.
