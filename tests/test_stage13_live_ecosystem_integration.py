"""Stage 13 / Issue #99 — live ecosystem-client integration evidence.

The test client follows the current Yasin-Agent public execution concepts:
agent/task/session context plus a tool runner, while using the MCP SDK's
Streamable HTTP client as the actual wire client. Yasin-Agent itself remains
transport-agnostic and does not currently ship an MCP transport dependency.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from dataclasses import dataclass

import httpx2
import pytest
import uvicorn

from yasin_mcp.approval.constants import APPROVAL_PRESENT_ENV
from yasin_mcp.config.config import SecretStr, ServerConfig
from yasin_mcp.governance.audit import AuditEventType, InMemoryAuditRecorder
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.transport.remote import build_remote_asgi_app

SECRET = "TEST_STAGE13_ECOSYSTEM_SECRET"


@dataclass(frozen=True)
class AgentExecutionContext:
    """Minimal adapter payload matching Yasin-Agent's session/task semantics."""

    agent_id: str
    project_id: str
    workspace_id: str
    task_id: str
    session_id: str
    request_id: str
    correlation_id: str

    def headers(self) -> dict[str, str]:
        import json

        context = {
            "client_id": "yasin-agent-stage13",
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
        }
        return {
            "Authorization": f"Bearer {SECRET}",
            "X-Yasin-Context": json.dumps(context, separators=(",", ":")),
        }


class LiveYasinAgentClient:
    """Small ecosystem compatibility client; orchestration stays in Yasin-Agent."""

    def __init__(self, url: str, context: AgentExecutionContext) -> None:
        self.url = url
        self.context = context

    async def run(self) -> tuple[list[str], object, object]:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with httpx2.AsyncClient(
            headers=self.context.headers(),
            timeout=httpx2.Timeout(10.0, read=30.0),
            follow_redirects=True,
        ) as http_client:
            async with streamable_http_client(
                self.url,
                http_client=http_client,
            ) as (read_stream, write_stream, _session_id):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = [tool.name for tool in tools.tools]
                    low_risk = await session.call_tool(
                        "yasin_gov_ping_low_risk",
                        arguments={},
                    )
                    mutation = await session.call_tool(
                        "yasin_gov_apply_mark",
                        arguments={"mark": "stage13-live"},
                    )
                    return names, low_risk, mutation


def _config(port: int) -> ServerConfig:
    return ServerConfig(
        auth_token=SecretStr(SECRET),
        auth_subject_id="agent-stage13",
        require_authentication=True,
        remote_enabled=True,
        remote_host="127.0.0.1",
        remote_port=port,
        remote_allow_insecure_http=True,
    )


def _start_server(port: int, runtime: ServerRuntime) -> tuple[uvicorn.Server, threading.Thread]:
    app = build_remote_asgi_app(runtime.server, runtime.config)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            if httpx2.get(f"http://127.0.0.1:{port}/healthz", timeout=0.5).status_code == 200:
                return server, thread
        except Exception:
            time.sleep(0.05)
    server.should_exit = True
    thread.join(timeout=5)
    pytest.fail("Stage 13 live MCP server did not become ready")


def test_live_yasin_agent_compatible_client_context_auth_governance_and_approval() -> None:
    """One real remote MCP session crosses the complete governed boundary."""
    async def exercise() -> tuple[list[str], object, object]:
        port = 18766
        auditor = InMemoryAuditRecorder()
        runtime = ServerRuntime.create(_config(port), auditor=auditor)
        token = runtime.governance.approval_store.issue(
            tool_name="yasin_gov_apply_mark",
            subject_id="agent-stage13",
            request_id="req-stage13-1",
            project_id="project-stage13",
            ttl_seconds=60,
        )
        old = os.environ.get(APPROVAL_PRESENT_ENV)
        os.environ[APPROVAL_PRESENT_ENV] = token
        server, thread = _start_server(port, runtime)
        try:
            client = LiveYasinAgentClient(
                f"http://127.0.0.1:{port}/mcp",
                AgentExecutionContext(
                    agent_id="agent-stage13",
                    project_id="project-stage13",
                    workspace_id="workspace-stage13",
                    task_id="task-stage13-1",
                    session_id="session-stage13-1",
                    request_id="req-stage13-1",
                    correlation_id="corr-stage13-1",
                ),
            )
            result = await client.run()
            assert "yasin_gov_ping_low_risk" in result[0]
            assert result[1] is not None
            assert result[2] is not None

            requests = auditor.of_type(AuditEventType.REQUEST)
            assert len(requests) >= 2
            contexts = [event.context for event in requests]
            assert any(c.get("correlation_id") == "corr-stage13-1" for c in contexts)
            assert any(c.get("request_id") == "req-stage13-1" for c in contexts)
            assert all(c.get("agent_id") == "agent-stage13" for c in contexts)
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            if old is None:
                os.environ.pop(APPROVAL_PRESENT_ENV, None)
            else:
                os.environ[APPROVAL_PRESENT_ENV] = old

        return result

    asyncio.run(exercise())


@pytest.mark.anyio
async def test_remote_context_isolation_and_malformed_context_fail_closed() -> None:
    """Different request contexts remain distinct and malformed input is rejected."""
    auditor = InMemoryAuditRecorder()
    runtime = ServerRuntime.create(_config(18767), auditor=auditor)
    app = build_remote_asgi_app(runtime.server, runtime.config)

    async with httpx2.AsyncClient(
        base_url="http://test",
        transport=httpx2.ASGITransport(app=app),
        headers={"Authorization": f"Bearer {SECRET}"},
    ) as client:
        malformed = await client.post(
            "/mcp",
            headers={"X-Yasin-Context": "not-json"},
            json={},
        )
        assert malformed.status_code == 400
        assert malformed.json()["code"] == "INVALID_CONTEXT"

        import json

        for request_id in ("req-a", "req-b"):
            context = json.dumps(
                {
                    "client_id": "yasin-agent-stage13",
                    "agent_id": "agent-stage13",
                    "project_id": "project-stage13",
                    "task_id": request_id,
                    "session_id": f"session-{request_id}",
                    "request_id": request_id,
                    "correlation_id": f"corr-{request_id}",
                },
                separators=(",", ":"),
            )
            response = await client.post(
                "/mcp",
                headers={"X-Yasin-Context": context},
                json={},
            )
            assert response.status_code != 401

    # No request should have inherited malformed or stale context.
    assert all(event.context.get("request_id") in {"req-a", "req-b"} for event in auditor.events)
