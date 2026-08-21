"""Version and evidence-model metadata.

EvidenceStatus is used throughout later issues to distinguish what a
response actually confirmed (CONFIRMED) versus documented aspiration
(TARGET), a proposal not yet implemented (PROPOSED), or something
that could not be determined (UNRESOLVED). Defined here in Issue #1
so every later adapter/tool can depend on it from the start rather
than each inventing its own status field.
"""

from __future__ import annotations

from enum import Enum

__version__ = "0.1.0"

# Tool/capability surface version for client compatibility checks.
# Bump when always-on tool names/schemas change in a client-visible way.
CAPABILITY_SURFACE_VERSION = "1.1.0"


class EvidenceStatus(str, Enum):
    """How confident a piece of returned information is.

    CONFIRMED: directly observed from a live, authoritative source
    (e.g. a real GitHub API response, a file actually read).
    TARGET: documented intent/architecture, not verified against a
    running system.
    PROPOSED: a suggestion or plan, not yet implemented anywhere.
    UNRESOLVED: could not be determined (source unavailable, missing
    documentation, etc) -- must not be presented as fact.
    """

    CONFIRMED = "confirmed"
    TARGET = "target"
    PROPOSED = "proposed"
    UNRESOLVED = "unresolved"
