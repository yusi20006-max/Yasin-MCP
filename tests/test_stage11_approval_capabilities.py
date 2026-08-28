"""Stage 11 / Issue #97 — approval + LOW_RISK/MUTATION capabilities."""

from __future__ import annotations

import concurrent.futures
from datetime import datetime, timedelta, timezone

import pytest

from yasin_mcp.approval import APPROVAL_TOKEN_KWARG, InMemoryApprovalStore
from yasin_mcp.errors.errors import PolicyDeniedError, ValidationError
from yasin_mcp.governance import (
    DefaultConservativePolicy,
    GovernanceContext,
    GovernanceGate,
    InMemoryAuditRecorder,
    RiskLevel,
    ToolRiskCatalog,
)
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.tools.governance_ref import TOOL_GOV_APPLY_MARK, TOOL_GOV_PING_LOW_RISK


def _gate(store: InMemoryApprovalStore | None = None) -> tuple[GovernanceGate, InMemoryApprovalStore]:
    store = store or InMemoryApprovalStore()
    gate = GovernanceGate(
        ToolRiskCatalog(
            {
                TOOL_GOV_PING_LOW_RISK: RiskLevel.LOW_RISK,
                TOOL_GOV_APPLY_MARK: RiskLevel.MUTATION,
                "danger": RiskLevel.HIGH_RISK,
            }
        ),
        policy=DefaultConservativePolicy(),
        auditor=InMemoryAuditRecorder(),
        approval_store=store,
    )
    return gate, store


def test_low_risk_allows() -> None:
    gate, _ = _gate()
    calls: list[str] = []
    assert gate.execute(TOOL_GOV_PING_LOW_RISK, lambda: calls.append("x") or 1) == 1
    assert calls == ["x"]


def test_mutation_requires_approval() -> None:
    gate, _ = _gate()
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError) as ei:
        gate.execute(TOOL_GOV_APPLY_MARK, lambda: calls.append("x") or 1)
    assert calls == []
    assert ei.value.details["decision"] == "approval_required"


def test_mutation_with_approval_executes() -> None:
    gate, store = _gate()
    token = store.issue(tool_name=TOOL_GOV_APPLY_MARK, ttl_seconds=60)
    assert gate.execute(TOOL_GOV_APPLY_MARK, lambda: 7, kwargs={APPROVAL_TOKEN_KWARG: token}) == 7


def test_approval_replay_blocked() -> None:
    gate, store = _gate()
    token = store.issue(tool_name=TOOL_GOV_APPLY_MARK, ttl_seconds=60)
    gate.execute(TOOL_GOV_APPLY_MARK, lambda: 1, kwargs={APPROVAL_TOKEN_KWARG: token})
    with pytest.raises(ValidationError) as ei:
        gate.execute(TOOL_GOV_APPLY_MARK, lambda: 2, kwargs={APPROVAL_TOKEN_KWARG: token})
    assert ei.value.details["reason_code"] == "approval_replayed"


def test_high_risk_denied_with_approval() -> None:
    gate, store = _gate()
    token = store.issue(tool_name="danger", ttl_seconds=60)
    calls: list[str] = []
    with pytest.raises(PolicyDeniedError):
        gate.execute("danger", lambda: calls.append("x") or 1, kwargs={APPROVAL_TOKEN_KWARG: token})
    assert calls == []


def test_forged_context_approval_ignored() -> None:
    gate, _ = _gate()
    calls: list[str] = []
    ctx = GovernanceContext(extra={"approval_status": "granted"})
    with pytest.raises(PolicyDeniedError):
        gate.execute(TOOL_GOV_APPLY_MARK, lambda: calls.append("x") or 1, context=ctx)
    assert calls == []


def test_token_stripped() -> None:
    gate, store = _gate()
    token = store.issue(tool_name=TOOL_GOV_APPLY_MARK, ttl_seconds=60)
    seen: list[dict] = []

    def tool(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(dict(kwargs))
        return "ok"

    assert (
        gate.execute(
            TOOL_GOV_APPLY_MARK, tool, kwargs={APPROVAL_TOKEN_KWARG: token, "mark": "m"}
        )
        == "ok"
    )
    assert APPROVAL_TOKEN_KWARG not in seen[0]


def test_concurrent_consume_once() -> None:
    gate, store = _gate()
    token = store.issue(tool_name=TOOL_GOV_APPLY_MARK, ttl_seconds=120)

    def worker() -> str:
        try:
            gate.execute(TOOL_GOV_APPLY_MARK, lambda: "ok", kwargs={APPROVAL_TOKEN_KWARG: token})
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return type(exc).__name__

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _: worker(), range(8)))
    assert outcomes.count("ok") == 1


def test_runtime_registers_gov_tools() -> None:
    rt = ServerRuntime.create()
    assert TOOL_GOV_PING_LOW_RISK in rt.governance.catalog.known_names()
    assert rt.governance.resolve_tool(TOOL_GOV_APPLY_MARK).risk is RiskLevel.MUTATION
    assert rt.governance.approval_store is not None
