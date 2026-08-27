"""Request authentication pipeline for Stage 7.1 (Issue #89).

Order:
1. Evaluate stdio peer identity (always TRANSPORT_UNAVAILABLE for trusted peer).
2. Optionally verify shared-secret credential if configured / presented.
3. Bind asserted IntegrationContext to AuthOutcome (fail closed on mismatch).
"""

from __future__ import annotations

from yasin_mcp.auth.binding import BoundRequestContext, bind_context
from yasin_mcp.auth.shared_secret import authenticate_shared_secret
from yasin_mcp.auth.stdio import authenticate_stdio_peer
from yasin_mcp.auth.types import AuthOutcome, AuthStatus
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.contracts.integration_context import IntegrationContext


def resolve_authentication(
    *,
    config: ServerConfig,
    asserted: IntegrationContext | None = None,
    presented_secret: str | None = None,
) -> BoundRequestContext:
    """Authenticate and bind context for one request.

    ``presented_secret`` is never stored on IntegrationContext (sensitive keys
    are rejected there). Callers pass it only to this function.
    """
    asserted = asserted or IntegrationContext()

    peer = authenticate_stdio_peer()
    assert peer.status is AuthStatus.TRANSPORT_UNAVAILABLE

    secret_outcome = authenticate_shared_secret(
        configured_secret=config.auth_token,
        presented_secret=presented_secret,
        subject_id=config.auth_subject_id,
    )

    auth: AuthOutcome
    if secret_outcome.status is AuthStatus.AUTHENTICATED:
        auth = secret_outcome
    elif presented_secret is not None and presented_secret != "":
        auth = secret_outcome
    elif config.require_authentication:
        if secret_outcome.status is AuthStatus.TRANSPORT_UNAVAILABLE:
            auth = AuthOutcome(
                status=AuthStatus.MISSING_CREDENTIAL,
                transport="stdio",
                reason_code="auth_required_no_credential",
            )
        else:
            auth = secret_outcome
    else:
        auth = AuthOutcome(
            status=AuthStatus.UNAUTHENTICATED,
            transport="stdio",
            reason_code="stdio_unauthenticated_asserted_context",
        )

    return bind_context(
        asserted,
        auth,
        require_authentication=config.require_authentication,
    )
