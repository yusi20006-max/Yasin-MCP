"""Project registry adapter tests."""

from __future__ import annotations

import pytest

from yasin_mcp.adapters.project_registry import ProjectRegistryAdapter
from yasin_mcp.errors.errors import NotFoundError, UnavailableDependencyError


class FakeDocument:
    path = "PROJECT_REGISTRY.yaml"
    source_url = "https://github.com/yusi20006-max/YASIN-DOCS/blob/main/PROJECT_REGISTRY.yaml"
    evidence_status = type("Evidence", (), {"value": "confirmed"})()


class FakeDocs:
    def __init__(self, content: str | None) -> None:
        self.content = content

    def get_doc(self, path: str):
        if path != "PROJECT_REGISTRY.yaml" or self.content is None:
            raise NotFoundError("missing")
        document = FakeDocument()
        document.content = self.content
        return document


def test_project_registry_normalizes_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = ProjectRegistryAdapter(
        FakeDocs(
            "projects:\n  Yasin-Core:\n    repository: yusi20006-max/Yasin-Core\n    status: stable\n    owner: Yasin Team\n"
        )
    )
    project = adapter.get_project("Yasin-Core")
    assert project.repository == "yusi20006-max/Yasin-Core"
    assert project.status == "stable"
    assert project.evidence_status.value == "confirmed"


def test_project_registry_normalizes_list() -> None:
    adapter = ProjectRegistryAdapter(
        FakeDocs("- name: Yasin-Agent\n  repository: yusi20006-max/Yasin-Agent\n")
    )
    assert adapter.list_projects()[0].name == "Yasin-Agent"


def test_missing_registry_is_explicitly_unavailable() -> None:
    with pytest.raises(UnavailableDependencyError):
        ProjectRegistryAdapter(FakeDocs(None)).list_projects()


def test_missing_project_is_not_invented() -> None:
    adapter = ProjectRegistryAdapter(FakeDocs("projects:\n  Yasin-Core:\n    status: stable\n"))
    with pytest.raises(NotFoundError):
        adapter.get_project("Yasin-Agent")
