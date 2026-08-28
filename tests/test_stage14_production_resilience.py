from __future__ import annotations

import json
import threading

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from yasin_mcp.config.config import ServerConfig
from yasin_mcp.errors.errors import RateLimitedError
from yasin_mcp.governance.catalog import ToolRiskCatalog
from yasin_mcp.governance.gate import GovernanceGate
from yasin_mcp.governance.types import RiskLevel


def _gate(limit: int = 1) -> GovernanceGate:
    catalog = ToolRiskCatalog({"stage14.test": RiskLevel.READ_ONLY})
    return GovernanceGate(catalog, security_config=ServerConfig(max_concurrent_requests=limit))


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
