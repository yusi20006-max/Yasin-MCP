"""Diagnostics boundary tests."""

from __future__ import annotations

from yasin_mcp.capabilities.registry import CapabilityRegistry
from yasin_mcp.diagnostics.health import DiagnosticsAdapter
from yasin_mcp.version import EvidenceStatus


def test_health_is_unresolved_without_operations() -> None:
    result = DiagnosticsAdapter(registry=CapabilityRegistry()).get_health()
    assert result.status == "unresolved"
    assert result.evidence_status is EvidenceStatus.UNRESOLVED


def test_public_project_health_is_confirmed() -> None:
    adapter = DiagnosticsAdapter(
        registry=CapabilityRegistry(),
        project_health=lambda: {"status": "healthy", "version": "1"},
    )
    result = adapter.get_health()
    assert result.status == "healthy"
    assert result.evidence_status is EvidenceStatus.CONFIRMED


def test_capability_snapshot_is_deterministic() -> None:
    result = DiagnosticsAdapter(registry=CapabilityRegistry()).get_capabilities()
    assert result["capabilities"] == []


def test_diagnostics_do_not_require_operations() -> None:
    result = DiagnosticsAdapter(registry=CapabilityRegistry()).get_diagnostics()
    assert result.health.status == "unresolved"
    assert result.diagnostics["status"] == "unresolved"


def test_optional_operations_contract_is_consumed_read_only() -> None:
    class Operations:
        def health(self):
            return {"status": "healthy"}

        def diagnostics(self):
            return {"checks": 3}

    result = DiagnosticsAdapter(
        registry=CapabilityRegistry(), operations=Operations()
    ).get_diagnostics()
    assert result.health.status == "healthy"
    assert result.diagnostics == {"checks": 3}
