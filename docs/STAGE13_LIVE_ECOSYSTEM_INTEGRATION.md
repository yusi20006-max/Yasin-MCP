# Stage 13 — Live Ecosystem Integration

Issue #99.

## Boundary

Yasin-Agent remains the orchestration layer. Yasin-MCP remains the governed execution boundary. The integration client uses the current Yasin-Agent public concepts (agent, task, session and context) and the MCP SDK Streamable HTTP transport.

```text
Yasin-Agent-compatible client
        │
        │ Authorization: Bearer
        │ X-Yasin-Context: JSON (ASSERTED)
        ▼
RequireBearerAuthMiddleware
        │
        ▼
IntegrationContext → auth binding → GovernanceGate
        │                         │
        │                         ├── policy
        │                         ├── approval
        │                         └── audit
        ▼
      tool
```

## Remote context contract

The optional `X-Yasin-Context` header carries the Stage 6 integration fields as a JSON object:

- `client_id`
- `agent_id`
- `project_id`
- `workspace_id`
- `task_id`
- `session_id`
- `request_id`
- `correlation_id`
- optional bounded `extra`

The header is validated through `IntegrationContext.from_mapping`. It is **ASSERTED** input, not authenticated identity. `TRUSTED` remains exclusively derived from the configured authentication subject after successful Bearer verification.

Malformed or oversized context fails closed with `INVALID_CONTEXT`.

## Live evidence

`tests/test_stage13_live_ecosystem_integration.py` starts the real Yasin-MCP Streamable HTTP application under uvicorn and uses the MCP Python SDK client. The path exercises:

1. initialize
2. tools/list
3. authenticated LOW_RISK execution
4. server-issued single-use MUTATION approval
5. approval-bound request/project/agent context
6. audit correlation
7. malformed context rejection
8. request-context isolation checks

The test deliberately does not pretend that Yasin-Agent currently provides a native MCP transport. The repository's README describes Yasin-Agent as transport-agnostic; the Stage 13 client is therefore a minimal compatibility boundary rather than a rewrite of Agent orchestration.

## Trust and security

- Caller context stays ASSERTED.
- Bearer authentication proves knowledge of the configured secret only.
- Configured `auth_subject_id` is the trusted subject.
- Auth does not grant authorization: HIGH_RISK remains denied and MUTATION requires approval.
- Approval remains server-issued, single-use, expiring, and bound to request/project/subject where configured.
- Secrets are not copied into tool arguments or audit payloads.

## Non-goals

- No Yasin-Agent orchestration rewrite.
- No YasinHub UI or Control Plane.
- No Telegram/PWA.
- No OAuth/OIDC or mTLS implementation.
- No release/PyPI work.
