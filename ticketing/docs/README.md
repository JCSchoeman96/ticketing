# Implementation docs

These files are derived implementation documentation. They describe code that has merged and do not define product semantics. Canonical authority remains in [`authority/`](../../authority/).

## Platform

- [Runtime baseline](platform/runtime.md)
- [Database baseline](platform/database.md)
- [Tenancy and authorization](platform/tenancy-and-authorization.md)
- [Testing and quality gates](platform/testing-and-quality-gates.md)

## Domains

- [Identity](domains/identity/README.md)
- [Events](domains/events/README.md)

The merged T0-01 increment contains the governed organizer-to-draft-Event creation path and its supplemental TICK-28 verification. This does not implement Event publication, Occurrence, sales, commerce, ticketing or later T0 behavior. See the [T0-01 implementation handoff](handoffs/T0-01.md) for the merged-state record.

## Handoffs

- [T0-00 closeout record](handoffs/T0-00.md)
- [T0-01 closeout record](handoffs/T0-01.md)
