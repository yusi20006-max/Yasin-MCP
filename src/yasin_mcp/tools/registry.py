"""Read-only MCP tools over the project registry adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from yasin_mcp.adapters.project_registry import ProjectRegistryAdapter
from yasin_mcp.errors.errors import ValidationError

TOOL_LIST_PROJECTS = "yasin_registry_list_projects"
TOOL_GET_PROJECT = "yasin_registry_get_project"
TOOL_LIST_DEPS = "yasin_registry_list_dependencies"


class RegistryToolset:
    def __init__(self, adapter: ProjectRegistryAdapter) -> None:
        self._adapter = adapter

    def list_projects(self) -> dict[str, Any]:
        projects = self._adapter.list_projects()
        return {
            "projects": [p.as_dict() for p in projects],
            "count": len(projects),
            "evidence_status": "confirmed" if projects else "unresolved",
        }

    def get_project(self, name: str) -> dict[str, Any]:
        if not isinstance(name, str):
            raise ValidationError("name must be a string")
        return self._adapter.get_project(name).as_dict()

    def list_dependencies(self, name: str) -> dict[str, Any]:
        if not isinstance(name, str):
            raise ValidationError("name must be a string")
        return self._adapter.list_dependencies(name)


@dataclass(frozen=True)
class RegistryToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, Any]


REGISTRY_TOOL_DEFINITIONS: tuple[RegistryToolDefinition, ...] = (
    RegistryToolDefinition(
        name=TOOL_LIST_PROJECTS,
        description="List projects from the YASIN-DOCS registry (read-only).",
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    ),
    RegistryToolDefinition(
        name=TOOL_GET_PROJECT,
        description="Get one project metadata entry from the registry.",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    ),
    RegistryToolDefinition(
        name=TOOL_LIST_DEPS,
        description="List outbound dependencies for a registry project.",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    ),
)
