"""Stage 6 / Issue #87 — integration context, trust boundary, isolation."""

from __future__ import annotations

import concurrent.futures
from typing import Any

import pytest

from yasin_mcp.config.config import ServerConfig
from yasin_mcp.contracts.integration_context import (
    INTEGRATION_CONTRACT_VERSION,
    IntegrationContext,
    TrustClassification,
    integration_contract_summary,
)
from yasin_mcp.errors.errors import PolicyDeniedError, ValidationError
from yasin_mcp.governance import (
    AuditEventType,
    DefaultConservativePolicy,
    GovernanceDecision,
    GovernanceGate,
    InMemoryAuditRecorder,
    RiskLevel,
    StaticDecisionPolicy,
    ToolRiskCatalog,
)
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.tools.docs import TOOL_LIST_DOCS


def test_integration_contract_summary_is_safe() -> None:
    summary = integration_contract_summary()
    assert summary["integration_contract_version"] == INTEGRATION_CONTRACT_VERSION
    assert summary["identity_trust_default"] == TrustClassification.ASSERTED.value
    assert summary["stdio_authentication"] == TrustClassification.UNRESOLVED.value
    assert summary["privilege_escalation_via_metadata"] is False


def test_valid_context_maps_to_governance() -> None:
    ctx = IntegrationContext(
        client_id="client-1",
        agent_id="agent-1",
        project_id="proj-1",
        workspace_id="ws-1",
        task_id="task-1",
        session_id="sess-1",
        request_id="req-1",
        correlation_id="corr-1",
        extra={"role": "reader"},
    )
    assert ctx.trust is TrustClassification.ASSERTED
    gov = ctx.to_governance_context()
    assert gov.agent_id == "agent-1"
    assert gov.session_id == "sess-1"
    assert gov.correlation_id == "corr-1"
    assert gov.task_id == "task-1"
    d = ctx.as_dict()
    assert d["trust"] == "asserted"
    assert d["integration_contract_version"] == INTEGRATION_CONTRACT_VERSION


@pytest.mark.parametrize(
    "payload",
    [
        {"client_id": ""},
        {"client_id": " "},
        {"agent_id": "bad id with spaces!"},
        {"request_id": "x" * 200},
        {"extra": {"api_token": "TEST_SECRET_VALUE"}},
        {"extra": {"nested": {"a": 1}}},
        {"trust": "trusted"},
        {"unknown_field": "x"},
        "not-a-mapping",
    ],
)
def test_malformed_context_fails_closed(payload: Any) -> None:
    with pytest.raises(ValidationError):
        IntegrationContext.from_mapping(payload)  # type: ignore[arg-type]


def test_asserted_agent_cannot_bypass_deny() -> None:
    catalog = ToolRiskCatalog({"blocked": RiskLevel.HIGH_RISK})
    rec = InMemoryAuditRecorder()
    gate = GovernanceGate(catalog, policy=DefaultConservativePolicy(), auditor=rec)
    calls: list[str] = []
    ctx = IntegrationContext(
        agent_id="trusted-looking-agent",
        project_id="prod",
        session_id="sess-x",
        request_id="req-x",
        extra={"role": "admin"},
    )
    with pytest.raises(PolicyDeniedError):
        gate.execute(
            "blocked",
            lambda: calls.append("x") or "no",
            context=ctx.to_governance_context(),
        )
    assert calls == []
    assert any(e.event_type is AuditEventType.DECISION for e in rec.events)


def test_allow_deny_approval_unknown_with_context() -> None:
    def _run(risk: RiskLevel | None, name: str, expect_decision: str) -> None:
        entries = {} if risk is None else {name: risk}
        gate = GovernanceGate(
            ToolRiskCatalog(entries),
            policy=DefaultConservativePolicy(),
            auditor=InMemoryAuditRecorder(),
        )
        calls: list[str] = []
        ctx = IntegrationContext(request_id="r1", correlation_id="c1", session_id="s1")
        if expect_decision == "allow":
            assert (
                gate.execute(
                    name, lambda: calls.append("x") or 1, context=ctx.to_governance_context()
                )
                == 1
            )
            assert calls == ["x"]
        else:
            with pytest.raises(PolicyDeniedError) as ei:
                gate.execute(
                    name,
                    lambda: calls.append("x") or "no",
                    context=ctx.to_governance_context(),
                )
            assert calls == []
            assert ei.value.details["decision"] == expect_decision

    _run(RiskLevel.READ_ONLY, "safe", "allow")
    _run(RiskLevel.HIGH_RISK, "hi", "deny")
    _run(RiskLevel.MUTATION, "mut", "approval_required")
    _run(None, "unknown_zzz", "deny")


def test_context_isolation_concurrent_requests() -> None:
    catalog = ToolRiskCatalog({"t": RiskLevel.READ_ONLY})
    rec = InMemoryAuditRecorder()
    gate = GovernanceGate(catalog, policy=DefaultConservativePolicy(), auditor=rec)

    def worker(i: int) -> str:
        ctx = IntegrationContext(
            project_id=f"project-{i}",
            request_id=f"req-{i}",
            session_id=f"sess-{i}",
        )
        result = gate.execute(
            "t",
            lambda: f"ok-{i}",
            context=ctx.to_governance_context(),
        )
        return str(result)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(16)))
    assert results == [f"ok-{i}" for i in range(16)]
    projects = sorted(
        {
            e.context.get("project_id")
            for e in rec.events
            if e.event_type is AuditEventType.REQUEST and e.context.get("project_id")
        }
    )
    assert projects == sorted(f"project-{i}" for i in range(16))


def test_surface_info_exposes_integration_contract() -> None:
    rt = ServerRuntime.create(ServerConfig())
    info = rt.surface_info()
    assert info["governance"] == "centralized"
    integ = info["integration"]
    assert isinstance(integ, dict)
    assert integ["integration_contract_version"] == INTEGRATION_CONTRACT_VERSION
    assert integ["stdio_authentication"] == "unresolved"


def test_runtime_deny_with_integration_context() -> None:
    rt = ServerRuntime.create(
        ServerConfig(),
        policy=StaticDecisionPolicy({TOOL_LIST_DOCS: GovernanceDecision.DENY}),
        auditor=InMemoryAuditRecorder(),
    )
    ctx = IntegrationContext(agent_id="a1", request_id="r1")
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError):
        rt.governance.execute(
            TOOL_LIST_DOCS,
            lambda: calls.append("x") or "no",
            context=ctx.to_governance_context(),
        )
    assert calls == []


def test_from_mapping_empty_and_none() -> None:
    assert IntegrationContext.from_mapping(None).request_id is None
    assert IntegrationContext.from_mapping({}).session_id is None
