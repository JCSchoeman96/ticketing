# Ticketing repository governance

This repository is contract-first. The coding agent is an implementation executor, not the authority that invents or approves product/domain semantics.

## Authority order

For material product/domain work, follow this precedence:

```text
current canonical CANON + installed canonical contracts
→ current planning/ROADMAP.md
→ current active tracer
→ user-approved Feature Planning Pack (FPP)
→ implementation
```

Higher authority wins. An FPP, issue, roadmap item, historical planning file, or code comment MUST NOT override canonical contracts.

## Absolute implementation gate

Do not begin material product/domain implementation unless the task includes an `APPROVED` Feature Planning Pack produced by the ChatGPT JIT Grill workflow.

This gate applies before work that can change:

- Ash resources/actions or domain ownership;
- persistence, migrations, constraints, indexes, or immutability;
- lifecycle/state-machine behavior;
- tenancy, actor/auth, authorization, capabilities, or RLS;
- idempotency, locks, CAS/version fences, or concurrency behavior;
- inventory, pricing, money, tax, ledger, payment, ticketing, or admission semantics;
- canonical errors or fail-closed behavior;
- events, outbox behavior, jobs, audit, observability, or other side effects;
- public API/domain boundaries;
- a tracer, vertical slice, or material feature capability.

A coding request, contract reference, roadmap item, tracer, historical FPP, or prior chat is not sufficient authorization by itself.

## What counts as a valid FPP

The FPP must identify, as applicable:

- FPP ID and `APPROVED` status;
- exact authority snapshot and implementation baseline;
- governing contract IDs/versions;
- active tracer;
- scope and explicit non-goals;
- material decisions classified as `CONTRACT_LOCKED`, `IMPLEMENTATION_LOCKED`, `IMPLEMENTATION_FREE`, or `AUTHORITY_GAP`;
- resources/actions/ownership;
- lifecycle rules;
- tenancy/auth/RLS rules;
- DB invariants and transaction/concurrency/idempotency rules;
- canonical errors and side effects;
- migration/rollout constraints;
- required verification/tests;
- definition of done.

The FPP must be self-contained enough that implementation does not depend on hidden chat history.

## Decision classes

### `CONTRACT_LOCKED`
Canonical authority defines the behavior. Implement it as written.

### `IMPLEMENTATION_LOCKED`
The contracts permit alternatives and the approved FPP selected one. Follow it.

### `IMPLEMENTATION_FREE`
Choose the simplest idiomatic implementation only where the choice cannot alter contract semantics, externally observable behavior, lifecycle, persistence invariants, tenancy/auth, idempotency/concurrency, inventory, money, ownership, or side effects.

### `AUTHORITY_GAP`
Stop the affected implementation. Do not invent missing states, resources, identifiers, transitions, errors, events, or semantic bridges. Report the gap so authority can be corrected, then resume only after re-Grill/re-approval where required.

Authority work specifically required to resolve an `AUTHORITY_GAP` is exempt from the product implementation FPP gate.

## Staleness

Treat an FPP as stale and stop affected implementation if a material change occurs to canonical authority, CANON, governing contract versions/semantics, active tracer, implementation baseline, scope, or a locked lifecycle/persistence/tenancy/auth/concurrency/idempotency/inventory/money/side-effect decision.

Do not silently reinterpret a stale FPP. Return to ChatGPT for targeted re-Grill.

## Coding-agent behavior

When an approved current FPP is present:

- implement only the approved scope;
- obey `CONTRACT_LOCKED` and `IMPLEMENTATION_LOCKED` decisions;
- use discretion only for `IMPLEMENTATION_FREE` choices;
- use TDD for material behavior;
- preserve contract ownership boundaries;
- prefer Ash actions over direct Repo bypasses for governed domain behavior;
- avoid unrelated refactors;
- surface contradictions immediately;
- provide fresh verification evidence before claiming completion.

The coding agent MUST NOT conduct/recreate the JIT Grill, generate a replacement FPP as authority, self-approve planning decisions, infer missing semantics, or use historical planning as execution authority.

## Mechanical exceptions

A new FPP is normally unnecessary for changes that cannot alter product/domain semantics, such as typo-only documentation edits, formatting/comments, mechanical test renames, mechanical CI maintenance, or a mechanical follow-up already covered by an approved FPP.

If there is reasonable doubt that a change can affect product/domain behavior or architecture, require the FPP gate.

## Nested `AGENTS.md` files

Nested `AGENTS.md` files may add Phoenix/Ash/Elixir and directory-specific technical rules. They do not replace this root governance gate.

Any nested reference to a **"JIT Implementation Packet"** is legacy terminology and MUST be interpreted as the current **user-approved Feature Planning Pack (FPP)** defined here. If nested governance wording conflicts with this file, this root FPP governance controls while non-conflicting nested technical guidance still applies.
