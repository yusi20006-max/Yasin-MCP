# Stage 7.1 — Trusted Transport & Authentication Boundary (Issue #89)

## Core answer

**What does Yasin-MCP know about the identity of its caller on stdio?**

| Fact | Classification |
|------|----------------|
| Caller can supply IntegrationContext IDs | CONFIRMED / ASSERTED |
| Stdio proves remote/authenticated peer principal | **UNRESOLVED / unavailable** |
| Caller can set `trust=trusted` | CONFIRMED prevented |
| Optional shared-secret can prove knowledge of a configured secret | IMPLEMENTED |
| Shared-secret subject_id comes from **config**, not caller claims | IMPLEMENTED |

## Threat model (summary)

| Threat | Expected | Stage 7.1 behavior |
|--------|----------|-------------------|
| Claim another agent_id | ASSERTED only; no privilege | CONFIRMED — policy ignores elevation |
| Claim admin in extra | No escalation | CONFIRMED |
| Forge trust=trusted | Rejected | CONFIRMED |
| Impersonate after shared-secret auth (agent_id ≠ subject) | Fail closed | IMPLEMENTED |
| Invalid / missing credential when auth required | No tool path via bind | IMPLEMENTED |
| Secret in logs/audit | Never | CONFIRMED (SecretStr + redaction) |
| Cross-request identity leak | Isolated | IMPLEMENTED (request-scoped outcomes) |

## Architecture

```text
MCP request (stdio)
    → authenticate_stdio_peer()     → TRANSPORT_UNAVAILABLE (no TRUSTED peer)
    → optional shared-secret verify → AUTHENTICATED | INVALID | MISSING | …
    → bind_context(asserted, auth)  → fail closed on mismatch / require_auth
    → GovernanceGate                → ALLOW | DENY | APPROVAL_REQUIRED
    → tool only on ALLOW
```

Authentication **never** executes tools and **never** bypasses GovernanceGate.

## Trust model

| Class | Meaning |
|-------|---------|
| **ASSERTED** | Default for all IntegrationContext fields over stdio |
| **TRUSTED** | Only `AuthenticatedIdentity` from authenticators |
| **UNRESOLVED** | Stdio peer principal; future remote transport auth |

## Configuration

| Variable | Purpose |
|----------|---------|
| `YASIN_MCP_AUTH_TOKEN` | Optional shared secret (`SecretStr`) |
| `YASIN_MCP_AUTH_SUBJECT` | Subject ID on successful shared-secret auth |
| `YASIN_MCP_REQUIRE_AUTH` | If true, requires successful authentication |

## Explicit non-goals

Yasin-Agent/Hub/Control Plane integration, approval UI, remote TLS client auth, custom cryptography, Stage 8.

## Follow-up (TARGET)

Authenticated remote transports (HTTP + mTLS / OAuth) when non-stdio transport is adopted — separate issue.
