---
name: ticketing-implementation
description: Use when implementing an approved READY Ticketing application work item. Follow the current Plane and JIP workflow before changes, and stop when authority, readiness, scope, or prerequisites are unclear.
---

# Ticketing implementation workflow

This skill is an operational checklist. The repository root `AGENTS.md` defines authority, JIP, Plane, blocker, and completion rules. `ticketing/AGENTS.md` defines application implementation rules. Follow those documents and the current approved JIP when they apply. This skill does not add or change product semantics.

1. Confirm the assigned Plane item has the `READY` label, has no unresolved `blocked_by` dependency, and belongs to a current approved JIP.
2. Verify the current canonical authority pin, active tracer, technical baseline, and accepted implementation baseline against the JIP and Plane item. Stop if a relevant change makes either stale.
3. Read the ticket's exact `Context Docs`, its JIP, and only the authority, code, and tests needed for the assigned scope.
4. Load the relevant specialist skills: `ash-framework` for Ash work, `phoenix-framework` for Phoenix or LiveView work, and `elixir-otp` for material process, supervision, or concurrency work. Do not load the OTP skill for routine resource CRUD.
5. Inspect the existing implementation and tests before editing. Keep changes within the READY work item's approved scope.
6. Verify unfamiliar or material API behavior in current authoritative docs for the installed version. Prefer Tidewave `get_docs` when the DEV app is running, then `mix usage_rules.docs`, `mix usage_rules.search_docs`, and official version-matched package docs. Use model memory only when those sources do not answer the question.
7. Use official generators or Igniter first for supported structural changes, then inspect every generated file and migration.
8. Use TDD for material behavior: write a behavior test, confirm it fails for the expected reason, implement the smallest change, and run the focused test before broader checks.
9. Implement the smallest coherent change that satisfies the approved work item. Do not add an unapproved dependency, capability, persistence path, or product behavior.
10. Stop affected work and record the blocker or discovery in Plane if authority is missing, the JIP or ticket is stale, scope must expand, a dependency or capability is unapproved, or a locked invariant cannot be met.
11. Use Tidewave runtime tools for useful evidence when the DEV application is running. Otherwise prefer a reproducible `mix run -e`; use IEx for genuinely interactive investigation and `dbg` or `pry` for difficult runtime problems. Runtime exploration does not replace automated tests.
12. Ticketing DEV uses `TICKETING_DEV_HTTP_PORT`, default `4200`, on `127.0.0.1`. Reserve `4200` for the primary checkout and use an available worktree slot from `4201–4219`; Phoenix and Tidewave share the port. Use `mix tidewave.proxy` for worktree-aware MCP access where appropriate.
13. Before PR handoff, load `ticketing-verification` and complete its checklist.
