defmodule Ticketing.RepoPoolConfigTest do
  use ExUnit.Case, async: false

  test "TEST Repo uses a fixed pool size of ten" do
    config_path = Path.expand("../../config/test.exs", __DIR__)

    repo_config =
      config_path
      |> Config.Reader.read!(env: :test)
      |> get_in([:ticketing, Ticketing.Repo])

    assert repo_config[:pool_size] == 10
  end
end
