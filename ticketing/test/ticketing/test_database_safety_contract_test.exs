defmodule Ticketing.TestDatabaseSafetyContractTest do
  use ExUnit.Case, async: true

  @database_mutations %{
    setup: [
      "ecto.migrate -r Ticketing.MigrationRepo",
      "ticketing.db.grant_runtime_privileges"
    ],
    "ecto.setup": [
      "ecto.create -r Ticketing.MigrationRepo",
      "ecto.migrate -r Ticketing.MigrationRepo",
      "ticketing.db.grant_runtime_privileges"
    ],
    test: [
      "ecto.create -r Ticketing.MigrationRepo --quiet",
      "ecto.migrate -r Ticketing.MigrationRepo --quiet",
      "ticketing.db.grant_runtime_privileges"
    ]
  }

  test "TEST setup and verification aliases guard before every database mutation" do
    aliases = Mix.Project.config() |> Keyword.fetch!(:aliases)

    for {alias_name, mutation_steps} <- @database_mutations do
      steps = Keyword.fetch!(aliases, alias_name)
      guard_index = Enum.find_index(steps, &(&1 == "ticketing.test_database.guard"))

      assert is_integer(guard_index), "#{alias_name} must include the TEST database guard"

      if alias_name == :setup do
        assert hd(steps) == "deps.get", "setup must fetch dependencies before loading local tasks"

        assert Enum.find_index(steps, &(&1 == "deps.get")) < guard_index
      else
        assert hd(steps) == "ticketing.test_database.guard",
               "#{alias_name} must fail closed before any TEST database work"
      end

      mutation_indexes =
        Enum.map(mutation_steps, &Enum.find_index(steps, fn step -> step == &1 end))

      assert Enum.all?(mutation_indexes, &is_integer/1),
             "#{alias_name} must retain its database steps"

      assert Enum.all?(mutation_indexes, &(&1 > guard_index)),
             "#{alias_name} must guard before database work"
    end
  end

  test "precommit and check still enter the guarded TEST alias" do
    aliases = Mix.Project.config() |> Keyword.fetch!(:aliases)

    assert "test" in Keyword.fetch!(aliases, :precommit)
    assert "test" in Keyword.fetch!(aliases, :check)
  end
end
