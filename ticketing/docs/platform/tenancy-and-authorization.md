# Tenancy and authorization

> Nature and status: Derived implementation documentation. This document describes merged platform behavior and does not define product semantics.
>
> Last verified main SHA: `25a6a0956d7bb81214e348c7511132f5297d0fc5`
>
> Governing JIP: JIP-T0-01 v0.1.6. Relevant merged Plane work: TICK-25 and TICK-26 plus the previously merged tenant/database substrate they reuse.
>
> Relevant merged implementation PRs: [#40 (TICK-25)](https://github.com/JCSchoeman96/ticketing/pull/40), [#45 (TICK-26)](https://github.com/JCSchoeman96/ticketing/pull/45), and [#55 (TICK-28 verification)](https://github.com/JCSchoeman96/ticketing/pull/55).

## Database-role boundary

Ticketing separates schema ownership/migration authority from the constrained application runtime role. `Ticketing.Platform.DatabasePrivileges` applies the runtime privileges after migrations rather than giving the runtime role ownership of the schema.

The runtime grant set covers the database/schema access and application-table DML needed by the application. It excludes `schema_migrations` from the ordinary application table grant set. Verification also proves that the constrained role cannot perform schema-changing operations that belong to the owner/migration boundary.

This role split is infrastructure enforcement. It does not itself grant product/domain authority to a user or tenant.

## Transaction-local tenant context

Tenant data access is bound to the PostgreSQL setting:

`app.current_org_id`

`Ticketing.Platform.TenantContext.put_current_org!/1` validates the tenant UUID, requires an active Repo transaction, and installs the value using transaction-local PostgreSQL `set_config(..., true)` semantics.

`Ticketing.Repo.on_transaction_begin/1` connects Ash tenant transactions to that database tenant context. The setting is therefore scoped to the active transaction instead of being a durable connection-level tenant identity.

A caller-provided organization UUID is not, by itself, authorization. The tenant context controls database visibility; higher-level organizer authority comes from the persisted evidence and IAM checks performed by the governed action.

TICK-26 uses one outer `Ash.transact/3` tenant transaction for draft Event creation. The candidate organization is present as the transaction-local tenant so the matching Membership proof can execute. Before successful Membership proof, that UUID is only a selector for the Membership probe. The same UUID remains in place after proof and through the Event insert; the implementation does not clear, switch, or reinstall tenant context mid-flow.

## Tenant RLS posture

The currently merged tenant tables in this T0 slice are:

- `identity_org_memberships`;
- `identity_sessions`;
- `identity_org_role_assignments`;
- `events`.

All four use both PostgreSQL `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`. Each has the `tenant_context_isolation` policy, whose `USING` and `WITH CHECK` expressions require row `org_id` to equal transaction-local `app.current_org_id`.

The merged constrained-runtime Identity tests prove:

- no tenant context hides tenant rows;
- a mismatched tenant hides tenant rows;
- the matching tenant exposes the row;
- knowing a globally unique Session or RoleAssignment physical UUID does not bypass tenant isolation.

TICK-26 exercises Event insertion through the same tenant-scoped runtime boundary and verifies cross-tenant/fabricated-organizer attempts do not create an Event. TICK-28 adds the following integrated verification evidence without changing the authorization mechanism:

- the candidate `org_id` is installed as transaction-local context for the matching Membership probe and remains only a selector until that persisted proof succeeds;
- after Membership proof, the same UUID remains in `app.current_org_id` through Event insertion;
- test instrumentation observes the Membership query and Event INSERT on the same PostgreSQL backend PID, with one tenant-context transition;
- cleanup is verified after commit, proof rollback and exception, followed by reuse of the pooled backend without tenant bleed;
- direct-SQL cross-tenant reads of Membership, Session and RoleAssignment rows return no rows, including when the caller knows globally unique physical UUIDs;
- direct-SQL write probes target Event rows: updating another tenant's Event affects zero rows, and changing an Event's `org_id` is rejected by RLS; TICK-28 does not directly test Identity-table writes, although those tables have RLS `WITH CHECK` policies;
- runtime-role tests verify the role is not the table owner, is not a superuser and has `NOBYPASSRLS` posture.

These are test observations of the approved transaction and RLS behavior. They do not create a new authorization mechanism or make a UUID an authorization credential.

The global `identity_users` table is outside tenant RLS semantics.

## TEN-1 physical-PK exception

JIP-T0-01 v0.1.5 explicitly selects TEN-1's narrow single-column physical-primary-key exception for exactly:

- `identity_org_memberships(org_membership_id)`;
- `identity_sessions(id)`;
- `identity_org_role_assignments(role_assignment_id)`.

Those physical keys are database-generated UUIDv7 values in production and remain non-writable through the merged production Ash interfaces. Their global uniqueness is never treated as authorization.

The exception does not relax the required tenant identities. The merged database contains and tests these exact org-first unique indexes:

- Membership `(org_id, org_membership_id)`;
- Membership `(org_id, user_id)`;
- RoleAssignment `(org_id, user_id, role)`;
- Session `(org_id, id)`.

The Event resource does not use that exception: its merged physical primary key is tenant-composite `(org_id, event_id)`.

Future tenant-to-tenant relationships must preserve the tenant dimension even when the target has a globally unique physical UUID.

## Identity evidence boundary

The merged Identity resources use Ash policies in addition to database RLS. Their governed read actions require the authenticated actor's `user_id` to match the persisted row user where applicable.

The organizer flow consumes these persisted evidence reads in order:

- active/non-revoked organization Membership proof;
- active User liveness;
- active, non-revoked, unexpired Session liveness using PostgreSQL UTC `now()`;
- active/non-revoked organization RoleAssignment evidence.

Session credentials remain outside this application boundary: the resource contains a sensitive, non-public `token_hash`, but the governed liveness action deliberately selects only non-secret Session fields. Session has no merged create/update/destroy action.

Authentication/session infrastructure supplies authoritative authenticated `user_id` and `session_id`. Organization, scope, and role values presented by a caller are selectors until the governing action proves the corresponding persisted state.

## Event-create authorization boundary

`Ticketing.Events.create_event/2` is the merged production entry point for the TICK-26 Event-create effect. The Event resource has one create action, `create_event`; there is no second `persist_draft` or equivalent Event persistence action.

The action performs the organizer proof chain before the terminal Event insert:

```text
Membership proof
→ User liveness
→ Session liveness using DB time
→ RoleAssignment liveness
→ IAM authorize_event_create
→ Event insert
```

The Event action's initial actor check is only a preliminary trusted-session shape gate. It is not sufficient authority to insert a row. The persisted Identity evidence must still be read and IAM authorization must succeed in the same transaction.

`Ticketing.Identity.Authorization.authorize_event_create` is a private, non-persistent Ash action. Its policy validates the current human actor and the persisted User/Membership/Session/RoleAssignment records against the selected organization, scope and role. The current permitted roles are `org_owner` and `org_admin`, with `active_scope == "org"`.

The authorization action returns boolean success for the current orchestration. It does not return a reusable organizer persona, signed capability, opaque token, or other object that can independently authorize a later Event mutation.

All Event persistence remains authorized (`authorize?: true`). Events does not duplicate IAM role/capability policy in a second write action, and ordinary runtime code does not bypass this boundary with direct Repo/Ecto/raw-SQL persistence.

## Current boundary and downstream work

TICK-26 ends after one authorized tenant-owned draft Event is persisted. It does not implement occurrence creation, publication, publication outbox/event behavior, sales, commerce, tickets or ledger behavior.

TICK-28 is merged verification evidence for the same create-only T0-01 boundary. The complete record is in the [T0-01 implementation handoff](../handoffs/T0-01.md). Event publication, Occurrence and later sales work remain outside this increment.
