# Coding Agent Prompt: FP-CI-002 — Migration Safety Baseline

Use this prompt together with `FP-CI-002-migration-safety-baseline.md`.

```text
You are implementing Feature Planning Pack FP-CI-002-migration-safety-baseline.

You MUST implement only migration-safety tooling, tests, and CI/reporting scope.

Project rules:
- Root module namespace MUST be Ticketing.
- OTP app atom MUST be :ticketing.
- Ash posture MUST remain Ash 3.x only.
- Do not use V42.* module prefixes.
- Do not implement product resources or product migrations.
- Do not implement DMSC-1 fully.
- Do not approve waivers silently.

Before editing:
1. Confirm FP-TB-000 exists and identify AirlockTrace migration if present.
2. Inspect priv/repo/migrations or equivalent.
3. Inspect existing CI/lint/test structure.
4. Search for migration audit tooling already present.
5. Decide whether to implement as Mix task or standalone script based on repo conventions.

Implement:
1. Migration audit tool or Mix task.
2. Deterministic scan of migration files.
3. Detection of destructive operations.
4. Detection of unsafe RLS/constraint disabling patterns.
5. Detection of tenant-owned table without org_id in fixture tests.
6. Check for AirlockTrace org_id migration/table evidence if present.
7. Stable human-readable and machine-readable report.
8. Tests/fixtures proving safe and unsafe cases.
9. CI or documented local gate command.

Acceptance:
- mix compile passes if Mix task is used.
- migration audit tests pass.
- unsafe fixtures fail deterministically.
- report includes pass/fail/pending status.
- no product migration is created.

Stop and report a blocker if:
- migration layout is unknown;
- existing migration framework is not Ecto/AshPostgres-compatible;
- unsafe patterns cannot be detected without broad parser work;
- enforcing pack metadata would fail existing framework migrations without a clear waiver convention.

Final response required:
- Pack implemented
- Changed files
- Tests added
- Tests run
- Gates/checks run
- Evidence report path
- Blockers
- Non-goals intentionally not touched
- Next recommended pack: FP-TB-001-tenant-context-rls-denial
```
