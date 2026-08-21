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

**P0, P1, P2, and P3 are complete.** The repository is currently
**READY_FOR_CONTROLLED_RELEASE**.

This status means the read-only MCP server has passed its repository,
architecture, security-boundary, quality, and live stdio protocol
validation gates. It is intentionally **not** classified as
`PRODUCTION_READY` because vendor-specific external client sessions
and always-on live upstream smoke tests are not mandatory evidence in
this repository.

### Completed phases

- **P0 — Audit foundation:** Issues #35–#37 complete, including the
  live MCP stdio audit with the official `mcp` client.
- **P1 — Ecosystem integration and contracts:** Issues #38–#45
  complete, covering YASIN-DOCS, GitHub, project registry,
  Operations, agent/evidence contracts, E2E integration coverage,
  and prompt-injection hardening.
- **P2 — Runtime hardening:** P2-1 through P2-9 complete, including
  untrusted-context enforcement, live MCP regression harness,
  capability-surface versioning, request correlation and reliability
  policy, registry validation, Operations discovery, and external
  client smoke procedures.
- **P3 — Documentation and release readiness:** Issues #51–#53
  complete, including architecture documentation, operational
  runbook, release-readiness assessment, and residual untrusted-data
  path fixes.

### Current evidence classification

- MCP protocol and current tool surface: **CONFIRMED / LIVE_RUNTIME**
- Read-only and deny-by-default boundaries: **CONFIRMED**
- Untrusted content envelopes: **CONFIRMED**
- Reliability and bounded retry policy: **CONFIRMED**
- CI quality gates: **CONFIRMED**
- Hermes live integration: **UNRESOLVED**
- Yasin-Agent live session: **UNRESOLVED**
- Optional live GitHub/Docs upstream CI: **UNRESOLVED / not required**
- Global MCP-level request middleware: **PARTIAL**

These classifications are deliberate. `UNRESOLVED` must never be
presented as `CONFIRMED` merely because an integration is documented.

## Architecture boundary

- Yasin-MCP does **not** replace YASIN-DOCS, Yasin-Core, Yasin-Agent,
  Yasin-AI, YasinHub, YasinCLI, or Yasin-Operations.
- The MCP surface is strictly **read-only**: no repository mutation,
  deployment, lifecycle mutation (start/stop/restart), memory mutation,
  or arbitrary shell/command execution.
- No private cross-repository imports. Integrations use public APIs,
  SDKs, contracts, or explicit read-only adapters.
- Existing Yasin projects must not become dependent on Yasin-MCP.
- A deny-by-default policy boundary (`policies/policy.py`) rejects
  forbidden or mutating capabilities at construction time.

## Tool surface

Always available:

- `yasin_docs_*` — documentation access
- `yasin_github_*` — read-only GitHub ecosystem access
- `yasin_registry_*` — project/dependency registry access

Conditionally available:

- `yasin_operations_*` — registered only when the
  `yasin-operations` executable is available on `PATH`.

The exact capability surface is versioned independently through
`CAPABILITY_SURFACE_VERSION` and exposed through `surface_info()`.

## Package layout

```
src/yasin_mcp/
    server/        MCP server runtime
    protocol/      MCP protocol types/boundary
    capabilities/  capability descriptor + discovery
    tools/         MCP tool implementations
    resources/     MCP resource implementations
    adapters/      domain adapters: YASIN-DOCS, GitHub, Operations
    policies/      deny-by-default policy boundary
    errors/        structured error model
    audit/         structured logging, correlation IDs
    config/        configuration model, secret handling
    version.py     package version, EvidenceStatus and surface version
```

## Evidence model

Responses that report ecosystem state should tag information with
one of:

- `CONFIRMED` — directly observed from a live, authoritative source
- `TARGET` — documented intent/architecture, not verified against a
  running system
- `PROPOSED` — a suggestion or plan, not yet implemented anywhere
- `UNRESOLVED` — could not be determined; must not be presented as fact

## Security boundary

Yasin-MCP treats retrieved documentation, GitHub content, registry
content, and Operations output as external/untrusted data. Structural
trust envelopes preserve the distinction between retrieved data and
instructions; keyword detection is not treated as a sufficient
security control.

The server is intentionally read-only and deny-by-default. There is
no generic shell passthrough, arbitrary command execution, mutation
surface, or implicit trust elevation for external content.

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

## Termux / Android

Yasin-MCP is intended to be runnable on Termux as a normal Python
package and does not require a desktop-only runtime.

Recommended baseline:

- Termux with a current Python 3.x package
- Git
- A network connection for GitHub/YASIN-DOCS integrations
- Optional `yasin-operations` executable only when Operations tools
  are required

Basic installation:

```bash
pkg update
pkg install git python

git clone https://github.com/yusi20006-max/Yasin-MCP.git
cd Yasin-MCP
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run the MCP server over stdio:

```bash
yasin-mcp
```

For a minimal installation without development tooling:

```bash
pip install -e .
yasin-mcp
```

Termux support is a compatibility target and should be validated on a
real Android/Termux environment before being treated as a confirmed
platform-specific release claim.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
mypy src
bandit -q -r src
```

## Documentation index

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Post-P2 architecture and evidence map |
| [RUNBOOK.md](docs/RUNBOOK.md) | Install, run, diagnose, failure modes |
| [RELEASE_READINESS.md](docs/RELEASE_READINESS.md) | Controlled-release assessment |
| [CLIENT_RUNTIME.md](docs/CLIENT_RUNTIME.md) | Stdio client config and smoke checklist |
| [CAPABILITY_SURFACE.md](docs/CAPABILITY_SURFACE.md) | Surface version semantics |
| [LIVE_MCP_HARNESS.md](docs/LIVE_MCP_HARNESS.md) | Live runtime evidence class |
| [OPERATIONS_INTEGRATION.md](docs/OPERATIONS_INTEGRATION.md) | Optional Operations gateway |
| [REGISTRY_INTEGRATION.md](docs/REGISTRY_INTEGRATION.md) | Registry consumer contract |
| [RELIABILITY.md](docs/RELIABILITY.md) | Retry policy |
| [OBSERVABILITY.md](docs/OBSERVABILITY.md) | Correlation and redaction |
