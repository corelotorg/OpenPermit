#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util
import os
import tempfile
from pathlib import Path

from mcp import Client

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "reference-node" / "server.py"
os.environ["ORI_STATE_DIR"] = tempfile.mkdtemp(prefix="ori-state-")

spec = importlib.util.spec_from_file_location("openpermit_ori_server", SERVER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


async def main() -> None:
    async with Client(module.mcp, raise_exceptions=True) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        required = {
            "ori_capabilities",
            "ori_get",
            "ori_traverse",
            "ori_provenance",
            "ori_verify",
            "ori_analyze_precedence",
            "ori_challenge",
            "ori_resolve_challenge",
            "ori_list_profiles",
        }
        missing = required - names
        assert not missing, f"missing tools: {sorted(missing)}"

        capabilities = await client.call_tool("ori_capabilities", {})
        assert not capabilities.is_error
        assert capabilities.structured_content
        assert capabilities.structured_content["ok"] is True

        profiles = await client.call_tool("ori_list_profiles", {})
        assert not profiles.is_error
        data = profiles.structured_content["data"]
        assert any(p.get("authority_classification") == "federal_guidance" for p in data)

        graph = await client.call_tool(
            "ori_analyze_precedence",
            {
                "graph": {
                    "nodes": [
                        {"id": "a", "duration": 2},
                        {"id": "b", "duration": 5},
                        {"id": "c", "duration": 3},
                        {"id": "d", "duration": 2},
                    ],
                    "edges": [
                        {"from": "a", "to": "b"},
                        {"from": "a", "to": "c"},
                        {"from": "b", "to": "d"},
                        {"from": "c", "to": "d"},
                    ],
                }
            },
        )
        assert not graph.is_error
        assert graph.structured_content["data"]["critical_nodes"] == ["a", "b", "d"]

        profile_id = "ori:profile:federal:hud-home-construction-best-practices:2026"
        challenge = await client.call_tool(
            "ori_challenge",
            {
                "subject_id": profile_id,
                "challenged_by": "ori:agent:smoke-test",
                "grounds": "test_only",
                "statement": "Exercise append-only challenge lifecycle.",
                "evidence": [],
            },
        )
        assert not challenge.is_error
        challenge_id = challenge.structured_content["data"]["id"]

        resolution = await client.call_tool(
            "ori_resolve_challenge",
            {
                "challenge_id": challenge_id,
                "decided_by": "ori:agent:smoke-test",
                "disposition": "withdrawn",
                "statement": "Smoke test complete.",
                "evidence": [],
            },
        )
        assert not resolution.is_error
        assert resolution.structured_content["data"]["disposition"] == "withdrawn"

        retrieved = await client.call_tool("ori_get", {"object_id": profile_id})
        assert not retrieved.is_error
        assert retrieved.structured_content["data"]["open_challenges"] == []

    print("PASS reference-node MCP smoke")


if __name__ == "__main__":
    asyncio.run(main())
