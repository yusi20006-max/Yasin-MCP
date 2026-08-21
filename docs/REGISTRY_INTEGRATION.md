# Ecosystem Project Registry Integration

**Status:** CONFIRMED for adapter + MCP tools (Issue #40, hardened P2-6 / #70).

## Cross-repository contract

| Consumer | Producer | Artifact |
|----------|----------|----------|
| Yasin-MCP (`ProjectRegistryAdapter`) | YASIN-DOCS | `PROJECT_REGISTRY.yaml` (or `.yml`) |

Yasin-MCP does **not** own the registry file. It reads it through the
docs adapter using a fixed candidate path list. Schema expectations
below are the **consumer contract**; producer repos may add fields, but
unknown keys are ignored (never elevated to trust).

## Canonical path search order

First readable hit wins:

1. `docs/projects/PROJECT_REGISTRY.yaml`
2. `docs/projects/PROJECT_REGISTRY.yml`
3. `PROJECT_REGISTRY.yaml`
4. `PROJECT_REGISTRY.yml`

Paths are relative to the configured YASIN-DOCS document root.

## Schema expectations (consumer)

Supported top-level shapes:

- mapping with key `projects` | `repositories` | `items` → list of entries, **or**
  mapping of `name → fields`
- top-level list of entry mappings
- single entry mapping with a `name` / `project` / `id` field

Per-entry recognized fields (aliases in parentheses):

| Field | Type | Required |
|-------|------|----------|
| `name` (`project`, `id`) | string | **yes** (nameless rows skipped) |
| `role` (`type`, `kind`) | string | no |
| `repository` (`repo`, `github`) | string | no |
| `documentation` (`docs`, `doc`) | string | no |
| `status` (`state`) | string | no |
| `owner` (`maintainer`) | string | no |
| `dependencies` (`depends_on`, `deps`) | list[str] or str | no |
| `public_contracts` (`contracts`, `apis`) | list[str] or str | no |
| `operational_state` (`ops_state`, `runtime_state`) | string | no |
| `mcp_capabilities` (`mcp_tools`, `capabilities`) | list[str] or str | no |

Dependency direction is always **outbound** (`project → depends_on`).
Inbound or bidirectional graphs are out of scope.

## Tools

| Tool | Purpose |
|------|---------|
| `yasin_registry_list_projects` | List registry projects |
| `yasin_registry_get_project` | One project metadata |
| `yasin_registry_list_dependencies` | Outbound dependencies |

## Evidence and failure semantics

| Condition | Behavior | Evidence |
|-----------|----------|----------|
| Registry file readable, entry has name | Normalized metadata returned | **CONFIRMED** |
| Optional field absent | `null` / empty list; `unknowns` for missing deps | CONFIRMED (partial) |
| Empty `projects: []` | Empty list; tool may report `evidence_status: unresolved` | empty catalog |
| Nameless entry | **Skipped** (does not fail the list) | n/a |
| Invalid YAML / scalar / empty document | `ValidationError` | not returned |
| No candidate path found | `UnavailableDependencyError` | **UNRESOLVED** at runtime |
| PyYAML missing | `UnavailableDependencyError` | **UNRESOLVED** |

All successful payloads carry the untrusted-context envelope
(`source=yasin-docs-registry`). Registry content never elevates trust.

## Non-goals

- No write / mutate path against the registry file
- No inventing projects when the file is missing
- No cross-repo network calls beyond the docs adapter already in use
