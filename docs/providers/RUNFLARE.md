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

## Capability contract

| Capability | Operation | Risk | Execution policy |
| --- | --- | --- | --- |
| `runflare_status` | status | READ_ONLY | autonomous |
| `runflare_events` | event | READ_ONLY | autonomous |
| `runflare_logs` | log | READ_ONLY | autonomous |
| `runflare_deploy` | deploy | MUTATION | governance approval |
| `runflare_start` | start | MUTATION | governance approval |
| `runflare_restart` | restart | MUTATION | governance approval |
| `runflare_stop` | stop | MUTATION | explicit confirmation |

There is no generic shell or `run_command(command: string)` capability.

## CLI compatibility

The provider targets the official Runflare CLI 1.3.1 contract:

- `runflare status`
- `runflare deploy -y`
- `runflare event -y`
- `runflare event -y -f`
- `runflare log -y`
- `runflare log -y -f`
- `runflare start -y`
- `runflare restart -y`
- `runflare stop` (confirmation-gated; not exposed as a normal MCP tool)

MCP capability names remain `runflare_events` / `runflare_logs` for stable
tool identity; the provider maps them to the singular CLI verbs `event` /
`log`.

Runflare documents `-y` as the cached-project/service selection path, which is required for non-interactive execution.

Yasin-MCP includes a read-only compatibility probe in
`yasin_mcp.providers.runflare.compatibility`. It checks the `version`
subcommand, top-level `--help`, and command-level `--help` only. It never
executes deploy/start/restart/stop.

### Local live validation

Live validation is explicitly opt-in and is never part of CI:

```text
RUNFLARE_LIVE_TESTS=1
RUNFLARE_PROJECT_DIR=<existing project>
RUNFLARE_ALLOWED_PROJECT_ROOT=<parent directory>
pytest -q tests/providers/runflare/test_live_compatibility.py
```

The live checks require the existing official CLI authentication. They do not
accept or print credentials and only execute compatibility probes plus
non-destructive event/log diagnostics.

## Configuration

- `RUNFLARE_PROJECT_DIR` — explicit project directory
- `RUNFLARE_ALLOWED_PROJECT_ROOT` — mandatory filesystem boundary
- `RUNFLARE_BIN` — must resolve to the official `runflare` executable
- `RUNFLARE_TIMEOUT_SECONDS` — bounded CLI execution timeout
- `RUNFLARE_MAX_OUTPUT` — bounded/redacted output size

## Security invariants

- `shell=False` argv execution only
- official executable name enforced
- no user-controlled executable injection
- closed MCP tool inputs (no credential fields)
- project path constrained under allowed root
- stdout/stderr redacted and truncated
- `stop` confirmation-gated and not a normal MCP tool

## Hermes relationship

Hermes is a separate control/diagnostic plane; it does not
replace Hermes application credentials, messaging configuration, or startup
process.

## Migration note

This provider supersedes the standalone implementation in
`yusi20006-max/Yasin-Runflare-MCP`. The standalone repository is retained
during migration for source/reference comparison; it is not deleted automatically.
