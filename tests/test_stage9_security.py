"""Stage 9 / Issue #92 — structured errors, credential transport, trust hardening."""

from __future__ import annotations

import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

from yasin_mcp.auth import AUTH_TOKEN_KWARG, credential_transport_summary
from yasin_mcp.config.config import SecretStr, ServerConfig
from yasin_mcp.errors.client_contract import (
    CLIENT_ERROR_CONTRACT_VERSION,
    ClientErrorCode,
    map_mcp_error,
    raise_as_mcp_tool_error,
)
from yasin_mcp.errors.errors import McpError, PolicyDeniedError, UnauthenticatedError, ValidationError
from yasin_mcp.governance import (
    DefaultConservativePolicy,
    GovernanceGate,
    InMemoryAuditRecorder,
    RiskLevel,
    ToolRiskCatalog,
)
from yasin_mcp.governance.types import GovernanceContext


def _gate(require: bool = True) -> GovernanceGate:
    return GovernanceGate(
        ToolRiskCatalog({"safe": RiskLevel.READ_ONLY, "hi": RiskLevel.HIGH_RISK}),
        policy=DefaultConservativePolicy(),
        auditor=InMemoryAuditRecorder(),
        security_config=ServerConfig(
            auth_token=SecretStr("TEST_STAGE9_SECRET"),
            require_authentication=require,
            auth_subject_id="local-operator",
        ),
    )


def test_wrap_tool_maps_unauthenticated_to_tool_error() -> None:
    gate = _gate(require=True)
    wrapped = gate.wrap_tool("safe", lambda: 1)
    with pytest.raises(ToolError) as ei:
        wrapped()
    payload = json.loads(str(ei.value))
    assert payload["code"] == ClientErrorCode.AUTHENTICATION_REQUIRED.value
    assert payload["error_contract_version"] == CLIENT_ERROR_CONTRACT_VERSION
    assert "TEST_STAGE9_SECRET" not in str(ei.value)


def test_wrap_tool_maps_deny_to_authorization_denied() -> None:
    gate = _gate(require=True)
    wrapped = gate.wrap_tool("hi", lambda: "x")
    with pytest.raises(ToolError) as ei:
        wrapped(**{AUTH_TOKEN_KWARG: "TEST_STAGE9_SECRET"})
    payload = json.loads(str(ei.value))
    assert payload["code"] == ClientErrorCode.AUTHORIZATION_DENIED.value


def test_wrap_tool_maps_approval_required() -> None:
    gate = GovernanceGate(
        ToolRiskCatalog({"mut": RiskLevel.MUTATION}),
        policy=DefaultConservativePolicy(),
        auditor=InMemoryAuditRecorder(),
        security_config=ServerConfig(
            auth_token=SecretStr("TEST_STAGE9_SECRET"),
            require_authentication=True,
        ),
    )
    wrapped = gate.wrap_tool("mut", lambda: "x")
    with pytest.raises(ToolError) as ei:
        wrapped(**{AUTH_TOKEN_KWARG: "TEST_STAGE9_SECRET"})
    payload = json.loads(str(ei.value))
    assert payload["code"] == ClientErrorCode.APPROVAL_REQUIRED.value


def test_map_unknown_tool_code() -> None:
    err = PolicyDeniedError(
        "denied",
        details={"tool": "x", "decision": "deny", "risk": "high_risk", "known": False},
    )
    assert map_mcp_error(err)["code"] == ClientErrorCode.UNKNOWN_TOOL.value


def test_secret_keys_stripped_from_client_payload() -> None:
    err = UnauthenticatedError(
        "fail",
        details={"status": "invalid_credential", "token": "SECRET_LEAK", "auth_token": "x"},
    )
    blob = json.dumps(map_mcp_error(err))
    assert "SECRET_LEAK" not in blob


def test_credential_never_reaches_tool_after_wrap() -> None:
    gate = _gate(require=True)
    seen: list[dict] = []

    def tool(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(dict(kwargs))
        return 1

    wrapped = gate.wrap_tool("safe", tool)
    assert wrapped(**{AUTH_TOKEN_KWARG: "TEST_STAGE9_SECRET", "q": "docs"}) == 1
    assert AUTH_TOKEN_KWARG not in seen[0]


def test_credential_transport_summary_honest() -> None:
    s = credential_transport_summary()
    assert s["remote_peer_authenticated"] is False
    assert s["credential_reaches_tool_body"] is False


def test_forged_trusted_still_rejected() -> None:
    from yasin_mcp.contracts.integration_context import IntegrationContext

    with pytest.raises(ValidationError):
        IntegrationContext.from_mapping({"trust": "trusted"})


def test_mcp_error_not_unexpected_when_wrapped() -> None:
    gate = _gate(require=True)
    wrapped = gate.wrap_tool("safe", lambda: 1)
    with pytest.raises(ToolError) as ei:
        wrapped()
    assert not isinstance(ei.value, UnexpectedToolError)


def test_identity_mismatch_tool_error() -> None:
    gate = _gate(require=True)
    ctx = GovernanceContext(agent_id="other-agent")
    try:
        gate.execute(
            "safe",
            lambda: 1,
            kwargs={AUTH_TOKEN_KWARG: "TEST_STAGE9_SECRET"},
            context=ctx,
        )
    except McpError as exc:
        with pytest.raises(ToolError) as ei:
            raise_as_mcp_tool_error(exc)
        payload = json.loads(str(ei.value))
        assert payload["code"] == ClientErrorCode.INVALID_CONTEXT.value
