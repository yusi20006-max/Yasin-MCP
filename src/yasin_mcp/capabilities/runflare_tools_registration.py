"""Registration of scoped Runflare MCP tools."""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry, descriptor_for
from yasin_mcp.governance.types import RiskLevel
from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope
from yasin_mcp.tools.runflare import tool_definitions


def register_runflare_tools(registry: CapabilityRegistry) -> int:
    """Register the six operational Runflare MCP tool contracts."""
    definitions = tool_definitions()
    for definition in definitions:
        mutating = definition.name in {
            "runflare_deploy",
            "runflare_start",
            "runflare_restart",
        }
        registry.register(
            CapabilityContract(
                descriptor=descriptor_for(
                    definition.name,
                    "tool",
                    definition.description,
                    is_mutating=mutating,
                ),
                scope=CapabilityScope.TOOL,
                input_schema=dict(definition.input_schema),
                risk=RiskLevel.MUTATION if mutating else RiskLevel.READ_ONLY,
            )
        )
    return len(definitions)
