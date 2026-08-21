# Ecosystem Project Registry Integration

**Status:** CONFIRMED for adapter + MCP tools (Issue #40).

## Source

YASIN-DOCS `PROJECT_REGISTRY.yaml` (candidate paths under `docs/projects/` or repo root).

## Tools

| Tool | Purpose |
|------|---------|
| `yasin_registry_list_projects` | List registry projects |
| `yasin_registry_get_project` | One project metadata |
| `yasin_registry_list_dependencies` | Outbound dependencies |

## Evidence model

- Declared fields → **CONFIRMED** when the registry file is readable
- Missing optional fields → `null` / empty; listed under `unknowns` for dependencies
- Registry unavailable → `UnavailableDependencyError` (UNRESOLVED at runtime)

Dependency direction is always **outbound** (`project → depends_on`).
