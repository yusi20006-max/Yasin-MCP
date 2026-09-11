"""Compatibility with Yasin-Core v3.4.0 shared ecosystem contracts.

Post-Core integration layer: dependency-free, read-model-only translators
that let Yasin-MCP emit payloads shaped exactly like the public Core SDK
contracts (``yasin_core.sdk``: ``HealthReport``, ``ServiceStatus``,
``ErrorInfo``) without importing ``yasin_core`` at all.

Design rules (hard):

- No ``yasin_core`` import anywhere in this package — Yasin-MCP stays
  independently installable/runnable (see ``tests/test_independence.py``).
  Compatibility is proven by tests that parse our dicts with the real
  Core SDK when it happens to be installed (test-only, skipped otherwise).
- Read models only. Nothing here starts, stops, or otherwise controls a
  service. Lifecycle ownership stays with YasinHub; Runit stays behind
  YasinHub. ``ControlResult`` verdicts are therefore intentionally *not*
  produced here — they belong to the Control Plane.
- Existing MCP behavior is unchanged. These helpers only *add* an export
  shape alongside the native ``HealthStatus`` / ``OperationsResult`` /
  ``McpError`` models; they never replace them.
- Never guess HEALTHY: only an explicit healthy token maps to
  ``HEALTHY`` (mirrors Core's ``HealthReport.is_healthy`` rule).

Reference: Yasin-Core v3.4.0, contract registry ``1.1.0``
(``yasin_core/sdk/contract_registry.json``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Final

from yasin_mcp.errors.errors import ErrorCategory, McpError

#: Core contract-registry version this module mirrors.
CORE_CONTRACT_VERSION: Final[str] = "1.1.0"

#: Minimum Core release providing the shared observation contracts.
CORE_MIN_VERSION: Final[str] = "3.4.0"

#: Declared compatibility range for the mirrored read models.
CORE_VERSION_COMPAT: Final[str] = ">=3.4.0"

#: Import boundary consumers must use; MCP never imports even this.
CORE_IMPORT_BOUNDARY: Final[str] = "yasin_core.sdk"

# ---------------------------------------------------------------------------
# Canonical value vocabularies (mirrors of the Core enums, kept as plain
# frozensets so this module has no dependency on Core).
# ---------------------------------------------------------------------------

CORE_HEALTH_STATES: Final[frozenset[str]] = frozenset(
    {"HEALTHY", "DEGRADED", "UNHEALTHY", "UNKNOWN"}
)

CORE_STATUS_VALUES: Final[frozenset[str]] = frozenset(
    {"RUNNING", "STOPPED", "FAILED", "UNKNOWN", "IDLE", "SUCCESS", "STALE"}
)

CORE_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {"UNKNOWN", "INVALID", "NOT_FOUND", "UNAVAILABLE", "TIMEOUT", "REFUSED", "CONFLICT"}
)

_HEALTHY_TOKENS: Final[frozenset[str]] = frozenset({"healthy", "ok", "up"})
_DEGRADED_TOKENS: Final[frozenset[str]] = frozenset({"degraded"})
_UNHEALTHY_TOKENS: Final[frozenset[str]] = frozenset(
    {"unhealthy", "failed", "failure", "error", "down"}
)

# MCP ErrorCategory -> Core ErrorCode (Core has no auth/rate-limit codes;
# refusal-like categories map to REFUSED, capacity contention to CONFLICT).
_ERROR_CODE_MAP: Final[Mapping[ErrorCategory, str]] = {
    ErrorCategory.VALIDATION_ERROR: "INVALID",
    ErrorCategory.NOT_FOUND: "NOT_FOUND",
    ErrorCategory.UNAUTHENTICATED: "REFUSED",
    ErrorCategory.UNAUTHORIZED: "REFUSED",
    ErrorCategory.POLICY_DENIED: "REFUSED",
    ErrorCategory.RATE_LIMITED: "CONFLICT",
    ErrorCategory.TIMEOUT: "TIMEOUT",
    ErrorCategory.UNAVAILABLE_DEPENDENCY: "UNAVAILABLE",
    ErrorCategory.UPSTREAM_ERROR: "UNAVAILABLE",
    ErrorCategory.INTERNAL_ERROR: "UNKNOWN",
}

_SECRET_PATTERN = re.compile(
    r"(token|secret|password|passwd|api[_-]?key|bearer|authorization)(\s*[:=]\s*)\S+",
    re.IGNORECASE,
)
_JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def redact_secrets_compatible(text: Any, limit: int = 500) -> str:
    """Best-effort secret redaction mirroring Core's ``redact_secrets``.

    Same pattern set and truncation semantics as
    ``yasin_core.sdk.redact_secrets`` so MCP-produced ``ErrorInfo.message``
    values carry the same hygiene. Never raises.
    """
    try:
        cleaned = _SECRET_PATTERN.sub(r"\1\2***", str(text))
        cleaned = _JWT_PATTERN.sub("***", cleaned)
        return cleaned[: max(1, int(limit))]
    except Exception:
        return "Unknown error."


def coerce_health_state_compatible(value: Any) -> str:
    """Map a free-form MCP health token to a Core ``HealthState`` value.

    Only explicit healthy/degraded/unhealthy tokens map to their verdict;
    anything else (including ``unresolved``/``unknown``/empty) becomes
    ``UNKNOWN`` — never guess.
    """
    token = str(value or "").strip().lower()
    if token in _HEALTHY_TOKENS:
        return "HEALTHY"
    if token in _DEGRADED_TOKENS:
        return "DEGRADED"
    if token in _UNHEALTHY_TOKENS:
        return "UNHEALTHY"
    return "UNKNOWN"


def coerce_status_value_compatible(value: Any) -> str:
    """Map a free-form status token to a Core ``ServiceStatusValue``.

    Case-insensitive passthrough for the seven canonical values;
    anything else becomes ``UNKNOWN``.
    """
    token = str(value or "").strip().upper()
    if token in CORE_STATUS_VALUES:
        return token
    return "UNKNOWN"


def coerce_error_code_compatible(category: ErrorCategory) -> str:
    """Map an MCP ``ErrorCategory`` to a Core ``ErrorCode`` value."""
    return _ERROR_CODE_MAP.get(category, "UNKNOWN")


def mcp_health_to_core_report(
    service: str,
    status: str,
    message: str = "",
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Core-shaped ``HealthReport`` dict from MCP health data.

    ``service`` must be non-empty; ``status`` is coerced with
    :func:`coerce_health_state_compatible` (never guesses HEALTHY).
    """
    name = str(service or "").strip()
    if not name:
        raise ValueError("service must be a non-empty string.")
    report = {
        "service": name,
        "state": coerce_health_state_compatible(status),
        "message": str(message or ""),
        "details": dict(details or {}),
    }
    validate_core_health_report(report)
    return report


def _coerce_pid(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def operations_result_to_core_status(
    name: str,
    status: str,
    running: bool = False,
    message: str = "",
    pid: int | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Core-shaped ``ServiceStatus`` snapshot from MCP observations.

    Accepts the scalar fields of an MCP ``OperationsResult`` (or Hub
    snapshot row) and returns the Core ``ServiceStatus.to_dict()`` shape.
    Non-positive/non-integer PIDs are dropped to ``None`` rather than
    failing, because PID ownership stays behind YasinHub/Runit and MCP
    must never fabricate process identity.
    """
    service_name = str(name or "").strip()
    if not service_name:
        raise ValueError("name must be a non-empty string.")
    snapshot = {
        "name": service_name,
        "status": coerce_status_value_compatible(status),
        "pid": _coerce_pid(pid),
        "running": bool(running),
        "message": str(message or ""),
        "extra": dict(extra or {}),
    }
    validate_core_service_status(snapshot)
    return snapshot


def mcp_error_to_core_info(
    exc: McpError,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Core-shaped ``ErrorInfo`` dict from an MCP error.

    The message is redacted at build (mirroring Core's ``ErrorInfo``
    constructor guarantee); secret-named detail keys are dropped.
    """
    code = coerce_error_code_compatible(exc.category)
    safe_details: dict[str, Any] = {}
    for key, value in dict(details if details is not None else exc.details or {}).items():
        key_l = str(key).lower().replace("-", "_")
        if any(
            part in key_l
            for part in (
                "token",
                "secret",
                "password",
                "credential",
                "authorization",
                "api_key",
                "apikey",
            )
        ):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe_details[str(key)] = value
        else:
            safe_details[str(key)] = type(value).__name__
    record = {
        "code": code,
        "message": redact_secrets_compatible(exc.message),
        "details": safe_details,
    }
    validate_core_error_info(record)
    return record


def validate_core_health_report(data: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` when a HealthReport-shaped dict is malformed."""
    if not isinstance(data, Mapping):
        raise ValueError("HealthReport snapshot must be a dict.")
    if not isinstance(data.get("service"), str) or not str(data.get("service")).strip():
        raise ValueError("HealthReport.service must be a non-empty string.")
    if str(data.get("state")) not in CORE_HEALTH_STATES:
        raise ValueError(f"HealthReport.state must be one of {sorted(CORE_HEALTH_STATES)}.")
    if not isinstance(data.get("message"), str):
        raise ValueError("HealthReport.message must be a string.")
    if not isinstance(data.get("details"), dict):
        raise ValueError("HealthReport.details must be a dict.")


def validate_core_service_status(data: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` when a ServiceStatus-shaped dict is malformed."""
    if not isinstance(data, Mapping):
        raise ValueError("ServiceStatus snapshot must be a dict.")
    if not isinstance(data.get("name"), str) or not str(data.get("name")).strip():
        raise ValueError("ServiceStatus.name must be a non-empty string.")
    if str(data.get("status")) not in CORE_STATUS_VALUES:
        raise ValueError(f"ServiceStatus.status must be one of {sorted(CORE_STATUS_VALUES)}.")
    pid = data.get("pid")
    if pid is not None and (isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0):
        raise ValueError("ServiceStatus.pid must be a positive integer PID or None.")
    if not isinstance(data.get("running"), bool):
        raise ValueError("ServiceStatus.running must be a bool.")
    if not isinstance(data.get("message"), str):
        raise ValueError("ServiceStatus.message must be a string.")
    if not isinstance(data.get("extra"), dict):
        raise ValueError("ServiceStatus.extra must be a dict.")


def validate_core_error_info(data: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` when an ErrorInfo-shaped dict is malformed."""
    if not isinstance(data, Mapping):
        raise ValueError("ErrorInfo record must be a dict.")
    if str(data.get("code")) not in CORE_ERROR_CODES:
        raise ValueError(f"ErrorInfo.code must be one of {sorted(CORE_ERROR_CODES)}.")
    if not isinstance(data.get("message"), str):
        raise ValueError("ErrorInfo.message must be a string.")
    if not isinstance(data.get("details"), dict):
        raise ValueError("ErrorInfo.details must be a dict.")


def core_contract_summary() -> dict[str, Any]:
    """Safe discovery metadata describing this Core-compatibility layer."""
    return {
        "core_contract_version": CORE_CONTRACT_VERSION,
        "core_min_version": CORE_MIN_VERSION,
        "core_version_compat": CORE_VERSION_COMPAT,
        "core_import_boundary": CORE_IMPORT_BOUNDARY,
        "scope": "observation_only",
        "lifecycle": "not_owned",
        "control_plane": "YasinHub",
        "shared_contracts": "Yasin-Core",
        "produces": ["HealthReport", "ServiceStatus", "ErrorInfo"],
        "explicitly_not_produced": ["ControlResult"],
        "control_result_owner": "YasinHub",
    }
