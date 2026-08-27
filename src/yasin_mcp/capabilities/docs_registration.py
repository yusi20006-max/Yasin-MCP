"""Registration of YASIN-DOCS read-only tools into the capability registry.

Docs tools are always registered: the adapter talks to the public GitHub API
for the fixed YASIN-DOCS repository. Failures (network, rate limit, not found)
are returned as structured MCP errors at call time, not registration time.
"""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry, descriptor_for
from yasin_mcp.governance.types import RiskLevel
from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope
from yasin_mcp.tools.docs import DOCS_TOOL_DEFINITIONS


def register_docs_tools(registry: CapabilityRegistry) -> int:
    """Register all docs tools. Returns the number of tools registered."""
    for definition in DOCS_TOOL_DEFINITIONS:
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
    return len(DOCS_TOOL_DEFINITIONS)
