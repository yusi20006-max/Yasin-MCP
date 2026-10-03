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
| `runflare_status` | status/events | READ_ONLY | autonomous |
| `runflare_events` | events | READ_ONLY | autonomous |
| `runflare_logs` | logs | READ_ONLY | autonomous |
| `runflare_deploy` | deploy | MUTATION | governance approval |
| `runflare_start` | start | MUTATION | governance approval |
| `runflare_restart` | restart | MUTATION | governance approval |
| `runflare_stop` | stop | MUTATION | explicit confirmation |

There is no generic shell or `run_command(command: string)` capability.

## CLI compatibility

The provider targets the documented official CLI contract:

- `runflare deploy -y`
- `runflare events -y`
- `runflare events -y -f`
- `runflare logs -y`
- `runflare logs -y -f`
- `runflare start -y`
- `runflare restart -y`

Runflare documents `-y` as the cached-project/service selection path, which is required for non-interactive execution. citeturn0search0turn0search1turn0search2

Yasin-MCP includes a read-only compatibility probe in
`yasin_mcp.providers.runflare.compatibility`. It checks `--version`,
top-level `--help`, and command-level `--help` only. It never executes
deploy/start/restart/stop.

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
non-destructive events/logs diagnostics.

## Configuration

- `RUNFLARE_PROJECT_DIR` — explicit project directory
- `RUNFLARE_ALLOWED_PROJECT_ROOT` — mandatory filesystem boundary
- `RUNFLARE_BIN` — must resolve to the official `runflare` executable
- `RUNFLARE_TIMEOUT_SECONDS` — bounded CLI execution timeout
- `RUNFLARE_MAX_OUTPUT` — bounded/redacted output size

## Hermes integration contract

The existing `yusi20006-max/hermes-runflare` deployment uses a Dockerized
Hermes gateway on Runflare. Its documented service contract is project
`hermes`, service `hermes-gate`, port 8000, with persistent data at
`/opt/data`. The repository keeps Telegram/Bale/provider credentials in
Runflare environment variables rather than source files. No Hermes-side
change is required by the Yasin-MCP provider contract.

For Hermes, Yasin-MCP is an operational control/diagnostic plane; it does not
replace Hermes application credentials, messaging configuration, or startup
process.

## Migration note

This provider supersedes the standalone implementation in
`yusi20006-max/Yasin-Runflare-MCP`. The standalone repository is retained
during migration for source/reference comparison; it is not deleted automatically.
