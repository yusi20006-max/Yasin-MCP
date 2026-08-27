"""Typed domain model for the MCP governance boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GovernanceDecision(str, Enum):
    """Outcome of a governance policy evaluation.

    Only ALLOW may reach underlying tool execution.
    """

    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"


class RiskLevel(str, Enum):
    """Risk classification attached to a governed tool.

    READ_ONLY / LOW_RISK are eligible for default ALLOW under the
    conservative policy. MUTATION requires explicit approval.
    HIGH_RISK is denied by default until a future approval path exists.
    """

    READ_ONLY = "read_only"
    LOW_RISK = "low_risk"
    MUTATION = "mutation"
    HIGH_RISK = "high_risk"


@dataclass(frozen=True)
class ToolIdentity:
    """Stable identity of a tool known to the governance layer."""

    name: str
    risk: RiskLevel
    description: str = ""
    known: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("ToolIdentity.name must not be empty")


@dataclass(frozen=True)
class GovernanceContext:
    """Optional request/subject context for policy evaluation.

    Fields are deliberately product-agnostic: do not hard-code Hermes,
    Yasin-Agent, YasinHub, or Control Plane names into policy logic.

    All caller-supplied values are ASSERTED (unauthenticated) over stdio
    unless a future authenticated transport marks them TRUSTED. See
    ``yasin_mcp.contracts.integration_context`` and docs/STAGE6_INTEGRATION.md.
    """

    client_id: str | None = None
    agent_id: str | None = None
    project_id: str | None = None
    workspace_id: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.client_id is not None:
            payload["client_id"] = self.client_id
        if self.agent_id is not None:
            payload["agent_id"] = self.agent_id
        if self.project_id is not None:
            payload["project_id"] = self.project_id
        if self.workspace_id is not None:
            payload["workspace_id"] = self.workspace_id
        if self.task_id is not None:
            payload["task_id"] = self.task_id
        if self.session_id is not None:
            payload["session_id"] = self.session_id
        if self.request_id is not None:
            payload["request_id"] = self.request_id
        if self.correlation_id is not None:
            payload["correlation_id"] = self.correlation_id
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload
