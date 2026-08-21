"""Bounded, read-only GitHub adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from yasin_mcp.config.config import SecretStr
from yasin_mcp.errors.errors import (
    UpstreamError,
    ValidationError,
)
from yasin_mcp.reliability.http_retry import github_get_json
from yasin_mcp.security.untrusted_context import attach_untrusted_envelope
from yasin_mcp.version import EvidenceStatus

GITHUB_API = "https://api.github.com"
API_VERSION = "2026-03-10"
MAX_SEARCH_RESULTS = 50
MAX_RESPONSE_BYTES = 1_000_000

JsonRequester = Callable[[str, dict[str, str], int], Any]


def _meta(
    source_url: str,
    html_url: str = "",
    *,
    text_for_markers: str | None = None,
) -> dict[str, Any]:
    prov: dict[str, Any] = {"source": "github", "source_url": source_url}
    if html_url:
        prov["html_url"] = html_url
    out: dict[str, Any] = {
        "source_url": source_url,
        "evidence_status": EvidenceStatus.CONFIRMED.value,
        "provenance": prov,
    }
    if html_url:
        out["html_url"] = html_url
    return attach_untrusted_envelope(
        out,
        source="github",
        text_for_markers=text_for_markers,
    )


@dataclass(frozen=True)
class RepositoryInfo:
    full_name: str
    default_branch: str
    description: str | None
    private: bool
    html_url: str
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "default_branch": self.default_branch,
            "description": self.description,
            "private": self.private,
            **_meta(self.source_url, self.html_url),
        }


@dataclass(frozen=True)
class IssueInfo:
    number: int
    title: str
    state: str
    html_url: str
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "state": self.state,
            **_meta(self.source_url, self.html_url),
        }


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    title: str
    state: str
    draft: bool
    html_url: str
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "state": self.state,
            "draft": self.draft,
            **_meta(self.source_url, self.html_url),
        }


@dataclass(frozen=True)
class CommitStatus:
    sha: str
    state: str
    total_count: int
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "sha": self.sha,
            "state": self.state,
            "total_count": self.total_count,
            **_meta(self.source_url),
        }


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    message: str
    author: str
    date: str
    html_url: str
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "sha": self.sha,
            "message": self.message,
            "author": self.author,
            "date": self.date,
            **_meta(self.source_url, self.html_url),
        }


@dataclass(frozen=True)
class BranchInfo:
    name: str
    protected: bool
    commit_sha: str
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "protected": self.protected,
            "commit_sha": self.commit_sha,
            **_meta(self.source_url),
        }


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    name: str
    draft: bool
    prerelease: bool
    html_url: str
    published_at: str | None
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "tag_name": self.tag_name,
            "name": self.name,
            "draft": self.draft,
            "prerelease": self.prerelease,
            "published_at": self.published_at,
            **_meta(self.source_url, self.html_url),
        }


@dataclass(frozen=True)
class SearchResult:
    name: str
    path: str
    repository: str
    html_url: str
    source_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "repository": self.repository,
            **_meta(self.source_url, self.html_url),
        }


class GitHubAdapter:
    """Read-only GitHub API adapter."""

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
        if number < 1:
            raise ValidationError("pull request number must be positive")
