# Database baseline

> Nature and status: Derived implementation documentation. This document describes merged infrastructure and database state; it does not define product semantics.
>
> Last verified main SHA: `25a6a0956d7bb81214e348c7511132f5297d0fc5`
>
> Governing JIPs: JIP-T0-00 / Plane TICK-1, approved; JIP-T0-01 v0.1.6 / Plane TICK-25 and TICK-26 for the merged Identity persistence, tenant isolation, and draft Event persistence posture.
>
> Plane work: TICK-4, TICK-7, TICK-8, TICK-9, TICK-12, TICK-16, TICK-17, TICK-25, TICK-26.
>
> Related merged PRs include [#9 (TICK-12)](https://github.com/JCSchoeman96/ticketing/pull/9), [#12 (TICK-4)](https://github.com/JCSchoeman96/ticketing/pull/12), [#15](https://github.com/JCSchoeman96/ticketing/pull/15), [#40 (TICK-25)](https://github.com/JCSchoeman96/ticketing/pull/40), and [#45 (TICK-26)](https://github.com/JCSchoeman96/ticketing/pull/45).

## PostgreSQL ownership and environments

| Environment | Owner | Endpoint | Role and database | Version and notes |
| --- | --- | --- | --- | --- |
| DEV | `SHARED_LOCAL` | `127.0.0.1:55432` | `ticketing_dev` / `ticketing_dev` | PostgreSQL 18.6 |
| TEST | `SHARED_LOCAL` | `127.0.0.1:55433` | `ticketing_test` / base database `ticketing_test` | PostgreSQL 18.6; Repo pool size is 10 |
| CI bootstrap | `TOOL_OWNED` | Job-local service | Ephemeral PostgreSQL service | `postgres:18.6-alpine`; no dependency on workstation `dev-core` |

DEV and TEST use separate physical PostgreSQL clusters. The TEST role has `CREATEDB` only to create deterministic `MIX_TEST_PARTITION` databases. The TEST configuration appends the partition suffix to the `ticketing_test` base database and rejects the DEV port and database name.

`dev-core` is workstation-owned. Ticketing configuration uses its shared endpoints; repository code and workflows do not lifecycle-manage those services. The repository does not define a `pgdata18` service or volume. The deployment [`compose.yaml`](../../../compose.yaml) contains only the application service and has no PostgreSQL or Redis service.

Redis is N/A for Ticketing. The DEV allocation contract sets `USE_REDIS=no`; the current application does not depend on Redis.

## Owner/runtime role split

Ticketing uses the configured owner/migration connection for schema ownership and migration work and a distinct constrained runtime role for application data access. `Ticketing.Platform.DatabasePrivileges` applies the runtime grants after migrations. The runtime role receives database connect, schema usage, application-table DML privileges and sequence usage as required, while `schema_migrations` remains outside the application-table grant set.

The runtime role is not the migration owner. Runtime-role tests verify that application DML can operate only within the intended database controls and that schema-changing operations are denied.

## Tenant context

`Ticketing.Platform.TenantContext` maps the active tenant to the PostgreSQL setting `app.current_org_id`. The setting is installed only inside an active Repo transaction and is transaction-local via PostgreSQL `set_config(..., true)`.

`Ticketing.Repo.on_transaction_begin/1` installs that tenant value when Ash begins a tenant transaction. Missing tenant context therefore leaves the tenant setting absent rather than creating a process-global or connection-persistent tenant identity.

TICK-26 reuses this substrate for the organizer-to-Event transaction. The candidate organization is installed as the transaction-local tenant so the matching Membership proof can run; successful proof establishes that same UUID as the proven organization, and the value remains unchanged through the Event insert.

## Current application migrations

The merged migration directory contains:

- `20261009193532_b0_ash_postgres_functions_extensions_1.exs` — AshPostgres functions/extensions baseline;
- `20261025200030_tick25_identity_resources.exs` — TICK-25 Identity tables, relationships, tenant indexes and tenant RLS/FORCE-RLS policies;
- `20261026051729_tick25_session_identity_snapshots.exs` — Session `(org_id, id)` identity/index follow-up generated from the final Ash snapshot;
- `20261026132000_tick26_events.exs` — TICK-26 `events` table, tenant identities, defaults, unique indexes, and tenant RLS/FORCE-RLS policy.

## Merged Identity persistence

The merged Identity tables are:

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

## Merged Event persistence

The `events` table is tenant-scoped and uses composite physical primary key `(org_id, event_id)`. The merged Event resource marks both fields as protected/non-writable through the production create surface; `event_id` is generated by the governed action and `org_id` is forced from the proven tenant context.

The table currently stores the draft-Event fields implemented by TICK-26, including public event key, slug, visibility, locale fields, featured flag, taxonomy references, lifecycle timestamps, version and lock version. Database defaults preserve the initial draft posture where applicable: `status = 'draft'`, `featured = false`, `taxonomy_refs = []`, `version = 1`, `lock_version = 1`, and database-owned UTC create/update timestamps.

The database enforces these tenant-scoped uniqueness rules:

- Event `(org_id, public_event_key)`;
- Event `(org_id, slug)`.

These constraints are the authoritative arbiter for duplicate/concurrent uniqueness races. The application does not rely on a preflight-only uniqueness check.

## Row-level security

`identity_org_memberships`, `identity_sessions`, `identity_org_role_assignments`, and `events` each have both `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` applied. Their `tenant_context_isolation` policy uses transaction-local `app.current_org_id` for both `USING` and `WITH CHECK`.

The constrained runtime Identity matrix verifies that a tenant row is hidden with no tenant context, hidden under a mismatched tenant, and visible under the matching tenant. Session and RoleAssignment are also queried by their globally unique physical primary keys in those tests, demonstrating that knowledge of the UUID alone does not bypass tenant isolation.

TICK-26 verifies the Event create path under the tenant transaction and proves cross-tenant or fabricated-organizer attempts cannot use the Event action as an alternate authorization path. TICK-28's direct-SQL test checks cross-tenant reads of Membership, Session, and RoleAssignment rows; those reads return no rows even when the caller knows globally unique physical UUIDs. Its write probes target Event rows: updating another tenant's Event affects zero rows, and changing an Event's `org_id` is rejected by RLS. The test does not attempt writes to Identity tables. Their policies' `WITH CHECK` clauses are structural enforcement, not direct Identity-write test evidence. TICK-28 also checks runtime ownership and `NOBYPASSRLS` posture, observes tenant GUC continuity on one backend through proof and insert, and verifies cleanup/pool reuse. This supplements TICK-26 tests and changes no database architecture or schema. See the [T0-01 implementation handoff](../handoffs/T0-01.md).

`identity_users` is global and is not protected by tenant RLS semantics.

## Legacy rollback evidence

TICK-16 records two preserved PostgreSQL 16 worktree containers and their named volumes: `refresh-contract-authority-pin-db-1` with `refresh-contract-authority-pin_pgdata`, and `b0-bootstrap-db-1` with `b0-bootstrap_pgdata`. The investigation found no evidence that a Ticketing Redis container or volume had been instantiated. This document makes no claim that a Redis asset was preserved. Those assets are historical rollback/context evidence and are not the active PostgreSQL 18 baseline.
