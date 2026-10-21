# Ticketing downstream implementation planning

This directory contains **downstream implementation-planning artifacts**. It is not canonical product authority and it does not describe merged implementation state.

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

Higher authority always wins.

## JIPs

`planning/jips/` stores versioned JIT Implementation Packets. Only explicit user acceptance makes a JIP `APPROVED`. A material change to its governing authority, tracer, baseline, prerequisite, scope, or locked decisions can make it `STALE` and requires targeted JIT review before implementation continues.

JIP filenames include their SemVer so amendments do not silently overwrite history.

## Specs

`planning/specs/` stores durable implementation specifications derived from an approved JIP. A spec may choose implementation mechanics within the JIP's allowed decision space, but it cannot create or override product semantics.

Specs are reviewed planning artifacts, not implementation authority independent of their governing JIP.

## Plans

`planning/plans/` stores executable implementation handoffs derived from an approved JIP and reviewed spec. Plans decompose work into the already-governed Plane tickets and their TDD/review steps; they do not grant READY status, authorize future tickets early, or create product semantics.

A plan is subordinate to the JIP/spec and to Plane freshness/dependency state. Implement only the single ticket currently marked `READY`; later plan sections remain inactive until their native dependencies are closed and freshness is rechecked.

## Plane and implementation documentation

Plane is the execution ledger for dependencies, blockers, evidence and closure; it is not semantic authority.

`ticketing/docs/` is reserved for **derived documentation of merged implementation state**. Do not place speculative future architecture, JIPs, pre-implementation specs, or execution plans there.
