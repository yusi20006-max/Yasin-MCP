"""Phase-1 capability matrix and evidence-model tests."""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.version import EvidenceStatus


def test_default_runtime_advertises_only_safe_docs_capabilities() -> None:
    runtime = ServerRuntime.create()
    names = [item.name for item in runtime.capability_catalog().capabilities]
    assert names
    assert all(
        name.startswith("yasin_docs_") or name.startswith("yasin_github_")
        for name in names
    )
    assert all("exec" not in name and "shell" not in name for name in names)


def test_evidence_status_is_explicit_for_confirmed_data() -> None:
    registry = CapabilityRegistry()
    assert EvidenceStatus.CONFIRMED.value == "confirmed"
    assert EvidenceStatus.TARGET.value == "target"
    assert EvidenceStatus.PROPOSED.value == "proposed"
    assert EvidenceStatus.UNRESOLVED.value == "unresolved"
