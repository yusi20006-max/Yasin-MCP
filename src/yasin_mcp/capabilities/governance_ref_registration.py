"""Register Stage 11 governance reference capabilities."""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry, descriptor_for
from yasin_mcp.governance.types import RiskLevel
from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope
from yasin_mcp.tools.governance_ref import TOOL_GOV_APPLY_MARK, TOOL_GOV_PING_LOW_RISK


def register_governance_ref_tools(registry: CapabilityRegistry) -> int:
    contracts = [
        CapabilityContract(
            descriptor=descriptor_for(
                TOOL_GOV_PING_LOW_RISK,
                "tool",
                "Governance reference: LOW_RISK ping (Stage 11).",
                is_mutating=False,
            ),
            scope=CapabilityScope.TOOL,
            input_schema={"type": "object", "properties": {}},
            risk=RiskLevel.LOW_RISK,
        ),
        CapabilityContract(
            descriptor=descriptor_for(
                TOOL_GOV_APPLY_MARK,
                "tool",
                "Governance reference: MUTATION apply_mark (requires approval).",
                is_mutating=True,
            ),
            scope=CapabilityScope.TOOL,
            input_schema={
                "type": "object",
                "properties": {"mark": {"type": "string"}},
            },
            risk=RiskLevel.MUTATION,
        ),
    ]
    registry.register_many(contracts)
    return len(contracts)
