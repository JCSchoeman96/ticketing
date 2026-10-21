# JIP-T0-01 v0.1.1 — Tenant/Auth/RLS Foundation + Event Create/Publish

- **ID:** JIP-T0-01
- **Version:** 0.1.1
- **Status:** APPROVED
- **Approved:** explicit user acceptance on 2026-10-21
- **Supersedes for implementation planning:** JIP-T0-01 v0.1.0
- **Nature of change from v0.1.0:** technical-baseline amendment only; product/domain semantics unchanged
- **Roadmap horizon:** T0 — Tenant-scoped GA pending sale
- **Increment boundary:** tenant/auth/RLS foundation through Event create/publish; stops before Occurrence

This JIP is downstream implementation planning. Installed canonical contracts, ROADMAP and the active tracer remain higher authority.

## 1. Amendment history

### v0.1.0

JIP-T0-01 v0.1.0 was explicitly user-approved after the T0-01 JIT Grill. It established the semantic and implementation decisions for the minimum persisted IAM authorization substrate, explicit tenant context, PostgreSQL FORCE-RLS enforcement, separate migration-owner/runtime identities, Ash attribute multitenancy, Event create/publish, optimistic/CAS fencing, and atomic durable publication outbox.

### v0.1.1

v0.1.0 became technically stale before implementation because Phoenix 1.8.16 and Phoenix LiveView 1.2.13 became the accepted current patch baseline. TICK-20 isolated and merged that prerequisite. v0.1.1 re-anchors the unchanged T0-01 design to the resulting repository baseline.

Changes from v0.1.0:

- repository baseline `0de712893f5b28a70b3a2fadd9d62d575868f940` → `b99e291ca6f388cd119c648bb89cd6e555f7033b`;
- repository tree → `15da625279eb8e67e03cad39d5e51063f74ef57a`;
- Phoenix `1.8.15` → `1.8.16`;
- Phoenix LiveView `1.2.12` → `1.2.13`;
- records TICK-21, the non-product CI push-trigger anomaly discovered after PR #20.

No lifecycle, tenancy, authorization, persistence, concurrency, error, outbox, observability, ownership or increment-scope decision changed.

## 2. Objective

Establish the smallest secure implementation substrate required for the first T0 tracer increment by delivering:

1. the minimum persisted IAM authorization/persona state needed for authenticated organizer actions;
2. explicit tenant context through Ash and PostgreSQL;
3. forced database-level tenant isolation;
4. governed Event creation;
5. governed Event publication;
6. atomic persistence of the registered `ticketing.event.published.v1` event.

This increment proves the foundation on which the rest of the tenant-scoped GA tracer can safely be built. It stops before Occurrence.

## 3. Verified baseline

### Repository

- Repository: `JCSchoeman96/ticketing`
- Approved implementation baseline: `b99e291ca6f388cd119c648bb89cd6e555f7033b`
- Baseline tree: `15da625279eb8e67e03cad39d5e51063f74ef57a`
- Phoenix application: `ticketing/`

PR #20 changed only `ticketing/mix.lock`, resolving Phoenix 1.8.16 and LiveView 1.2.13. No T0-01 product/domain implementation was included.

PR #20's CI-tested synthetic merge `7e21825d39fb241e5fcff3f0cd2ac4ee49671849` and the actual main merge `b99e291ca6f388cd119c648bb89cd6e555f7033b` have the same Git tree `15da625279eb8e67e03cad39d5e51063f74ef57a`. Full PR CI passed on that exact tree. No separate `push` workflow run materialized for the actual merge SHA despite `ci.yml` declaring push-on-main; that process defect is TICK-21. Do not describe PR #20 as having exact-main push CI.

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

Active planning evidence:

- `authority/planning/ROADMAP.md`: B0 COMPLETE, T0 NEXT.
- `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`: active T0 tracer, CANON-1 2.0.16 snapshot.

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

### Reference repositories

- Store_Blueprint_Hardening current accepted `main`: `02cade1bbad64a1c49fc859bfd605c604eba37fa` — **REFERENCE_ONLY** for durable outbox/transaction/idempotency implementation evidence; Ticketing authority controls semantics.
- LiveFrames current accepted `main`: `bd8bc4daae8b0b3b0ad79c1711a798b5028b7784` — **NOT_APPLICABLE** because T0-01 contains no material UI work.

## 4. Scope

### In scope

- migration-owner/runtime database-role separation;
- transaction-local `app.current_org_id`;
- Ash attribute multitenancy on `org_id`;
- PostgreSQL `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`;
- minimum persisted IAM authorization substrate:
  - global `User`;
  - global `AuthIdentity` only to the extent required as persisted identity substrate;
  - tenant `OrgMembership`;
  - tenant `OrgRoleAssignment`;
- organizer actor construction from persisted IAM state;
- tenant-scoped Event resource;
- `EVT-2.create_event`;
- `EVT-2.publish_event`;
- Event state/version/lock-version CAS;
- atomic durable `ticketing.event.published.v1` outbox persistence;
- required security, cross-tenant, race, replay and rollback tests;
- required derived implementation documentation after implementation merges.

### Explicit non-goals

- authentication-provider integration;
- password, magic-link, OAuth or service-token login flows;
- AshAuthentication;
- persisted application Session/login UI;
- Occurrence and occurrence sale windows;
- Event archive implementation;
- pricing, offers/products, tax;
- inventory, holds, quotes, checkout, Orders;
- payment, ticket, ledger, admission;
- background outbox dispatch, Oban/AshOban;
- PubSub as a substitute for the durable event;
- UI/LiveView features;
- dependency upgrades;
- later T0/T1 work.

## 5. Why this is the next coherent tracer increment

Event create/publish is the first complete T0 lifecycle that exercises authenticated organizer authority, explicit tenant context, tenant persistence, cross-tenant hiding, PostgreSQL RLS, database time, optimistic concurrency, a registered event and atomic outbox persistence.

Pulling Occurrence into this packet would introduce a second lifecycle, sale-window temporal guards and another event before the tenancy/security substrate is independently proven. Occurrence remains a later JIP boundary.

## 6. Ash capability decisions

### ADOPT

- Ash core;
- AshPostgres;
- AshPhoenix where needed by the application boundary;
- Ash authorization policies;
- Ash attribute multitenancy on `org_id` for tenant-owned resources;
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

### REJECT for this increment

- AshArchival as Event lifecycle implementation;
- direct Repo/Ecto CRUD as the runtime domain API;
- `authorize?: false` on ordinary organizer paths;
- application-side tenant filtering as an RLS substitute;
- session-scoped tenant GUCs;
- process-dictionary tenant truth;
- hidden dependency upgrades.

If canonical runtime behavior appears to require a direct persistence bypass, stop affected work, capture the blocker, run targeted JIT review and amend/reapprove the JIP/spec if an exception is genuinely required.

## 7. Decision classification

### CONTRACT_LOCKED

Canonical authority controls:

- explicit `org_id` tenancy;
- tenant information hiding;
- membership/role authorization semantics;
- Event identity, shape and lifecycle;
- required database time where prescribed;
- Event version/lock fencing;
- registered `ticketing.event.published.v1` event semantics;
- canonical errors;
- transactionally coupled mutation/event persistence;
- actor/tenant boundaries and cross-tenant denial behavior.

### IMPLEMENTATION_LOCKED

This JIP selects:

- separate migration/owner and runtime DB identities;
- non-owner, non-superuser, `NOBYPASSRLS` application runtime roles;
- `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`;
- transaction-local `app.current_org_id`;
- Ash attribute multitenancy on `org_id`;
- explicit actor plus explicit Ash tenant;
- same backend transaction/connection for tenant GUC and governed tenant work;
- Event `version` and `lock_version` optimistic fencing;
- PostgreSQL durable publication outbox;
- database uniqueness for publication dedupe keyed by the semantic equivalent of event type + `org_id` + `event_id` + Event `version`.

### IMPLEMENTATION_FREE

Provided governed semantics do not change:

- exact Elixir file/module layout under `Ticketing`;
- helper names;
- internal policy/check decomposition;
- migration/index/policy object names;
- test factory/helper design;
- exact narrow infrastructure helper used to establish the same-connection tenant GUC;
- internal outbox resource/table name;
- internal noncanonical log event names.

### AUTHORITY_GAP

None identified at approval time.

## 8. Database owner/runtime separation

Existing shared-local allocated roles remain owner/bootstrap/migration identities:

- DEV: `ticketing_dev`;
- TEST: `ticketing_test`.

The TEST owner may retain `CREATEDB` only for deterministic `MIX_TEST_PARTITION` database provisioning.

Introduce normal application runtime roles:

- DEV: `ticketing_dev_runtime`;
- TEST: `ticketing_test_runtime`;
- CI: ephemeral equivalent.

Runtime roles MUST:

- not be superusers;
- be `NOBYPASSRLS`;
- not own tenant tables;
- not have `CREATEDB` or `CREATEROLE`;
- receive only runtime schema/table/sequence/function privileges required by approved actions.

Normal application processes use runtime credentials. Schema migration/bootstrap uses owner credentials.

Because workstation `dev-core` is external/shared infrastructure, repository work must not lifecycle-manage it or assume the owner role can create arbitrary roles. Provisioning mechanics must respect the established environment ownership boundary; missing role provisioning capability is a technical blocker, not permission to broaden `ticketing_dev`/`ticketing_test` or run the application as owner.

Production configuration likewise separates runtime credentials from migration-owner credentials.

## 9. Tenant and RLS model

For every tenant-owned table introduced here:

1. `org_id` is required/non-null.
2. Tenant identities/indexes place `org_id` first where canonical authority requires tenant-first identity.
3. Tenant relationships/FKs preserve `org_id`.
4. RLS is enabled.
5. RLS is forced.
6. Read policy compares row `org_id` with transaction-local `app.current_org_id`.
7. Write policy applies the same condition through `WITH CHECK`.
8. Missing or malformed tenant context fails closed.
9. Cross-tenant resources are hidden as not found at the public boundary.
10. Runtime roles cannot bypass RLS.

Policy behavior is semantically equivalent to:

```sql
org_id = current_setting('app.current_org_id', true)::uuid
```

for visibility and write checking.

The application validates tenant UUID format before setting the GUC.

The GUC MUST be transaction-local (`SET LOCAL` or equivalent `set_config(..., true)` semantics), established on the same backend connection before tenant-scoped SQL, and gone after commit/rollback. Session-level GUC mutation and ambient process-global tenant truth are forbidden.

Ash multitenancy and PostgreSQL RLS are independent guards; neither replaces the other.

## 10. IAM substrate and actor derivation

### User

Global, non-PII principal boundary according to IAM-1. No direct email/phone ownership is invented.

### AuthIdentity

Global persisted identity substrate only to the extent required by current canonical IAM shape. Real provider authentication, login and session construction remain out of scope.

### OrgMembership

Tenant scoped. It preserves:

- UUIDv7 `org_membership_id`;
- tenant identity involving `org_id` and `org_membership_id`;
- existing canonical `(org_id, user_id)` uniqueness/identity semantics;
- active/revoked membership behavior.

`auth_context.actor.org_membership_id` identifies the selected active membership row/persona. It does not replace `org_id` as tenant/RLS context.

### OrgRoleAssignment

Tenant scoped. Preserve canonical tenant/user/role assignment identity and revocation semantics.

### Actor derivation

A caller may not assert an authoritative roles array.

Organizer actor context is reconstructed from persisted canonical IAM state using explicit `user_id` and `org_id`, yielding the selected active membership identity and current active organization roles.

Event create/publish requires:

- human actor kind;
- active organization persona;
- qualifying active role `org_owner` or `org_admin` according to IAM authority.

Platform/support personas do not satisfy this path.

Authentication-provider/session mechanics are deferred; this packet establishes the persisted authorization substrate and actor-resolution boundary only.

## 11. Event resource and lifecycle

### Create Event

Transition:

`absent → draft`

Requirements:

- explicit tenant;
- authorized human organizer;
- valid canonical Event input;
- database-created timestamps;
- `published_at_utc = null`;
- canonical initial `version = 1`;
- canonical initial `lock_version = 1`;
- lock/version fence not client-authored.

A rejected create leaves no Event row.

### Publish Event

Transition:

`draft → published`

Guards:

- same tenant;
- authorized human organizer;
- current state is `draft`;
- expected/current lock fence matches.

Atomic effects:

1. status becomes `published`;
2. `published_at_utc` uses database time;
3. Event `version` increments;
4. Event `lock_version` increments;
5. `ticketing.event.published.v1` outbox row is inserted in the same transaction.

Invalid/stale transition returns the governing precondition error and writes neither Event transition nor outbox row.

Event archive and Occurrence behavior are outside this packet.

## 12. Publication outbox

Persist one durable PostgreSQL-backed publication record sufficient to represent the canonical EVT-1 envelope and the `ticketing.event.published.v1` event.

Canonical domain payload:

```text
{
  event_id,
  version
}
```

Required context/envelope outside the domain payload includes `org_id`, `request_id`, `trace_id` and other registry/event metadata required by current EVT authority. Do not add product semantics to the payload.

The publication event is outbox-driven and committed atomically with the Event mutation.

Database dedupe identity is the semantic equivalent of:

`(event_type, org_id, event_id, version)`

If the implementation uses a table/resource dedicated solely to this event type, the fixed event-type component may be implicit; the database must still make duplicate persistence of the same publication version impossible.

Canonical event identity/payload/envelope content is immutable after enqueue except future delivery bookkeeping that does not change event semantics.

Background dispatch, workers, retries, broker delivery and PubSub are deferred.

## 13. Transactions, races and replay

### Create

Use the governed Ash create action and database constraints as authoritative protection for canonical persistence invariants. Do not implement correctness as check-then-insert.

### Publish

One database transaction contains:

- lifecycle/current-state compare;
- optimistic lock/version compare;
- Event status/time/version/fence mutation;
- durable publication outbox insertion.

No split-phase publication is allowed.

### Concurrent publish

Two attempts racing from the same draft state/fence:

- exactly one may win;
- loser writes nothing;
- only one publication outbox record exists for the successful Event version.

### Replay/duplicate attempt

A completed Event publication cannot create a second publication row for the same Event version. State/fence guards fail closed and the outbox unique constraint independently protects durable dedupe.

This does not create a generic Event HTTP idempotency scheme; later checkout LOCKS/API semantics are not pulled forward.

### Rollback

Required outbox insertion failure rolls back the Event publication mutation. Event mutation failure leaves no orphan publication row.

## 14. Persistence invariants

### Global IAM

Global User/AuthIdentity state is not tenant-RLS scoped. Preserve IAM-1's non-PII boundary for User.

### Tenant IAM

At minimum:

- OrgMembership preserves `(org_id, org_membership_id)` identity and `(org_id, user_id)` canonical uniqueness/identity;
- OrgRoleAssignment preserves canonical tenant/user/role assignment identity;
- tenant relationships carry `org_id` as required.

### Event

Tenant scoped. Canonical timestamp/state/version rules are database-backed where prescribed. `lock_version` is not client-authored.

### Outbox

Tenant scoped. Required database uniqueness prevents duplicate durable publication for the same semantic Event publication identity/version.

## 15. Errors and fail-closed behavior

Preserve canonical errors rather than exposing framework/PostgreSQL exceptions as product semantics.

Required boundary behavior includes:

- missing Ash tenant → `Ash.Error.Invalid.TenantRequired` internally;
- cross-tenant resource → hidden `ERR_NOT_FOUND` externally;
- unauthenticated organizer → `ERR_UNAUTHENTICATED`;
- authenticated actor lacking organizer authority → `ERR_FORBIDDEN`;
- invalid Event input → `ERR_VALIDATION`;
- invalid/stale publish transition → `ERR_PRECONDITION`;
- outbox persistence failure → transaction failure with no publication;
- CAS loser → no Event/outbox write.

Inactive/revoked membership or role fails authorization according to the governing IAM/ERR boundary. Do not reveal hidden cross-tenant existence through a differentiated denial.

## 16. Observability and audit

Carry and correlate where applicable:

- `org_id`;
- actor/persona identity;
- `request_id`;
- `trace_id`;
- operation/action identity, including `EVT-2.create_event` and `EVT-2.publish_event`.

Follow OBS-1 for logs/spans/metrics/alerts applicable to the increment. Do not invent new canonical telemetry vocabulary.

Do not log credentials, authentication secrets, unnecessary PII or hidden cross-tenant identifiers to callers.

Implement only audit persistence actually required by current Event/IAM authority; do not invent a generic audit stream.

## 17. Migration, rollout and rollback

### Migration order

1. establish/verify owner-vs-runtime credential and privilege model;
2. add minimum IAM schema;
3. add Event schema;
4. add publication-outbox schema;
5. add tenant composite keys/FKs/indexes;
6. create RLS policies;
7. enable RLS;
8. force RLS;
9. grant runtime role minimum required privileges;
10. configure normal application Repo/runtime credentials;
11. prove privilege/RLS posture before relying on domain tests.

Generated AshPostgres migrations must be inspected. Generated output is not presumed to satisfy tenant-first identities, composite FKs, RLS, immutability or concurrency requirements.

### Local DEV/TEST

Use existing shared-local PostgreSQL endpoints:

- DEV `127.0.0.1:55432`;
- TEST `127.0.0.1:55433`.

DEV and TEST remain separate physical clusters. Repository agents do not lifecycle-manage workstation `dev-core`.

TEST partition databases are provisioned through the owner/bootstrap identity, but actual application behavior must be exercised under the runtime role once the partition exists.

### CI

CI remains tool-owned PostgreSQL 18.6. It must exercise owner/runtime separation sufficiently to prove the runtime RLS assumptions rather than executing all application behavior as a privileged table owner.

### Production

Production configuration must distinguish application/runtime database credentials from migration/owner credentials. Exact secret management/provider is outside this JIP.

### Rollback

Rollback must respect migration ordering/dependencies and may remove only objects introduced by this increment where safe. Never disable RLS as a rollback shortcut or broaden runtime privileges to make rollback easier.

Do not alter/delete legacy PostgreSQL 16/Redis evidence assets without separate authorization.

## 18. Required tests

### Database/security

- runtime role is not superuser;
- runtime role is `NOBYPASSRLS`;
- runtime role does not own tenant tables;
- runtime role lacks `CREATEDB`/`CREATEROLE`;
- tenant tables have RLS enabled and forced;
- no tenant GUC → tenant reads/writes fail closed;
- tenant A cannot read/update/delete tenant B;
- tenant A cannot insert a row claiming tenant B;
- tenant-local GUC is gone after commit;
- tenant-local GUC is gone after rollback;
- pooled connection reuse cannot leak the previous tenant;
- partitioned TEST databases prove the same posture.

### IAM/authorization

- active membership + active `org_owner` can create/publish;
- active membership + active `org_admin` can create/publish;
- no membership denied;
- inactive/revoked membership denied;
- missing/revoked qualifying role denied;
- platform/support persona denied;
- fabricated caller-supplied role cannot grant access;
- actor membership ID is the selected persisted membership UUID.

### Event positive

- create produces draft Event;
- database timestamps populated;
- initial version = 1;
- initial lock version = 1;
- publication time initially null;
- publish transitions draft → published;
- publication time comes from database;
- version and lock version increment;
- exactly one canonical outbox record is created.

### Event negative/race/replay

- invalid/missing tenant fails closed;
- cross-tenant Event is hidden;
- publish non-draft Event fails without write;
- stale lock fence fails without write;
- two concurrent publishes yield one winner/one loser and one outbox row;
- completed duplicate attempt produces no additional publication row.

### Rollback

Inject required outbox insertion failure and prove:

- Event remains draft;
- publication time remains null;
- version/fence unchanged;
- no outbox row survives.

### Database time/context

- publication timestamp is DB-owned, not caller trusted;
- `org_id`, actor/persona, request/trace and operation context reaches required governed/outbox/observability boundaries without secret leakage.

### Bypass review

Tests/review must expose unexplained runtime use of direct `Ticketing.Repo`, Ecto query/update APIs, raw SQL or `authorize?: false` for canonical domain behavior. Narrow migration/RLS/test infrastructure SQL is permitted only inside the approved infrastructure exception.

## 19. Documentation impact

### CREATE after implementation

- `ticketing/docs/platform/tenancy-and-authorization.md`
- `ticketing/docs/domains/identity/README.md`
- `ticketing/docs/domains/events/README.md`
- `ticketing/docs/handoffs/T0-01.md`

### UPDATE only if navigation requires it

- `ticketing/docs/README.md`

Documentation describes merged implementation state only, identifies its derived nature and governing JIP, and does not present later T0 work as implemented.

## 20. Durable-spec decision

`to-spec`: **REQUIRED**.

T0-01 crosses database identities, migrations, tenant propagation, RLS, IAM persistence, Ash policies, Event lifecycle, optimistic concurrency and atomic outbox persistence. The derived spec may select implementation mechanics but cannot create semantics.

## 21. Risks and stop conditions

Stop and re-Grill if:

1. Ash transaction mechanics cannot guarantee tenant GUC installation on the exact backend transaction used by tenant SQL;
2. generated AshPostgres migrations cannot safely express canonical tenant key/FK/RLS posture without an unapproved runtime bypass;
3. IAM actor derivation requires authentication/session semantics absent from current authority;
4. Event publication cannot persist the required outbox row in the same transaction behind governed Ash boundaries;
5. CAS implementation would require weakening the approved fence;
6. current authority requires background delivery as part of publication completion rather than durable enqueue;
7. another governing contract introduces conflicting role/tenancy/audit/event requirements;
8. CANON/tracer/baseline/prerequisite materially changes;
9. implementation requires a dependency upgrade not approved here.

### TICK-21

TICK-21 tracks the missing `push → main` CI run observed after PR #20. It is an independent infrastructure/process defect, not a product/domain semantic blocker. Do not rewrite tree-equivalent PR CI as exact-main push CI evidence.

## 22. Definition of Done

T0-01 is complete only when:

- this approved JIP and derived spec remain fresh;
- Plane children are dependency-correct;
- only fresh dependency-clear work entered READY;
- material behavior was implemented with TDD;
- owner/runtime DB separation is proven;
- tenant RLS is enabled and forced;
- runtime role cannot bypass RLS;
- transaction-local tenant context is proven leak-free;
- persisted IAM state derives organizer authority;
- unauthorized/cross-tenant paths fail closed;
- Event create and publish actions pass;
- CAS race/replay/rollback tests pass;
- exactly one publication outbox row is created per successful Event publication version;
- no Occurrence/later-T0 work entered scope;
- Ash codegen/generated migration review passes;
- `mix precommit`, `mix check`, `mix check.types` pass;
- applicable fresh PR-head CI passes;
- exact final diff receives independent review;
- merge result is verified against reviewed content;
- required implementation docs/handoff are updated and verified against merged main;
- no unresolved blocker/authority gap affects the increment;
- Plane closure records evidence.

## 23. Approval record

**APPROVED.**

The user explicitly approved `JIP-T0-01 v0.1.1` on 2026-10-21 after the baseline amendment was presented. Approval authorizes the next planning steps (`to-spec`, then `to-tickets`) but does not itself authorize implementation without a dependency-clear, freshness-checked Plane item marked `READY`.
