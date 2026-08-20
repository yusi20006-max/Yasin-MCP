from unittest.mock import MagicMock

from yasin_mcp.capabilities.operations_registration import register_operations_tools
from yasin_mcp.capabilities.registry import CapabilityRegistry
from yasin_mcp.tools.operations import TOOL_MAP


def test_registers_all_four_tools_when_available():
    adapter = MagicMock()
    adapter.available = True
    registry = CapabilityRegistry()

    registered = register_operations_tools(registry, adapter)

    assert registered is True
    assert len(registry) == 4
    for tool_name in TOOL_MAP:
        contract = registry.get(tool_name)
        assert contract.as_dict()["read_only"] is True


def test_registers_nothing_when_unavailable():
    adapter = MagicMock()
    adapter.available = False
    registry = CapabilityRegistry()

    registered = register_operations_tools(registry, adapter)

    assert registered is False
    assert len(registry) == 0


def test_unavailable_does_not_raise():
    adapter = MagicMock()
    adapter.available = False
    registry = CapabilityRegistry()

    # Must not raise -- unavailability is a structured, expected outcome.
    register_operations_tools(registry, adapter)


def test_other_capabilities_unaffected_when_operations_unavailable():
    """Confirms that Operations being unavailable does not prevent
    other, unrelated capabilities from being registered."""
    from yasin_mcp.capabilities.registry import descriptor_for
    from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope

    adapter = MagicMock()
    adapter.available = False
    registry = CapabilityRegistry()

    registry.register(
        CapabilityContract(
            descriptor=descriptor_for("get_project", "tool", "unrelated capability"),
            scope=CapabilityScope.TOOL,
        )
    )
    register_operations_tools(registry, adapter)

    assert len(registry) == 1
    assert registry.get("get_project") is not None


def test_registered_contracts_are_all_read_only():
    adapter = MagicMock()
    adapter.available = True
    registry = CapabilityRegistry()

    register_operations_tools(registry, adapter)

    for contract in registry.all():
        assert contract.as_dict()["read_only"] is True
