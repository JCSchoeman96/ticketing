# Roadmap

This is the active execution order beneath installed canonical authority. CANON and the installed contract suite govern every planning statement here.

## B0: Minimal implementation bootstrap

**Status: COMPLETE**

B0 is only the bootstrap needed to execute T0. The implementation repository is `JCSchoeman96/ticketing`, and the Phoenix application lives in `ticketing/`.

- Phoenix, Ash, and AshPostgres bootstrap exists.
- PostgreSQL and migration bootstrap exists.
- contract-authority verification exists.
- B0 no longer blocks T0.

B0 does not include product-domain work. Do not expand it into sales, inventory, orders, payment, or ticket behavior.

## T0: Tenant-scoped GA pending sale

**Status: NEXT**

Deliver one end-to-end general-admission sale path. An authenticated organizer uses explicit tenant context to create and publish an Event, configure the organization's Occurrence admission policy, and create an Occurrence whose explicit check-in window satisfies that policy. The organizer then configures a reusable PRICE-1 program revision and an OFFER-1 ProductRevision, and opens sales for a GA inventory bucket. A buyer retrieves the sellable offer, obtains a quote, claims inventory atomically, creates an idempotent Order, and retrieves the persisted Order in the same tenant.

EVT-2 has no implicit admission-policy default. An organization without a configured policy cannot create an Occurrence; policy changes apply prospectively and do not change persisted Occurrence windows.

The installed contracts define the GA hold-to-checkout path:

```text
SEAT-1.claim_bucket_inventory
→ signed InventoryBucketHold proof
→ SEAT-1.verify_bucket_hold_proofs
→ ORD-1.create_checkout
→ persisted tenant-scoped ORD-1 draft Order
```

This path does not require or permit a fabricated seat ID. `ProductRevision` binds to reusable `PricingProgramRevision` authority. Quote creation produces the transaction-specific signed PRICE-1 `PricingSnapshot`. The T0 TaxProfile uses `default_tax_basis = org_location` and T0 rounding uses `half_even_minor_units`.

The installed SEAT-1 4.1.0 and ORD-1 4.0.1 authorities define the GA bucket proof-to-checkout path. It is not an authority gap. Single-order `ORD-1.create_checkout` emits no checkout-created event. Do not invent one.

T0 ends with a persisted ORD-1 `draft` Order and same-tenant retrieval. It stops before provider payment confirmation, ORD finalization, seat or bucket allocation finalization, ticket issuance, and ledger work. Do not pull T1 into T0.

Use the resources, actions, lifecycle guards, idempotency rules, and error vocabulary recorded in [the active T0 tracer](tracers/T0-tenant-scoped-ga-pending-sale.md). Do not add private states, identities, transitions, events, or semantic bridges.

## T1: Provider-confirmed sale

```text
ORD-1 draft Order awaiting provider payment
→ payment/provider confirmation
→ replay-safe verified processing
→ paid sale
→ allocation finalized
→ ticket
→ minimal ledger
→ durable recovery
```

This is a high-level horizon. It does not add detail to T0.

## T2: Transaction and production hardening

High-level scope includes reconciliation, retries and quarantine, tenant red-team work, migration and release safety, concurrency and load, recovery, and observability and alerts.

## T3: Admission and financial closure

```text
ticket
→ online scan
→ duplicate or void denial
→ admission
→ reconciliation
→ closure
```

Offline scanning is outside this horizon unless current canonical authority requires it.
