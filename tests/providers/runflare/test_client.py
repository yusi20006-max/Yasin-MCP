import subprocess

import pytest

from yasin_mcp.providers.runflare.client import RunflareCLI
from yasin_mcp.providers.runflare.security import redact, validate_project_dir


def test_redacts_common_secrets() -> None:
    value = "token=abc authorization: Bearer xyz password=secret"
    output = redact(value, 1000)
    assert "abc" not in output
    assert "xyz" not in output
    assert "secret" not in output
    assert "[REDACTED]" in output


def test_requires_project_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RUNFLARE_PROJECT_DIR", raising=False)
    with pytest.raises(ValueError):
        validate_project_dir("")


def test_project_root_boundary(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    project = allowed / "project"
    project.mkdir()
    monkeypatch.setenv("RUNFLARE_ALLOWED_PROJECT_ROOT", str(allowed))
    assert validate_project_dir(str(project)) == project.resolve()
    with pytest.raises(ValueError):
        validate_project_dir(str(tmp_path / "outside"))


def test_rejects_non_runflare_executable(monkeypatch, tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("RUNFLARE_PROJECT_DIR", str(project))
    monkeypatch.setenv("RUNFLARE_BIN", "bash")
    with pytest.raises(ValueError):
        RunflareCLI()


def test_missing_cli_is_reported(monkeypatch, tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("RUNFLARE_PROJECT_DIR", str(project))
    monkeypatch.setenv("RUNFLARE_BIN", "runflare")
    with pytest.raises(RuntimeError, match="not found"):
        RunflareCLI()._run("events", "-y")


def test_null_byte_is_rejected(monkeypatch, tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("RUNFLARE_PROJECT_DIR", str(project))
    cli = RunflareCLI()
    with pytest.raises(ValueError):
        cli._run("events", "bad\x00arg")


def test_timeout_is_bounded(monkeypatch, tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("RUNFLARE_PROJECT_DIR", str(project))
    cli = RunflareCLI()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="runflare", timeout=1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="timed out"):
        cli._run("events", "-y")


def test_stop_is_confirmation_gated(monkeypatch, tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("RUNFLARE_PROJECT_DIR", str(project))
    with pytest.raises(PermissionError):
        RunflareCLI().stop()


def test_redacts_authorization_header_and_x_api_key() -> None:
    output = redact(
        "Authorization: Bearer super-secret x-api-key: hidden-key",
        1000,
    )
    assert "super-secret" not in output
    assert "hidden-key" not in output


def test_rejects_null_project_dir(tmp_path) -> None:
    with pytest.raises(ValueError):
        validate_project_dir(str(tmp_path) + "\x00")


def test_allowed_root_is_required(monkeypatch, tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.delenv("RUNFLARE_ALLOWED_PROJECT_ROOT", raising=False)
    with pytest.raises(ValueError):
        validate_project_dir(str(project))
