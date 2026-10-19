# Ticketing application

This Phoenix application is the product implementation. Canonical Ticketing authority lives in the parent repository's `authority/` directory. Its precedence remains CANON and canonical contracts, then the ROADMAP and active tracer, then approved JIP and Plane execution work.

Run Mix commands from this directory. Use `mix setup` to fetch dependencies, create and migrate the development database, and build assets. The checked-in AshPostgres migration installs support functions and creates no application tables.

Run `mix contract.authority` to validate the in-repository manifest, CANON, active tracer, and strict canonical audit. The current CANON version is derived from the authority manifest.

To start the Phoenix server:

- Run `mix setup` to install and set up dependencies.
- Start the endpoint with `mix phx.server` or inside IEx with `iex -S mix phx.server`.

Visit [localhost:4000](http://localhost:4000) from your browser.

## Learn more

- Official website: https://www.phoenixframework.org/
- Guides: https://hexdocs.pm/phoenix/overview.html
- Docs: https://hexdocs.pm/phoenix
- Forum: https://elixirforum.com/c/phoenix-forum
- Source: https://github.com/phoenixframework/phoenix
