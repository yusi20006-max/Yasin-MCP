"""Stage 12 / Issue #98 — remote Bearer auth + streamable HTTP boundary."""

from __future__ import annotations

import threading
import time

import httpx
import pytest
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from yasin_mcp.config.config import InvalidConfigurationError, SecretStr, ServerConfig
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.transport.bearer import extract_bearer_token
from yasin_mcp.transport.remote import RequireBearerAuthMiddleware, build_remote_asgi_app

SECRET = "TEST_STAGE12_REMOTE_SECRET"


def _remote_config(**kwargs: object) -> ServerConfig:
    base: dict = {
        "auth_token": SecretStr(SECRET),
        "require_authentication": True,
        "auth_subject_id": "remote-operator",
        "remote_enabled": True,
        "remote_host": "127.0.0.1",
        "remote_port": 8765,
        "remote_allow_insecure_http": True,
    }
    base.update(kwargs)
    return ServerConfig(**base)


def test_extract_bearer_token() -> None:
    assert extract_bearer_token("Bearer abc") == "abc"
    assert extract_bearer_token(None) is None


def test_remote_config_requires_tls_without_insecure_flag() -> None:
    with pytest.raises(InvalidConfigurationError):
        ServerConfig(
            auth_token=SecretStr(SECRET),
            require_authentication=True,
            remote_enabled=True,
            remote_allow_insecure_http=False,
        )


@pytest.mark.anyio
async def test_middleware_rejects_missing_and_invalid_bearer() -> None:
    cfg = _remote_config()
    rt = ServerRuntime.create(cfg)
    app = build_remote_asgi_app(rt.server, cfg)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/healthz")).status_code == 200
        r = await client.post("/mcp", json={})
        assert r.status_code == 401
        assert r.json()["code"] == "AUTHENTICATION_REQUIRED"
        r = await client.post("/mcp", headers={"Authorization": "Bearer WRONG"}, json={})
        assert r.status_code == 401
        assert r.json()["code"] == "AUTHENTICATION_FAILED"
        assert SECRET not in r.text


@pytest.mark.anyio
async def test_middleware_accepts_valid_bearer() -> None:
    async def ok(_request):  # type: ignore[no-untyped-def]
        return PlainTextResponse("ok")

    app = Starlette(
        routes=[Route("/mcp", endpoint=ok, methods=["POST"])],
        middleware=[
            Middleware(
                RequireBearerAuthMiddleware,
                required=True,
                expected_secret=SECRET,
            )
        ],
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {SECRET}"},
            content=b"{}",
        )
        assert r.status_code == 200
        assert SECRET not in r.text


def test_stdio_runtime_unaffected() -> None:
    rt = ServerRuntime.create(ServerConfig())
    assert rt.governance is not None


def test_live_remote_uvicorn_health_and_auth() -> None:
    cfg = _remote_config(remote_port=18765)
    rt = ServerRuntime.create(cfg)
    app = build_remote_asgi_app(rt.server, cfg)
    config = uvicorn.Config(app, host="127.0.0.1", port=18765, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                if httpx.get("http://127.0.0.1:18765/healthz", timeout=0.5).status_code == 200:
                    break
            except Exception:
                time.sleep(0.05)
        else:
            pytest.fail("server did not become ready")
        assert httpx.get("http://127.0.0.1:18765/healthz", timeout=2).status_code == 200
        r = httpx.post("http://127.0.0.1:18765/mcp", json={}, timeout=2)
        assert r.status_code == 401
        r = httpx.post(
            "http://127.0.0.1:18765/mcp",
            headers={"Authorization": f"Bearer {SECRET}"},
            json={},
            timeout=2,
        )
        assert r.status_code != 401
        assert SECRET not in r.text
    finally:
        server.should_exit = True
        thread.join(timeout=5)
