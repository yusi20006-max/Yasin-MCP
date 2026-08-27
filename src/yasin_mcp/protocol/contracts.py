"""Versioned, typed contracts for the MCP-facing boundary.

Issue #2 intentionally keeps these contracts independent from a concrete
MCP server runtime. The runtime/transport implementation belongs to Issue #4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from yasin_mcp.capabilities.descriptor import CapabilityDescriptor
from yasin_mcp.errors.errors import ValidationError
from yasin_mcp.governance.types import RiskLevel
from yasin_mcp.version import EvidenceStatus

CURRENT_PROTOCOL_VERSION = "2026-07-28"
CONTRACT_VERSION = "1.0"


class CapabilityScope(str, Enum):
    """Semantic scope of a published capability contract."""

    TOOL = "tool"
    RESOURCE = "resource"


@dataclass(frozen=True)
class ProtocolVersion:
    """Opaque MCP protocol version plus Yasin contract compatibility version."""

    protocol: str = CURRENT_PROTOCOL_VERSION
    contract: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.protocol.strip():
            raise ValidationError("protocol version must not be empty")
        if not self.contract.strip():
            raise ValidationError("contract version must not be empty")

    def as_dict(self) -> dict[str, str]:
        return {"protocol": self.protocol, "contract": self.contract}


@dataclass(frozen=True)
class ServerIdentity:
    """Stable identity metadata advertised by Yasin-MCP."""

    name: str = "Yasin-MCP"
    version: str = "0.1.0"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("server name must not be empty")
        if not self.version.strip():
            raise ValidationError("server version must not be empty")

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True)
class CapabilityContract:
    """Published contract metadata for one safe MCP capability."""

    descriptor: CapabilityDescriptor
    scope: CapabilityScope
    version: str = CONTRACT_VERSION
    input_schema: dict[str, Any] = field(default_factory=dict)
    evidence_status: EvidenceStatus = EvidenceStatus.CONFIRMED
    risk: RiskLevel = RiskLevel.READ_ONLY

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValidationError("capability contract version must not be empty")
        if self.scope.value != self.descriptor.kind.value:
            raise ValidationError(
                "capability scope must match its descriptor kind",
                details={"scope": self.scope.value, "kind": self.descriptor.kind.value},
            )
        if not isinstance(self.input_schema, dict):
            raise ValidationError("input_schema must be a dictionary")

    @property
    def name(self) -> str:
        return self.descriptor.name

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.scope.value,
            "description": self.descriptor.description,
            "version": self.version,
            "input_schema": dict(self.input_schema),
            "read_only": not self.descriptor.is_mutating,
            "evidence_status": self.evidence_status.value,
            "risk": self.risk.value,
        }
