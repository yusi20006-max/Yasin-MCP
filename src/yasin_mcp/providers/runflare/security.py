"""Runflare provider input validation and output sanitization."""

from __future__ import annotations

import os
import re
from pathlib import Path

_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(secret\s*[:=]\s*)[^\s,;]+"),
)


def redact(text: str, limit: int) -> str:
    value = text
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(r"\1[REDACTED]", value)
    if len(value) > limit:
        value = value[:limit] + "\n[OUTPUT TRUNCATED]"
    return value


def validate_project_dir(project_dir: str) -> Path:
    if not project_dir:
        raise ValueError("Runflare project directory is not configured")
    path = Path(project_dir).expanduser().resolve()
    if not path.is_dir():
        raise ValueError("Runflare project directory does not exist")
    root = os.getenv("RUNFLARE_ALLOWED_PROJECT_ROOT")
    if root:
        allowed = Path(root).expanduser().resolve()
        try:
            path.relative_to(allowed)
        except ValueError as exc:
            raise ValueError("Runflare project directory is outside the allowed root") from exc
    return path
