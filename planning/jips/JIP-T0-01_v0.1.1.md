# JIP-T0-01 v0.1.1 — Tenant/Auth/RLS Foundation + Event Create/Publish

- **ID:** JIP-T0-01
- **Version:** 0.1.1
- **Status:** APPROVED
- **Approved by:** user, 2026-10-21
- **Supersedes for implementation planning:** JIP-T0-01 v0.1.0
- **Nature of change from v0.1.0:** technical-baseline amendment only; product/domain semantics unchanged
- **Roadmap horizon:** T0 — Tenant-scoped GA pending sale
- **Increment boundary:** tenant/auth/RLS foundation through Event create/publish; stops before Occurrence

## 1. Objective

Establish the first production-grade tenant/auth/RLS substrate and implement the first complete T0 lifecycle through `EVT-2.create_event` and `EVT-2.publish_event`, including atomic persistence of the registered `ticketing.event.published.v1` outbox record.

This JIP proves the security, authorization, transaction, concurrency, and durable-event foundations needed by later T0 work without pulling Occurrence or commerce forward.

## 2. Exact verified baseline

At approval:

- repository: `JCSchoeman96/ticketing`
- `main`: `b99e291ca6f388cd119c648bb89cd6e555f7033b`
- tree: `15da625279eb8e67e03cad39d5e51063f74ef57a`
- CANON-1: `2.0.16`
- active roadmap: `authority/planning/ROADMAP.md`, T0 = `NEXT`
- active tracer: `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`

Governing installed authority includes:

- TEN-1 `2.0.0`
- IAM-1 `4.1.2`
- IAM-2 `1.5.0`
- EVT-1 `3.0.0`
- EVT-2 `3.0.0`
- ERR-1 `2.0.0`
- OBS-1 `2.9.0`
- LOCKS-1 `3.0.0`
- API-0 `1.2.0`

Technical baseline:

- Elixir `1.20.4`
- Erlang/OTP `29.1.2`
- PostgreSQL `18.6`
- Phoenix `1.8.16`
- Phoenix LiveView `1.2.13`
- Ash `3.36.1`
- AshPhoenix `2.3.25`
- AshPostgres `2.15.1`
- Postgrex `0.22.4`

PR #20 changed only the resolved Phoenix/LiveView patch baseline in `ticketing/mix.lock`. No T0-01 product/domain implementation was introduced.

### CI closeout note

PR #20's reviewed synthetic merge `7e21825d39fb241e5fcff3f0cd2ac4ee49671849` and actual merge `b99e291ca6f388cd119c648bb89cd6e555f7033b` have the identical Git tree `15da625279eb8e67e03cad39d5e51063f74ef57a`. Full PR CI passed on that tree. A separate `push` CI run did not materialize for the actual merge SHA; that process defect is tracked as TICK-21 and MUST NOT be misreported as exact-main CI evidence.

## 3. Reference evaluation

### Store_Blueprint_Hardening

- verified reference commit: `02cade1bbad64a1c49fc859bfd605c604eba37fa`
- classification: `REFERENCE_ONLY`
- useful evidence: durable PostgreSQL outbox patterns, transaction discipline, replay/idempotency test ideas
- Ticketing authority remains controlling for tenancy, identity, lifecycle, errors, and event ownership

### LiveFrames

- verified reference commit: `bd8bc4daae8b0b3b0ad79c1711a798b5028b7784`
- classification: `NOT_APPLICABLE`
- reason: this increment contains no material UI work

## 4. Scope

### In scope

1. Migration-owner/runtime-role separation.
2. Transaction-local PostgreSQL `app.current_org_id` context.
3. Ash attribute multitenancy for tenant-owned resources.
4. PostgreSQL `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` for tenant-owned tables introduced here.
5. Minimum persisted IAM authorization substrate required to derive an organizer actor:
   - global `User`;
   - global `AuthIdentity` only to the extent required by the canonical persisted substrate;
   - tenant-scoped `OrgMembership`;
   - tenant-scoped `OrgRoleAssignment`.
6. Organizer actor/persona derivation from persisted IAM state.
7. Canonical Event resource.
8. `EVT-2.create_event`.
9. `EVT-2.publish_event`.
10. Event state + `lock_version` CAS/version fencing.
11. Atomic durable `ticketing.event.published.v1` outbox persistence.
12. Positive, negative, cross-tenant, race, replay/dedupe, pool-leakage, and rollback tests.
13. Derived implementation documentation and T0-01 handoff.

### Explicit non-goals

- authentication-provider integration;
- password, magic-link, OAuth, or service-token login flows;
- AshAuthentication;
- session persistence or login UI;
- Occurrence or occurrence sales lifecycle;
- pricing, tax, offers, products, inventory, holds, quote, checkout, Order;
- payment, ticket, ledger, admission;
- background outbox dispatch, jobs, Oban/AshOban;
- PubSub delivery as a substitute for the durable outbox;
- LiveView/UI work;
- dependency upgrades;
- later T0/T1 semantics.

## 5. Technology and Ash decisions

### ADOPT

- Ash core, AshPostgres, and AshPhoenix where needed by application boundaries.
- PostgreSQL-backed Ash Resources.
- Ash policies and explicit actor context.
- Ash attribute multitenancy on `org_id`.
- Governed Ash transactions.
- PostgreSQL constraints, composite tenant keys/FKs, indexes, RLS, and transaction primitives as defence-in-depth.
- Optimistic/CAS fencing required by Event publication.

### DEFER

- AshAuthentication
- AshStateMachine
- AshOban
- Ash Signals
- Temporal Resources
- explicit Reactor adoption
- AshPaperTrail
- Ash Storage
- JSON:API

### REJECT for T0-01

- AshArchival as Event lifecycle implementation.
- Direct Repo/Ecto CRUD as an alternative canonical runtime API.
- `authorize?: false` for ordinary organizer behavior.
- Application-side tenant filtering as an RLS substitute.
- Session-level tenant GUCs.
- Process-dictionary/ambient mutable tenant truth.
- Hidden dependency upgrades.

Any apparent need to bypass Ash/AshPostgres for ordinary canonical runtime behavior is a STOP condition requiring a targeted JIT re-Grill.

## 6. Decision classes

### CONTRACT_LOCKED

- explicit `org_id` tenant context and cross-tenant hide-existence behavior;
- active membership/role authorization semantics;
- qualifying organizer roles and human actor posture;
- Event identity, shape, initial state, and lifecycle;
- database-owned timestamps where prescribed;
- Event `version` and `lock_version` fencing;
- publication event type/payload/envelope requirements;
- atomic mutation + durable event enqueue;
- canonical error semantics.

### IMPLEMENTATION_LOCKED

- separate DB owner/migration and application runtime identities;
- existing DEV/TEST roles serve owner/bootstrap duties, not ordinary runtime duties;
- dedicated least-privilege runtime roles;
- runtime role is non-superuser, `NOBYPASSRLS`, non-owner, no `CREATEDB`/`CREATEROLE`;
- Ash attribute multitenancy on `org_id`;
- transaction-local `app.current_org_id` installed on the exact transaction connection before tenant SQL;
- tenant tables use ENABLE + FORCE RLS;
- organizer actor derives from persisted IAM state, not caller-trusted role lists;
- publication outbox persists in PostgreSQL;
- publication dedupe is database-enforced around the semantic identity `(org_id, event_id, version)` scoped to the publication event;
- no outbox dispatcher in this increment.

### IMPLEMENTATION_FREE

Provided no governed semantics change:

- exact internal module/helper names;
- internal file decomposition beneath approved domain boundaries;
- migration/index/policy object names;
- factory/helper layout;
- internal outbox resource/table name;
- exact infrastructure helper used to install transaction-local tenant context, provided the same-connection invariant is proven.

### AUTHORITY_GAP

None currently identified.

## 7. Resource/action ownership and interfaces

All governed canonical runtime state MUST use Ash Resources registered with approved Ash Domains and `AshPostgres.DataLayer` unless a newly approved exception says otherwise.

### Global IAM

**User** — global, non-tenant principal resource. Preserve IAM-1's non-PII ownership boundary.

**AuthIdentity** — global persisted identity substrate only as required by current IAM authority. T0-01 does not create full provider-login/session behavior.

### Tenant IAM

**OrgMembership** — tenant-scoped; includes stable immutable UUIDv7 `org_membership_id`, `org_id`, `user_id`, canonical liveness/revocation fields, tenant identity `(org_id, org_membership_id)`, and preserved uniqueness `(org_id, user_id)`.

**OrgRoleAssignment** — tenant-scoped; preserves canonical org/user/role assignment semantics and revocation/liveness behavior.

### Events

**Event** — tenant-scoped EVT-2 resource. Public governed actions in this JIP are `create_event` and `publish_event`; generic status mutation MUST NOT replace lifecycle intent.

### Event outbox

One internal PostgreSQL-backed Ash resource/table is permitted to persist the required canonical publication envelope atomically. It is not a second public domain API.

Cross-domain callers MUST use approved Ash/domain interfaces, not persistence-level coupling.

## 8. Actor, tenant, authorization and RLS

The caller MUST NOT supply authoritative roles. The organizer actor is reconstructed from persisted IAM state using explicit `user_id` + selected `org_id` and contains the canonical selected `org_membership_id` and active role context.

Event create/publish require:

- human actor kind;
- active organization persona;
- active qualifying role, including `org_owner` or `org_admin`;
- same-tenant authorization.

Platform/support/service/system personas do not satisfy this organizer capability merely by representation.

For each tenant-scoped table introduced here:

1. `org_id` is required and non-null.
2. Tenant keys/unique identities place `org_id` first unless canonical authority explicitly requires otherwise.
3. Tenant FKs carry tenant identity where necessary to prevent cross-tenant references.
4. RLS is enabled.
5. RLS is forced.
6. Read policy checks `org_id` against transaction-local `app.current_org_id`.
7. Write policy applies the equivalent condition through `WITH CHECK`.
8. Missing/malformed context fails closed.
9. Cross-tenant resources are hidden according to TEN/ERR authority.

Policy behavior is semantically equivalent to:

```sql
org_id = current_setting('app.current_org_id', true)::uuid
```

The tenant UUID is validated before setting the GUC. Only transaction-local `SET LOCAL` / `set_config(..., true)` behavior is allowed. Pool reuse MUST NOT leak tenant context.

## 9. Database identity posture

Owner/bootstrap identities remain:

- DEV: `ticketing_dev`
- TEST: `ticketing_test`
- CI: equivalent ephemeral job-owned migration identity

Application runtime identities:

- DEV: `ticketing_dev_runtime`
- TEST: `ticketing_test_runtime`
- CI: ephemeral equivalent

Runtime roles MUST NOT be superusers, `BYPASSRLS`, table owners, `CREATEDB`, or `CREATEROLE`. They receive only required runtime privileges.

The TEST owner may retain `CREATEDB` solely for deterministic `MIX_TEST_PARTITION` database provisioning. Partitioned tests then exercise the runtime role for normal application operations.

Production configuration MUST separate migration/owner credentials from application/runtime credentials.

## 10. Event lifecycle and persistence

### Create Event

Transition: `absent → draft`.

Required results:

- explicit tenant;
- authorized human organizer;
- valid canonical input;
- server/database-owned timestamps as prescribed;
- `published_at_utc = null`;
- initial `version = 1`;
- initial `lock_version = 1`.

Client input cannot author the concurrency fence. Failure writes nothing.

### Publish Event

Transition: `draft → published`.

Guards:

- same tenant;
- authorized organizer;
- current state is `draft`;
- expected/current optimistic lock fence matches.

One transaction atomically:

1. changes status to `published`;
2. sets `published_at_utc` from database time;
3. increments Event `version`;
4. increments Event `lock_version`;
5. inserts the registered `ticketing.event.published.v1` outbox row.

Invalid lifecycle or stale fence returns the governed precondition failure and writes neither Event transition nor outbox record.

## 11. Publication outbox

Registered event type: `ticketing.event.published.v1`.

Canonical payload contains:

- `event_id`
- committed Event `version`

The durable envelope/context carries governing canonical metadata, including where required:

- `org_id`
- `request_id`
- `trace_id`
- registered event identity/registry metadata

Do not add product semantics to the payload.

Durable publication dedupe identity is backed by a DB unique constraint semantically covering the publication event plus `(org_id, event_id, version)`.

Canonical event content/identity is immutable after enqueue except future delivery bookkeeping that cannot alter canonical payload identity.

Background delivery is deferred.

## 12. Transactions, concurrency, replay/dedupe and rollback

Create uses the governed Ash action transaction where applicable.

Publish state mutation and required outbox insertion MUST share the same PostgreSQL transaction and backend connection.

For concurrent publish attempts from the same draft/fence:

- exactly one transition may succeed;
- the loser writes nothing;
- only one publication outbox row for that Event version survives.

A retry after successful publication MUST NOT produce a second state transition or outbox row. This follows lifecycle failure plus independent DB uniqueness; no unrelated generic HTTP idempotency system is invented.

Any required outbox insert failure MUST roll back the Event publication. Any Event mutation failure MUST leave no orphan publication row.

## 13. Canonical error posture

Required boundary behavior includes:

- missing Ash tenant: internal `Ash.Error.Invalid.TenantRequired` posture;
- cross-tenant hidden resource: canonical external not-found behavior;
- unauthenticated organizer: `ERR_UNAUTHENTICATED` where applicable at the boundary;
- authenticated actor lacking authority: `ERR_FORBIDDEN` where existence is not hidden;
- invalid Event input: `ERR_VALIDATION`;
- invalid/stale lifecycle transition: `ERR_PRECONDITION`;
- outbox persistence failure: transaction error with no published Event.

PostgreSQL policy/constraint/Ecto internals MUST NOT leak as public domain error semantics.

## 14. Observability and audit

Carry and correlate, where applicable:

- `org_id`
- actor/persona identity
- `request_id`
- `trace_id`
- operation identity (`EVT-2.create_event`, `EVT-2.publish_event`)

Use existing Ash/Phoenix telemetry/tracing and structured logging in accordance with OBS-1. Do not invent new canonical metric/event vocabulary.

Do not log credentials, secrets, unnecessary PII, or caller-visible information that defeats cross-tenant hiding.

Implement only audit persistence required by governing authority; do not invent a generic audit subsystem.

## 15. Migration, rollout and rollback

Migration work MUST follow `authority/planning/architecture/migration-safety.md`.

Rollout order:

1. provision/verify owner and runtime role posture;
2. add minimum IAM schema;
3. add Event schema;
4. add publication outbox schema;
5. establish tenant-first constraints/FKs/indexes;
6. create RLS policies;
7. ENABLE RLS;
8. FORCE RLS;
9. grant minimum runtime privileges;
10. configure application runtime to use runtime credentials;
11. verify role/RLS/schema posture before domain tests.

Generated AshPostgres migrations MUST be inspected; generator output is not presumed to satisfy Ticketing composite tenant keys, FKs, RLS, checks, or rollback requirements.

DEV/TEST continue to use workstation-owned shared PostgreSQL endpoints. Repository code/agents MUST NOT lifecycle-manage `dev-core`. Existing PostgreSQL 16/Redis rollback/evidence assets remain untouched absent separate authorization.

Rollback MUST NOT use disabling RLS as a shortcut and MUST NOT broaden runtime privileges.

## 16. Required tests

### Database/security

- runtime role is non-superuser, `NOBYPASSRLS`, non-owner, no `CREATEDB`/`CREATEROLE`;
- owner and runtime roles are distinct;
- tenant tables have ENABLE + FORCE RLS;
- missing/malformed tenant GUC fails closed;
- tenant A cannot read/write/insert as tenant B;
- direct SQL under runtime role cannot bypass RLS;
- transaction-local GUC disappears after commit and rollback;
- pooled connection reuse does not leak prior tenant;
- partitioned TEST databases exercise the runtime posture.

### IAM/authorization

- active `org_owner` succeeds;
- active `org_admin` succeeds;
- missing/inactive/revoked membership denied;
- missing/inactive/revoked qualifying role denied;
- platform/support/service persona denied;
- fabricated caller role data cannot grant access;
- actor membership identity matches selected persisted membership UUID.

### Event positive

- create produces draft Event;
- initial `version = 1`, `lock_version = 1`, publication time null;
- DB timestamps populated;
- publish transitions draft→published;
- publication uses DB time;
- version/fence increment;
- exactly one canonical publication outbox row created.

### Negative/race/replay

- invalid/cross-tenant access fails closed;
- non-draft publish writes nothing;
- stale fence writes nothing;
- two concurrent publish attempts produce one winner/one outbox row;
- retry after completed publication produces no duplicate event.

### Rollback

Inject required outbox insertion failure and prove Event remains draft with unchanged publication time/version/fence and no outbox row.

### Bypass review

Tests/review MUST detect unexplained production use of direct Repo/Ecto/raw SQL, `authorize?: false`, or application-side tenant filtering as a substitute for RLS.

## 17. Documentation Impact

### CREATE

- `ticketing/docs/platform/tenancy-and-authorization.md`
- `ticketing/docs/domains/identity/README.md`
- `ticketing/docs/domains/events/README.md`
- `ticketing/docs/handoffs/T0-01.md`

### UPDATE only if needed for accurate navigation/current implementation

- `ticketing/docs/README.md`
- `ticketing/docs/platform/runtime.md`
- `ticketing/docs/platform/database.md`
- `ticketing/docs/platform/testing-and-quality-gates.md`

No future Occurrence/commerce documentation may be presented as implemented state.

## 18. Durable spec requirement

`to-spec` is REQUIRED because this increment crosses DB roles, migrations, tenancy/RLS, IAM persistence, Ash policy/actor boundaries, transaction ownership, CAS, and atomic outbox persistence.

The spec may select implementation mechanics beneath this JIP but MUST NOT create product semantics.

## 19. Risks and stop conditions

STOP and re-Grill if:

1. current Ash/AshPostgres APIs cannot guarantee tenant GUC installation on the exact backend transaction/connection before tenant SQL;
2. generated migrations cannot express the locked tenant key/FK/RLS posture safely;
3. actor derivation unexpectedly requires deferred authentication/session semantics;
4. Event publication cannot persist the required outbox atomically through governed Ash boundaries;
5. CAS correctness appears to require ordinary runtime persistence bypass;
6. authority requires dispatch completion, rather than durable enqueue, as part of publication;
7. another governing contract introduces a conflicting role/tenant/lifecycle/audit/event requirement;
8. CANON, tracer, baseline, prerequisite, or a locked decision materially changes.

TICK-21 is a separate CI/process bug and does not alter T0-01 product semantics. Its existence MUST remain visible in verification reporting.

## 20. Definition of Done

T0-01 closes only when:

- this approved JIP and derived spec remain fresh;
- Plane children are dependency-correct and complete;
- only freshness-checked/dependency-clear work entered READY;
- owner/runtime DB separation is proven;
- tenant RLS is enabled and forced;
- runtime role cannot bypass RLS;
- transaction-local tenant context is leak-free;
- persisted IAM state derives the organizer actor correctly;
- cross-tenant/unauthorized paths fail closed;
- Event create and publish actions pass;
- publication CAS race, replay/dedupe, and rollback tests pass;
- exactly one publication outbox row exists for one successful publication version;
- no Occurrence or later T0 work entered scope;
- generated-code/migration checks pass;
- `mix precommit`, `mix check`, and `mix check.types` pass;
- fresh applicable CI passes on exact final PR head;
- exact final diff receives independent review;
- no unresolved blocker/authority gap affects the increment;
- required implementation docs are updated;
- `ticketing/docs/handoffs/T0-01.md` is verified against merged implementation SHA;
- Plane records closure evidence.

## 21. Approval record

JIP-T0-01 v0.1.1 was explicitly approved by the user on 2026-10-21 after the targeted technical baseline amendment. v0.1.0 remains historical superseded planning evidence; v0.1.1 is the current approved JIP for T0-01.
