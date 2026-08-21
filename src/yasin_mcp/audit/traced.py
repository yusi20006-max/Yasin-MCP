"""Helpers that emit correlated, redacted structured logs around external I/O."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from yasin_mcp.audit.context import get_request_id, request_scope
from yasin_mcp.audit.logging_setup import configure_logging, log_with_context, redact

T = TypeVar("T")
_logger = logging.getLogger("yasin_mcp.traced")


def ensure_logger() -> logging.Logger:
    return configure_logging()


def run_traced(
    operation: str,
    fn: Callable[[], T],
    *,
    fields: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> T:
    """Execute *fn* under a request scope with start/end structured logs.

    Sensitive keys in *fields* are redacted. The returned value is not logged.
    """
    logger = ensure_logger()
    with request_scope(request_id) as rid:
        safe = redact(fields or {})
        merged: dict[str, Any] = {"operation": operation}
        if isinstance(safe, dict):
            merged.update(safe)
        log_with_context(
            logger,
            logging.INFO,
            f"start:{operation}",
            request_id=rid,
            fields=merged,
        )
        try:
            result = fn()
        except Exception as exc:
            log_with_context(
                logger,
                logging.ERROR,
                f"error:{operation}",
                request_id=rid,
                fields={
                    "operation": operation,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                },
            )
            raise
        log_with_context(
            logger,
            logging.INFO,
            f"end:{operation}",
            request_id=rid,
            fields={"operation": operation, "ok": True},
        )
        return result


def current_request_id() -> str | None:
    return get_request_id()
