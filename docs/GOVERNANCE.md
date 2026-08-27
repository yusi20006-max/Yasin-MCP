# MCP Governance Layer

**Status:** CONFIRMED for Issue #80 (Stage 3).

Yasin-MCP owns **tool governance** for the MCP surface: risk metadata,
deterministic policy evaluation, centralized enforcement before execution,
and structured audit events.

Yasin-Agent (and other clients) own **orchestration**. Yasin-MCP does **not**
own agent fleet management, human approval UI, Hermes-specific policy, or
Control Plane workflows. The `APPROVAL_REQUIRED` decision is a governance
state only; it does not implement an approval product.

## Enforcement path

```text
MCP Client
    |
    v
tools/call
    |
    v
MCPServer tool manager
    |
    v
GovernanceGate.wrap_tool  (registered at ServerRuntime.create)
    |
    v
resolve ToolIdentity (ToolRiskCatalog)
    |
    v
GovernancePolicy.evaluate → GovernanceDecision
    |
    ├── DENY ───────────────► PolicyDeniedError (tool NOT executed)
    ├── APPROVAL_REQUIRED ──► PolicyDeniedError (tool NOT executed)
    └── ALLOW ──────────────► underlying tool function
                                  |
                                  ├── success → EXECUTION_RESULT audit
                                  └── failure → EXECUTION_FAILURE audit
```

Single enforcement boundary: `yasin_mcp.governance.gate.GovernanceGate`.
All production tools registered by `ServerRuntime` are wrapped through it.

## Decision model

| Decision | Meaning |
|----------|---------|
| `ALLOW` | Policy permits execution |
| `DENY` | Policy rejects; tool must not run |
| `APPROVAL_REQUIRED` | Execution withheld; tool must not run |

## Risk model

| Level | Default policy |
|-------|----------------|
| `READ_ONLY` | `ALLOW` |
| `LOW_RISK` | `ALLOW` |
| `MUTATION` | `APPROVAL_REQUIRED` |
| `HIGH_RISK` | `DENY` |

Current production tools are registered as `READ_ONLY`.

## Deny-by-default

Unknown tool → `known=False` → `DENY` → no execution.

## Audit

Events: `REQUEST`, `DECISION`, `EXECUTION_RESULT`, `EXECUTION_FAILURE`.
Payloads sanitized (token/secret/password/authorization/api_key/credential/…).

## Future integration

Yasin-Agent may supply `GovernanceContext`. Approval UI and Control Plane
orchestration remain outside this repository.
