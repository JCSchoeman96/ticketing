defmodule Ticketing.RepoConfigTest do
  use ExUnit.Case, async: false

  @dev_env_vars ~w(
    TICKETING_DEV_DB_HOST
    TICKETING_DEV_DB_PORT
    TICKETING_DEV_DB_USER
    TICKETING_DEV_DB_PASSWORD
    TICKETING_DEV_DB_NAME
    DATABASE_URL
  )

  @test_env_vars ~w(
    TICKETING_TEST_DB_HOST
    TICKETING_TEST_DB_PORT
    TICKETING_TEST_DB_USER
    TICKETING_TEST_DB_PASSWORD
    TICKETING_TEST_DB_NAME
    DATABASE_URL_TEST
    MIX_TEST_PARTITION
  )

  test "development Repo defaults to the documented DEV allocation" do
    environment =
      empty_env(@dev_env_vars, "dev")
      |> Map.put("DATABASE_URL", "postgresql://ignored.invalid/ignored")

    repo_config = read_repo_config("dev.exs", :dev, environment)

    assert repo_config[:hostname] == "127.0.0.1"
    assert repo_config[:port] == 55432
    assert repo_config[:username] == "ticketing_dev"
    assert repo_config[:database] == "ticketing_dev"
    assert is_binary(repo_config[:password])
    refute repo_config[:show_sensitive_data_on_connection_error]
    refute Keyword.has_key?(repo_config, :url)
  end

  test "development Repo requires its local password variable" do
    environment =
      empty_env(@dev_env_vars, "dev")
      |> Map.put("TICKETING_DEV_DB_PASSWORD", nil)

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
      refute Keyword.has_key?(repo_config, :url)
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
    assert repo_config[:port] == 55433
    assert repo_config[:username] == "ticketing_test"
    assert repo_config[:database] == "ticketing_test"
    refute Keyword.has_key?(repo_config, :url)
  end

  test "TEST Repo requires its local password variable" do
    environment =
      empty_env(@test_env_vars, "test")
      |> Map.put("TICKETING_TEST_DB_PASSWORD", nil)

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
    |> Map.put("TICKETING_#{String.upcase(profile)}_DB_PASSWORD", "not-a-real-password")
    |> maybe_put("MIX_TEST_PARTITION", partition)
    |> maybe_put("TICKETING_#{String.upcase(profile)}_DB_PORT", port)
    |> maybe_put("TICKETING_#{String.upcase(profile)}_DB_NAME", database)
  end

  defp maybe_put(environment, _key, nil), do: environment
  defp maybe_put(environment, key, value), do: Map.put(environment, key, value)

  defp read_repo_config(file, config_env, environment) do
    config_path = Path.expand("../../config/#{file}", __DIR__)

    with_system_env(environment, fn ->
      config_path
      |> Config.Reader.read!(env: config_env)
      |> get_in([:ticketing, Ticketing.Repo])
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

  test "the TEST database has all nine Ash helper functions" do
    assert %{rows: [[9]]} =
             Ecto.Adapters.SQL.query!(
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

  test "Repo uses the TEST components and reaches the expected PostgreSQL 18 database" do
    repo_config = Application.fetch_env!(:ticketing, Ticketing.Repo)
    test_base = System.get_env("TICKETING_TEST_DB_NAME", "ticketing_test")
    partition = System.get_env("MIX_TEST_PARTITION", "")
    expected_database = test_base <> partition

    assert repo_config[:hostname] == System.get_env("TICKETING_TEST_DB_HOST", "127.0.0.1")

    assert repo_config[:port] ==
             String.to_integer(System.get_env("TICKETING_TEST_DB_PORT", "55433"))

    refute repo_config[:port] == 55432
    assert repo_config[:database] == expected_database
    refute repo_config[:database] == "ticketing_dev"
    assert repo_config[:username] == System.get_env("TICKETING_TEST_DB_USER", "ticketing_test")
    assert is_binary(repo_config[:password])
    refute Keyword.has_key?(repo_config, :url)

    assert %{rows: [[^expected_database, server_version_num]]} =
             Ecto.Adapters.SQL.query!(
               Ticketing.Repo,
               "SELECT current_database(), current_setting('server_version_num')::integer",
               []
             )

    assert div(server_version_num, 10_000) == 18
  end
end
