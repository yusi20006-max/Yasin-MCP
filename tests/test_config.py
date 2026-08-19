import os
from unittest.mock import patch

import pytest

from yasin_mcp.config.config import (
    InvalidConfigurationError,
    SecretStr,
    ServerConfig,
    load_config,
)


def test_defaults():
    config = ServerConfig()
    assert config.log_level == "INFO"
    assert config.request_timeout_seconds == 30
    assert config.github_token is None


def test_rejects_invalid_log_level():
    with pytest.raises(InvalidConfigurationError):
        ServerConfig(log_level="NOT_A_LEVEL")


def test_rejects_non_positive_timeout():
    with pytest.raises(InvalidConfigurationError):
        ServerConfig(request_timeout_seconds=0)


def test_load_config_defaults():
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
    assert config.log_level == "INFO"
    assert config.github_token is None


def test_load_config_env_override():
    env = {
        "YASIN_MCP_LOG_LEVEL": "DEBUG",
        "YASIN_MCP_REQUEST_TIMEOUT_SECONDS": "60",
    }
    with patch.dict(os.environ, env, clear=True):
        config = load_config()
    assert config.log_level == "DEBUG"
    assert config.request_timeout_seconds == 60


def test_load_config_invalid_timeout_env_raises():
    with patch.dict(os.environ, {"YASIN_MCP_REQUEST_TIMEOUT_SECONDS": "abc"}, clear=True):
        with pytest.raises(InvalidConfigurationError):
            load_config()


def test_github_token_loaded_from_env():
    with patch.dict(os.environ, {"YASIN_MCP_GITHUB_TOKEN": "ghp_secret123"}, clear=True):
        config = load_config()
    assert config.github_token is not None
    assert config.github_token.get_secret_value() == "ghp_secret123"


def test_github_token_absent_by_default():
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
    assert config.github_token is None


# -- SecretStr redaction (critical: must never leak in repr/str/logs) ------


def test_secret_str_repr_does_not_contain_value():
    secret = SecretStr("super-secret-token")
    assert "super-secret-token" not in repr(secret)


def test_secret_str_str_does_not_contain_value():
    secret = SecretStr("super-secret-token")
    assert "super-secret-token" not in str(secret)


def test_secret_str_get_secret_value_returns_real_value():
    secret = SecretStr("super-secret-token")
    assert secret.get_secret_value() == "super-secret-token"


def test_secret_str_bool_true_when_set():
    assert bool(SecretStr("x")) is True


def test_secret_str_bool_false_when_empty():
    assert bool(SecretStr("")) is False


def test_config_repr_does_not_leak_token():
    config = ServerConfig(github_token=SecretStr("ghp_leaked_if_broken"))
    assert "ghp_leaked_if_broken" not in repr(config)
