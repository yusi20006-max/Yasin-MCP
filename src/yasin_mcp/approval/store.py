"""In-memory single-use approval store (Stage 11 test/provider boundary)."""

from __future__ import annotations

import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from yasin_mcp.approval.types import ApprovalGrant, ApprovalStatus, ApprovalValidationResult
from yasin_mcp.errors.errors import ValidationError


class InMemoryApprovalStore:
    """Issues opaque tokens; consumption is single-use and synchronized."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[ApprovalGrant, bool]] = {}

    def issue(
        self,
        *,
        tool_name: str,
        subject_id: str | None = None,
        request_id: str | None = None,
        project_id: str | None = None,
        ttl_seconds: int = 300,
        single_use: bool = True,
    ) -> str:
        if not tool_name or not tool_name.strip():
            raise ValidationError(
                "approval tool_name must be non-empty",
                details={"reason_code": "approval_tool_required"},
            )
        if ttl_seconds <= 0:
            raise ValidationError(
                "approval ttl_seconds must be positive",
                details={"reason_code": "approval_ttl_invalid"},
            )
        token = secrets.token_urlsafe(32)
        grant = ApprovalGrant(
            approval_id=secrets.token_hex(8),
            tool_name=tool_name.strip(),
            subject_id=subject_id,
            request_id=request_id,
            project_id=project_id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            single_use=single_use,
        )
        with self._lock:
            self._entries[token] = (grant, False)
        return token

    def validate_and_consume(
        self,
        token: str | None,
        *,
        tool_name: str,
        context: Any | None = None,
        subject_id: str | None = None,
    ) -> ApprovalValidationResult:
        if token is None or not str(token).strip():
            return ApprovalValidationResult(
                status=ApprovalStatus.MISSING,
                reason_code="approval_missing",
            )
        presented = str(token).strip()
        with self._lock:
            entry = self._entries.get(presented)
            if entry is None:
                return ApprovalValidationResult(
                    status=ApprovalStatus.INVALID,
                    reason_code="approval_unknown",
                )
            grant, consumed = entry
            if consumed and grant.single_use:
                return ApprovalValidationResult(
                    status=ApprovalStatus.REPLAYED,
                    grant=grant,
                    reason_code="approval_replayed",
                )
            if grant.is_expired():
                return ApprovalValidationResult(
                    status=ApprovalStatus.EXPIRED,
                    grant=grant,
                    reason_code="approval_expired",
                )
            if grant.tool_name != tool_name:
                return ApprovalValidationResult(
                    status=ApprovalStatus.MISMATCH,
                    grant=grant,
                    reason_code="approval_tool_mismatch",
                )
            expected_subject = subject_id
            if expected_subject is None and context is not None:
                expected_subject = getattr(context, "agent_id", None)
            if grant.subject_id is not None and expected_subject is not None:
                if grant.subject_id != expected_subject:
                    return ApprovalValidationResult(
                        status=ApprovalStatus.MISMATCH,
                        grant=grant,
                        reason_code="approval_subject_mismatch",
                    )
            if grant.request_id is not None:
                got = getattr(context, "request_id", None) if context else None
                if got != grant.request_id:
                    return ApprovalValidationResult(
                        status=ApprovalStatus.MISMATCH,
                        grant=grant,
                        reason_code="approval_request_mismatch",
                    )
            if grant.project_id is not None:
                got_p = getattr(context, "project_id", None) if context else None
                if got_p != grant.project_id:
                    return ApprovalValidationResult(
                        status=ApprovalStatus.MISMATCH,
                        grant=grant,
                        reason_code="approval_project_mismatch",
                    )
            if grant.single_use:
                self._entries[presented] = (grant, True)
            return ApprovalValidationResult(
                status=ApprovalStatus.GRANTED,
                grant=grant,
                reason_code="approval_granted",
            )
