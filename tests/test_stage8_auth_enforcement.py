"""Stage 8 — mandatory authentication enforcement on MCP execution path."""

from __future__ import annotations

import concurrent.futures

import pytest

from yasin_mcp.auth import AUTH_TOKEN_KWARG, auth_request_scope
from yasin_mcp.config.config import SecretStr, ServerConfig
from yasin_mcp.contracts.integration_context import IntegrationContext
from yasin_mcp.errors.errors import PolicyDeniedError, UnauthenticatedError, ValidationError
from yasin_mcp.governance import (
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


def _gate(
    *,
    require: bool = True,
    token: str = "TEST_STAGE8_SECRET",
    subject: str = "local-operator",
    entries: dict[str, RiskLevel] | None = None,
    policy=None,
) -> GovernanceGate:
    cfg = ServerConfig(
        auth_token=SecretStr(token),
        require_authentication=require,
        auth_subject_id=subject,
    )
    return GovernanceGate(
        ToolRiskCatalog(entries or {"safe": RiskLevel.READ_ONLY}),
        policy=policy or DefaultConservativePolicy(),
        auditor=InMemoryAuditRecorder(),
        security_config=cfg,
    )


def test_require_auth_missing_credential_blocks_execution() -> None:
    gate = _gate()
    calls: list[str] = []
    with pytest.raises(UnauthenticatedError):
        gate.execute("safe", lambda: calls.append("x") or 1)
    assert calls == []


def test_require_auth_invalid_credential_blocks() -> None:
    gate = _gate()
    calls: list[str] = []
    with pytest.raises(UnauthenticatedError):
        gate.execute(
            "safe",
            lambda: calls.append("x") or 1,
            kwargs={AUTH_TOKEN_KWARG: "wrong-secret"},
        )
    assert calls == []


def test_require_auth_valid_credential_allows_then_governance() -> None:
    gate = _gate()
    assert (
        gate.execute(
            "safe",
            lambda: 42,
            kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET"},
            context=None,
        )
        == 42
    )


def test_auth_success_does_not_bypass_deny() -> None:
    gate = _gate(entries={"danger": RiskLevel.HIGH_RISK})
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError):
        gate.execute(
            "danger",
            lambda: calls.append("x") or "no",
            kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET"},
        )
    assert calls == []


def test_auth_success_does_not_bypass_approval_required() -> None:
    gate = _gate(entries={"mut": RiskLevel.MUTATION})
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError) as ei:
        gate.execute(
            "mut",
            lambda: calls.append("x") or "no",
            kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET"},
        )
    assert calls == []
    assert ei.value.details["decision"] == "approval_required"


def test_auth_token_stripped_from_tool_kwargs() -> None:
    gate = _gate()
    seen: list[dict] = []

    def tool(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(dict(kwargs))
        return "ok"

    assert (
        gate.execute(
            "safe",
            tool,
            kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET", "path": "docs"},
        )
        == "ok"
    )
    assert AUTH_TOKEN_KWARG not in seen[0]
    assert seen[0]["path"] == "docs"


def test_compatibility_mode_without_auth_still_works() -> None:
    gate = _gate(require=False)
    assert gate.execute("safe", lambda: 1) == 1


def test_context_mismatch_fail_closed() -> None:
    gate = _gate(subject="subject-A")
    from yasin_mcp.governance.types import GovernanceContext

    ctx = GovernanceContext(agent_id="subject-B", request_id="r1")
    with pytest.raises(ValidationError):
        gate.execute(
            "safe",
            lambda: 1,
            kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET"},
            context=ctx,
        )


def test_request_scope_isolation_concurrent() -> None:
    gate = _gate(require=False)

    def worker(i: int) -> int:
        with auth_request_scope(
            asserted=IntegrationContext(request_id=f"req-{i}", project_id=f"p-{i}")
        ):
            return gate.execute("safe", lambda: i)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(12)))
    assert results == list(range(12))


def test_runtime_require_auth_blocks_without_token() -> None:
    cfg = ServerConfig(
        auth_token=SecretStr("TEST_STAGE8_SECRET"),
        require_authentication=True,
    )
    rt = ServerRuntime.create(cfg)
    calls: list[str] = []
    with pytest.raises(UnauthenticatedError):
        rt.governance.execute(TOOL_LIST_DOCS, lambda: calls.append("x") or "no")
    assert calls == []


def test_runtime_require_auth_with_token_then_policy_deny() -> None:
    cfg = ServerConfig(
        auth_token=SecretStr("TEST_STAGE8_SECRET"),
        require_authentication=True,
    )
    rt = ServerRuntime.create(
        cfg,
        policy=StaticDecisionPolicy({TOOL_LIST_DOCS: GovernanceDecision.DENY}),
    )
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError):
        rt.governance.execute(
            TOOL_LIST_DOCS,
            lambda: calls.append("x") or "no",
            kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET"},
        )
    assert calls == []


def test_wrap_tool_enforces_auth() -> None:
    gate = _gate()
    calls: list[str] = []
    wrapped = gate.wrap_tool("safe", lambda: calls.append("x") or 1)
    with pytest.raises(UnauthenticatedError):
        wrapped()
    assert calls == []
    assert wrapped(**{AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET"}) == 1
    assert calls == ["x"]


def test_secret_not_in_unauthenticated_error() -> None:
    gate = _gate()
    with pytest.raises(UnauthenticatedError) as ei:
        gate.execute("safe", lambda: 1, kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET_WRONG"})
    assert "TEST_STAGE8_SECRET" not in str(ei.value)
    assert "TEST_STAGE8_SECRET" not in repr(ei.value.details)


def test_unknown_tool_still_deny_after_auth() -> None:
    gate = _gate(entries={})
    with pytest.raises(PolicyDeniedError) as ei:
        gate.execute(
            "no_such_tool",
            lambda: "x",
            kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE8_SECRET"},
        )
    assert ei.value.details["decision"] == "deny"
