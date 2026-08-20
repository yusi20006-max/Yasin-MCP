"""Runnable MCP server runtime boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from mcp.server import MCPServer

from yasin_mcp.adapters.operations import OperationsAdapter
from yasin_mcp.capabilities.operations_registration import register_operations_tools
from yasin_mcp.capabilities.registry import (
    CapabilityCatalog,
    CapabilityRegistry,
    discover_capabilities,
)
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.tools.operations import (
    TOOL_DIAGNOSTICS,
    TOOL_HEALTH,
    TOOL_LIST_SERVICES,
    TOOL_SERVICE_STATUS,
    OperationsToolset,
)
from yasin_mcp.version import __version__

SERVER_NAME: Final[str] = "Yasin-MCP"
TRANSPORT_STDIO: Final[Literal["stdio"]] = "stdio"


@dataclass(frozen=True)
class ServerRuntime:
    """Owns server construction, capability registration, and transport lifecycle."""

    config: ServerConfig
    server: MCPServer[object]
    registry: CapabilityRegistry

    @classmethod
    def create(
        cls,
        config: ServerConfig | None = None,
        registry: CapabilityRegistry | None = None,
        operations_adapter: OperationsAdapter | None = None,
    ) -> ServerRuntime:
        """Construct the MCP server and conditionally register safe Operations tools."""
        resolved_config = config if config is not None else ServerConfig()
        resolved_registry = registry if registry is not None else CapabilityRegistry()
        adapter = operations_adapter if operations_adapter is not None else OperationsAdapter()

        server = MCPServer(
            SERVER_NAME,
            description="AI/Agent-facing access layer for the Yasin ecosystem",
            version=__version__,
        )

        operations_registered = register_operations_tools(resolved_registry, adapter)
        if operations_registered:
            toolset = OperationsToolset(adapter)
            server.add_tool(toolset.list_services, name=TOOL_LIST_SERVICES, structured_output=True)
            server.add_tool(toolset.service_status, name=TOOL_SERVICE_STATUS, structured_output=True)
            server.add_tool(toolset.health, name=TOOL_HEALTH, structured_output=True)
            server.add_tool(toolset.diagnostics, name=TOOL_DIAGNOSTICS, structured_output=True)

        return cls(resolved_config, server, resolved_registry)

    def capability_catalog(self) -> CapabilityCatalog:
        """Return the current deterministic capability discovery snapshot."""
        return discover_capabilities(self.registry)

    def run_stdio(self) -> None:
        """Run the server over the standard MCP stdio transport."""
        self.server.run(transport=TRANSPORT_STDIO)
