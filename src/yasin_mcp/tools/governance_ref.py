"""Governance reference capabilities (Stage 11) — not product domain tools."""

from __future__ import annotations

from typing import Any

TOOL_GOV_PING_LOW_RISK = "yasin_gov_ping_low_risk"
TOOL_GOV_APPLY_MARK = "yasin_gov_apply_mark"


class GovernanceReferenceToolset:
    def ping_low_risk(self) -> dict[str, Any]:
        return {"ok": True, "capability": TOOL_GOV_PING_LOW_RISK, "risk": "low_risk"}

    def apply_mark(self, mark: str = "stage11") -> dict[str, Any]:
        if not isinstance(mark, str) or not mark.strip():
            mark = "stage11"
        return {
            "applied": True,
            "mark": mark.strip()[:64],
            "capability": TOOL_GOV_APPLY_MARK,
            "risk": "mutation",
        }
