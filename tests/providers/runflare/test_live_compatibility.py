"""Opt-in live Runflare checks.

CI never runs these checks. They require an already authenticated official CLI
and an explicitly configured project; they do not mutate Runflare state.
"""

from __future__ import annotations

import os

import pytest

from yasin_mcp.providers.runflare.compatibility import probe_compatibility
from yasin_mcp.providers.runflare.client import RunflareCLI


@pytest.mark.skipif(
    os.getenv("RUNFLARE_LIVE_TESTS") != "1",
    reason="set RUNFLARE_LIVE_TESTS=1 for an authenticated local Runflare CLI",
)
def test_live_cli_compatibility() -> None:
    report = probe_compatibility()
    assert report.compatible, report


@pytest.mark.skipif(
    os.getenv("RUNFLARE_LIVE_TESTS") != "1",
    reason="set RUNFLARE_LIVE_TESTS=1 for an authenticated local Runflare CLI",
)
def test_live_non_destructive_diagnostics() -> None:
    cli = RunflareCLI()
    events = cli.events()
    logs = cli.logs()
    assert events.returncode == 0, events
    assert logs.returncode == 0, logs
