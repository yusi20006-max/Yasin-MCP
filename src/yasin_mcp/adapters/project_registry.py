"""Read-only normalization of the YASIN-DOCS project registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yasin_mcp.adapters.docs import YasinDocsAdapter
from yasin_mcp.errors.errors import NotFoundError, UnavailableDependencyError, ValidationError
from yasin_mcp.version import EvidenceStatus

REGISTRY_CANDIDATES = (
    "docs/projects/PROJECT_REGISTRY.yaml",
    "docs/projects/PROJECT_REGISTRY.yml",
    "PROJECT_REGISTRY.yaml",
    "PROJECT_REGISTRY.yml",
)


@dataclass(frozen=True)
class ProjectMetadata:
    name: str
    repository: str | None
    documentation: str | None
    status: str | None
    owner: str | None
    source_path: str
    source_url: str
    evidence_status: EvidenceStatus


class ProjectRegistryAdapter:
    """Expose only registry-backed project metadata."""

    def __init__(self, docs: YasinDocsAdapter) -> None:
        self._docs = docs

    def list_projects(self) -> tuple[ProjectMetadata, ...]:
        data, source = self._load_registry()
        entries = _extract_entries(data)
        return tuple(self._normalize(entry, source) for entry in entries)

    def get_project(self, name: str) -> ProjectMetadata:
        normalized = name.strip().casefold()
        if not normalized:
            raise ValidationError("project name must not be empty")
        for project in self.list_projects():
            if project.name.casefold() == normalized:
                return project
        raise NotFoundError(f"project {name!r} is not present in the registry")

    def _load_registry(self) -> tuple[Any, Any]:
        for path in REGISTRY_CANDIDATES:
            try:
                document = self._docs.get_doc(path)
            except NotFoundError:
                continue
            return _parse_registry(document.content), document
        raise UnavailableDependencyError(
            "YASIN-DOCS project registry is unavailable or not documented"
        )

    @staticmethod
    def _normalize(entry: dict[str, Any], source: Any) -> ProjectMetadata:
        name = _first_string(entry, "name", "project", "id")
        if not name:
            raise ValidationError("project registry entry is missing a name")
        return ProjectMetadata(
            name=name,
            repository=_first_string(entry, "repository", "repo", "github"),
            documentation=_first_string(entry, "documentation", "docs", "doc"),
            status=_first_string(entry, "status", "state"),
            owner=_first_string(entry, "owner", "maintainer"),
            source_path=source.path,
            source_url=source.source_url,
            evidence_status=source.evidence_status,
        )


def _parse_registry(content: str) -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise UnavailableDependencyError(
            "PyYAML is required to parse the YASIN-DOCS project registry"
        ) from exc
    try:
        value = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValidationError("YASIN-DOCS project registry is invalid YAML") from exc
    if not isinstance(value, (dict, list)):
        raise ValidationError("YASIN-DOCS project registry must be a mapping or list")
    return value


def _extract_entries(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    for key in ("projects", "repositories", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [
                {"name": name, **item}
                for name, item in value.items()
                if isinstance(item, dict)
            ]
    return [data]


def _first_string(entry: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
