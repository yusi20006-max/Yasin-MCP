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


def test_future_mutation_classes_subject_to_governance_after_stage_11() -> None:
    for safety_class in (SafetyClass.PROPOSED_MUTATION, SafetyClass.CONFIRMED_MUTATION):
        decision = evaluate_policy("future_change", safety_class=safety_class)
        assert decision.allowed is True


def test_explicit_deny_is_fail_closed() -> None:
    decision = evaluate_policy("safe_read", safety_class=SafetyClass.DENY)
    assert decision.allowed is False


def test_read_only_policy_decision() -> None:
    decision = evaluate_policy("read_docs")
    assert decision.allowed is True


def test_redact_secrets() -> None:
    payload = {"token": "SECRET", "nested": {"password": "x"}}
    out = redact(payload)
    assert "SECRET" not in str(out)


def test_request_id_unique() -> None:
    assert new_request_id() != new_request_id()


def test_json_formatter_basic() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", (), None)
    line = formatter.format(record)
    data = json.loads(line)
    assert data["message"] == "hello"


def test_log_with_context_does_not_raise() -> None:
    log_with_context(logging.getLogger("t"), logging.INFO, "msg", request_id="r1")


def test_validate_adapter_timeout() -> None:
    validate_adapter_timeout(1.0)
    with pytest.raises(ValidationError):
        validate_adapter_timeout(0)


def test_secret_str_redacts() -> None:
    s = SecretStr("super-secret")
    assert "super-secret" not in repr(s)


def test_invalid_config_raises() -> None:
    with pytest.raises(InvalidConfigurationError):
        ServerConfig(request_timeout_seconds=0)
