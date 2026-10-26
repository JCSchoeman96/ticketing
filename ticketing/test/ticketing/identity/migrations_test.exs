defmodule Ticketing.Identity.MigrationsTest do
  use ExUnit.Case, async: false

  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.MigrationRepo

  @tenant_tables ~w(
    identity_org_memberships
    identity_org_role_assignments
    identity_sessions
  )

  test "identity tenant tables have FORCE RLS and tenant_context_isolation policy" do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               for table <- @tenant_tables do
                 assert %Postgrex.Result{rows: [[true, true]]} =
                          SQL.query!(
                            repo,
                            """
                            SELECT relrowsecurity, relforcerowsecurity
                            FROM pg_catalog.pg_class
                            WHERE oid = to_regclass($1)::oid
                            """,
                            ["public.#{table}"]
                          )

                 assert %Postgrex.Result{rows: [[policy_name | _]]} =
                          SQL.query!(
                            repo,
                            """
                            SELECT policy.polname
                            FROM pg_catalog.pg_policy AS policy
                            WHERE policy.polrelid = to_regclass($1)::oid
                            """,
                            ["public.#{table}"]
                          )

                 assert policy_name == "tenant_context_isolation"
               end
             end)
  end

  test "identity_users has no row level security enabled" do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               assert %Postgrex.Result{rows: [[false, false]]} =
                        SQL.query!(
                          repo,
                          """
                          SELECT relrowsecurity, relforcerowsecurity
                          FROM pg_catalog.pg_class
                          WHERE oid = 'public.identity_users'::regclass
                          """
                        )
             end)
  end

  test "migration does not recreate generic b0 RLS substrate" do
    migration_path =
      Path.expand(
        "priv/repo/migrations/20261025200030_tick25_identity_resources.exs",
        File.cwd!()
      )

    contents = File.read!(migration_path)

    refute contents =~ "t0_01_tenant_context_fixture"
    refute contents =~ "DROP POLICY tenant_context_isolation ON public"
  end
end
