"""Read-only adapter for the canonical YASIN-DOCS GitHub repository.

The repository target and API host are fixed constants: callers cannot turn this
adapter into an arbitrary URL fetcher. Network I/O is injected through a small
function boundary so tests never require the real GitHub service.
"""

from __future__ import annotations

import base64
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
from yasin_mcp.version import EvidenceStatus

GITHUB_API = "https://api.github.com"
DOCS_OWNER = "yusi20006-max"
DOCS_REPOSITORY = "YASIN-DOCS"
DOCS_REF = "main"
API_VERSION = "2026-03-10"
DEFAULT_MAX_FILES = 50
MAX_DOCUMENT_BYTES = 1_000_000

JsonRequester = Callable[[str, dict[str, str], int], dict[str, Any]]


@dataclass(frozen=True)
class DocumentRef:
    path: str
    sha: str
    size: int
    url: str
    repository: str = f"{DOCS_OWNER}/{DOCS_REPOSITORY}"
    ref: str = DOCS_REF


@dataclass(frozen=True)
class Document:
    path: str
    content: str
    source_url: str
    sha: str
    evidence_status: EvidenceStatus
    repository: str = f"{DOCS_OWNER}/{DOCS_REPOSITORY}"
    ref: str = DOCS_REF
    content_kind: str = "documentation"

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "content": self.content,
            "source_url": self.source_url,
            "sha": self.sha,
            "repository": self.repository,
            "ref": self.ref,
            "content_kind": self.content_kind,
            "evidence_status": self.evidence_status.value,
            "provenance": {
                "source": "yasin-docs",
                "repository": self.repository,
                "ref": self.ref,
                "path": self.path,
                "sha": self.sha,
                "source_url": self.source_url,
            },
        }


@dataclass(frozen=True)
class DocumentSearchResult:
    document: Document
    matches: int

    def as_dict(self) -> dict[str, Any]:
        return {"document": self.document.as_dict(), "matches": self.matches}


class YasinDocsAdapter:
    """Bounded read-only access to YASIN-DOCS."""

    def __init__(
        self,
        *,
        token: SecretStr | None = None,
        timeout_seconds: int = 30,
        max_files: int = DEFAULT_MAX_FILES,
        requester: JsonRequester | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValidationError("timeout_seconds must be positive")
        if not 1 <= max_files <= 200:
            raise ValidationError("max_files must be between 1 and 200")
        self._token = token
        self._timeout = timeout_seconds
        self._max_files = max_files
        self._requester = requester or _request_json

    @property
    def repository(self) -> str:
        return f"{DOCS_OWNER}/{DOCS_REPOSITORY}"

    def list_documents(self) -> tuple[DocumentRef, ...]:
        payload = self._get(
            f"/repos/{DOCS_OWNER}/{DOCS_REPOSITORY}/git/trees/{DOCS_REF}?recursive=1"
        )
        if payload.get("truncated"):
            raise UpstreamError("YASIN-DOCS tree response was truncated")
        refs: list[DocumentRef] = []
        for item in payload.get("tree", []):
            if item.get("type") != "blob":
                continue
            path = str(item.get("path", ""))
            if not _is_text_document(path):
                continue
            size = int(item.get("size", 0) or 0)
            if size > MAX_DOCUMENT_BYTES:
                continue
            refs.append(
                DocumentRef(
                    path=path,
                    sha=str(item.get("sha", "")),
                    size=size,
                    url=str(item.get("url", "")),
                )
            )
            if len(refs) >= self._max_files:
                break
        return tuple(sorted(refs, key=lambda item: item.path))

    def get_doc(self, path: str) -> Document:
        _validate_path(path)
        payload = self._get(
            f"/repos/{DOCS_OWNER}/{DOCS_REPOSITORY}/contents/{path}?ref={DOCS_REF}"
        )
        if payload.get("type") != "file":
            raise ValidationError("requested documentation path is not a file")
        encoded = payload.get("content")
        if not isinstance(encoded, str):
            raise UpstreamError("YASIN-DOCS file response did not contain content")
        try:
            content = base64.b64decode(encoded.replace("\n", ""), validate=True).decode(
                "utf-8"
            )
        except (ValueError, UnicodeDecodeError) as exc:
            raise UpstreamError("YASIN-DOCS file content could not be decoded") from exc
        if len(content.encode("utf-8")) > MAX_DOCUMENT_BYTES:
            raise ValidationError("document exceeds the maximum supported size")
        return Document(
            path=path,
            content=content,
            source_url=str(payload.get("html_url", "")),
            sha=str(payload.get("sha", "")),
            evidence_status=EvidenceStatus.CONFIRMED,
        )

    def search_docs(self, query: str) -> tuple[DocumentSearchResult, ...]:
        normalized = query.strip().casefold()
        if not normalized:
            raise ValidationError("query must not be empty")
        results: list[DocumentSearchResult] = []
        for ref in self.list_documents():
            document = self.get_doc(ref.path)
            matches = document.content.casefold().count(normalized)
            if matches:
                results.append(DocumentSearchResult(document=document, matches=matches))
        return tuple(
            sorted(results, key=lambda item: (-item.matches, item.document.path))
        )

    def get_adr(self, name: str) -> Document:
        normalized = name.strip()
        if not normalized:
            raise ValidationError("ADR name must not be empty")
        if "/" in normalized or normalized.lower().endswith((".md", ".mdx")):
            candidates: tuple[str, ...] = (normalized,)
        else:
            candidates = (f"docs/adr/{normalized}.md", f"docs/adr/{normalized}.mdx")
        for path in candidates:
            try:
                return self.get_doc(path)
            except NotFoundError:
                continue
        raise NotFoundError(f"ADR {name!r} was not found")

    def get_project_architecture(self, project: str) -> Document:
        normalized = project.strip()
        if not normalized:
            raise ValidationError("project must not be empty")
        matches = self.search_docs(normalized)
        for result in matches:
            path = result.document.path.lower()
            if "architecture" not in path:
                continue
            if normalized.casefold() in result.document.content.casefold():
                return result.document
        raise NotFoundError(
            f"No architecture document was found for project {project!r}"
        )

    def list_adrs(self) -> tuple[DocumentRef, ...]:
        return tuple(
            ref for ref in self.list_documents() if ref.path.startswith("docs/adr/")
        )

    def list_architecture_docs(self) -> tuple[DocumentRef, ...]:
        refs: list[DocumentRef] = []
        for ref in self.list_documents():
            path = ref.path
            if path == "ARCHITECTURE.md" or path.lower().startswith(
                "docs/architecture/"
            ):
                refs.append(ref)
        return tuple(refs)

    def search_docs_scoped(
        self, query: str, *, path_prefix: str | None = None
    ) -> tuple[DocumentSearchResult, ...]:
        if path_prefix is not None:
            prefix = path_prefix.strip().rstrip("/")
            if prefix:
                _validate_path(prefix)
            else:
                prefix = ""
        else:
            prefix = ""
        results = self.search_docs(query)
        if not prefix:
            return results
        return tuple(
            item
            for item in results
            if item.document.path == prefix
            or item.document.path.startswith(prefix + "/")
        )

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{GITHUB_API}{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "Yasin-MCP",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token.get_secret_value()}"
        return self._requester(url, headers, self._timeout)


def _is_text_document(path: str) -> bool:
    return path.lower().endswith((".md", ".mdx", ".txt", ".yaml", ".yml", ".json"))


def _validate_path(path: str) -> None:
    if not path or path.startswith("/") or ".." in path.split("/"):
        raise ValidationError("invalid documentation path")


def _request_json(url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:  # nosec B310
            raw = response.read(MAX_DOCUMENT_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 401:
            raise UnauthenticatedError("GitHub authentication failed") from exc
        if exc.code == 404:
            raise NotFoundError("YASIN-DOCS resource was not found") from exc
        if exc.code == 403:
            raise RateLimitedError(
                "GitHub denied the request or rate limit was reached"
            ) from exc
        raise UpstreamError(f"GitHub returned HTTP {exc.code}") from exc
    except TimeoutError as exc:
        raise TimeoutMcpError("GitHub request timed out") from exc
    except URLError as exc:
        raise UnavailableDependencyError("GitHub is unavailable") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpstreamError("GitHub returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise UpstreamError("GitHub returned an unexpected JSON shape")
    return value
