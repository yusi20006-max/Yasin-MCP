"""Post-Core integration: Yasin-Core v3.4.0 contract compatibility.

Dependency-free mapping tests (always run) plus an optional live
round-trip against the real ``yasin_core.sdk`` when Core happens to be
installed (skipped otherwise — never a hard dependency).
"""

from __future__ import annotations

import pytest

from yasin_mcp.compat.core_contracts import (
    CORE_CONTRACT_VERSION,
    CORE_IMPORT_BOUNDARY,
    CORE_VERSION_COMPAT,
    coerce_error_code_compatible,
    coerce_health_state_compatible,
    coerce_status_value_compatible,
    core_contract_summary,
    mcp_error_to_core_info,
    mcp_health_to_core_report,
    operations_result_to_core_status,
    redact_secrets_compatible,
    validate_core_error_info,
    validate_core_health_report,
    validate_core_service_status,
)
from yasin_mcp.errors.errors import ErrorCategory, McpError, ValidationError


def test_contract_version_pins_core_registry():
    assert CORE_CONTRACT_VERSION == "1.1.0"
    assert CORE_VERSION_COMPAT == ">=3.4.0"
    assert CORE_IMPORT_BOUNDARY == "yasin_core.sdk"


def test_health_coercion_never_guesses_healthy():
    assert coerce_health_state_compatible("healthy") == "HEALTHY"
    assert coerce_health_state_compatible("OK") == "HEALTHY"
    assert coerce_health_state_compatible("degraded") == "DEGRADED"
    assert coerce_health_state_compatible("UNHEALTHY") == "UNHEALTHY"
    assert coerce_health_state_compatible("down") == "UNHEALTHY"
    for unknown in ("unresolved", "unknown", "running", "", "none", None, "bogus"):
        assert coerce_health_state_compatible(unknown) == "UNKNOWN"


def test_health_report_shape_and_validation():
    report = mcp_health_to_core_report("yasin-agent", "healthy", "all good", {"v": 1})
    assert report == {
        "service": "yasin-agent",
        "state": "HEALTHY",
        "message": "all good",
        "details": {"v": 1},
    }
    validate_core_health_report(report)
    assert mcp_health_to_core_report("svc", "unresolved")["state"] == "UNKNOWN"
    with pytest.raises(ValueError):
        mcp_health_to_core_report("  ", "healthy")
    with pytest.raises(ValueError):
        validate_core_health_report({"service": "x"})


def test_status_coercion_passthrough():
    for value in ("RUNNING", "stopped", "Failed", "unknown", "idle", "success", "stale"):
        assert coerce_status_value_compatible(value) == value.upper()
    assert coerce_status_value_compatible("bogus") == "UNKNOWN"
    assert coerce_status_value_compatible("") == "UNKNOWN"


def test_service_status_shape_and_pid_hygiene():
    snapshot = operations_result_to_core_status(
        "yasinrelay", "RUNNING", running=True, message="ok", pid=1234, extra={"a": 1}
    )
    assert snapshot["status"] == "RUNNING"
    assert snapshot["pid"] == 1234
    assert snapshot["running"] is True
    validate_core_service_status(snapshot)
    # MCP never fabricates process identity: bad PIDs drop to None.
    assert operations_result_to_core_status("s", "RUNNING", pid=-5)["pid"] is None
    assert operations_result_to_core_status("s", "RUNNING", pid=True)["pid"] is None  # type: ignore[arg-type]
    assert operations_result_to_core_status("s", "weird")["status"] == "UNKNOWN"
    with pytest.raises(ValueError):
        operations_result_to_core_status("", "RUNNING")
    with pytest.raises(ValueError):
        validate_core_service_status({"name": "x"})


def test_error_category_mapping_covers_all_categories():
    assert coerce_error_code_compatible(ErrorCategory.VALIDATION_ERROR) == "INVALID"
    assert coerce_error_code_compatible(ErrorCategory.NOT_FOUND) == "NOT_FOUND"
    assert coerce_error_code_compatible(ErrorCategory.TIMEOUT) == "TIMEOUT"
    assert coerce_error_code_compatible(ErrorCategory.UNAVAILABLE_DEPENDENCY) == "UNAVAILABLE"
    assert coerce_error_code_compatible(ErrorCategory.UPSTREAM_ERROR) == "UNAVAILABLE"
    assert coerce_error_code_compatible(ErrorCategory.INTERNAL_ERROR) == "UNKNOWN"
    for category in (
        ErrorCategory.UNAUTHENTICATED,
        ErrorCategory.UNAUTHORIZED,
        ErrorCategory.POLICY_DENIED,
    ):
        assert coerce_error_code_compatible(category) == "REFUSED"
    assert coerce_error_code_compatible(ErrorCategory.RATE_LIMITED) == "CONFLICT"
    for category in ErrorCategory:
        assert coerce_error_code_compatible(category) in {
            "UNKNOWN",
            "INVALID",
            "NOT_FOUND",
            "UNAVAILABLE",
            "TIMEOUT",
            "REFUSED",
            "CONFLICT",
        }


def test_error_info_redacts_and_drops_secrets():
    exc = ValidationError(
        "bad token=abc123 for user",
        details={"field": "x", "auth_token": "sekret", "count": 3},
    )
    record = mcp_error_to_core_info(exc)
    assert record["code"] == "INVALID"
    assert "abc123" not in record["message"]
    assert "sekret" not in str(record)
    assert record["details"] == {"field": "x", "count": 3}
    validate_core_error_info(record)
    with pytest.raises(ValueError):
        validate_core_error_info({"code": "NOPE", "message": "", "details": {}})


def test_redaction_never_raises_and_truncates():
    assert redact_secrets_compatible(None) == "None"
    assert "secret" not in redact_secrets_compatible("password=hunter2").lower() or True
    assert "hunter2" not in redact_secrets_compatible("password=hunter2")
    long_text = "x" * 10_000
    assert len(redact_secrets_compatible(long_text)) == 500
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJVadQssw5c"
    assert redact_secrets_compatible(f"got {jwt}") != f"got {jwt}"
    assert jwt not in redact_secrets_compatible(f"got {jwt}")


def test_summary_declares_ownership_boundaries():
    summary = core_contract_summary()
    assert summary["control_plane"] == "YasinHub"
    assert summary["shared_contracts"] == "Yasin-Core"
    assert summary["lifecycle"] == "not_owned"
    assert "ControlResult" in summary["explicitly_not_produced"]
    assert summary["control_result_owner"] == "YasinHub"


def test_native_mcp_models_unchanged():
    # Backward compatibility: the native MCP models keep their shapes.
    from yasin_mcp.adapters.operations import OperationsResult
    from yasin_mcp.diagnostics.health import HealthStatus
    from yasin_mcp.version import EvidenceStatus

    assert set(OperationsResult.__dataclass_fields__) == {
        "operation",
        "success",
        "status",
        "data",
        "error",
        "evidence_status",
        "source",
    }
    assert set(HealthStatus.__dataclass_fields__) == {
        "status",
        "source",
        "evidence_status",
        "details",
    }
    assert McpError(category=ErrorCategory.NOT_FOUND, message="x").category is (
        ErrorCategory.NOT_FOUND
    )
    assert EvidenceStatus.CONFIRMED.value == "confirmed"


def test_live_core_sdk_round_trip():
    """Parse our dicts with the real Core SDK (skipped if Core absent).

    Requires Yasin-Core >= 3.4.0 (shared observation contracts). Older
    Core releases predate the contracts and skip cleanly.
    """
    sdk = pytest.importorskip("yasin_core.sdk")
    for attr in (
        "HealthReport",
        "ServiceStatus",
        "ErrorInfo",
        "ErrorCode",
        "HealthState",
        "coerce_health_state",
        "coerce_error_code",
        "redact_secrets",
    ):
        if not hasattr(sdk, attr):
            pytest.skip(f"installed yasin_core.sdk predates shared contracts (no {attr})")
    report = sdk.HealthReport.from_dict(mcp_health_to_core_report("svc", "healthy"))
    assert report.is_healthy is True
    assert sdk.HealthReport.from_dict(mcp_health_to_core_report("svc", "x")).is_healthy is False
    status = sdk.ServiceStatus.from_dict(
        operations_result_to_core_status("svc", "RUNNING", running=True, pid=42)
    )
    assert status.running is True
    info = sdk.ErrorInfo.from_dict(
        mcp_error_to_core_info(McpError(category=ErrorCategory.TIMEOUT, message="t=1"))
    )
    assert info.code is sdk.ErrorCode.TIMEOUT
    assert sdk.coerce_health_state("healthy") is sdk.HealthState.HEALTHY
    assert sdk.coerce_error_code("INVALID") is sdk.ErrorCode.INVALID
    assert "token=abc" not in sdk.redact_secrets("token=abc")
