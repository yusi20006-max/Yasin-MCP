"""Structured logging, correlation IDs, and defensive secret redaction."""

from __future__ import annotations

import json
import logging
import sys
import uuid
from collections.abc import Mapping
from typing import Any

_REDACTED = "***"
_SENSITIVE_KEY_PARTS = (
    "token",
    "secret",
    "password",
    "passwd",
    "authorization",
    "api_key",
    "apikey",
    "credential",
)


def new_request_id() -> str:
    """Generate a new correlation/request ID."""
    return str(uuid.uuid4())


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def redact(value: Any) -> Any:
    """Recursively redact sensitive mapping keys before they reach logs."""
    if isinstance(value, Mapping):
        return {
            key: _REDACTED if _is_sensitive_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON with redacted fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            payload["request_id"] = request_id
        extra_fields = getattr(record, "fields", None)
        if extra_fields:
            payload["fields"] = redact(extra_fields)
        return json.dumps(redact(payload), default=str)


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the yasin_mcp logger idempotently."""
    logger = logging.getLogger("yasin_mcp")
    logger.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    request_id: str | None = None,
    fields: Mapping[str, Any] | None = None,
) -> None:
    """Log a message with correlation ID and defensively redacted fields."""
    logger.log(
        level,
        message,
        extra={"request_id": request_id, "fields": redact(fields or {})},
    )
