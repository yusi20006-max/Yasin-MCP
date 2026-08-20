"""Runtime registration tests for the read-only Yasin-Operations bridge."""

from __future__ import annotations

from unittest.mock import Mock

from yasin_mcp.adapters.operations import OperationsAdapter
from yasin_mcp.capabilities.registry import CapabilityRegistry
from yasin_mcp.server.runtime import ServerRuntime


def _available_adapter() -> OperationsAdapter:
    adapter = Mock(spec=OperationsAdapter)
    adapter.available = True
    return adapter


def test_runtime_registers_exactly_four_operations_tools() -> None:
    registry = CapabilityRegistry()
    runtime = ServerRuntime.create(registry=registry, operations_adapter=_available_adapter())

    tools = runtime.server._tool_manager.list_tools()  # type: ignore[attr-defined]
    names = {tool.name for tool in tools}

    assert names == {
        "yasin_operations_list_services",
        "yasin_operations_service_status",
        "yasin_operations_health",
        "yasin_operations_diagnostics",
    }
    assert {cap.name for cap in runtime.capability_catalog().capabilities} == names


def test_runtime_does_not_advertise_operations_when_gateway_unavailable() -> None:
    registry = CapabilityRegistry()
    adapter = Mock(spec=OperationsAdapter)
    adapter.available = False

    runtime = ServerRuntime.create(registry=registry, operations_adapter=adapter)

    assert runtime.server._tool_manager.list_tools() == []  # type: ignore[attr-defined]
    assert runtime.capability_catalog().capabilities == ()
