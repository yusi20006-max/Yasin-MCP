"""Runnable MCP server runtime boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, Literal

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
from yasin_mcp.governance.audit import AuditRecorder, LoggingAuditRecorder
from yasin_mcp.governance.catalog import ToolRiskCatalog
from yasin_mcp.governance.gate import GovernanceGate
from yasin_mcp.governance.policy import DefaultConservativePolicy, GovernancePolicy
from yasin_mcp.governance.types import RiskLevel
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


def _catalog_from_registry(registry: CapabilityRegistry) -> ToolRiskCatalog:
    catalog = ToolRiskCatalog()
    for contract in registry.all():
        risk = getattr(contract, "risk", RiskLevel.READ_ONLY)
        if not isinstance(risk, RiskLevel):
            risk = RiskLevel.READ_ONLY
        catalog.register(contract.name, risk)
    return catalog


@dataclass(frozen=True)
class ServerRuntime:
    """Owns server construction, capability registration, governance, and transport."""

    config: ServerConfig
    server: MCPServer[object]
    registry: CapabilityRegistry
    governance: GovernanceGate
    operations_available: bool = False

    @classmethod
    def create(
        cls,
        config: ServerConfig | None = None,
        registry: CapabilityRegistry | None = None,
        operations_adapter: OperationsAdapter | None = None,
        docs_adapter: YasinDocsAdapter | None = None,
        github_adapter: GitHubAdapter | None = None,
        policy: GovernancePolicy | None = None,
        auditor: AuditRecorder | None = None,
        governance: GovernanceGate | None = None,
    ) -> ServerRuntime:
        """Construct the MCP server, register tools, and wrap them with governance."""
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

        register_docs_tools(resolved_registry)
        register_github_tools(resolved_registry)
        register_registry_tools(resolved_registry)
        operations_registered = register_operations_tools(resolved_registry, ops_adapter)

        risk_catalog = _catalog_from_registry(resolved_registry)
        gate = governance or GovernanceGate(
            risk_catalog,
            policy=policy or DefaultConservativePolicy(),
            auditor=auditor or LoggingAuditRecorder(),
        )
        for name in risk_catalog.known_names():
            if name not in gate.catalog:
                gate.catalog.register(name, risk_catalog.resolve(name).risk)

        def add_governed(fn: Callable[..., Any], name: str) -> None:
            server.add_tool(gate.wrap_tool(name, fn), name=name, structured_output=True)

        docs_tools = DocsToolset(docs)
        add_governed(docs_tools.list_documents, TOOL_LIST_DOCS)
        add_governed(docs_tools.get_document, TOOL_GET_DOC)
        add_governed(docs_tools.search, TOOL_SEARCH_DOCS)
        add_governed(docs_tools.list_adrs, TOOL_LIST_ADRS)
        add_governed(docs_tools.get_adr, TOOL_GET_ADR)
        add_governed(docs_tools.list_architecture, TOOL_LIST_ARCHITECTURE)
        add_governed(docs_tools.get_project_architecture, TOOL_GET_PROJECT_ARCHITECTURE)

        gh = github_adapter
        if gh is None:
            gh = GitHubAdapter(
                token=resolved_config.github_token,
                timeout_seconds=resolved_config.request_timeout_seconds,
            )
        gh_tools = GitHubToolset(gh)
        add_governed(gh_tools.get_repository, TOOL_GET_REPO)
        add_governed(gh_tools.list_issues, TOOL_LIST_ISSUES)
        add_governed(gh_tools.get_issue, TOOL_GET_ISSUE)
        add_governed(gh_tools.list_pull_requests, TOOL_LIST_PRS)
        add_governed(gh_tools.get_pull_request, TOOL_GET_PR)
        add_governed(gh_tools.list_commits, TOOL_LIST_COMMITS)
        add_governed(gh_tools.get_commit_status, TOOL_COMMIT_STATUS)
        add_governed(gh_tools.list_workflow_runs, TOOL_LIST_WORKFLOWS)
        add_governed(gh_tools.list_branches, TOOL_LIST_BRANCHES)
        add_governed(gh_tools.list_releases, TOOL_LIST_RELEASES)

        reg = ProjectRegistryAdapter(docs)
        reg_tools = RegistryToolset(reg)
        add_governed(reg_tools.list_projects, TOOL_LIST_PROJECTS)
        add_governed(reg_tools.get_project, TOOL_GET_PROJECT)
        add_governed(reg_tools.list_dependencies, TOOL_LIST_DEPS)

        if operations_registered:
            toolset = OperationsToolset(ops_adapter)
            add_governed(toolset.list_services, TOOL_LIST_SERVICES)
            add_governed(toolset.service_status, TOOL_SERVICE_STATUS)
            add_governed(toolset.health, TOOL_HEALTH)
            add_governed(toolset.diagnostics, TOOL_DIAGNOSTICS)

        return cls(
            resolved_config,
            server,
            resolved_registry,
            gate,
            operations_available=operations_registered,
        )

    def surface_info(self) -> dict[str, object]:
        meta = surface_metadata()
        meta["operations_available"] = self.operations_available
        meta["governance"] = "centralized"
        return meta

    def capability_catalog(self) -> CapabilityCatalog:
        return discover_capabilities(self.registry)

    def run_stdio(self) -> None:
        self.server.run(transport=TRANSPORT_STDIO)
