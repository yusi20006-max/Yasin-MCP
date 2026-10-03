"""Scoped MCP tools for the Runflare provider with explicit operations only."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from yasin_mcp.providers.runflare.client import CLIResult, RunflareCLI

TOOL_STATUS = "runflare_status"
TOOL_EVENTS = "runflare_events"
TOOL_LOGS = "runflare_logs"
TOOL_DEPLOY = "runflare_deploy"
TOOL_START = "runflare_start"
TOOL_RESTART = "runflare_restart"

_EMPTY_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

RUNFLARE_TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": TOOL_STATUS,
        "description": "Read Runflare project status.",
        "input_schema": _EMPTY_SCHEMA,
    },
    {
        "name": TOOL_EVENTS,
        "description": "Read bounded Runflare project events.",
        "input_schema": _EMPTY_SCHEMA,
    },
    {
        "name": TOOL_LOGS,
        "description": "Read bounded Runflare project logs.",
        "input_schema": _EMPTY_SCHEMA,
    },
    {
        "name": TOOL_DEPLOY,
        "description": "Deploy the configured Runflare project.",
        "input_schema": _EMPTY_SCHEMA,
    },
    {
        "name": TOOL_START,
        "description": "Start the configured Runflare project.",
        "input_schema": _EMPTY_SCHEMA,
    },
    {
        "name": TOOL_RESTART,
        "description": "Restart the configured Runflare project.",
        "input_schema": _EMPTY_SCHEMA,
    },
)


def _result(result: CLIResult) -> dict[str, Any]:
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


class RunflareToolset:
    """Bind each MCP tool to exactly one hardcoded provider operation."""

    def __init__(self, cli: RunflareCLI) -> None:
        self._cli = cli

    def status(self) -> dict[str, Any]:
        return _result(self._cli.status())

    def events(self) -> dict[str, Any]:
        return _result(self._cli.events())

    def logs(self) -> dict[str, Any]:
        return _result(self._cli.logs())

    def deploy(self) -> dict[str, Any]:
        return _result(self._cli.deploy())

    def start(self) -> dict[str, Any]:
        return _result(self._cli.start())

    def restart(self) -> dict[str, Any]:
        return _result(self._cli.restart())


@dataclass(frozen=True)
class RunflareToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, Any]


def tool_definitions() -> tuple[RunflareToolDefinition, ...]:
    return tuple(
        RunflareToolDefinition(
            name=item["name"],
            description=item["description"],
            input_schema=item["input_schema"],
        )
        for item in RUNFLARE_TOOL_DEFINITIONS
    )
