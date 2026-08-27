"""Stage 7.1 / Issue #89 — authentication boundary and trust isolation."""

from __future__ import annotations

import concurrent.futures

import pytest

from yasin_mcp.auth import (
    AuthenticatedIdentity,
    AuthStatus,
    authenticate_shared_secret,
    authenticate_stdio_peer,
    bind_context,
    resolve_authentication,
)
from yasin_mcp.auth.types import AuthOutcome
from yasin_mcp.config.config import InvalidConfigurationError, SecretStr, ServerConfig, load_config
from yasin_mcp.contracts.integration_context import IntegrationContext, TrustClassification
from yasin_mcp.errors.errors import PolicyDeniedError, UnauthenticatedError, ValidationError
from yasin_mcp.governance import (
    DefaultConservativePolicy,
    GovernanceGate,
    InMemoryAuditRecorder,
    RiskLevel,
    ToolRiskCatalog,
)
from yasin_mcp.server.runtime import ServerRuntime


def test_stdio_peer_never_trusted() -> None:
    outcome = authenticate_stdio_peer()
    assert outcome.status is AuthStatus.TRANSPORT_UNAVAILABLE
    assert outcome.identity is None
    assert outcome.transport == "stdio"


def test_caller_cannot_construct_trusted_via_context() -> None:
    with pytest.raises(ValidationError):
        IntegrationContext.from_mapping({"trust": "trusted"})


def test_authenticated_identity_requires_trusted() -> None:
    with pytest.raises(ValidationError):
        AuthenticatedIdentity(
            subject_id="x",
            scheme="shared_secret",
            trust=TrustClassification.ASSERTED,
        )


def test_shared_secret_success_issues_config_subject() -> None:
    secret = SecretStr("TEST_AUTH_SECRET_VALUE")
    out = authenticate_shared_secret(
        configured_secret=secret,
        presented_secret="TEST_AUTH_SECRET_VALUE",
        subject_id="local-operator",
    )
    assert out.is_authenticated
    assert out.identity is not None
    assert out.identity.subject_id == "local-operator"
    assert out.identity.trust is TrustClassification.TRUSTED
    blob = str(out.as_dict())
    assert "TEST_AUTH_SECRET_VALUE" not in blob


def test_shared_secret_invalid_and_missing() -> None:
    secret = SecretStr("TEST_AUTH_SECRET_VALUE")
    bad = authenticate_shared_secret(
        configured_secret=secret, presented_secret="wrong", subject_id="op"
    )
    assert bad.status is AuthStatus.INVALID_CREDENTIAL
    assert bad.identity is None
    missing = authenticate_shared_secret(
        configured_secret=secret, presented_secret=None, subject_id="op"
    )
    assert missing.status is AuthStatus.MISSING_CREDENTIAL


def test_context_mismatch_fail_closed() -> None:
    secret = SecretStr("TEST_AUTH_SECRET_VALUE")
    auth = authenticate_shared_secret(
        configured_secret=secret,
        presented_secret="TEST_AUTH_SECRET_VALUE",
        subject_id="subject-A",
    )
    asserted = IntegrationContext(agent_id="subject-B", request_id="req-1")
    with pytest.raises(ValidationError) as ei:
        bind_context(asserted, auth)
    assert "conflicts" in ei.value.message


def test_require_auth_blocks_without_credential() -> None:
    cfg = ServerConfig(
        auth_token=SecretStr("TEST_AUTH_SECRET_VALUE"),
        require_authentication=True,
        auth_subject_id="local-operator",
    )
    with pytest.raises(UnauthenticatedError):
        resolve_authentication(config=cfg, asserted=IntegrationContext())


def test_require_auth_allows_after_valid_secret_then_governance_still_applies() -> None:
    cfg = ServerConfig(
        auth_token=SecretStr("TEST_AUTH_SECRET_VALUE"),
        require_authentication=True,
        auth_subject_id="local-operator",
    )
    bound = resolve_authentication(
        config=cfg,
        asserted=IntegrationContext(agent_id="local-operator", request_id="r1"),
        presented_secret="TEST_AUTH_SECRET_VALUE",
    )
    assert bound.auth.is_authenticated
    gate = GovernanceGate(
        ToolRiskCatalog({"blocked": RiskLevel.HIGH_RISK}),
        policy=DefaultConservativePolicy(),
        auditor=InMemoryAuditRecorder(),
    )
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError):
        gate.execute(
            "blocked",
            lambda: calls.append("x") or "no",
            context=bound.governance,
        )
    assert calls == []


def test_default_unauthenticated_path_still_governed() -> None:
    cfg = ServerConfig()
    bound = resolve_authentication(
        config=cfg,
        asserted=IntegrationContext(agent_id="anyone", request_id="r2"),
    )
    assert bound.auth.status is AuthStatus.UNAUTHENTICATED
    assert bound.trust is TrustClassification.ASSERTED
    gate = GovernanceGate(
        ToolRiskCatalog({"safe": RiskLevel.READ_ONLY}),
        policy=DefaultConservativePolicy(),
        auditor=InMemoryAuditRecorder(),
    )
    assert gate.execute("safe", lambda: 1, context=bound.governance) == 1


def test_secret_not_in_config_repr() -> None:
    cfg = ServerConfig(auth_token=SecretStr("TEST_AUTH_SECRET_VALUE"))
    assert "TEST_AUTH_SECRET_VALUE" not in repr(cfg)
    assert "TEST_AUTH_SECRET_VALUE" not in str(cfg.auth_token)


def test_require_auth_without_token_fails_config() -> None:
    with pytest.raises(InvalidConfigurationError):
        ServerConfig(require_authentication=True)


def test_load_config_require_auth_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YASIN_MCP_AUTH_TOKEN", "TEST_AUTH_SECRET_VALUE")
    monkeypatch.setenv("YASIN_MCP_REQUIRE_AUTH", "true")
    monkeypatch.setenv("YASIN_MCP_AUTH_SUBJECT", "op-1")
    cfg = load_config()
    assert cfg.require_authentication is True
    assert cfg.auth_subject_id == "op-1"
    assert cfg.auth_token is not None
    assert "TEST_AUTH_SECRET_VALUE" not in repr(cfg)


def test_concurrent_auth_isolation() -> None:
    secret = SecretStr("TEST_AUTH_SECRET_VALUE")
    cfg = ServerConfig(auth_token=secret, auth_subject_id="local-operator")

    def worker(i: int) -> str:
        bound = resolve_authentication(
            config=cfg,
            asserted=IntegrationContext(request_id=f"req-{i}", session_id=f"s-{i}"),
            presented_secret="TEST_AUTH_SECRET_VALUE",
        )
        return bound.governance.extra.get("auth_subject_id", "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(12)))
    assert results == ["local-operator"] * 12


def test_surface_info_authentication_boundary() -> None:
    info = ServerRuntime.create(ServerConfig()).surface_info()
    assert info["authentication"]["trusted_via_stdio_peer"] is False
    assert info["authentication"]["caller_cannot_set_trusted"] is True
    assert info["require_authentication"] is False


def test_invalid_credential_attempt_does_not_authenticate() -> None:
    cfg = ServerConfig(auth_token=SecretStr("TEST_AUTH_SECRET_VALUE"))
    bound = resolve_authentication(
        config=cfg,
        asserted=IntegrationContext(),
        presented_secret="nope",
    )
    assert bound.auth.status is AuthStatus.INVALID_CREDENTIAL
    assert bound.auth.identity is None


def test_auth_outcome_rejects_identity_on_failure() -> None:
    with pytest.raises(ValidationError):
        AuthOutcome(
            status=AuthStatus.INVALID_CREDENTIAL,
            identity=AuthenticatedIdentity(subject_id="x", scheme="shared_secret"),
        )
