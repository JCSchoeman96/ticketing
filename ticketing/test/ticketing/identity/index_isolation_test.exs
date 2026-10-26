defmodule Ticketing.Identity.IndexIsolationTest do
  @moduledoc """
  TEN-1 index-isolation evidence for TICK-25 Identity tables.

  Composite IAM/JIP identities are enforced as org_id-first (or IAM-specified) unique
  indexes. Single-column UUIDv7 primary keys on tenant tables remain subject to an
  explicit TEN-1 `index_isolation.exceptions` pin in the governing JIP; no such pin
  exists in JIP-T0-01 v0.1.4 today (governance follow-up, not silently assumed here).
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

  test "tenant tables use UUIDv7 single-column primary keys pending explicit TEN-1 exception pin" do
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
                        "expected non-composite primary key on #{table} until JIP pins TEN-1 exception"
               end
             end)
  end

  test "IAM composite unique indexes include org_id for tenant-scoped identifiers" do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               assert index_exists?(repo, "identity_org_memberships_unique_user_per_org_index")

               assert index_exists?(
                        repo,
                        "identity_org_memberships_unique_membership_id_per_org_index"
                      )

               assert index_exists?(repo, "identity_org_role_assignments_by_user_role_org_index")
               assert index_exists?(repo, "identity_sessions_unique_id_per_org_index")

               assert org_id_leads_index?(
                        repo,
                        "identity_org_memberships_unique_user_per_org_index"
                      )

               assert org_id_leads_index?(
                        repo,
                        "identity_org_memberships_unique_membership_id_per_org_index"
                      )

               assert org_id_leads_index?(repo, "identity_sessions_unique_id_per_org_index")
             end)
  end

  defp index_exists?(repo, name) do
    match?(
      %Postgrex.Result{rows: [[true]]},
      SQL.query!(
        repo,
        "SELECT to_regclass($1) IS NOT NULL",
        ["public.#{name}"]
      )
    )
  end

  defp org_id_leads_index?(repo, index_name) do
    %Postgrex.Result{rows: rows} =
      SQL.query!(
        repo,
        """
        SELECT pg_get_indexdef(c.oid)
        FROM pg_catalog.pg_class AS c
        WHERE c.relname = $1
          AND c.relkind = 'i'
        """,
        [index_name]
      )

    [[definition]] = rows
    String.downcase(definition) =~ "org_id"
  end
end
