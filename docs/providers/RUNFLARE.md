# Runflare provider

Runflare is an independent provider unit inside Yasin-MCP. It is not a generic shell bridge and does not expose the Runflare API directly.

## Boundary

```text
MCP client
   ↓
Yasin-MCP capability registry
   ↓
GovernanceGate
   ↓
Scoped Runflare tools
   ↓
Runflare provider
   ↓
official `runflare` CLI
   ↓
Runflare project
```

The provider uses authentication already configured for the official CLI. Credentials are never MCP arguments, tool results, repository files, CI secrets, or logs.

## Phase 1 capability registry

Phase 1 registers stable capability contracts before exposing the operational tools. The registry metadata is the source of truth for governance risk and input boundaries.

| Capability | Operation | Risk | Execution policy |
| --- | --- | --- | --- |
| `runflare_status` | status | READ_ONLY | autonomous |
| `runflare_events` | events | READ_ONLY | autonomous |
| `runflare_logs` | logs | READ_ONLY | autonomous |
| `runflare_deploy` | deploy | MUTATION | governance approval |
| `runflare_start` | start | MUTATION | governance approval |
| `runflare_restart` | restart | MUTATION | governance approval |
| `runflare_stop` | stop | MUTATION | explicit confirmation |

The names intentionally use scoped provider identifiers rather than a generic command capability. The provider never registers or exposes `run_command(command: string)`.

Phase 1 does not expose the Runflare subprocess directly as an MCP tool. Subsequent phases bind the approved operations to typed tools, and each binding must go through `GovernanceGate`.

## Scoped operations

- status/events: non-destructive diagnostics
- events/logs: bounded and redacted observation
- deploy: normal release operation when the explicitly configured target satisfies the deployment gate
- start/restart: operational controls
- stop: confirmation-gated outside the provider

## Configuration

- `RUNFLARE_PROJECT_DIR` — explicit project directory
- `RUNFLARE_ALLOWED_PROJECT_ROOT` — optional filesystem boundary
- `RUNFLARE_BIN` — must resolve to the `runflare` executable
- `RUNFLARE_TIMEOUT_SECONDS` — bounded CLI execution timeout
- `RUNFLARE_MAX_OUTPUT` — bounded/redacted output size

## Migration note

This provider supersedes the standalone implementation in `yusi20006-max/Yasin-Runflare-MCP`. The standalone repository is retained during migration for source/reference comparison; it is not deleted automatically.
