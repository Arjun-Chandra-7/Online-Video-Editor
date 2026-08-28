#!/usr/bin/env python3
"""Read-only end-to-end MCP protocol smoke test for a running Viralist API."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


ROOT = Path(__file__).resolve().parent.parent


async def main() -> None:
    env = os.environ.copy()
    env["VIRALIST_AUTOSTART_WEB"] = "false"
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "backend" / "mcp_server.py")],
        cwd=ROOT,
        env=env,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            resources = await session.list_resources()
            names = {tool.name for tool in tools.tools}
            required = {"editor_capabilities", "project_inspect", "edit_batch", "project_export"}
            missing = required - names
            if missing:
                raise RuntimeError(f"Missing MCP tools: {sorted(missing)}")
            result = await session.call_tool("editor_capabilities", {})
            if result.is_error or not result.structured_content:
                raise RuntimeError(f"Capability call failed: {result}")
            payload = result.structured_content
            if isinstance(payload.get("result"), dict):
                payload = payload["result"]
            operations = payload.get("operations", [])
            if len(operations) < 30:
                raise RuntimeError(f"Unexpected operation count: {len(operations)}")
            before = await session.call_tool("project_inspect", {"detail": "summary"})
            preview = await session.call_tool("edit_apply", {
                "operation": "project.update_settings",
                "parameters": {"title": "MCP smoke-test preview"},
                "dry_run": True,
            })
            after = await session.call_tool("project_inspect", {"detail": "summary"})
            if before.is_error or preview.is_error or after.is_error:
                raise RuntimeError("Read or dry-run MCP operation failed")
            if before.structured_content != after.structured_content:
                raise RuntimeError("Dry-run changed the live project")
            print({
                "mcp": "ok",
                "tools": len(names),
                "resources": len(resources.resources),
                "operations": len(operations),
            })


if __name__ == "__main__":
    asyncio.run(main())
