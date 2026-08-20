"""Tests for the explicit, read-only GitHub adapter."""

from __future__ import annotations

import pytest

from yasin_mcp.adapters.github import GitHubAdapter
from yasin_mcp.errors.errors import ValidationError


def requester(url: str, headers: dict[str, str], timeout: int):
    assert url.startswith("https://api.github.com/")
    assert headers["User-Agent"] == "Yasin-MCP"
    assert timeout == 10
    if url.endswith("/repos/yusi/Yasin"):
        return {
            "full_name": "yusi/Yasin",
            "default_branch": "main",
            "description": "Yasin project",
            "private": False,
            "html_url": "https://github.com/yusi/Yasin",
        }
    if "/issues/4" in url:
        return {
            "number": 4,
            "title": "Test issue",
            "state": "open",
            "html_url": "https://github.com/i/4",
        }
    if "/issues?" in url:
        return [
            {"number": 4, "title": "Issue", "state": "open", "html_url": "https://github.com/i/4"},
            {
                "number": 5,
                "title": "PR",
                "state": "open",
                "html_url": "https://github.com/p/5",
                "pull_request": {},
            },
        ]
    if "/pulls/8" in url:
        return {
            "number": 8,
            "title": "PR",
            "state": "open",
            "draft": False,
            "html_url": "https://github.com/p/8",
        }
    if "/pulls?" in url:
        return [
            {
                "number": 8,
                "title": "PR",
                "state": "open",
                "draft": False,
                "html_url": "https://github.com/p/8",
            }
        ]
    if "/commits/abc/status" in url:
        return {"state": "success", "total_count": 2}
    if "/actions/runs?" in url:
        return {
            "workflow_runs": [
                {
                    "id": 1,
                    "name": "CI",
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "https://github.com/run/1",
                }
            ]
        }
    if "/search/code?" in url:
        return {
            "items": [
                {
                    "name": "README.md",
                    "path": "README.md",
                    "repository": {"full_name": "yusi/Yasin"},
                    "html_url": "https://github.com/r",
                }
            ]
        }
    raise AssertionError(f"unexpected endpoint: {url}")


@pytest.fixture
def adapter() -> GitHubAdapter:
    return GitHubAdapter(timeout_seconds=10, requester=requester)


def test_repository_metadata(adapter: GitHubAdapter) -> None:
    result = adapter.get_repository("yusi", "Yasin")
    assert result.full_name == "yusi/Yasin"
    assert result.private is False


def test_issue_and_pull_request_reads(adapter: GitHubAdapter) -> None:
    assert adapter.get_issue("yusi", "Yasin", 4).title == "Test issue"
    assert adapter.get_pull_request("yusi", "Yasin", 8).draft is False
    assert len(adapter.list_issues("yusi", "Yasin")) == 1
    assert len(adapter.list_pull_requests("yusi", "Yasin")) == 1


def test_commit_and_workflow_status(adapter: GitHubAdapter) -> None:
    assert adapter.get_commit_status("yusi", "Yasin", "abc").state == "success"
    assert adapter.list_workflow_runs("yusi", "Yasin")[0]["conclusion"] == "success"


def test_bounded_code_search(adapter: GitHubAdapter) -> None:
    assert adapter.search_code("Yasin")[0].path == "README.md"


@pytest.mark.parametrize(
    "owner,repo", [("", "Yasin"), ("yusi", ""), ("yusi/evil", "Yasin"), ("yusi", "../evil")]
)
def test_repository_identifiers_are_validated(
    adapter: GitHubAdapter, owner: str, repo: str
) -> None:
    with pytest.raises(ValidationError):
        adapter.get_repository(owner, repo)


@pytest.mark.parametrize("limit", [0, 51])
def test_limits_are_bounded(adapter: GitHubAdapter, limit: int) -> None:
    with pytest.raises(ValidationError):
        adapter.list_issues("yusi", "Yasin", limit=limit)


def test_invalid_numbers_are_rejected(adapter: GitHubAdapter) -> None:
    with pytest.raises(ValidationError):
        adapter.get_issue("yusi", "Yasin", 0)
    with pytest.raises(ValidationError):
        adapter.get_pull_request("yusi", "Yasin", 0)
