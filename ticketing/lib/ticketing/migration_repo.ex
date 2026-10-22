defmodule Ticketing.MigrationRepo do
  @moduledoc """
  Owner-scoped Repo used only for database creation, migrations, and setup.

  It is not supervised by the application. `Ticketing.Repo` remains the normal
  runtime Repo and uses a separate, constrained database identity.
  """

  use AshPostgres.Repo, otp_app: :ticketing

  @impl AshPostgres.Repo
  def installed_extensions, do: ["ash-functions"]

  @impl AshPostgres.Repo
  def min_pg_version, do: %Version{major: 18, minor: 0, patch: 0}
end
