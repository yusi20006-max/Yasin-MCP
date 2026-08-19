"""Yasin-MCP: standalone AI/Agent-facing MCP access and integration layer.

Read-only in Phase 1. Does not replace YASIN-DOCS, Yasin-Core,
Yasin-Agent, Yasin-AI, YasinHub, YasinCLI, or Yasin-Operations --
it consumes their public interfaces read-only where such
integration exists (see docs/ for what is implemented vs planned).
"""

from yasin_mcp.version import __version__

__all__ = ["__version__"]
