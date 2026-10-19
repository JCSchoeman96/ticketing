# V42 — Enterprise Ticketing Core Foundation Spec (v1.3)
**Status:** LOCKED  
**Canonical:** true  
**Supersedes:** v1.2.1  
**Effective:** Immediately

---

## Purpose
V42 defines the **non-negotiable constitutional rules** of the platform. It does **not** specify features or UI.
All subsystems must comply with these invariants. Feature-specific behavior is governed by downstream contracts.

---

## What Changed in v1.3 (No Behavioral Drift)
- Explicitly declares **Seating & Dynamic Pricing** as first-class governed subsystems.
- Introduces **Feature Registry (FR-1)** as the planning surface for future capabilities.
- Confirms **Pricing ownership** and **Order snapshot invariants** for dynamic pricing engines.
- No changes to money, tenancy, or observability invariants.

---

## Core Invariants (Unchanged)
### Money & Ledger
- Double-entry, immutable journals.
- Idempotent money operations.
- No recomputation of historical prices.
- Payouts blocked on integrity violations.

### Inventory & Seats
- Inventory is truth; availability derives from inventory state.
- Seat holds are time-bounded, exclusive, and versioned.
- Orders capture **price snapshots**; prices never float after capture.

### Tenancy
- Every write path requires `org_id`.
- Postgres RLS enforced with transaction-local tenant injection.
- Cross-tenant access is a hard failure.

### Reliability & Ops
- Oban-only retries for side effects.
- Circuit breakers and degraded modes preserve correctness.
- Observability gates payouts and release actions.

---

## First-Class Governed Subsystems
These subsystems are governed by contracts that extend V42:

- **SEAT-1** — Seating Builder & Allocation Engine
- **PRICE-1** — Dynamic Pricing Rules & Versioning
- **ORD-1** — Order Snapshot & Price Capture
- **OBS-1** — Observability, Alerts, Runbooks
- **PSC-1** — Performance Budgets
- **OBQC-1** — Queue Capacity & Backpressure
- **DMSC-1** — Deployment & Migration Safety

Each subsystem:
- Must be versioned
- Must be deterministic
- Must not violate V42 invariants

---

## Explicit Non-Goals (Remain Deferred)
- CRM / Meeting Notes / Event Planning UX
- CMS / Editorial tooling
- Cashless wallet / stored value systems
- Hardware integrations (RFID) beyond credential abstraction
- Contract signing / document workflows

These are tracked in **FR-1** and may be added later without changing V42.

---

## Change Control
- V42 changes require cross-contract review.
- Any proposal that weakens invariants is rejected by default.
- Feature expansion must occur in downstream contracts.

---

## Canonical References
- Feature Registry: **FR-1_Platform_Feature_List_v1.0**
- Seating Contract: **SEAT-1 (upcoming)**
- Pricing Contract: **PRICE-1 (upcoming)**

---
