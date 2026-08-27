"""Validated environment configuration with conservative defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class InvalidConfigurationError(Exception):
    """Raised when a configuration value fails validation."""


@dataclass(frozen=True)
class SecretStr:
    """Secret wrapper that redacts itself from normal string representations."""

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
_DEFAULT_TIMEOUT = 30
_MAX_TIMEOUT = 120
_DEFAULT_MAX_CONCURRENCY = 32
_MAX_CONCURRENCY = 256
_MAX_AUTH_SUBJECT_LEN = 128


@dataclass(frozen=True)
class ServerConfig:
    """Top-level configuration with bounded resource and timeout settings."""

    log_level: str = "INFO"
    request_timeout_seconds: int = _DEFAULT_TIMEOUT
    max_concurrent_requests: int = _DEFAULT_MAX_CONCURRENCY
    github_token: SecretStr | None = None
    auth_token: SecretStr | None = None
    auth_subject_id: str = "local-operator"
    require_authentication: bool = False

    def __post_init__(self) -> None:
        if self.log_level not in _VALID_LOG_LEVELS:
            raise InvalidConfigurationError(
                f"log_level must be one of {sorted(_VALID_LOG_LEVELS)}, got {self.log_level!r}"
            )
        if not 1 <= self.request_timeout_seconds <= _MAX_TIMEOUT:
            raise InvalidConfigurationError(
                f"request_timeout_seconds must be between 1 and {_MAX_TIMEOUT}"
            )
        if not 1 <= self.max_concurrent_requests <= _MAX_CONCURRENCY:
            raise InvalidConfigurationError(
                f"max_concurrent_requests must be between 1 and {_MAX_CONCURRENCY}"
            )
        subject = self.auth_subject_id.strip()
        if not subject or len(subject) > _MAX_AUTH_SUBJECT_LEN:
            raise InvalidConfigurationError(
                "auth_subject_id must be a non-empty string up to "
                f"{_MAX_AUTH_SUBJECT_LEN} characters"
            )
        object.__setattr__(self, "auth_subject_id", subject)
        if self.require_authentication and (
            self.auth_token is None or not self.auth_token.get_secret_value()
        ):
            raise InvalidConfigurationError(
                "require_authentication=true requires YASIN_MCP_AUTH_TOKEN to be set"
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
        raise InvalidConfigurationError(f"Environment variable {name} must be an integer") from None


def _env_secret(name: str) -> SecretStr | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    return SecretStr(raw)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise InvalidConfigurationError(
        f"Environment variable {name} must be a boolean (true/false)"
    )


def load_config() -> ServerConfig:
    """Build validated configuration from environment variables."""
    return ServerConfig(
        log_level=_env_str("YASIN_MCP_LOG_LEVEL", "INFO").upper(),
        request_timeout_seconds=_env_int("YASIN_MCP_REQUEST_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT),
        max_concurrent_requests=_env_int(
            "YASIN_MCP_MAX_CONCURRENT_REQUESTS", _DEFAULT_MAX_CONCURRENCY
        ),
        github_token=_env_secret("YASIN_MCP_GITHUB_TOKEN"),
        auth_token=_env_secret("YASIN_MCP_AUTH_TOKEN"),
        auth_subject_id=_env_str("YASIN_MCP_AUTH_SUBJECT", "local-operator"),
        require_authentication=_env_bool("YASIN_MCP_REQUIRE_AUTH", False),
    )
