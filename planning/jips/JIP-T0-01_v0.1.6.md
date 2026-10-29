# JIP-T0-01 v0.1.6 — Trusted Event-Create Action Boundary Hardening

- **ID:** JIP-T0-01
- **Version:** 0.1.6
- **Status:** APPROVED
- **Approved:** explicit user approval on 2026-10-29
- **Supersedes for implementation planning:** JIP-T0-01 v0.1.5; earlier versions remain historical
- **Governing spec:** SPEC-T0-01 v0.1.5
- **Roadmap horizon:** T0 — Tenant-scoped GA pending sale
- **Affected implementation item:** TICK-26
- **Blocking discovery:** TICK-63

This amendment preserves all canonical T0-01 product/domain semantics and changes only the implementation-locked action boundary required to make the governed `create_event` effect non-bypassable. Installed canonical contracts, ROADMAP and the active T0 tracer remain higher authority.

## 1. Trigger and verified baseline

Fresh control-tower review on 2026-10-29 verified:

- repository: `JCSchoeman96/ticketing`;
- signed/verified `main`: `6a3d0569ad872cdfc6c197a3108a7a90b15b5e0d`;
- CANON-1: 2.0.18;
- ROADMAP: B0 COMPLETE / T0 NEXT;
- active tracer: `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`;
- governing contracts remain TEN-1 2.0.1, IAM-1 4.1.3, IAM-2 1.5.0, EVT-1 3.0.0, EVT-2 3.0.0 and ERR-1 2.0.0;
- technical baseline remains Elixir 1.20.4 / OTP 29.1.2 / PostgreSQL 18.6 / Phoenix 1.8.16 / LiveView 1.2.13 / Ash 3.37.2 / AshPostgres 2.15.2 / ash_sql 0.8.4 / AshPhoenix 2.3.25 / Postgrex 0.22.4 / SimpleSat 0.1.4;
- secure runtime baseline remains Bandit 1.14.1 and DEV-only Tidewave 0.9.2;
- no authority, ROADMAP, tracer or dependency change created the blocker.

Reference refresh remains:

- Store_Blueprint_Hardening `0c41435a9f745aa7490a303e240bd48b58ea44ab` — REFERENCE_ONLY;
- LiveFrames `d03f635c779e86af907d9c1225b0bcba846bae62` — NOT_APPLICABLE.

No dependency upgrade or Ash capability adoption is approved by this amendment.

## 2. Reproduced blocker and root cause

TICK-63 records a deterministic negative test demonstrating that the TICK-26 candidate can construct a fabricated organizer persona map and invoke the private Event `persist_draft` Ash create action with authorization enabled. The write succeeds without Membership, User, Session or RoleAssignment proof.

The candidate architecture creates two distinct Event-write capability boundaries:

1. governed `create_event`, which performs the required proof chain; and
2. private `persist_draft`, whose bypass policy accepts a caller-supplied actor/persona by field shape.

`public? false` limits ordinary API/domain exposure but does not establish provenance or make the Ash action uncallable from trusted/internal code. The bypass policy therefore authorizes claims rather than proving that those claims were derived from the required persisted evidence in the current transaction.

The separate IAM `authorize_event_create` candidate also returns an ordinary map representing the authorized persona. Such a map or struct is not an unforgeable bearer credential and MUST NOT independently authorize a subsequent Event mutation.

This is an implementation-architecture defect. It does not expose a contradiction or missing product/domain rule in canonical authority.

## 3. Objective

Preserve the canonical T0-01 flow while making the final Event insert inseparable from it:

```text
candidate-org membership proof
→ persisted User, Session and role liveness
→ persisted active organization persona
→ IAM-1 evt.event.create authorization
→ single Event insert
```

The entire sequence remains one outer governed Ash/PostgreSQL transaction using the same transaction-local tenant context.

There must be no alternate Ash action, actor shape, synthetic persona or transferable intermediate object that can independently authorize the Event insert.

## 4. Decision classification

### CONTRACT_LOCKED — unchanged

- membership proof precedes all other tenant business-row reads;
- candidate `org_id` is only a selector until membership proof succeeds;
- failed proof preserves information hiding;
- post-proof User, Session and role liveness are required;
- trusted authentication/session infrastructure supplies authoritative `user_id` and `session_id`;
- IAM-1 alone owns `evt.event.create`;
- only canonical permitted human organization roles may satisfy `evt.event.create`;
- platform/support personas do not satisfy it unless separately governed by higher authority;
- the organizer persona is persisted-evidence-derived and transaction-local;
- no completed organizer persona is reusable across transactions;
- one outer `Ash.transact/3` boundary spans proof through Event insert;
- RLS/FORCE-RLS and the constrained runtime role remain required;
- EVT-2 draft Event invariants and ERR-1 behavior remain unchanged.

### IMPLEMENTATION_LOCKED — amended

1. `create_event` is the **single canonical production capability** that may result in insertion of a new Event row.
2. The final Event insert MUST be inseparable from the governed `create_event` proof and IAM authorization sequence in the same outer transaction.
3. There MUST NOT be a separately invokable Event persistence Ash action whose authorization can be satisfied by a caller-supplied or synthetic actor/persona.
4. The transaction-local organizer persona MAY exist as ephemeral orchestration state, but MUST NOT be treated as a bearer capability for a later write.
5. IAM authorization MAY return success/evidence for the current orchestration, but the returned value MUST NOT independently authorize a subsequent mutation.
6. Any Event persistence helper must be an implementation detail of the governed `create_event` execution path, not an alternate domain/action authorization boundary.
7. Do not use `authorize?: false` to bypass the requirement.
8. Do not duplicate IAM capability/role logic inside Events.
9. Do not introduce a cryptographic, signed, opaque, process-local or secret-bearing capability token to preserve the two-action design.
10. Do not rely on a private module, private constructor, struct type or actor-map shape as proof of authorization provenance.

### IMPLEMENTATION_FREE

Subject to the rules above:

- exact private helper/module/change layout;
- exact orchestration return shape when it is not reusable as authorization authority;
- exact failing-test file placement;
- test-only instrumentation used to prove action reachability and query/transaction ordering;
- mechanical migration/snapshot regeneration attributable only to the approved Event resource.

### AUTHORITY_GAP

None identified.

## 5. Resource/action ownership and interfaces

### Ticketing.Identity

Ownership remains unchanged. Identity supplies governed Membership/User/Session/RoleAssignment reads and owns IAM authorization semantics.

The organizer authorization step must consume the persisted records read in the current transaction and validate the canonical active organization persona. It must not expose a reusable production capability object.

### Ticketing.Events

Events owns the canonical Event resource and complete `create_event` effect.

The production interface remains the governed `create_event` action/domain interface only. No second production Event-create/persist action is authorized.

The Event row may be inserted only after the current transaction has satisfied all preceding proof and IAM checks.

## 6. Lifecycle and Event invariants

No lifecycle semantics change.

The successful transition remains:

```text
absent → draft
```

initiated only by an authorized human organizer.

The created Event remains:

- tenant-owned by the proven organization;
- UUIDv7 identified as already governed;
- assigned an action/server-generated public event key;
- `status = draft`;
- `published_at_utc = nil`;
- `version = 1`;
- `lock_version = 1`;
- database-owned timestamps;
- protected identity/tenant/status/time/version/fence fields not caller-authored;
- subject to canonical `(org_id, public_event_key)` and `(org_id, slug)` uniqueness.

## 7. Tenancy, authentication, actor and RLS

No tenancy or actor semantics change.

The same candidate `org_id` may be established in transaction-local context before proof solely so the matching TEN-1 Membership probe can run. It becomes proven organization context only after successful membership proof and remains unchanged through Event insertion.

No User, Session, RoleAssignment or Event business-row read/write may precede the matching Membership proof.

The final insert remains subject to tenant multitenancy and FORCE RLS under the constrained runtime role.

A synthetic actor/persona that merely contains `org_id`, `user_id`, `session_id`, membership id, role and capability fields is not sufficient authority.

## 8. Transactions, concurrency, idempotency and replay

The one outer transaction remains mandatory.

Required order remains:

```text
Membership probe
→ User liveness
→ Session liveness using authoritative DB UTC
→ RoleAssignment liveness
→ active organization persona validation
→ IAM-1 capability authorization
→ Event insert
```

The operation must stay on the same PostgreSQL backend transaction through the insert. Tenant context must not be cleared/re-established or switched mid-flow.

No stronger Session/role revocation linearization is introduced. No generic idempotency/replay contract is introduced. Database constraints remain authoritative for duplicate/concurrent uniqueness races.

## 9. Errors, events, outbox, jobs, audit and observability

ERR-1 remains governing error authority; this amendment creates no new canonical error.

Unauthorized or cross-tenant attempts must preserve hide-existence behavior.

Draft Event creation still emits no publication event, outbox row or job.

Observability restrictions remain unchanged: no raw `org_id`, `user_id`, `session_id`, credentials or token hashes in telemetry labels/logs.

TICK-63 itself is an execution/security discovery record, not a new product event/audit semantic.

## 10. Persistence, migrations and rollback

No schema change is expected solely because of this action-boundary amendment.

The existing Event migration/resource snapshot from the TICK-26 candidate must be regenerated only if current Ash codegen requires it after the action model is corrected. Any unexpected table, column, index, constraint, RLS, default or identity drift is a STOP condition and requires targeted re-Grill.

Rollback strategy is code rollback only to a previously safe non-merged state. The vulnerable two-action design is not an acceptable rollback target once this amendment is implemented.

## 11. Required tests

### Permanent forged-persona regression

The TICK-63 reproducer must become permanent repository coverage, adapted to the final implementation shape.

It must prove at minimum that:

- a caller cannot construct a synthetic actor/persona and cause an Event insert;
- no independently invokable Ash action can persist a new Event while skipping Membership/User/Session/role proof;
- a direct/internal action invocation attempt cannot turn actor-map shape into authorization provenance.

If the corrected design removes `persist_draft`, the regression should assert the absence/unavailability of any equivalent alternate write capability and exercise the nearest possible bypass attempt.

### Existing TICK-26 evidence remains required

Retain and freshly prove:

- `org_owner` success;
- `org_admin` success;
- Membership proof before every other tenant business-row read;
- same PostgreSQL backend transaction through Event insert;
- authoritative user/session/org/membership/role binding;
- active Session and DB-time expiry behavior;
- forged role denial;
- platform/support denial;
- invalid/mixed scope denial;
- cross-tenant information hiding;
- protected Event fields are not caller writable;
- canonical initial Event values and database-owned timestamps;
- rollback leaves no Event and does not mutate Session;
- duplicate/concurrent uniqueness outcomes are database-enforced;
- no tenant-context leakage after commit/rollback/exception and applicable pool-reuse coverage remains owned as previously sequenced with TICK-28.

## 12. Scope and non-goals

### In scope

- remove the alternate forgeable Event write capability;
- make Event insertion terminal to the governed `create_event` orchestration;
- adjust Identity/Event orchestration interfaces only as needed to remove bearer-persona semantics;
- permanent negative regression coverage;
- rerun all TICK-26 required evidence.

### Explicit non-goals

- no canonical contract change;
- no new capability or role;
- no IAM policy redesign;
- no dependency upgrade;
- no Session lifecycle mutation;
- no AuthIdentity/provider work;
- no reusable organizer resolver/persona;
- no occurrence/publication/outbox work;
- no commerce, pricing, inventory, order, payment, ticket or ledger work;
- no UI/API work;
- no new cryptographic/internal capability-token subsystem;
- no ordinary runtime Repo/Ecto/raw-SQL domain bypass.

## 13. Plane and execution impact

- TICK-63 remains the native blocker of TICK-26 **while the governance/action-boundary decision is unresolved**.
- After this approved amendment/spec merge to verified `main`, record the exact merged SHA and review/CI evidence on TICK-63 and close TICK-63 as the **governance blocker disposition**. That closure means the control-tower decision and safe recovery path are resolved; it MUST NOT be represented as proof that the staged TICK-26 code defect is already fixed.
- With TICK-63's governance blocker resolved, perform a fresh TICK-26 readiness check. TICK-26 may return to Ready only if no other blocker/staleness exists.
- The forged-persona failure remains a mandatory TICK-26 implementation/acceptance gate until the candidate code is corrected and freshly verified.
- PR #45 remains draft and its old head/CI/review evidence remains stale.
- The locally reconciled candidate must not be committed/pushed before the planning amendment is merged and Builder dispatch is refreshed.
- TICK-28 remains downstream and must not be pulled forward.

## 14. Documentation impact

### Planning/governance

**CREATE**

- `planning/jips/JIP-T0-01_v0.1.6.md`
- `planning/specs/SPEC-T0-01_v0.1.5.md`

**UPDATE after planning merge**

- TICK-22 governing packet reference if it names v0.1.5;
- TICK-26 governing packet/readiness reference;
- TICK-63 closure/disposition evidence;
- PR #45 planning references where necessary.

### Derived implementation docs after implementation merge

Existing T0-01 documentation impact remains. Update only affected implementation-state docs, including the Events domain dossier and tenancy/authorization material if the final merged action boundary changes their implementation description.

Do not claim future occurrence/publication behavior.

## 15. Risks and stop conditions

Stop and return to the control tower if:

- fixing the boundary requires changing canonical IAM/EVT semantics;
- the only apparent implementation requires `authorize?: false`;
- the implementation reintroduces a second independently invokable Event write capability;
- an authorization result must become a transferable bearer token;
- Events must duplicate IAM role/capability rules;
- same-backend transaction continuity cannot be preserved;
- membership-first ordering cannot be preserved;
- codegen produces unexpected persistence drift;
- TICK-25 interfaces must be semantically reopened;
- a dependency upgrade appears necessary;
- a new canonical error or lifecycle state appears necessary.

Any of these creates a new targeted Grill and may create an authority gap depending on the evidence.

## 16. Definition of Done for this amendment

This planning amendment is complete when:

- JIP-T0-01 v0.1.6 is explicitly approved by the user;
- SPEC-T0-01 v0.1.5 contains no semantics beyond this JIP;
- both planning artifacts receive exact-diff independent review;
- planning CI passes;
- the planning PR merges only after explicit user merge authorization;
- merged `main` is freshly verified;
- Plane references are refreshed;
- TICK-63 is closed only as the governance blocker disposition with wording that the implementation defect remains to be fixed in TICK-26;
- TICK-26 is re-readied only if no further blocker/staleness exists.

T0-01 implementation is not complete until corrected TICK-26 implementation, the permanent forged-persona regression, exact-head review/CI, explicit user merge authorization, merged-main verification and required derived documentation all pass.