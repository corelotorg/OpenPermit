#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

from mcp import Client

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "reference-node" / "server.py"

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
            "ori_challenge",
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

    print("PASS reference-node MCP smoke")


if __name__ == "__main__":
    asyncio.run(main())
