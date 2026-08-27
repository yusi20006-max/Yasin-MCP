"""Stage 9 / Issue #92 — machine-readable client error contract.

Maps internal McpError types to stable codes safe for MCP ToolError
messages. Never includes secrets, tracebacks, or exception *values*.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import Enum
from typing import Any, Final

from yasin_mcp.errors.errors import (
    ErrorCategory,
    McpError,
    PolicyDeniedError,
    UnauthenticatedError,
    ValidationError,
)

CLIENT_ERROR_CONTRACT_VERSION: Final[str] = "1.0.0"


class ClientErrorCode(str, Enum):
    """Stable codes exposed to MCP clients (via ToolError message JSON)."""

    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    INVALID_CONTEXT = "INVALID_CONTEXT"
    INVALID_POLICY = "INVALID_POLICY"
    EXECUTION_FAILURE = "EXECUTION_FAILURE"
    UPSTREAM_FAILURE = "UPSTREAM_FAILURE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def map_mcp_error(exc: McpError) -> dict[str, Any]:
    """Build a secret-free client payload from an application error."""
    code = _code_for(exc)
    details = _safe_details(exc)
    return {
        "error_contract_version": CLIENT_ERROR_CONTRACT_VERSION,
        "code": code.value,
        "category": exc.category.value,
        "message": exc.message,
        "details": details,
    }


def format_tool_error_message(payload: Mapping[str, Any]) -> str:
    """Single-line JSON for ToolError content (model-readable, secret-free)."""
    return json.dumps(dict(payload), separators=(",", ":"), sort_keys=True)


def _code_for(exc: McpError) -> ClientErrorCode:
    if isinstance(exc, PolicyDeniedError):
        decision = str(exc.details.get("decision", ""))
        if decision == "approval_required":
            return ClientErrorCode.APPROVAL_REQUIRED
        if decision == "deny" and exc.details.get("known") is False:
            return ClientErrorCode.UNKNOWN_TOOL
        return ClientErrorCode.AUTHORIZATION_DENIED

    if isinstance(exc, UnauthenticatedError):
        status = str(exc.details.get("status", ""))
        if status in {"invalid_credential", "malformed"}:
            return ClientErrorCode.AUTHENTICATION_FAILED
        return ClientErrorCode.AUTHENTICATION_REQUIRED

    if isinstance(exc, ValidationError):
        reason = str(exc.details.get("reason_code", ""))
        if reason == "context_mismatch" or "conflicts" in exc.message:
            return ClientErrorCode.INVALID_CONTEXT
        return ClientErrorCode.VALIDATION_ERROR

    mapping = {
        ErrorCategory.UNAUTHENTICATED: ClientErrorCode.AUTHENTICATION_REQUIRED,
        ErrorCategory.UNAUTHORIZED: ClientErrorCode.AUTHORIZATION_DENIED,
        ErrorCategory.POLICY_DENIED: ClientErrorCode.AUTHORIZATION_DENIED,
        ErrorCategory.VALIDATION_ERROR: ClientErrorCode.VALIDATION_ERROR,
        ErrorCategory.UPSTREAM_ERROR: ClientErrorCode.UPSTREAM_FAILURE,
        ErrorCategory.UNAVAILABLE_DEPENDENCY: ClientErrorCode.UPSTREAM_FAILURE,
        ErrorCategory.TIMEOUT: ClientErrorCode.UPSTREAM_FAILURE,
        ErrorCategory.INTERNAL_ERROR: ClientErrorCode.INTERNAL_ERROR,
        ErrorCategory.NOT_FOUND: ClientErrorCode.VALIDATION_ERROR,
        ErrorCategory.RATE_LIMITED: ClientErrorCode.UPSTREAM_FAILURE,
    }
    return mapping.get(exc.category, ClientErrorCode.INTERNAL_ERROR)


_BLOCKED_DETAIL_KEYS = frozenset(
    {
        "token",
        "secret",
        "password",
        "credential",
        "authorization",
        "api_key",
        "apikey",
        "presented_secret",
        "auth_token",
    }
)


def _safe_details(exc: McpError) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in dict(exc.details or {}).items():
        key_l = str(key).lower().replace("-", "_")
        if any(b in key_l for b in _BLOCKED_DETAIL_KEYS):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[str(key)] = value
        else:
            out[str(key)] = type(value).__name__
    return out


def raise_as_mcp_tool_error(exc: McpError) -> None:
    """Re-raise as SDK ToolError so clients get isError + structured message.

    Uses ``from None`` so exception chaining does not leak causes to clients.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    payload = map_mcp_error(exc)
    raise ToolError(format_tool_error_message(payload)) from None
