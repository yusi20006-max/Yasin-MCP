"""Structured governance audit events with centralized sanitization."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from yasin_mcp.audit.logging_setup import redact
from yasin_mcp.governance.types import (
    GovernanceDecision,
    RiskLevel,
)

_logger = logging.getLogger("yasin_mcp.governance.audit")


class AuditEventType(str, Enum):
    REQUEST = "request"
    DECISION = "decision"
    EXECUTION_RESULT = "execution_result"
    EXECUTION_FAILURE = "execution_failure"


@dataclass(frozen=True)
class AuditEvent:
    event_type: AuditEventType
    tool_name: str
    risk: RiskLevel | None
    decision: GovernanceDecision | None
    success: bool | None = None
    message: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_type": self.event_type.value,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
        }
        if self.risk is not None:
            payload["risk"] = self.risk.value
        if self.decision is not None:
            payload["decision"] = self.decision.value
        if self.success is not None:
            payload["success"] = self.success
        if self.message is not None:
            payload["message"] = self.message
        if self.context:
            payload["context"] = dict(self.context)
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload


def sanitize_audit_payload(value: Any) -> Any:
    return redact(value)


class AuditRecorder(Protocol):
    def record(self, event: AuditEvent) -> None: ...


class LoggingAuditRecorder:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or _logger

    def record(self, event: AuditEvent) -> None:
        safe = sanitize_audit_payload(event.as_dict())
        self._logger.info(
            "governance_audit",
            extra={"fields": safe if isinstance(safe, dict) else {"payload": safe}},
        )


class InMemoryAuditRecorder:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(
            AuditEvent(
                event_type=event.event_type,
                tool_name=event.tool_name,
                risk=event.risk,
                decision=event.decision,
                success=event.success,
                message=event.message,
                context=sanitize_audit_payload(event.context)
                if isinstance(event.context, dict)
                else {},
                timestamp=event.timestamp,
                extra=sanitize_audit_payload(event.extra) if isinstance(event.extra, dict) else {},
            )
        )

    def clear(self) -> None:
        self.events.clear()

    def of_type(self, event_type: AuditEventType) -> list[AuditEvent]:
        return [e for e in self.events if e.event_type is event_type]
