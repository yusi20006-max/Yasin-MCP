"""Post-Core integration compatibility helpers (read models only)."""

from yasin_mcp.compat.core_contracts import (
    CORE_CONTRACT_VERSION,
    CORE_VERSION_COMPAT,
    core_contract_summary,
    mcp_error_to_core_info,
    mcp_health_to_core_report,
    operations_result_to_core_status,
)

__all__ = [
    "CORE_CONTRACT_VERSION",
    "CORE_VERSION_COMPAT",
    "core_contract_summary",
    "mcp_error_to_core_info",
    "mcp_health_to_core_report",
    "operations_result_to_core_status",
]
