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

The merged TICK-26 baseline now contains the governed organizer-to-draft-Event creation path. Occurrence creation, publication, sales, commerce, ticketing and later T0 behavior remain unimplemented unless a later merged dossier says otherwise.

## Handoffs

- [T0-00 closeout record](handoffs/T0-00.md)

`T0-01.md` is created only when the complete T0-01 increment has merged and its final closeout evidence can be frozen. TICK-28 remains downstream of TICK-26, so the T0-01 handoff is not yet final.
