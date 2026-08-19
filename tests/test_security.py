"""Security and observability regression tests."""

from __future__ import annotations

import json
import logging

import pytest

from yasin_mcp.audit.logging_setup import JsonFormatter, log_with_context, new_request_id, redact
from yasin_mcp.config.config import InvalidConfigurationError, SecretStr, ServerConfig, load_config
from yasin_mcp.errors.errors import PolicyDeniedError, ValidationError
from yasin_mcp.policies.policy import SafetyClass, evaluate_policy
from yasin_mcp.policies.timeouts import validate_adapter_timeout


def test_future_mutation_classes_remain_denied() -> None:
    for safety_class in (SafetyClass.PROPOSED_MUTATION, SafetyClass.CONFIRMED_MUTATION):
        with pytest.raises(PolicyDeniedError):
            evaluate_policy("future_change", safety_class=safety_class)


def test_explicit_deny_is_fail_closed() -> None:
    decision = evaluate_policy("safe_read", safety_class=SafetyClass.DENY)
    assert decision.allowed is False


def test_read_only_policy_decision() -> None:
    decision = evaluate_policy("read_docs")
    assert decision.allowed is True
    assert decision.safety_class is SafetyClass.READ_ONLY


@pytest.mark.parametrize("seconds", [0, -1, 121, 999])
def test_adapter_timeout_bounds(seconds: int) -> None:
    with pytest.raises(ValidationError):
        validate_adapter_timeout(seconds)


def test_adapter_timeout_accepts_safe_value() -> None:
    assert validate_adapter_timeout(30) == 30


def test_config_bounds() -> None:
    with pytest.raises(InvalidConfigurationError):
        ServerConfig(request_timeout_seconds=121)
    with pytest.raises(InvalidConfigurationError):
        ServerConfig(max_concurrent_requests=257)


def test_config_normalizes_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YASIN_MCP_LOG_LEVEL", "warning")
    assert load_config().log_level == "WARNING"


def test_secret_redacts_nested_configuration() -> None:
    secret = "super-secret-value"
    config = ServerConfig(github_token=SecretStr(secret))
    assert secret not in repr(config)
    assert secret not in str(config.github_token)
    assert redact({"github_token": secret})["github_token"] == "***"


def test_redact_sensitive_keys_recursively() -> None:
    value = {
        "token": "abc",
        "nested": {"authorization": "Bearer xyz", "safe": "ok"},
        "items": [{"api_key": "def"}],
    }
    result = redact(value)
    assert result == {
        "token": "***",
        "nested": {"authorization": "***", "safe": "ok"},
        "items": [{"api_key": "***"}],
    }


def test_request_id_is_uuid_like() -> None:
    first = new_request_id()
    second = new_request_id()
    assert first != second
    assert len(first) == 36


def test_json_formatter_redacts_fields() -> None:
    record = logging.LogRecord("yasin_mcp", logging.INFO, __file__, 1, "ok", (), None)
    record.fields = {"github_token": "secret", "status": "ok"}  # type: ignore[attr-defined]
    record.request_id = "request-1"  # type: ignore[attr-defined]
    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "request-1"
    assert payload["fields"] == {"github_token": "***", "status": "ok"}
    assert "secret" not in JsonFormatter().format(record)


def test_log_helper_redacts_before_logging(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("yasin_mcp.security-test")
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_with_context(
            logger,
            logging.INFO,
            "request",
            request_id="r1",
            fields={"api_key": "secret", "value": "safe"},
        )
    assert "secret" not in caplog.text
    assert "***" in caplog.text
