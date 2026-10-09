defmodule Ticketing.Repo do
  use AshPostgres.Repo,
    otp_app: :ticketing

  @impl AshPostgres.Repo
  def installed_extensions, do: ["ash-functions"]

  @impl AshPostgres.Repo
  def min_pg_version, do: %Version{major: 16, minor: 0, patch: 0}
end
