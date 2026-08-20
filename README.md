# Yasin-MCP

Standalone AI/Agent-facing MCP (Model Context Protocol) access and
integration layer for the Yasin ecosystem.

## Mission

Yasin-MCP exposes read-only, structured access to Yasin ecosystem
information (project registry, documentation, GitHub repository
state, runtime diagnostics) through the MCP protocol, so AI agents
and MCP clients can query the ecosystem's state without needing
direct, unbounded access to any individual repository or service.

## Status

**Phase 0, Issue #1 (Repository Bootstrap and Engineering Baseline)
only.** No MCP server runtime exists yet. No domain adapter
(YASIN-DOCS, GitHub, Yasin-Operations) exists yet. This issue only
establishes the package structure, tooling, and the safety
primitives (error model, deny-by-default policy, secret handling)
that everything else will build on.

### A note on architecture provenance

The originating task description for this project states that
YASIN-DOCS is "the canonical architecture and boundary" for
Yasin-MCP. Direct verification against the `yusi20006-max/YASIN-DOCS`
repository (both a code search for "Yasin-MCP"/"MCP" and a direct
check of `PROJECT_REGISTRY.yaml` and `ECOSYSTEM.md`) found **no
mention of Yasin-MCP anywhere in that repository** as of this issue.

This means the architecture implemented here is derived directly
from this project's own Issue #1–#10 descriptions (which are
detailed and self-consistent), not from a YASIN-DOCS document that
does not currently exist. If/when YASIN-DOCS is updated to include
Yasin-MCP, that should become the source of truth and this note
should be removed or updated to reflect where it now lives.

## Architecture boundary

- Yasin-MCP does **not** replace YASIN-DOCS, Yasin-Core, Yasin-Agent,
  Yasin-AI, YasinHub, YasinCLI, or Yasin-Operations.
- Phase 1 is strictly **read-only**: no repository mutation, no
  deployment, no lifecycle mutation (start/stop/restart), no memory
  mutation, no arbitrary shell/command execution.
- No private cross-repository imports. Integrations use public
  APIs, SDKs, contracts, or explicit read-only adapters.
- Existing Yasin projects must not become dependent on Yasin-MCP.
- A deny-by-default policy boundary (`policies/policy.py`) rejects
  any capability whose name matches a forbidden pattern (`exec`,
  `shell`, `command`, `request`, `arbitrary`, `filesystem`,
  `deploy`, `delete`, `start_`/`stop_`/`restart_`) or that declares
  itself mutating while Phase 1 is in effect — enforced at
  construction time, not just at registration.

## Package layout

```
src/yasin_mcp/
    server/        MCP server runtime (Issue #4)
    protocol/       MCP protocol types/boundary (Issue #2)
    capabilities/   capability descriptor + discovery (Issue #2)
    tools/          MCP tool implementations (Issue #4+)
    resources/      MCP resource implementations (Issue #4+)
    adapters/       domain adapters: YASIN-DOCS, GitHub, Yasin-Operations (Issue #5-7)
    policies/       deny-by-default policy boundary
    errors/         structured error model (McpError + ErrorCategory)
    audit/          structured logging, correlation IDs
    config/         configuration model, secret handling
    version.py      package version, EvidenceStatus enum
```

## Evidence model

Responses that report ecosystem state should tag information with
one of:

- `CONFIRMED` — directly observed from a live, authoritative source
- `TARGET` — documented intent/architecture, not verified against a
  running system
- `PROPOSED` — a suggestion or plan, not yet implemented anywhere
- `UNRESOLVED` — could not be determined; must not be presented as fact

## Yasin-Operations integration

Yasin-MCP exposes four read-only MCP tools over Yasin-Operations
(`yasin_operations_list_services`, `yasin_operations_service_status`,
`yasin_operations_health`, `yasin_operations_diagnostics`), via a
subprocess adapter that never imports the `yasin_operations` package
directly and is registered only when the `yasin-operations`
executable is available. See
[`docs/OPERATIONS_INTEGRATION.md`](docs/OPERATIONS_INTEGRATION.md)
for the full architecture, safety boundary, availability behavior,
and known limitations.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
mypy src
bandit -q -r src
```
