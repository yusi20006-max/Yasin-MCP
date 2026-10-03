# Runflare provider

Runflare is an independent provider unit inside Yasin-MCP. It is not a generic shell bridge and does not expose the Runflare API directly.

## Boundary

```text
MCP client
   ↓
Yasin-MCP governance
   ↓
Runflare provider
   ↓
official `runflare` CLI
   ↓
Runflare project
```

The provider uses authentication already configured for the official CLI. Credentials are never MCP arguments, tool results, repository files, CI secrets, or logs.

## Scoped operations

- status/events: non-destructive diagnostics
- events/logs: bounded and redacted observation
- deploy: normal release operation when the explicitly configured target satisfies the deployment gate
- start/restart: operational controls
- stop: confirmation-gated outside the provider

There is deliberately no `run_command(command: string)` capability.

## Configuration

- `RUNFLARE_PROJECT_DIR` — explicit project directory
- `RUNFLARE_ALLOWED_PROJECT_ROOT` — optional filesystem boundary
- `RUNFLARE_BIN` — must resolve to the `runflare` executable
- `RUNFLARE_TIMEOUT_SECONDS` — bounded CLI execution timeout
- `RUNFLARE_MAX_OUTPUT` — bounded/redacted output size

## Migration note

This provider supersedes the standalone implementation in `yusi20006-max/Yasin-Runflare-MCP`. The standalone repository is retained during migration for source/reference comparison; it is not deleted automatically.
