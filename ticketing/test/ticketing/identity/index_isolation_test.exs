defmodule Ticketing.Identity.IndexIsolationTest do
  @moduledoc """
  TEN-1 index-isolation evidence for TICK-25 Identity tables.

  Composite IAM/JIP identities are enforced with org_id as the leading index column
  where tenant isolation requires it. JIP-T0-01 v0.1.5 and SPEC-T0-01 v0.1.4
  explicitly select the narrow TEN-1 physical-primary-key exception for
  `identity_org_memberships(org_membership_id)`, `identity_sessions(id)`, and
  `identity_org_role_assignments(role_assignment_id)` only.
  """

  use ExUnit.Case, async: false

  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.MigrationRepo

  @tenant_tables ~w(
    identity_org_memberships
    identity_org_role_assignments
    identity_sessions
  )

  test "tenant tables retain the UUIDv7 single-column physical primary keys selected under TEN-1" do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               for table <- @tenant_tables do
                 assert %Postgrex.Result{rows: [[column_name]]} =
                          SQL.query!(
                            repo,
                            """
                            SELECT a.attname
                            FROM pg_catalog.pg_index i
                            JOIN pg_catalog.pg_attribute a
                              ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                            WHERE i.indrelid = to_regclass($1)::oid
                              AND i.indisprimary
                            """,
                            ["public.#{table}"]
                          )

                 refute column_name == "org_id",
                        "expected the selected single-column TEN-1 physical primary key on #{table}"
               end
             end)
  end

  test "IAM composite unique indexes use org_id-first column order in PostgreSQL" do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               assert_index_columns!(
                 repo,
                 "identity_org_memberships_unique_user_per_org_index",
                 ["org_id", "user_id"]
               )

               assert_index_columns!(
                 repo,
                 "identity_org_memberships_unique_membership_id_per_org_index",
                 ["org_id", "org_membership_id"]
               )

               assert_index_columns!(
                 repo,
                 "identity_org_role_assignments_by_user_role_org_index",
                 ["org_id", "user_id", "role"]
               )

               assert_index_columns!(
                 repo,
                 "identity_sessions_unique_id_per_org_index",
                 ["org_id", "id"]
               )
             end)
  end

  defp assert_index_columns!(repo, index_name, expected_columns) do
    columns = index_column_names(repo, index_name)

    assert columns == expected_columns,
           "expected index #{index_name} columns #{inspect(expected_columns)}, got #{inspect(columns)}"

    assert List.first(columns) == "org_id",
           "expected org_id as first column on tenant isolation index #{index_name}"
  end

  defp index_column_names(repo, index_name) do
    %Postgrex.Result{rows: rows} =
      SQL.query!(
        repo,
        """
        SELECT a.attname
        FROM pg_catalog.pg_class AS ic
        JOIN pg_catalog.pg_index AS idx ON idx.indexrelid = ic.oid
        JOIN LATERAL unnest(idx.indkey) WITH ORDINALITY AS key(attnum, ord) ON true
        JOIN pg_catalog.pg_attribute AS a
          ON a.attrelid = idx.indrelid
         AND a.attnum = key.attnum
         AND NOT a.attisdropped
        WHERE ic.relname = $1
          AND ic.relkind = 'i'
        ORDER BY key.ord
        """,
        [index_name]
      )

    Enum.map(rows, fn [name] -> name end)
  end
end
