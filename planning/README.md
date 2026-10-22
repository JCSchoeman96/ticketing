# Ticketing downstream implementation planning

This directory holds implementation-planning artifacts. It is not canonical product authority and does not describe merged implementation state.

Authority and execution precedence is:

```text
authority/contracts/CANON-1 + installed canonical contracts
→ authority/planning/ROADMAP.md
→ active tracer under authority/planning/tracers/
→ user-approved JIP under planning/jips/
→ derived implementation spec under planning/specs/
→ ticket-scoped execution plan under planning/plans/
→ Plane execution work
→ ticketing/ implementation
```

Higher authority wins.

## Current T0-01 planning set

- **Approved JIP:** [JIP-T0-01 v0.1.2](jips/JIP-T0-01_v0.1.2.md). It corrects the downstream planning drift while retaining the accepted Phoenix/LiveView baseline.
- **Current reconciled spec:** [SPEC-T0-01 v0.1.1](specs/SPEC-T0-01_v0.1.1.md), derived from JIP v0.1.2 and pending independent review of PR #21.
- **Execution plan:** [T0-01 implementation plan](plans/2026-10-21-t0-01-tenant-auth-rls-event.md), derived from JIP v0.1.2 and SPEC v0.1.1.
- **Plane parent:** TICK-22. TICK-31 records the earlier planning drift and remains open until its closeout requirements are met.

No implementation child becomes READY through this planning reconciliation.

## JIP history

JIP filenames use SemVer so amendments do not silently erase history.

- JIP v0.1.0 was the original approved packet. Its scope and approval history remain recorded in the amendment history of v0.1.1 and v0.1.2.
- [JIP-T0-01 v0.1.1](jips/JIP-T0-01_v0.1.1.md) was approved as a technical-baseline update. It is now superseded for implementation planning because downstream planning drift added AuthIdentity and narrowed the documentation impact.
- [JIP-T0-01 v0.1.2](jips/JIP-T0-01_v0.1.2.md) is the current approved packet.

A material change to canonical authority, tracer, baseline, prerequisite, scope, or locked decisions can make a JIP stale. Recheck freshness before implementation.

## Spec history

Specs derive from an approved JIP. They cannot create or override product semantics.

- [SPEC-T0-01 v0.1.0](specs/SPEC-T0-01_v0.1.0.md) is historical and superseded for implementation planning. It derives from the drifted v0.1.1 JIP.
- [SPEC-T0-01 v0.1.1](specs/SPEC-T0-01_v0.1.1.md) is the current reconciled spec for approved JIP v0.1.2, pending independent review of PR #21.

## Execution plans

Plans decompose JIP/spec decisions into existing Plane work. They do not grant READY status or add product semantics. Follow one child at a time, using its native dependency state and a fresh authority check.

## Plane and implementation documentation

Plane tracks execution, dependencies, blockers, evidence, and closure. It is not semantic authority.

`ticketing/docs/` is derived documentation of merged implementation state. Do not put speculative future architecture, pre-implementation specs, JIPs, or execution plans there.
