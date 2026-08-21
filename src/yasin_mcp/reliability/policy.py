"""Explicit reliability boundaries for outbound read-only operations.

Retries are only permitted for safe, idempotent reads. There is no unbounded
retry loop. Rate-limit errors remain explicit after the retry budget is exhausted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

MAX_SAFE_RETRIES: Final[int] = 2
RETRY_BACKOFF_SECONDS: Final[tuple[float, ...]] = (0.05, 0.15)


@dataclass(frozen=True)
class ReliabilityPolicy:
    """Bounded retry and timeout policy for safe read operations."""

    max_retries: int = MAX_SAFE_RETRIES
    backoff_seconds: tuple[float, ...] = RETRY_BACKOFF_SECONDS
    retry_on_rate_limit: bool = True
    retry_on_timeout: bool = False  # timeouts stay deterministic; no retry by default

    def __post_init__(self) -> None:
        if self.max_retries < 0 or self.max_retries > MAX_SAFE_RETRIES:
            raise ValueError(f"max_retries must be between 0 and {MAX_SAFE_RETRIES}")
        if len(self.backoff_seconds) < self.max_retries:
            raise ValueError("backoff_seconds must cover max_retries entries")

    def delay_for_attempt(self, attempt: int) -> float:
        """Return deterministic backoff delay before the given 0-based retry attempt."""
        if attempt < 0 or attempt >= self.max_retries:
            raise ValueError("attempt out of retry range")
        return self.backoff_seconds[attempt]

    def should_retry(self, *, error_kind: str, attempt: int) -> bool:
        """Whether another attempt is permitted after *attempt* failed attempts."""
        if attempt >= self.max_retries:
            return False
        if error_kind == "rate_limit" and self.retry_on_rate_limit:
            return True
        if error_kind == "timeout" and self.retry_on_timeout:
            return True
        return False


def default_policy() -> ReliabilityPolicy:
    return ReliabilityPolicy()
