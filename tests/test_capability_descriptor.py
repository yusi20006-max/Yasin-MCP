import pytest

from yasin_mcp.capabilities.descriptor import CapabilityDescriptor
from yasin_mcp.errors.errors import PolicyDeniedError
from yasin_mcp.policies.policy import CapabilityKind


def test_valid_read_only_descriptor():
    desc = CapabilityDescriptor(
        name="get_project",
        kind=CapabilityKind.TOOL,
        description="Fetch a single project's metadata",
    )
    assert desc.name == "get_project"
    assert desc.is_mutating is False


def test_descriptor_rejects_empty_name():
    with pytest.raises(ValueError):
        CapabilityDescriptor(name="", kind=CapabilityKind.TOOL, description="x")


def test_descriptor_rejects_empty_description():
    with pytest.raises(ValueError):
        CapabilityDescriptor(name="x", kind=CapabilityKind.TOOL, description="")


def test_descriptor_rejects_forbidden_name_at_construction():
    with pytest.raises(PolicyDeniedError):
        CapabilityDescriptor(
            name="execute_shell",
            kind=CapabilityKind.TOOL,
            description="dangerous",
        )


def test_descriptor_rejects_mutating_capability_in_phase_1():
    with pytest.raises(PolicyDeniedError):
        CapabilityDescriptor(
            name="update_project",
            kind=CapabilityKind.TOOL,
            description="mutates something",
            is_mutating=True,
        )


def test_resource_kind_descriptor():
    desc = CapabilityDescriptor(
        name="get_doc",
        kind=CapabilityKind.RESOURCE,
        description="Fetch a documentation resource",
    )
    assert desc.kind == CapabilityKind.RESOURCE
