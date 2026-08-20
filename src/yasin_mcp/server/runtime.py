"""Runnable MCP server runtime boundary.

Issue #4 deliberately exposes only the stdio transport. Remote HTTP serving
can be added later after authentication and transport-security policy are
explicitly designed. The runtime contains no domain tools yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from mcp.server import MCPServer

from yasin_mcp.capabilities.registry import (
    CapabilityCatalog,
    CapabilityRegistry,
    discover_capabilities,
)
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.version import __version__

SERVER_NAME: Final[str] = "Yasin-MCP"
TRANSPORT_STDIO: Final[Literal["stdio"]] = "stdio"


@dataclass(frozen=True)
class ServerRuntime:
    """Owns server construction and transport lifecycle configuration."""

    config: ServerConfig
    server: MCPServer[object]
    registry: CapabilityRegistry

    @classmethod
    def create(
        cls,
        config: ServerConfig | None = None,
        registry: CapabilityRegistry | None = None,
    ) -> ServerRuntime:
        """Construct an empty, policy-safe MCP server."""
        resolved_config = config if config is not None else ServerConfig()
        resolved_registry = registry if registry is not None else CapabilityRegistry()
        server = MCPServer(
            SERVER_NAME,
            description="AI/Agent-facing access layer for the Yasin ecosystem",
            version=__version__,
        )
        return cls(resolved_config, server, resolved_registry)

    def capability_catalog(self) -> CapabilityCatalog:
        """Return the current deterministic capability discovery snapshot."""
        return discover_capabilities(self.registry)

    def run_stdio(self) -> None:
        """Run the server over the standard MCP stdio transport."""
        self.server.run(transport=TRANSPORT_STDIO)
