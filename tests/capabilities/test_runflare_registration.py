from yasin_mcp.capabilities.registry import CapabilityRegistry
from yasin_mcp.capabilities.runflare_registration import (
    RUNFLARE_CAPABILITY_DEFINITIONS,
    register_runflare_capabilities,
)
from yasin_mcp.governance.types import RiskLevel


def test_registers_all_scoped_runflare_capabilities() -> None:
    registry = CapabilityRegistry()
    assert register_runflare_capabilities(registry) == 7

    names = {item.name for item in registry.all()}
    assert names == {
        "runflare_status",
        "runflare_events",
        "runflare_logs",
        "runflare_deploy",
        "runflare_start",
        "runflare_restart",
        "runflare_stop",
    }


def test_runflare_mutations_are_governed_as_mutation_risk() -> None:
    registry = CapabilityRegistry()
    register_runflare_capabilities(registry)

    risks = {item.name: item.risk for item in registry.all()}
    assert risks["runflare_status"] is RiskLevel.READ_ONLY
    assert risks["runflare_events"] is RiskLevel.READ_ONLY
    assert risks["runflare_logs"] is RiskLevel.READ_ONLY
    assert risks["runflare_release"] is RiskLevel.MUTATION
    assert risks["runflare_start"] is RiskLevel.MUTATION
    assert risks["runflare_restart"] is RiskLevel.MUTATION
    assert risks["runflare_stop"] is RiskLevel.MUTATION


def test_every_runflare_definition_has_closed_input_schema() -> None:
    for definition in RUNFLARE_CAPABILITY_DEFINITIONS:
        assert definition.input_schema["type"] == "object"
        assert definition.input_schema["additionalProperties"] is False


def test_no_generic_command_capability_is_registered() -> None:
    registry = CapabilityRegistry()
    register_runflare_capabilities(registry)
    assert all("command" not in item.name.lower() for item in registry.all())
