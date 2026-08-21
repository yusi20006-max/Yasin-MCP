"""Reliability policy bounds (P2-5)."""

import pytest

from yasin_mcp.reliability.policy import (
    MAX_SAFE_RETRIES,
    ReliabilityPolicy,
    default_policy,
)


def test_default_policy_is_bounded() -> None:
    policy = default_policy()
    assert policy.max_retries == MAX_SAFE_RETRIES
    assert policy.max_retries <= 2
    assert policy.retry_on_timeout is False


def test_should_retry_rate_limit_within_budget() -> None:
    policy = default_policy()
    assert policy.should_retry(error_kind="rate_limit", attempt=0) is True
    assert policy.should_retry(error_kind="rate_limit", attempt=1) is True
    assert policy.should_retry(error_kind="rate_limit", attempt=2) is False


def test_timeout_not_retried_by_default() -> None:
    policy = default_policy()
    assert policy.should_retry(error_kind="timeout", attempt=0) is False


def test_deterministic_backoff() -> None:
    policy = default_policy()
    assert policy.delay_for_attempt(0) == policy.backoff_seconds[0]
    assert policy.delay_for_attempt(1) == policy.backoff_seconds[1]


def test_invalid_max_retries_rejected() -> None:
    with pytest.raises(ValueError):
        ReliabilityPolicy(max_retries=99)
