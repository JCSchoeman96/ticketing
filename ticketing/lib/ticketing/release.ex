defmodule Ticketing.Release do
  @moduledoc """
  Used for executing DB release tasks when run in production without Mix
  installed.
  """
  @app :ticketing

  alias Ticketing.Platform.DatabasePrivileges

  def migrate do
    load_app()
    migration_repo = migration_repo!()

    {:ok, :ok, _} =
      Ecto.Migrator.with_repo(migration_repo, fn repo ->
        Ecto.Migrator.run(repo, :up, all: true)
        DatabasePrivileges.apply!(repo)
      end)
  end

  def rollback(_repo, version) do
    load_app()
    migration_repo = migration_repo!()

    {:ok, _, _} =
      Ecto.Migrator.with_repo(migration_repo, fn repo ->
        Ecto.Migrator.run(repo, :down, to: version)
        DatabasePrivileges.apply!(repo)
      end)
  end

  defp load_app do
    # Many platforms require SSL when connecting to the database
    Application.ensure_all_started(:ssl)
    Application.ensure_loaded(@app)
  end

  defp migration_repo! do
    if Application.get_env(@app, Ticketing.MigrationRepo) do
      Ticketing.MigrationRepo
    else
      raise "Ticketing.MigrationRepo is not configured. Set MIGRATION_DATABASE_URL for release migrations."
    end
  end
end
