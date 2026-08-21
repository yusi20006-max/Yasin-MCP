"""LIVE_RUNTIME MCP client regression harness (P2-2 / Issue #64).

Spawns the real ``yasin-mcp`` console script over stdio and exercises the
official MCP Python SDK client. This is not a unit test of mocks.

Default CI does not require GitHub credentials: always-on tool *discovery*
is asserted; a domain ``call_tool`` is attempted and either structured success
or structured error is accepted (the process must not crash).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path

import pytest

EVIDENCE_CLASS = "LIVE_RUNTIME"

ALWAYS_ON_PREFIXES = (
    "yasin_docs_",
    "yasin_github_",
    "yasin_registry_",
)


def _yasin_mcp_executable() -> str:
    # Prefer the console script next to the active interpreter (venv/bin).
    candidate = Path(sys.executable).resolve().parent / "yasin-mcp"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    which = shutil.which("yasin-mcp")
    if which:
        return which
    pytest.skip("yasin-mcp console script not available in this environment")


async def _run_live_session() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    command = _yasin_mcp_executable()
    params = StdioServerParameters(
        command=command,
        args=[],
        env={**os.environ},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init is not None

            protocol_version = getattr(init, "protocolVersion", None) or getattr(
                init, "protocol_version", None
            )
            assert protocol_version is not None

            server_info = getattr(init, "serverInfo", None) or getattr(init, "server_info", None)
            assert server_info is not None

            capabilities = getattr(init, "capabilities", None)
            assert capabilities is not None

            tools_result = await session.list_tools()
            tools = getattr(tools_result, "tools", tools_result) or []
            names = {getattr(t, "name", None) for t in tools}
            names.discard(None)
            assert names, "expected always-on tools to be registered"

            for prefix in ALWAYS_ON_PREFIXES:
                assert any(n.startswith(prefix) for n in names), (
                    f"missing always-on tools with prefix {prefix!r}; got {sorted(names)}"
                )

            sample = next(n for n in sorted(names) if n.startswith("yasin_docs_list"))
            call_result = await session.call_tool(sample, arguments={})
            assert call_result is not None

            invalid = await session.call_tool("yasin_mcp_nonexistent_tool_xyz", arguments={})
            invalid_is_error = getattr(invalid, "isError", None)
            if invalid_is_error is None:
                invalid_is_error = getattr(invalid, "is_error", None)
            assert invalid_is_error is True or getattr(invalid, "content", None) is not None


def test_live_mcp_stdio_client_harness() -> None:
    """Full live stdio client path against the real server process (LIVE_RUNTIME)."""
    asyncio.run(_run_live_session())
