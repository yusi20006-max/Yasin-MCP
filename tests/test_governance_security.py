"""Stage 4 / Issue #82 — Governance security, fail-closed, and leak tests.

These tests prove execution behaviour (invocation counts), not only
policy return values. Synthetic secrets only; never real credentials.
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from yasin_mcp.config.config import ServerConfig
from yasin_mcp.errors.errors import PolicyDeniedError, ValidationError
from yasin_mcp.governance import (
    APPROVAL_REQUIRED,
    DENY,
    AuditEventType,
    DefaultConservativePolicy,
    GovernanceContext,
    GovernanceDecision,
    GovernanceGate,
    InMemoryAuditRecorder,
    RiskLevel,
    StaticDecisionPolicy,
    ToolIdentity,
    ToolRiskCatalog,
    sanitize_audit_payload,
)
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.tools.docs import TOOL_LIST_DOCS


def _counting_gate(
    entries: dict[str, RiskLevel] | None = None,
    *,
    policy: Any = None,
) -> tuple[GovernanceGate, InMemoryAuditRecorder, list[str]]:
    catalog = ToolRiskCatalog(entries or {"safe.read": RiskLevel.READ_ONLY})
    rec = InMemoryAuditRecorder()
    gate = GovernanceGate(catalog, policy=policy or DefaultConservativePolicy(), auditor=rec)
    calls: list[str] = []
    return gate, rec, calls


def test_allow_executes_exactly_once() -> None:
    gate, rec, calls = _counting_gate()
    result = gate.execute("safe.read", lambda: calls.append("x") or {"ok": 1})
    assert result == {"ok": 1}
    assert calls == ["x"]
    assert any(e.event_type is AuditEventType.REQUEST for e in rec.events)
    assert any(
        e.event_type is AuditEventType.DECISION and e.decision is GovernanceDecision.ALLOW
        for e in rec.events
    )
    assert any(e.event_type is AuditEventType.EXECUTION_RESULT for e in rec.events)


@pytest.mark.parametrize(
    "risk,expected_decision",
    [
        (RiskLevel.HIGH_RISK, DENY),
        (RiskLevel.MUTATION, APPROVAL_REQUIRED),
    ],
)
def test_deny_and_approval_never_execute(
    risk: RiskLevel, expected_decision: GovernanceDecision
) -> None:
    gate, rec, calls = _counting_gate({"t": risk})
    with pytest.raises(PolicyDeniedError) as ei:
        gate.execute("t", lambda: calls.append("x") or "no")
    assert calls == []
    assert ei.value.details["decision"] == expected_decision.value
    assert any(
        e.event_type is AuditEventType.DECISION and e.decision is expected_decision
        for e in rec.events
    )
    assert not any(e.event_type is AuditEventType.EXECUTION_RESULT for e in rec.events)


def test_unknown_tool_never_executes() -> None:
    gate, rec, calls = _counting_gate({})
    with pytest.raises(PolicyDeniedError) as ei:
        gate.execute("totally_unknown_zzz", lambda: calls.append("x") or "no")
    assert calls == []
    assert ei.value.details["known"] is False
    assert ei.value.details["decision"] == DENY.value


def test_policy_exception_is_fail_closed() -> None:
    class BoomPolicy:
        def evaluate(self, tool: ToolIdentity, context: Any = None) -> GovernanceDecision:
            raise RuntimeError("policy boom")

    gate, _, calls = _counting_gate(policy=BoomPolicy())
    with pytest.raises(RuntimeError, match="policy boom"):
        gate.execute("safe.read", lambda: calls.append("x") or "no")
    assert calls == []


def test_invalid_policy_decision_is_fail_closed() -> None:
    class BadDecisionPolicy:
        def evaluate(self, tool: ToolIdentity, context: Any = None) -> str:
            return "allow"

    gate, _, calls = _counting_gate(policy=BadDecisionPolicy())
    with pytest.raises(ValidationError):
        gate.execute("safe.read", lambda: calls.append("x") or "no")
    assert calls == []


def test_malformed_static_policy_rejects_invalid_decision() -> None:
    with pytest.raises(ValidationError):
        StaticDecisionPolicy({"t": "not-a-decision"})  # type: ignore[dict-item]
    with pytest.raises(ValidationError):
        StaticDecisionPolicy({"": GovernanceDecision.ALLOW})
    with pytest.raises(ValidationError):
        StaticDecisionPolicy({"t": GovernanceDecision.ALLOW}, fallback="allow")  # type: ignore[arg-type]


def test_empty_tool_name_rejected() -> None:
    with pytest.raises(ValueError):
        ToolIdentity(name="", risk=RiskLevel.READ_ONLY)
    catalog = ToolRiskCatalog()
    with pytest.raises(ValueError):
        catalog.register("", RiskLevel.READ_ONLY)
    with pytest.raises(ValueError):
        catalog.register("x", "read_only")  # type: ignore[arg-type]


def test_trusted_agent_context_does_not_bypass_deny() -> None:
    gate, _, calls = _counting_gate(
        {"blocked": RiskLevel.HIGH_RISK},
        policy=DefaultConservativePolicy(),
    )
    ctx = GovernanceContext(
        client_id="trusted-client",
        agent_id="trusted-agent",
        project_id="prod",
        workspace_id="ws-1",
        request_id="req-1",
        extra={"role": "admin"},
    )
    with pytest.raises(PolicyDeniedError):
        gate.execute("blocked", lambda: calls.append("x") or "no", context=ctx)
    assert calls == []


def test_context_isolation_between_requests() -> None:
    gate, rec, _ = _counting_gate()
    ctx_a = GovernanceContext(project_id="project-A", request_id="A")
    ctx_b = GovernanceContext(project_id="project-B", request_id="B")
    gate.execute("safe.read", lambda: "a", context=ctx_a)
    gate.execute("safe.read", lambda: "b", context=ctx_b)
    projects = [
        e.context.get("project_id") for e in rec.events if e.event_type is AuditEventType.REQUEST
    ]
    assert projects == ["project-A", "project-B"]
    req_ids = [
        e.context.get("request_id") for e in rec.events if e.event_type is AuditEventType.DECISION
    ]
    assert req_ids == ["A", "B"]


def test_secret_redaction_nested_and_key_variants() -> None:
    payload = {
        "token": "TEST_SECRET_VALUE",
        "access_token": "TEST_API_TOKEN",
        "API_KEY": "TEST_API_TOKEN",
        "ApiKey": "TEST_API_TOKEN",
        "password": "TEST_PASSWORD",
        "passwd": "TEST_PASSWORD",
        "Authorization": "TEST_AUTH_HEADER",
        "credential": "TEST_SECRET_VALUE",
        "credentials": ["TEST_SECRET_VALUE", "ok"],
        "nested": {"secret": "TEST_SECRET_VALUE", "safe": 1},
        "list": [{"api_token": "TEST_API_TOKEN"}],
        "safe_field": "visible",
    }
    redacted = sanitize_audit_payload(payload)
    blob = str(redacted)
    for secret in (
        "TEST_SECRET_VALUE",
        "TEST_API_TOKEN",
        "TEST_PASSWORD",
        "TEST_AUTH_HEADER",
    ):
        assert secret not in blob
    assert redacted["safe_field"] == "visible"
    assert redacted["nested"]["safe"] == 1


def test_execution_failure_audit_omits_exception_value() -> None:
    gate, rec, _ = _counting_gate()

    def boom() -> None:
        raise RuntimeError("token=TEST_SECRET_VALUE password=TEST_PASSWORD")

    with pytest.raises(RuntimeError):
        gate.execute("safe.read", boom)
    failures = [e for e in rec.events if e.event_type is AuditEventType.EXECUTION_FAILURE]
    assert len(failures) == 1
    assert failures[0].message == "RuntimeError"
    blob = str([e.as_dict() for e in rec.events])
    assert "TEST_SECRET_VALUE" not in blob
    assert "TEST_PASSWORD" not in blob


def test_runtime_production_tools_have_risk_and_are_governed() -> None:
    rec = InMemoryAuditRecorder()
    rt = ServerRuntime.create(ServerConfig(), auditor=rec)
    assert rt.surface_info()["governance"] == "centralized"
    names = rt.governance.catalog.known_names()
    assert names
    assert TOOL_LIST_DOCS in names
    for name in names:
        identity = rt.governance.resolve_tool(name)
        assert identity.known is True
        assert isinstance(identity.risk, RiskLevel)
    catalog = rt.capability_catalog()
    assert catalog is not None
    rt_deny = ServerRuntime.create(
        ServerConfig(),
        policy=StaticDecisionPolicy({TOOL_LIST_DOCS: GovernanceDecision.DENY}),
        auditor=InMemoryAuditRecorder(),
    )
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError):
        rt_deny.governance.execute(TOOL_LIST_DOCS, lambda: calls.append("x") or "no")
    assert calls == []


def test_operations_registration_path_is_governed_when_present() -> None:
    src = open("src/yasin_mcp/server/runtime.py", encoding="utf-8").read()
    assert "add_governed(toolset.list_services" in src
    assert "add_governed(toolset.service_status" in src
    assert "add_governed(toolset.health" in src
    assert "add_governed(toolset.diagnostics" in src
    assert src.count("server.add_tool") == 1
    assert "gate.wrap_tool" in src


def test_no_global_mutable_authorization_state() -> None:
    cat = ToolRiskCatalog({"t": RiskLevel.READ_ONLY})
    g1 = GovernanceGate(
        cat,
        policy=StaticDecisionPolicy({"t": GovernanceDecision.DENY}),
        auditor=InMemoryAuditRecorder(),
    )
    g2 = GovernanceGate(
        ToolRiskCatalog({"t": RiskLevel.READ_ONLY}),
        policy=StaticDecisionPolicy({"t": GovernanceDecision.ALLOW}),
        auditor=InMemoryAuditRecorder(),
    )
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError):
        g1.execute("t", lambda: calls.append("1") or "no")
    assert g2.execute("t", lambda: calls.append("2") or "ok") == "ok"
    assert calls == ["2"]


def test_wrap_tool_is_the_mcp_enforcement_boundary() -> None:
    gate, _, calls = _counting_gate({"blocked": RiskLevel.HIGH_RISK})
    wrapped = gate.wrap_tool("blocked", lambda: calls.append("x") or "no")
    with pytest.raises(ToolError):
        wrapped()
    assert calls == []
    gate2, _, calls2 = _counting_gate()
    assert gate2.wrap_tool("safe.read", lambda: calls2.append("y") or 1)() == 1
    assert calls2 == ["y"]
