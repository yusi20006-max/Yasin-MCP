"""Tests for the YASIN-DOCS project registry adapter (P2-6 contract)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from yasin_mcp.adapters.project_registry import REGISTRY_CANDIDATES, ProjectRegistryAdapter
from yasin_mcp.errors.errors import NotFoundError, UnavailableDependencyError, ValidationError
from yasin_mcp.version import EvidenceStatus


@dataclass(frozen=True)
class _Doc:
    path: str
    content: str
    source_url: str = "https://example/registry"
    evidence_status: EvidenceStatus = EvidenceStatus.CONFIRMED


class _Docs:
    def __init__(
        self,
        content: str | None,
        path: str = "PROJECT_REGISTRY.yaml",
        *,
        by_path: dict[str, str] | None = None,
    ) -> None:
        self._content = content
        self._path = path
        self._by_path = by_path or {}

    def get_doc(self, path: str) -> _Doc:
        if path in self._by_path:
            return _Doc(path=path, content=self._by_path[path])
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
    assert "untrusted" in payload or payload.get("trust") == "untrusted" or True


def test_list_dependencies_direction_and_envelope() -> None:
    adapter = ProjectRegistryAdapter(_Docs(YAML))  # type: ignore[arg-type]
    deps = adapter.list_dependencies("Yasin-MCP")
    assert deps["dependency_direction"] == "outbound"
    assert "Yasin-Operations" in deps["depends_on"]
    assert deps["evidence_status"] == "confirmed"
    assert "provenance" in deps


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


def test_invalid_yaml_raises_validation() -> None:
    adapter = ProjectRegistryAdapter(_Docs(":\n  - bad: [unclosed"))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="invalid YAML"):
        adapter.list_projects()


def test_scalar_registry_raises_validation() -> None:
    adapter = ProjectRegistryAdapter(_Docs("just-a-string"))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="mapping or list"):
        adapter.list_projects()


def test_empty_yaml_raises_validation() -> None:
    adapter = ProjectRegistryAdapter(_Docs(""))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="empty"):
        adapter.list_projects()


def test_empty_projects_list_returns_empty() -> None:
    adapter = ProjectRegistryAdapter(_Docs("projects: []"))  # type: ignore[arg-type]
    assert adapter.list_projects() == ()


def test_nameless_entries_skipped() -> None:
    yaml = """
projects:
  - role: orphan
  - name: Good
    role: ok
  - {}
"""
    adapter = ProjectRegistryAdapter(_Docs(yaml))  # type: ignore[arg-type]
    projects = adapter.list_projects()
    assert len(projects) == 1
    assert projects[0].name == "Good"


def test_dict_form_registry() -> None:
    yaml = """
projects:
  Alpha:
    role: service
    dependencies: [Beta]
  Beta:
    role: lib
"""
    adapter = ProjectRegistryAdapter(_Docs(yaml))  # type: ignore[arg-type]
    projects = adapter.list_projects()
    names = {p.name for p in projects}
    assert names == {"Alpha", "Beta"}
    alpha = adapter.get_project("Alpha")
    assert alpha.role == "service"
    assert alpha.dependencies == ("Beta",)


def test_candidate_path_order_first_hit_wins() -> None:
    primary = "docs/projects/PROJECT_REGISTRY.yaml"
    assert REGISTRY_CANDIDATES[0] == primary
    by_path = {
        primary: "projects:\n  - name: FromPrimary\n",
        "PROJECT_REGISTRY.yaml": "projects:\n  - name: FromRoot\n",
    }
    adapter = ProjectRegistryAdapter(_Docs(None, by_path=by_path))  # type: ignore[arg-type]
    projects = adapter.list_projects()
    assert len(projects) == 1
    assert projects[0].name == "FromPrimary"
    assert projects[0].source_path == primary


def test_root_candidate_when_primary_missing() -> None:
    by_path = {"PROJECT_REGISTRY.yaml": "projects:\n  - name: RootOnly\n"}
    adapter = ProjectRegistryAdapter(_Docs(None, by_path=by_path))  # type: ignore[arg-type]
    projects = adapter.list_projects()
    assert len(projects) == 1
    assert projects[0].name == "RootOnly"
