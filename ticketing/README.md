# Ticketing application

This Phoenix application is the product implementation. Canonical Ticketing authority lives in the parent repository's `authority/` directory. Its precedence remains CANON and canonical contracts, then the ROADMAP and active tracer, then approved JIP and Plane execution work.

Run Mix commands from this directory. Before setup, render and check the workstation `dev-core` allocation from the repository root with `devcore-project render` and `devcore-project doctor`, then load the root `.envrc` environment. DEV uses `127.0.0.1:55432`; TEST uses `127.0.0.1:55433` with the `MIX_TEST_PARTITION` suffix. The checked-in AshPostgres migration installs support functions and creates no application tables.

`mix setup` fetches dependencies, migrates the provisioned DEV database without creating it, runs seeds, and builds assets. It works with the DEV role's `NOCREATEDB` privilege. The destructive `mix ecto.reset` alias was removed because it dropped and recreated the shared database. Start the local server on [localhost:4200](http://localhost:4200). Redis is not a Ticketing prerequisite.

Run `mix contract.authority` to validate the in-repository manifest, CANON, active tracer, and strict canonical audit. The current CANON version is derived from the authority manifest.

To start the Phoenix server:

- Run `mix setup` to install and set up dependencies.
- Start the endpoint with `mix phx.server` or inside IEx with `iex -S mix phx.server`.

The local Phoenix server listens on port `4200`. Reserve ports `4201` to `4219` for worktrees.

## Learn more

- Official website: https://www.phoenixframework.org/
- Guides: https://hexdocs.pm/phoenix/overview.html
- Docs: https://hexdocs.pm/phoenix
- Forum: https://elixirforum.com/c/phoenix-forum
- Source: https://github.com/phoenixframework/phoenix
