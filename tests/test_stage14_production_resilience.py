from __future__ import annotations

import json
import threading

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from yasin_mcp.config.config import ServerConfig
from yasin_mcp.errors.errors import RateLimitedError
from yasin_mcp.governance.audit import InMemoryAuditRecorder
from yasin_mcp.governance.catalog import ToolRiskCatalog
from yasin_mcp.governance.gate import GovernanceGate
from yasin_mcp.governance.types import GovernanceContext, RiskLevel


def _gate(limit: int = 1, auditor: InMemoryAuditRecorder | None = None) -> GovernanceGate:
    catalog = ToolRiskCatalog({"stage14.test": RiskLevel.READ_ONLY})
    return GovernanceGate(
        catalog,
        security_config=ServerConfig(max_concurrent_requests=limit),
        auditor=auditor,
    )


def test_concurrency_limit_rejects_without_executing_extra_work() -> None:
    gate = _gate(1)
    started = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    def slow() -> str:
        calls.append("first")
        started.set()
        assert release.wait(timeout=2)
        return "ok"

    wrapped = gate.wrap_tool("stage14.test", slow)
    first_result: list[str] = []

    def run_first() -> None:
        first_result.append(wrapped())

    thread = threading.Thread(target=run_first)
    thread.start()
    assert started.wait(timeout=2)

    def unexpected() -> str:
        calls.append("unexpected")
        return "bad"

    rejected = gate.wrap_tool("stage14.test", unexpected)
    with pytest.raises(ToolError) as exc_info:
        rejected()

    payload = json.loads(str(exc_info.value))
    assert payload["code"] == "CONCURRENCY_LIMIT"
    assert payload["details"]["limit"] == 1
    assert calls == ["first"]

    release.set()
    thread.join(timeout=2)
    assert first_result == ["ok"]
    assert not thread.is_alive()


def test_concurrency_slot_is_released_after_failure() -> None:
    gate = _gate(1)
    calls: list[str] = []

    def failing() -> None:
        calls.append("failed")
        raise RuntimeError("expected failure")

    wrapped_failure = gate.wrap_tool("stage14.test", failing)
    with pytest.raises(RuntimeError, match="expected failure"):
        wrapped_failure()

    def succeeds() -> str:
        calls.append("success")
        return "ok"

    wrapped_success = gate.wrap_tool("stage14.test", succeeds)
    assert wrapped_success() == "ok"
    assert calls == ["failed", "success"]


def test_rate_limited_error_is_secret_free() -> None:
    error = RateLimitedError(
        "MCP concurrency limit reached; retry later",
        details={"limit": 2, "authorization": "secret-value"},
    )
    from yasin_mcp.errors.client_contract import map_mcp_error

    payload = map_mcp_error(error)
    assert payload["code"] == "CONCURRENCY_LIMIT"
    assert payload["details"] == {"limit": 2}


def test_repeated_sessions_keep_request_identity_isolated_and_audited() -> None:
    auditor = InMemoryAuditRecorder()
    gate = _gate(2, auditor)
    observed: list[GovernanceContext] = []

    def capture() -> str:
        return "ok"

    for index in range(50):
        context = GovernanceContext(
            client_id="stage14-client",
            agent_id="stage14-agent",
            project_id="stage14-project",
            session_id=f"session-{index}",
            request_id=f"request-{index}",
            correlation_id=f"correlation-{index}",
        )
        gate.execute("stage14.test", capture, context=context)
        observed.append(context)

    assert len(observed) == 50
    assert len({item.session_id for item in observed}) == 50
    assert len({item.request_id for item in observed}) == 50
    assert len({item.correlation_id for item in observed}) == 50
    requests = auditor.of_type(__import__("yasin_mcp.governance.audit", fromlist=["AuditEventType"]).AuditEventType.REQUEST)
    assert len(requests) == 50
    assert [event.context["request_id"] for event in requests] == [
        f"request-{index}" for index in range(50)
    ]
    assert [event.context["correlation_id"] for event in requests] == [
        f"correlation-{index}" for index in range(50)
    ]


def test_bounded_stress_never_exceeds_configured_concurrency_and_recovers() -> None:
    gate = _gate(2)
    lock = threading.Lock()
    active = 0
    maximum = 0
    completed = 0

    def work() -> str:
        nonlocal active, maximum, completed
        with lock:
            active += 1
            maximum = max(maximum, active)
        try:
            assert threading.Event().wait(0.01)
            return "ok"
        finally:
            with lock:
                active -= 1
                completed += 1

    wrapped = gate.wrap_tool("stage14.test", work)
    results: list[str] = []
    errors: list[Exception] = []

    def invoke() -> None:
        try:
            results.append(wrapped())
        except Exception as exc:  # rejected requests are expected under saturation
            errors.append(exc)

    threads = [threading.Thread(target=invoke) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert all(not thread.is_alive() for thread in threads)
    assert maximum <= 2
    assert active == 0
    assert completed == len(results)
    assert results

    # The gate must remain usable after the stress burst.
    assert wrapped() == "ok"
