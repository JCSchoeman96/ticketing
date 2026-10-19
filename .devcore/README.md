# dev-core local contract (T0-00.3A)

These files are committed and contain **no secrets**.

## Scope

T0-00.3A provisions **workstation PostgreSQL allocation only** on the shared `dev-core` clusters:

- DEV: `ticketing_dev` @ `127.0.0.1:55432` / database `ticketing_dev`
- TEST: `ticketing_test` @ `127.0.0.1:55433` / base database `ticketing_test` (`CREATEDB=yes` for partition DBs)

**Application DB wiring** (`dev.exs`, `test.exs`, CI, and full URL construction) is **TICK-4**, not this increment.

## Rendered variables

`env.local.template` renders **inert Ticketing-specific components** into ignored `.envrc.private` (host, port, user, password, database name per profile). It does **not** export `DATABASE_URL` or `DATABASE_URL_TEST`, so the 3A bootstrap cannot bypass existing config or `MIX_TEST_PARTITION` semantics.

TICK-4 must construct the effective test database as `ticketing_test#{MIX_TEST_PARTITION}` (e.g. `ticketing_test1`) from `TICKETING_TEST_DB_NAME` and the partition suffix.

## Redis

Redis is **N/A** for Ticketing (`USE_REDIS=no`). Do not provision or configure shared Redis for this project in 3A.

## Activation

1. Ensure every render target in `render-map.tsv` is ignored by Git.
2. From the repository root:

   ```bash
   devcore-project plan
   devcore-project activate
   ```

3. Run application migrations/tests only after TICK-4 wires config, or using explicit env you control for that work item.
