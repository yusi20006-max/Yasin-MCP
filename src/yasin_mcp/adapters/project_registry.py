"""Read-only normalization of the YASIN-DOCS project registry.

Unknown fields stay unknown. Dependency direction is explicit when present.
Malformed or nameless entries are skipped during list; invalid YAML raises
ValidationError. Missing registry file raises UnavailableDependencyError
(runtime UNRESOLVED).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yasin_mcp.adapters.docs import YasinDocsAdapter
from yasin_mcp.errors.errors import NotFoundError, UnavailableDependencyError, ValidationError
from yasin_mcp.security.untrusted_context import attach_untrusted_envelope
from yasin_mcp.version import EvidenceStatus

# Canonical search order for the cross-repository registry file.
# First hit wins; paths are relative to the configured YASIN-DOCS root.
REGISTRY_CANDIDATES = (
    "docs/projects/PROJECT_REGISTRY.yaml",
    "docs/projects/PROJECT_REGISTRY.yml",
    "PROJECT_REGISTRY.yaml",
    "PROJECT_REGISTRY.yml",
)


@dataclass(frozen=True)
class ProjectMetadata:
    name: str
    role: str | None
    repository: str | None
    documentation: str | None
    status: str | None
    owner: str | None
    dependencies: tuple[str, ...]
    public_contracts: tuple[str, ...]
    operational_state: str | None
    mcp_capabilities: tuple[str, ...]
    source_path: str
    source_url: str
    evidence_status: EvidenceStatus

    def as_dict(self) -> dict[str, Any]:
        marker_bits = [self.name]
        if self.role:
            marker_bits.append(self.role)
        if self.documentation:
            marker_bits.append(self.documentation)
        base = {
            "name": self.name,
            "role": self.role,
            "repository": self.repository,
            "documentation": self.documentation,
            "status": self.status,
            "owner": self.owner,
            "dependencies": list(self.dependencies),
            "public_contracts": list(self.public_contracts),
            "operational_state": self.operational_state,
            "mcp_capabilities": list(self.mcp_capabilities),
            "source_path": self.source_path,
            "source_url": self.source_url,
            "evidence_status": self.evidence_status.value,
            "provenance": {
                "source": "yasin-docs-registry",
                "path": self.source_path,
                "source_url": self.source_url,
            },
        }
        return attach_untrusted_envelope(
            base,
            source="yasin-docs-registry",
            text_for_markers="\n".join(marker_bits),
        )


class ProjectRegistryAdapter:
    """Expose only registry-backed project metadata."""

    def __init__(self, docs: YasinDocsAdapter) -> None:
        self._docs = docs

    def list_projects(self) -> tuple[ProjectMetadata, ...]:
        data, source = self._load_registry()
        entries = _extract_entries(data)
        results: list[ProjectMetadata] = []
        for entry in entries:
            try:
                results.append(self._normalize(entry, source))
            except ValidationError:
                # Nameless / unusable entries are skipped so one bad row
                # does not poison the whole catalog.
                continue
        return tuple(results)

    def get_project(self, name: str) -> ProjectMetadata:
        normalized = name.strip().casefold()
        if not normalized:
            raise ValidationError("project name must not be empty")
        for project in self.list_projects():
            if project.name.casefold() == normalized:
                return project
        raise NotFoundError(f"project {name!r} is not present in the registry")

    def list_dependencies(self, name: str) -> dict[str, Any]:
        project = self.get_project(name)
        base: dict[str, Any] = {
            "project": project.name,
            "depends_on": list(project.dependencies),
            "dependency_direction": "outbound",
            "evidence_status": project.evidence_status.value,
            "provenance": {
                "source": "yasin-docs-registry",
                "path": project.source_path,
                "source_url": project.source_url,
            },
            "unknowns": [] if project.dependencies else ["dependencies not declared in registry"],
        }
        return attach_untrusted_envelope(
            base,
            source="yasin-docs-registry",
            text_for_markers=project.name,
        )

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
            role=_first_string(entry, "role", "type", "kind"),
            repository=_first_string(entry, "repository", "repo", "github"),
            documentation=_first_string(entry, "documentation", "docs", "doc"),
            status=_first_string(entry, "status", "state"),
            owner=_first_string(entry, "owner", "maintainer"),
            dependencies=_string_list(entry, "dependencies", "depends_on", "deps"),
            public_contracts=_string_list(entry, "public_contracts", "contracts", "apis"),
            operational_state=_first_string(
                entry, "operational_state", "ops_state", "runtime_state"
            ),
            mcp_capabilities=_string_list(entry, "mcp_capabilities", "mcp_tools", "capabilities"),
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
    if value is None:
        raise ValidationError("YASIN-DOCS project registry is empty")
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
                {"name": name, **item} for name, item in value.items() if isinstance(item, dict)
            ]
    if isinstance(data, dict) and (
        "name" in data or "project" in data or "id" in data
    ):
        return [data]
    return []


def _first_string(entry: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _string_list(entry: dict[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, list):
            return tuple(
                str(item).strip()
                for item in value
                if isinstance(item, (str, int)) and str(item).strip()
            )
        if isinstance(value, str) and value.strip():
            return (value.strip(),)
    return ()
