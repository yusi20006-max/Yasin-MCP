"""Stage 5 / Issue #84 — production readiness invariants.

Lifecycle, capability integrity, repeated sessions, config failure path.
Does not expand governance architecture or integrate external products.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from yasin_mcp.config.config import ServerConfig
from yasin_mcp.governance import RiskLevel
from yasin_mcp.server import cli
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.tools.docs import DOCS_TOOL_DEFINITIONS, TOOL_LIST_DOCS
from yasin_mcp.tools.github import GITHUB_TOOL_DEFINITIONS
from yasin_mcp.tools.registry import REGISTRY_TOOL_DEFINITIONS


def _always_on_names() -> set[str]:
    return (
        {d.name for d in DOCS_TOOL_DEFINITIONS}
        | {d.name for d in GITHUB_TOOL_DEFINITIONS}
        | {d.name for d in REGISTRY_TOOL_DEFINITIONS}
    )


def test_capability_catalog_matches_mcp_and_governance_surface() -> None:
    """Catalog, governance risk catalog, and MCP tool manager must agree."""
    rt = ServerRuntime.create(ServerConfig())
    expected = _always_on_names()
    catalog_names = {c.name for c in rt.capability_catalog().capabilities}
    gov_names = set(rt.governance.catalog.known_names())
    mcp_tools = rt.server._tool_manager.list_tools()  # type: ignore[attr-defined]
    mcp_names = {t.name for t in mcp_tools}

    assert expected <= catalog_names
    assert expected <= gov_names
    assert expected <= mcp_names
    # Always-on sets must be identical across the three surfaces
    assert catalog_names & expected == expected
    assert gov_names & expected == expected
    assert mcp_names & expected == expected
    # No duplicate MCP tool names
    assert len(mcp_names) == len(list(mcp_tools))
    # Every governed production tool has a RiskLevel
    for name in expected:
        identity = rt.governance.resolve_tool(name)
        assert identity.known is True
        assert isinstance(identity.risk, RiskLevel)
    assert rt.surface_info()["governance"] == "centralized"


def test_independent_runtimes_do_not_share_mutable_state() -> None:
    a = ServerRuntime.create(ServerConfig())
    b = ServerRuntime.create(ServerConfig())
    assert a is not b
    assert a.governance is not b.governance
    assert a.registry is not b.registry
    assert a.server is not b.server
    # Catalog contents are equal by value, not identity
    assert set(a.governance.catalog.known_names()) == set(b.governance.catalog.known_names())


def test_cli_invalid_configuration_exits_without_starting_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["yasin-mcp"])
    monkeypatch.setenv("YASIN_MCP_LOG_LEVEL", "NOT_A_LEVEL")
    monkeypatch.setattr(
        cli.ServerRuntime,
        "create",
        lambda _config: (_ for _ in ()).throw(AssertionError("server must not start")),
    )
    with pytest.raises(SystemExit) as ei:
        cli.main()
    assert ei.value.code == 2
    err = capsys.readouterr().err
    assert "configuration error" in err
    assert "NOT_A_LEVEL" in err or "log_level" in err.lower()


def test_cli_invalid_timeout_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["yasin-mcp"])
    monkeypatch.setenv("YASIN_MCP_REQUEST_TIMEOUT_SECONDS", "9999")
    with pytest.raises(SystemExit) as ei:
        cli.main()
    assert ei.value.code == 2


def _yasin_mcp_executable() -> str:
    candidate = Path(sys.executable).resolve().parent / "yasin-mcp"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    which = shutil.which("yasin-mcp")
    if which:
        return which
    pytest.skip("yasin-mcp console script not available")


async def _one_session(*, call_unknown_first: bool = False) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=_yasin_mcp_executable(), args=[], env={**os.environ})
    out: dict[str, Any] = {}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            out["protocol"] = getattr(init, "protocolVersion", None) or getattr(
                init, "protocol_version", None
            )
            tools = getattr(await session.list_tools(), "tools", []) or []
            out["tool_count"] = len(tools)
            names = [getattr(t, "name", "") for t in tools]
            out["has_list_docs"] = TOOL_LIST_DOCS in names

            if call_unknown_first:
                inv = await session.call_tool("yasin_mcp_nonexistent_tool_xyz", arguments={})
                out["unknown_is_error"] = bool(
                    getattr(inv, "isError", None) or getattr(inv, "is_error", None)
                )

            # Recovery / sequential call after optional failure
            result = await session.call_tool(TOOL_LIST_DOCS, arguments={})
            out["list_docs_ok"] = result is not None
            if not call_unknown_first:
                inv = await session.call_tool("yasin_mcp_nonexistent_tool_xyz", arguments={})
                out["unknown_is_error"] = bool(
                    getattr(inv, "isError", None) or getattr(inv, "is_error", None)
                )
    out["clean"] = True
    return out


def test_repeated_live_mcp_sessions_are_isolated() -> None:
    """Two sequential stdio sessions must both initialize and shut down cleanly."""
    first = asyncio.run(_one_session())
    second = asyncio.run(_one_session(call_unknown_first=True))
    assert first["protocol"] and second["protocol"]
    assert first["tool_count"] == second["tool_count"]
    assert first["has_list_docs"] and second["has_list_docs"]
    assert first["unknown_is_error"] is True
    assert second["unknown_is_error"] is True
    assert first["list_docs_ok"] and second["list_docs_ok"]
    assert first["clean"] and second["clean"]


def test_failure_then_success_in_single_session() -> None:
    """Unknown tool error must not poison subsequent calls in the same session."""
    res = asyncio.run(_one_session(call_unknown_first=True))
    assert res["unknown_is_error"] is True
    assert res["list_docs_ok"] is True
    assert res["clean"] is True
