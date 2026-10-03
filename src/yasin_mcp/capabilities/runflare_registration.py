"""Runflare capability registration for the central Yasin-MCP registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yasin_mcp.capabilities.registry import CapabilityRegistry, descriptor_for
from yasin_mcp.governance.types import RiskLevel
from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope


@dataclass(frozen=True)
class RunflareCapabilityDefinition:
    """Stable metadata for one scoped Runflare operation."""

    name: str
    operation: str
    description: str
    risk: RiskLevel
    input_schema: dict[str, Any]
    is_mutating: bool = False


RUNFLARE_CAPABILITY_DEFINITIONS: tuple[RunflareCapabilityDefinition, ...] = (
    RunflareCapabilityDefinition(
        name="runflare_status",
        operation="status",
        description="Read the configured Runflare project's current status/diagnostics.",
        risk=RiskLevel.READ_ONLY,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    RunflareCapabilityDefinition(
        name="runflare_events",
        operation="events",
        description="Read bounded, sanitized Runflare project events.",
        risk=RiskLevel.READ_ONLY,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    RunflareCapabilityDefinition(
        name="runflare_logs",
        operation="logs",
        description="Read bounded, sanitized Runflare project logs.",
        risk=RiskLevel.READ_ONLY,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    RunflareCapabilityDefinition(
        name="runflare_release",
        operation="deploy",
        description="Deploy the explicitly configured Runflare project target.",
        risk=RiskLevel.MUTATION,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        is_mutating=True,
    ),
    RunflareCapabilityDefinition(
        name="runflare_start",
        operation="start",
        description="Start the explicitly configured Runflare project target.",
        risk=RiskLevel.MUTATION,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        is_mutating=True,
    ),
    RunflareCapabilityDefinition(
        name="runflare_restart",
        operation="restart",
        description="Restart the explicitly configured Runflare project target.",
        risk=RiskLevel.MUTATION,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        is_mutating=True,
    ),
    RunflareCapabilityDefinition(
        name="runflare_stop",
        operation="stop",
        description="Stop the explicitly configured Runflare project target; confirmation is required.",
        risk=RiskLevel.MUTATION,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        is_mutating=True,
    ),
)


def register_runflare_capabilities(registry: CapabilityRegistry) -> int:
    """Register all stable Runflare capability contracts."""
    for definition in RUNFLARE_CAPABILITY_DEFINITIONS:
        registry.register(
            CapabilityContract(
                descriptor=descriptor_for(
                    definition.name,
                    "tool",
                    definition.description,
                    is_mutating=definition.is_mutating,
                ),
                scope=CapabilityScope.TOOL,
                input_schema=dict(definition.input_schema),
                risk=definition.risk,
            )
        )
    return len(RUNFLARE_CAPABILITY_DEFINITIONS)
