# Database baseline

> Nature and status: Derived implementation documentation. This document describes merged infrastructure and database configuration; it does not define product semantics.
>
> Last verified main SHA: `ebf0018d18fd4422707551a2b391d92f7ad52246`
>
> Governing JIP: JIP-T0-00 / Plane TICK-1, approved
>
> Plane work: TICK-4, TICK-7, TICK-8, TICK-9, TICK-16, TICK-17
>
> Merged PRs: [#9](https://github.com/JCSchoeman96/ticketing/pull/9), [#12](https://github.com/JCSchoeman96/ticketing/pull/12), [#15](https://github.com/JCSchoeman96/ticketing/pull/15)

## Current PostgreSQL ownership

| Environment | Owner | Endpoint | Role and database | Version and notes |
| --- | --- | --- | --- | --- |
| DEV | `SHARED_LOCAL` | `127.0.0.1:55432` | `ticketing_dev` / `ticketing_dev` | PostgreSQL 18.6 |
| TEST | `SHARED_LOCAL` | `127.0.0.1:55433` | `ticketing_test` / base database `ticketing_test` | PostgreSQL 18.6; Repo pool size is 10 |
| CI bootstrap | `TOOL_OWNED` | Job-local service | Ephemeral PostgreSQL service | `postgres:18.6-alpine`; no dependency on workstation `dev-core` |

DEV and TEST use separate physical PostgreSQL clusters. The TEST role has `CREATEDB` only to create deterministic `MIX_TEST_PARTITION` databases. The TEST configuration appends the partition suffix to the `ticketing_test` base database and rejects the DEV port and database name.

`dev-core` is workstation-owned. Ticketing configuration uses its shared endpoints; repository code and workflows do not lifecycle-manage those services. The repository does not define a `pgdata18` service or volume. The deployment [`compose.yaml`](../../../compose.yaml) contains only the application service and has no PostgreSQL or Redis service.

Redis is N/A for Ticketing. The DEV allocation contract sets `USE_REDIS=no`; the current application does not depend on Redis.

## Legacy rollback evidence

TICK-16 records two preserved PostgreSQL 16 worktree containers and their named volumes: `refresh-contract-authority-pin-db-1` with `refresh-contract-authority-pin_pgdata`, and `b0-bootstrap-db-1` with `b0-bootstrap_pgdata`. The investigation found no evidence that a Ticketing Redis container or volume had been instantiated. This document makes no claim that a Redis asset was preserved. T0-00 did not authorize deletion of legacy assets.

## Migration state and deferral

The only application migration at this baseline is [`20261009193532_b0_ash_postgres_functions_extensions_1.exs`](../../priv/repo/migrations/20261009193532_b0_ash_postgres_functions_extensions_1.exs), the generated AshPostgres functions/extensions setup. There is no T0 product-domain migration.

T0-00 did not decide the migration owner, runtime database role, or `FORCE ROW LEVEL SECURITY` posture. T0-01 JIT must make those decisions before tenant or RLS implementation. This document does not infer them from local database ownership.
