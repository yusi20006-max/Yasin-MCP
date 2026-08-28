# Stage 14 — Production Resilience

Baseline: `0c345c066e21a1269685c20e8a8c3ae445f1f3f3` (post-Stage-13 main).

## Concurrency model

`ServerConfig.max_concurrent_requests` is enforced at the governed MCP tool wrapper with a `threading.BoundedSemaphore`. The default remains 32 and the existing configuration bounds remain unchanged.

A request that cannot acquire a slot is rejected before `GovernanceGate.execute()` and therefore before authentication-derived execution, approval consumption, policy execution, or the protected tool function. The client receives the stable `CONCURRENCY_LIMIT` error code with only the configured limit in details.

Slots are released in a `finally` block after every admitted request, including failures.

## Fault containment

The Stage 14 tests prove that:

- an over-limit request does not execute protected work;
- the rejection payload is secret-free;
- a failed admitted request releases its slot;
- a subsequent request can execute normally after an upstream failure.

Existing OperationsAdapter coverage continues to provide deterministic evidence for subprocess timeout, missing executable, malformed response, oversized response, and fixed-argv/shell-disabled behavior. The adapter remains read-only and unavailable environments are reported as unresolved rather than represented as live success.

## Scope confirmation

This stage does not introduce a new transport or authentication protocol, ecosystem orchestration, UI, packaging/release publication, or a rewrite of Yasin-Agent/YasinHub.
