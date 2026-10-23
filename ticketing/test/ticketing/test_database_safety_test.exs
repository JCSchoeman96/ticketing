defmodule Ticketing.TestDatabaseSafetyTest do
  use ExUnit.Case, async: false

  alias Mix.Tasks.Ticketing.TestDatabase.Guard
  alias Ticketing.TestDatabaseSafety

  @shared_database_error "Ticketing TEST safety guard: 127.0.0.1:55433/ticketing_test is the shared workstation TEST base database. Set a unique MIX_TEST_PARTITION for this worktree before running database setup or test gates."

  test "the Mix task fails with a helpful message for the shared TEST base" do
    previous_config = Application.fetch_env!(:ticketing, Ticketing.MigrationRepo)

    Application.put_env(
      :ticketing,
      Ticketing.MigrationRepo,
      Keyword.merge(previous_config,
        hostname: "127.0.0.1",
        port: 55_433,
        database: "ticketing_test"
      )
    )

    on_exit(fn ->
      Application.put_env(:ticketing, Ticketing.MigrationRepo, previous_config)
    end)

    error = assert_raise Mix.Error, fn -> Guard.run([]) end
    assert Exception.message(error) == @shared_database_error
  end

  test "a valid TEST partition keeps the shared TEST endpoint and avoids the base database" do
    repo_config = [hostname: "127.0.0.1", port: 55_433, database: "ticketing_test17"]

    assert repo_config[:port] == 55_433
    assert repo_config[:database] == "ticketing_test17"
    refute repo_config[:database] == "ticketing_test"
    assert TestDatabaseSafety.validate_migration_repo(repo_config) == :ok
  end

  test "job-owned CI PostgreSQL on port 5432 remains supported" do
    repo_config = [hostname: "127.0.0.1", port: 5432, database: "ticketing_test"]

    assert TestDatabaseSafety.validate_migration_repo(repo_config) == :ok
  end

  test "TEST's DEV endpoint is outside the local shared TEST guard" do
    repo_config = [hostname: "127.0.0.1", port: 55_432, database: "ticketing_dev"]

    assert TestDatabaseSafety.validate_migration_repo(repo_config) == :ok
  end
end
