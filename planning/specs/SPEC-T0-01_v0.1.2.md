# SPEC-T0-01 v0.1.2 — Trusted Organizer Effect Boundary and Draft Event Creation

- **ID:** SPEC-T0-01
- **Version:** 0.1.2
- **Status:** APPROVED
- **Approved:** explicit user approval on 2026-10-22
- **Governing JIP:** JIP-T0-01 v0.1.3 — APPROVED
- **Supersedes for implementation planning:** SPEC-T0-01 v0.1.1
- **Repository/authority snapshot:** `f43f5bebe2a9fc13d2dd1c8c8f27a0ef7397a54a`, tree `2c4ef454de570d1c230d262cb55b0875401d6249`
- **Manifest:** `authority/contracts/manifest.json`, SHA-256 `f44764cd8310281b7f34a2cef6e50bb67ee659e147268a65e83a86586a842dd0`
- **Active tracer:** `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`

This spec derives from the approved JIP and records its implementation boundary. It cannot create or override canonical semantics. Earlier JIP/spec versions remain unchanged as historical planning evidence.

## 1. Objective and current baseline

Implement canonical organizer authorization for one `EVT-2.create_event` operation. The trusted authentication/session boundary supplies authoritative `user_id` and `session_id`. Ticketing proves organization membership, validates the persisted Session and requested role, constructs an active organization persona, authorizes IAM-1 4.1.3's `evt.event.create` capability, and inserts one tenant-owned draft Event inside one outer `Ash.transact/3` effect transaction. All stages must use the same PostgreSQL backend and transaction.

The following are already merged baseline and are not new T0-01 work: separate migration-owner/runtime DB identities, runtime grants, transaction-local `TenantContext`, the Repo transaction hook, and reusable FORCE-RLS infrastructure. This increment must use those facilities.

Locked technical baseline: Elixir 1.20.4, OTP 29.1.2, PostgreSQL 18.6, Phoenix 1.8.16, LiveView 1.2.13, Ash 3.36.1, AshPhoenix 2.3.25, AshPostgres 2.15.1, and Postgrex 0.22.4. Adopt Ash core, AshPostgres, Ash policies/attribute multitenancy, and `Ash.transact/3` for this effect. Defer AshPhoenix 2.3.25 for new work because this increment has no Phoenix/LiveView/API boundary; retain the installed package without upgrade. No dependency or runtime upgrade is authorized.

IAM-1 4.1.3 owns `evt.event.create` mapping and its allowed organization roles (`org_owner`, `org_admin`). IAM-2 1.5.0 does not authorize this capability; its invitation/customer-role-grant sovereignty boundary is outside this increment.

## 2. Owned Ash domains and interfaces

### `Ticketing.Identity`

Owns the canonical global `User` and tenant `OrgMembership`, read-only T0 `Session`, and `OrgRoleAssignment` resources. It exposes only governed interfaces needed to prove membership and read persisted authorization state. Events code uses these interfaces and does not query Identity tables directly.

### `Ticketing.Events`

Owns the canonical tenant-scoped Event and the governed `create_event` action/code interface. That action coordinates the entire effect and calls the approved Identity interface inside the same outer transaction.

No public resolver may return an organizer persona from one completed transaction for later use as `create_event` authority. A transient persona exists only within the current proof-to-insert transaction. The outer effect uses `Ash.transact/3`; deterministic test-only evidence must prove the membership probe, post-proof reads, capability authorization, and Event insert share the same PostgreSQL backend transaction. The exact evidence mechanism is implementation-free. Stop and re-Grill if installed Ash/AshPostgres cannot demonstrate this continuity.

Every canonical resource is an Ash Resource registered with its approved Ash Domain and uses `AshPostgres.DataLayer`. Ordinary runtime reads and writes go through Ash actions/interfaces with actor, tenant, and authorization context. No direct Repo/Ecto/raw-SQL domain API is allowed.

## 3. Organizer inputs and proof sequence

Trusted authentication/session infrastructure authenticates the underlying session credential and supplies authoritative `user_id` and `session_id`. It does not pass a raw credential or token hash to the T0 organizer effect.

The caller may select candidate `org_id`, requested `active_scope = org`, and requested `active_role`. These are selectors only and do not establish tenant or role authority. Reject any `active_scope` other than exactly `org`, including mixed scopes. Platform and support personas cannot satisfy the T0 tenant Event-create capability.

The required order inside one outer transaction is:

1. Start the outer `Ash.transact/3` boundary. The existing Repo transaction hook sets transaction-local `app.current_org_id` to candidate `org_id` as the transaction starts. Before successful proof, that GUC value may authorize only TEN-1's system-internal probe of the matching OrgMembership. Require authoritative `user_id`, active status, and no revocation. Retain persisted `org_membership_id`.
2. Before successful membership proof, no User, Session, role-assignment, or Event business-row read may occur. If proof fails, stop without logical promotion of candidate scope to resolved tenant authority and perform no later business-row reads.
3. Successful proof establishes candidate org equals proven org. Keep the same UUID in `app.current_org_id` for the rest of the same transaction; promote its logical authorization meaning without unsetting/resetting the GUC or performing another tenant-context transition. Require an active User. Read Session by authoritative `session_id` and require exact Session ID, user ID, and proven `org_id` matches.
4. Require Session `status = active`, `revoked_at_utc = null`, and `expires_at_utc > evaluated_at_utc`, with expiry checked against authoritative database UTC time.
5. Require an active, non-revoked same-org OrgRoleAssignment for authoritative `user_id` and requested `active_role`.
6. Construct the active organization persona only from exact persisted proof: authoritative `user_id` and `session_id`, proven `org_id`, persisted `org_membership_id`, `active_scope = org`, and the verified same-org assignment/`active_role`. Do not accept caller-supplied persona fields.
7. Authorize `evt.event.create` under IAM-1 4.1.3 for the verified human organization persona. IAM-1 permits `org_owner` and `org_admin`. Caller-supplied roles and platform/support personas never grant authority. IAM-2 is not Event-create authorization authority.
8. Insert one Event through the governed Events action and commit. Any failure rolls back the outer transaction. Deterministic test-only evidence proves all stages share the same PostgreSQL backend transaction; the exact evidence mechanism is implementation-free.

Candidate organization scope is not reusable authorization context. The complete flow must not be split across transactions.

## 4. Session posture

T0 consumes an already-issued canonical Session as read-only state. T0 never receives, returns, derives, reads, or compares a raw Session token or `token_hash`. It does not issue or create a Session; implement `sign_in_with_org`; refresh expiry; rebind user or organization; revoke Session; write `last_seen_at_utc`; or emit Session-created/revoked events. Test fixtures may prepare pre-existing Session state through a narrow test-only owner boundary; no production Session or role issuance convenience API is permitted.

Session attributes, tenant identity, and liveness follow installed IAM-1. The existing authentication/session owner remains responsible for providing the authoritative identifiers and for any Session issuance lifecycle.

## 5. Event creation boundary

The only Event transition in this increment is `absent → draft`. Use the exact EVT-2 3.0.0 resource shape and `create_event` semantics. The action generates Event UUIDv7 and `public_event_key`, sets tenant ownership to the proven organization, and writes the canonical initial status `draft`, database-owned timestamps, `version = 1`, `lock_version = 1`, and null `published_at_utc`. The caller cannot author tenant ownership, generated identity/public-key, status, timestamp, version, or fence fields, or supply the verified persona.

Preserve canonical Event identity. EVT-2 defines `public_event_key` uniqueness with `org_id` and `slug` uniqueness with `org_id`. Verify those constraints and concurrent duplicate attempts, including the contract-defined result for the losing operation; do not invent a new error mapping.

The Event insert is the final effect within the same transaction that performed the proof and authorization. Rejected authorization, invalid input, or failed insert leaves no Event row. Do not add a generic lifecycle update.

## 6. Transaction, tenancy, and database posture

- One outer `Ash.transact/3` starts before membership proof and ends after Event insert or rollback.
- At outer transaction start, the existing Repo transaction hook sets transaction-local `app.current_org_id` to candidate `org_id`. Before proof, this value may authorize only the matching TEN-1 membership probe. Successful proof establishes candidate org equals proven org; the same GUC UUID remains through post-proof work while its logical authorization meaning is promoted. Do not unset/reset the GUC or add a second tenant-context transition.
- Deterministic query-order instrumentation proves no User/Session/role/Event business-row read before successful proof. Deterministic test-only evidence proves the probe, liveness/persona work, authorization, and insert share one PostgreSQL backend transaction; the evidence mechanism is implementation-free.
- Prove the transaction-local GUC is cleaned up after commit, rollback, exception, and pooled-connection reuse.
- Runtime role remains a non-owner with `NOBYPASSRLS`. Verify direct runtime SQL cannot read/write across tenants; this is an isolation test, not a product persistence interface.
- Use only narrow test-only owner/fixture setup for pre-existing User, Membership, Session, and role state. Production exposes no convenience API to issue Session or activate/grant organizer roles.
- Use existing `Ticketing.Platform.TenantContext`, Repo transaction hook, migration-owner path, grants, and FORCE-RLS facilities. Do not add a second GUC or runtime persistence path.
- Tenant resources use Ash attribute multitenancy and PostgreSQL RLS with `ENABLE` and `FORCE`; canonical identities and tenant-aware relations follow installed contracts.
- Session/User/membership/role reads, authorization, and Event insert all use approved Ash domain/resource interfaces. Infrastructure-only database mechanics remain behind the approved boundary.
- No publication CAS, publication event, outbox, or idempotency/replay contract is introduced.
- Telemetry must not tag raw `org_id`, `user_id`, or `session_id`.
- Do not invent stronger concurrent Session/role-revocation linearization. If implementation requires it, stop and capture an `AUTHORITY_GAP` for authority resolution.

## 7. Errors and information hiding

Preserve installed TEN-1, IAM-1, EVT-2, and ERR-1 behavior. Failed membership proof follows the TEN-1 hide-existence boundary and external `ERR_NOT_FOUND`. After proof, invalid or non-live Session uses `ERR_UNAUTHENTICATED`; a missing, inactive, revoked, or incapable requested role uses `ERR_FORBIDDEN`. Invalid Event input follows canonical validation behavior. Do not invent codes, leak hidden tenant existence, or turn database errors into a new product result.

## 8. Tests and generated database evidence

Use TDD for implementation. Tests must cover:

- successful creation for an active persisted owner/admin persona;
- deterministic query-order instrumentation proves no User, Session, role-assignment, or Event business-row read before successful membership proof;
- the existing Repo hook sets transaction-local `app.current_org_id` to candidate `org_id` at transaction start; before proof its value is limited to the matching membership probe; after proof the same UUID remains while its logical authorization meaning is promoted; cleanup after commit, rollback, exception, and pool reuse;
- deterministic test-only evidence that membership probe through liveness/persona/capability to Event insert use the same PostgreSQL backend transaction, without prescribing an instrumentation technique;
- candidate org/scope/role selectors do not grant authority; invalid or mixed `active_scope` fails; platform/support personas fail the T0 capability;
- missing, inactive, revoked, or other-user membership cannot proceed;
- exact Session ID/user/org matching and active, unrevoked, unexpired Session using DB UTC; T0 never receives, returns, derives, reads, or compares raw token/token_hash;
- no Session issuance, refresh, rebind, revocation, last-seen mutation, or lifecycle event; test-only owner fixtures create pre-existing proof state without a production issuance/grant API;
- missing, mismatched, inactive, revoked, or expired Session denial;
- requested role matches an active/non-revoked same-org persisted assignment;
- fabricated caller roles do not grant the capability;
- cross-tenant rows remain hidden with a runtime role that is non-owner and `NOBYPASSRLS`; direct runtime SQL cannot cross tenants;
- exact persona binding to trusted user/session, proven organization/membership, and persisted same-org role assignment; caller and platform/support roles cannot satisfy `evt.event.create`;
- one canonical tenant-owned draft Event with action-generated UUIDv7 and `public_event_key`, draft state, null publication time, version/lock version 1, and DB timestamps;
- caller cannot set protected tenant, generated identity/public-key, status, timestamp, version, or fence fields;
- canonical Event identity plus EVT-2 `public_event_key` uniqueness with `org_id` and `slug` uniqueness with `org_id`, including concurrent duplicate-race behavior;
- failure at proof, liveness, role, authorization, validation, or insertion leaves no Event and no Session mutation;
- telemetry has no raw `org_id`, `user_id`, or `session_id` tags;
- no invented stronger concurrent Session/role-revocation linearization; if required, stop with `AUTHORITY_GAP`;
- generated AshPostgres migrations preserve canonical fields, identities, tenant relations, RLS, and grants;
- normal and partitioned PostgreSQL 18.6 TEST paths use the established owner/runtime model.

Review every direct Repo/Ecto/raw-SQL call. It must be a narrowly approved migration, DDL/RLS, or isolated test-fixture use, not a parallel domain interface.

## 9. Migration and rollback

Create only the resource schema required by this increment and use the existing migration-owner and runtime-grant flow. Inspect generated migrations before acceptance. The one effect transaction must roll back intermediate writes if any later validation, authorization, or Event insertion fails. No Session write or issuance migration is part of T0.

## 10. Documentation impact

After implementation merges, update:

- `ticketing/docs/README.md`
- `ticketing/docs/platform/runtime.md`
- `ticketing/docs/platform/database.md`
- `ticketing/docs/platform/testing-and-quality-gates.md`

Create:

- `ticketing/docs/platform/tenancy-and-authorization.md`
- `ticketing/docs/domains/identity/README.md`
- `ticketing/docs/domains/events/README.md`
- `ticketing/docs/handoffs/T0-01.md`

Describe merged code only. Keep the handoff tied to the final merged SHA and exact Plane/PR/test evidence.

## 11. Explicitly deferred work

This increment stops after draft Event creation. It does not implement:

- `create_occurrence`;
- `publish_event`;
- Event publication CAS;
- `ticketing.event.published.v1` outbox;
- occurrence sales lifecycle;
- pricing, offers, inventory, quote, order, payment, ticket, or ledger work.

This order follows the active tracer: `create_event → create_occurrence → publish_event`.

## 12. Stop conditions

Stop affected implementation if TEN-1 membership proof cannot precede all User/Session/role/Event business-row reads, if candidate scope becomes treated as resolved authority before proof, or if GUC ordering/cleanup cannot be proved. Stop if `Ash.transact/3` cannot keep every stage on the same PostgreSQL backend transaction; capture a blocker and require targeted re-Grill before considering another orchestration mechanism. Stop if Session issuance/mutation, stronger Session/role-revocation linearization, or any other authority-undefined behavior is required. Capture authority gaps in Plane and resolve them through the authority workflow; do not widen this spec to work around a gap.
