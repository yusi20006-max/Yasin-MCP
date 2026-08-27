"""Stage 7.1 / Issue #89 — authentication result and verified identity types.

TRUSTED identity is never constructed from caller-supplied IntegrationContext.
Only authenticators in this package may produce AuthenticatedIdentity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from yasin_mcp.contracts.integration_context import TrustClassification
from yasin_mcp.errors.errors import ValidationError

AUTH_CONTRACT_VERSION: Final[str] = "1.0.0"


class AuthStatus(str, Enum):
    """Outcome of an authentication attempt (not authorization)."""

    AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"
    INVALID_CREDENTIAL = "invalid_credential"
    MISSING_CREDENTIAL = "missing_credential"
    CONTEXT_MISMATCH = "context_mismatch"
    UNKNOWN_SCHEME = "unknown_scheme"
    MALFORMED = "malformed"
    TRANSPORT_UNAVAILABLE = "transport_unavailable"


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """Identity verified by an authenticator — TRUSTED only.

    Do not construct this from client JSON. Use authenticator APIs.
    """

    subject_id: str
    scheme: str
    trust: TrustClassification = TrustClassification.TRUSTED
    scopes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_id or not self.subject_id.strip():
            raise ValidationError("AuthenticatedIdentity.subject_id must not be empty")
        if self.trust is not TrustClassification.TRUSTED:
            raise ValidationError(
                "AuthenticatedIdentity.trust must be TRUSTED",
                details={"trust": self.trust.value},
            )
        if not self.scheme or not self.scheme.strip():
            raise ValidationError("AuthenticatedIdentity.scheme must not be empty")

    def as_dict(self) -> dict[str, Any]:
        """Safe metadata for audit (no credentials)."""
        return {
            "subject_id": self.subject_id,
            "scheme": self.scheme,
            "trust": self.trust.value,
            "scopes": list(self.scopes),
        }


@dataclass(frozen=True)
class AuthOutcome:
    """Result of authentication for one request/session."""

    status: AuthStatus
    identity: AuthenticatedIdentity | None = None
    transport: str = "stdio"
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.status is AuthStatus.AUTHENTICATED:
            if self.identity is None:
                raise ValidationError("AUTHENTICATED outcome requires identity")
        elif self.identity is not None:
            raise ValidationError(
                "non-AUTHENTICATED outcome must not carry identity",
                details={"status": self.status.value},
            )

    @property
    def is_authenticated(self) -> bool:
        return self.status is AuthStatus.AUTHENTICATED and self.identity is not None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status.value,
            "transport": self.transport,
            "auth_contract_version": AUTH_CONTRACT_VERSION,
        }
        if self.reason_code:
            payload["reason_code"] = self.reason_code
        if self.identity is not None:
            payload["identity"] = self.identity.as_dict()
        return payload
