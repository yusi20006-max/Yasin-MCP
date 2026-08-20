"""Tests for the bounded YASIN-DOCS adapter."""

from __future__ import annotations

import base64

import pytest

from yasin_mcp.adapters.docs import (
    DOCS_OWNER,
    DOCS_REPOSITORY,
    YasinDocsAdapter,
)
from yasin_mcp.errors.errors import NotFoundError, ValidationError


def make_requester(files: dict[str, str]):
    encoded = {path: base64.b64encode(content.encode()).decode() for path, content in files.items()}

    def requester(url: str, headers: dict[str, str], timeout: int):
        assert url.startswith("https://api.github.com/")
        assert headers["User-Agent"] == "Yasin-MCP"
        assert timeout == 10
        if "/git/trees/" in url:
            return {
                "truncated": False,
                "tree": [
                    {
                        "path": path,
                        "type": "blob",
                        "sha": f"sha-{index}",
                        "size": len(content.encode()),
                        "url": f"https://api.github.com/blob/{index}",
                    }
                    for index, (path, content) in enumerate(files.items())
                ],
            }
        marker = "/contents/"
        path = url.split(marker, 1)[1].split("?", 1)[0]
        if path not in encoded:
            raise NotFoundError("missing")
        return {
            "type": "file",
            "content": encoded[path],
            "sha": f"sha-{path}",
            "html_url": f"https://github.com/{DOCS_OWNER}/{DOCS_REPOSITORY}/blob/main/{path}",
        }

    return requester


@pytest.fixture
def adapter() -> YasinDocsAdapter:
    return YasinDocsAdapter(
        timeout_seconds=10,
        requester=make_requester(
            {
                "README.md": "Yasin architecture overview",
                "docs/adr/ADR-0001.md": "Decision: keep boundaries explicit",
                "docs/architecture/CORE.md": (
                    "Yasin-Core architecture. This architecture document "
                    "describes the Core architecture in detail."
                ),
            }
        ),
    )


def test_lists_only_bounded_text_documents(adapter: YasinDocsAdapter) -> None:
    refs = adapter.list_documents()
    assert [ref.path for ref in refs] == [
        "README.md",
        "docs/adr/ADR-0001.md",
        "docs/architecture/CORE.md",
    ]


def test_get_doc_returns_confirmed_evidence(adapter: YasinDocsAdapter) -> None:
    document = adapter.get_doc("docs/adr/ADR-0001.md")
    assert document.content.startswith("Decision")
    assert document.evidence_status.value == "confirmed"


def test_search_is_case_insensitive_and_ranked(adapter: YasinDocsAdapter) -> None:
    results = adapter.search_docs("architecture")
    assert [result.document.path for result in results] == [
        "docs/architecture/CORE.md",
        "README.md",
    ]


def test_get_adr_resolves_filename(adapter: YasinDocsAdapter) -> None:
    assert adapter.get_adr("ADR-0001").path == "docs/adr/ADR-0001.md"


def test_project_architecture_does_not_invent_missing_docs(adapter: YasinDocsAdapter) -> None:
    with pytest.raises(NotFoundError):
        adapter.get_project_architecture("Yasin-Agent")


def test_path_traversal_is_rejected(adapter: YasinDocsAdapter) -> None:
    with pytest.raises(ValidationError):
        adapter.get_doc("docs/../secrets.txt")


def test_empty_search_is_rejected(adapter: YasinDocsAdapter) -> None:
    with pytest.raises(ValidationError):
        adapter.search_docs("  ")


def test_invalid_max_files_is_rejected() -> None:
    with pytest.raises(ValidationError):
        YasinDocsAdapter(max_files=0, requester=lambda *_: {})
