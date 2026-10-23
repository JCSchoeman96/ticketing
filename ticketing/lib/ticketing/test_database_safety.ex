defmodule Ticketing.TestDatabaseSafety do
  @moduledoc false

  @shared_test_hosts ["127.0.0.1", "localhost", "::1"]
  @shared_test_port 55_433
  @shared_test_database "ticketing_test"

  def validate_migration_repo(repo_config) do
    host = Keyword.get(repo_config, :hostname)
    port = Keyword.get(repo_config, :port)
    database = Keyword.get(repo_config, :database)

    if host in @shared_test_hosts and port == @shared_test_port and
         database == @shared_test_database do
      {:error,
       "Ticketing TEST safety guard: #{host}:#{port}/#{database} is the shared workstation TEST base database. Set a unique MIX_TEST_PARTITION for this worktree before running database setup or test gates."}
    else
      :ok
    end
  end
end
