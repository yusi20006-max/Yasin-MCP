"""Read-only MCP tools over the GitHub adapter.

No write capabilities. No arbitrary API passthrough. Explicit allow-listed tools only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from yasin_mcp.adapters.github import GitHubAdapter
from yasin_mcp.errors.errors import ValidationError

TOOL_GET_REPO = "yasin_github_get_repository"
TOOL_LIST_ISSUES = "yasin_github_list_issues"
TOOL_GET_ISSUE = "yasin_github_get_issue"
TOOL_LIST_PRS = "yasin_github_list_pull_requests"
TOOL_GET_PR = "yasin_github_get_pull_request"
TOOL_LIST_COMMITS = "yasin_github_list_commits"
TOOL_COMMIT_STATUS = "yasin_github_get_commit_status"
TOOL_LIST_WORKFLOWS = "yasin_github_list_workflow_runs"
TOOL_LIST_BRANCHES = "yasin_github_list_branches"
TOOL_LIST_RELEASES = "yasin_github_list_releases"


class GitHubToolset:
    """Binds GitHubAdapter methods to MCP tool callables (read-only)."""

    def __init__(self, adapter: GitHubAdapter) -> None:
        self._adapter = adapter

    def get_repository(self, owner: str, repository: str) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        return self._adapter.get_repository(owner, repository).as_dict()

    def list_issues(self, owner: str, repository: str, limit: int = 20) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        items = self._adapter.list_issues(owner, repository, limit=limit)
        return {
            "owner": owner,
            "repository": repository,
            "issues": [item.as_dict() for item in items],
            "count": len(items),
            "evidence_status": "confirmed",
        }

    def get_issue(self, owner: str, repository: str, number: int) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        if not isinstance(number, int):
            raise ValidationError("number must be an integer")
        return self._adapter.get_issue(owner, repository, number).as_dict()

    def list_pull_requests(self, owner: str, repository: str, limit: int = 20) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        items = self._adapter.list_pull_requests(owner, repository, limit=limit)
        return {
            "owner": owner,
            "repository": repository,
            "pull_requests": [item.as_dict() for item in items],
            "count": len(items),
            "evidence_status": "confirmed",
        }

    def get_pull_request(self, owner: str, repository: str, number: int) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        if not isinstance(number, int):
            raise ValidationError("number must be an integer")
        return self._adapter.get_pull_request(owner, repository, number).as_dict()

    def list_commits(self, owner: str, repository: str, limit: int = 20) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        items = self._adapter.list_commits(owner, repository, limit=limit)
        return {
            "owner": owner,
            "repository": repository,
            "commits": [item.as_dict() for item in items],
            "count": len(items),
            "evidence_status": "confirmed",
        }

    def get_commit_status(self, owner: str, repository: str, sha: str) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        if not isinstance(sha, str):
            raise ValidationError("sha must be a string")
        return self._adapter.get_commit_status(owner, repository, sha).as_dict()

    def list_workflow_runs(self, owner: str, repository: str, limit: int = 20) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        runs = self._adapter.list_workflow_runs(owner, repository, limit=limit)
        return {
            "owner": owner,
            "repository": repository,
            "workflow_runs": list(runs),
            "count": len(runs),
            "evidence_status": "confirmed",
            "provenance": {"source": "github"},
        }

    def list_branches(self, owner: str, repository: str, limit: int = 20) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        items = self._adapter.list_branches(owner, repository, limit=limit)
        return {
            "owner": owner,
            "repository": repository,
            "branches": [item.as_dict() for item in items],
            "count": len(items),
            "evidence_status": "confirmed",
        }

    def list_releases(self, owner: str, repository: str, limit: int = 20) -> dict[str, Any]:
        if not isinstance(owner, str) or not isinstance(repository, str):
            raise ValidationError("owner and repository must be strings")
        items = self._adapter.list_releases(owner, repository, limit=limit)
        return {
            "owner": owner,
            "repository": repository,
            "releases": [item.as_dict() for item in items],
            "count": len(items),
            "evidence_status": "confirmed",
        }


@dataclass(frozen=True)
class GitHubToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, Any]


_REPO_PROPS = {
    "owner": {"type": "string"},
    "repository": {"type": "string"},
}
_LIMIT = {"limit": {"type": "integer", "minimum": 1, "maximum": 50}}

GITHUB_TOOL_DEFINITIONS: tuple[GitHubToolDefinition, ...] = (
    GitHubToolDefinition(
        name=TOOL_GET_REPO,
        description="Get repository metadata (read-only).",
        input_schema={
            "type": "object",
            "properties": dict(_REPO_PROPS),
            "required": ["owner", "repository"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_LIST_ISSUES,
        description="List repository issues (read-only, bounded).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, **_LIMIT},
            "required": ["owner", "repository"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_GET_ISSUE,
        description="Get one issue by number (read-only).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, "number": {"type": "integer"}},
            "required": ["owner", "repository", "number"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_LIST_PRS,
        description="List pull requests (read-only, bounded).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, **_LIMIT},
            "required": ["owner", "repository"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_GET_PR,
        description="Get one pull request by number (read-only).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, "number": {"type": "integer"}},
            "required": ["owner", "repository", "number"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_LIST_COMMITS,
        description="List recent commits (read-only, bounded).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, **_LIMIT},
            "required": ["owner", "repository"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_COMMIT_STATUS,
        description="Get combined commit status (read-only).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, "sha": {"type": "string"}},
            "required": ["owner", "repository", "sha"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_LIST_WORKFLOWS,
        description="List recent workflow/CI runs (read-only, bounded).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, **_LIMIT},
            "required": ["owner", "repository"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_LIST_BRANCHES,
        description="List repository branches (read-only, bounded).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, **_LIMIT},
            "required": ["owner", "repository"],
            "additionalProperties": False,
        },
    ),
    GitHubToolDefinition(
        name=TOOL_LIST_RELEASES,
        description="List repository releases (read-only, bounded).",
        input_schema={
            "type": "object",
            "properties": {**_REPO_PROPS, **_LIMIT},
            "required": ["owner", "repository"],
            "additionalProperties": False,
        },
    ),
)
