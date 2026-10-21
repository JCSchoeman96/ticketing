# Ticketing downstream implementation planning

This directory contains **downstream implementation-planning artifacts**. It is not canonical product authority and it does not describe merged implementation state.

Authority and execution precedence is:

```text
authority/contracts/CANON-1 + installed canonical contracts
→ authority/planning/ROADMAP.md
→ active tracer under authority/planning/tracers/
→ user-approved JIP under planning/jips/
→ derived implementation spec under planning/specs/
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

## Plane and implementation documentation

Plane is the execution ledger for dependencies, blockers, evidence and closure; it is not semantic authority.

`ticketing/docs/` is reserved for **derived documentation of merged implementation state**. Do not place speculative future architecture, JIPs or pre-implementation specs there.
