# Coding Agent Prompt: FP-MVP0-000 — Repo and Airlock Scaffolding

Use this prompt together with `FP-MVP0-000-repo-airlock-scaffold.md`.

```text
You are implementing Feature Planning Pack FP-MVP0-000-repo-airlock-scaffold for the Ticketing project.

You MUST implement only the scaffolding scope in the pack.

Project rules:
- Root module namespace MUST be Ticketing.
- OTP app atom MUST be :ticketing.
- Ash posture MUST be Ash 3.x only.
- Do not use V42.* or contract-ID-prefixed module namespaces.
- Do not implement product features.
- Do not create orders, payments, seats, tickets, refunds, payouts, scanner admission, ledger posting, tenant switching, or dynamic pricing.
- Do not create product migrations.

Before editing:
1. Inspect the repo layout.
2. Report whether this is an empty repo or existing repo.
3. Confirm current git branch and dirty files.
4. Locate existing contracts, tools, docs, and CI files.
5. If the repo already has equivalent scaffolding, patch minimally instead of recreating.

Implement:
1. Minimum repo/governance directory scaffold.
2. Minimal docs/domain_map/00_DOMAIN_MAP.md skeleton with required matrix headings.
3. Minimal source_manifest and contract_register placeholders.
4. tools/airlock and tools/trace placeholders or installed provided scripts if available.
5. Basic compile/test/CI placeholders needed for TB-000.
6. A README explaining that product implementation remains blocked.

Acceptance:
- Repo compiles if a Mix project exists.
- Test command runs or fails honestly due to missing project initialization.
- No product modules exist.
- No product migrations exist.
- Trace validator placeholder does not fake success.

Stop and report a blocker if:
- repo layout differs materially from the pack assumptions;
- implementing would require product code;
- Ash 3.x cannot be preserved;
- the project is not safely identifiable as Ticketing / :ticketing.

Final response required:
- Pack implemented
- Changed files
- Tests run
- Gates/checks run
- Evidence produced
- Blockers
- Non-goals intentionally not touched
- Next recommended pack
```
