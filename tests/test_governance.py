"""Unit and enforcement tests for MCP governance (Issue #80)."""

from __future__ import annotations

import inspect
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from yasin_mcp.errors.errors import PolicyDeniedError, ValidationError
from yasin_mcp.governance import (
    ALLOW,
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


def _gate(
    entries: dict[str, RiskLevel] | None = None,
    *,
    policy: Any = None,
) -> tuple[GovernanceGate, InMemoryAuditRecorder]:
    catalog = ToolRiskCatalog(entries or {"safe.read": RiskLevel.READ_ONLY})
    rec = InMemoryAuditRecorder()
    return GovernanceGate(catalog, policy=policy or DefaultConservativePolicy(), auditor=rec), rec


def test_decision_enum_values() -> None:
    assert ALLOW is GovernanceDecision.ALLOW
    assert DENY is GovernanceDecision.DENY
    assert APPROVAL_REQUIRED is GovernanceDecision.APPROVAL_REQUIRED


def test_risk_and_default_policy() -> None:
    for level in (
        RiskLevel.READ_ONLY,
        RiskLevel.LOW_RISK,
        RiskLevel.MUTATION,
        RiskLevel.HIGH_RISK,
    ):
        assert ToolIdentity(name=f"t_{level.value}", risk=level).risk is level
    p = DefaultConservativePolicy()
    assert p.evaluate(ToolIdentity(name="a", risk=RiskLevel.READ_ONLY)) is GovernanceDecision.ALLOW
    assert p.evaluate(ToolIdentity(name="b", risk=RiskLevel.LOW_RISK)) is GovernanceDecision.ALLOW
    assert (
        p.evaluate(ToolIdentity(name="c", risk=RiskLevel.MUTATION))
        is GovernanceDecision.APPROVAL_REQUIRED
    )
    assert p.evaluate(ToolIdentity(name="d", risk=RiskLevel.HIGH_RISK)) is GovernanceDecision.DENY
    assert (
        p.evaluate(ToolIdentity(name="e", risk=RiskLevel.HIGH_RISK, known=False))
        is GovernanceDecision.DENY
    )


def test_allow_executes_once() -> None:
    gate, rec = _gate()
    calls: list[int] = []

    def impl(x: int = 1) -> dict[str, int]:
        calls.append(x)
        return {"ok": x}

    assert gate.execute("safe.read", impl, kwargs={"x": 7}) == {"ok": 7}
    assert calls == [7]
    assert any(e.event_type is AuditEventType.EXECUTION_RESULT for e in rec.events)


def test_deny_approval_unknown_do_not_execute() -> None:
    gate, _ = _gate({"blocked": RiskLevel.HIGH_RISK})
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError) as ei:
        gate.execute("blocked", lambda: calls.append("x") or "no")
    assert calls == [] and ei.value.details["decision"] == DENY.value

    gate2, _ = _gate({"m": RiskLevel.MUTATION})
    with pytest.raises(PolicyDeniedError) as ei2:
        gate2.execute("m", lambda: calls.append("x") or "no")
    assert calls == [] and ei2.value.details["decision"] == APPROVAL_REQUIRED.value

    gate3, _ = _gate({})
    with pytest.raises(PolicyDeniedError) as ei3:
        gate3.execute("unknown_xyz", lambda: calls.append("x") or "no")
    assert calls == [] and ei3.value.details["known"] is False


def test_wrap_tool_enforcement() -> None:
    gate, _ = _gate({"blocked": RiskLevel.HIGH_RISK})
    calls: list[str] = []
    with pytest.raises(ToolError):
        gate.wrap_tool("blocked", lambda: calls.append("x") or "no")()
    assert calls == []
    gate2, _ = _gate()
    assert gate2.wrap_tool("safe.read", lambda: 1)() == 1


def test_wrap_tool_preserves_callable_signature_for_mcp_schema_generation() -> None:
    gate, _ = _gate()

    def impl(owner: str, repository: str, limit: int = 20) -> dict[str, Any]:
        return {"owner": owner, "repository": repository, "limit": limit}

    wrapped = gate.wrap_tool("safe.read", impl)
    signature = inspect.signature(wrapped)

    assert list(signature.parameters) == ["owner", "repository", "limit"]
    assert signature.parameters["owner"].annotation is str
    assert signature.parameters["repository"].annotation is str
    assert signature.parameters["limit"].default == 20
    assert wrapped(owner="yusi20006-max", repository="Yasin-MCP")["repository"] == "Yasin-MCP"


def test_context_redaction_audit_failure() -> None:
    gate, rec = _gate()
    ctx = GovernanceContext(
        client_id="c1",
        extra={"token": "TEST_SECRET_VALUE", "api_key": "TEST_API_TOKEN"},
    )
    gate.execute("safe.read", lambda: "ok", context=ctx)
    blob = str([e.as_dict() for e in rec.events])
    assert "TEST_SECRET_VALUE" not in blob
    assert "TEST_API_TOKEN" not in blob
    assert sanitize_audit_payload({"password": "TEST_SECRET_VALUE"})["password"] == "***"
    with pytest.raises(RuntimeError):
        gate.execute(
            "safe.read",
            lambda: (_ for _ in ()).throw(RuntimeError("controlled failure")),
        )
    assert rec.of_type(AuditEventType.EXECUTION_FAILURE)


def test_invalid_policy() -> None:
    with pytest.raises(ValidationError):
        StaticDecisionPolicy({"t": "bad"})  # type: ignore[dict-item]

    class Bad:
        def evaluate(self, tool: ToolIdentity, context: Any = None) -> str:
            return "allow"

    gate, _ = _gate(policy=Bad())
    with pytest.raises(ValidationError):
        gate.execute("safe.read", lambda: "x")
