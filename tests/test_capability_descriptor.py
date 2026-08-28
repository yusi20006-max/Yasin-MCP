"""CapabilityDescriptor unit tests."""

from __future__ import annotations

import pytest

from yasin_mcp.capabilities.descriptor import CapabilityDescriptor
from yasin_mcp.errors.errors import PolicyDeniedError
from yasin_mcp.policies.policy import CapabilityKind


def test_valid_tool_descriptor() -> None:
    desc = CapabilityDescriptor(
        name="read_docs",
        kind=CapabilityKind.TOOL,
        description="Read documentation",
    )
    assert desc.name == "read_docs"
    assert desc.is_mutating is False


def test_forbidden_name_rejected() -> None:
    with pytest.raises(PolicyDeniedError):
        CapabilityDescriptor(
            name="execute_shell",
            kind=CapabilityKind.TOOL,
            description="dangerous",
        )


def test_descriptor_allows_mutating_capability_after_stage_11() -> None:
    desc = CapabilityDescriptor(
        name="update_project",
        kind=CapabilityKind.TOOL,
        description="mutates something",
        is_mutating=True,
    )
    assert desc.is_mutating is True


def test_resource_kind_descriptor() -> None:
    desc = CapabilityDescriptor(
        name="get_doc",
        kind=CapabilityKind.RESOURCE,
        description="Fetch a documentation resource",
    )
    assert desc.kind is CapabilityKind.RESOURCE
