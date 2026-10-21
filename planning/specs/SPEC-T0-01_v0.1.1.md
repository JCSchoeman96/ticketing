# SPEC-T0-01 v0.1.1 — Tenant/Auth/RLS Foundation + Event Create/Publish

- **ID:** SPEC-T0-01
- **Version:** 0.1.1
- **Status:** Current reconciled spec; pending independent review of PR #21
- **Governing JIP:** `JIP-T0-01 v0.1.2` — APPROVED
- **Supersedes for implementation planning:** `SPEC-T0-01 v0.1.0`
- **Derived from repository baseline:** `b99e291ca6f388cd119c648bb89cd6e555f7033b`
- **Baseline tree:** `15da625279eb8e67e03cad39d5e51063f74ef57a`
- **Authority snapshot:** CANON-1 `2.0.16`; installed manifest `authority/contracts/manifest.json` SHA-256 `8c976c2c37964adcc0861ad1019e2cc5d88ffebf2102830b17f834e0fc7edf9a`
- **Active tracer:** `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`

This spec derives from the approved JIP above. It cannot create or override semantics in installed authority or the JIP. Where this document selects a mechanic, that choice is subordinate to the JIP decision class and must be revisited if implementation evidence shows a conflict. The v0.1.0 spec remains unchanged as historical evidence; it was derived from the drifted v0.1.1 JIP and is not the current implementation spec.

## 1. Implementation objective

Deliver one secure, testable application foundation in four layers:

1. owner/runtime PostgreSQL separation and deterministic test/CI bootstrap;
2. transaction-local tenant context + forced RLS substrate;
3. persisted IAM organizer-persona substrate and actor resolution;
4. Event create/publish with optimistic fencing and atomic durable publication outbox.

Do not implement Occurrence or later T0 behavior.

## 2. Current repository reality

At the approved baseline the application has no Ticketing domain modules. `Ticketing.Application` starts the Repo, PubSub and Phoenix endpoint; `Ticketing.Repo` is an `AshPostgres.Repo`; the only migration is the B0 AshPostgres functions/extensions migration.

Current DEV/TEST config connects the application Repo directly as the owner/bootstrap roles (`ticketing_dev` and `ticketing_test`). T0-01 must replace that normal-runtime posture while preserving the shared-local endpoint/database allocation and TEST partition construction.

The current `mix test` alias creates/migrates through the same Repo config that tests later use. T0-01.1 must split bootstrap/migration credentials from normal application runtime credentials without silently weakening test isolation.

## 3. Domain and module ownership

The following module layout is the implementation plan. Module/file naming is an implementation choice selected here for consistency and may be mechanically adjusted during implementation review only if semantics/ownership remain unchanged.

### Identity domain

Create:

- `ticketing/lib/ticketing/identity.ex` — Ash Domain `Ticketing.Identity`.
- `ticketing/lib/ticketing/identity/user.ex` — global `Ticketing.Identity.User`.
- `ticketing/lib/ticketing/identity/org_membership.ex` — tenant `Ticketing.Identity.OrgMembership`.
- `ticketing/lib/ticketing/identity/org_role_assignment.ex` — tenant `Ticketing.Identity.OrgRoleAssignment`.
- `ticketing/lib/ticketing/identity/organizer_actor.ex` — typed internal actor/persona representation if needed.
- `ticketing/lib/ticketing/identity/resolve_organizer.ex` or equivalent private policy/action support — persisted actor derivation behind the Identity domain boundary.

`Ticketing.Identity` owns persisted user/membership/role relationships and the code interface that resolves an organizer persona. Other domains do not query IAM tables directly.

The trusted upstream boundary supplies an already-authenticated human `user_id` and explicit target `org_id`. This increment does not implement authentication, provider identity mapping, or session construction.

### Events domain

Create:

- `ticketing/lib/ticketing/events.ex` — Ash Domain `Ticketing.Events`.
- `ticketing/lib/ticketing/events/event.ex` — tenant `Ticketing.Events.Event`.
- `ticketing/lib/ticketing/events/publication_outbox.ex` — tenant, Events-domain-private durable publication outbox resource.
- supporting private changes/checks under `ticketing/lib/ticketing/events/` for create/publish authorization, CAS and outbox insertion as needed.

`Ticketing.Events` owns Event lifecycle and its required publication record. The outbox is private implementation infrastructure for this domain increment; this spec does not establish a generic cross-domain event bus.

### Platform tenancy/runtime infrastructure

Create only the smallest infrastructure modules required, under:

- `ticketing/lib/ticketing/platform/tenant_context.ex` — narrow approved same-transaction GUC seam;
- optional `ticketing/lib/ticketing/platform/database_roles.ex` or Mix-task helpers only if useful for verification/bootstrap, not as a runtime domain service.

`TenantContext` is the only approved production runtime location for a low-level PostgreSQL call needed to establish `app.current_org_id`. It is infrastructure, not an alternative CRUD/query API.

The exact Ecto/Postgrex call used inside that helper is intentionally **not preselected**. T0-01.2 must first prove with a RED test that the chosen hook executes on the same database transaction/connection and is transaction-local. Current AshPostgres exposes transaction-start hooks, and Ash attribute multitenancy accepts an explicit tenant; implementation may use those capabilities if the proof holds. If no supported Ash/AshPostgres mechanism can satisfy the same-connection invariant, stop and re-Grill rather than broadening direct Repo use.

## 4. Ash domain registration

Register the new Ash Domains through the project-supported Ash configuration/generator mechanism during implementation.

Expected domains:

- `Ticketing.Identity`
- `Ticketing.Events`

Do not create a third generic service/domain merely to hold RLS or outbox logic.

Every governed PostgreSQL-backed resource uses `AshPostgres.DataLayer` and ordinary runtime access flows through domain/action/code interfaces with actor/tenant/authorization context.

## 5. Resource shape discipline

The coding ticket that introduces each resource MUST inspect the exact installed selected contract JSON from the approved CANON snapshot and model the canonical attributes, identities, required/nullability rules, lifecycle state and relationships needed by this increment.

This spec deliberately does not duplicate full contract bodies. No resource may add a convenience field/state/identity that is absent from authority just because it would simplify implementation.

### Global resources

`User` does not use Ash tenant filtering or PostgreSQL tenant RLS. `AuthIdentity` is outside this increment and has no resource, module, interface, migration, or test work here.

### Tenant resources

`OrgMembership`, `OrgRoleAssignment`, `Event`, and `PublicationOutbox` use:

```elixir
multitenancy do
  strategy :attribute
  attribute :org_id
  global? false
end
```

or the current-version equivalent produced/accepted by the installed Ash APIs.

Callers must set the Ash tenant explicitly. Attribute multitenancy is not relied upon as the only security boundary.

## 6. Database credential and bootstrap architecture

### Normal runtime

Normal DEV/TEST application Repo configuration must resolve to runtime roles, not the migration owner.

Introduce explicit runtime credential variables rather than overloading owner credentials. Preferred naming:

DEV runtime:

- `TICKETING_DEV_RUNTIME_DB_USER`
- `TICKETING_DEV_RUNTIME_DB_PASSWORD`

TEST runtime:

- `TICKETING_TEST_RUNTIME_DB_USER`
- `TICKETING_TEST_RUNTIME_DB_PASSWORD`

Keep host/port/database allocation variables aligned with the existing Ticketing allocation unless a narrower config refactor is needed.

Default usernames may be the approved role names (`ticketing_dev_runtime`, `ticketing_test_runtime`); real passwords remain required local secrets and are never committed.

Production normal runtime continues to use a runtime `DATABASE_URL` or an explicitly renamed runtime URL if ticket implementation chooses to make the distinction unambiguous.

### Migration/bootstrap credentials

Introduce separately named migration-owner credential inputs for tasks that create/migrate/grant:

- DEV migration owner = existing `ticketing_dev` allocation;
- TEST migration/bootstrap owner = existing `ticketing_test` allocation;
- CI owner = job-owned bootstrap role.

Preferred environment naming is `TICKETING_<ENV>_MIGRATION_DB_*` where separate values are needed. Exact variable decomposition is implementation-free as long as owner credentials cannot become the default application runtime path and tests cover the separation.

### Local role provisioning boundary

Ticketing MUST NOT create/drop/rotate the shared-local `ticketing_dev_runtime` or `ticketing_test_runtime` cluster roles itself unless a later explicit workstation-infrastructure change authorizes that.

These shared-local runtime roles are prerequisites provisioned by the workstation infrastructure owner. T0-01.1 must:

- document the required role names/attributes;
- detect missing/misconfigured roles with an actionable failure;
- grant per-database/schema/table/function privileges only where the existing database owner is authorized to do so;
- never escalate `ticketing_dev`/`ticketing_test` to CREATEROLE for convenience.

If the runtime roles do not exist and cannot be provisioned through the accepted workstation allocation process, capture a technical blocker.

### CI role provisioning

CI PostgreSQL is `TOOL_OWNED`; its job bootstrap may create an ephemeral runtime role and grants because the service is owned by that job. The CI application verification must then run ordinary application/database behavior as that runtime role, not only as the bootstrap superuser/owner.

### TEST partition sequence

For each partitioned TEST database:

1. owner/bootstrap credential creates the partition DB when absent;
2. owner runs migrations;
3. owner applies/grants runtime privileges required by generated/new objects;
4. application Repo/test process connects as `ticketing_test_runtime`;
5. Sandbox runs application tests as runtime;
6. privilege/RLS tests independently verify runtime posture.

Refactor the current `mix test` bootstrap/aliases or introduce a narrowly scoped Mix task so this sequence is deterministic. Do not start the normal application under owner credentials merely because Ecto's default test alias is simpler.

## 7. Role and privilege verification

T0-01.1 must add automated checks using PostgreSQL catalog/current-user queries proving normal runtime:

- `current_user` is the expected runtime role;
- `rolsuper = false`;
- `rolbypassrls = false`;
- `rolcreatedb = false`;
- `rolcreaterole = false`;
- runtime role does not own tenant tables once those tables exist;
- runtime has only needed connection/schema/object privileges.

The owner/runtime distinction is an implementation prerequisite before tenant RLS tests can be meaningful.

## 8. Tenant transaction context

### Public/internal API

`Ticketing.Platform.TenantContext` owns the narrow operation that installs the already-validated tenant UUID into PostgreSQL transaction-local state.

It MUST NOT provide arbitrary SQL execution.

Conceptual interface:

```text
put_current_org!(validated_org_uuid)
```

The implementation may accept Ash transaction metadata/context if required to guarantee correct connection selection.

### Same-connection proof

Before implementation is accepted, T0-01.2 must RED/GREEN prove:

- the GUC setter executes inside an active transaction;
- the setter and subsequent tenant SQL observe the same PostgreSQL backend transaction/connection;
- `current_setting('app.current_org_id', true)` is visible during the operation;
- the setting disappears after commit;
- the setting disappears after rollback;
- a later Sandbox/pool borrower does not inherit it.

A process-local variable is not sufficient evidence.

### Integration with Ash

Use the current installed Ash/AshPostgres transaction mechanism. AshPostgres transaction-start hooks may be used if they can receive the required tenant context and the tests prove ordering/same-connection behavior. Otherwise use the narrowest JIP-approved transaction infrastructure that remains behind governed Ash actions.

Do not set the tenant GUC outside a transaction and do not issue tenant SQL before it is set.

## 9. RLS migration pattern

For each tenant table introduced by this packet, migrations must add/verify:

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table> FORCE ROW LEVEL SECURITY;
```

and a policy semantically equivalent to:

```sql
USING (org_id = current_setting('app.current_org_id', true)::uuid)
WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
```

The implementation may choose a fail-closed helper SQL function if that reduces policy duplication **only** if it preserves missing/malformed-context denial, has no privilege escalation, is reviewed as infrastructure, and does not change canonical semantics. Otherwise use direct policy expressions.

Tenant tables must use tenant-aware composite uniqueness/FKs where required by canonical resource relationships. Generated AshPostgres migrations are reviewed and amended through new/generated migration work as needed; do not hand-edit historical applied B0 migration semantics.

## 10. Identity domain interfaces and policies

### Domain interface

Expose only the minimum code interfaces required by tests and Events, for example:

- create/read User for controlled setup/application use as canonically allowed;
- create/update/read OrgMembership through governed actions;
- create/revoke/read OrgRoleAssignment through governed actions;
- resolve organizer actor from trusted authenticated `user_id` and explicit `org_id`.

Do not expose generic unrestricted update/destroy interfaces merely because Ash generates them easily.

### Organizer resolution

The resolver:

1. receives authenticated human `user_id` and explicit `org_id` from the trusted caller boundary;
2. executes under that Ash tenant / PostgreSQL tenant context for tenant IAM rows;
3. loads the selected membership matching canonical identity;
4. requires active/non-revoked membership;
5. derives `org_membership_id` from that persisted row;
6. loads only active/non-revoked organization role assignments;
7. constructs the internal actor/persona from persisted state;
8. does not merge an externally supplied role list.

Events receives the resulting actor; Events does not query membership/role tables itself.

### Policy placement

Identity owns membership/role truth. Events policies/checks ask whether the supplied resolved actor has the canonical Event capability/qualifying role and belongs to the same tenant; they do not reproduce membership persistence queries in Event code.

If current Ash policy APIs make it safer to represent a capability check through a reusable Identity policy/check module, keep that module under `Ticketing.Identity` or a clearly named shared authorization namespace without creating new product semantics.

## 11. Event domain interface

Expose explicit actions/interfaces representing canonical intent:

- `create_event`
- `publish_event`

Do not expose a public generic update action that permits arbitrary `status`, `version`, `lock_version` or publication timestamp mutation.

Every public Event action requires:

- resolved actor;
- explicit Ash tenant;
- authorization enabled;
- request/trace context when required by the action/event envelope.

### Create implementation shape

`create_event` creates canonical Event data with:

- generated UUIDv7 identity through approved DB/Ash mechanism;
- status `draft`;
- version `1`;
- lock_version `1`;
- DB timestamps;
- null publication time;
- client input restricted to canonical create inputs.

Use database defaults/constraints where authority requires DB ownership.

### Publish implementation shape

`publish_event` is a dedicated Ash update/action with transaction enabled. It must express a compare-and-swap against the current permitted state plus expected lock fence using Ash/AshPostgres atomic/filter mechanisms where supported.

The successful mutation atomically:

- sets published state;
- sets DB publication time;
- increments version;
- increments lock_version;
- inserts exactly one durable `ticketing.event.published.v1` outbox record for the committed Event version in the same PostgreSQL transaction.

The exact Ash atomic/update API is selected during T0-01.5 using installed-version UsageRules/HexDocs. A read-then-write sequence is not acceptable as the concurrency guarantee.

## 12. Publication outbox implementation

### Ownership

`Ticketing.Events.PublicationOutbox` is private Events infrastructure. It is an Ash Resource backed by PostgreSQL so outbox persistence can remain behind the governed Ash boundary and participate in the Event transaction.

It is not registered as a generic public application API.

### Minimum shape

Model fields necessary to preserve the JIP/EVT envelope, including:

- internal outbox row identity;
- `org_id`;
- registered event type `ticketing.event.published.v1`;
- Event identity;
- Event version;
- canonical payload containing exactly `event_id` and the committed `version`;
- `request_id`/`trace_id` and required event registry/envelope metadata;
- immutable enqueue timestamp from DB;
- future-delivery bookkeeping only if required to make the row dispatchable without inventing worker semantics.

Do not add speculative broker/provider fields.

### Dedupe

Back the registered publication identity with a DB unique constraint semantically equivalent to:

```text
(org_id, event_id, version)
```

If a generic outbox table stores multiple event types, its physical unique key may include the event-type discriminator without changing this semantic identity.

### Same transaction

Persist the outbox row through an approved Ash action/change participating in the enclosing Event publication transaction. RED/GREEN tests must prove a forced outbox failure rolls back the Event mutation.

If current Ash APIs cannot guarantee this transaction boundary without a forbidden direct persistence path, stop T0-01.5 and re-Grill.

## 13. Error translation

Keep framework/database errors internal and normalize through the approved application boundary.

Required mappings:

- missing tenant: preserve `Ash.Error.Invalid.TenantRequired` internally;
- hidden cross-tenant lookup: external `ERR_NOT_FOUND`;
- missing authentication: `ERR_UNAUTHENTICATED`;
- insufficient organizer authority: `ERR_FORBIDDEN`;
- invalid Event data: `ERR_VALIDATION`;
- invalid lifecycle/stale CAS: `ERR_PRECONDITION`.

Do not create a full HTTP error renderer in T0-01 unless an existing boundary requires it. Tests may assert domain-normalized errors at the Ash/code-interface boundary.

## 14. Observability implementation

Use existing Phoenix/Ash telemetry and structured Logger metadata; do not add an observability dependency.

At governed action boundaries attach/carry applicable:

- `org_id`;
- actor user/persona identity;
- action/operation ID;
- `request_id`;
- `trace_id`.

Outbox envelope receives the required request/trace identifiers supplied to publish. Avoid duplicating canonical Event payload fields into arbitrary logs.

OBS-1-specific metric/span names must come from the installed contract when implemented; this spec does not invent replacements.

## 15. Test architecture

### Existing test posture

Retain `Ticketing.DataCase`/SQL Sandbox and the partitioned TEST isolation already present. Extend rather than bypass the existing DEV/TEST safety assertions.

### New support modules

Implementation may add focused test helpers under `ticketing/test/support/`, such as:

- owner/runtime DB bootstrap helper;
- IAM factory/setup helpers that use governed actions wherever possible;
- tenant transaction helper for assertions;
- concurrency barrier helper.

Test helpers must not become production persistence shortcuts.

### TDD requirement

Each material child ticket writes the failing proof first and observes the intended failure before production implementation.

For DB-role/RLS tickets, the RED can be a security invariant failing against the current owner-connected baseline rather than a unit-test mock.

### Required integration suites

Plan tests under focused paths such as:

- `ticketing/test/ticketing/platform/database_roles_test.exs`
- `ticketing/test/ticketing/platform/tenant_context_test.exs`
- `ticketing/test/ticketing/platform/rls_test.exs`
- `ticketing/test/ticketing/identity/...`
- `ticketing/test/ticketing/events/event_create_test.exs`
- `ticketing/test/ticketing/events/event_publish_test.exs`
- `ticketing/test/ticketing/events/event_publish_concurrency_test.exs`
- `ticketing/test/ticketing/events/event_publish_rollback_test.exs`

Exact filenames may be adjusted without changing the test ownership.

## 16. Migration/codegen strategy

For Ash resources:

1. define resource/domain/actions/policies in the responsible ticket;
2. run current Ash code generation/migration tooling;
3. inspect generated snapshots/migrations;
4. add only the required migration corrections/DDL for composite tenant invariants, RLS, grants and DB defaults that generators do not express;
5. rerun `mix ash.codegen --check`;
6. migrate a clean PostgreSQL 18.6 TEST database;
7. prove rollback/reapply where the migration is expected to be reversible.

Never hand-edit the historical B0 migration.

DDL/raw SQL is permitted for role/grant/RLS infrastructure because the JIP explicitly requires it. Keep it isolated to migration/bootstrap/test infrastructure and review every occurrence.

## 17. Ticket-by-ticket implementation plan

### T0-01.1 — Separate PostgreSQL owner and runtime identities

Primary files expected:

- `ticketing/config/dev.exs`
- `ticketing/config/test.exs`
- `ticketing/config/runtime.exs`
- `ticketing/mix.exs` and/or narrowly scoped Mix task files if needed for migration/test bootstrap
- `ticketing/test/ticketing/repo_smoke_test.exs`
- new database-role/config tests/support
- CI workflow only if required to create/use the ephemeral CI runtime role

RED first:

- normal DEV/TEST config currently resolves owner usernames, so a test expecting approved runtime usernames must fail;
- catalog/CI proof expecting runtime role attributes should fail before bootstrap exists.

GREEN:

- normal Repo uses runtime credential inputs;
- migration/test bootstrap has explicit owner credential path;
- local role existence/posture is verified, not lifecycle-created by Ticketing;
- CI creates/uses ephemeral runtime role;
- test partition sequence remains deterministic.

No domain tables/resources in this ticket.

### T0-01.2 — Transaction-local tenant context and FORCE-RLS substrate

Expected files:

- `ticketing/lib/ticketing/platform/tenant_context.ex`
- migration/helper modules for reusable RLS DDL if warranted
- platform tenant/RLS tests

RED first:

- tenant GUC absent/current owner baseline does not satisfy same-connection/transaction-local security assertions.

GREEN:

- narrow tenant-context infrastructure;
- proof of same transaction/backend connection;
- commit/rollback reset and pool-leak tests;
- reusable migration pattern for ENABLE/FORCE RLS and policy/grant posture ready for tenant resources.

No IAM/Event domain behavior yet.

### T0-01.3 — Minimum IAM organizer authorization substrate

Expected files:

- Identity domain/resources/support described above;
- generated snapshots/migrations plus reviewed tenant/RLS/composite-FK corrections;
- Identity policy/action tests.

RED first:

- organizer cannot be resolved from persisted canonical state because resources do not exist.

GREEN:

- canonical minimum IAM resources exist;
- tenant resources use Ash multitenancy + FORCE RLS;
- actor resolution derives membership/roles from DB state;
- active/revoked/forged/cross-tenant cases pass.

No Event resource yet.

### T0-01.4 — Event resource and create_event

Expected files:

- Events domain;
- Event resource;
- generated/reviewed migration and RLS;
- Event create tests.

RED first:

- governed `create_event` interface absent/fails.

GREEN:

- canonical Event shape for T0-01;
- draft initial lifecycle/version/fence;
- DB timestamps;
- organizer policy;
- same-tenant RLS;
- no public arbitrary lifecycle update.

No publish/outbox behavior yet.

### T0-01.5 — publish_event CAS and atomic publication outbox

Expected files:

- Event publish action/change/checks;
- `PublicationOutbox` resource;
- generated/reviewed migration, unique dedupe and RLS;
- publication/race/rollback tests.

RED first:

- publish action/outbox atomicity/CAS tests fail on create-only Event implementation.

GREEN:

- atomic draft→published transition;
- DB publication time;
- version + lock_version increments;
- CAS one-winner behavior;
- durable registered event row in same transaction;
- dedupe uniqueness;
- forced outbox failure rolls back Event.

No dispatcher.

### T0-01.6 — Cross-cutting security/race/replay/rollback verification

This ticket does not introduce new product semantics. It closes integration-proof gaps across the preceding implementation:

- direct runtime-role SQL isolation;
- no-GUC fail closed;
- cross-tenant Ash + RLS hiding;
- pool reuse;
- forged actor denial;
- publish concurrency;
- duplicate/replay outbox protection;
- rollback fault injection;
- clean PostgreSQL 18.6 partition migration/reapply checks.

If a required proof fails because a locked design is unimplementable, stop and capture a blocker rather than altering semantics inside this verification ticket.

### T0-01.7 — Derived implementation docs/handoff

After implementation is merged, update the JIP-authorized docs to describe the merged implementation state:

CREATE:

- `ticketing/docs/platform/tenancy-and-authorization.md`
- `ticketing/docs/domains/identity/README.md`
- `ticketing/docs/domains/events/README.md`
- `ticketing/docs/handoffs/T0-01.md`

UPDATE:

- `ticketing/docs/README.md`
- `ticketing/docs/platform/runtime.md`
- `ticketing/docs/platform/database.md`
- `ticketing/docs/platform/testing-and-quality-gates.md`

Documents describe actual implemented state, not later T0 design.

### T0-01.8 — Independent implementation/closeout review

Review:

- governing authority + approved JIP + this spec + Plane graph;
- exact implementation diff/PR(s);
- all direct Repo/Ecto/raw-SQL occurrences;
- generated migrations/snapshots;
- RLS/role evidence;
- TDD/positive/negative/race/rollback evidence;
- fresh final-head CI;
- documentation/handoff against merged SHA.

Close the JIP only when DoD is proven.

## 18. Dependency graph

Use Plane native dependencies:

```text
T0-01.1
  → T0-01.2
  → T0-01.3
  → T0-01.4
  → T0-01.5
  → T0-01.6
  → T0-01.7
  → T0-01.8
```

This intentionally serializes the foundation because each later ticket depends on the security/interface substrate produced by the preceding ticket. Do not parallelize domain work against unstable tenancy/runtime interfaces.

## 19. Context Docs per ticket

Until the new implementation docs exist, use the smallest current merged docs:

- T0-01.1: `ticketing/docs/platform/runtime.md`, `ticketing/docs/platform/database.md`, `ticketing/docs/platform/testing-and-quality-gates.md`.
- T0-01.2: `ticketing/docs/platform/database.md`, `ticketing/docs/platform/testing-and-quality-gates.md`.
- T0-01.3: T0-01.2 merged platform docs plus governing IAM/TEN contract paths.
- T0-01.4/T0-01.5: merged tenancy/identity docs from prior children plus Events governing contracts.
- T0-01.6: all affected platform/domain docs produced by preceding children.
- T0-01.7/T0-01.8: exact merged implementation and all affected docs.

Plane tickets must list their precise current paths; future docs must not be referenced as though they already exist before their creating ticket merges.

## 20. Verification gates

Every implementation child must run the narrowest relevant RED/GREEN tests plus repository-required gates before PR handoff.

Before a child is claimed complete:

- `mix precommit`;
- `mix check` when material application/database behavior is touched;
- `mix check.types` for material code changes;
- `mix ash.codegen --check` when Ash resources/migrations are affected;
- clean relevant PostgreSQL 18.6 migration/test evidence;
- `git diff --check`;
- exact-head GitHub CI;
- independent exact-diff review.

The planning PR that carries this spec contains no application code and does not itself prove implementation gates.

## 21. Staleness and stop rules

This spec becomes stale when a relevant change materially affects:

- CANON or governing IAM/TEN/EVT/ERR/OBS authority;
- active T0 tracer;
- JIP-T0-01;
- accepted framework/database baseline;
- owner/runtime role prerequisite;
- transaction-local same-connection tenant mechanism;
- resource/action ownership;
- lifecycle, RLS, CAS or outbox atomicity decisions.

Implementation-free file/helper naming changes do not by themselves stale the spec.

Any newly discovered material semantic contradiction is an authority gap. Any clear semantic requirement that the selected framework cannot safely implement is a technical blocker/prerequisite. Neither may be silently solved by implementation invention.

## 22. Planning-review acceptance

This spec is ready to become the durable implementation plan only when an independent reviewer confirms:

- it is a faithful derivative of approved JIP-T0-01 v0.1.2;
- it introduces no product semantics;
- module/resource ownership is coherent with the Ash-native application policy;
- low-level DB mechanics are confined to approved infrastructure seams;
- tickets are small enough for independent TDD/review;
- Plane dependencies match the actual produced/consumed interfaces;
- no implementation ticket is prematurely marked READY.

## 23. Reference repositories

Reference repositories provide implementation evidence only; they do not supply Ticketing semantics.

### Store_Blueprint_Hardening

Fresh `main` SHA: `da0dfa9b022f26872efe1f17277e62769c6c0808`.

| Applicable material | Classification | Boundary |
|---|---|---|
| PostgreSQL transaction patterns | `REFERENCE_ONLY` | Review evidence for transaction boundaries; use the approved Ash/AshPostgres transaction selected by this JIP. |
| Durable outbox patterns | `REFERENCE_ONLY` | Review evidence only; Ticketing uses the Event publication identity, payload, and atomicity required by installed authority and the JIP. |
| Idempotency patterns | `REFERENCE_ONLY` | Checkout/payment/webhook semantics do not define Event publication replay behavior. |
| Runtime-resource-safety review evidence | `REFERENCE_ONLY` | Review evidence only; it does not change Ticketing credential, infrastructure ownership, or cleanup rules. |

No code or product semantics are imported from this repository.

### LiveFrames

Fresh `main` SHA: `bd8bc4daae8b0b3b0ad79c1711a798b5028b7784`. Classification: `NOT_APPLICABLE`, because T0-01 contains no UI work.

## 24. Planning history and execution

This v0.1.1 spec is the current reconciled derivative of approved JIP-T0-01 v0.1.2. The execution plan and Plane children must point to these versions. TICK-31 records the earlier planning drift and remains open until its own closeout requirements are met.

The native Plane dependency chain remains:

`TICK-23 → TICK-24 → TICK-25 → TICK-26 → TICK-27 → TICK-28 → TICK-29 → TICK-30`.

This spec does not set any implementation child READY. Recheck authority freshness, native dependencies, and ticket scope before each implementation handoff.
