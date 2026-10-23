# Ticketing Control-Tower Workflow

## Status and purpose

This document defines the repository-native operating protocol for collaboration between the user, planning/architecture agents, implementation agents, ChatGPT acting as the independent control tower, Plane, and GitHub.

It is **process governance**, not canonical product authority. It does not create or override Ticketing product/domain semantics.

Product semantics continue to follow the repository authority order:

```text
authority/contracts/CANON-1 + installed canonical contracts
→ authority/planning/ROADMAP.md
→ current active tracer
→ user-approved JIT Implementation Packet (JIP)
→ Plane execution work
→ ticketing/ implementation
```

Higher authority wins.

This workflow exists so a new ChatGPT conversation, a fresh coding-agent session, or a different planning agent can reconstruct the expected operating model directly from the repository without relying on chat history.

## Roles and authority

### User

The user is the final human authority for:

- explicit semantic approval of a JIP and any material amendment to it;
- accepting a derived spec when one is used;
- authorizing merges after independent review;
- authorizing destructive, exceptional, or otherwise explicitly user-gated operations.

A user-approved JIP is the implementation-planning authority for its increment, subordinate to canonical contracts, ROADMAP, and the active tracer.

### Planning / architecture agent

The planning agent is the **author and planner**, not the approver.

It owns, as applicable:

- freshness verification;
- selection of the next coherent tracer increment;
- `grill-with-docs`;
- technology and reference evaluation;
- decision classification;
- drafting or amending the JIP;
- `to-spec` when a durable derivative spec materially helps;
- `to-tickets`;
- Plane reconciliation;
- planning-only PRs.

The planning agent MUST NOT:

- self-approve a JIP or spec;
- treat its own Grill conclusions as authority;
- mark implementation work `READY` merely because it authored the packet;
- silently resolve an `AUTHORITY_GAP` inside a JIP/spec;
- reinterpret stale authority, tracer, scope, or locked decisions;
- begin product implementation while the planning packet is still awaiting independent review.

### ChatGPT control tower

ChatGPT acts as the **independent challenger, reviewer, readiness gate, and PR gate**.

The control tower owns:

- independent freshness verification;
- independent review of Grill conclusions and decision classifications;
- fidelity review of JIP/spec against canonical authority and the active tracer;
- review of `to-tickets` decomposition, dependencies, scope, non-goals, tests, and documentation impact;
- readiness review before the first implementation child becomes `READY`;
- independent exact-head PR review;
- verification of fresh CI and exact merged `main` state;
- final closeout review where required by the JIP/Plane graph.

The control tower returns explicit outcomes such as:

- `PASS`;
- `CHANGES REQUIRED`;
- `BLOCKED` / `AUTHORITY GAP` where applicable;
- `READY FOR MERGE AUTHORIZATION` after exact-head review passes.

The control tower MUST NOT silently replace user semantic approval. A material JIP change still requires explicit user approval.

### Implementation agent

The implementation agent is an **executor of one approved READY work item at a time**.

It owns:

- freshness validation for its assigned item;
- loading the item’s exact Context Docs;
- TDD for material behavior;
- the smallest coherent implementation that satisfies the approved item;
- applicable migrations/generated-code inspection;
- required verification;
- opening the implementation PR and handing back exact evidence.

The implementation agent MUST NOT:

- invent product semantics;
- self-approve planning;
- implement a Planning, Blocked, stale, or dependency-blocked item;
- widen scope beyond its READY item;
- silently add or upgrade dependencies;
- bypass locked Ash/tenancy/RLS/transaction rules;
- merge its own PR without the independent review and user merge gate.

### Plane

Plane is the execution ledger for:

- JIP parents;
- implementation children;
- dependencies;
- blockers;
- discoveries;
- bugs;
- authority gaps;
- review items;
- evidence and completion records.

Plane is never semantic authority.

### GitHub `main`

Verified GitHub `main` is the durable repository state used for freshness checks and post-merge verification.

A branch, PR head, local worktree, chat transcript, generated plan, or unmerged candidate does not replace `main` as the accepted repository baseline.

## Mandatory end-to-end flow

For material product/domain work, use this sequence unless a higher-authority rule explicitly requires otherwise:

```text
1.  Freshness verification
2.  Select next coherent tracer increment
3.  grill-with-docs
4.  Technology/reference evaluation
5.  Decision classification
6.  Resolve blocking authority gaps, if any
7.  Draft JIP
8.  Independent control-tower review
9.  Explicit user JIP approval
10. Optional to-spec
11. to-tickets
12. Plane reconciliation
13. Planning PR
14. Independent control-tower planning review
15. User merge authorization
16. Post-merge main verification
17. First dependency-clear child may become READY
18. Implement exactly one READY item with TDD
19. Implementation PR
20. Independent exact-head control-tower review
21. User merge authorization
22. Post-merge main verification
23. Advance the next dependency-clear item
24. Final docs/handoff/closeout review
```

Do not collapse planning authorship, semantic approval, implementation, and independent review into one self-approving agent role.

## Stage 1 — Freshness verification

Before material planning, verify the current applicable:

- GitHub `main` SHA and tree;
- root and scoped `AGENTS.md` files;
- installed CANON version;
- installed contract manifest and selected contract versions;
- ROADMAP;
- active tracer;
- current JIP/spec history;
- relevant Plane state and dependencies;
- current implementation baseline;
- relevant dependency/toolchain baseline;
- required reference-repository commits.

Without verified freshness, only DRAFT analysis may continue.

If a relevant material change makes an existing JIP/spec/ticket stale, mark or treat it as `STALE` and stop affected implementation until the packet is reconciled and reapproved where required.

## Stage 2 — Grill and decision classification

The planning agent runs `grill-with-docs` for material work and pressure-tests, as applicable:

- ownership and domain boundaries;
- resources, actions, inputs, outputs, and interfaces;
- lifecycle states and transitions;
- persistence constraints, indexes, foreign keys, immutability, and DB-owned time;
- tenancy, actor, authorization, capabilities, and RLS;
- transaction ownership;
- concurrency, locks, CAS/version fences, and races;
- idempotency and replay;
- canonical errors and hiding behavior;
- events, outbox, jobs, audit, and observability;
- migration, rollout, and rollback;
- positive, negative, cross-tenant, replay, race, and rollback tests;
- scope and explicit non-goals.

Material decisions are classified as:

- `CONTRACT_LOCKED`;
- `IMPLEMENTATION_LOCKED`;
- `IMPLEMENTATION_FREE`;
- `AUTHORITY_GAP`.

An `AUTHORITY_GAP` stops affected downstream planning/implementation until authority is repaired through the governed authority workflow.

## Stage 3 — JIP authoring and approval

The planning agent produces one narrow JIP for the selected tracer increment.

JIP states are:

- `DRAFT` — authored but not yet user-approved;
- `APPROVED` — explicitly approved by the user;
- `STALE` — a material authority/tracer/baseline/prerequisite/scope/locked-decision change invalidated the approval basis.

The planning agent MUST NOT convert `DRAFT` to `APPROVED` on its own.

The control tower independently reviews the draft packet before recommending approval.

Only explicit user acceptance makes a JIP `APPROVED`.

A material semantic change to an approved JIP requires targeted re-Grill as appropriate and explicit user reapproval.

## Stage 4 — Derived spec

Use `to-spec` only when a durable derivative spec materially helps architectural, cross-resource, transaction, lifecycle, or interface clarity.

A spec:

- is subordinate to the approved JIP and canonical authority;
- cannot create product semantics;
- cannot reopen a locked JIP decision without making the JIP stale;
- must preserve append-only/supersession history where versioned planning artifacts are used.

If a spec materially changes the approved JIP rather than merely deriving from it, stop and return to JIP review/approval.

## Stage 5 — to-tickets and Plane reconciliation

Run `to-tickets` against the approved JIP and accepted derivative spec, when present.

Use one `[JIP]` parent plus small dependency-ordered children.

Children should include, as applicable:

- exact JIP/spec and authority references;
- scope and explicit non-goals;
- locked requirements;
- dependencies and blockers;
- TDD/test expectations;
- DoD;
- exact Context Docs;
- documentation impact.

Plane tickets MUST NOT invent or override semantics.

After `to-tickets`, all implementation children remain non-READY until independent control-tower review of the packet and dependency graph passes.

## Stage 6 — Planning PR

Persist approved planning artifacts in the repository when durable files are required.

A planning PR should contain planning/governance changes only unless its approved purpose explicitly includes something else.

Before handoff:

- verify the exact base and head SHA;
- review the exact final diff;
- run applicable planning/authority checks;
- run `git diff --check`;
- obtain fresh exact-head CI where the repository supports it;
- keep product implementation out of the planning PR.

The planning agent stops after opening the PR and reconciling Plane.

The control tower independently reviews the exact PR head and returns `PASS` or `CHANGES REQUIRED`.

The user authorizes the merge after a control-tower PASS.

## Stage 7 — Post-merge readiness gate

After a planning PR merges, do not immediately dispatch implementation from memory or from the old PR head.

The control tower re-verifies:

- actual merged `main` SHA/tree;
- that the expected planning artifacts are present on `main`;
- relevant authority/tracer freshness;
- post-merge CI/check state where applicable;
- Plane dependency state;
- absence of a new blocker or authority gap.

Only then may the first genuinely dependency-clear implementation child move to `READY`.

The `[JIP]` parent should reflect the current execution phase according to the project workflow, but parent state never makes blocked children executable.

## Stage 8 — READY implementation

Only a work item that is all of the following may enter implementation:

- belongs to the approved current JIP;
- independently reviewed;
- freshness-checked;
- dependency-clear;
- not stale;
- explicitly in `READY` state.

Implement one READY item at a time.

Material behavior uses TDD:

```text
RED
→ verify expected failure
→ smallest implementation
→ GREEN
→ focused verification
→ broader required checks
```

Any material discovery that changes authority, scope, a locked decision, dependencies, persistence/security behavior, or observable semantics stops affected work and is captured in Plane.

## Stage 9 — Implementation PR and independent review

Before PR handoff, the implementation agent follows the repository implementation/verification skills and reports exact evidence.

The control tower independently reviews:

- current canonical authority;
- approved JIP/spec;
- exact Plane item;
- exact PR base/head;
- exact diff;
- migrations/generated files;
- dependency/lock changes;
- tests and required verification;
- documentation impact;
- fresh exact-head CI;
- unresolved blockers, discoveries, or authority gaps.

A passing implementation review may result in `READY FOR MERGE AUTHORIZATION`.

It does not itself authorize the merge.

The user retains merge authorization.

## Stage 10 — Post-merge verification and progression

After each implementation merge, verify actual `main` before advancing downstream work.

Do not mark a dependent child READY merely because its predecessor PR was merged in the UI.

Verify:

- merged SHA/tree;
- applicable post-merge checks;
- completion evidence/DoD;
- no new stale authority or packet state;
- dependencies now genuinely clear.

Then update Plane and move only the next eligible item to `READY`.

## Discoveries, blockers, bugs, and authority gaps

Capture meaningful findings in Plane rather than leaving them only in chat or PR prose.

Use the project conventions:

- `[DISCOVERY]` for useful findings that do not themselves change authority;
- `[BLOCKER]` where execution cannot continue safely;
- `[BUG]` for defects;
- `[AUTHORITY GAP]` where canonical semantics are missing, contradictory, or insufficient;
- `[REVIEW]` for explicit independent review work where useful.

For an authority gap:

```text
stop affected work
→ capture the gap
→ correct authority in authority/
→ validate and merge authority repair
→ targeted re-Grill
→ refresh JIP/spec/tickets
→ reapprove if material
→ resume only when dependency-clear and fresh
```

Do not hide a prerequisite or authority repair inside feature implementation.

## Staleness rules

A JIP/spec/ticket is stale when a relevant material change occurs in any of:

- CANON or installed canonical contracts;
- ROADMAP or active tracer;
- implementation baseline/prerequisite;
- approved scope or non-goals;
- locked lifecycle, persistence, tenancy, authorization, concurrency, idempotency, money, inventory, or side-effect decisions.

Do not silently reinterpret stale work.

Nonmaterial reference movement does not automatically stale a packet when the reference is demonstrably `NOT_APPLICABLE`; record the refreshed evidence and continue only when the classification still holds.

## Merge authority

No agent should assume that passing tests or receiving a review PASS means it may merge.

The default Ticketing merge gate is:

```text
fresh exact-head evidence
→ independent control-tower PASS
→ explicit user merge authorization
→ merge
→ post-merge main verification
```

If the user delegates a narrower merge authority for a specific task, that delegation must be explicit and must not override higher repository or product authority.

## Completion

A material increment is not complete merely because code merged.

Completion requires, as applicable:

- all in-scope Plane children complete;
- required tests/checks pass;
- no unresolved blocker or authority gap;
- exact-diff and independent review evidence;
- required implementation documentation updated;
- handoff/closeout evidence tied to merged SHAs;
- final JIP closeout/review complete.

## Fresh-session bootstrap

A fresh planning or implementation agent should reconstruct context in this order:

1. read root `AGENTS.md`;
2. read the effective scoped `AGENTS.md` for the files it will touch;
3. read this `planning/WORKFLOW.md` when the task involves planning, readiness, implementation handoff, review, or merge progression;
4. inspect current GitHub `main`;
5. verify current canonical authority, ROADMAP, tracer, JIP/spec, and Plane item as applicable;
6. load the relevant repository skills;
7. act only within the role and gate defined by the current workflow stage.

Chat history can provide context, but it is never required to reconstruct the repository workflow and never outranks repository or canonical authority.
