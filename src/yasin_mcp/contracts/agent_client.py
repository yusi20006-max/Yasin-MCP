"""Versioned public contract between Yasin-Agent (MCP client) and Yasin-MCP.

Yasin-Agent MUST NOT gain a mandatory runtime dependency on Yasin-MCP.
This module is documentation-as-code: pure data/types, no network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

CONTRACT_VERSION: Final[str] = "1.0.0"
TRANSPORT: Final[str] = "stdio"
PROTOCOL_HINT: Final[str] = "MCP initialize + tools/list + tools/call"


@dataclass(frozen=True)
class ClientCapabilityExpectation:
    tool_name_prefixes: tuple[str, ...]
    read_only: bool
    mutating_tools: bool
    optional_operations_gateway: bool


DEFAULT_EXPECTATIONS = ClientCapabilityExpectation(
    tool_name_prefixes=(
        "yasin_docs_",
        "yasin_github_",
        "yasin_registry_",
        "yasin_operations_",
    ),
    read_only=True,
    mutating_tools=False,
    optional_operations_gateway=True,
)


@dataclass(frozen=True)
class FallbackBehavior:
    mandatory: bool
    on_unavailable: str
    on_timeout: str
    on_tool_error: str


DEFAULT_FALLBACK = FallbackBehavior(
    mandatory=False,
    on_unavailable="continue without MCP tools; do not crash",
    on_timeout="surface timeout to user; do not retry unboundedly",
    on_tool_error="preserve error envelope; do not invent data",
)


def contract_summary() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "transport": TRANSPORT,
        "protocol": PROTOCOL_HINT,
        "expectations": {
            "tool_name_prefixes": list(DEFAULT_EXPECTATIONS.tool_name_prefixes),
            "read_only": DEFAULT_EXPECTATIONS.read_only,
            "mutating_tools": DEFAULT_EXPECTATIONS.mutating_tools,
            "optional_operations_gateway": DEFAULT_EXPECTATIONS.optional_operations_gateway,
        },
        "fallback": {
            "mandatory": DEFAULT_FALLBACK.mandatory,
            "on_unavailable": DEFAULT_FALLBACK.on_unavailable,
            "on_timeout": DEFAULT_FALLBACK.on_timeout,
            "on_tool_error": DEFAULT_FALLBACK.on_tool_error,
        },
        "evidence_status": "confirmed",
    }
