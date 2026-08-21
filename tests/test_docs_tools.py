"""Unit tests for YASIN-DOCS MCP toolset (mocked adapter I/O)."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from yasin_mcp.adapters.docs import DOCS_OWNER, DOCS_REPOSITORY, YasinDocsAdapter
from yasin_mcp.errors.errors import NotFoundError, ValidationError
from yasin_mcp.tools.docs import DOCS_TOOL_DEFINITIONS, DocsToolset


def make_requester(files: dict[str, str]):
    encoded = {
        path: base64.b64encode(content.encode("utf-8")).decode("ascii")
        for path, content in files.items()
    }
    tree = {
        "truncated": False,
        "tree": [
            {"type": "blob", "path": path, "sha": f"sha-{path}", "size": len(content), "url": ""}
            for path, content in files.items()
        ],
    }

    def requester(url: str, _headers: dict[str, str], _timeout: int) -> dict[str, Any]:
        if "/git/trees/" in url:
            return tree
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
def toolset() -> DocsToolset:
    adapter = YasinDocsAdapter(
        timeout_seconds=10,
        requester=make_requester(
            {
                "ARCHITECTURE.md": "Ecosystem architecture overview",
                "docs/adr/ADR-0001.md": "Decision: keep boundaries explicit",
                "docs/architecture/CORE.md": (
                    "Yasin-Core architecture. This architecture document "
                    "describes the Core architecture in detail."
                ),
            }
        ),
    )
    return DocsToolset(adapter)


def test_tool_definitions_are_read_only_and_named() -> None:
    assert len(DOCS_TOOL_DEFINITIONS) == 7
    assert all(definition.name.startswith("yasin_docs_") for definition in DOCS_TOOL_DEFINITIONS)
    assert all(
        "additionalProperties" in definition.input_schema for definition in DOCS_TOOL_DEFINITIONS
    )


def test_list_documents_payload(toolset: DocsToolset) -> None:
    payload = toolset.list_documents()
    assert payload["count"] == 3
    assert payload["evidence_status"] == "confirmed"
    assert payload["documents"][0]["provenance"]["source"] == "yasin-docs"


def test_get_document_includes_provenance(toolset: DocsToolset) -> None:
    payload = toolset.get_document("docs/adr/ADR-0001.md")
    assert payload["content"].startswith("Decision")
    assert payload["provenance"]["path"] == "docs/adr/ADR-0001.md"
    assert payload["evidence_status"] == "confirmed"


def test_search_with_path_prefix(toolset: DocsToolset) -> None:
    payload = toolset.search("architecture", path_prefix="docs/architecture")
    assert payload["count"] == 1
    assert payload["results"][0]["document"]["path"] == "docs/architecture/CORE.md"


def test_list_adrs_and_architecture(toolset: DocsToolset) -> None:
    adrs = toolset.list_adrs()
    assert adrs["count"] == 1
    arch = toolset.list_architecture()
    assert {item["path"] for item in arch["architecture_docs"]} == {
        "ARCHITECTURE.md",
        "docs/architecture/CORE.md",
    }


def test_get_adr_and_project_architecture(toolset: DocsToolset) -> None:
    adr = toolset.get_adr("ADR-0001")
    assert adr["path"] == "docs/adr/ADR-0001.md"
    project = toolset.get_project_architecture("Yasin-Core")
    assert project["path"] == "docs/architecture/CORE.md"


def test_invalid_inputs_raise_validation(toolset: DocsToolset) -> None:
    with pytest.raises(ValidationError):
        toolset.get_document(123)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        toolset.search(None)  # type: ignore[arg-type]
