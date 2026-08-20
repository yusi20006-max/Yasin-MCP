"""Bounded, read-only GitHub adapter.

Only explicit allow-listed endpoints are exposed. There is no generic request
method, so callers cannot turn this adapter into an arbitrary GitHub API proxy.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from yasin_mcp.config.config import SecretStr
from yasin_mcp.errors.errors import (
    NotFoundError,
    RateLimitedError,
    TimeoutMcpError,
    UnauthenticatedError,
    UnavailableDependencyError,
    UpstreamError,
    ValidationError,
)

GITHUB_API = "https://api.github.com"
API_VERSION = "2026-03-10"
MAX_SEARCH_RESULTS = 50
MAX_RESPONSE_BYTES = 1_000_000

JsonRequester = Callable[[str, dict[str, str], int], Any]


@dataclass(frozen=True)
class RepositoryInfo:
    full_name: str
    default_branch: str
    description: str | None
    private: bool
    html_url: str
    source_url: str


@dataclass(frozen=True)
class IssueInfo:
    number: int
    title: str
    state: str
    html_url: str
    source_url: str


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    title: str
    state: str
    draft: bool
    html_url: str
    source_url: str


@dataclass(frozen=True)
class CommitStatus:
    sha: str
    state: str
    total_count: int
    source_url: str


@dataclass(frozen=True)
class SearchResult:
    name: str
    path: str
    repository: str
    html_url: str
    source_url: str


class GitHubAdapter:
    """Read-only GitHub API adapter with an explicit endpoint allow-list."""

    def __init__(
        self,
        *,
        token: SecretStr | None = None,
        timeout_seconds: int = 30,
        requester: JsonRequester | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValidationError("timeout_seconds must be positive")
        self._token = token
        self._timeout = timeout_seconds
        self._requester = requester or _request_json

    def get_repository(self, owner: str, repository: str) -> RepositoryInfo:
        owner, repository = _validate_repo(owner, repository)
        payload = self._get(f"/repos/{owner}/{repository}")
        return RepositoryInfo(
            full_name=str(payload.get("full_name", f"{owner}/{repository}")),
            default_branch=str(payload.get("default_branch", "main")),
            description=payload.get("description"),
            private=bool(payload.get("private", False)),
            html_url=str(payload.get("html_url", "")),
            source_url=f"{GITHUB_API}/repos/{owner}/{repository}",
        )

    def get_issue(self, owner: str, repository: str, number: int) -> IssueInfo:
        owner, repository = _validate_repo(owner, repository)
        if number < 1:
            raise ValidationError("issue number must be positive")
        payload = self._get(f"/repos/{owner}/{repository}/issues/{number}")
        return IssueInfo(
            number=number,
            title=str(payload.get("title", "")),
            state=str(payload.get("state", "")),
            html_url=str(payload.get("html_url", "")),
            source_url=f"{GITHUB_API}/repos/{owner}/{repository}/issues/{number}",
        )

    def list_issues(self, owner: str, repository: str, *, limit: int = 20) -> tuple[IssueInfo, ...]:
        owner, repository = _validate_repo(owner, repository)
        limit = _validate_limit(limit)
        payload = self._get(f"/repos/{owner}/{repository}/issues?state=all&per_page={limit}")
        if not isinstance(payload, list):
            raise UpstreamError("GitHub returned an unexpected issue-list shape")
        return tuple(
            IssueInfo(
                number=int(item.get("number", 0)),
                title=str(item.get("title", "")),
                state=str(item.get("state", "")),
                html_url=str(item.get("html_url", "")),
                source_url=(
                    f"{GITHUB_API}/repos/{owner}/{repository}/issues/{item.get('number', 0)}"
                ),
            )
            for item in payload[:limit]
            if "pull_request" not in item
        )

    def get_pull_request(self, owner: str, repository: str, number: int) -> PullRequestInfo:
        owner, repository = _validate_repo(owner, repository)
        if number < 1:
            raise ValidationError("pull request number must be positive")
        payload = self._get(f"/repos/{owner}/{repository}/pulls/{number}")
        return PullRequestInfo(
            number=number,
            title=str(payload.get("title", "")),
            state=str(payload.get("state", "")),
            draft=bool(payload.get("draft", False)),
            html_url=str(payload.get("html_url", "")),
            source_url=f"{GITHUB_API}/repos/{owner}/{repository}/pulls/{number}",
        )

    def list_pull_requests(
        self, owner: str, repository: str, *, limit: int = 20
    ) -> tuple[PullRequestInfo, ...]:
        owner, repository = _validate_repo(owner, repository)
        limit = _validate_limit(limit)
        payload = self._get(f"/repos/{owner}/{repository}/pulls?state=all&per_page={limit}")
        if not isinstance(payload, list):
            raise UpstreamError("GitHub returned an unexpected pull-request-list shape")
        return tuple(
            PullRequestInfo(
                number=int(item.get("number", 0)),
                title=str(item.get("title", "")),
                state=str(item.get("state", "")),
                draft=bool(item.get("draft", False)),
                html_url=str(item.get("html_url", "")),
                source_url=f"{GITHUB_API}/repos/{owner}/{repository}/pulls/{item.get('number', 0)}",
            )
            for item in payload[:limit]
        )

    def get_commit_status(self, owner: str, repository: str, sha: str) -> CommitStatus:
        owner, repository = _validate_repo(owner, repository)
        if not sha or "/" in sha or " " in sha:
            raise ValidationError("invalid commit SHA")
        payload = self._get(f"/repos/{owner}/{repository}/commits/{sha}/status")
        return CommitStatus(
            sha=sha,
            state=str(payload.get("state", "unknown")),
            total_count=int(payload.get("total_count", 0)),
            source_url=f"{GITHUB_API}/repos/{owner}/{repository}/commits/{sha}/status",
        )

    def list_workflow_runs(
        self, owner: str, repository: str, *, limit: int = 20
    ) -> tuple[dict[str, Any], ...]:
        owner, repository = _validate_repo(owner, repository)
        limit = _validate_limit(limit)
        payload = self._get(f"/repos/{owner}/{repository}/actions/runs?per_page={limit}")
        runs = payload.get("workflow_runs", [])
        if not isinstance(runs, list):
            raise UpstreamError("GitHub returned an unexpected workflow-run shape")
        return tuple(
            {
                "id": run.get("id"),
                "name": run.get("name"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "html_url": run.get("html_url"),
                "source_url": f"{GITHUB_API}/repos/{owner}/{repository}/actions/runs",
            }
            for run in runs[:limit]
        )

    def search_code(self, query: str, *, limit: int = 20) -> tuple[SearchResult, ...]:
        query = query.strip()
        if not query:
            raise ValidationError("search query must not be empty")
        limit = _validate_limit(limit)
        payload = self._get(f"/search/code?q={_quote_query(query)}&per_page={limit}")
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise UpstreamError("GitHub returned an unexpected search shape")
        return tuple(
            SearchResult(
                name=str(item.get("name", "")),
                path=str(item.get("path", "")),
                repository=str(item.get("repository", {}).get("full_name", "")),
                html_url=str(item.get("html_url", "")),
                source_url=f"{GITHUB_API}/search/code",
            )
            for item in items[:limit]
        )

    def _get(self, path: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "Yasin-MCP",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token.get_secret_value()}"
        return self._requester(f"{GITHUB_API}{path}", headers, self._timeout)


def _validate_repo(owner: str, repository: str) -> tuple[str, str]:
    if (
        not owner
        or not repository
        or any(value in owner + repository for value in ("/", "..", " "))
    ):
        raise ValidationError("invalid GitHub repository identifier")
    return owner, repository


def _validate_limit(limit: int) -> int:
    if not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise ValidationError(f"limit must be between 1 and {MAX_SEARCH_RESULTS}")
    return limit


def _quote_query(query: str) -> str:
    from urllib.parse import quote

    return quote(query, safe="")


def _request_json(url: str, headers: dict[str, str], timeout: int) -> Any:
    request = Request(url, headers=headers, method="GET")
    try:
        # nosec B310: url is always constructed from the hardcoded
        # GITHUB_API = "https://api.github.com" prefix (see module
        # constants above) plus path segments this module builds
        # itself -- never a caller-supplied scheme or arbitrary URL.
        with urlopen(request, timeout=timeout) as response:  # nosec B310
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 401:
            raise UnauthenticatedError("GitHub authentication failed") from exc
        if exc.code == 404:
            raise NotFoundError("GitHub resource was not found") from exc
        if exc.code == 403 or exc.code == 429:
            raise RateLimitedError("GitHub denied the request or rate limit was reached") from exc
        raise UpstreamError(f"GitHub returned HTTP {exc.code}") from exc
    except TimeoutError as exc:
        raise TimeoutMcpError("GitHub request timed out") from exc
    except URLError as exc:
        raise UnavailableDependencyError("GitHub is unavailable") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise UpstreamError("GitHub response exceeded the configured size limit")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpstreamError("GitHub returned invalid JSON") from exc
