"""Central governance enforcement boundary for tool execution."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from yasin_mcp.errors.errors import PolicyDeniedError, ValidationError
from yasin_mcp.governance.audit import (
    AuditEvent,
    AuditEventType,
    AuditRecorder,
    LoggingAuditRecorder,
    sanitize_audit_payload,
)
from yasin_mcp.governance.catalog import ToolRiskCatalog
from yasin_mcp.governance.policy import DefaultConservativePolicy, GovernancePolicy
from yasin_mcp.governance.types import (
    GovernanceContext,
    GovernanceDecision,
    ToolIdentity,
)

F = TypeVar("F", bound=Callable[..., Any])


def _decision_message(decision: GovernanceDecision, tool_name: str) -> str:
    if decision is GovernanceDecision.DENY:
        return f"Governance denied execution of tool {tool_name!r}"
    if decision is GovernanceDecision.APPROVAL_REQUIRED:
        return (
            f"Governance requires approval before executing tool {tool_name!r}; "
            "execution was not performed"
        )
    return f"Governance decision {decision.value} for tool {tool_name!r}"


class GovernanceGate:
    """Single enforcement point: evaluate policy, audit, then optionally execute."""

    def __init__(
        self,
        catalog: ToolRiskCatalog,
        policy: GovernancePolicy | None = None,
        auditor: AuditRecorder | None = None,
    ) -> None:
        self._catalog = catalog
        self._policy: GovernancePolicy = policy or DefaultConservativePolicy()
        self._auditor: AuditRecorder = auditor or LoggingAuditRecorder()

    @property
    def catalog(self) -> ToolRiskCatalog:
        return self._catalog

    @property
    def policy(self) -> GovernancePolicy:
        return self._policy

    def resolve_tool(self, name: str) -> ToolIdentity:
        return self._catalog.resolve(name)

    def evaluate(
        self,
        tool_name: str,
        context: GovernanceContext | None = None,
    ) -> tuple[ToolIdentity, GovernanceDecision]:
        tool = self.resolve_tool(tool_name)
        decision = self._policy.evaluate(tool, context)
        if not isinstance(decision, GovernanceDecision):
            raise ValidationError(
                f"Policy returned invalid decision {decision!r}",
                details={"tool": tool_name, "decision": str(decision)},
            )
        return tool, decision

    def execute(
        self,
        tool_name: str,
        fn: Callable[..., Any],
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        context: GovernanceContext | None = None,
    ) -> Any:
        kwargs = dict(kwargs or {})
        tool, decision = self.evaluate(tool_name, context)
        safe_context = sanitize_audit_payload(context.as_dict() if context else {})
        if not isinstance(safe_context, dict):
            safe_context = {}

        self._auditor.record(
            AuditEvent(
                event_type=AuditEventType.REQUEST,
                tool_name=tool_name,
                risk=tool.risk,
                decision=None,
                context=safe_context,
                extra={"known": tool.known},
            )
        )
        self._auditor.record(
            AuditEvent(
                event_type=AuditEventType.DECISION,
                tool_name=tool_name,
                risk=tool.risk,
                decision=decision,
                context=safe_context,
                message=_decision_message(decision, tool_name),
            )
        )

        if decision is not GovernanceDecision.ALLOW:
            raise PolicyDeniedError(
                _decision_message(decision, tool_name),
                details={
                    "tool": tool_name,
                    "decision": decision.value,
                    "risk": tool.risk.value,
                    "known": tool.known,
                },
            )

        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            self._auditor.record(
                AuditEvent(
                    event_type=AuditEventType.EXECUTION_FAILURE,
                    tool_name=tool_name,
                    risk=tool.risk,
                    decision=decision,
                    success=False,
                    message=f"{type(exc).__name__}: {str(exc)[:300]}",
                    context=safe_context,
                )
            )
            raise

        self._auditor.record(
            AuditEvent(
                event_type=AuditEventType.EXECUTION_RESULT,
                tool_name=tool_name,
                risk=tool.risk,
                decision=decision,
                success=True,
                context=safe_context,
            )
        )
        return result

    def wrap_tool(self, tool_name: str, fn: F) -> F:
        gate = self
        if inspect.iscoroutinefunction(fn):
            raise TypeError(
                f"Async tool functions are not supported by GovernanceGate (tool {tool_name!r})"
            )

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return gate.execute(tool_name, fn, args=args, kwargs=kwargs)

        return sync_wrapper  # type: ignore[return-value]
