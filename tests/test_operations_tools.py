from unittest.mock import MagicMock

import pytest

from yasin_mcp.adapters.operations import (
    OPERATION_DIAGNOSTICS,
    OPERATION_HEALTH_CHECK,
    OPERATION_LIST_SERVICES,
    OPERATION_SERVICE_STATUS,
    OperationsResult,
)
from yasin_mcp.errors.errors import ValidationError
from yasin_mcp.tools.operations import (
    OPERATIONS_TOOL_DEFINITIONS,
    TOOL_DIAGNOSTICS,
    TOOL_HEALTH,
    TOOL_LIST_SERVICES,
    TOOL_MAP,
    TOOL_SERVICE_STATUS,
    OperationsToolset,
)
from yasin_mcp.version import EvidenceStatus


def _fake_result(operation: str, data: dict | None = None) -> OperationsResult:
    return OperationsResult(
        operation=operation,
        success=True,
        status="succeeded",
        data=data or {},
        error=None,
        evidence_status=EvidenceStatus.CONFIRMED,
        source="test",
    )


# -- TOOL_MAP contract (the core safety invariant) ---------------------------


def test_tool_map_has_exactly_four_entries():
    assert len(TOOL_MAP) == 4


def test_tool_map_is_entirely_read_only():
    """The single most important safety assertion in this test suite:
    every TOOL_MAP entry must declare safety_class == 'read_only'.
    If this ever fails, a mutating operation has been exposed."""
    for name, entry in TOOL_MAP.items():
        assert entry["safety_class"] == "read_only", f"{name} is not read_only!"


def test_tool_map_operations_match_expected_four():
    operations = {entry["operation"] for entry in TOOL_MAP.values()}
    assert operations == {
        OPERATION_LIST_SERVICES,
        OPERATION_SERVICE_STATUS,
        OPERATION_HEALTH_CHECK,
        OPERATION_DIAGNOSTICS,
    }


def test_tool_map_contains_exact_expected_tool_names():
    assert set(TOOL_MAP.keys()) == {
        TOOL_LIST_SERVICES,
        TOOL_SERVICE_STATUS,
        TOOL_HEALTH,
        TOOL_DIAGNOSTICS,
    }


@pytest.mark.parametrize(
    "mutating_operation",
    [
        "start",
        "stop",
        "restart",
        "deploy",
        "shell",
        "service_start",
        "service_stop",
        "service_restart",
    ],
)
def test_no_mutating_operation_appears_anywhere_in_tool_map(mutating_operation):
    operations_in_map = {entry["operation"] for entry in TOOL_MAP.values()}
    assert mutating_operation not in operations_in_map


def test_tool_definitions_count_matches_tool_map():
    assert len(OPERATIONS_TOOL_DEFINITIONS) == len(TOOL_MAP)


def test_tool_definitions_names_match_tool_map_keys():
    definition_names = {d.name for d in OPERATIONS_TOOL_DEFINITIONS}
    assert definition_names == set(TOOL_MAP.keys())


def test_no_tool_definition_input_schema_accepts_operation_or_safety_class():
    """Structural guarantee: no tool's declared input schema allows a
    caller to pass 'operation' or 'safety_class' -- these can only
    ever be the hardcoded TOOL_MAP values."""
    for definition in OPERATIONS_TOOL_DEFINITIONS:
        properties = definition.input_schema.get("properties", {})
        assert "operation" not in properties
        assert "safety_class" not in properties


def test_all_tool_schemas_reject_additional_properties():
    for definition in OPERATIONS_TOOL_DEFINITIONS:
        assert definition.input_schema.get("additionalProperties") is False


# -- OperationsToolset: methods call exactly one hardcoded adapter method ---


def test_list_services_calls_adapter_list_services():
    adapter = MagicMock()
    adapter.list_services.return_value = _fake_result(OPERATION_LIST_SERVICES)
    toolset = OperationsToolset(adapter)

    result = toolset.list_services()

    adapter.list_services.assert_called_once_with()
    assert result["success"] is True


def test_service_status_calls_adapter_service_status_with_name():
    adapter = MagicMock()
    adapter.service_status.return_value = _fake_result(OPERATION_SERVICE_STATUS)
    toolset = OperationsToolset(adapter)

    toolset.service_status("yasin-ai")

    adapter.service_status.assert_called_once_with("yasin-ai")


def test_service_status_rejects_non_string_input():
    adapter = MagicMock()
    toolset = OperationsToolset(adapter)
    with pytest.raises(ValidationError):
        toolset.service_status(12345)  # type: ignore[arg-type]
    adapter.service_status.assert_not_called()


def test_health_calls_adapter_health():
    adapter = MagicMock()
    adapter.health.return_value = _fake_result(OPERATION_HEALTH_CHECK)
    toolset = OperationsToolset(adapter)

    toolset.health()

    adapter.health.assert_called_once_with()


def test_diagnostics_calls_adapter_diagnostics():
    adapter = MagicMock()
    adapter.diagnostics.return_value = _fake_result(OPERATION_DIAGNOSTICS)
    toolset = OperationsToolset(adapter)

    toolset.diagnostics()

    adapter.diagnostics.assert_called_once_with()


def test_toolset_has_no_generic_invoke_method():
    """Structural guarantee: OperationsToolset must not expose any
    method that accepts an arbitrary operation name."""
    toolset = OperationsToolset(MagicMock())
    forbidden_method_names = ("call", "invoke", "execute", "run_operation", "call_operation")
    for name in forbidden_method_names:
        assert not hasattr(toolset, name)


def test_result_dict_includes_evidence_metadata():
    adapter = MagicMock()
    adapter.diagnostics.return_value = _fake_result(
        OPERATION_DIAGNOSTICS, data={"python_version": "3.12"}
    )
    toolset = OperationsToolset(adapter)

    result = toolset.diagnostics()

    assert result["evidence_status"] == "confirmed"
    assert result["source"] == "test"
    assert result["data"] == {"python_version": "3.12"}


def test_available_reflects_adapter_availability():
    adapter = MagicMock()
    adapter.available = True
    toolset = OperationsToolset(adapter)
    assert toolset.available is True

    adapter.available = False
    assert toolset.available is False
