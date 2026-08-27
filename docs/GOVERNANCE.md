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

## Stage 4 security guarantees (Issue #82)

Proven by audit and regression tests (`tests/test_governance_security.py`):

| Guarantee | Evidence |
|-----------|----------|
| Centralized enforcement | All production `ServerRuntime` tools register via `gate.wrap_tool` only |
| ALLOW executes once | Invocation count == 1 |
| DENY / APPROVAL_REQUIRED | Invocation count == 0; no auto-approval |
| Unknown tools | `known=False` → DENY → no execution |
| Policy / decision failure | Fail-closed: exception or `ValidationError`; no execution |
| Invalid metadata | Empty names / non-`RiskLevel` rejected |
| Context isolation | Per-request `GovernanceContext`; no cross-request leakage |
| Trusted agent context | Does **not** elevate DENY → ALLOW under default policy |
| Secret redaction | Sensitive keys redacted in audit payloads |
| Execution failure audit | Exception **type** only (no exception value / secret payload) |
| Operations tools | When registered, same `add_governed` path |

### tools/list vs execution

`tools/list` may expose a tool that policy would DENY or mark APPROVAL_REQUIRED.
Governance controls **execution**, not discovery. Hiding tools is not used as a security mechanism.

### Known limitations

- MCP SDK may map `PolicyDeniedError` to a generic `UnexpectedToolError` on the client.
  Protocol remains safe (`isError`); decision details stay in server-side audit. Optional future error-bridge.
- No human approval product, Control Plane, or agent fleet management in this repository.
