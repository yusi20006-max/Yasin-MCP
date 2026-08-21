"""MCP tools exposing Yasin-Operations, read-only only.

Explicit, non-dynamic mapping between MCP tool name and Operations
operation -- TOOL_MAP below is the single source of truth and is
covered by tests asserting every entry is read_only. No code path
in this module accepts a caller-supplied operation name or
safety_class; each tool function calls exactly one hardcoded
OperationsAdapter method.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from yasin_mcp.adapters.operations import (
    OPERATION_DIAGNOSTICS,
    OPERATION_HEALTH_CHECK,
    OPERATION_LIST_SERVICES,
    OPERATION_SERVICE_STATUS,
    OperationsAdapter,
    OperationsResult,
)
from yasin_mcp.errors.errors import ValidationError

TOOL_LIST_SERVICES = "yasin_operations_list_services"
TOOL_SERVICE_STATUS = "yasin_operations_service_status"
TOOL_HEALTH = "yasin_operations_health"
TOOL_DIAGNOSTICS = "yasin_operations_diagnostics"

# Explicit, reviewable contract mapping. Every entry's safety class
# is "read_only" by construction (see test_operations_tools.py's
# test_tool_map_is_entirely_read_only, which asserts this
# programmatically so the invariant cannot silently regress).
TOOL_MAP: Mapping[str, Mapping[str, str]] = {
    TOOL_LIST_SERVICES: {"operation": OPERATION_LIST_SERVICES, "safety_class": "read_only"},
    TOOL_SERVICE_STATUS: {"operation": OPERATION_SERVICE_STATUS, "safety_class": "read_only"},
    TOOL_HEALTH: {"operation": OPERATION_HEALTH_CHECK, "safety_class": "read_only"},
    TOOL_DIAGNOSTICS: {"operation": OPERATION_DIAGNOSTICS, "safety_class": "read_only"},
}


def _result_to_dict(result: OperationsResult) -> dict[str, Any]:
    return result.as_dict()


class OperationsToolset:
    """Binds TOOL_MAP entries to callable MCP tool functions.

    Each method here corresponds 1:1 to one TOOL_MAP entry and calls
    exactly one hardcoded OperationsAdapter method -- there is no
    generic "call_operation(name)" method that could be pointed at
    an arbitrary operation.
    """

    def __init__(self, adapter: OperationsAdapter) -> None:
        self._adapter = adapter

    @property
    def available(self) -> bool:
        return self._adapter.available

    def list_services(self) -> dict[str, Any]:
        return _result_to_dict(self._adapter.list_services())

    def service_status(self, service_name: str) -> dict[str, Any]:
        if not isinstance(service_name, str):
            raise ValidationError("service_name must be a string")
        return _result_to_dict(self._adapter.service_status(service_name))

    def health(self) -> dict[str, Any]:
        return _result_to_dict(self._adapter.health())

    def diagnostics(self) -> dict[str, Any]:
        return _result_to_dict(self._adapter.diagnostics())


@dataclass(frozen=True)
class OperationsToolDefinition:
    """Static description of one Operations MCP tool, for capability discovery."""

    name: str
    description: str
    input_schema: Mapping[str, Any]


OPERATIONS_TOOL_DEFINITIONS: tuple[OperationsToolDefinition, ...] = (
    OperationsToolDefinition(
        name=TOOL_LIST_SERVICES,
        description="List known Yasin-Operations managed services (read-only).",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    OperationsToolDefinition(
        name=TOOL_SERVICE_STATUS,
        description="Get the current status of a named service (read-only).",
        input_schema={
            "type": "object",
            "properties": {"service_name": {"type": "string"}},
            "required": ["service_name"],
            "additionalProperties": False,
        },
    ),
    OperationsToolDefinition(
        name=TOOL_HEALTH,
        description="Get the Yasin-Operations runtime health summary (read-only).",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    OperationsToolDefinition(
        name=TOOL_DIAGNOSTICS,
        description="Get the Yasin-Operations runtime diagnostic snapshot (read-only).",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
)
