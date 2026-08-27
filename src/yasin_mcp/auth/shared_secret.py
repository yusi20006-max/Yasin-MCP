"""Optional shared-secret authenticator for process-local integration (Issue #89).

Verifies knowledge of a configured secret (SecretStr). Does NOT claim OS
peer identity. On success, produces TRUSTED AuthenticatedIdentity whose
subject_id comes from configuration — never from caller-supplied agent_id.
"""

from __future__ import annotations

import hmac
from typing import Final

from yasin_mcp.auth.types import AuthenticatedIdentity, AuthOutcome, AuthStatus
from yasin_mcp.config.config import SecretStr
from yasin_mcp.errors.errors import ValidationError

SCHEME: Final[str] = "shared_secret"


def authenticate_shared_secret(
    *,
    configured_secret: SecretStr | None,
    presented_secret: str | None,
    subject_id: str,
) -> AuthOutcome:
    """Compare presented secret to configured secret with constant-time compare."""
    if configured_secret is None or not configured_secret.get_secret_value():
        return AuthOutcome(
            status=AuthStatus.TRANSPORT_UNAVAILABLE,
            transport="stdio",
            reason_code="shared_secret_not_configured",
        )
    if presented_secret is None or presented_secret == "":
        return AuthOutcome(
            status=AuthStatus.MISSING_CREDENTIAL,
            transport="stdio",
            reason_code="credential_missing",
        )
    if not isinstance(presented_secret, str):
        return AuthOutcome(
            status=AuthStatus.MALFORMED,
            transport="stdio",
            reason_code="credential_malformed",
        )
    expected = configured_secret.get_secret_value()
    try:
        ok = hmac.compare_digest(presented_secret, expected)
    except (TypeError, ValueError):
        return AuthOutcome(
            status=AuthStatus.MALFORMED,
            transport="stdio",
            reason_code="credential_malformed",
        )
    if not ok:
        return AuthOutcome(
            status=AuthStatus.INVALID_CREDENTIAL,
            transport="stdio",
            reason_code="credential_invalid",
        )
    if not subject_id or not subject_id.strip():
        raise ValidationError("auth subject_id must be non-empty when secret is configured")
    identity = AuthenticatedIdentity(
        subject_id=subject_id.strip(),
        scheme=SCHEME,
        scopes=("mcp:invoke",),
    )
    return AuthOutcome(
        status=AuthStatus.AUTHENTICATED,
        identity=identity,
        transport="stdio",
        reason_code="shared_secret_ok",
    )
