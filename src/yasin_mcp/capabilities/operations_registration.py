"""Conditional registration of Operations tools into the capability registry.

Operations tools are registered only when OperationsAdapter.available
is True (the gateway executable is on PATH). When unavailable, no
Operations capability is registered at all -- the server still
starts and every other capability continues to work unaffected.
"""

from __future__ import annotations

from yasin_mcp.adapters.operations import OperationsAdapter
from yasin_mcp.capabilities.registry import CapabilityRegistry, descriptor_for
from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope
from yasin_mcp.tools.operations import OPERATIONS_TOOL_DEFINITIONS


def register_operations_tools(registry: CapabilityRegistry, adapter: OperationsAdapter) -> bool:
    """Register the four Operations tools if the gateway is available.

    Returns True if registration occurred, False if the gateway was
    unavailable and nothing was registered. Never raises for
    unavailability -- that is an expected, structured outcome, not
    an error condition for the caller of this function.
    """
    if not adapter.available:
        return False

    for definition in OPERATIONS_TOOL_DEFINITIONS:
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
    return True
