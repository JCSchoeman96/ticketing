defmodule Ticketing.Events.EventSchemaContractTest do
  use ExUnit.Case, async: false

  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.MigrationRepo

  test "Event version fences use canonical int32 PostgreSQL columns" do
    assert {:ok, rows, _repo} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               assert %Postgrex.Result{rows: rows} =
                        SQL.query!(
                          repo,
                          """
                          SELECT column_name, data_type
                          FROM information_schema.columns
                          WHERE table_schema = 'public'
                            AND table_name = 'events'
                            AND column_name IN ('version', 'lock_version')
                          ORDER BY column_name
                          """,
                          []
                        )

               rows
             end)

    assert rows == [["lock_version", "integer"], ["version", "integer"]]
  end
end
