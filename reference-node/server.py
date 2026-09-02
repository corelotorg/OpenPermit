#!/usr/bin/env python3
"""OpenPermit / ORI zero-ceremony reference node.

Public semantics, local-first runtime. MCP is served over Streamable HTTP at /mcp.
The node indexes repository JSON objects, preserves provenance boundaries, and stores
challenge records append-only in reference-node/state/challenges.jsonl.
"""

from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = Path(os.getenv("ORI_STATE_DIR", ROOT / "reference-node" / "state"))
CHALLENGE_LOG = STATE_DIR / "challenges.jsonl"
ORI_VERSION = "0.1.0-draft"
IMPLEMENTATION_VERSION = "0.1.0"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _load_documents() -> list[tuple[Path, Any]]:
    candidates: list[Path] = []
    for base in [ROOT / "profiles", ROOT / "conformance" / "fixtures"]:
        if base.exists():
            candidates.extend(sorted(base.rglob("*.json")))
    docs: list[tuple[Path, Any]] = []
    for path in candidates:
        try:
            docs.append((path, _read_json(path)))
        except (OSError, json.JSONDecodeError):
            continue
    return docs


def _build_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path, doc in _load_documents():
        for obj in _iter_dicts(doc):
            object_id = obj.get("id")
            if isinstance(object_id, str):
                enriched = dict(obj)
                enriched.setdefault("_source_path", str(path.relative_to(ROOT)))
                index[object_id] = enriched
    for challenge in _read_challenges():
        challenge_id = challenge.get("id")
        if isinstance(challenge_id, str):
            index[challenge_id] = challenge
    return index


def _read_challenges() -> list[dict[str, Any]]:
    if not CHALLENGE_LOG.exists():
        return []
    items: list[dict[str, Any]] = []
    try:
        with CHALLENGE_LOG.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return items


def _append_challenge(record: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with CHALLENGE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def _warnings_for(obj: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if obj.get("status") in {"draft", "recovery-inventory", "public-working-draft"}:
        warnings.append("Object is not a final normative release.")
    if obj.get("authority_classification") == "federal_guidance":
        warnings.append("Federal guidance is not silently promoted to binding local law.")
    if obj.get("confidence") is not None and isinstance(obj.get("confidence"), (int, float)) and obj["confidence"] < 0.8:
        warnings.append("Object carries low confidence and should be independently checked.")
    return warnings


def _envelope(operation: str, data: Any, *, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": operation,
        "data": data,
        "warnings": warnings or [],
        "conformance": {
            "ori_version": ORI_VERSION,
            "implementation": "openpermit-reference-node",
            "implementation_version": IMPLEMENTATION_VERSION,
        },
    }


mcp = MCPServer(
    "OpenPermit ORI Reference Node",
    version=IMPLEMENTATION_VERSION,
    instructions=(
        "Preserve source, authority, jurisdiction and version. Distinguish mappings and assertions "
        "from authoritative source objects. Treat verification as verification, not legal approval. "
        "Retrieve open challenges before presenting a disputed conclusion as settled."
    ),
)


@mcp.tool()
def ori_capabilities() -> dict[str, Any]:
    """Return ORI version, public capabilities, profiles and conformance surfaces."""
    profiles = []
    for path, doc in _load_documents():
        if isinstance(doc, dict) and doc.get("type") == "GuidanceProfile":
            profiles.append({"id": doc.get("id"), "version": doc.get("version"), "status": doc.get("status"), "path": str(path.relative_to(ROOT))})
    return _envelope(
        "ori.capabilities",
        {
            "mcp_transport": "streamable-http",
            "mcp_path": "/mcp",
            "health_path": "/health",
            "discovery_path": "/.well-known/ori.json",
            "operations": [
                "ori.capabilities",
                "ori.get",
                "ori.traverse",
                "ori.provenance",
                "ori.verify",
                "ori.challenge",
                "ori.list_profiles",
            ],
            "profiles": profiles,
            "challenge_log": "append-only-local-jsonl",
            "legal_effect": "none-by-protocol",
        },
    )


@mcp.tool()
def ori_get(object_id: str) -> dict[str, Any]:
    """Get one addressable ORI object and surface draft/guidance warnings."""
    obj = _build_index().get(object_id)
    if obj is None:
        return {"ok": False, "operation": "ori.get", "error": "not_found", "object_id": object_id}
    open_challenges = [c for c in _read_challenges() if c.get("subject") == object_id and c.get("status") in {"open", "answered"}]
    return _envelope("ori.get", {"object": obj, "open_challenges": open_challenges}, warnings=_warnings_for(obj))


@mcp.tool()
def ori_list_profiles() -> dict[str, Any]:
    """List available public ORI profiles with authority classification and legal boundary."""
    profiles = []
    for path, doc in _load_documents():
        if isinstance(doc, dict) and doc.get("type") == "GuidanceProfile":
            profiles.append(
                {
                    "id": doc.get("id"),
                    "title": doc.get("title"),
                    "version": doc.get("version"),
                    "status": doc.get("status"),
                    "authority_classification": doc.get("authority_classification"),
                    "legal_boundary": doc.get("legal_boundary"),
                    "path": str(path.relative_to(ROOT)),
                }
            )
    return _envelope("ori.list_profiles", profiles)


@mcp.tool()
def ori_provenance(object_id: str) -> dict[str, Any]:
    """Return provenance, source, jurisdiction, version and supersession context for an ORI object."""
    obj = _build_index().get(object_id)
    if obj is None:
        return {"ok": False, "operation": "ori.provenance", "error": "not_found", "object_id": object_id}
    data = {
        "id": object_id,
        "source": obj.get("source", []),
        "derived_from": obj.get("derived_from", obj.get("derivedFrom", [])),
        "supersedes": obj.get("supersedes", []),
        "jurisdiction": obj.get("jurisdiction", []),
        "version": obj.get("version"),
        "effective_from": obj.get("effective_from"),
        "effective_to": obj.get("effective_to"),
        "authority_classification": obj.get("authority_classification"),
        "source_path": obj.get("_source_path"),
    }
    return _envelope("ori.provenance", data, warnings=_warnings_for(obj))


@mcp.tool()
def ori_traverse(start_id: str, relationship: str | None = None, max_depth: int = 2) -> dict[str, Any]:
    """Cycle-safely traverse ID-valued relationships from one ORI object."""
    max_depth = max(0, min(max_depth, 8))
    index = _build_index()
    if start_id not in index:
        return {"ok": False, "operation": "ori.traverse", "error": "not_found", "object_id": start_id}

    visited = {start_id}
    queue = deque([(start_id, 0)])
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []

    while queue:
        current_id, depth = queue.popleft()
        current = index[current_id]
        nodes.append({"id": current_id, "type": current.get("type"), "label": current.get("title") or current.get("label"), "depth": depth})
        if depth >= max_depth:
            continue
        for key, value in current.items():
            if key.startswith("_") or (relationship is not None and key != relationship):
                continue
            refs: list[str] = []
            if isinstance(value, str) and value in index:
                refs = [value]
            elif isinstance(value, list):
                refs = [v for v in value if isinstance(v, str) and v in index]
            for target_id in refs:
                edges.append({"from": current_id, "relationship": key, "to": target_id})
                if target_id not in visited:
                    visited.add(target_id)
                    queue.append((target_id, depth + 1))
    return _envelope("ori.traverse", {"start": start_id, "nodes": nodes, "edges": edges, "max_depth": max_depth})


@mcp.tool()
def ori_verify(object_id: str) -> dict[str, Any]:
    """Run structural schema validation for a public ORI object; this is not legal approval."""
    obj = _build_index().get(object_id)
    if obj is None:
        return {"ok": False, "operation": "ori.verify", "error": "not_found", "object_id": object_id}

    if obj.get("type") == "GuidanceProfile":
        schema_path = ROOT / "spec" / "ori-guidance-profile-0.1.schema.json"
    else:
        schema_path = ROOT / "spec" / "ori-core-0.1.schema.json"

    schema = _read_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(obj), key=lambda err: list(err.path))
    result = {
        "subject": object_id,
        "validator": "jsonschema.Draft202012Validator",
        "schema": str(schema_path.relative_to(ROOT)),
        "outcome": "pass" if not errors else "fail",
        "errors": [
            {"path": "/".join(str(p) for p in err.path) or "<root>", "message": err.message}
            for err in errors
        ],
        "legal_approval": False,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    return _envelope("ori.verify", result, warnings=["Structural conformance does not prove legal correctness, applicability, factual truth, or approval."])


@mcp.tool()
def ori_challenge(subject_id: str, challenged_by: str, grounds: str, statement: str, evidence: list[str] | None = None) -> dict[str, Any]:
    """Append a first-class challenge without mutating the challenged object."""
    index = _build_index()
    if subject_id not in index:
        return {"ok": False, "operation": "ori.challenge", "error": "subject_not_found", "subject_id": subject_id}
    now = datetime.now(timezone.utc)
    sequence = len(_read_challenges()) + 1
    challenge = {
        "id": f"ori:challenge:{now.strftime('%Y%m%dT%H%M%SZ')}:{sequence}",
        "type": "Challenge",
        "version": "1.0.0",
        "effective_from": now.isoformat(),
        "effective_to": None,
        "jurisdiction": [],
        "source": [],
        "derived_from": [],
        "supersedes": [],
        "metadata": {"reference_node": True},
        "subject": subject_id,
        "challenged_by": challenged_by,
        "grounds": grounds,
        "statement": statement,
        "evidence": evidence or [],
        "status": "open",
        "created_at": now.isoformat(),
    }
    _append_challenge(challenge)
    return _envelope("ori.challenge", challenge)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok", "service": "openpermit-reference-node", "ori_version": ORI_VERSION})


@mcp.custom_route("/.well-known/ori.json", methods=["GET"])
async def discovery(request: Request) -> Response:
    return JSONResponse(ori_capabilities()["data"])


def _security() -> TransportSecuritySettings:
    public_host = os.getenv("ORI_PUBLIC_HOST", "localhost").strip()
    hosts = ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*", "[::1]", "[::1]:*"]
    origins = ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]
    if public_host and public_host not in {"localhost", "127.0.0.1", "::1"}:
        hosts.extend([public_host, f"{public_host}:*"])
        origins.extend([f"https://{public_host}", f"https://{public_host}:*"])
    extra_origins = [x.strip() for x in os.getenv("ORI_ALLOWED_ORIGINS", "").split(",") if x.strip()]
    origins.extend(extra_origins)
    return TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins)


app = mcp.streamable_http_app(
    json_response=True,
    stateless_http=True,
    transport_security=_security(),
    host=os.getenv("ORI_BIND_HOST", "0.0.0.0"),
)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("ORI_BIND_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        json_response=True,
        stateless_http=True,
        transport_security=_security(),
    )
