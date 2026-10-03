from __future__ import annotations

from pathlib import Path

from yasin_mcp.tools.runflare import tool_definitions


def test_runflare_release_surface_has_no_generic_execution() -> None:
    source = Path("src/yasin_mcp/tools/runflare.py").read_text(encoding="utf-8").lower()
    assert "run_command" not in source
    assert "shell" not in source


def test_runflare_release_surface_has_closed_inputs() -> None:
    definitions = tool_definitions()
    assert definitions
    for definition in definitions:
        assert definition.input_schema["type"] == "object"
        assert definition.input_schema["properties"] == {}
        assert definition.input_schema["additionalProperties"] is False


def test_runflare_release_surface_excludes_credentials() -> None:
    forbidden = {"token", "password", "secret", "api_key", "authorization"}
    for definition in tool_definitions():
        properties = definition.input_schema.get("properties", {})
        assert not forbidden.intersection(properties)
