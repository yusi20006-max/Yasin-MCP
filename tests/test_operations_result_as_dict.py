"""Provenance coverage for OperationsResult.as_dict."""

from yasin_mcp.adapters.operations import OperationsResult
from yasin_mcp.version import EvidenceStatus


def test_operations_result_as_dict_provenance() -> None:
    result = OperationsResult(
        operation="health_check",
        success=True,
        status="ok",
        data={"services": 1},
        error=None,
        evidence_status=EvidenceStatus.CONFIRMED,
        source="yasin-operations",
    )
    payload = result.as_dict()
    assert payload["operation"] == "health_check"
    assert payload["success"] is True
    assert payload["evidence_status"] == "confirmed"
    assert payload["provenance"]["source"] == "yasin-operations"
    assert payload["provenance"]["operation"] == "health_check"


def test_operations_result_as_dict_untrusted_envelope() -> None:
    result = OperationsResult(
        operation="health_check",
        success=True,
        status="ok",
        data={"services": 1},
        error=None,
        evidence_status=EvidenceStatus.CONFIRMED,
        source="yasin-operations",
    )
    payload = result.as_dict()
    assert payload["untrusted"] is True
    assert payload["trust"]["source_kind"] == "yasin-operations"
    assert payload["data"] == {"services": 1}
