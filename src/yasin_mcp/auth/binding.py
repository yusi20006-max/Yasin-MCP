"""Bind ASSERTED IntegrationContext to optional TRUSTED identity (Issue #89).

Conflict between authenticated subject and asserted agent_id/client_id
fails closed — never silently prefer the asserted claim.
"""

from __future__ import annotations

from dataclasses import dataclass

from yasin_mcp.auth.types import AuthenticatedIdentity, AuthOutcome, AuthStatus
from yasin_mcp.contracts.integration_context import IntegrationContext, TrustClassification
from yasin_mcp.errors.errors import UnauthenticatedError, ValidationError
from yasin_mcp.governance.types import GovernanceContext


@dataclass(frozen=True)
class BoundRequestContext:
    """Request-scoped context after auth + binding."""

    asserted: IntegrationContext
    auth: AuthOutcome
    governance: GovernanceContext

    @property
    def trust(self) -> TrustClassification:
        if self.auth.is_authenticated:
            return TrustClassification.TRUSTED
        return TrustClassification.ASSERTED


def bind_context(
    asserted: IntegrationContext,
    auth: AuthOutcome,
    *,
    require_authentication: bool = False,
) -> BoundRequestContext:
    """Produce governance context; fail closed on mismatch or required auth failure."""
    if require_authentication and not auth.is_authenticated:
        raise UnauthenticatedError(
            "authentication required but not established",
            details={
                "status": auth.status.value,
                "reason_code": auth.reason_code,
                "transport": auth.transport,
            },
        )

    if auth.status is AuthStatus.CONTEXT_MISMATCH:
        raise ValidationError(
            "authentication context mismatch",
            details={"reason_code": auth.reason_code},
        )

    identity = auth.identity
    if identity is not None:
        _enforce_no_impersonation(asserted, identity)

    gov = asserted.to_governance_context()
    extra = dict(gov.extra)
    extra["auth_status"] = auth.status.value
    if identity is not None:
        extra["auth_subject_id"] = identity.subject_id
        extra["auth_scheme"] = identity.scheme
        extra["auth_trust"] = identity.trust.value
    else:
        extra["auth_trust"] = TrustClassification.ASSERTED.value
    gov = GovernanceContext(
        client_id=gov.client_id,
        agent_id=gov.agent_id,
        project_id=gov.project_id,
        workspace_id=gov.workspace_id,
        task_id=gov.task_id,
        session_id=gov.session_id,
        request_id=gov.request_id,
        correlation_id=gov.correlation_id,
        extra=extra,
    )
    return BoundRequestContext(asserted=asserted, auth=auth, governance=gov)


def _enforce_no_impersonation(
    asserted: IntegrationContext,
    identity: AuthenticatedIdentity,
) -> None:
    """If asserted agent/client conflicts with verified subject, fail closed."""
    for field_name, value in (
        ("agent_id", asserted.agent_id),
        ("client_id", asserted.client_id),
    ):
        if value is not None and value != identity.subject_id:
            raise ValidationError(
                f"asserted {field_name} conflicts with authenticated subject",
                details={
                    "field": field_name,
                    "reason_code": AuthStatus.CONTEXT_MISMATCH.value,
                    "asserted": value,
                    "subject_id": identity.subject_id,
                },
            )
