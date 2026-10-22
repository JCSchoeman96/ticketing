defmodule Ticketing.RepoConfigTest do
  use ExUnit.Case, async: false

  @dev_env_vars ~w(
    TICKETING_DEV_DB_HOST
    TICKETING_DEV_DB_PORT
    TICKETING_DEV_DB_USER
    TICKETING_DEV_DB_PASSWORD
    TICKETING_DEV_DB_NAME
    TICKETING_DEV_RUNTIME_DB_USER
    TICKETING_DEV_RUNTIME_DB_PASSWORD
    TICKETING_DEV_MIGRATION_DB_USER
    TICKETING_DEV_MIGRATION_DB_PASSWORD
    DATABASE_URL
  )

  @test_env_vars ~w(
    TICKETING_TEST_DB_HOST
    TICKETING_TEST_DB_PORT
    TICKETING_TEST_DB_USER
    TICKETING_TEST_DB_PASSWORD
    TICKETING_TEST_DB_NAME
    TICKETING_TEST_RUNTIME_DB_USER
    TICKETING_TEST_RUNTIME_DB_PASSWORD
    TICKETING_TEST_MIGRATION_DB_USER
    TICKETING_TEST_MIGRATION_DB_PASSWORD
    DATABASE_URL_TEST
    MIX_TEST_PARTITION
  )

  @prod_env_vars ~w(DATABASE_URL MIGRATION_DATABASE_URL SECRET_KEY_BASE)

  test "development Repo defaults to the documented DEV runtime allocation" do
    environment =
      empty_env(@dev_env_vars, "dev")
      |> Map.put("DATABASE_URL", "postgresql://ignored.invalid/ignored")

    repo_config = read_repo_config("dev.exs", :dev, environment)

    assert repo_config[:hostname] == "127.0.0.1"
    assert repo_config[:port] == 55_432
    assert repo_config[:username] == "ticketing_dev_runtime"
    assert repo_config[:database] == "ticketing_dev"
    assert repo_config[:password] == "runtime-test-password"
    refute repo_config[:show_sensitive_data_on_connection_error]
    refute Keyword.has_key?(repo_config, :url)
  end

  test "development migration Repo stays owner-scoped with separate credentials" do
    environment =
      empty_env(@dev_env_vars, "dev")
      |> Map.put("TICKETING_DEV_MIGRATION_DB_USER", "ticketing_dev")
      |> Map.put("TICKETING_DEV_MIGRATION_DB_PASSWORD", "migration-test-password")

    configs = read_repo_configs("dev.exs", :dev, environment)

    assert configs.runtime[:username] == "ticketing_dev_runtime"
    assert configs.runtime[:password] == "runtime-test-password"
    assert configs.migration[:username] == "ticketing_dev"
    assert configs.migration[:password] == "migration-test-password"
    refute configs.runtime[:password] == configs.migration[:password]
  end

  test "local Repo config rejects the same owner and runtime role" do
    for {file, config_env, environment, prefix, owner_user} <- [
          {"dev.exs", :dev, empty_env(@dev_env_vars, "dev"), "DEV", "ticketing_dev"},
          {"test.exs", :test, empty_env(@test_env_vars, "test"), "TEST", "ticketing_test"}
        ] do
      environment =
        environment
        |> Map.put("TICKETING_#{prefix}_RUNTIME_DB_USER", owner_user)
        |> Map.put("TICKETING_#{prefix}_MIGRATION_DB_USER", owner_user)

      assert_raise ArgumentError, ~r/must be different/, fn ->
        read_repo_config(file, config_env, environment)
      end
    end
  end

  test "production runtime and migration Repos have separate database URLs" do
    environment =
      Map.new(@prod_env_vars, &{&1, nil})
      |> Map.put("DATABASE_URL", "ecto://ticketing_runtime:runtime-test@localhost/ticketing_prod")
      |> Map.put(
        "MIGRATION_DATABASE_URL",
        "ecto://ticketing_owner:migration-test@localhost/ticketing_prod"
      )
      |> Map.put("SECRET_KEY_BASE", String.duplicate("s", 64))

    configs = read_runtime_repo_configs(environment)

    assert configs.runtime[:url] == environment["DATABASE_URL"]
    assert configs.migration[:url] == environment["MIGRATION_DATABASE_URL"]
    refute configs.runtime[:url] == configs.migration[:url]
  end

  test "production runtime config does not require migration credentials" do
    environment =
      Map.new(@prod_env_vars, &{&1, nil})
      |> Map.put("DATABASE_URL", "ecto://ticketing_runtime:runtime-test@localhost/ticketing_prod")
      |> Map.put("SECRET_KEY_BASE", String.duplicate("s", 64))

    configs = read_runtime_repo_configs(environment)

    assert configs.runtime[:url] == environment["DATABASE_URL"]
    assert configs.migration == nil
  end

  test "production rejects migration URLs that use the runtime role" do
    environment =
      Map.new(@prod_env_vars, &{&1, nil})
      |> Map.put("DATABASE_URL", "ecto://ticketing_runtime:runtime-test@localhost/ticketing_prod")
      |> Map.put(
        "MIGRATION_DATABASE_URL",
        "ecto://ticketing_runtime:migration-test@localhost/ticketing_prod"
      )
      |> Map.put("SECRET_KEY_BASE", String.duplicate("s", 64))

    assert_raise ArgumentError, ~r/must use different PostgreSQL roles/, fn ->
      read_runtime_repo_configs(environment)
    end
  end

  test "development Repo requires its local password variable" do
    environment =
      empty_env(@dev_env_vars, "dev")
      |> Map.put("TICKETING_DEV_RUNTIME_DB_PASSWORD", nil)

    assert_raise System.EnvError, fn ->
      read_repo_config("dev.exs", :dev, environment)
    end
  end

  test "TEST database names append the partition to the configured base name" do
    for {partition, database} <- [
          {"", "ticketing_test"},
          {"1", "ticketing_test1"},
          {"2", "ticketing_test2"},
          {"17", "ticketing_test17"}
        ] do
      repo_config =
        read_repo_config("test.exs", :test, empty_env(@test_env_vars, "test", partition))

      assert repo_config[:database] == database
      assert repo_config[:username] == "ticketing_test_runtime"
      refute Keyword.has_key?(repo_config, :url)
    end
  end

  test "TEST migration Repo uses owner credentials and the same partition database" do
    for {partition, database} <- [{"", "ticketing_test"}, {"17", "ticketing_test17"}] do
      environment =
        empty_env(@test_env_vars, "test", partition)
        |> Map.put("TICKETING_TEST_MIGRATION_DB_USER", "ticketing_test")
        |> Map.put("TICKETING_TEST_MIGRATION_DB_PASSWORD", "migration-test-password")

      configs =
        read_repo_configs("test.exs", :test, environment)

      assert configs.runtime[:database] == database
      assert configs.migration[:database] == database
      assert configs.runtime[:username] == "ticketing_test_runtime"
      assert configs.migration[:username] == "ticketing_test"
      assert configs.runtime[:password] == "runtime-test-password"
      assert configs.migration[:password] == "migration-test-password"
      refute configs.runtime[:password] == configs.migration[:password]
    end
  end

  test "DATABASE_URL_TEST cannot bypass TEST partition construction" do
    environment =
      empty_env(@test_env_vars, "test", "17")
      |> Map.put("DATABASE_URL_TEST", "postgresql://ignored.invalid/ignored")

    repo_config = read_repo_config("test.exs", :test, environment)

    assert repo_config[:database] == "ticketing_test17"
    refute Keyword.has_key?(repo_config, :url)
  end

  test "TEST defaults to its isolated local allocation" do
    repo_config = read_repo_config("test.exs", :test, empty_env(@test_env_vars, "test"))

    assert repo_config[:hostname] == "127.0.0.1"
    assert repo_config[:port] == 55_433
    assert repo_config[:username] == "ticketing_test_runtime"
    assert repo_config[:database] == "ticketing_test"
    refute Keyword.has_key?(repo_config, :url)
  end

  test "TEST config rejects a database base outside the Ticketing namespace" do
    environment = empty_env(@test_env_vars, "test", nil, nil, "some_other_database")

    assert_raise ArgumentError, ~r/TICKETING_TEST_DB_NAME.*ticketing_test/, fn ->
      read_repo_config("test.exs", :test, environment)
    end
  end

  test "TEST Repo requires its local password variable" do
    environment =
      empty_env(@test_env_vars, "test")
      |> Map.put("TICKETING_TEST_RUNTIME_DB_PASSWORD", nil)

    assert_raise System.EnvError, fn ->
      read_repo_config("test.exs", :test, environment)
    end
  end

  test "TEST config rejects the local DEV port" do
    assert_raise ArgumentError, ~r/TEST.*55432/, fn ->
      read_repo_config("test.exs", :test, empty_env(@test_env_vars, "test", nil, "55432"))
    end
  end

  test "TEST config rejects the DEV database" do
    assert_raise ArgumentError, ~r/TEST.*ticketing_dev/, fn ->
      read_repo_config(
        "test.exs",
        :test,
        empty_env(@test_env_vars, "test", nil, nil, "ticketing_dev")
      )
    end
  end

  test "Ticketing does not require a Redis client" do
    direct_dependencies = Enum.map(Mix.Project.config()[:deps], &elem(&1, 0))

    refute Enum.any?(direct_dependencies, &(&1 in [:redix, :eredis]))
  end

  defp empty_env(vars, profile, partition \\ nil, port \\ nil, database \\ nil) do
    vars
    |> Map.new(&{&1, nil})
    |> Map.put("TICKETING_#{String.upcase(profile)}_DB_PASSWORD", "owner-test-password")
    |> Map.put("TICKETING_#{String.upcase(profile)}_RUNTIME_DB_PASSWORD", "runtime-test-password")
    |> maybe_put("MIX_TEST_PARTITION", partition)
    |> maybe_put("TICKETING_#{String.upcase(profile)}_DB_PORT", port)
    |> maybe_put("TICKETING_#{String.upcase(profile)}_DB_NAME", database)
  end

  defp maybe_put(environment, _key, nil), do: environment
  defp maybe_put(environment, key, value), do: Map.put(environment, key, value)

  defp read_repo_config(file, config_env, environment) do
    read_repo_configs(file, config_env, environment).runtime
  end

  defp read_repo_configs(file, config_env, environment) do
    config_path = Path.expand("../../config/#{file}", __DIR__)

    with_system_env(environment, fn ->
      config = Config.Reader.read!(config_path, env: config_env)

      %{
        runtime: get_in(config, [:ticketing, Ticketing.Repo]),
        migration: get_in(config, [:ticketing, Ticketing.MigrationRepo])
      }
    end)
  end

  defp read_runtime_repo_configs(environment) do
    config_path = Path.expand("../../config/runtime.exs", __DIR__)

    with_system_env(environment, fn ->
      config = Config.Reader.read!(config_path, env: :prod)

      %{
        runtime: get_in(config, [:ticketing, Ticketing.Repo]),
        migration: get_in(config, [:ticketing, Ticketing.MigrationRepo])
      }
    end)
  end

  defp with_system_env(environment, callback) do
    original_environment =
      Map.new(environment, fn {key, _value} -> {key, System.get_env(key)} end)

    Enum.each(environment, fn
      {key, nil} -> System.delete_env(key)
      {key, value} -> System.put_env(key, value)
    end)

    try do
      callback.()
    after
      Enum.each(original_environment, fn
        {key, nil} -> System.delete_env(key)
        {key, value} -> System.put_env(key, value)
      end)
    end
  end
end

defmodule Ticketing.RepoSmokeTest do
  use Ticketing.DataCase, async: false

  alias Ecto.Adapters.SQL

  test "the TEST database has all nine Ash helper functions" do
    assert %{rows: [[9]]} =
             SQL.query!(
               Ticketing.Repo,
               """
               SELECT count(*)
               FROM pg_proc AS p
               JOIN pg_namespace AS n ON n.oid = p.pronamespace
               WHERE n.nspname = 'public'
                 AND p.proname IN (
                   'ash_elixir_or',
                   'ash_elixir_and',
                   'ash_trim_whitespace',
                   'ash_raise_error',
                   'ash_required',
                   'uuid_generate_v7'
                 )
               """,
               []
             )
  end

  test "runtime Repo uses the TEST allocation and reaches PostgreSQL 18" do
    repo_config = Application.fetch_env!(:ticketing, Ticketing.Repo)
    test_base = System.get_env("TICKETING_TEST_DB_NAME", "ticketing_test")
    partition = System.get_env("MIX_TEST_PARTITION", "")
    expected_database = test_base <> partition

    assert repo_config[:hostname] == System.get_env("TICKETING_TEST_DB_HOST", "127.0.0.1")

    assert repo_config[:port] ==
             String.to_integer(System.get_env("TICKETING_TEST_DB_PORT", "55433"))

    refute repo_config[:port] == 55_432
    assert repo_config[:database] == expected_database
    refute repo_config[:database] == "ticketing_dev"

    assert repo_config[:username] ==
             System.get_env("TICKETING_TEST_RUNTIME_DB_USER", "ticketing_test_runtime")

    assert is_binary(repo_config[:password])
    refute Keyword.has_key?(repo_config, :url)

    assert %{rows: [[^expected_database, server_version_num]]} =
             SQL.query!(
               Ticketing.Repo,
               "SELECT current_database(), current_setting('server_version_num')::integer",
               []
             )

    assert div(server_version_num, 10_000) == 18
  end
end
