import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from yasin_mcp.adapters.operations import (
    DEFAULT_GATEWAY_EXECUTABLE,
    OPERATION_DIAGNOSTICS,
    OPERATION_HEALTH_CHECK,
    OPERATION_LIST_SERVICES,
    OPERATION_SERVICE_STATUS,
    OperationsAdapter,
    _build_request,
)
from yasin_mcp.errors.errors import (
    InternalError,
    TimeoutMcpError,
    UnavailableDependencyError,
    ValidationError,
)
from yasin_mcp.version import EvidenceStatus


def _gateway_response(
    operation: str = "list_services",
    success: bool = True,
    status: str = "succeeded",
    data: dict | None = None,
    error: dict | None = None,
    service_available: bool = True,
) -> str:
    payload = {
        "schema_version": 1,
        "request_id": "abc-123",
        "operation_id": "op-1",
        "success": success,
        "status": status,
        "data": data or {},
        "error": error,
        "service_available": service_available,
    }
    return json.dumps(payload) + "\n"


def _mock_completed(stdout: str, returncode: int = 0):
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.stdout = stdout
    result.stderr = ""
    result.returncode = returncode
    return result


# -- Availability check (no subprocess spawned) -----------------------------


def test_available_true_when_executable_found():
    with patch(
        "yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/yasin-operations"
    ):
        adapter = OperationsAdapter()
        assert adapter.available is True


def test_available_false_when_executable_missing():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value=None):
        adapter = OperationsAdapter()
        assert adapter.available is False


def test_available_check_does_not_spawn_subprocess():
    with patch(
        "yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"
    ) as mock_which:
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            adapter = OperationsAdapter()
            _ = adapter.available
            mock_which.assert_called_once()
            mock_run.assert_not_called()


# -- Successful read-only calls ---------------------------------------------


def test_list_services_success():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(
                _gateway_response(data={"services": ["yasin-ai"]})
            )
            adapter = OperationsAdapter()
            result = adapter.list_services()

    assert result.success is True
    assert result.data == {"services": ["yasin-ai"]}
    assert result.evidence_status == EvidenceStatus.CONFIRMED


def test_service_status_success():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(_gateway_response(data={"state": "running"}))
            adapter = OperationsAdapter()
            result = adapter.service_status("yasin-ai")

    assert result.success is True
    assert result.data == {"state": "running"}


def test_service_status_rejects_empty_name():
    adapter = OperationsAdapter()
    with pytest.raises(ValidationError):
        adapter.service_status("")


def test_service_status_rejects_whitespace_only_name():
    adapter = OperationsAdapter()
    with pytest.raises(ValidationError):
        adapter.service_status("   ")


def test_health_success():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(_gateway_response(data={"healthy": True}))
            adapter = OperationsAdapter()
            result = adapter.health()

    assert result.success is True


def test_diagnostics_success():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(
                _gateway_response(data={"python_version": "3.12"})
            )
            adapter = OperationsAdapter()
            result = adapter.diagnostics()

    assert result.success is True


# -- Failure result from gateway (structured, not raised) -------------------


def test_gateway_reports_failure_result():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(
                _gateway_response(
                    success=False,
                    status="failed",
                    error={"category": "not_found", "message": "service not found"},
                )
            )
            adapter = OperationsAdapter()
            result = adapter.service_status("nonexistent")

    assert result.success is False
    assert result.error == {"category": "not_found", "message": "service not found"}


def test_gateway_service_unavailable_reflected_in_evidence_status():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(
                _gateway_response(success=False, service_available=False)
            )
            adapter = OperationsAdapter()
            result = adapter.health()

    assert result.evidence_status == EvidenceStatus.UNRESOLVED


# -- Availability / unavailable dependency ----------------------------------


def test_unavailable_when_executable_not_on_path():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value=None):
        adapter = OperationsAdapter()
        with pytest.raises(UnavailableDependencyError):
            adapter.list_services()


def test_unavailable_when_subprocess_raises_file_not_found():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch(
            "yasin_mcp.adapters.operations.subprocess.run",
            side_effect=FileNotFoundError("no such file"),
        ):
            adapter = OperationsAdapter()
            with pytest.raises(UnavailableDependencyError):
                adapter.list_services()


# -- Timeout ------------------------------------------------------------


def test_timeout_raises_timeout_mcp_error():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch(
            "yasin_mcp.adapters.operations.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="yasin-operations", timeout=15),
        ):
            adapter = OperationsAdapter()
            with pytest.raises(TimeoutMcpError):
                adapter.list_services()


# -- Malformed / oversized responses -----------------------------------


def test_malformed_json_response_raises_internal_error():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed("not valid json at all\n")
            adapter = OperationsAdapter()
            with pytest.raises(InternalError):
                adapter.list_services()


def test_non_object_json_response_raises_internal_error():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed('["not", "an", "object"]\n')
            adapter = OperationsAdapter()
            with pytest.raises(InternalError):
                adapter.list_services()


def test_empty_response_raises_internal_error():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed("")
            adapter = OperationsAdapter()
            with pytest.raises(InternalError):
                adapter.list_services()


def test_oversized_response_raises_internal_error():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            huge = _gateway_response(data={"padding": "x" * 2_000_000})
            mock_run.return_value = _mock_completed(huge)
            adapter = OperationsAdapter(max_response_bytes=1000)
            with pytest.raises(InternalError):
                adapter.list_services()


# -- Subprocess safety (no shell, fixed argv) --------------------------------


def test_subprocess_called_with_shell_false():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(_gateway_response())
            adapter = OperationsAdapter()
            adapter.list_services()

    assert mock_run.call_args.kwargs.get("shell") is False


def test_subprocess_called_with_fixed_list_argv():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(_gateway_response())
            adapter = OperationsAdapter()
            adapter.list_services()

    argv = mock_run.call_args.args[0]
    assert isinstance(argv, list)
    assert argv == [DEFAULT_GATEWAY_EXECUTABLE, "gateway"]


def test_subprocess_argv_never_contains_caller_input():
    """Even a service_name containing shell metacharacters must never
    appear in the subprocess argv -- it only ever goes into the
    JSON request body written to stdin."""
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(_gateway_response())
            adapter = OperationsAdapter()
            adapter.service_status("yasin-ai; rm -rf /")

    argv = mock_run.call_args.args[0]
    assert "rm" not in " ".join(argv)
    assert argv == [DEFAULT_GATEWAY_EXECUTABLE, "gateway"]


def test_request_sent_via_stdin_not_argv():
    with patch("yasin_mcp.adapters.operations.shutil.which", return_value="/usr/bin/x"):
        with patch("yasin_mcp.adapters.operations.subprocess.run") as mock_run:
            mock_run.return_value = _mock_completed(_gateway_response())
            adapter = OperationsAdapter()
            adapter.service_status("yasin-ai")

    sent_input = mock_run.call_args.kwargs.get("input")
    assert sent_input is not None
    parsed = json.loads(sent_input)
    assert parsed["request"]["target_identifier"] == "yasin-ai"


# -- Request construction: safety_class always hardcoded read_only ---------


def test_build_request_always_sets_read_only_safety_class():
    request = _build_request(OPERATION_LIST_SERVICES, "runtime", "local")
    assert request["request"]["safety_class"] == "read_only"


@pytest.mark.parametrize(
    "operation",
    [
        OPERATION_LIST_SERVICES,
        OPERATION_SERVICE_STATUS,
        OPERATION_HEALTH_CHECK,
        OPERATION_DIAGNOSTICS,
    ],
)
def test_build_request_allows_only_the_four_operations(operation):
    # Must not raise for any of the four permitted operations.
    _build_request(operation, "runtime", "local")


def test_build_request_rejects_any_other_operation():
    with pytest.raises(ValidationError):
        _build_request("service_start", "service", "yasin-ai")


def test_build_request_rejects_mutating_operation_name():
    for forbidden in ("service_stop", "service_restart", "deploy", "shell"):
        with pytest.raises(ValidationError):
            _build_request(forbidden, "service", "x")
