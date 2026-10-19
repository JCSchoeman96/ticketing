# Coding Agent Prompt: FP-VS-001 — App Baseline and CI Governance

Use this prompt together with `00_FEATURE_PLAN.md`.

```text
You are implementing Feature Planning Pack FP-VS-001-app-baseline-and-ci-governance.

You MUST implement only the VS-001 app baseline and CI governance scope.

Project rules:
- Root module namespace MUST be Ticketing.
- OTP app atom MUST be :ticketing.
- Ash posture MUST be Ash 3.x only.
- Do not use V42.* module prefixes.
- Do not implement product resources or product workflows.
- Do not implement User, Organization, OrgMembership, Session, AuditEvent, orders, payments, seats, tickets, refunds, payouts, or scanning.
- Do not treat the planning catalogue or CAI as contract law; contracts and gates win.

Before editing:
1. Inspect the existing repository structure.
2. Check whether Phoenix/Ash app skeleton already exists.
3. Check whether FP-MVP0-000, FP-TB-000, FP-CI-001, and FP-CI-002 artifacts or evidence exist.
4. Inspect mix.exs, config files, test setup, CI files, justfile/Makefile, AGENTS.md, and README.md.
5. Search for existing commands or wrappers for governance lint, strict contract gates, migration audit, and UUID sort checks.
6. Do not duplicate existing commands. Extend or document them.

Implement or align:
1. Ensure project compiles with Ticketing root namespace and :ticketing OTP app.
2. Ensure Ash 3.x posture is documented and no Ash 2.x/V42.* drift is introduced.
3. Ensure `mix check` or equivalent foundation command exists.
4. Wire or document gate commands for:
   - governance lint
   - strict contract bundle validation
   - migration safety check
   - deterministic UUID binary sort check
5. Add a baseline ExUnit smoke test if missing.
6. Add a scan/test that rejects V42.* module prefixes.
7. Add a scan/test that confirms this pack did not introduce product resources.
8. Create `reports/foundation/vs_001_foundation_report.md` with pass/fail/pending evidence.
9. Update README/AGENTS only where needed to document the foundation gate commands.

Acceptance:
- `mix compile` passes.
- `mix test` passes, or blockers are honestly reported.
- `mix check` or equivalent exists and is documented.
- Foundation evidence report exists.
- No product resource is created.
- Existing Wave 0 pack order is preserved.

Stop and report a blocker if:
- the repository is not yet initialized;
- Phoenix/Ash skeleton is absent and creating it would exceed this pack;
- Ash version is not 3.x or cannot be confirmed;
- CI/gate scripts are missing and cannot be safely wrapped without inventing behavior;
- implementing `mix check` would require product resources;
- existing files conflict with Ticketing/:ticketing naming.

Final response required:
- Pack implemented
- Changed files
- Tests added
- Tests run
- Gates/checks run
- Evidence report path
- Pending gates or blockers
- Non-goals intentionally not touched
- Confirmation that no product resources were introduced
- Next recommended pack: FP-TB-001-tenant-context-rls-denial
```
