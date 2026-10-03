from __future__ import annotations

from yasin_mcp.tools.runflare import (
    TOOL_DEPLOY,
    TOOL_EVENTS,
    TOOL_LOGS,
    TOOL_RESTART,
    TOOL_START,
    TOOL_STATUS,
    tool_definitions,
)


def test_hermes_runflare_uses_supported_control_plane_tools() -> None:
    names = {item.name for item in tool_definitions()}
    assert {
        TOOL_STATUS,
        TOOL_EVENTS,
        TOOL_LOGS,
        TOOL_DEPLOY,
        TOOL_START,
        TOOL_RESTART,
    } <= names


def test_hermes_integration_has_no_credential_input_surface() -> None:
    for item in tool_definitions():
        assert item.input_schema["properties"] == {}
        assert item.input_schema["additionalProperties"] is False
