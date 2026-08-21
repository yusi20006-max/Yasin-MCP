"""Read-only MCP tools over the YASIN-DOCS adapter.

These tools expose canonical documentation context with explicit provenance.
Document *content* is documentation text and must not be treated as confirmed
runtime fact merely because the file was successfully fetched (the fetch is
CONFIRMED; claims inside the document remain TARGET unless verified elsewhere).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from yasin_mcp.adapters.docs import Document, DocumentRef, YasinDocsAdapter
from yasin_mcp.errors.errors import ValidationError

TOOL_LIST_DOCS = "yasin_docs_list_documents"
TOOL_GET_DOC = "yasin_docs_get_document"
TOOL_SEARCH_DOCS = "yasin_docs_search"
TOOL_LIST_ADRS = "yasin_docs_list_adrs"
TOOL_GET_ADR = "yasin_docs_get_adr"
TOOL_LIST_ARCHITECTURE = "yasin_docs_list_architecture"
TOOL_GET_PROJECT_ARCHITECTURE = "yasin_docs_get_project_architecture"


def _ref_to_dict(ref: DocumentRef) -> dict[str, Any]:
    return {
        "path": ref.path,
        "sha": ref.sha,
        "size": ref.size,
        "url": ref.url,
        "repository": ref.repository,
        "ref": ref.ref,
        "provenance": {
            "source": "yasin-docs",
            "repository": ref.repository,
            "ref": ref.ref,
            "path": ref.path,
            "sha": ref.sha,
        },
    }


def _document_payload(document: Document) -> dict[str, Any]:
    return document.as_dict()


class DocsToolset:
    """Binds docs adapter methods to MCP tool callables (read-only)."""

    def __init__(self, adapter: YasinDocsAdapter) -> None:
        self._adapter = adapter

    def list_documents(self) -> dict[str, Any]:
        refs = self._adapter.list_documents()
        return {
            "documents": [_ref_to_dict(ref) for ref in refs],
            "count": len(refs),
            "repository": self._adapter.repository,
            "evidence_status": "confirmed",
            "note": (
                "Paths are CONFIRMED from the live YASIN-DOCS tree. "
                "Document body claims remain TARGET unless verified elsewhere."
            ),
        }

    def get_document(self, path: str) -> dict[str, Any]:
        if not isinstance(path, str):
            raise ValidationError("path must be a string")
        return _document_payload(self._adapter.get_doc(path))

    def search(self, query: str, path_prefix: str | None = None) -> dict[str, Any]:
        if not isinstance(query, str):
            raise ValidationError("query must be a string")
        if path_prefix is not None and not isinstance(path_prefix, str):
            raise ValidationError("path_prefix must be a string or omitted")
        results = self._adapter.search_docs_scoped(query, path_prefix=path_prefix)
        return {
            "query": query,
            "path_prefix": path_prefix,
            "results": [item.as_dict() for item in results],
            "count": len(results),
            "repository": self._adapter.repository,
            "evidence_status": "confirmed",
            "note": (
                "Match counts are CONFIRMED against fetched file bodies. "
                "Matched text is documentation content, not runtime proof."
            ),
        }

    def list_adrs(self) -> dict[str, Any]:
        refs = self._adapter.list_adrs()
        return {
            "adrs": [_ref_to_dict(ref) for ref in refs],
            "count": len(refs),
            "repository": self._adapter.repository,
            "evidence_status": "confirmed",
            "note": (
                "ADR file presence is CONFIRMED from the repository tree. "
                "ADR decisions describe TARGET architecture intent unless "
                "independently verified in code."
            ),
        }

    def get_adr(self, name: str) -> dict[str, Any]:
        if not isinstance(name, str):
            raise ValidationError("name must be a string")
        return _document_payload(self._adapter.get_adr(name))

    def list_architecture(self) -> dict[str, Any]:
        refs = self._adapter.list_architecture_docs()
        return {
            "architecture_docs": [_ref_to_dict(ref) for ref in refs],
            "count": len(refs),
            "repository": self._adapter.repository,
            "evidence_status": "confirmed",
            "note": (
                "Architecture document paths are CONFIRMED from the tree. "
                "Architecture statements inside documents are TARGET intent."
            ),
        }

    def get_project_architecture(self, project: str) -> dict[str, Any]:
        if not isinstance(project, str):
            raise ValidationError("project must be a string")
        return _document_payload(self._adapter.get_project_architecture(project))


@dataclass(frozen=True)
class DocsToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, Any]


DOCS_TOOL_DEFINITIONS: tuple[DocsToolDefinition, ...] = (
    DocsToolDefinition(
        name=TOOL_LIST_DOCS,
        description=(
            "List bounded text documents in the canonical YASIN-DOCS repository "
            "(read-only, with provenance)."
        ),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    DocsToolDefinition(
        name=TOOL_GET_DOC,
        description=(
            "Read one YASIN-DOCS document by path (read-only). Returns content with "
            "source provenance and evidence_status."
        ),
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    ),
    DocsToolDefinition(
        name=TOOL_SEARCH_DOCS,
        description=(
            "Search YASIN-DOCS document bodies for a query string (read-only). "
            "Optional path_prefix scopes the search (e.g. docs/adr)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path_prefix": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    ),
    DocsToolDefinition(
        name=TOOL_LIST_ADRS,
        description="List Architecture Decision Records under docs/adr/ (read-only).",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    DocsToolDefinition(
        name=TOOL_GET_ADR,
        description=(
            "Read an ADR by filename or path (read-only). Resolves docs/adr/<name>.md "
            "when only a short name is given."
        ),
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    ),
    DocsToolDefinition(
        name=TOOL_LIST_ARCHITECTURE,
        description=(
            "List architecture documentation paths (ARCHITECTURE.md and "
            "docs/architecture/*) from YASIN-DOCS (read-only)."
        ),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    DocsToolDefinition(
        name=TOOL_GET_PROJECT_ARCHITECTURE,
        description=(
            "Find a project architecture document by project name without inventing "
            "missing docs (read-only)."
        ),
        input_schema={
            "type": "object",
            "properties": {"project": {"type": "string"}},
            "required": ["project"],
            "additionalProperties": False,
        },
    ),
)
