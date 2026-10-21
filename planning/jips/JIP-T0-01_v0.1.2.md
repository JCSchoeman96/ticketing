# JIP-T0-01 v0.1.2 — Tenant/Auth/RLS Foundation + Event Create/Publish

- **ID:** JIP-T0-01
- **Version:** 0.1.2
- **Status:** APPROVED
- **Approved:** user instruction on 2026-10-21 identifies v0.1.2 as approved and directs downstream reconciliation
- **Supersedes for implementation planning:** JIP-T0-01 v0.1.1
- **Nature of change from v0.1.1:** planning-drift correction only; restores the originally approved v0.1.0 IAM scope and documentation impact while retaining the accepted v0.1.1 technical baseline; current reference evidence is refreshed without importing reference semantics
- **Roadmap horizon:** T0 — Tenant-scoped GA pending sale
- **Increment boundary:** tenant/auth/RLS foundation through Event create/publish; stops before Occurrence

This JIP is downstream implementation planning. Installed canonical contracts, ROADMAP and the active tracer remain higher authority.

## 1. Amendment and supersession history

### v0.1.0 — previously approved

The first approved T0-01 packet established the product/implementation boundary: separate migration-owner/runtime DB identities, Ash attribute multitenancy plus FORCE RLS, minimum persisted organizer authorization state, Event create/publish, optimistic/CAS fencing, and atomic durable publication outbox.

Its minimum IAM substrate was:

- global `User`;
- tenant `OrgMembership`;
- tenant `OrgRoleAssignment`.

Authentication-provider/session construction was explicitly deferred.

Its documentation impact required updates to the existing runtime/database/testing platform docs in addition to the new tenancy/domain/handoff docs.

### v0.1.1 — previously approved, now stale for implementation planning

TICK-20 updated the technical baseline to Phoenix 1.8.16 / LiveView 1.2.13 on repository main `b99e291ca6f388cd119c648bb89cd6e555f7033b`.

v0.1.1 correctly incorporated that technical baseline, but independent review of planning PR #21 found two unintended non-baseline changes:

1. it added `AuthIdentity` to T0-01 implementation scope;
2. it dropped the existing runtime/database/testing documentation updates.

Those changes were not produced by the TICK-20 re-Grill and contradicted the stated baseline-only purpose of v0.1.1. TICK-31 records this downstream planning defect. No implementation child became READY and no application code consumed the drift.

### v0.1.2 — approved correction

v0.1.2 retains the accepted v0.1.1 technical baseline and all settled T0-01 product/domain/architecture decisions, while restoring the original scope/documentation boundary:

- `AuthIdentity` implementation is not part of T0-01;
- T0-01 receives an already-authenticated human `user_id` at its trusted boundary;
- persisted authorization/persona derivation uses `User`, `OrgMembership`, and `OrgRoleAssignment` only;
- the existing runtime/database/testing docs are updated because this increment materially changes those implementation areas.

The Store_Blueprint_Hardening reference pin is also freshness-refreshed from `02cade1bbad64a1c49fc859bfd605c604eba37fa` to current `main` `da0dfa9b022f26872efe1f17277e62769c6c0808`. That reference remains `REFERENCE_ONLY`; its runtime-resource-safety review guidance is evidence for implementation review and creates no Ticketing product semantics or additional acceptance requirement by itself.

No lifecycle, tenancy, authorization meaning, persistence invariant, concurrency rule, error, event, outbox, observability or tracer boundary is otherwise changed.

## 2. Objective

Establish the smallest secure implementation substrate required for the first T0 tracer increment by delivering:

1. minimum persisted IAM authorization/persona state for an already-authenticated human organizer;
2. explicit tenant context through Ash and PostgreSQL;
3. forced database-level tenant isolation;
4. governed Event creation;
5. governed Event publication;
6. atomic persistence of registered `ticketing.event.published.v1`.

This increment stops before Occurrence.

## 3. Verified baseline

### Repository

- Repository: `JCSchoeman96/ticketing`
- Implementation baseline: `b99e291ca6f388cd119c648bb89cd6e555f7033b`
- Baseline tree: `15da625279eb8e67e03cad39d5e51063f74ef57a`
- Phoenix application: `ticketing/`

PR #20 changed only `ticketing/mix.lock`, resolving Phoenix 1.8.16 and LiveView 1.2.13. Its CI-tested synthetic merge and actual merge have the same tree. No separate push-to-main CI run materialized for the actual merge SHA; TICK-21 tracks that infrastructure/process defect. Do not state that exact-main push CI ran for PR #20.

### Canonical authority

- CANON-1 `2.0.16`
- TEN-1 `2.0.0`
- IAM-1 `4.1.2`
- IAM-2 `1.5.0`
- EVT-1 `3.0.0`
- EVT-2 `3.0.0`
- ERR-1 `2.0.0`
- OBS-1 `2.9.0`
- LOCKS-1 `3.0.0`
- API-0 `1.2.0`

Planning evidence:

- `authority/planning/ROADMAP.md`: B0 COMPLETE, T0 NEXT;
- active tracer: `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`.

### Runtime/framework baseline

Retain without hidden upgrades:

- Elixir `1.20.4`
- Erlang/OTP `29.1.2`
- PostgreSQL `18.6`
- Phoenix `1.8.16`
- Phoenix LiveView `1.2.13`
- Ash `3.36.1`
- AshPhoenix `2.3.25`
- AshPostgres `2.15.1`
- Postgrex `0.22.4`

No dependency upgrade is authorized inside T0-01 implementation.

### References

- Store_Blueprint_Hardening `da0dfa9b022f26872efe1f17277e62769c6c0808` — `REFERENCE_ONLY` for durable outbox/transaction/idempotency and relevant runtime-resource-safety review evidence; Ticketing authority and this JIP control semantics and acceptance.
- LiveFrames `bd8bc4daae8b0b3b0ad79c1711a798b5028b7784` — `NOT_APPLICABLE`; no material UI work.

## 4. Scope

### In scope

- migration-owner/runtime DB-role separation;
- transaction-local `app.current_org_id`;
- Ash attribute multitenancy on `org_id`;
- PostgreSQL ENABLE + FORCE RLS;
- minimum persisted IAM authorization substrate:
  - global `User`;
  - tenant `OrgMembership`;
  - tenant `OrgRoleAssignment`;
- organizer actor construction from persisted IAM state using already-authenticated `user_id` + explicit `org_id`;
- tenant-scoped Event;
- `EVT-2.create_event`;
- `EVT-2.publish_event`;
- Event state/version/lock-version CAS;
- atomic durable `ticketing.event.published.v1` outbox persistence;
- required positive, negative, cross-tenant, race, replay, rollback and pool-isolation tests;
- approved derived implementation documentation after implementation merges.

### Explicit non-goals

- `AuthIdentity` persistence/implementation;
- authentication-provider integration;
- password, magic-link, OAuth or service-token flows;
- AshAuthentication;
- Session persistence/login UI;
- Event archive implementation;
- Occurrence and occurrence sales lifecycle;
- pricing, offer/product, tax, inventory, hold, quote, checkout, Order;
- payment, ticket, ledger, admission;
- background outbox dispatch / Oban / AshOban;
- PubSub as a substitute for durable publication event persistence;
- UI/LiveView features;
- dependency upgrades;
- later T0/T1 work.

## 5. Decision classification

### CONTRACT_LOCKED

Canonical authority controls:

- explicit `org_id` tenancy and hide-existence behavior;
- active membership/role authorization semantics;
- Event identity, shape, lifecycle and DB-time requirements;
- Event version/lock fencing;
- `ticketing.event.published.v1` event semantics;
- canonical errors;
- mutation/event atomicity;
- actor and tenant boundaries.

### IMPLEMENTATION_LOCKED

This JIP selects:

- separate migration/owner and runtime DB identities;
- runtime DB roles are non-owner, non-superuser, `NOBYPASSRLS`, no `CREATEDB`, no `CREATEROLE`;
- ENABLE + FORCE RLS;
- transaction-local `app.current_org_id` on the same backend transaction/connection as tenant SQL;
- Ash attribute multitenancy on `org_id`;
- explicit actor + explicit Ash tenant;
- actor roles derived from persisted membership/role state rather than caller input;
- Event `version`/`lock_version` optimistic fencing;
- PostgreSQL durable publication outbox;
- DB uniqueness preventing duplicate publication for the semantic Event publication identity/version;
- no asynchronous dispatcher in this increment.

### IMPLEMENTATION_FREE

Provided governed semantics do not change:

- exact `Ticketing` module/file layout;
- helper names;
- internal policy/check/change decomposition;
- migration/index/policy object names;
- test factory/helper design;
- exact narrow infrastructure helper used for same-connection tenant GUC setup;
- internal outbox resource/table name;
- internal noncanonical structured-log names.

### AUTHORITY_GAP

None identified at approval time.

## 6. Ash capability decisions

### ADOPT

- Ash core;
- AshPostgres;
- AshPhoenix where needed at the application boundary;
- Ash authorization policies;
- Ash attribute multitenancy on `org_id`;
- governed Ash transaction boundaries;
- PostgreSQL constraints/FKs/indexes/RLS as defence in depth.

### DEFER

- AshAuthentication;
- AshStateMachine;
- AshOban;
- Ash Signals;
- Temporal Resources;
- explicit Reactor adoption;
- AshPaperTrail;
- Ash Storage;
- JSON:API.

### REJECT for T0-01

- AshArchival as Event lifecycle implementation;
- direct Repo/Ecto CRUD as runtime domain API;
- `authorize?: false` for ordinary organizer behavior;
- application-only tenant filtering as an RLS substitute;
- session-scoped tenant GUCs;
- process-dictionary tenant truth;
- hidden dependency upgrades.

If canonical runtime behavior appears to require a persistence bypass, stop affected work and return through the targeted JIT/JIP process.

## 7. Database owner/runtime separation

Shared-local owner/bootstrap/migration identities remain:

- DEV: `ticketing_dev`;
- TEST: `ticketing_test`.

The TEST owner may retain `CREATEDB` only for deterministic `MIX_TEST_PARTITION` database provisioning.

Normal runtime identities:

- DEV: `ticketing_dev_runtime`;
- TEST: `ticketing_test_runtime`;
- CI: ephemeral equivalent.

Runtime roles MUST NOT be superuser, BYPASSRLS, table owner, CREATEDB or CREATEROLE. Grant only required runtime privileges.

Normal application processes use runtime credentials; migration/bootstrap uses owner credentials. Ticketing must not lifecycle-create/rotate shared-local workstation roles or broaden owner privileges for convenience. Production likewise separates runtime from migration-owner credentials.

## 8. Tenant/RLS model

Every tenant-owned table introduced here:

1. requires non-null `org_id`;
2. preserves tenant-first identities/indexes where authority requires them;
3. carries `org_id` through tenant relationships/FKs;
4. enables RLS;
5. forces RLS;
6. uses read/write policy semantics equivalent to `org_id = current_setting('app.current_org_id', true)::uuid`;
7. fails closed for missing/malformed tenant context;
8. hides cross-tenant resources at the public boundary;
9. is accessed by a runtime role unable to bypass RLS.

Tenant UUID is validated before setting the GUC. The GUC is transaction-local only (`SET LOCAL` / equivalent `set_config(..., true)`), established before tenant SQL on the same backend transaction/connection, and absent after commit/rollback/pool reuse.

Ash explicit tenant filtering and PostgreSQL RLS are independent required guards.

## 9. IAM resources and organizer actor

### User

Global, non-PII canonical human principal required by the persisted IAM relationship model.

### OrgMembership

Tenant scoped. Preserve:

- UUIDv7 `org_membership_id`;
- canonical tenant identity involving `(org_id, org_membership_id)`;
- existing `(org_id, user_id)` identity/uniqueness;
- active/revoked lifecycle semantics.

`org_membership_id` identifies the selected active persona; it does not replace `org_id` as RLS tenant context.

### OrgRoleAssignment

Tenant scoped. Preserve canonical tenant/user/role assignment identity and revocation semantics.

### AuthIdentity

Not implemented by T0-01. Authentication/provider identity mapping remains outside this increment. The T0-01 boundary receives an already-authenticated human `user_id` from a trusted upstream/authentication boundary and builds only the persisted organization persona/authorization context required by Event actions.

### Organizer derivation

The caller cannot assert authoritative roles.

Given authenticated `user_id` + explicit `org_id`, governed Identity logic:

1. loads the same-tenant membership;
2. requires active/non-revoked membership;
3. derives the persisted `org_membership_id`;
4. loads active/non-revoked org role assignments;
5. constructs the human organizer actor/persona;
6. ignores externally fabricated roles.

Event create/publish requires active `org_owner` or `org_admin` authority under current IAM contracts. Platform/support personas do not satisfy this path.

## 10. Event lifecycle/actions

### Create Event

Transition: `absent → draft`.

Requirements:

- explicit tenant;
- authorized human organizer;
- valid canonical input;
- DB-owned timestamps;
- `published_at_utc = null`;
- initial `version = 1`;
- initial `lock_version = 1`;
- concurrency fence not client-authored.

Rejected create writes nothing.

### Publish Event

Transition: `draft → published`.

Guards:

- same tenant;
- authorized human organizer;
- current state `draft`;
- expected/current lock fence match.

Atomic effects:

1. status → `published`;
2. DB publication time;
3. Event version increments;
4. lock_version increments;
5. durable `ticketing.event.published.v1` outbox row inserted in the same PostgreSQL transaction.

Invalid/stale publish returns governing precondition failure and writes neither transition nor outbox row.

No Event archive or Occurrence implementation in this JIP.

## 11. Persistence, transactions, concurrency and replay

Use governed Ash resources/actions backed by AshPostgres for canonical runtime state. DB constraints are authoritative race-safe enforcement beneath Ash.

### Publication transaction

One DB transaction contains:

- state compare;
- lock/version CAS compare;
- Event state/time/version/fence mutation;
- publication outbox insert.

No split-phase publication and no read-then-write correctness substitute.

### Race

Two concurrent publish attempts from the same draft/fence produce exactly one winner. The loser writes nothing. Exactly one durable publication exists for the committed Event version.

### Replay/duplicate

A completed publication cannot create a second publication row for the same Event version. State/fence guards plus DB uniqueness independently protect against duplicate persistence. This does not invent generic HTTP Event idempotency.

### Rollback

Outbox insertion failure rolls back the Event mutation; Event mutation failure leaves no orphan publication row.

### Outbox

Canonical payload is exactly the registered Event publication payload required by EVT-1/EVT-2 (`event_id`, committed `version`). Required `org_id`, request/trace and registry/envelope context is persisted outside the domain payload as required by current authority.

DB uniqueness must be semantically equivalent to the registered publication identity `(org_id, event_id, version)`; if a generic outbox table stores multiple event types, include the event-type discriminator in the physical unique key without changing the canonical event-specific dedupe meaning.

No worker/dispatcher/broker/PubSub delivery behavior is implemented.

## 12. Canonical errors and fail-closed behavior

Required boundary behavior includes:

- missing Ash tenant → `Ash.Error.Invalid.TenantRequired` internally;
- hidden cross-tenant resource → external `ERR_NOT_FOUND`;
- unauthenticated organizer → `ERR_UNAUTHENTICATED`;
- insufficient organizer authority → `ERR_FORBIDDEN`;
- invalid Event input → `ERR_VALIDATION`;
- invalid lifecycle/stale CAS → `ERR_PRECONDITION`;
- outbox failure → transaction failure with no publication;
- CAS loser → no Event/outbox write.

Do not leak PostgreSQL/Ash implementation errors as product semantics and do not reveal hidden cross-tenant existence through differentiated errors.

## 13. Observability/audit

Carry/correlate as applicable:

- `org_id`;
- actor/persona identity;
- `request_id`;
- `trace_id`;
- operation/action ID (`EVT-2.create_event`, `EVT-2.publish_event`).

Use existing Ash/Phoenix telemetry and structured logs; OBS-1 owns canonical names. Do not add an observability dependency or invent metric/span vocabulary. Do not log credentials, secrets, unnecessary PII or hidden cross-tenant identifiers to callers.

Implement only audit persistence actually required by current authority; no generic audit stream.

## 14. Migration, rollout and rollback

Implementation order:

1. establish/verify owner-vs-runtime credential/privilege model;
2. establish transaction-local tenant/RLS substrate;
3. add minimum IAM schema (`User`, `OrgMembership`, `OrgRoleAssignment`);
4. add Event schema;
5. add publication outbox;
6. add/review tenant composite keys/FKs/indexes;
7. create/enable/force RLS and grants;
8. prove runtime privilege/RLS posture;
9. run domain tests under runtime identity.

Generated AshPostgres migrations/snapshots must be inspected; generated output does not override canonical tenant identities/FKs/RLS/defaults/concurrency requirements.

DEV/TEST continue to use the existing physically separated PostgreSQL 18.6 clusters at ports 55432/55433. Do not lifecycle-manage workstation `dev-core`. TEST owner may provision partition DBs; ordinary tests/application behavior run as runtime role.

CI remains tool-owned PostgreSQL 18.6 and must exercise the same owner/runtime distinction sufficiently to prove RLS assumptions.

Rollback respects migration dependencies; never disable RLS or broaden runtime privileges as a shortcut. Do not delete/reuse retained legacy PostgreSQL 16/Redis evidence assets without separate authorization.

## 15. Required tests

### Database/security

- runtime role non-superuser/NOBYPASSRLS/non-owner/no CREATEDB/no CREATEROLE;
- owner/runtime identities distinct;
- ENABLE + FORCE RLS present;
- no/malformed tenant GUC fails closed;
- tenant A cannot read/update/delete tenant B or insert claiming tenant B;
- GUC absent after commit and rollback;
- pooled/Sandbox reuse cannot leak tenant;
- partitioned TEST databases prove the same posture.

### IAM/authorization

- active `org_owner` succeeds;
- active `org_admin` succeeds;
- missing/inactive/revoked membership denied;
- missing/revoked qualifying role denied;
- platform/support persona denied;
- fabricated caller role does not grant access;
- actor uses selected persisted `org_membership_id`;
- cross-tenant IAM rows remain hidden.

### Event create/publish

- create produces draft Event with DB timestamps, version=1, lock_version=1, null publication time;
- client cannot author the fence;
- publish produces published state, DB publication time, incremented version/fence and one durable publication row;
- invalid/non-draft/stale publish writes nothing;
- cross-tenant Event hidden.

### Race/replay/rollback

- concurrent publish yields one winner/one loser and one outbox row;
- duplicate completed attempt cannot add a second publication for the same Event version;
- injected outbox failure leaves Event draft with unchanged version/fence and no outbox row.

### Context/bypass/migration

- request/trace/org/actor context reaches required governed/outbox/observability boundaries;
- every direct Repo/Ecto/raw-SQL occurrence is reviewed and confined to approved migration/DDL/RLS/test-fixture/tenant-context infrastructure;
- no `authorize?: false` on ordinary governed paths;
- clean PostgreSQL 18.6 migration/codegen/rollback-reapply evidence where applicable.

## 16. Documentation impact

### UPDATE

- `ticketing/docs/README.md` — navigation only as required;
- `ticketing/docs/platform/runtime.md` — actual owner/runtime credential/runtime behavior;
- `ticketing/docs/platform/database.md` — implemented role/RLS/persistence posture;
- `ticketing/docs/platform/testing-and-quality-gates.md` — implemented runtime-role/RLS/partition/security verification.

### CREATE

- `ticketing/docs/platform/tenancy-and-authorization.md`;
- `ticketing/docs/domains/identity/README.md`;
- `ticketing/docs/domains/events/README.md`;
- `ticketing/docs/handoffs/T0-01.md`.

Documentation describes merged implementation state only, identifies its derived nature/governing JIP/verified SHA where appropriate, and must not present Occurrence or later T0 architecture as implemented.

## 17. Durable spec / Plane execution

`to-spec`: REQUIRED because this increment crosses DB identities, migrations, RLS, tenant propagation, IAM persistence, Ash policies, Event lifecycle, concurrency and atomic outbox persistence.

For approved v0.1.2:

- update SPEC-T0-01 to derive from v0.1.2 and remove `AuthIdentity` implementation;
- restore the existing platform-doc updates in the execution plan and TICK-29;
- keep the native Plane chain TICK-23 → TICK-24 → TICK-25 → TICK-26 → TICK-27 → TICK-28 → TICK-29 → TICK-30;
- no implementation child becomes READY until planning PR review/merge and fresh dependency/freshness check.

## 18. Risks and stop conditions

Stop/re-Grill if:

1. Ash cannot guarantee same-backend-transaction tenant GUC setup;
2. AshPostgres cannot express canonical tenant/RLS persistence without an unapproved runtime bypass;
3. organizer derivation actually requires AuthIdentity/session/provider semantics for this increment;
4. Event publish cannot preserve CAS or same-transaction outbox persistence;
5. authority requires delivery (not only durable enqueue) as publication completion;
6. governing CANON/contracts/tracer/baseline/prerequisites materially change;
7. an unapproved dependency upgrade becomes necessary.

TICK-21 remains an independent CI-process defect. TICK-31 records the v0.1.1 planning drift and remains open through the reconciliation PR closeout. Its native blocking relation remains in place; no implementation child is READY.

## 19. Definition of Done

T0-01 closes only when:

- this JIP is explicitly APPROVED and remains fresh;
- derived spec/Plane graph are current;
- only fresh dependency-clear child work entered READY;
- each material behavior used TDD;
- owner/runtime separation proven;
- FORCE RLS and non-bypass runtime posture proven;
- transaction-local tenant isolation proven leak-free;
- persisted membership/role state derives organizer authority;
- Event create/publish pass;
- cross-tenant, race, replay and rollback tests pass;
- exactly one publication row exists per successful Event publication version;
- generated migrations/snapshots are reviewed;
- `mix precommit`, `mix check`, `mix check.types`, applicable codegen/migration checks and fresh PR-head CI pass;
- exact diffs receive independent review;
- merge result is verified;
- required UPDATE + CREATE implementation docs are truthful and handoff is verified against merged SHA;
- no unresolved blocker/authority gap affects the increment;
- Plane evidence supports closure.

## 20. Approval gate

**APPROVED.**

Approval record: the user instruction dated 2026-10-21 identifies `JIP-T0-01 v0.1.2` as approved and directs the durable spec, execution plan, Plane, and planning navigation to reconcile to it.

This packet is a narrow correction of planning drift: it retains the accepted Phoenix/LiveView baseline from v0.1.1, restores v0.1.0's minimum IAM scope (`User` + `OrgMembership` + `OrgRoleAssignment`), defers `AuthIdentity`, and restores updates to the existing runtime/database/testing implementation docs. The Store_Blueprint_Hardening pin was freshness-refreshed as `REFERENCE_ONLY` evidence only; it does not alter Ticketing semantics. All other settled T0-01 decisions remain unchanged.