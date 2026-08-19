"""Minimal capability descriptor.

Issue #1 scope: only the identity/kind data model, validated against
the policy boundary at construction time. Full capability discovery
(Issue #2) and actual tool/resource implementations (Issue #4+) are
out of scope here -- this only establishes that a capability cannot
even be *described* with a forbidden name or as mutating in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass

from yasin_mcp.policies.policy import (
    CapabilityKind,
    check_capability_name_allowed,
    check_mutation_allowed,
)


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Identity and safety metadata for a single MCP capability.

    Validated eagerly: constructing a CapabilityDescriptor with a
    forbidden name or a mutating capability during Phase 1 raises
    PolicyDeniedError immediately, rather than allowing it to exist
    and only failing later at registration or invocation time.
    """

    name: str
    kind: CapabilityKind
    description: str
    is_mutating: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("CapabilityDescriptor.name must not be empty")
        if not self.description or not self.description.strip():
            raise ValueError("CapabilityDescriptor.description must not be empty")
        check_capability_name_allowed(self.name)
        check_mutation_allowed(self.is_mutating)
