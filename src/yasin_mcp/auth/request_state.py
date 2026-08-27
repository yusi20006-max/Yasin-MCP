"""Request-scoped authentication material (Stage 8).

Uses contextvars so concurrent requests cannot share identity/credentials.
Credentials are never logged by this module.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from yasin_mcp.contracts.integration_context import IntegrationContext

_presented_secret: ContextVar[str | None] = ContextVar("yasin_mcp_presented_secret", default=None)
_asserted_context: ContextVar[IntegrationContext | None] = ContextVar(
    "yasin_mcp_asserted_context", default=None
)

AUTH_TOKEN_KWARG = "_yasin_auth_token"


def get_presented_secret() -> str | None:
    return _presented_secret.get()


def get_asserted_context() -> IntegrationContext | None:
    return _asserted_context.get()


@contextmanager
def auth_request_scope(
    *,
    presented_secret: str | None = None,
    asserted: IntegrationContext | None = None,
) -> Iterator[None]:
    """Bind auth material for the duration of one request."""
    t_secret = _presented_secret.set(presented_secret)
    t_ctx = _asserted_context.set(asserted)
    try:
        yield
    finally:
        _presented_secret.reset(t_secret)
        _asserted_context.reset(t_ctx)
