defmodule Mix.Tasks.Ticketing.TestDatabase.Guard do
  use Mix.Task

  @moduledoc false
  @shortdoc "Fails closed before TEST mutations target the shared base database"

  @impl Mix.Task
  def run(_args) do
    if Mix.env() == :test do
      :ticketing
      |> Application.fetch_env!(Ticketing.MigrationRepo)
      |> Ticketing.TestDatabaseSafety.validate_migration_repo()
      |> case do
        :ok -> :ok
        {:error, message} -> Mix.raise(message)
      end
    end
  end
end
