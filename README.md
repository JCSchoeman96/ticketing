# Ticketing

This is the product implementation repository. The Phoenix application lives in `ticketing/`.
Canonical domain authority lives in [JCSchoeman96/ticketing-contracts](https://github.com/JCSchoeman96/ticketing-contracts).
This implementation consumes CANON-1 2.0.10 from reviewed contracts commit
`cc335793e7a542e44938883f87cc96f796a4fe32`. The pin in `contracts/authority.json` records
that reviewed baseline and does not create a second contract release.

The next product implementation slice after bootstrap B0 is T0, described by
`planning/tracers/T0-tenant-scoped-ga-pending-sale.md` in the contracts repository.

## Local setup

From the repository root:

1. Install the runtimes listed in `.tool-versions` with `mise install` or `asdf install`.
2. Start PostgreSQL with `docker compose up -d db`. Compose publishes it on `localhost:5433`.
3. Run `direnv allow` to load the local environment from `.envrc`.
4. Check out the contracts repository beside this repository and pin it to the reviewed commit:

   ```sh
   git clone git@github.com:JCSchoeman96/ticketing-contracts.git ../ticketing-contracts
   git -C ../ticketing-contracts checkout cc335793e7a542e44938883f87cc96f796a4fe32
   ```

   If your checkout is elsewhere, set `TICKETING_CONTRACTS_PATH` in the shell or in the
   ignored `.envrc.private` file. The default is `../../ticketing-contracts` from `ticketing/`.
5. Run application commands from `ticketing/`:

   ```sh
   cd ticketing
   mix setup
   mix contract.authority
   mix precommit
   mix phx.server
   ```

`mix contract.authority --pin-only` checks the checked-in authority pin without accessing the
contracts repository. CI uses this mode because it does not need credentials for the private
contracts repository. `mix setup` also applies one AshPostgres support-function migration; it
creates no application tables.
