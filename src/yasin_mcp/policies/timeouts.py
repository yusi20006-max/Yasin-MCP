"""Bounded timeout policy for future adapters."""

from __future__ import annotations

from yasin_mcp.errors.errors import ValidationError

MIN_ADAPTER_TIMEOUT_SECONDS = 1
MAX_ADAPTER_TIMEOUT_SECONDS = 120


def validate_adapter_timeout(seconds: int) -> int:
    """Validate an adapter timeout and fail closed outside safe bounds."""
    if not MIN_ADAPTER_TIMEOUT_SECONDS <= seconds <= MAX_ADAPTER_TIMEOUT_SECONDS:
        raise ValidationError(
            "adapter timeout is outside the allowed safety bounds",
            details={
                "minimum": MIN_ADAPTER_TIMEOUT_SECONDS,
                "maximum": MAX_ADAPTER_TIMEOUT_SECONDS,
            },
        )
    return seconds
