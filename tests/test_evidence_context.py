"""Tests for agent evidence context contract."""

from yasin_mcp.contracts.evidence_context import (
    AgentContextBundle,
    ContextSource,
    classify_tool_payload,
)
from yasin_mcp.version import EvidenceStatus


def test_bundle_separates_inferences() -> None:
    source = ContextSource(
        kind="docs",
        identifier="README.md",
        content="hello",
        evidence_status=EvidenceStatus.CONFIRMED,
        provenance={"source": "yasin-docs"},
    )
    bundle = AgentContextBundle(
        query="what is yasin?",
        sources=(source,),
        inferences=("possibly related to MCP",),
        unresolved=("ops status unknown",),
    )
    payload = bundle.as_dict()
    assert payload["sources"][0]["evidence_status"] == "confirmed"
    assert "inferences" in payload


def test_classify_tool_payload() -> None:
    assert classify_tool_payload({"evidence_status": "confirmed"}) is EvidenceStatus.CONFIRMED
    assert classify_tool_payload({}) is EvidenceStatus.UNRESOLVED
    assert classify_tool_payload({"evidence_status": "nope"}) is EvidenceStatus.UNRESOLVED
