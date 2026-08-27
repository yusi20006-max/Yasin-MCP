"""Stage 9 / Issue #92 — credential presentation abstraction.

Separates how a credential is *acquired* from authentication itself.
Stdio does not authenticate remote peers; credentials prove knowledge of
a configured shared secret only when presented per request.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from yasin_mcp.auth.request_state import AUTH_TOKEN_KWARG, get_presented_secret

STDIO_CREDENTIAL_KWARG: Final[str] = AUTH_TOKEN_KWARG
CREDENTIAL_TRANSPORT: Final[str] = "stdio_request_kwarg"


@dataclass(frozen=True)
class PresentedCredential:
    """Request-scoped credential material — never log or audit the value."""

    value: str | None
    source: str  # "kwarg" | "contextvar" | "none"

    def __repr__(self) -> str:
        return f"PresentedCredential(source={self.source!r}, value={'***' if self.value else None})"

    def __str__(self) -> str:
        return "PresentedCredential(***)"


def extract_credential(kwargs: dict[str, Any]) -> tuple[dict[str, Any], PresentedCredential]:
    """Strip credential from tool kwargs; prefer kwarg then contextvar."""
    cleaned = dict(kwargs)
    raw = cleaned.pop(STDIO_CREDENTIAL_KWARG, None)
    source = "none"
    value: str | None = None
    if raw is not None:
        value = raw if isinstance(raw, str) else str(raw)
        source = "kwarg"
    else:
        ctx_val = get_presented_secret()
        if ctx_val is not None:
            value = ctx_val
            source = "contextvar"
    return cleaned, PresentedCredential(value=value, source=source)


def credential_transport_summary() -> dict[str, object]:
    return {
        "transport": CREDENTIAL_TRANSPORT,
        "stdio_kwarg": STDIO_CREDENTIAL_KWARG,
        "remote_peer_authenticated": False,
        "credential_reaches_tool_body": False,
        "evidence_status": "confirmed",
    }
