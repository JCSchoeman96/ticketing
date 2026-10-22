defmodule Mix.Tasks.Ticketing.Db.GrantRuntimePrivileges do
  use Mix.Task

  @moduledoc "Applies runtime database privileges after owner migrations."

  @shortdoc "Apply least-privilege runtime grants after owner migrations"

  alias Ecto.Migrator
  alias Ticketing.MigrationRepo
  alias Ticketing.Platform.DatabasePrivileges

  @impl Mix.Task
  def run(_args) do
    Mix.Task.run("app.config")

    case Migrator.with_repo(MigrationRepo, &DatabasePrivileges.apply!/1) do
      {:ok, :ok, _repo} ->
        :ok

      {:error, _reason} ->
        Mix.raise("Could not apply runtime database privileges through Ticketing.MigrationRepo")
    end
  end
end
