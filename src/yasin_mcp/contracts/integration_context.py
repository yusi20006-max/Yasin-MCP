"""Stage 6 / Issue #87 — typed integration context contract.

Caller-supplied fields are ASSERTED only. Stdio does not authenticate the
peer; nothing in this module elevates ASSERTED → TRUSTED.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from yasin_mcp.errors.errors import ValidationError
from yasin_mcp.governance.types import GovernanceContext

INTEGRATION_CONTRACT_VERSION: Final[str] = "1.0.0"
MAX_ID_LENGTH: Final[int] = 128
MAX_EXTRA_KEYS: Final[int] = 16
MAX_EXTRA_VALUE_LENGTH: Final[int] = 256

# Printable identifier: letters, digits, and a small set of separators.
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+/-]{0,127}$")

_SENSITIVE_EXTRA_PARTS = (
    "token",
    "secret",
    "password",
    "passwd",
    "authorization",
    "api_key",
    "apikey",
    "credential",
)


class TrustClassification(str, Enum):
    """How strongly an identity field may be treated by policy.

    ASSERTED: supplied by the MCP client; unauthenticated over stdio.
    TRUSTED: verified by an authentication layer (not available on stdio).
    UNRESOLVED: not established for this transport/deployment.
    """

    ASSERTED = "asserted"
    TRUSTED = "trusted"
    UNRESOLVED = "unresolved"


def _validate_optional_id(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(
            f"{name} must be a string or null",
            details={"field": name, "type": type(value).__name__},
        )
    stripped = value.strip()
    if not stripped:
        raise ValidationError(
            f"{name} must not be empty or whitespace",
            details={"field": name},
        )
    if len(stripped) > MAX_ID_LENGTH:
        raise ValidationError(
            f"{name} exceeds maximum length {MAX_ID_LENGTH}",
            details={"field": name, "length": len(stripped)},
        )
    if not _ID_RE.match(stripped):
        raise ValidationError(
            f"{name} contains invalid characters",
            details={"field": name},
        )
    return stripped


def _validate_extra(extra: Mapping[str, Any] | None) -> dict[str, Any]:
    if extra is None:
        return {}
    if not isinstance(extra, Mapping):
        raise ValidationError(
            "extra must be a mapping",
            details={"type": type(extra).__name__},
        )
    if len(extra) > MAX_EXTRA_KEYS:
        raise ValidationError(
            f"extra may contain at most {MAX_EXTRA_KEYS} keys",
            details={"count": len(extra)},
        )
    out: dict[str, Any] = {}
    for key, value in extra.items():
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(
                "extra keys must be non-empty strings",
                details={"key": str(key)[:64]},
            )
        key_l = key.lower().replace("-", "_")
        if any(part in key_l for part in _SENSITIVE_EXTRA_PARTS):
            raise ValidationError(
                "extra must not contain sensitive key names",
                details={"key": key},
            )
        if isinstance(value, str) and len(value) > MAX_EXTRA_VALUE_LENGTH:
            raise ValidationError(
                f"extra[{key!r}] value exceeds maximum length",
                details={"key": key, "length": len(value)},
            )
        if isinstance(value, (dict, list)):
            raise ValidationError(
                f"extra[{key!r}] must be a scalar",
                details={"key": key},
            )
        out[key] = value
    return out


@dataclass(frozen=True)
class IntegrationContext:
    """Minimal typed context for ecosystem → Yasin-MCP integration.

    All identity fields are ASSERTED when constructed from client input.
    """

    client_id: str | None = None
    agent_id: str | None = None
    project_id: str | None = None
    workspace_id: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    extra: dict[str, Any] | None = None
    trust: TrustClassification = TrustClassification.ASSERTED

    def __post_init__(self) -> None:
        object.__setattr__(self, "client_id", _validate_optional_id("client_id", self.client_id))
        object.__setattr__(self, "agent_id", _validate_optional_id("agent_id", self.agent_id))
        object.__setattr__(self, "project_id", _validate_optional_id("project_id", self.project_id))
        object.__setattr__(
            self, "workspace_id", _validate_optional_id("workspace_id", self.workspace_id)
        )
        object.__setattr__(self, "task_id", _validate_optional_id("task_id", self.task_id))
        object.__setattr__(self, "session_id", _validate_optional_id("session_id", self.session_id))
        object.__setattr__(self, "request_id", _validate_optional_id("request_id", self.request_id))
        object.__setattr__(
            self, "correlation_id", _validate_optional_id("correlation_id", self.correlation_id)
        )
        object.__setattr__(self, "extra", _validate_extra(self.extra))
        if not isinstance(self.trust, TrustClassification):
            raise ValidationError(
                "trust must be a TrustClassification",
                details={"trust": str(self.trust)},
            )
        # Client-constructed contexts cannot claim TRUSTED over this contract.
        if self.trust is TrustClassification.TRUSTED:
            raise ValidationError(
                "caller cannot assert TRUSTED identity; authentication is UNRESOLVED on stdio",
                details={"trust": self.trust.value},
            )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> IntegrationContext:
        """Parse and validate a mapping; malformed input fails closed."""
        if data is None:
            return cls()
        if not isinstance(data, Mapping):
            raise ValidationError(
                "integration context must be a mapping",
                details={"type": type(data).__name__},
            )
        unknown = set(data) - {
            "client_id",
            "agent_id",
            "project_id",
            "workspace_id",
            "task_id",
            "session_id",
            "request_id",
            "correlation_id",
            "extra",
            "trust",
        }
        if unknown:
            raise ValidationError(
                "integration context contains unknown fields",
                details={"unknown": sorted(unknown)[:10]},
            )
        trust_raw = data.get("trust", TrustClassification.ASSERTED.value)
        if isinstance(trust_raw, TrustClassification):
            trust = trust_raw
        elif isinstance(trust_raw, str):
            try:
                trust = TrustClassification(trust_raw.lower())
            except ValueError as exc:
                raise ValidationError(
                    "invalid trust classification",
                    details={"trust": trust_raw},
                ) from exc
        else:
            raise ValidationError(
                "trust must be a string",
                details={"type": type(trust_raw).__name__},
            )
        return cls(
            client_id=data.get("client_id"),
            agent_id=data.get("agent_id"),
            project_id=data.get("project_id"),
            workspace_id=data.get("workspace_id"),
            task_id=data.get("task_id"),
            session_id=data.get("session_id"),
            request_id=data.get("request_id"),
            correlation_id=data.get("correlation_id"),
            extra=data.get("extra"),
            trust=trust,
        )

    def to_governance_context(self) -> GovernanceContext:
        """Map to GovernanceContext for gate evaluation and audit."""
        return GovernanceContext(
            client_id=self.client_id,
            agent_id=self.agent_id,
            project_id=self.project_id,
            workspace_id=self.workspace_id,
            task_id=self.task_id,
            session_id=self.session_id,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            extra=dict(self.extra or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        payload = self.to_governance_context().as_dict()
        payload["trust"] = self.trust.value
        payload["integration_contract_version"] = INTEGRATION_CONTRACT_VERSION
        return payload


def integration_contract_summary() -> dict[str, Any]:
    """Safe, non-secret discovery metadata for integrators."""
    return {
        "integration_contract_version": INTEGRATION_CONTRACT_VERSION,
        "transport": "stdio",
        "identity_trust_default": TrustClassification.ASSERTED.value,
        "stdio_authentication": TrustClassification.UNRESOLVED.value,
        "fields": [
            "client_id",
            "agent_id",
            "project_id",
            "workspace_id",
            "task_id",
            "session_id",
            "request_id",
            "correlation_id",
            "extra",
        ],
        "governance": "centralized",
        "privilege_escalation_via_metadata": False,
        "evidence_status": "confirmed",
    }
