from dataclasses import dataclass

from yasin_mcp.providers.runflare.client import CLIResult
from yasin_mcp.tools.runflare import (
    TOOL_DEPLOY,
    TOOL_EVENTS,
    TOOL_LOGS,
    TOOL_RESTART,
    TOOL_START,
    TOOL_STATUS,
    RunflareToolset,
    tool_definitions,
)


@dataclass
class FakeRunflareCLI:
    calls: list[str]

    def status(self) -> CLIResult:
        self.calls.append("status")
        return CLIResult(0, "status", "")

    def events(self) -> CLIResult:
        self.calls.append("events")
        return CLIResult(0, "events", "")

    def logs(self) -> CLIResult:
        self.calls.append("logs")
        return CLIResult(0, "logs", "")

    def deploy(self) -> CLIResult:
        self.calls.append("deploy")
        return CLIResult(0, "deploy", "")

    def start(self) -> CLIResult:
        self.calls.append("start")
        return CLIResult(0, "start", "")

    def restart(self) -> CLIResult:
        self.calls.append("restart")
        return CLIResult(0, "restart", "")


def test_scoped_definitions_are_closed_and_explicit() -> None:
    names = [item.name for item in tool_definitions()]
    assert names == [
        TOOL_STATUS,
        TOOL_EVENTS,
        TOOL_LOGS,
        TOOL_DEPLOY,
        TOOL_START,
        TOOL_RESTART,
    ]
    assert all(
        item.input_schema["additionalProperties"] is False
        for item in tool_definitions()
    )


def test_each_tool_calls_one_hardcoded_provider_operation() -> None:
    fake = FakeRunflareCLI([])
    tools = RunflareToolset(fake)

    assert tools.status()["stdout"] == "status"
    assert tools.events()["stdout"] == "events"
    assert tools.logs()["stdout"] == "logs"
    assert tools.deploy()["stdout"] == "deploy"
    assert tools.start()["stdout"] == "start"
    assert tools.restart()["stdout"] == "restart"
    assert fake.calls == ["status", "events", "logs", "deploy", "start", "restart"]


def test_no_generic_command_tool_exists() -> None:
    names = [item.name for item in tool_definitions()]
    assert all("command" not in name.lower() for name in names)
    assert all("shell" not in name.lower() for name in names)
