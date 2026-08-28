"""Stage 11 / Issue #97 — typed approval contract (server-issued only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    GRANTED = "granted"
    MISSING = "missing"
    INVALID = "invalid"
    EXPIRED = "expired"
    REPLAYED = "replayed"
    MISMATCH = "mismatch"


@dataclass(frozen=True)
class ApprovalGrant:
    """Server-owned approval grant metadata (never includes secret material)."""

    approval_id: str
    tool_name: str
    subject_id: str | None
    request_id: str | None
    project_id: str | None
    expires_at: datetime
    single_use: bool = True

    def is_expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return current >= exp

    def as_audit_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "tool_name": self.tool_name,
            "subject_id": self.subject_id,
            "request_id": self.request_id,
            "project_id": self.project_id,
            "expires_at": self.expires_at.isoformat(),
            "single_use": self.single_use,
        }


@dataclass(frozen=True)
class ApprovalValidationResult:
    status: ApprovalStatus
    grant: ApprovalGrant | None = None
    reason_code: str = ""
