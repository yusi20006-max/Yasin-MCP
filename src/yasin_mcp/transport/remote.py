"""HTTPS / streamable-HTTP remote MCP transport with Bearer auth (Stage 12)."""

from __future__ import annotations

import hmac
import logging
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from yasin_mcp.auth.request_state import auth_request_scope
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.transport.bearer import extract_bearer_token

logger = logging.getLogger(__name__)


class RequireBearerAuthMiddleware:
    """Validate Bearer against configured shared secret before MCP handlers."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        required: bool,
        expected_secret: str | None,
    ) -> None:
        self.app = app
        self.required = required
        self.expected_secret = expected_secret

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or ""
        if path in {"/healthz", "/readyz"}:
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []
        }
        token = extract_bearer_token(headers.get("authorization"))

        if self.required:
            if token is None:
                response = JSONResponse(
                    {
                        "error_contract_version": "1.0.0",
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": "Bearer authentication required",
                    },
                    status_code=401,
                )
                await response(scope, receive, send)
                return
            if not self.expected_secret or not hmac.compare_digest(token, self.expected_secret):
                response = JSONResponse(
                    {
                        "error_contract_version": "1.0.0",
                        "code": "AUTHENTICATION_FAILED",
                        "message": "Bearer authentication failed",
                    },
                    status_code=401,
                )
                await response(scope, receive, send)
                return
            with auth_request_scope(presented_secret=token):
                await self.app(scope, receive, send)
            return

        if token and self.expected_secret and hmac.compare_digest(token, self.expected_secret):
            with auth_request_scope(presented_secret=token):
                await self.app(scope, receive, send)
            return
        await self.app(scope, receive, send)


def build_remote_asgi_app(
    mcp_server: Any,
    config: ServerConfig,
    *,
    streamable_http_path: str = "/mcp",
) -> Starlette:
    base_app = mcp_server.streamable_http_app(
        streamable_http_path=streamable_http_path,
        host=config.remote_host,
    )

    async def healthz(_request: Request) -> Response:
        return JSONResponse({"status": "ok"})

    expected = config.auth_token.get_secret_value() if config.auth_token is not None else None
    middleware = [
        Middleware(
            RequireBearerAuthMiddleware,
            required=config.require_authentication,
            expected_secret=expected,
        ),
    ]

    routes = [
        Route("/healthz", endpoint=healthz, methods=["GET"]),
        Route("/readyz", endpoint=healthz, methods=["GET"]),
    ]
    routes.extend(list(getattr(base_app, "routes", []) or []))
    app = Starlette(routes=routes, middleware=middleware)
    if getattr(base_app, "router", None) is not None and getattr(
        base_app.router, "lifespan_context", None
    ):
        app.router.lifespan_context = base_app.router.lifespan_context
    return app


async def run_remote_server_async(runtime: Any) -> None:
    import uvicorn

    config: ServerConfig = runtime.config
    if not config.remote_enabled:
        raise RuntimeError("remote transport is not enabled in configuration")

    app = build_remote_asgi_app(runtime.server, config)

    ssl_certfile = config.remote_tls_certfile
    ssl_keyfile = config.remote_tls_keyfile
    if not config.remote_allow_insecure_http:
        if not ssl_certfile or not ssl_keyfile:
            raise RuntimeError(
                "remote TLS cert/key required or enable remote_allow_insecure_http "
                "only for local test"
            )

    uv_config = uvicorn.Config(
        app,
        host=config.remote_host,
        port=config.remote_port,
        log_level=config.log_level.lower(),
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
    )
    server = uvicorn.Server(uv_config)
    await server.serve()


def run_remote_server(runtime: Any) -> None:
    import anyio

    anyio.run(run_remote_server_async, runtime)
