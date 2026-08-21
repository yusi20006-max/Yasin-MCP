"""Registration of project-registry tools."""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry, descriptor_for
from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope
from yasin_mcp.tools.registry import REGISTRY_TOOL_DEFINITIONS


def register_registry_tools(registry: CapabilityRegistry) -> int:
    for definition in REGISTRY_TOOL_DEFINITIONS:
        registry.register(
            CapabilityContract(
                descriptor=descriptor_for(
                    definition.name,
                    "tool",
                    definition.description,
                    is_mutating=False,
                ),
                scope=CapabilityScope.TOOL,
                input_schema=dict(definition.input_schema),
            )
        )
    return len(REGISTRY_TOOL_DEFINITIONS)
