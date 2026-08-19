"""Capability registry and deterministic discovery.

The registry is intentionally a pure in-process contract registry. It does not
execute tools, load adapters, or contact external systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from yasin_mcp.capabilities.descriptor import CapabilityDescriptor
from yasin_mcp.errors.errors import ValidationError
from yasin_mcp.protocol.contracts import CapabilityContract, ProtocolVersion, ServerIdentity


@dataclass
class CapabilityRegistry:
    """Register validated capability contracts and expose deterministic snapshots."""

    _items: dict[str, CapabilityContract] = field(default_factory=dict)

    def register(self, contract: CapabilityContract) -> None:
        if contract.name in self._items:
            raise ValidationError(
                f"Capability {contract.name!r} is already registered",
                details={"name": contract.name},
            )
        self._items[contract.name] = contract

    def register_many(self, contracts: Iterable[CapabilityContract]) -> None:
        for contract in contracts:
            self.register(contract)

    def get(self, name: str) -> CapabilityContract:
        try:
            return self._items[name]
        except KeyError as exc:
            raise ValidationError(
                f"Capability {name!r} is not registered", details={"name": name}
            ) from exc

    def all(self) -> tuple[CapabilityContract, ...]:
        return tuple(self._items[name] for name in sorted(self._items))

    def __len__(self) -> int:
        return len(self._items)


@dataclass(frozen=True)
class CapabilityCatalog:
    """Stable discovery snapshot advertised by the protocol boundary."""

    identity: ServerIdentity
    protocol: ProtocolVersion
    capabilities: tuple[CapabilityContract, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "server": self.identity.as_dict(),
            "protocol": self.protocol.as_dict(),
            "capabilities": [item.as_dict() for item in self.capabilities],
        }


def discover_capabilities(
    registry: CapabilityRegistry,
    *,
    identity: ServerIdentity | None = None,
    protocol: ProtocolVersion | None = None,
) -> CapabilityCatalog:
    """Return a deterministic, immutable discovery snapshot."""
    return CapabilityCatalog(
        identity=identity or ServerIdentity(),
        protocol=protocol or ProtocolVersion(),
        capabilities=registry.all(),
    )


def descriptor_for(
    name: str,
    kind: str,
    description: str,
    *,
    is_mutating: bool = False,
) -> CapabilityDescriptor:
    """Convenience factory kept at the contract boundary for future adapters."""
    from yasin_mcp.policies.policy import CapabilityKind

    try:
        capability_kind = CapabilityKind(kind)
    except ValueError as exc:
        raise ValidationError(
            f"Unsupported capability kind {kind!r}", details={"kind": kind}
        ) from exc
    return CapabilityDescriptor(
        name=name,
        kind=capability_kind,
        description=description,
        is_mutating=is_mutating,
    )
