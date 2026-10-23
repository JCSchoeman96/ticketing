---
name: ticketing-implementation
description: Use when implementing an approved Ticketing work item in Plane's Ready state. Stop when authority, readiness, scope, or prerequisites are unclear.
---

# Ticketing implementation workflow

This skill is an implementation checklist. Root `AGENTS.md` governs repository authority, JIP approval, Plane readiness, blockers, and completion. `planning/WORKFLOW.md` governs the control-tower process. Follow both, the effective scoped `AGENTS.md`, the current approved JIP/spec, and the assigned Plane item. This skill does not add or change product semantics.

## Confirm dispatch readiness

1. Read root `AGENTS.md`, the effective scoped `AGENTS.md` for the application files in scope, `planning/WORKFLOW.md`, the assigned Plane item, and its current approved JIP and accepted spec when one exists.
2. Verify current GitHub `main`, canonical authority, active tracer, technical and implementation baselines, JIP/spec approval, and ticket freshness. Treat only explicit user acceptance as JIP/spec approval; do not self-approve or infer approval from a review `PASS`.
3. Dispatch only when the assigned Plane item's state is exactly `Ready`, its approved current JIP and scope are verified, and all dependencies and blockers are clear. A `READY` label does not make an item dispatchable. Implement exactly one Ready item at a time.
4. Read the item's exact `Context Docs`. If required Context Docs are missing or unclear, stop and request Plane reconciliation or the missing scoped documents before implementation. Inspect only the authority, code, and tests needed for the assigned scope.

If any gate is unclear or fails, do not start implementation. Stop when authority, JIP/spec, or ticket is stale; a blocker or authority gap exists; a dependency is unresolved or unapproved; or the scope must expand. Capture the blocker or discovery in Plane and return it to the control tower.

## Implement within scope

5. Load applicable specialist skills: `ash-framework` for Ash work, `phoenix-framework` for Phoenix or LiveView work, and `elixir-otp` for material process, supervision, or concurrency work. Do not load the OTP skill for routine resource CRUD.
6. Inspect existing implementation and tests before editing. For material behavior, use TDD: write a behavior test, confirm it fails for the expected reason, implement the smallest correct change, then run the focused test.
7. Verify unfamiliar or material API behavior in current authoritative documentation for the installed version. Prefer Tidewave `get_docs` when the DEV app is running, then `mix usage_rules.docs`, `mix usage_rules.search_docs`, and official version-matched package docs.
8. Use official generators or Igniter first for supported structural changes, then inspect every generated file and migration. Do not add unapproved dependencies, capabilities, persistence paths, or product behavior.
9. Use Tidewave runtime tools for useful evidence when DEV is running. Otherwise prefer a reproducible `mix run -e`; use IEx for interactive investigation and `dbg` or `pry` for difficult runtime problems. Runtime exploration does not replace tests.

## Hand off for review

10. Before PR handoff, load `ticketing-verification` and complete its checklist. Report the exact Plane item, approved JIP/spec, branch, PR, diff, and verification evidence.
11. The implementation agent cannot approve its own JIP/spec, declare its work independently reviewed, or merge. A control-tower `PASS` is not merge authorization. Leave the PR open and wait for explicit user merge authorization after independent review.
