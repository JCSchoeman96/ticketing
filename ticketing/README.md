# Ticketing application

This Phoenix application is the product implementation in the parent repository. Run Mix
commands from this directory. Canonical domain contracts live in the sibling
`JCSchoeman96/ticketing-contracts` repository. The reviewed implementation baseline is
CANON-1 2.0.13 at reviewed contracts commit `b6e4bac210a7bdd906b611984150d1f1198f3141`, recorded in
`../contracts/authority.json` as a consumption pin rather than a second release.

After B0 bootstrap, T0 is the next implementation slice. Its tracer is in the canonical
contracts repository at `planning/tracers/T0-tenant-scoped-ga-pending-sale.md`.

Use `mix setup` to fetch dependencies, create and migrate the development database, and build
assets. The checked-in AshPostgres migration installs support functions and creates no
application tables. Then use `mix contract.authority` to verify the local canonical checkout.

To start your Phoenix server:

* Run `mix setup` to install and setup dependencies
* Start Phoenix endpoint with `mix phx.server` or inside IEx with `iex -S mix phx.server`

Now you can visit [`localhost:4000`](http://localhost:4000) from your browser.

Ready to run in production? Please [check our deployment guides](https://hexdocs.pm/phoenix/deployment.html).

## Learn more

* Official website: https://www.phoenixframework.org/
* Guides: https://hexdocs.pm/phoenix/overview.html
* Docs: https://hexdocs.pm/phoenix
* Forum: https://elixirforum.com/c/phoenix-forum
* Source: https://github.com/phoenixframework/phoenix
