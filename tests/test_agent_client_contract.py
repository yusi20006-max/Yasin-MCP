"""Tests for the Yasin-Agent MCP client contract."""

from yasin_mcp.contracts.agent_client import (
    CONTRACT_VERSION,
    DEFAULT_EXPECTATIONS,
    DEFAULT_FALLBACK,
    contract_summary,
)


def test_contract_version_and_non_mandatory() -> None:
    assert CONTRACT_VERSION == "1.0.0"
    assert DEFAULT_FALLBACK.mandatory is False
    assert DEFAULT_EXPECTATIONS.mutating_tools is False
    summary = contract_summary()
    assert summary["fallback"]["mandatory"] is False
    assert "yasin_docs_" in summary["expectations"]["tool_name_prefixes"]
