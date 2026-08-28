"""Runtime registration tests for the read-only Yasin-Operations bridge."""

from __future__ import annotations

from unittest.mock import Mock

from yasin_mcp.adapters.operations import OperationsAdapter
from yasin_mcp.capabilities.registry import CapabilityRegistry
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.tools.docs import DOCS_TOOL_DEFINITIONS
from yasin_mcp.tools.github import GITHUB_TOOL_DEFINITIONS
from yasin_mcp.tools.governance_ref import TOOL_GOV_APPLY_MARK, TOOL_GOV_PING_LOW_RISK
from yasin_mcp.tools.registry import REGISTRY_TOOL_DEFINITIONS


def _available_adapter() -> OperationsAdapter:
    adapter = Mock(spec=OperationsAdapter)
    adapter.available = True
    return adapter


DOCS_NAMES = {definition.name for definition in DOCS_TOOL_DEFINITIONS}
GH_NAMES = {definition.name for definition in GITHUB_TOOL_DEFINITIONS}
REG_NAMES = {definition.name for definition in REGISTRY_TOOL_DEFINITIONS}
GOV_NAMES = {TOOL_GOV_PING_LOW_RISK, TOOL_GOV_APPLY_MARK}
ALWAYS_NAMES = DOCS_NAMES | GH_NAMES | REG_NAMES | GOV_NAMES
OPS_NAMES = {
    "yasin_operations_list_services",
    "yasin_operations_service_status",
    "yasin_operations_health",
    "yasin_operations_diagnostics",
}


def test_runtime_registers_docs_and_operations_when_gateway_available():
    registry = CapabilityRegistry()
    runtime = ServerRuntime.create(registry=registry, operations_adapter=_available_adapter())

    tools = runtime.server._tool_manager.list_tools()  # type: ignore[attr-defined]
    names = {tool.name for tool in tools}

    assert OPS_NAMES <= names
    assert ALWAYS_NAMES <= names
    assert {cap.name for cap in runtime.capability_catalog().capabilities} == names


def test_runtime_registers_docs_only_when_gateway_unavailable():
    registry = CapabilityRegistry()
    adapter = Mock(spec=OperationsAdapter)
    adapter.available = False

    runtime = ServerRuntime.create(registry=registry, operations_adapter=adapter)

    tools = runtime.server._tool_manager.list_tools()  # type: ignore[attr-defined]
    names = {tool.name for tool in tools}
    assert names == ALWAYS_NAMES
    assert OPS_NAMES.isdisjoint(names)
    assert {cap.name for cap in runtime.capability_catalog().capabilities} == ALWAYS_NAMES
