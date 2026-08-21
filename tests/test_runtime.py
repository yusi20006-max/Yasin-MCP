"""Runtime and transport foundation tests."""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.server.runtime import SERVER_NAME, TRANSPORT_STDIO, ServerRuntime
from yasin_mcp.tools.docs import DOCS_TOOL_DEFINITIONS


def test_runtime_registers_docs_tools_by_default() -> None:
    runtime = ServerRuntime.create(ServerConfig())
    assert runtime.server.name == SERVER_NAME
    expected = {definition.name for definition in DOCS_TOOL_DEFINITIONS}
    catalog_names = {cap.name for cap in runtime.capability_catalog().capabilities}
    assert expected <= catalog_names
    tools = runtime.server._tool_manager.list_tools()  # type: ignore[attr-defined]
    assert expected <= {tool.name for tool in tools}


def test_runtime_uses_stdio_transport_constant() -> None:
    assert TRANSPORT_STDIO == "stdio"


def test_runtime_accepts_dependency_free_registry() -> None:
    registry = CapabilityRegistry()
    runtime = ServerRuntime.create(registry=registry)
    assert runtime.registry is registry
    assert len(runtime.capability_catalog().capabilities) == len(DOCS_TOOL_DEFINITIONS)
