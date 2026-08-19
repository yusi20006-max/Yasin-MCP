"""Runtime and transport foundation tests."""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.server.runtime import SERVER_NAME, TRANSPORT_STDIO, ServerRuntime


def test_runtime_creates_empty_server_without_domain_integrations() -> None:
    runtime = ServerRuntime.create(ServerConfig())
    assert runtime.server.name == SERVER_NAME
    assert runtime.registry == CapabilityRegistry()
    assert runtime.capability_catalog().capabilities == ()


def test_runtime_uses_stdio_transport_constant() -> None:
    assert TRANSPORT_STDIO == "stdio"


def test_runtime_accepts_dependency_free_registry() -> None:
    registry = CapabilityRegistry()
    runtime = ServerRuntime.create(registry=registry)
    assert runtime.registry is registry
