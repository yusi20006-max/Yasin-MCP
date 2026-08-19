"""Phase 1 integration and security regression matrix."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from yasin_mcp.capabilities.registry import CapabilityRegistry, descriptor_for, discover_capabilities
from yasin_mcp.errors.errors import PolicyDeniedError
from yasin_mcp.policies.policy import SafetyClass, evaluate_policy
from yasin_mcp.protocol.contracts import CapabilityContract, CapabilityScope
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.version import EvidenceStatus


@pytest.mark.parametrize(
    "name",
    ["exec", "shell", "run_command", "delete_repo", "deploy_service", "start_service", "stop_service"],
)
def test_forbidden_capability_names_never_register(name: str) -> None:
    with pytest.raises(PolicyDeniedError):
        descriptor_for(name, "tool", "forbidden")


def test_all_future_mutation_classes_are_denied() -> None:
    for safety_class in SafetyClass:
        if safety_class is not SafetyClass.READ_ONLY:
            if safety_class is SafetyClass.DENY:
                assert evaluate_policy("safe", safety_class=safety_class).allowed is False
            else:
                with pytest.raises(PolicyDeniedError):
                    evaluate_policy("future", safety_class=safety_class)


def test_capability_discovery_matches_registry() -> None:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityContract(
            descriptor=descriptor_for("read_docs", "tool", "Read docs"),
            scope=CapabilityScope.TOOL,
        )
    )
    catalog = discover_capabilities(registry)
    assert [item["name"] for item in catalog.as_dict()["capabilities"]] == ["read_docs"]


def test_empty_runtime_advertises_no_unsafe_capabilities() -> None:
    runtime = ServerRuntime.create()
    names = [item.name for item in runtime.capability_catalog().capabilities]
    assert names == []


def test_evidence_status_is_explicit_for_confirmed_data() -> None:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityContract(
            descriptor=descriptor_for("read_status", "resource", "Read status"),
            scope=CapabilityScope.RESOURCE,
            evidence_status=EvidenceStatus.CONFIRMED,
        )
    )
    assert registry.all()[0].evidence_status is EvidenceStatus.CONFIRMED


def test_no_private_yasin_imports_in_source() -> None:
    root = Path(__file__).parents[1] / "src"
    forbidden_prefixes = ("yasin_core", "yasin_agent", "yasin_ai", "yasinhub", "yasin_operations")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            assert not any(module.startswith(forbidden_prefixes) for module in modules), path
