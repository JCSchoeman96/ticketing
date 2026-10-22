defmodule Ticketing.Repo do
  use AshPostgres.Repo,
    otp_app: :ticketing

  alias Ticketing.Platform.TenantContext

  @impl AshPostgres.Repo
  def installed_extensions, do: ["ash-functions"]

  @impl AshPostgres.Repo
  def min_pg_version, do: %Version{major: 18, minor: 0, patch: 0}

  @impl AshPostgres.Repo
  def on_transaction_begin(%{tenant: tenant}) when not is_nil(tenant) do
    TenantContext.put_current_org!(tenant)
  end

  def on_transaction_begin(_reason), do: :ok
end
