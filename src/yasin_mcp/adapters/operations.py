"""Read-only adapter over the Yasin-Operations JSONL gateway.

Transport: launches `yasin-operations gateway` as a subprocess and
speaks the gateway's line-delimited JSON protocol over its
stdin/stdout. This adapter never imports the `yasin_operations`
package directly -- Yasin-MCP remains independently importable and
runnable whether or not Yasin-Operations is installed, on PATH, or
running.

Security boundary: this module never uses shell=True, os.system,
eval, or exec. The subprocess command is a fixed, hardcoded
argument list (`[executable, "gateway"]`) -- no caller-supplied
string is ever used to build a shell command. The four operations
this adapter can invoke (list_services, service_status,
health_check, diagnostics) are hardcoded Python constants, never
derived from caller input, so a caller cannot request any other
operation -- including a mutating one -- through this adapter.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from yasin_mcp.errors.errors import (
    InternalError,
    TimeoutMcpError,
    UnavailableDependencyError,
    ValidationError,
)
from yasin_mcp.version import EvidenceStatus

# Fixed, non-configurable set of operations this adapter will ever
# request. This is the enforcement point that prevents a caller from
# reaching any operation other than these four -- there is no code
# path in this module that accepts an operation name as a parameter.
OPERATION_LIST_SERVICES = "list_services"
OPERATION_SERVICE_STATUS = "service_status"
OPERATION_HEALTH_CHECK = "health_check"
OPERATION_DIAGNOSTICS = "diagnostics"

_ALLOWED_OPERATIONS = frozenset(
    {
        OPERATION_LIST_SERVICES,
        OPERATION_SERVICE_STATUS,
        OPERATION_HEALTH_CHECK,
        OPERATION_DIAGNOSTICS,
    }
)

# Every request this adapter sends declares safety_class itself --
# it is never accepted from a caller. See operations.py's tool layer
# for the corresponding guarantee that MCP tool inputs cannot supply
# an operation name or safety_class either.
_SAFETY_CLASS_READ_ONLY = "read_only"

DEFAULT_GATEWAY_EXECUTABLE = "yasin-operations"
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_RESPONSE_BYTES = 1_000_000
_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class OperationsResult:
    """A single successful or failed Operations gateway response."""

    operation: str
    success: bool
    status: str
    data: Mapping[str, Any]
    error: Mapping[str, Any] | None
    evidence_status: EvidenceStatus
    source: str


def _executable_available(executable: str) -> bool:
    return shutil.which(executable) is not None


def _build_request(operation: str, target_kind: str, target_identifier: str) -> dict[str, Any]:
    if operation not in _ALLOWED_OPERATIONS:
        # Defensive: this function is only ever called by this
        # module's own hardcoded call sites below, never with a
        # caller-supplied operation, so this branch should be
        # unreachable in practice -- but it must fail closed if it
        # is ever reached.
        raise ValidationError(
            f"operation {operation!r} is not permitted through the Operations adapter",
            details={"operation": operation},
        )
    return {
        "schema_version": _SCHEMA_VERSION,
        "request": {
            "operation": operation,
            "target_kind": target_kind,
            "target_identifier": target_identifier,
            "safety_class": _SAFETY_CLASS_READ_ONLY,
            "parameters": {},
            "actor": "yasin-mcp",
            "source": "yasin-mcp",
            "request_id": str(uuid.uuid4()),
        },
    }


class OperationsAdapter:
    """Read-only client for the Yasin-Operations JSONL gateway.

    Each call spawns a fresh gateway subprocess, writes exactly one
    request line, reads exactly one response line, and terminates
    the subprocess. This keeps the adapter simple and avoids holding
    a long-lived subprocess whose lifecycle would need separate
    health management; the cost is one process spawn per call, which
    is acceptable for a diagnostics/inspection interface.
    """

    def __init__(
        self,
        executable: str = DEFAULT_GATEWAY_EXECUTABLE,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    @property
    def available(self) -> bool:
        """Whether the gateway executable can be found on PATH.

        This is a cheap, non-blocking check (no subprocess is
        spawned) used by capability registration to decide whether
        to advertise the Operations tools at all.
        """
        return _executable_available(self.executable)

    def _invoke(self, operation: str, target_kind: str, target_identifier: str) -> OperationsResult:
        if not self.available:
            raise UnavailableDependencyError(
                "Yasin-Operations gateway executable is not available on PATH",
                details={"executable": self.executable},
            )

        request = _build_request(operation, target_kind, target_identifier)
        line = json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n"

        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, no user-controlled command
                [self.executable, "gateway"],
                input=line,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise UnavailableDependencyError(
                "Yasin-Operations gateway executable could not be started",
                details={"executable": self.executable},
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise TimeoutMcpError(
                f"Yasin-Operations gateway did not respond within {self.timeout_seconds}s",
                details={"operation": operation},
            ) from exc

        stdout = completed.stdout or ""
        if len(stdout.encode("utf-8")) > self.max_response_bytes:
            raise InternalError(
                "Yasin-Operations gateway response exceeded the maximum allowed size",
                details={"max_response_bytes": self.max_response_bytes},
            )

        response_line = stdout.strip().splitlines()[0] if stdout.strip() else ""
        if not response_line:
            raise InternalError(
                "Yasin-Operations gateway produced no response",
                details={"operation": operation, "returncode": completed.returncode},
            )

        try:
            payload = json.loads(response_line)
        except json.JSONDecodeError as exc:
            raise InternalError(
                "Yasin-Operations gateway returned a malformed response",
                details={"operation": operation},
            ) from exc

        if not isinstance(payload, Mapping):
            raise InternalError(
                "Yasin-Operations gateway response envelope must be a JSON object",
                details={"operation": operation},
            )

        success = bool(payload.get("success", False))
        status = str(payload.get("status", "unknown"))
        raw_data = payload.get("data")
        data: Mapping[str, Any] = raw_data if isinstance(raw_data, Mapping) else {}
        raw_error = payload.get("error")
        error: Mapping[str, Any] | None = raw_error if isinstance(raw_error, Mapping) else None
        service_available = payload.get("service_available", True)

        return OperationsResult(
            operation=operation,
            success=success,
            status=status,
            data=data,
            error=error,
            evidence_status=(
                EvidenceStatus.CONFIRMED if service_available else EvidenceStatus.UNRESOLVED
            ),
            source=f"yasin-operations gateway ({self.executable})",
        )

    def list_services(self) -> OperationsResult:
        return self._invoke(
            OPERATION_LIST_SERVICES, target_kind="runtime", target_identifier="local"
        )

    def service_status(self, service_name: str) -> OperationsResult:
        if not service_name or not service_name.strip():
            raise ValidationError("service_name must not be empty")
        return self._invoke(
            OPERATION_SERVICE_STATUS, target_kind="service", target_identifier=service_name.strip()
        )

    def health(self) -> OperationsResult:
        return self._invoke(OPERATION_HEALTH_CHECK, target_kind="self", target_identifier="runtime")

    def diagnostics(self) -> OperationsResult:
        return self._invoke(OPERATION_DIAGNOSTICS, target_kind="runtime", target_identifier="local")
