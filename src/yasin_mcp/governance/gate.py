"""Central governance enforcement boundary for tool execution."""

from __future__ import annotations

import functools
import inspect
import os
import threading
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, Any, TypeVar

from yasin_mcp.approval.constants import APPROVAL_PRESENT_ENV, APPROVAL_TOKEN_KWARG
from yasin_mcp.approval.store import InMemoryApprovalStore
from yasin_mcp.approval.types import ApprovalStatus
from yasin_mcp.errors.errors import PolicyDeniedError, RateLimitedError, ValidationError
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
    RiskLevel,
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


def _extract_approval_token(
    kwargs: dict[str, Any],
    *,
    allow_environment_fallback: bool,
) -> tuple[dict[str, Any], str | None]:
    """Extract request-presented approval without using a remote process fallback."""
    cleaned = dict(kwargs)
    raw = cleaned.pop(APPROVAL_TOKEN_KWARG, None)
    if raw is not None:
        return cleaned, raw if isinstance(raw, str) else str(raw)
    if not allow_environment_fallback:
        return cleaned, None
    env_val = os.environ.get(APPROVAL_PRESENT_ENV)
    return cleaned, env_val if env_val else None


class GovernanceGate:
    """Single enforcement point: auth → approval → policy → execute."""

    def __init__(
        self,
        catalog: ToolRiskCatalog,
        policy: GovernancePolicy | None = None,
        auditor: AuditRecorder | None = None,
        security_config: ServerConfig | None = None,
        approval_store: InMemoryApprovalStore | None = None,
    ) -> None:
        self._catalog = catalog
        self._policy: GovernancePolicy = policy or DefaultConservativePolicy()
        self._auditor: AuditRecorder = auditor or LoggingAuditRecorder()
        self._security_config = security_config
        self._approval_store = approval_store
        configured_limit = getattr(security_config, "max_concurrent_requests", 32)
        self._concurrency_limit = configured_limit
        self._concurrency_slots = threading.BoundedSemaphore(configured_limit)

    @property
    def catalog(self) -> ToolRiskCatalog:
        return self._catalog

    @property
    def policy(self) -> GovernancePolicy:
        return self._policy

    @property
    def security_config(self) -> ServerConfig | None:
        return self._security_config

    @property
    def approval_store(self) -> InMemoryApprovalStore | None:
        return self._approval_store

    @property
    def concurrency_limit(self) -> int:
        return self._concurrency_limit

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

    def _apply_approval(
        self,
        tool_name: str,
        tool: ToolIdentity,
        context: GovernanceContext | None,
        approval_token: str | None,
    ) -> GovernanceContext | None:
        needs = tool.risk is RiskLevel.MUTATION or approval_token is not None
        if not needs:
            return context

        store = self._approval_store
        if store is None:
            if tool.risk is RiskLevel.MUTATION and approval_token:
                raise ValidationError(
                    "approval store not configured",
                    details={"reason_code": "approval_unknown", "tool": tool_name},
                )
            return context

        subject: str | None = None
        if context is not None:
            subject = context.agent_id
        result = store.validate_and_consume(
            approval_token,
            tool_name=tool_name,
            context=context,
            subject_id=subject,
        )

        extra: dict[str, Any] = dict(context.extra) if context else {}
        extra["approval_status"] = result.status.value
        extra["approval_reason"] = result.reason_code
        if result.grant is not None:
            extra["approval_id"] = result.grant.approval_id

        if result.status is ApprovalStatus.GRANTED:
            if context is None:
                return GovernanceContext(extra=extra)
            return replace(context, extra=extra)

        if result.status is ApprovalStatus.MISSING:
            if context is None:
                return GovernanceContext(extra=extra)
            return replace(context, extra=extra)

        raise ValidationError(
            f"approval rejected: {result.reason_code}",
            details={
                "reason_code": result.reason_code,
                "tool": tool_name,
                "approval_status": result.status.value,
            },
        )

    def execute(
        self,
        tool_name: str,
        fn: Callable[..., Any],
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        context: GovernanceContext | None = None,
        presented_secret: str | None = None,
        approval_token: str | None = None,
    ) -> Any:
        kwargs = dict(kwargs or {})

        from yasin_mcp.auth.enforcement import extract_presented_secret, resolve_execution_auth

        kwargs, extracted_secret = extract_presented_secret(kwargs)
        if presented_secret is None:
            presented_secret = extracted_secret

        allow_environment_fallback = not bool(
            getattr(self._security_config, "remote_enabled", False)
        )
        kwargs, extracted_approval = _extract_approval_token(
            kwargs,
            allow_environment_fallback=allow_environment_fallback,
        )
        if approval_token is None:
            approval_token = extracted_approval

        bound = resolve_execution_auth(
            self._security_config,
            context=context,
            presented_secret=presented_secret,
        )
        if bound is not None:
            context = bound.governance

        tool = self.resolve_tool(tool_name)
        context = self._apply_approval(tool_name, tool, context, approval_token)

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
            from yasin_mcp.errors.client_contract import raise_as_mcp_tool_error
            from yasin_mcp.errors.errors import McpError

            acquired = gate._concurrency_slots.acquire(blocking=False)
            if not acquired:
                raise_as_mcp_tool_error(
                    RateLimitedError(
                        "MCP concurrency limit reached; retry later",
                        details={
                            "limit": gate._concurrency_limit,
                            "reason_code": "concurrency_limit",
                        },
                    )
                )
            try:
                return gate.execute(tool_name, fn, args=args, kwargs=kwargs)
            except McpError as exc:
                raise_as_mcp_tool_error(exc)
                raise  # pragma: no cover
            finally:
                if acquired:
                    gate._concurrency_slots.release()

        # MCP's tool schema generator may inspect the concrete wrapper signature
        # rather than following functools' __wrapped__ chain. Preserve the wrapped
        # callable's signature explicitly so governed tools expose their real
        # arguments (for example owner/repository) instead of *args/**kwargs.
        setattr(sync_wrapper, "__signature__", inspect.signature(fn))

        return sync_wrapper  # type: ignore[return-value]
