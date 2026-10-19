# Coding Agent Prompt: FP-TB-000 — Governance Tracer Bullet

Use this prompt together with `FP-TB-000-governance-tracer-bullet.md`.

```text
You are implementing Feature Planning Pack FP-TB-000-governance-tracer-bullet.

You MUST implement only TB-000 governance tracer proof scope.

Project rules:
- Root module namespace MUST be Ticketing.
- OTP app atom MUST be :ticketing.
- Ash posture MUST be Ash 3.x only.
- Do not use V42.* module prefixes.
- Do not implement product behaviour.
- Do not create orders, payments, seats, tickets, refunds, payouts, scanner admission, ledger posting, tenant switching, or dynamic pricing.
- Do not name AirlockTrace as AuditLog.
- Do not promote AirlockTrace into audit subsystem.

Before editing:
1. Read FP-TB-000-governance-tracer-bullet.md.
2. Inspect existing repo scaffold from FP-MVP0-000.
3. Locate docs/domain_map/00_DOMAIN_MAP.md or equivalent.
4. Locate trace validator placeholder.
5. Locate test structure and Oban/Ash setup.
6. Stop if scaffold pack is missing or incomplete.

Implement:
1. Ticketing.System.HealthCheck with TB-000 trace metadata.
2. Ticketing.System.AirlockTrace Ash resource with tenant key org_id.
3. AirlockTrace migration/table parity with org_id.
4. Ticketing.System.AirlockTraceWorker with Oban queue :ops and explicit org_id, correlation_id, idempotency_key.
5. Domain Map rows for HealthCheck, AirlockTrace, and AirlockTraceWorker.
6. Generated Domain Map artifact or a deterministic placeholder if generator is not yet implemented.
7. Trace validator checks for TB000-001 through TB000-016.
8. Tests proving TB-000 scope and non-product boundaries.
9. Evidence report under vault/Control or equivalent.

Acceptance:
- mix compile passes.
- mix test passes for TB-000 tests.
- TB000-001 through TB000-016 are reported as pass/fail, not omitted.
- Product domains are not referenced.
- Direct Repo is not used in governed flow.

Stop and report a blocker if:
- Ash/Oban is not configured enough to implement the worker/resource safely;
- Domain Map format is missing or malformed;
- trace validator cannot be implemented without inventing source law;
- any product behaviour becomes necessary.

Final response required:
- Pack implemented
- Changed files
- Tests added
- Tests run
- Gates run
- Evidence report path
- Blockers
- Non-goals intentionally not touched
- Next recommended pack: FP-CI-001-deterministic-uuid-binary-sort
```
