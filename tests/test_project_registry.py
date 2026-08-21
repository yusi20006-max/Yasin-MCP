"""Tests for the YASIN-DOCS project registry adapter."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from yasin_mcp.adapters.project_registry import ProjectRegistryAdapter
from yasin_mcp.errors.errors import NotFoundError, UnavailableDependencyError, ValidationError
from yasin_mcp.version import EvidenceStatus


@dataclass(frozen=True)
class _Doc:
    path: str
    content: str
    source_url: str = "https://example/registry"
    evidence_status: EvidenceStatus = EvidenceStatus.CONFIRMED


class _Docs:
    def __init__(self, content: str | None, path: str = "PROJECT_REGISTRY.yaml") -> None:
        self._content = content
        self._path = path

    def get_doc(self, path: str) -> _Doc:
        if self._content is None or path != self._path:
            raise NotFoundError(path)
        return _Doc(path=path, content=self._content)


YAML = """
projects:
  - name: Yasin-MCP
    role: mcp-server
    repository: yusi20006-max/Yasin-MCP
    status: active
    dependencies: [YASIN-DOCS, Yasin-Operations]
    public_contracts: [MCP stdio]
    operational_state: optional-ops-gateway
    mcp_capabilities: [yasin_docs_*, yasin_github_*]
  - name: YASIN-DOCS
    role: documentation
    repository: yusi20006-max/YASIN-DOCS
    status: active
"""


def test_list_and_get_project() -> None:
    adapter = ProjectRegistryAdapter(_Docs(YAML))  # type: ignore[arg-type]
    projects = adapter.list_projects()
    assert len(projects) == 2
    mcp = adapter.get_project("Yasin-MCP")
    assert mcp.role == "mcp-server"
    assert "YASIN-DOCS" in mcp.dependencies
    payload = mcp.as_dict()
    assert payload["evidence_status"] == "confirmed"
    assert payload["provenance"]["source"] == "yasin-docs-registry"


def test_list_dependencies_direction() -> None:
    adapter = ProjectRegistryAdapter(_Docs(YAML))  # type: ignore[arg-type]
    deps = adapter.list_dependencies("Yasin-MCP")
    assert deps["dependency_direction"] == "outbound"
    assert "Yasin-Operations" in deps["depends_on"]


def test_missing_project_and_empty_name() -> None:
    adapter = ProjectRegistryAdapter(_Docs(YAML))  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):
        adapter.get_project("missing")
    with pytest.raises(ValidationError):
        adapter.get_project("  ")


def test_missing_registry_is_unavailable() -> None:
    adapter = ProjectRegistryAdapter(_Docs(None))  # type: ignore[arg-type]
    with pytest.raises(UnavailableDependencyError):
        adapter.list_projects()


def test_unknown_fields_stay_none() -> None:
    yaml = "projects:\n  - name: Alone\n"
    adapter = ProjectRegistryAdapter(_Docs(yaml))  # type: ignore[arg-type]
    alone = adapter.get_project("Alone")
    assert alone.role is None
    assert alone.dependencies == ()
    deps = adapter.list_dependencies("Alone")
    assert "dependencies not declared in registry" in deps["unknowns"]
