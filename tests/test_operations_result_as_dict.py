"""Provenance coverage for OperationsResult.as_dict."""

from __future__ import annotations

from yasin_mcp.adapters.operations import OperationsResult
from yasin_mcp.version import EvidenceStatus


def test_operations_result_as_dict_provenance() -> None:
    result = OperationsResult(
        operation="health_check",
        success=True,
        status="ok",
        data={"healthy": True},
        error=None,
        evidence_status=EvidenceStatus.CONFIRMED,
        source="yasin-operations gateway (yasin-operations)",
    )
    payload = result.as_dict()
    assert payload["evidence_status"] == "confirmed"
    assert payload["provenance"]["source"] == "yasin-operations"
    assert payload["data"]["healthy"] is True
    assert payload["operation"] == "health_check"
