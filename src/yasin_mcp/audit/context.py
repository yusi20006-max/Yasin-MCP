"""Request correlation context for end-to-end observability."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from yasin_mcp.audit.logging_setup import new_request_id

_request_id: ContextVar[str | None] = ContextVar("yasin_mcp_request_id", default=None)


def get_request_id() -> str | None:
    """Return the current request correlation ID, if any."""
    return _request_id.get()


def set_request_id(request_id: str | None) -> None:
    """Set the current request correlation ID."""
    _request_id.set(request_id)


@contextmanager
def request_scope(request_id: str | None = None) -> Iterator[str]:
    """Bind a request ID for the duration of the block; generate one if omitted."""
    rid = request_id or new_request_id()
    token = _request_id.set(rid)
    try:
        yield rid
    finally:
        _request_id.reset(token)


def correlated_fields(**fields: Any) -> dict[str, Any]:
    """Merge explicit fields with the active request_id for structured logs."""
    out = dict(fields)
    rid = get_request_id()
    if rid is not None:
        out.setdefault("request_id", rid)
    return out
