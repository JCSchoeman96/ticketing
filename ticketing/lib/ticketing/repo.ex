defmodule Ticketing.Repo do
  use Ecto.Repo,
    otp_app: :ticketing,
    adapter: Ecto.Adapters.Postgres
end
