"""Central governance enforcement boundary for tool execution."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

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

if TYPE_CHECKING:
    from yasin_mcp.config.config import ServerConfig

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
    """Single enforcement point: optional auth, then policy, audit, execute.

    Ordering (Stage 8):
        Authentication resolution (when ServerConfig attached)
            → Identity binding
            → Policy evaluation
            → ALLOW / DENY / APPROVAL_REQUIRED
            → Tool execution only on ALLOW
    """

    def __init__(
        self,
        catalog: ToolRiskCatalog,
        policy: GovernancePolicy | None = None,
        auditor: AuditRecorder | None = None,
        security_config: ServerConfig | None = None,
    ) -> None:
        self._catalog = catalog
        self._policy: GovernancePolicy = policy or DefaultConservativePolicy()
        self._auditor: AuditRecorder = auditor or LoggingAuditRecorder()
        self._security_config = security_config

    @property
    def catalog(self) -> ToolRiskCatalog:
        return self._catalog

    @property
    def policy(self) -> GovernancePolicy:
        return self._policy

    @property
    def security_config(self) -> ServerConfig | None:
        return self._security_config

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
        presented_secret: str | None = None,
    ) -> Any:
        kwargs = dict(kwargs or {})

        from yasin_mcp.auth.enforcement import extract_presented_secret, resolve_execution_auth

        kwargs, extracted_secret = extract_presented_secret(kwargs)
        if presented_secret is None:
            presented_secret = extracted_secret

        bound = resolve_execution_auth(
            self._security_config,
            context=context,
            presented_secret=presented_secret,
        )
        if bound is not None:
            context = bound.governance

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
                    message=type(exc).__name__,
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
