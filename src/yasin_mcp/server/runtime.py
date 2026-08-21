"""Runnable MCP server runtime boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from mcp.server import MCPServer

from yasin_mcp.adapters.docs import YasinDocsAdapter
from yasin_mcp.adapters.github import GitHubAdapter
from yasin_mcp.adapters.operations import OperationsAdapter
from yasin_mcp.adapters.project_registry import ProjectRegistryAdapter
from yasin_mcp.capabilities.docs_registration import register_docs_tools
from yasin_mcp.capabilities.github_registration import register_github_tools
from yasin_mcp.capabilities.operations_registration import register_operations_tools
from yasin_mcp.capabilities.registry import (
    CapabilityCatalog,
    CapabilityRegistry,
    discover_capabilities,
)
from yasin_mcp.capabilities.registry_registration import register_registry_tools
from yasin_mcp.capabilities.surface import surface_metadata
from yasin_mcp.config.config import ServerConfig
from yasin_mcp.tools.docs import (
    TOOL_GET_ADR,
    TOOL_GET_DOC,
    TOOL_GET_PROJECT_ARCHITECTURE,
    TOOL_LIST_ADRS,
    TOOL_LIST_ARCHITECTURE,
    TOOL_LIST_DOCS,
    TOOL_SEARCH_DOCS,
    DocsToolset,
)
from yasin_mcp.tools.github import (
    TOOL_COMMIT_STATUS,
    TOOL_GET_ISSUE,
    TOOL_GET_PR,
    TOOL_GET_REPO,
    TOOL_LIST_BRANCHES,
    TOOL_LIST_COMMITS,
    TOOL_LIST_ISSUES,
    TOOL_LIST_PRS,
    TOOL_LIST_RELEASES,
    TOOL_LIST_WORKFLOWS,
    GitHubToolset,
)
from yasin_mcp.tools.operations import (
    TOOL_DIAGNOSTICS,
    TOOL_HEALTH,
    TOOL_LIST_SERVICES,
    TOOL_SERVICE_STATUS,
    OperationsToolset,
)
from yasin_mcp.tools.registry import (
    TOOL_GET_PROJECT,
    TOOL_LIST_DEPS,
    TOOL_LIST_PROJECTS,
    RegistryToolset,
)
from yasin_mcp.version import CAPABILITY_SURFACE_VERSION, __version__

SERVER_NAME: Final[str] = "Yasin-MCP"
TRANSPORT_STDIO: Final[Literal["stdio"]] = "stdio"


@dataclass(frozen=True)
class ServerRuntime:
    """Owns server construction, capability registration, and transport lifecycle."""

    config: ServerConfig
    server: MCPServer[object]
    registry: CapabilityRegistry
    operations_available: bool = False

    @classmethod
    def create(
        cls,
        config: ServerConfig | None = None,
        registry: CapabilityRegistry | None = None,
        operations_adapter: OperationsAdapter | None = None,
        docs_adapter: YasinDocsAdapter | None = None,
        github_adapter: GitHubAdapter | None = None,
    ) -> ServerRuntime:
        """Construct the MCP server and register safe read-only tools."""
        resolved_config = config if config is not None else ServerConfig()
        resolved_registry = registry if registry is not None else CapabilityRegistry()
        ops_adapter = operations_adapter if operations_adapter is not None else OperationsAdapter()
        docs = docs_adapter
        if docs is None:
            docs = YasinDocsAdapter(
                token=resolved_config.github_token,
                timeout_seconds=resolved_config.request_timeout_seconds,
            )

        server = MCPServer(
            SERVER_NAME,
            description=(
                "AI/Agent-facing access layer for the Yasin ecosystem "
                f"(capability surface {CAPABILITY_SURFACE_VERSION})"
            ),
            version=__version__,
        )

        # YASIN-DOCS tools are always registered (public GitHub contract).
        register_docs_tools(resolved_registry)
        docs_tools = DocsToolset(docs)
        server.add_tool(docs_tools.list_documents, name=TOOL_LIST_DOCS, structured_output=True)
        server.add_tool(docs_tools.get_document, name=TOOL_GET_DOC, structured_output=True)
        server.add_tool(docs_tools.search, name=TOOL_SEARCH_DOCS, structured_output=True)
        server.add_tool(docs_tools.list_adrs, name=TOOL_LIST_ADRS, structured_output=True)
        server.add_tool(docs_tools.get_adr, name=TOOL_GET_ADR, structured_output=True)
        server.add_tool(
            docs_tools.list_architecture, name=TOOL_LIST_ARCHITECTURE, structured_output=True
        )
        server.add_tool(
            docs_tools.get_project_architecture,
            name=TOOL_GET_PROJECT_ARCHITECTURE,
            structured_output=True,
        )

        # GitHub tools are always registered (public API; optional token).
        register_github_tools(resolved_registry)
        gh = github_adapter
        if gh is None:
            gh = GitHubAdapter(
                token=resolved_config.github_token,
                timeout_seconds=resolved_config.request_timeout_seconds,
            )
        gh_tools = GitHubToolset(gh)
        server.add_tool(gh_tools.get_repository, name=TOOL_GET_REPO, structured_output=True)
        server.add_tool(gh_tools.list_issues, name=TOOL_LIST_ISSUES, structured_output=True)
        server.add_tool(gh_tools.get_issue, name=TOOL_GET_ISSUE, structured_output=True)
        server.add_tool(gh_tools.list_pull_requests, name=TOOL_LIST_PRS, structured_output=True)
        server.add_tool(gh_tools.get_pull_request, name=TOOL_GET_PR, structured_output=True)
        server.add_tool(gh_tools.list_commits, name=TOOL_LIST_COMMITS, structured_output=True)
        server.add_tool(gh_tools.get_commit_status, name=TOOL_COMMIT_STATUS, structured_output=True)
        server.add_tool(
            gh_tools.list_workflow_runs, name=TOOL_LIST_WORKFLOWS, structured_output=True
        )
        server.add_tool(gh_tools.list_branches, name=TOOL_LIST_BRANCHES, structured_output=True)
        server.add_tool(gh_tools.list_releases, name=TOOL_LIST_RELEASES, structured_output=True)

        # Project registry tools (sourced from YASIN-DOCS registry file).
        register_registry_tools(resolved_registry)
        reg = ProjectRegistryAdapter(docs)
        reg_tools = RegistryToolset(reg)
        server.add_tool(reg_tools.list_projects, name=TOOL_LIST_PROJECTS, structured_output=True)
        server.add_tool(reg_tools.get_project, name=TOOL_GET_PROJECT, structured_output=True)
        server.add_tool(reg_tools.list_dependencies, name=TOOL_LIST_DEPS, structured_output=True)

        # Operations tools only when the gateway executable is available.
        operations_registered = register_operations_tools(resolved_registry, ops_adapter)
        if operations_registered:
            toolset = OperationsToolset(ops_adapter)
            server.add_tool(toolset.list_services, name=TOOL_LIST_SERVICES, structured_output=True)
            server.add_tool(
                toolset.service_status, name=TOOL_SERVICE_STATUS, structured_output=True
            )
            server.add_tool(toolset.health, name=TOOL_HEALTH, structured_output=True)
            server.add_tool(toolset.diagnostics, name=TOOL_DIAGNOSTICS, structured_output=True)

        return cls(
            resolved_config,
            server,
            resolved_registry,
            operations_available=operations_registered,
        )

    def surface_info(self) -> dict[str, object]:
        """Return capability surface compatibility metadata.

        Includes operations_available so clients can discover whether
        the optional Yasin-Operations gateway was registered without
        invoking any tool.
        """
        meta = surface_metadata()
        meta["operations_available"] = self.operations_available
        return meta

    def capability_catalog(self) -> CapabilityCatalog:
        """Return the current deterministic capability discovery snapshot."""
        return discover_capabilities(self.registry)

    def run_stdio(self) -> None:
        """Run the server over the standard MCP stdio transport."""
        self.server.run(transport=TRANSPORT_STDIO)
