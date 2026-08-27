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
    """Evaluate whether a tool invocation may proceed."""

    def evaluate(
        self,
        tool: ToolIdentity,
        context: GovernanceContext | None = None,
    ) -> GovernanceDecision:
        """Return exactly one of ALLOW, DENY, APPROVAL_REQUIRED."""
        ...


class DefaultConservativePolicy:
    """Deny-by-default policy for the current read-only MCP surface.

    Rules (deterministic):
    - Unknown tools -> DENY
    - READ_ONLY / LOW_RISK -> ALLOW
    - MUTATION -> APPROVAL_REQUIRED (do not execute)
    - HIGH_RISK -> DENY
    """

    def evaluate(
        self,
        tool: ToolIdentity,
        context: GovernanceContext | None = None,
    ) -> GovernanceDecision:
        del context
        if not tool.known:
            return GovernanceDecision.DENY
        if tool.risk in (RiskLevel.READ_ONLY, RiskLevel.LOW_RISK):
            return GovernanceDecision.ALLOW
        if tool.risk is RiskLevel.MUTATION:
            return GovernanceDecision.APPROVAL_REQUIRED
        if tool.risk is RiskLevel.HIGH_RISK:
            return GovernanceDecision.DENY
        raise ValidationError(
            f"Invalid risk classification {tool.risk!r} for tool {tool.name!r}",
            details={"tool": tool.name, "risk": str(tool.risk)},
        )


class StaticDecisionPolicy:
    """Test/extension policy that maps tool names to fixed decisions."""

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
                    f"Invalid decision value for tool {name!r}: {decision!r}",
                    details={"name": name, "decision": str(decision)},
                )
            normalized[name] = decision
        self._decisions = normalized
        self._fallback = fallback

    def evaluate(
        self,
        tool: ToolIdentity,
        context: GovernanceContext | None = None,
    ) -> GovernanceDecision:
        del context
        return self._decisions.get(tool.name, self._fallback)
