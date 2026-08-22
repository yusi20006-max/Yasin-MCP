from __future__ import annotations

import sys

import pytest

from yasin_mcp.server import cli


def test_help_exits_without_starting_server(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["yasin-mcp", "--help"])
    monkeypatch.setattr(cli.ServerRuntime, "create", lambda _config: pytest.fail("server started"))

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 0
    assert "usage: yasin-mcp" in capsys.readouterr().out


def test_version_exits_without_starting_server(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["yasin-mcp", "--version"])
    monkeypatch.setattr(cli.ServerRuntime, "create", lambda _config: pytest.fail("server started"))

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 0
    assert "yasin-mcp " in capsys.readouterr().out


def test_no_arguments_starts_server(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["yasin-mcp"])

    class RuntimeStub:
        def run_stdio(self) -> None:
            calls.append("stdio")

    config = object()
    runtime = RuntimeStub()
    calls: list[str] = []

    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "configure_logging", lambda _log_level: calls.append("logging"))
    monkeypatch.setattr(cli.ServerRuntime, "create", lambda value: runtime if value is config else None)

    cli.main()

    assert calls == ["logging", "stdio"]
