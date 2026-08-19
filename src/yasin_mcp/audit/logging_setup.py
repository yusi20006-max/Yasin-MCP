"""Structured logging and correlation/request IDs.

Provides a JSON-structured logger and a request-id generator so
every log line and error can be correlated to a single request
across adapter calls. Secret redaction: any log call using this
module's helpers must pass SecretStr values as-is (never
.get_secret_value()) -- SecretStr's own __str__/__repr__ already
redact, so a naive f-string or logging call is safe by construction
as long as the raw string is never extracted first.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from collections.abc import Mapping
from typing import Any


def new_request_id() -> str:
    """Generate a new correlation/request ID."""
    return str(uuid.uuid4())


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

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
            payload["fields"] = extra_fields
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the yasin_mcp root logger.

    Writes structured JSON to stdout. Safe to call multiple times
    (idempotent handler setup) for use in tests.
    """
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
    """Log message with optional request_id and structured fields."""
    logger.log(level, message, extra={"request_id": request_id, "fields": fields or {}})
