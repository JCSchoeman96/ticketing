# Database baseline

> Nature and status: Derived implementation documentation. This document describes merged infrastructure and database state; it does not define product semantics.
>
> Last verified main SHA: `c6979779a33ca2e4f84573bab7211bb800cf45cb`
>
> Governing JIPs: JIP-T0-00 / Plane TICK-1, approved; JIP-T0-01 v0.1.5 / Plane TICK-25 for the merged Identity persistence and tenant-isolation posture.
>
> Related merged PRs include [#40 (TICK-25)](https://github.com/JCSchoeman96/ticketing/pull/40).

## PostgreSQL ownership and environments

| Environment | Owner / migration connection | Endpoint | Version and notes |
| --- | --- | --- | --- |
| DEV | configured Ticketing DEV owner/migration role | `127.0.0.1:55432` | PostgreSQL 18.6 |
| TEST | configured Ticketing TEST owner/migration role | `127.0.0.1:55433` | PostgreSQL 18.6; partitioned test databases are supported |
| CI bootstrap | job-local owner/migration role | ephemeral PostgreSQL service | `postgres:18.6-alpine` |

DEV and TEST use separate PostgreSQL endpoints. The repository does not lifecycle-manage the workstation-owned shared database services. The deployment [`compose.yaml`](../../../compose.yaml) contains only the application service and has no PostgreSQL or Redis service.

Redis is N/A for Ticketing. The current application does not depend on Redis.

## Owner/runtime role split

Ticketing uses a privileged owner/migration connection for schema ownership and migration work and a distinct constrained runtime role for application data access. `Ticketing.Platform.DatabasePrivileges` applies the runtime grants after migrations. The runtime role receives database connect, schema usage, application-table DML privileges and sequence usage as required, while `schema_migrations` remains outside the application-table grant set.

The runtime role is not the migration owner. Runtime-role tests verify that application DML can operate only within the intended database controls and that schema-changing operations are denied.

## Tenant context

`Ticketing.Platform.TenantContext` maps the active tenant to the PostgreSQL setting `app.current_org_id`. The setting is installed only inside an active Repo transaction and is transaction-local via PostgreSQL `set_config(..., true)`.

`Ticketing.Repo.on_transaction_begin/1` installs that tenant value when Ash begins a tenant transaction. Missing tenant context therefore leaves the tenant setting absent rather than creating a process-global or connection-persistent tenant identity.

## Current application migrations

The merged migration directory contains:

- `20261009193532_b0_ash_postgres_functions_extensions_1.exs` — AshPostgres functions/extensions baseline;
- `20261025200030_tick25_identity_resources.exs` — TICK-25 Identity tables, relationships, tenant indexes and tenant RLS/FORCE-RLS policies;
- `20261026051729_tick25_session_identity_snapshots.exs` — Session `(org_id, id)` identity/index follow-up generated from the final Ash snapshot.

There is still no Event table or Event migration. Event persistence remains downstream TICK-26 work.

## Merged Identity persistence

The merged tables are:

| Table | Scope | Physical primary key |
| --- | --- | --- |
| `identity_users` | global | `id` |
| `identity_org_memberships` | tenant | `org_membership_id` |
| `identity_sessions` | tenant | `id` |
| `identity_org_role_assignments` | tenant | `role_assignment_id` |

The three tenant physical primary keys use database-generated UUIDv7 values. JIP-T0-01 v0.1.5 explicitly grants TEN-1's narrow single-column physical-PK exception to exactly those three keys. That exception does not make the IDs authorization credentials and does not relax tenant-scoped identities or RLS.

The required org-first unique indexes are physically present and their catalog order is tested:

- Membership `(org_id, org_membership_id)`;
- Membership `(org_id, user_id)`;
- RoleAssignment `(org_id, user_id, role)`;
- Session `(org_id, id)`.

Tenant Identity rows reference the global User resource where applicable. Future tenant-to-tenant relationships must still preserve the tenant dimension; the globally unique physical UUID does not create a cross-tenant relationship shortcut.

## Row-level security

`identity_org_memberships`, `identity_sessions`, and `identity_org_role_assignments` each have both `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` applied. Their `tenant_context_isolation` policy uses the transaction-local `app.current_org_id` value for both `USING` and `WITH CHECK`.

The constrained runtime test matrix verifies that a tenant row is hidden with no tenant context, hidden under a mismatched tenant, and visible under the matching tenant. Session and RoleAssignment are also queried by their globally unique physical primary keys in those tests, demonstrating that knowledge of the UUID alone does not bypass tenant isolation.

`identity_users` is global and is not protected by tenant RLS semantics.

## Legacy rollback evidence

TICK-16 records preserved PostgreSQL 16 worktree containers and named volumes from earlier bootstrap work. That evidence remains historical rollback/context information and is not the active PostgreSQL 18 runtime baseline. No claim is made that a Ticketing Redis asset existed.
