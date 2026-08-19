"""Configuration model.

Environment-based, with defaults and validation. Any field that can
hold a secret (currently: github_token) uses SecretStr so it is
never accidentally included in a repr(), str(), or log line -- only
.get_secret_value() exposes the raw value, and callers must do so
deliberately.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class InvalidConfigurationError(Exception):
    """Raised when a configuration value fails validation."""


@dataclass(frozen=True)
class SecretStr:
    """Wraps a secret value so it never appears in repr()/str()/logs by accident."""

    _value: str = field(repr=False)

    def get_secret_value(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "SecretStr('***')"

    def __str__(self) -> str:
        return "***"

    def __bool__(self) -> bool:
        return bool(self._value)


_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


@dataclass(frozen=True)
class ServerConfig:
    """Top-level Yasin-MCP server configuration.

    github_token is Optional: Issue #6 (GitHub adapter) must work
    with authentication absent (lower rate limits, public-only
    access) rather than requiring a token to start at all.
    """

    log_level: str = "INFO"
    request_timeout_seconds: int = 30
    github_token: SecretStr | None = None

    def __post_init__(self) -> None:
        if self.log_level not in _VALID_LOG_LEVELS:
            raise InvalidConfigurationError(
                f"log_level must be one of {sorted(_VALID_LOG_LEVELS)}, got {self.log_level!r}"
            )
        if self.request_timeout_seconds <= 0:
            raise InvalidConfigurationError(
                f"request_timeout_seconds must be positive, got {self.request_timeout_seconds!r}"
            )


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise InvalidConfigurationError(
            f"Environment variable {name} must be an integer, got {raw!r}"
        ) from None


def _env_secret(name: str) -> SecretStr | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    return SecretStr(raw)


def load_config() -> ServerConfig:
    """Build configuration from the environment.

    Recognized environment variables:
    - YASIN_MCP_LOG_LEVEL
    - YASIN_MCP_REQUEST_TIMEOUT_SECONDS
    - YASIN_MCP_GITHUB_TOKEN (optional; adapter must degrade gracefully without it)
    """
    return ServerConfig(
        log_level=_env_str("YASIN_MCP_LOG_LEVEL", "INFO"),
        request_timeout_seconds=_env_int("YASIN_MCP_REQUEST_TIMEOUT_SECONDS", 30),
        github_token=_env_secret("YASIN_MCP_GITHUB_TOKEN"),
    )
