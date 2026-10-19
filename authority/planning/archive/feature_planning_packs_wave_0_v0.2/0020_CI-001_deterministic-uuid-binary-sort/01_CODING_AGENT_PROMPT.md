# Coding Agent Prompt: FP-CI-001 — Deterministic UUID Binary Sort Gate

Use this prompt together with `FP-CI-001-deterministic-uuid-binary-sort.md`.

```text
You are implementing Feature Planning Pack FP-CI-001-deterministic-uuid-binary-sort.

You MUST implement only deterministic UUID binary sort helper and gate/test scope.

Project rules:
- Root module namespace MUST be Ticketing.
- OTP app atom MUST be :ticketing.
- Ash posture MUST remain Ash 3.x only.
- Do not use V42.* module prefixes.
- Do not implement pricing, apportionment, signatures, orders, payments, seats, tickets, ledger, refunds, payouts, or scanning.

Before editing:
1. Confirm FP-TB-000 has passed or report that it has not.
2. Inspect existing foundation/governance utility modules.
3. Search for existing UUID helper logic.
4. Search for unsafe UUID string sorting patterns.
5. Choose the smallest module location consistent with existing repo layout.

Implement:
1. A helper module, preferably Ticketing.Foundation.UUIDs.
2. normalize_uuid16!/1.
3. sort_uuid_bytes_asc!/1.
4. canonical_uuid_list_bytes!/1.
5. Tests with a fixture where string sort and raw byte sort differ.
6. Property tests where practical.
7. Governance documentation/gate placeholder if full lint integration is not ready.

Required behaviour:
- All UUIDs used for crypto/signature/apportionment/tie-break list inputs must normalize to raw 16-byte binaries.
- Sorting must compare binaries directly by unsigned lexicographic byte order ascending.
- Invalid UUIDs must fail deterministically.
- The helper must not return silently reordered strings as canonical truth.

Acceptance:
- mix compile passes.
- mix test passes for UUID helper tests.
- A counterexample test proves UUID string sorting is banned.
- No product code is introduced.

Stop and report a blocker if:
- UUIDv7 library support is missing and cannot be safely isolated;
- existing repo already has conflicting UUID helper semantics;
- implementing lint would require broad unrelated repo changes.

Final response required:
- Pack implemented
- Changed files
- Tests added
- Tests run
- Gates/checks run
- Evidence produced
- Blockers
- Non-goals intentionally not touched
- Next recommended pack: FP-CI-002-migration-safety-baseline
```
