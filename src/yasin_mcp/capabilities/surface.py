"""Capability surface identity for client compatibility checks."""

from __future__ import annotations

from typing import Any

from yasin_mcp.version import CAPABILITY_SURFACE_VERSION, __version__

SURFACE_NAME = "yasin-mcp-read-only"


def surface_metadata() -> dict[str, Any]:
    """Return discoverable package, surface, and protocol-facing identity."""
    return {
        "package_version": __version__,
        "capability_surface_version": CAPABILITY_SURFACE_VERSION,
        "surface_name": SURFACE_NAME,
        "phase": "read_only",
        "always_on_prefixes": [
            "yasin_docs_",
            "yasin_github_",
            "yasin_registry_",
        ],
        "optional_prefixes": [
            "yasin_operations_",
        ],
    }
