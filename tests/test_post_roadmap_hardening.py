from __future__ import annotations

import os

import pytest

from yasin_mcp.approval.store import InMemoryApprovalStore
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.governance.catalog import ToolRiskCatalog
from yasin_mcp.governance.gate import GovernanceGate
from yasin_mcp.governance.types import RiskLevel


def _mutation_gate(config: ServerConfig) -> tuple[GovernanceGate, InMemoryApprovalStore]:
    store = InMemoryApprovalStore()
    catalog = ToolRiskCatalog({"mutation": RiskLevel.MUTATION})
    return GovernanceGate(catalog, security_config=config, approval_store=store), store


def test_remote_execution_does_not_accept_process_environment_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ServerConfig(remote_enabled=True, remote_allow_insecure_http=True)
    gate, store = _mutation_gate(config)
    token = store.issue(tool_name="mutation")
    monkeypatch.setenv("YASIN_MCP_PRESENT_APPROVAL_TOKEN", token)

    with pytest.raises(Exception) as exc_info:
        gate.execute("mutation", lambda: "executed")

    assert "approval_required" in str(exc_info.value) or "policy_denied" in str(exc_info.value)


def test_local_execution_can_use_explicit_environment_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ServerConfig()
    gate, store = _mutation_gate(config)
    token = store.issue(tool_name="mutation")
    monkeypatch.setenv("YASIN_MCP_PRESENT_APPROVAL_TOKEN", token)

    assert gate.execute("mutation", lambda: "executed") == "executed"


def test_remote_approval_can_still_be_presented_per_request() -> None:
    config = ServerConfig(remote_enabled=True, remote_allow_insecure_http=True)
    gate, store = _mutation_gate(config)
    token = store.issue(tool_name="mutation")

    assert gate.execute("mutation", lambda: "executed", approval_token=token) == "executed"
