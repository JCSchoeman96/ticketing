defmodule Ticketing.RepoSmokeTest do
  use Ticketing.DataCase, async: false

  test "the application Repo executes a PostgreSQL query" do
    assert %{rows: [[1]]} = Ecto.Adapters.SQL.query!(Ticketing.Repo, "SELECT 1", [])
  end

  test "test database configuration uses the documented local PostgreSQL port" do
    test_url = Application.fetch_env!(:ticketing, Ticketing.Repo)[:url]

    if System.get_env("DATABASE_URL_TEST") do
      assert test_url == System.get_env("DATABASE_URL_TEST")
      assert %URI{scheme: "postgresql", path: "/ticketing_test"} = URI.parse(test_url)
    else
      assert %URI{scheme: "postgresql", host: "localhost", port: 5433, path: "/ticketing_test"} =
               URI.parse(test_url)
    end

    dev_config = Config.Reader.read!(Path.expand("../../config/dev.exs", __DIR__), env: :dev)
    dev_url = get_in(dev_config, [:ticketing, Ticketing.Repo, :url])

    if System.get_env("DATABASE_URL") do
      assert dev_url == System.get_env("DATABASE_URL")
      assert %URI{scheme: "postgresql", path: "/ticketing_dev"} = URI.parse(dev_url)
    else
      assert %URI{scheme: "postgresql", host: "localhost", port: 5433, path: "/ticketing_dev"} =
               URI.parse(dev_url)
    end

    compose = File.read!(Path.expand("../../../compose.yml", __DIR__))
    assert compose =~ "5433:5432"
    refute compose =~ "5432:5432"
  end
end
