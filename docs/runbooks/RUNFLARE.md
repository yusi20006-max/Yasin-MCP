# Runflare Operational Runbook

## Purpose

This runbook is the operator-facing procedure for the Runflare provider in Yasin-MCP. It covers configuration, read-only diagnostics, governed mutations, incident handling, and migration boundaries.

## Architecture

```text
MCP client
  -> Yasin-MCP capability registry
  -> GovernanceGate
  -> scoped Runflare tool
  -> RunflareCLI
  -> official runflare CLI
  -> explicitly configured project
```

The MCP layer never becomes a generic shell bridge.

## Permission matrix

| Operation | Risk | Autonomous | Confirmation |
|---|---|---:|---:|
| status | READ_ONLY | Yes | No |
| events | READ_ONLY | Yes | No |
| logs | READ_ONLY | Yes | No |
| deploy | MUTATION | No | Governance policy |
| start | MUTATION | No | Governance policy |
| restart | MUTATION | No | Governance policy |
| stop | MUTATION | No | Explicit confirmation |

The provider does not expose `runflare_stop` as an MCP tool. The capability remains registered so governance can represent the boundary.

## Required configuration

```text
RUNFLARE_PROJECT_DIR=/absolute/path/to/project
RUNFLARE_ALLOWED_PROJECT_ROOT=/absolute/path/to/allowed/root
```

Optional bounded execution settings:

```text
RUNFLARE_BIN=runflare
RUNFLARE_TIMEOUT_SECONDS=120
RUNFLARE_MAX_OUTPUT=12000
```

The project directory must exist and resolve beneath the configured allowed root. Credentials are supplied only through the official Runflare CLI authentication mechanism.

## Safe diagnostics

Before any mutation:

1. Confirm `RUNFLARE_PROJECT_DIR` points to the intended project.
2. Confirm it is beneath `RUNFLARE_ALLOWED_PROJECT_ROOT`.
3. Run status/events/log diagnostics.
4. Inspect sanitized output and return code.
5. Do not use a generic shell command or substitute another executable.

For local CLI compatibility validation:

```text
RUNFLARE_LIVE_TESTS=1
RUNFLARE_PROJECT_DIR=<existing project>
RUNFLARE_ALLOWED_PROJECT_ROOT=<parent directory>
pytest -q tests/providers/runflare/test_live_compatibility.py
```

This is never enabled by CI.

## Mutation procedure

For deploy/start/restart:

1. Verify the target project explicitly.
2. Verify the operation is permitted by GovernanceGate.
3. Verify no credential is supplied as an MCP argument.
4. Execute only the corresponding scoped tool.
5. Review bounded/redacted stdout/stderr and return code.
6. If the operation fails, stop and diagnose before retrying.

For stop, explicit confirmation is required and the current MCP surface does not expose the operation.

## Troubleshooting

### CLI not found
Check that the official executable is named `runflare` and that `RUNFLARE_BIN` does not point to another program.

### Project rejected
Check that the path exists and is contained by `RUNFLARE_ALLOWED_PROJECT_ROOT`. Do not weaken the boundary to make a path pass.

### Timeout
Treat a timeout as an incomplete operation. Inspect events/logs before retrying a mutation.

### Output contains a credential-like value
Do not copy or forward it. The provider redacts common authorization, API-key, token, password, and secret patterns. Report the sanitized result and investigate the upstream source separately.

### Authentication failure
Use the existing official Runflare CLI authentication flow. Never add credentials to MCP arguments, repository files, test fixtures, or CI configuration.

## Incident boundaries

- Never run `runflare reset --all` through the provider.
- Never introduce a generic `run_command` or shell tool.
- Never bypass the allowed project root.
- Never commit Runflare credentials.
- Never modify Hermes merely to satisfy a Yasin-MCP test.
- Never delete the standalone Yasin-Runflare-MCP repository as part of this migration.

## Migration

The standalone `yusi20006-max/Yasin-Runflare-MCP` repository remains retained for reference. Yasin-MCP is the active integration surface. Migration closure does not authorize deletion of the standalone repository.
