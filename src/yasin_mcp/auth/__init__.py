"""Authentication and trusted-identity boundary (Stage 7.1 / Stage 8)."""

from yasin_mcp.auth.binding import BoundRequestContext, bind_context
from yasin_mcp.auth.enforcement import extract_presented_secret, resolve_execution_auth
from yasin_mcp.auth.pipeline import resolve_authentication
from yasin_mcp.auth.request_state import AUTH_TOKEN_KWARG, auth_request_scope
from yasin_mcp.auth.shared_secret import authenticate_shared_secret
from yasin_mcp.auth.stdio import authenticate_stdio_peer
from yasin_mcp.auth.types import (
    AUTH_CONTRACT_VERSION,
    AuthenticatedIdentity,
    AuthOutcome,
    AuthStatus,
)


def authentication_boundary_summary() -> dict[str, object]:
    """Safe discovery metadata — no secrets."""
    return {
        "auth_contract_version": AUTH_CONTRACT_VERSION,
        "stdio_peer_identity": "unresolved",
        "trusted_via_stdio_peer": False,
        "optional_shared_secret": True,
        "caller_cannot_set_trusted": True,
        "enforcement_on_tools_call": True,
        "auth_before_governance": True,
        "evidence_status": "confirmed",
    }


__all__ = [
    "AUTH_CONTRACT_VERSION",
    "AUTH_TOKEN_KWARG",
    "AuthOutcome",
    "AuthStatus",
    "AuthenticatedIdentity",
    "BoundRequestContext",
    "authenticate_shared_secret",
    "authenticate_stdio_peer",
    "authentication_boundary_summary",
    "auth_request_scope",
    "bind_context",
    "extract_presented_secret",
    "resolve_authentication",
    "resolve_execution_auth",
]
