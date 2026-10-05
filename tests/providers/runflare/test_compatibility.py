from __future__ import annotations

import pytest

from yasin_mcp.providers.runflare.compatibility import probe_compatibility


class FakeCompleted:
    def __init__(self, text: str) -> None:
        self.returncode = 0
        self.stdout = text
        self.stderr = ""


def test_compatibility_probe_is_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[1] == "version":
            return FakeCompleted("Runflare CLI version 1.3.1")
        if args[1] == "--help":
            return FakeCompleted("status deploy event log start restart stop")
        return FakeCompleted("-y --help")

    monkeypatch.setattr(
        "yasin_mcp.providers.runflare.compatibility.subprocess.run",
        fake_run,
    )
    report = probe_compatibility("runflare")
    assert report.compatible
    assert report.version == "Runflare CLI version 1.3.1"
    assert all("deploy" not in call[1:] or "--help" in call for call in calls)
    assert all("version" in call or "--help" in call for call in calls)


def test_compatibility_probe_reports_missing_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args, **kwargs):
        if args[1] == "version":
            return FakeCompleted("Runflare CLI version 1.3.1")
        if args[1] == "--help":
            return FakeCompleted("status event log")
        return FakeCompleted("-y")

    monkeypatch.setattr(
        "yasin_mcp.providers.runflare.compatibility.subprocess.run",
        fake_run,
    )
    report = probe_compatibility("runflare")
    assert not report.compatible
    assert "deploy" in report.missing_commands


def test_compatibility_probe_never_uses_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[bool] = []

    def fake_run(args, **kwargs):
        observed.append(kwargs["shell"])
        return (
            FakeCompleted("Runflare CLI version 1.3.1")
            if args[1] == "version"
            else FakeCompleted("status deploy event log start restart stop -y")
        )

    monkeypatch.setattr(
        "yasin_mcp.providers.runflare.compatibility.subprocess.run",
        fake_run,
    )
    probe_compatibility("runflare")
    assert observed and all(value is False for value in observed)
