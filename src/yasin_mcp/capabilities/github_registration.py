"""Registration of read-only GitHub tools into the capability registry."""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry, descriptor_for
from yasin_mcp.governance.types import RiskLevel
from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope
from yasin_mcp.tools.github import GITHUB_TOOL_DEFINITIONS


def register_github_tools(registry: CapabilityRegistry) -> int:
    """Register all GitHub tools. Returns the number registered."""
    for definition in GITHUB_TOOL_DEFINITIONS:
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
                risk=RiskLevel.READ_ONLY,
            )
        )
    return len(GITHUB_TOOL_DEFINITIONS)
