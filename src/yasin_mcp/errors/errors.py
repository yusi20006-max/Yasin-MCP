"""Structured error model for Yasin-MCP.

All errors surfaced to callers (MCP clients, adapter consumers) must
be instances of McpError or a subclass, carrying a machine-readable
category. Raw/unstructured exceptions must never cross a public
boundary (server, adapter, tool) uncaught -- callers should catch and
wrap them here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """Machine-readable error categories.

    Intentionally small and extensible -- new categories are added
    only when a real need arises (mirrors the same design choice
    made in the Yasin-Operations Core error model).
    """

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHENTICATED = "unauthenticated"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UNAVAILABLE_DEPENDENCY = "unavailable_dependency"
    UPSTREAM_ERROR = "upstream_error"
    POLICY_DENIED = "policy_denied"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class McpError(Exception):
    """Base structured error type.

    A dataclass Exception so it carries structured fields
    (category, message, details) while still being raisable and
    catchable like a normal exception. `details` must never contain
    secrets, tokens, or credentials -- see audit/redaction.py for
    the corresponding redaction guarantee used when logging errors.
    """

    category: ErrorCategory
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message or not self.message.strip():
            raise ValueError("McpError.message must not be empty")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.category.value}: {self.message}"


class ValidationError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.VALIDATION_ERROR, message, details or {})


class NotFoundError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.NOT_FOUND, message, details or {})


class UnauthenticatedError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.UNAUTHENTICATED, message, details or {})


class UnauthorizedError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.UNAUTHORIZED, message, details or {})


class RateLimitedError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.RATE_LIMITED, message, details or {})


class TimeoutMcpError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.TIMEOUT, message, details or {})


class UnavailableDependencyError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.UNAVAILABLE_DEPENDENCY, message, details or {})


class UpstreamError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.UPSTREAM_ERROR, message, details or {})


class PolicyDeniedError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.POLICY_DENIED, message, details or {})


class InternalError(McpError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(ErrorCategory.INTERNAL_ERROR, message, details or {})
