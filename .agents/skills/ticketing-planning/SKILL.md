---
name: ticketing-planning
description: Use when planning a Ticketing increment, drafting or amending a JIP, deriving a planning spec, or decomposing approved planning work into Plane items.
---

# Ticketing planning workflow

This skill guides the planning agent as author and planner. Root `AGENTS.md` defines repository authority, and `planning/WORKFLOW.md` defines the control-tower roles and gates. Follow both; this skill does not grant approval or implementation authority.

## Verify freshness and select work

1. Read root `AGENTS.md`, the effective scoped `AGENTS.md`, and `planning/WORKFLOW.md`. Verify the current GitHub `main` SHA before planning.
2. Check the installed canonical authority, `ROADMAP.md`, active tracer, applicable JIP/spec, implementation and technical baselines, Plane item, dependencies, and blockers. Stop if relevant authority or planning state is stale or unclear.
3. Select one coherent increment from the active tracer. Do not expand scope to absorb unrelated work.

## Grill and classify

4. Run `grill-with-docs` for the increment. Record the decisions, evidence, scope, non-goals, and unresolved questions in the planning artifacts.
5. Evaluate current official technology capabilities and relevant accepted reference repositories. Record applicable capability and reference decisions as required by `AGENTS.md` and the JIP requirements. Do not add or upgrade dependencies through planning output alone.
6. Classify each material decision as `CONTRACT_LOCKED`, `IMPLEMENTATION_LOCKED`, `IMPLEMENTATION_FREE`, or `AUTHORITY_GAP`. Canonical authority controls contract-locked behavior. Do not use a planning preference to settle an authority gap.
7. For an `AUTHORITY_GAP`, stop the affected planning. Capture or link the gap in Plane and return it to the authority workflow. Do not invent a bridge, alias, state, guard, lifecycle rule, or other missing meaning in a JIP or spec. A control-tower `PASS` cannot waive a known authority gap. Resume only after authority is repaired and the increment is re-Grilled as required.

## Draft, review, and approve

8. Author a narrow, self-contained JIP for the selected increment. Include the applicable authority snapshot, decisions, scope, non-goals, dependencies, acceptance evidence, and other required JIP fields from root `AGENTS.md`. Set its state to `DRAFT`.
9. Hand the draft to ChatGPT acting as the independent control tower. Wait for its review. A planning agent cannot approve its own JIP, treat its Grill as approval, or change `DRAFT` to `APPROVED`.
10. After a control-tower `PASS`, present the JIP to the user for explicit approval. Only the user's explicit acceptance makes it `APPROVED`. A review `PASS` is not user approval or merge authorization.
11. If a derivative spec materially helps, create it only from the approved JIP. Keep it subordinate to authority and the JIP, and submit it for independent review and explicit user acceptance. Never self-approve a spec. If it would change a locked JIP decision, stop and return to JIP review and approval.

## Create tickets and reconcile Plane

12. Run `to-tickets` only against the approved JIP and, when used, the accepted spec. Create a small dependency-ordered work graph. Include exact authority, scope, non-goals, dependencies, tests, Definition of Done, documentation impact, and the smallest useful `Context Docs` set.
13. Reconcile Plane with the approved planning artifacts. Plane records execution and dependencies; it does not create semantics. Keep implementation children non-Ready. The planning agent cannot mark a child Ready, remove a blocker to force readiness, or begin product implementation, including a supposedly safe or unrelated portion, regardless of who asks or whether planning artifacts are complete.

## Open the planning PR and stop

14. Open a planning-only PR for the approved planning artifacts. Verify its base and head, exact diff, changed-file scope, applicable planning and authority checks, and fresh exact-head CI. Do not include product implementation.
15. Reconcile Plane with the PR and its exact head, then hand the open PR to the independent control tower for review. Stop. A control-tower `PASS` does not authorize a merge; the user retains merge authorization. Do not merge, advance implementation readiness, or begin product implementation while planning review or approval is pending.

## Stop conditions

Stop affected work and report or capture it in Plane when authority is missing, a JIP/spec/ticket is stale, a dependency or blocker remains, the approved scope must change, a required technical decision is unapproved, or a control-tower review requests changes. Do not use schedule pressure, partial ticket completion, or a review `PASS` to bypass these gates.
