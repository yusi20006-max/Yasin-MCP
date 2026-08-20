"""Tests for the Phase 0.2 protocol contract boundary."""

from __future__ import annotations

import pytest

from yasin_mcp.capabilities.registry import (
    CapabilityCatalog,
    CapabilityRegistry,
    descriptor_for,
    discover_capabilities,
)
from yasin_mcp.errors.errors import McpError, PolicyDeniedError, ValidationError
from yasin_mcp.protocol.contracts import (
    CONTRACT_VERSION,
    CURRENT_PROTOCOL_VERSION,
    CapabilityContract,
    CapabilityScope,
    ProtocolVersion,
    ServerIdentity,
)
from yasin_mcp.protocol.errors import ErrorResponse
from yasin_mcp.version import EvidenceStatus


def contract(name: str, scope: CapabilityScope = CapabilityScope.TOOL) -> CapabilityContract:
    descriptor = descriptor_for(name, scope.value, f"{name} capability")
    return CapabilityContract(
        descriptor=descriptor,
        scope=scope,
        input_schema={"type": "object"},
    )


def test_protocol_version_defaults_are_current() -> None:
    version = ProtocolVersion()
    assert version.protocol == CURRENT_PROTOCOL_VERSION
    assert version.contract == CONTRACT_VERSION
    assert version.as_dict() == {
        "protocol": CURRENT_PROTOCOL_VERSION,
        "contract": CONTRACT_VERSION,
    }


def test_identity_defaults() -> None:
    identity = ServerIdentity()
    assert identity.as_dict() == {"name": "Yasin-MCP", "version": "0.1.0"}


@pytest.mark.parametrize("protocol,contract_version", [("", "1.0"), ("2026-07-28", "")])
def test_empty_versions_are_rejected(protocol: str, contract_version: str) -> None:
    with pytest.raises(ValidationError):
        ProtocolVersion(protocol=protocol, contract=contract_version)


def test_scope_must_match_descriptor_kind() -> None:
    descriptor = descriptor_for("read_docs", "tool", "Read documentation")
    with pytest.raises(ValidationError):
        CapabilityContract(descriptor=descriptor, scope=CapabilityScope.RESOURCE)


def test_registry_rejects_duplicates() -> None:
    registry = CapabilityRegistry()
    registry.register(contract("alpha"))
    with pytest.raises(ValidationError):
        registry.register(contract("alpha"))


def test_registry_get_missing_is_structured_error() -> None:
    with pytest.raises(ValidationError):
        CapabilityRegistry().get("missing")


def test_discovery_is_deterministic_and_sorted() -> None:
    registry = CapabilityRegistry()
    registry.register(contract("zeta"))
    registry.register(contract("alpha"))
    catalog = discover_capabilities(registry)

    assert isinstance(catalog, CapabilityCatalog)
    assert [item.name for item in catalog.capabilities] == ["alpha", "zeta"]
    assert catalog.as_dict()["protocol"] == {
        "protocol": CURRENT_PROTOCOL_VERSION,
        "contract": CONTRACT_VERSION,
    }


def test_capability_contract_serialization_contains_safety_metadata() -> None:
    item = contract("read_docs")
    payload = item.as_dict()
    assert payload["name"] == "read_docs"
    assert payload["kind"] == "tool"
    assert payload["read_only"] is True
    assert payload["evidence_status"] == EvidenceStatus.CONFIRMED.value


def test_mutating_contract_cannot_be_constructed() -> None:
    with pytest.raises(PolicyDeniedError):
        descriptor_for("update_docs", "tool", "Update docs", is_mutating=True)


def test_forbidden_capability_name_is_rejected() -> None:
    with pytest.raises(PolicyDeniedError):
        descriptor_for("execute_tool", "tool", "Unsafe")


def test_error_response_from_structured_error() -> None:
    error = McpError(
        category=__import__(
            "yasin_mcp.errors.errors", fromlist=["ErrorCategory"]
        ).ErrorCategory.NOT_FOUND,
        message="missing",
        details={"resource": "docs"},
    )
    response = ErrorResponse.from_error(error)
    assert response.as_dict() == {
        "error": {"code": "not_found", "message": "missing", "details": {"resource": "docs"}}
    }
