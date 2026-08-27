"""Risk metadata catalog for governed tools."""

from __future__ import annotations

from yasin_mcp.governance.types import RiskLevel, ToolIdentity


class ToolRiskCatalog:
    """Maps registered tool names to risk classifications.

    Unknown names resolve to an identity with known=False so policy
    can deny-by-default without inventing risk metadata.
    """

    def __init__(self, entries: dict[str, RiskLevel] | None = None) -> None:
        self._entries: dict[str, RiskLevel] = dict(entries or {})

    def register(self, name: str, risk: RiskLevel) -> None:
        if not name or not name.strip():
            raise ValueError("tool name must not be empty")
        if not isinstance(risk, RiskLevel):
            raise ValueError(f"invalid risk value: {risk!r}")
        self._entries[name] = risk

    def register_many(self, entries: dict[str, RiskLevel]) -> None:
        for name, risk in entries.items():
            self.register(name, risk)

    def resolve(self, name: str, *, description: str = "") -> ToolIdentity:
        risk = self._entries.get(name)
        if risk is None:
            return ToolIdentity(
                name=name,
                risk=RiskLevel.HIGH_RISK,
                description=description,
                known=False,
            )
        return ToolIdentity(
            name=name,
            risk=risk,
            description=description,
            known=True,
        )

    def known_names(self) -> frozenset[str]:
        return frozenset(self._entries)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._entries

    def __len__(self) -> int:
        return len(self._entries)
