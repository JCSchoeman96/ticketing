# Tenancy and authorization

> Nature and status: Derived implementation documentation. This document describes merged platform behavior and does not define product semantics.
>
> Last verified main SHA: `c6979779a33ca2e4f84573bab7211bb800cf45cb`
>
> Governing JIP: JIP-T0-01 v0.1.5. Relevant merged Plane work: TICK-25 plus the previously merged tenant/database substrate it reuses.
>
> Merged implementation PR: [#40](https://github.com/JCSchoeman96/ticketing/pull/40).

## Database-role boundary

Ticketing separates schema ownership/migration authority from the constrained application runtime role. `Ticketing.Platform.DatabasePrivileges` applies the runtime privileges after migrations rather than giving the runtime role ownership of the schema.

The runtime grant set covers the database/schema access and application-table DML needed by the application. It excludes `schema_migrations` from the ordinary application table grant set. Verification also proves that the constrained role cannot perform schema-changing operations that belong to the owner/migration boundary.

This role split is infrastructure enforcement. It does not itself grant product/domain authority to a user or tenant.

## Transaction-local tenant context

Tenant data access is bound to the PostgreSQL setting:

`app.current_org_id`

`Ticketing.Platform.TenantContext.put_current_org!/1` validates the tenant UUID, requires an active Repo transaction, and installs the value using transaction-local PostgreSQL `set_config(..., true)` semantics.

`Ticketing.Repo.on_transaction_begin/1` connects Ash tenant transactions to that database tenant context. The setting is therefore scoped to the active transaction instead of being a durable connection-level tenant identity.

A caller-provided organization UUID is not, by itself, authorization. The tenant context controls database visibility; higher-level organizer authority still comes from the governed persisted evidence required by the applicable action.

## Tenant RLS posture

The currently merged tenant Identity tables are:

- `identity_org_memberships`;
- `identity_sessions`;
- `identity_org_role_assignments`.

All three use both PostgreSQL `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`. Each has the `tenant_context_isolation` policy, whose `USING` and `WITH CHECK` expressions require the row `org_id` to equal transaction-local `app.current_org_id`.

The merged constrained-runtime tests prove:

- no tenant context hides tenant rows;
- a mismatched tenant hides tenant rows;
- the matching tenant exposes the row;
- knowing a globally unique Session or RoleAssignment physical UUID does not bypass tenant isolation.

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

Future tenant-to-tenant relationships must preserve the tenant dimension even when the target has a globally unique physical UUID.

## Identity authorization boundary

The merged Identity resources use Ash policies in addition to database RLS. Their governed read actions require the authenticated actor's `user_id` to match the persisted row user where applicable.

The current domain exposes only the reads needed as evidence for the later organizer flow:

- User liveness;
- active/non-revoked organization Membership proof;
- active, non-revoked, unexpired Session liveness;
- active/non-revoked organization role assignment.

Session credentials are outside this T0 application boundary: the resource contains a sensitive, non-public `token_hash`, but the governed liveness action deliberately selects only non-secret Session fields. Session has no merged create/update/destroy action.

Authentication/session infrastructure is responsible for supplying authoritative authenticated `user_id` and `session_id`. Organization, scope, and role values presented by a caller remain selectors until the governing action proves the corresponding persisted state.

## Downstream constraint, not yet implemented

The approved T0-01 packet requires the future TICK-26 Event-create effect to keep candidate-org membership proof, post-proof User/Session/role validation, authorization, and the draft Event insert inside one outer governed transaction. Before successful membership proof, no other tenant business-row read may establish organizer authority.

That statement records a governing constraint on the next consumer of this substrate. `Ticketing.Events` and the integrated `create_event` transaction are **not** present in the merged implementation described by this document.
