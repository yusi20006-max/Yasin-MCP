# Stage 6 — Ecosystem Integration Contracts (Issue #87)

**Evidence class:** CONFIRMED for in-repo contracts and tests; TARGET/UNRESOLVED for live Agent/Hub sessions and authentication.

## Architectural boundary

```text
YasinHub / Control Plane (orchestration — OUT of this repo)
        │
        ▼
Yasin-Agent (MCP client — OUT of this repo)
        │  asserted IntegrationContext + MCP tools/call
        ▼
Yasin-MCP (this repository)
        │
        ├─ IntegrationContext (typed, validated, ASSERTED)
        ├─ GovernanceGate (ALLOW / DENY / APPROVAL_REQUIRED)
        ├─ Policy + Audit
        └─ Tool execution only on ALLOW
```

Yasin-MCP remains the **governed execution boundary**. It does not host agent loops, Hub UI, or a Control Plane service.

## Ecosystem reconnaissance

| Repository | HTTP | Finding | Class |
|------------|------|---------|-------|
| Yasin-MCP | local | Governed MCP stdio server; `GovernanceContext`; agent client contract 1.0.0 | CONFIRMED |
| Yasin-Agent | 200 | Exists under `yusi20006-max`; no mandatory MCP dependency per Yasin-MCP contract | CONFIRMED (existence) |
| YasinHub | 200 | Exists under `yusi20006-max` | CONFIRMED (existence) |
| Yasin-Core | 200 | Exists under `yusi20006-max` | CONFIRMED (existence) |
| YasinCLI | 404 | No public repo under that name at assessment time | UNRESOLVED |
| YasinCore (no hyphen) | 404 | Use `Yasin-Core` naming | UNRESOLVED as alternate name |
| Live Agent→MCP session | — | Not executed in this stage | UNRESOLVED |
| Stdio peer authentication | — | Not provided by MCP stdio transport | UNRESOLVED |

## Integration context contract

**Version:** `1.0.0` (`INTEGRATION_CONTRACT_VERSION`)

| Field | Required | Trust |
|-------|----------|-------|
| client_id | optional | ASSERTED |
| agent_id | optional | ASSERTED |
| project_id | optional | ASSERTED |
| workspace_id | optional | ASSERTED |
| task_id | optional | ASSERTED |
| session_id | optional | ASSERTED |
| request_id | optional | ASSERTED |
| correlation_id | optional | ASSERTED |
| extra | optional | ASSERTED; no sensitive keys; scalar values only |

Rules:

- Typed + validated (`IntegrationContext` / `from_mapping`)
- Malformed context → `ValidationError` (fail closed)
- Caller cannot set `trust=trusted`
- Metadata **cannot** escalate privileges under `DefaultConservativePolicy`
- Maps to `GovernanceContext` for gate/audit

## Trust model

| Classification | Meaning on stdio |
|----------------|------------------|
| ASSERTED | Client-supplied; unauthenticated |
| TRUSTED | Requires authentication layer — **not available** on stdio |
| UNRESOLVED | Authentication placement for future transports |

**Privilege escalation via metadata:** CONFIRMED prevented under default policy.

## Capability / versioning

| Version surface | Value |
|-----------------|-------|
| Integration contract | `1.0.0` |
| Agent client contract | `1.0.0` |
| Capability surface | `CAPABILITY_SURFACE_VERSION` |

## Agent / Hub boundaries

- Agent: stdio MCP client; non-mandatory; cannot bypass GovernanceGate
- Hub: discovery via `surface_info()`; no second execution path
- Approval: `APPROVAL_REQUIRED` = do not execute; no approval UI in Stage 6

## Error contract

SDK error bridge **not** implemented (non-blocking; same as Stages 4–5).

## Explicit non-goals

Agent orchestration, Hub UI, Control Plane service, Telegram, PWA, approval UI, fleet management, deployment, PyPI, Stage 7+.
