"""Deterministic integration test for the Operations MCP path.

Live Hermes -> Yasin-MCP -> Operations adapter -> Yasin-Operations
JSONL gateway -> Yasin-Operations Executor testing is not possible
in this environment: this sandbox has no Hermes installation, no
network access to install one, and no running Yasin-Operations
instance with real services under management. Faking that result
would violate the explicit instruction not to fake live integration
results.

Instead, this test exercises the *real* subprocess transport layer
(OperationsAdapter really spawns a subprocess and really
communicates over stdin/stdout using the JSONL protocol) against a
small fake gateway script that implements the exact wire protocol
Yasin-Operations' JsonlGateway uses (schema_version, request/
response envelope shape, service_available field). This is
deterministic (no external dependency, no network, no timing
flakiness) and proves the transport and parsing logic work
end-to-end, which is what this repository can actually control and
verify. It is not a substitute for a real Yasin-Operations gateway
test, and is not presented as one.
"""

from __future__ import annotations

import stat
import sys
import textwrap
from pathlib import Path

import pytest

from yasin_mcp.adapters.operations import OperationsAdapter
from yasin_mcp.tools.operations import OperationsToolset

_FAKE_GATEWAY_SCRIPT = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import sys

    line = sys.stdin.readline()
    payload = json.loads(line)
    request = payload["request"]
    operation = request["operation"]

    responses = {
        "list_services": {"services": ["yasin-ai", "yasinpress"]},
        "service_status": {"name": request["target_identifier"], "state": "running"},
        "health_check": {"healthy": True},
        "diagnostics": {"python_version": "3.12.0", "operating_system": "Linux"},
    }

    data = responses.get(operation)
    success = data is not None

    response = {
        "schema_version": 1,
        "request_id": request["request_id"],
        "operation_id": "fake-op-1",
        "success": success,
        "status": "succeeded" if success else "failed",
        "data": data or {},
        "error": (
            None
            if success
            else {
                "category": "unsupported_operation",
                "message": operation,
                "details": {},
            }
        ),
        "service_available": True,
    }
    sys.stdout.write(json.dumps(response) + "\\n")
    sys.stdout.flush()
    """
)


@pytest.fixture
def fake_gateway_executable(tmp_path: Path) -> str:
    """A real, executable script implementing the gateway wire protocol.

    Used in place of the real `yasin-operations gateway` command so
    this test has no dependency on Yasin-Operations being installed.
    """
    script_path = tmp_path / "fake-yasin-operations"
    script_path.write_text(_FAKE_GATEWAY_SCRIPT, encoding="utf-8")
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    # The adapter invokes `[executable, "gateway"]`; wrap the fake
    # script so that argv shape is honored without needing a real
    # argparse subcommand structure.
    wrapper_path = tmp_path / "yasin-operations-wrapper"
    wrapper_path.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import sys
            import subprocess
            # Ignore the "gateway" argv[1] the adapter always passes;
            # this fake only implements the gateway subcommand.
            subprocess.run(
                ["{sys.executable}", "{script_path}"],
                stdin=sys.stdin,
                stdout=sys.stdout,
            )
            """
        ),
        encoding="utf-8",
    )
    wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IEXEC)
    return str(wrapper_path)


def test_end_to_end_list_services(fake_gateway_executable: str):
    adapter = OperationsAdapter(executable=fake_gateway_executable)
    toolset = OperationsToolset(adapter)

    result = toolset.list_services()

    assert result["success"] is True
    assert result["data"]["services"] == ["yasin-ai", "yasinpress"]
    assert result["evidence_status"] == "confirmed"


def test_end_to_end_service_status(fake_gateway_executable: str):
    adapter = OperationsAdapter(executable=fake_gateway_executable)
    toolset = OperationsToolset(adapter)

    result = toolset.service_status("yasin-ai")

    assert result["success"] is True
    assert result["data"]["name"] == "yasin-ai"
    assert result["data"]["state"] == "running"


def test_end_to_end_health(fake_gateway_executable: str):
    adapter = OperationsAdapter(executable=fake_gateway_executable)
    toolset = OperationsToolset(adapter)

    result = toolset.health()

    assert result["success"] is True
    assert result["data"]["healthy"] is True


def test_end_to_end_diagnostics(fake_gateway_executable: str):
    adapter = OperationsAdapter(executable=fake_gateway_executable)
    toolset = OperationsToolset(adapter)

    result = toolset.diagnostics()

    assert result["success"] is True
    assert "python_version" in result["data"]


def test_end_to_end_mutation_attempt_is_structurally_impossible(fake_gateway_executable: str):
    """There is no OperationsToolset method that can request a
    mutating operation -- confirmed here by asserting the toolset's
    public surface only contains the four read-only methods, even
    against a real (fake) subprocess transport."""
    adapter = OperationsAdapter(executable=fake_gateway_executable)
    toolset = OperationsToolset(adapter)

    public_methods = {
        name
        for name in dir(toolset)
        if not name.startswith("_") and callable(getattr(toolset, name))
    }
    assert public_methods == {"list_services", "service_status", "health", "diagnostics"}


def test_adapter_is_available_when_fake_executable_present(fake_gateway_executable: str):
    adapter = OperationsAdapter(executable=fake_gateway_executable)
    assert adapter.available is True


def test_adapter_unavailable_with_nonexistent_executable():
    adapter = OperationsAdapter(executable="definitely-not-a-real-command-xyz123")
    assert adapter.available is False
