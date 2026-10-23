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

Implement canonical organizer authorization for one `EVT-2.create_event` operation. The trusted authentication/session boundary supplies authoritative `user_id` and `session_id`. Ticketing proves organization membership, validates the persisted Session and requested role, constructs an active organization persona, authorizes `evt.event.create`, and inserts one tenant-owned draft Event in one outer Ash/PostgreSQL effect transaction.

The following are already merged baseline and are not new T0-01 work: separate migration-owner/runtime DB identities, runtime grants, transaction-local `TenantContext`, the Repo transaction hook, and reusable FORCE-RLS infrastructure. This increment must use those facilities.

Locked technical baseline: Elixir 1.20.4, OTP 29.1.2, PostgreSQL 18.6, Phoenix 1.8.16, LiveView 1.2.13, Ash 3.36.1, AshPhoenix 2.3.25, AshPostgres 2.15.1, and Postgrex 0.22.4. No upgrades are authorized.

## 2. Owned Ash domains and interfaces

### `Ticketing.Identity`

Owns the canonical global `User` and tenant `OrgMembership`, read-only T0 `Session`, and `OrgRoleAssignment` resources. It exposes only governed interfaces needed to prove membership and read persisted authorization state. Events code uses these interfaces and does not query Identity tables directly.

### `Ticketing.Events`

Owns the canonical tenant-scoped Event and the governed `create_event` action/code interface. That action coordinates the entire effect and calls the approved Identity interface inside the same outer transaction.

No public resolver may return an organizer persona from one completed transaction for later use as `create_event` authority. A transient persona exists only within the current proof-to-insert transaction.

Every canonical resource is an Ash Resource registered with its approved Ash Domain and uses `AshPostgres.DataLayer`. Ordinary runtime reads and writes go through Ash actions/interfaces with actor, tenant, and authorization context. No direct Repo/Ecto/raw-SQL domain API is allowed.

## 3. Organizer inputs and proof sequence

Trusted authentication/session infrastructure authenticates the underlying session credential and supplies authoritative `user_id` and `session_id`. It does not pass a raw credential or token hash to the T0 organizer effect.

The caller may select candidate `org_id`, requested `active_scope = org`, and requested `active_role`. These are selectors only and do not establish tenant or role authority.

The required order inside one outer transaction is:

1. Run TEN-1 `org_membership_probe` using its system-internal candidate-organization scope. It reads only the matching OrgMembership. Require that it belongs to authoritative `user_id`, is active, and is not revoked. Retain its persisted `org_membership_id`.
2. If membership proof fails, stop without promoting candidate scope to resolved tenant authority. Do not read resolved-tenant Session, role, or Event state.
3. After proof, establish the proven organization as the tenant for remaining reads. Require an active User. Read Session by authoritative `session_id` and require exact Session ID, user ID, and proven `org_id` matches.
4. Require Session `status = active`, `revoked_at_utc = null`, and `expires_at_utc > evaluated_at_utc`, with expiry checked against authoritative database UTC time.
5. Require an active, non-revoked same-org OrgRoleAssignment for authoritative `user_id` and the requested `active_role`.
6. Construct the explicit active organization persona only from the persisted proof: authoritative `user_id`, validated `session_id`, proven `org_id`, persisted `org_membership_id`, `active_scope = org`, and verified `active_role`.
7. Authorize `evt.event.create` under IAM-1/IAM-2 for the verified persona. IAM-1 permits human `org_owner` and `org_admin` roles for this capability. Caller-supplied roles never grant authority.
8. Insert one Event through the governed Events action and commit. Any failure rolls back the outer transaction.

Candidate organization scope is not reusable authorization context. The complete flow must not be split across transactions.

## 4. Session posture

T0 consumes an already-issued canonical Session as read-only state. It does not issue or create a Session; implement `sign_in_with_org`; accept raw Session credentials; derive or compare token hashes; refresh expiry; rebind user or organization; revoke Session; write `last_seen_at_utc`; or emit Session-created/revoked events.

Session attributes, tenant identity, and liveness follow installed IAM-1. The existing authentication/session owner remains responsible for providing the authoritative identifiers and for any Session issuance lifecycle.

## 5. Event creation boundary

The only Event transition in this increment is `absent → draft`. Use the exact EVT-2 3.0.0 resource shape and `create_event` semantics. Set tenant ownership to the proven organization. Preserve canonical initial status, DB-owned timestamps, initial version/fence values, and null `published_at_utc`. Do not let a caller supply the verified persona or author the concurrency fence.

The Event insert is the final effect within the same transaction that performed the proof and authorization. Rejected authorization, invalid input, or failed insert leaves no Event row. Do not add a generic lifecycle update.

## 6. Transaction, tenancy, and database posture

- The one outer Ash/PostgreSQL transaction starts before membership proof and ends after the Event insert or rollback.
- TEN-1's candidate-org probe is system-internal and limited to matching OrgMembership proof. Candidate `org_id` is not resolved tenant authority.
- Only after proof may the operation read resolved-tenant Session, role, or Event state.
- Use existing `Ticketing.Platform.TenantContext`, Repo transaction hook, migration-owner path, grants, and FORCE-RLS facilities. Do not add a second GUC or runtime persistence path.
- Tenant resources use Ash attribute multitenancy and PostgreSQL RLS with `ENABLE` and `FORCE`; canonical identities and tenant-aware relations follow installed contracts.
- Session reads, User reads, membership proof, role reads, authorization, and Event insert all use approved Ash domain/resource interfaces. Infrastructure-only database mechanics remain behind the approved boundary.
- No publication CAS, publication event, outbox, or idempotency/replay contract is introduced.

## 7. Errors and information hiding

Preserve installed TEN-1, IAM-1, EVT-2, and ERR-1 behavior. Failed membership proof follows the TEN-1 hide-existence boundary and external `ERR_NOT_FOUND`. After proof, invalid or non-live Session uses `ERR_UNAUTHENTICATED`; a missing, inactive, revoked, or incapable requested role uses `ERR_FORBIDDEN`. Invalid Event input follows canonical validation behavior. Do not invent codes, leak hidden tenant existence, or turn database errors into a new product result.

## 8. Tests and generated database evidence

Use TDD for implementation. Tests must cover:

- successful creation for an active persisted owner/admin persona;
- membership proof before resolved-tenant Session/role/Event reads;
- candidate org/scope/role selectors do not grant authority;
- missing, inactive, revoked, or other-user membership cannot proceed;
- exact Session ID/user/org matching and active, unrevoked, unexpired Session using DB UTC;
- missing, mismatched, inactive, revoked, or expired Session denial;
- requested role matches an active/non-revoked same-org persisted assignment;
- fabricated caller roles do not grant the capability;
- cross-tenant rows remain hidden with the runtime role and FORCE RLS;
- one canonical tenant-owned draft Event is written only after authorization;
- failure at proof, liveness, role, authorization, validation, or insertion leaves no Event and no Session mutation;
- transaction-local tenant context clears on commit/rollback and pool reuse;
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

Stop affected implementation if TEN-1 membership proof cannot precede resolved-tenant reads, if candidate scope becomes treated as resolved authority before proof, if Session issuance/mutation is required, if the full effect cannot remain one governed Ash/PostgreSQL transaction, or if installed authority does not settle a required shape, authorization rule, or error. Capture the blocker in Plane and return through the authority/JIP process. Do not widen this spec to work around a gap.
