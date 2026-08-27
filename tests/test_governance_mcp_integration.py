"""MCP path governance integration tests (Issue #80)."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from yasin_mcp.config.config import ServerConfig
from yasin_mcp.errors.errors import PolicyDeniedError
from yasin_mcp.governance import (
    GovernanceDecision,
    InMemoryAuditRecorder,
    RiskLevel,
    StaticDecisionPolicy,
)
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.tools.docs import TOOL_LIST_DOCS


def _exe() -> str:
    c = Path(sys.executable).parent / "yasin-mcp"
    if c.is_file() and os.access(c, os.X_OK):
        return str(c)
    w = shutil.which("yasin-mcp")
    if w:
        return w
    pytest.skip("no yasin-mcp")


def test_runtime_governance() -> None:
    r = ServerRuntime.create(ServerConfig(), auditor=InMemoryAuditRecorder())
    assert TOOL_LIST_DOCS in r.governance.catalog
    assert r.governance.resolve_tool(TOOL_LIST_DOCS).risk is RiskLevel.READ_ONLY
    assert r.surface_info()["governance"] == "centralized"
    assert r.governance.execute(TOOL_LIST_DOCS, lambda: {"ok": 1}) == {"ok": 1}


def test_deny_and_approval_via_runtime() -> None:
    r = ServerRuntime.create(
        ServerConfig(),
        policy=StaticDecisionPolicy({TOOL_LIST_DOCS: GovernanceDecision.DENY}),
        auditor=InMemoryAuditRecorder(),
    )
    with pytest.raises(PolicyDeniedError):
        r.governance.execute(TOOL_LIST_DOCS, lambda: "x")
    r2 = ServerRuntime.create(
        ServerConfig(),
        policy=StaticDecisionPolicy({TOOL_LIST_DOCS: GovernanceDecision.APPROVAL_REQUIRED}),
        auditor=InMemoryAuditRecorder(),
    )
    with pytest.raises(PolicyDeniedError):
        r2.governance.execute(TOOL_LIST_DOCS, lambda: "x")


async def _session(cmd: str) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=cmd, args=[], env={**os.environ})
    out: dict[str, Any] = {}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            out["protocol"] = getattr(init, "protocolVersion", None) or getattr(
                init, "protocol_version", None
            )
            tools = getattr(await session.list_tools(), "tools", []) or []
            out["names"] = [getattr(t, "name", "") for t in tools]
            await session.call_tool(TOOL_LIST_DOCS, arguments={})
            inv = await session.call_tool("yasin_mcp_nonexistent_tool_xyz", arguments={})
            out["unknown"] = getattr(inv, "isError", None) or getattr(inv, "is_error", None)
    out["clean"] = True
    return out


def test_live_stdio() -> None:
    res = asyncio.run(_session(_exe()))
    assert res["protocol"] and res["unknown"] is True and res["clean"]
