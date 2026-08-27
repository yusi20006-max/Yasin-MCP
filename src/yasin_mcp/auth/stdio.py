"""Stdio transport authentication boundary (Issue #89).

What stdio provides (CONFIRMED):
- local process pipe / OS process boundary
- MCP protocol channel

What stdio does NOT provide (CONFIRMED):
- authenticated remote peer identity
- proof that client_id/agent_id claims are true
- authorization

Therefore peer identity claims over stdio remain ASSERTED / UNRESOLVED
unless a separate authenticator (e.g. shared-secret) verifies a credential.
"""

from __future__ import annotations

from yasin_mcp.auth.types import AuthOutcome, AuthStatus


def authenticate_stdio_peer() -> AuthOutcome:
    """Evaluate stdio peer identity.

    Always returns TRANSPORT_UNAVAILABLE for *trusted peer identity*.
    This is intentional — do not invent a fake peer principal.
    """
    return AuthOutcome(
        status=AuthStatus.TRANSPORT_UNAVAILABLE,
        identity=None,
        transport="stdio",
        reason_code="stdio_peer_identity_unavailable",
    )
