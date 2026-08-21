"""End-to-end ecosystem integration matrix (deterministic / mocked paths)."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from yasin_mcp.adapters.docs import Document, YasinDocsAdapter
from yasin_mcp.adapters.github import GitHubAdapter, RepositoryInfo
from yasin_mcp.adapters.operations import OperationsAdapter
from yasin_mcp.adapters.project_registry import ProjectRegistryAdapter
from yasin_mcp.errors.errors import (
    NotFoundError,
    RateLimitedError,
    TimeoutMcpError,
    UnauthenticatedError,
    UnavailableDependencyError,
    ValidationError,
)
from yasin_mcp.server.runtime import ServerRuntime
from yasin_mcp.version import EvidenceStatus


def test_runtime_success_path_registers_core_prefixes() -> None:
    runtime = ServerRuntime.create()
    names = {c.name for c in runtime.capability_catalog().capabilities}
    assert any(n.startswith("yasin_docs_") for n in names)
    assert any(n.startswith("yasin_github_") for n in names)
    assert any(n.startswith("yasin_registry_") for n in names)


def test_missing_ops_gateway_does_not_block_runtime() -> None:
    adapter = Mock(spec=OperationsAdapter)
    adapter.available = False
    runtime = ServerRuntime.create(operations_adapter=adapter)
    names = {c.name for c in runtime.capability_catalog().capabilities}
    assert not any(n.startswith("yasin_operations_") for n in names)
    assert any(n.startswith("yasin_docs_") for n in names)


def test_docs_not_found_surfaces_error() -> None:
    def requester(url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
        raise NotFoundError("missing")

    adapter = YasinDocsAdapter(timeout_seconds=5, requester=requester)
    with pytest.raises(NotFoundError):
        adapter.get_doc("missing.md")


def test_github_rate_limit_and_auth_errors() -> None:
    def rate_limited(url: str, headers: dict[str, str], timeout: int) -> Any:
        raise RateLimitedError("rate limited")

    def unauth(url: str, headers: dict[str, str], timeout: int) -> Any:
        raise UnauthenticatedError("auth failed")

    with pytest.raises(RateLimitedError):
        GitHubAdapter(timeout_seconds=5, requester=rate_limited).get_repository("a", "b")
    with pytest.raises(UnauthenticatedError):
        GitHubAdapter(timeout_seconds=5, requester=unauth).get_repository("a", "b")


def test_github_timeout() -> None:
    def timed_out(url: str, headers: dict[str, str], timeout: int) -> Any:
        raise TimeoutMcpError("timeout")

    with pytest.raises(TimeoutMcpError):
        GitHubAdapter(timeout_seconds=5, requester=timed_out).get_repository("a", "b")


def test_registry_unavailable_when_docs_missing() -> None:
    class _Docs:
        def get_doc(self, path: str) -> Document:
            raise NotFoundError(path)

    adapter = ProjectRegistryAdapter(_Docs())  # type: ignore[arg-type]
    with pytest.raises(UnavailableDependencyError):
        adapter.list_projects()


def test_malformed_registry_yaml() -> None:
    class _Docs:
        def get_doc(self, path: str) -> Document:
            return Document(
                path=path,
                content=": not yaml [[[",
                source_url="u",
                sha="s",
                evidence_status=EvidenceStatus.CONFIRMED,
            )

    adapter = ProjectRegistryAdapter(_Docs())  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        adapter.list_projects()


def test_github_repo_success_mocked() -> None:
    def requester(url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
        return {
            "full_name": "o/r",
            "default_branch": "main",
            "description": "d",
            "private": False,
            "html_url": "https://github.com/o/r",
        }

    info = GitHubAdapter(timeout_seconds=5, requester=requester).get_repository("o", "r")
    assert isinstance(info, RepositoryInfo)
    assert info.as_dict()["evidence_status"] == "confirmed"
