"""Agent context retrieval and evidence contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from yasin_mcp.version import EvidenceStatus


@dataclass(frozen=True)
class ContextSource:
    kind: str
    identifier: str
    content: str
    evidence_status: EvidenceStatus
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "identifier": self.identifier,
            "content": self.content,
            "evidence_status": self.evidence_status.value,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class AgentContextBundle:
    query: str
    sources: tuple[ContextSource, ...]
    inferences: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "sources": [s.as_dict() for s in self.sources],
            "inferences": list(self.inferences),
            "unresolved": list(self.unresolved),
            "evidence_note": (
                "sources carry evidence_status; inferences are not CONFIRMED facts"
            ),
        }


def classify_tool_payload(payload: dict[str, Any]) -> EvidenceStatus:
    raw = payload.get("evidence_status")
    if isinstance(raw, str):
        try:
            return EvidenceStatus(raw)
        except ValueError:
            return EvidenceStatus.UNRESOLVED
    return EvidenceStatus.UNRESOLVED
