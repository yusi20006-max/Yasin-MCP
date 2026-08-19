"""Deny-by-default policy boundary.

This module is the single place that decides whether a capability
name/kind is allowed to exist in this server at all. It is
deliberately conservative: anything not explicitly recognized as
safe is denied, and a fixed list of forbidden name patterns is
checked first and can never be overridden by configuration.

This exists so that no future tool/resource -- however it is
named -- can accidentally expose shell execution, arbitrary command
execution, filesystem mutation, or an arbitrary API passthrough
through this server, even by naming mistake.
"""

from __future__ import annotations

import re
from enum import Enum

from yasin_mcp.errors.errors import PolicyDeniedError


class CapabilityKind(str, Enum):
    """What kind of MCP capability a registered item is."""

    TOOL = "tool"
    RESOURCE = "resource"


# Matches on capability *names* is deliberately broad/substring-based
# (not just exact match) so a name like "run_shell_command" or
# "execute_arbitrary" is caught even if it isn't exactly "shell" or
# "execute". This trades a small risk of over-blocking a legitimate
# future name for a much lower risk of a dangerous name slipping
# through by accident.
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

# Phase 1 is read-only end to end: no capability kind or name may be
# registered that implies a mutation, regardless of what a future
# domain adapter might want. This flag exists so later phases have
# one obvious switch to flip (and audit) rather than needing to hunt
# down every call site.
PHASE_1_READ_ONLY = True


def check_capability_name_allowed(name: str) -> None:
    """Raise PolicyDeniedError if name matches a forbidden pattern.

    This check runs before a capability can be registered anywhere
    in the server (see capabilities/registry.py) and cannot be
    bypassed by configuration.
    """
    for pattern in _FORBIDDEN_NAME_PATTERNS:
        if pattern.search(name):
            raise PolicyDeniedError(
                f"Capability name {name!r} matches a forbidden pattern "
                f"({pattern.pattern!r}) and cannot be registered.",
                details={"name": name, "pattern": pattern.pattern},
            )


def check_mutation_allowed(is_mutating: bool) -> None:
    """Raise PolicyDeniedError if a mutating capability is attempted
    while PHASE_1_READ_ONLY is in effect."""
    if is_mutating and PHASE_1_READ_ONLY:
        raise PolicyDeniedError(
            "Mutating capabilities are not permitted in Phase 1 (read-only server).",
            details={"phase_1_read_only": True},
        )
