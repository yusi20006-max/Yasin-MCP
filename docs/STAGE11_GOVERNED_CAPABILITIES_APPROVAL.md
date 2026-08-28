# Stage 11 — Governed Non-Read-Only Capabilities & Approval

**Issue #97** (part of #96)

## Execution order

credential → authentication → identity/context binding → approval validation → policy → ALLOW → tool

## Reference capabilities

| Tool | Risk |
|------|------|
| `yasin_gov_ping_low_risk` | LOW_RISK |
| `yasin_gov_apply_mark` | MUTATION |

## Approval model

Server-issued opaque tokens via `InMemoryApprovalStore`; single-use, expiring, bound to tool/subject/request/project. Caller `approval_status=granted` is not trusted without a server token.

## Policy

MUTATION without grant → APPROVAL_REQUIRED. With grant → ALLOW. HIGH_RISK → DENY (approval does not override).

## Non-goals

Hub UI, Telegram/PWA, Control Plane, Stages 12–15.
