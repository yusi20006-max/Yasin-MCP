"""Normalized read-only health and diagnostics boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from yasin_mcp.capabilities.registry import CapabilityRegistry, discover_capabilities
from yasin_mcp.errors.errors import McpError, UnavailableDependencyError
from yasin_mcp.version import EvidenceStatus


class OperationsReader(Protocol):
    """Public read-only contract expected from an optional operations adapter."""

    def health(self) -> Mapping[str, Any]: ...

    def diagnostics(self) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class HealthStatus:
    status: str
    source: str
    evidence_status: EvidenceStatus
    details: Mapping[str, Any]


@dataclass(frozen=True)
class DiagnosticsSnapshot:
    health: HealthStatus
    diagnostics: Mapping[str, Any]
    capabilities: dict[str, object]


class DiagnosticsAdapter:
    """Expose health/diagnostics without becoming an operations control plane."""

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        operations: OperationsReader | None = None,
        project_health: Callable[[], Mapping[str, Any]] | None = None,
    ) -> None:
        self._registry = registry
        self._operations = operations
        self._project_health = project_health

    def get_capabilities(self) -> dict[str, object]:
        """Return the same deterministic capability discovery contract used by runtime."""
        return discover_capabilities(self._registry).as_dict()

    def get_health(self) -> HealthStatus:
        if self._project_health is not None:
            try:
                payload = dict(self._project_health())
                return HealthStatus(
                    status=str(payload.get("status", "unknown")),
                    source="project-public-contract",
                    evidence_status=EvidenceStatus.CONFIRMED,
                    details=payload,
                )
            except McpError:
                raise
            except Exception as exc:
                raise UnavailableDependencyError("project health source is unavailable") from exc
        if self._operations is not None:
            try:
                payload = dict(self._operations.health())
                return HealthStatus(
                    status=str(payload.get("status", "unknown")),
                    source="yasin-operations-public-contract",
                    evidence_status=EvidenceStatus.CONFIRMED,
                    details=payload,
                )
            except McpError:
                raise
            except Exception as exc:
                raise UnavailableDependencyError("Yasin-Operations health source is unavailable") from exc
        return HealthStatus(
            status="unresolved",
            source="none",
            evidence_status=EvidenceStatus.UNRESOLVED,
            details={"reason": "no approved health source is configured"},
        )

    def get_diagnostics(self) -> DiagnosticsSnapshot:
        health = self.get_health()
        if self._operations is None:
            diagnostics: Mapping[str, Any] = {
                "status": "unresolved",
                "reason": "Yasin-Operations adapter is optional and unavailable",
            }
        else:
            try:
                diagnostics = dict(self._operations.diagnostics())
            except McpError:
                raise
            except Exception as exc:
                raise UnavailableDependencyError(
                    "Yasin-Operations diagnostics source is unavailable"
                ) from exc
        return DiagnosticsSnapshot(
            health=health,
            diagnostics=diagnostics,
            capabilities=self.get_capabilities(),
        )
