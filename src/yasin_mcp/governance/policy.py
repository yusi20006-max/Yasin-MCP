"""Deterministic governance policy evaluation."""

from __future__ import annotations

from typing import Protocol

from yasin_mcp.errors.errors import ValidationError
from yasin_mcp.governance.types import (
    GovernanceContext,
    GovernanceDecision,
    RiskLevel,
    ToolIdentity,
)


class GovernancePolicy(Protocol):
    def evaluate(
        self,
        tool: ToolIdentity,
        context: GovernanceContext | None = None,
    ) -> GovernanceDecision: ...


class DefaultConservativePolicy:
    """Deny-by-default conservative policy (Stages 3–11).

    - Unknown -> DENY
    - READ_ONLY / LOW_RISK -> ALLOW
    - MUTATION without approval_status=granted -> APPROVAL_REQUIRED
    - MUTATION with granted -> ALLOW
    - HIGH_RISK -> DENY (approval does not override)
    """

    def evaluate(
        self,
        tool: ToolIdentity,
        context: GovernanceContext | None = None,
    ) -> GovernanceDecision:
        if not tool.known:
            return GovernanceDecision.DENY
        if tool.risk in (RiskLevel.READ_ONLY, RiskLevel.LOW_RISK):
            return GovernanceDecision.ALLOW
        if tool.risk is RiskLevel.MUTATION:
            if context is not None and context.extra.get("approval_status") == "granted":
                return GovernanceDecision.ALLOW
            return GovernanceDecision.APPROVAL_REQUIRED
        if tool.risk is RiskLevel.HIGH_RISK:
            return GovernanceDecision.DENY
        raise ValidationError(
            f"Invalid risk classification {tool.risk!r} for tool {tool.name!r}",
            details={"tool": tool.name, "risk": str(tool.risk)},
        )


class StaticDecisionPolicy:
    def __init__(
        self,
        decisions: dict[str, GovernanceDecision],
        *,
        fallback: GovernanceDecision = GovernanceDecision.DENY,
    ) -> None:
        if not isinstance(fallback, GovernanceDecision):
            raise ValidationError(
                f"Invalid fallback decision {fallback!r}",
                details={"fallback": str(fallback)},
            )
        normalized: dict[str, GovernanceDecision] = {}
        for name, decision in decisions.items():
            if not isinstance(name, str) or not name.strip():
                raise ValidationError(
                    "Policy tool name must be a non-empty string",
                    details={"name": name},
                )
            if not isinstance(decision, GovernanceDecision):
                raise ValidationError(
                    f"Invalid decision {decision!r} for tool {name!r}",
                    details={"name": name, "decision": str(decision)},
                )
            normalized[name.strip()] = decision
        self._decisions = normalized
        self._fallback = fallback

    def evaluate(
        self,
        tool: ToolIdentity,
        context: GovernanceContext | None = None,
    ) -> GovernanceDecision:
        del context
        return self._decisions.get(tool.name, self._fallback)
