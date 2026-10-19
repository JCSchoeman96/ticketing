# Ticketing repository governance

This repository is contract-first and uses mandatory Just-In-Time planning, capture, ticketing, implementation, and independent review.

The coding agent is an implementation executor. It does not invent or approve product/domain semantics, silently resolve authority gaps, or treat implementation preferences as authority.

## Authority order

For material product/domain work:

```text
authority/contracts/CANON-1 + installed canonical contracts under authority/contracts/
→ authority/planning/ROADMAP.md
→ current active tracer under authority/planning/tracers/
→ user-approved JIT Implementation Packet (JIP)
→ Plane execution work item
→ ticketing/ implementation
```

Higher authority wins.

A Plane work item, JIP, reference repository, roadmap item, historical plan, PR comment, code comment, existing implementation, framework convention, or agent assumption MUST NOT override canonical contracts.

`FPP` / `Feature Planning Pack` is historical terminology. Existing FPP IDs may be treated as aliases during migration; new implementation increments use **JIP — JIT Implementation Packet**.

## Mandatory planning and execution gate

Do not begin material product/domain implementation unless:

1. current canonical authority is verified;
2. a current user-approved JIP exists;
3. the JIP has been decomposed into Plane execution work;
4. the current work item belongs to that JIP;
5. required dependencies/blockers are resolved;
6. the JIP/work item is not stale.

A coding request, contract reference, roadmap entry, tracer, chat conversation, reference implementation, historical plan, or Plane work item alone is not sufficient authorization.

This gate applies before changes affecting:

- Ash resources, actions, policies, ownership or domain boundaries;
- persistence, migrations, constraints, indexes or immutability;
- lifecycle/state-machine behavior;
- tenancy, actors, authorization, capabilities or RLS;
- idempotency, locks, CAS/version fences or concurrency;
- inventory, pricing, money, tax, ledger, payments, orders, ticketing or admission;
- canonical errors or fail-closed behavior;
- events, signals, outbox behavior, jobs, audit or observability;
- public API/domain boundaries;
- material framework, database or architectural capability choices;
- a tracer, vertical slice or material product capability.

## Required upstream workflow

Material implementation flows through:

```text
current authority
→ active roadmap/tracer increment
→ JIT grill-with-docs
→ technology/reference evaluation
→ decision classification
→ approved JIP
→ optional to-spec where materially useful
→ to-tickets
→ reviewed Plane dependency graph
→ READY implementation work item
→ TDD implementation
→ PR
→ independent review
```

The coding agent MUST NOT recreate the planning process to grant itself implementation authority.

It may inspect authority and references to validate the supplied JIP/work item, but may not self-approve missing or contradictory semantics.

## Technology freshness policy

Ticketing is greenfield development and SHOULD begin new work on the newest practical stable stack.

Do not hard-code moving framework or package version numbers in this file.

At fresh-session bootstrap and every material JIT, evaluate the current:

- Elixir and Erlang/OTP releases;
- Phoenix and Phoenix LiveView;
- Ash core and applicable Ash extensions;
- AshPostgres and persistence dependencies;
- PostgreSQL;
- Tailwind and frontend build tooling;
- other material runtime/development dependencies.

Prefer the newest release that is all of:

- stable;
- supported upstream;
- not retired;
- free of known applicable security advisories;
- mutually compatible with the selected stack;
- compatible with canonical Ticketing requirements;
- reasonable for production use.

Experimental capabilities may be evaluated and intentionally adopted only through an explicit JIP decision with maturity/risk recorded.

Do not retain an older version merely because the repository currently uses it when we are still early enough to upgrade safely.

### Version semantics

`AGENTS.md` defines policy, not current numbers.

Use project manifests to define an intentional supported range:

- set a tested minimum version;
- constrain the next incompatible major where appropriate;
- avoid meaningless requirements such as `>= 0.0.0` when a meaningful compatibility floor is known;
- allow compatible newer releases unless there is a documented reason not to.

`mix.lock` remains the exact reproducible dependency resolution.

Runtime toolchain files such as `.tool-versions` or `mise.toml` MAY pin exact Elixir/OTP versions for reproducibility. Those pins are operational baselines, not permanent architecture decisions, and should be refreshed deliberately when newer compatible stable releases are accepted.

Dependency or runtime upgrades that can affect implementation semantics, generated code, database behavior or architecture must be explicit JIP/Plane work and verified before dependent domain work proceeds.

## Mandatory Ash/Phoenix/Elixir capability evaluation

Every material JIT must determine whether current Ash/Phoenix/Elixir capabilities provide an appropriate implementation mechanism.

Consult current official documentation/releases, not remembered or historical APIs.

Evaluate materially relevant capabilities including, but not limited to:

- Ash core;
- AshPhoenix;
- AshPostgres;
- Ash Signals;
- Temporal Resources;
- Ash Storage;
- AshStateMachine;
- AshOban;
- AshPaperTrail / AshArchival;
- Reactor;
- AshAuthentication;
- other applicable official or accepted extensions.

This is an evaluation gate, not an adoption mandate.

For each materially relevant capability record:

- current installed baseline;
- newest stable compatible release;
- maturity/stability status;
- relevance to the increment;
- compatibility with canonical semantics;
- tenancy, authorization, policy and RLS implications;
- transaction/concurrency/idempotency/rollback implications;
- DB/runtime/dependency prerequisites;
- migration and rollback cost;
- established alternatives;
- decision: `ADOPT`, `DEFER`, `REJECT`, or `PREREQUISITE`.

Canonical contracts remain authoritative. A newer Ash feature MUST NOT replace contract-required behavior merely because it is newer or more idiomatic.

Coding agents MUST NOT silently add or upgrade architectural dependencies.

## Required implementation references

Reference repositories are implementation evidence, not canonical Ticketing product authority.

### Store Blueprint Hardening

Repository:

`JCSchoeman96/Store_Blueprint_Hardening`

For JITs involving commerce capabilities — including catalog/product structure, carts, pricing, checkout, orders, payments, provider boundaries, webhooks, money, fulfillment, subscriptions, digital delivery, notifications, idempotency, outbox/jobs or related performance/concurrency behavior — current accepted `main` MUST be inspected.

Prefer reuse/adaptation of proven compatible code, tests, boundaries and invariants instead of independently rebuilding equivalent mechanisms.

For each relevant JIP classify Store Blueprint material as:

- `REUSE_AS_IS`;
- `ADAPT`;
- `REFERENCE_ONLY`;
- `NOT_APPLICABLE`.

Document why.

Do not copy semantics that conflict with Ticketing authority. In particular, differences in tenancy, identities, lifecycle, money, event ownership or public API semantics must follow Ticketing contracts.

Preserve licensing/provenance when code is reused.

### LiveFrames

Repository:

`JCSchoeman96/LiveFrames`

For material frontend/UI work, current accepted LiveFrames capabilities MUST be inspected before creating an equivalent component, token, layout or design-conversion mechanism.

Prefer supported native LiveFrames components/generation/integration when compatible with the approved Ticketing design and runtime.

LiveFrames is a frontend/design implementation reference, not Ticketing product authority.

Respect its provenance, redistribution and package-boundary rules. Do not import private/vendor source material as a Ticketing runtime dependency.

## Decision classes

### `CONTRACT_LOCKED`

Canonical authority defines the behavior.

Implement exactly as required.

### `IMPLEMENTATION_LOCKED`

Canonical authority permits alternatives and the approved JIP selects the project-level choice.

Follow that decision.

### `IMPLEMENTATION_FREE`

The choice cannot alter contract semantics, externally observable behavior, lifecycle, persistence invariants, tenancy/auth, idempotency/concurrency, inventory, money, ownership, errors or side effects.

Choose the simplest idiomatic current implementation consistent with the repository.

### `AUTHORITY_GAP`

Canonical authority does not safely determine required behavior.

Stop affected implementation.

Do not invent resources, identifiers, aliases, states, transitions, lifecycle guards, error semantics, events/signals, ownership, hidden persistence, semantic bridges or authorization behavior.

Capture the gap and resolve it through the authority workflow before affected product implementation resumes.

Authority work required specifically to resolve an `AUTHORITY_GAP` is exempt from the product implementation JIP gate.

## JIP requirements

A valid JIP identifies, where applicable:

- JIP ID and approval state;
- exact contracts commit;
- CANON version;
- implementation baseline;
- active tracer;
- governing contract IDs/versions;
- current technical baseline and accepted prerequisites/upgrades;
- Ash capability evaluation;
- Store Blueprint / LiveFrames reference evaluation where relevant;
- scope and explicit non-goals;
- decision classifications;
- resources/actions/ownership;
- lifecycle initial states, transitions, guards, invalid transitions, side effects and terminal states;
- tenancy/auth/RLS;
- persistence invariants;
- transaction boundaries;
- concurrency/locking/CAS/version fences;
- idempotency/replay;
- canonical errors/information hiding;
- events/signals/outbox/jobs/audit/observability;
- migrations/rollout;
- required tests/evidence;
- known gaps;
- Definition of Done.

The JIP must be self-contained enough that implementation does not depend on hidden chat history.

## Plane execution ledger

Plane project `Ticketing Platform` (`TICK`) is the persistent execution ledger.

Plane is NOT canonical semantic authority.

Each material JIP has a parent work item and small executable child work items.

Each execution work item should contain or link:

- parent JIP;
- exact authority snapshot;
- relevant contracts;
- purpose;
- scope/non-goals;
- locked decisions;
- dependencies/blockers;
- required tests;
- Definition of Done.

Use native `blocking` / `blocked_by` relations where available.

Do not rely only on numbering or prose for dependency order.

### Plane feature portability

The development workflow MUST NOT depend on a paid/optional Plane feature.

If work-item types or custom properties are unavailable, represent classification using ordinary work items plus:

- consistent title prefixes;
- labels;
- parent/child relationships;
- native dependency relations;
- comments/descriptions.

If richer Plane features later become available, they may improve presentation but MUST NOT change execution semantics or canonical authority.

## Ready-to-implement rule

A material work item is READY only when:

- parent JIP is approved/current;
- work is inside JIP scope;
- required authority is known;
- required technical/reference prerequisites are complete;
- dependencies are complete;
- no unresolved blocker/authority gap applies;
- acceptance/verification requirements are clear.

Do not start blocked work merely because partial coding is possible.

## Discovery and blocker capture

Material discoveries belong in Plane, not only chat, PR comments, local TODOs, code comments or agent memory.

### `IMPLEMENTATION_FREE`

Record on the current work item when useful and continue.

### New `IMPLEMENTATION_LOCKED`

Record the decision and rationale before relying on it.

If material to the approved JIP, stop and re-Grill.

### `BLOCKER`

Create/link the blocker and stop affected work.

### `AUTHORITY_GAP`

Create/link an authority-gap blocker and stop affected product implementation.

Recovery:

```text
capture gap
→ identify affected work
→ correct canonical authority/tracer
→ merge authority
→ update implementation authority pin if required
→ targeted JIT re-Grill
→ revise/approve JIP if required
→ update Plane dependencies
→ resume
```

### Technical prerequisite

Create/link prerequisite work for framework, database, dependency or infrastructure changes rather than hiding them inside unrelated feature work.

## Coding-agent behavior

For an approved READY work item:

- implement only its JIP scope;
- obey `CONTRACT_LOCKED` and `IMPLEMENTATION_LOCKED`;
- use discretion only for true `IMPLEMENTATION_FREE` choices;
- use TDD for material behavior;
- preserve contract ownership boundaries;
- prefer governed Ash actions over direct Repo bypasses;
- use Repo/DDL/test-fixture mechanisms only for justified infrastructure or explicit JIP needs;
- use current official APIs and idioms;
- avoid unrelated refactors;
- surface contradictions immediately;
- capture/report discoveries and blockers;
- provide current verification evidence.

Work on one coherent ready item at a time unless the approved execution graph explicitly allows safe parallel work.

## Lifecycle implementation discipline

Meaningful lifecycle work explicitly accounts for:

- initial state;
- permitted transitions;
- actor/capability guards;
- data preconditions;
- transaction boundary;
- concurrency/version fencing;
- transition side effects;
- rejected transitions;
- terminal states;
- required transition tests.

Do not implement governed lifecycle behavior as ad-hoc field updates.

## TDD

For material behavior:

1. write or identify a failing behavior test;
2. confirm failure for the expected reason;
3. implement the minimum correct behavior;
4. run focused tests;
5. refactor without changing semantics;
6. run broader regression/contract tests;
7. run repository verification.

Tests must prove governed behavior, not merely execute code.

## Staleness

A JIP/Plane work item is stale when relevant changes occur to:

- contracts authority;
- CANON/governing contracts;
- active tracer;
- implementation baseline;
- accepted technical prerequisites;
- approved scope;
- lifecycle/persistence/tenancy/auth/concurrency/idempotency/inventory/money/side-effect decisions.

Do not silently reinterpret stale planning.

Return to the orchestration layer for targeted re-Grill.

## Completion gate

Before claiming a material work item complete:

- focused tests pass;
- required negative tests pass;
- cross-tenant tests pass where applicable;
- replay/idempotency tests pass where applicable;
- race/concurrency tests pass where applicable;
- rollback/atomicity tests pass where applicable;
- migrations are reviewed where applicable;
- contract regression tests pass;
- `mix precommit` passes;
- applicable security/dependency checks pass;
- current verification evidence is supplied;
- no unresolved blocker or authority gap remains.

Independent review must evaluate:

```text
canonical authority
+ approved JIP
+ Plane work item
+ accepted reference/prerequisite decisions
+ exact diff
+ test/CI evidence
```

A JIP parent is complete only after required child work and whole-increment integration/review are complete.

## Mechanical exceptions

A new JIP cycle is normally unnecessary for changes that cannot alter product/domain semantics, such as typo-only docs, formatting/comments, mechanical test/CI maintenance or explicitly covered mechanical follow-up work.

If semantics, architecture, runtime/database requirements, or material dependency capability may change, use the JIT flow.

## Nested `AGENTS.md`

This root file owns repository-wide planning/execution governance.

`authority/AGENTS.md` adds authority-specific release, provenance, integrity, and validation rules.

`ticketing/AGENTS.md` adds Phoenix, Ash, Elixir, LiveView, testing, frontend, and application-specific technical rules.

Nested files MUST NOT redefine authority hierarchy, JIP approval, Plane execution semantics, decision classes or completion gates.

If a nested rule conflicts with this file, root governance controls.
