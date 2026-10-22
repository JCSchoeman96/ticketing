defmodule Ticketing.TenantContextTestRepo do
  @moduledoc false

  use Ecto.Repo,
    otp_app: :ticketing,
    adapter: Ecto.Adapters.Postgres
end
