"""Deny-by-default policy and future mutation safety classes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from yasin_mcp.errors.errors import PolicyDeniedError


class CapabilityKind(str, Enum):
    """What kind of MCP capability a registered item is."""

    TOOL = "tool"
    RESOURCE = "resource"


class SafetyClass(str, Enum):
    """Policy class reserved for explicit future capability governance."""

    READ_ONLY = "read_only"
    PROPOSED_MUTATION = "proposed_mutation"
    CONFIRMED_MUTATION = "confirmed_mutation"
    DENY = "deny"


PHASE_1_READ_ONLY = True

_FORBIDDEN_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"exec", re.IGNORECASE),
    re.compile(r"shell", re.IGNORECASE),
    re.compile(r"command", re.IGNORECASE),
    re.compile(r"^request$", re.IGNORECASE),
    re.compile(r"arbitrary", re.IGNORECASE),
    re.compile(r"filesystem", re.IGNORECASE),
    re.compile(r"\bdeploy", re.IGNORECASE),
    re.compile(r"delete", re.IGNORECASE),
    re.compile(r"^(start|stop|restart)_", re.IGNORECASE),
)


@dataclass(frozen=True)
class PolicyDecision:
    """Auditable result of a capability policy evaluation."""

    allowed: bool
    safety_class: SafetyClass
    reason: str


def check_capability_name_allowed(name: str) -> None:
    """Raise when a capability name matches a permanently forbidden pattern."""
    for pattern in _FORBIDDEN_NAME_PATTERNS:
        if pattern.search(name):
            raise PolicyDeniedError(
                f"Capability name {name!r} matches a forbidden pattern "
                f"({pattern.pattern!r}) and cannot be registered.",
                details={"name": name, "pattern": pattern.pattern},
            )


def check_mutation_allowed(is_mutating: bool) -> None:
    """Reject all mutations while the Phase 1 read-only gate is active."""
    if is_mutating and PHASE_1_READ_ONLY:
        raise PolicyDeniedError(
            "Mutating capabilities are not permitted in Phase 1 (read-only server).",
            details={"phase_1_read_only": True},
        )


def evaluate_policy(
    name: str,
    *,
    is_mutating: bool = False,
    safety_class: SafetyClass = SafetyClass.READ_ONLY,
) -> PolicyDecision:
    """Evaluate a capability without executing it.

    This function is deliberately fail-closed. Future mutation classes are
    represented now so authorization/confirmation can be added without
    changing the contract vocabulary, but they cannot be enabled in Phase 1.
    """
    check_capability_name_allowed(name)
    if safety_class is SafetyClass.DENY:
        return PolicyDecision(False, safety_class, "capability is explicitly denied")
    if is_mutating or safety_class is not SafetyClass.READ_ONLY:
        check_mutation_allowed(True)
    return PolicyDecision(True, SafetyClass.READ_ONLY, "capability is read-only")
