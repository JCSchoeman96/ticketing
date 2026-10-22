defmodule Ticketing.Platform.TenantContextTest do
  use ExUnit.Case, async: false

  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.MigrationRepo
  alias Ticketing.Platform.DatabasePrivileges
  alias Ticketing.Platform.TenantContext
  alias Ticketing.TenantContextTestDomain
  alias Ticketing.TenantContextTestRepo
  alias Ticketing.TenantContextTestResource

  @fixture_table "t0_01_tenant_context_fixture"
  @tenant_a "11111111-1111-4111-8111-111111111111"
  @tenant_b "22222222-2222-4222-8222-222222222222"
  @row_a "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  @row_b "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

  setup_all do
    on_exit(&drop_fixture_table!/0)
    create_fixture_table!()
    :ok
  end

  setup do
    repo_config =
      Ticketing.Repo.config()
      |> Keyword.put(:pool, DBConnection.ConnectionPool)
      |> Keyword.put(:pool_size, 1)
      |> Keyword.put(:name, TenantContextTestRepo)

    _repo_pid = start_supervised!({TenantContextTestRepo, repo_config})
    Ticketing.Repo.put_dynamic_repo(TenantContextTestRepo)
    assert Ticketing.Repo.get_dynamic_repo() == TenantContextTestRepo
    on_exit(fn -> Ticketing.Repo.put_dynamic_repo(Ticketing.Repo) end)
    :ok
  end

  test "rejects a tenant context outside an explicit Repo transaction" do
    assert_raise ArgumentError, fn ->
      put_current_org!(@tenant_a)
    end

    assert %Postgrex.Result{rows: [[nil]]} =
             runtime_query!("SELECT current_setting('app.current_org_id', true)", [])
  end

  test "validates tenant UUID input before setting PostgreSQL context" do
    assert {:ok, _} =
             Ticketing.Repo.transaction(fn ->
               assert_raise ArgumentError, fn ->
                 put_current_org!("not-a-uuid")
               end

               assert %Postgrex.Result{rows: [[setting]]} =
                        runtime_query!(
                          "SELECT current_setting('app.current_org_id', true)",
                          []
                        )

               assert is_nil(setting)
               :ok
             end)
  end

  test "sets the tenant on the same backend as subsequent tenant SQL" do
    assert {:error, {pid_before, setting, pid_after, row_ids}} =
             Ticketing.Repo.transaction(fn ->
               assert %Postgrex.Result{rows: [[pid_before]]} =
                        runtime_query!("SELECT pg_backend_pid()", [])

               assert :ok = put_current_org!(@tenant_a)

               assert %Postgrex.Result{rows: [[setting, pid_after]]} =
                        runtime_query!(
                          "SELECT current_setting('app.current_org_id', true), pg_backend_pid()",
                          []
                        )

               assert %Postgrex.Result{rows: rows} =
                        runtime_query!(
                          "SELECT id FROM public.#{@fixture_table} ORDER BY id",
                          []
                        )

               row_ids = Enum.map(rows, fn [id] -> id end)
               Ticketing.Repo.rollback({pid_before, setting, pid_after, row_ids})
             end)

    assert pid_before == pid_after
    assert setting == @tenant_a
    assert Enum.map(row_ids, &uuid_load!/1) == [@row_a]
  end

  test "Ash installs its explicit tenant before its transactional read" do
    test_pid = self()

    query =
      Ash.Query.for_read(TenantContextTestResource, :read, %{},
        domain: TenantContextTestDomain,
        tenant: @tenant_a
      )
      |> Ash.Query.before_action(fn query ->
        assert %Postgrex.Result{rows: [[backend_pid, tenant_setting]]} =
                 runtime_query!(
                   "SELECT pg_backend_pid(), current_setting('app.current_org_id', true)",
                   []
                 )

        send(test_pid, {:tenant_read_context, backend_pid, tenant_setting})
        query
      end)

    rows = Ash.read!(query, domain: TenantContextTestDomain)

    assert_receive {:tenant_read_context, backend_pid, @tenant_a}
    assert is_integer(backend_pid)

    assert Enum.map(rows, & &1.id) == [@row_a]
  end

  test "Ash attribute tenancy filters independently while RLS permits another tenant" do
    assert {:error, {:ash_rows, []}} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = put_current_org!(@tenant_b)

               assert %Postgrex.Result{rows: [[row_b]]} =
                        runtime_query!(
                          "SELECT id FROM public.#{@fixture_table} WHERE org_id = $1::uuid",
                          [uuid!(@tenant_b)]
                        )

               assert uuid_load!(row_b) == @row_b

               query =
                 Ash.Query.for_read(TenantContextTestResource, :read_without_transaction, %{},
                   domain: TenantContextTestDomain,
                   tenant: @tenant_a
                 )

               rows = Ash.read!(query, domain: TenantContextTestDomain)
               Ticketing.Repo.rollback({:ash_rows, Enum.map(rows, & &1.id)})
             end)
  end

  test "RLS catalog state includes ENABLE, FORCE, and tenant USING and WITH CHECK policy" do
    assert %Postgrex.Result{rows: [[server_version]]} =
             runtime_query!("SELECT current_setting('server_version')", [])

    assert server_version =~ ~r/^18\.6(?:\s|$)/

    assert %Postgrex.Result{
             rows: [[runtime_user, false, false, false, false, fixture_owner]]
           } =
             runtime_query!(
               """
               SELECT current_user,
                      role.rolsuper,
                      role.rolbypassrls,
                      role.rolcreatedb,
                      role.rolcreaterole,
                      relation.relowner::regrole::text
               FROM pg_catalog.pg_roles AS role
               CROSS JOIN pg_catalog.pg_class AS relation
               WHERE role.rolname = current_user
                 AND relation.oid = to_regclass($1)::oid
               """,
               ["public.#{@fixture_table}"]
             )

    assert runtime_user == "ticketing_test_runtime"
    refute runtime_user == fixture_owner
    assert fixture_owner == migration_fixture_owner!()

    assert %Postgrex.Result{rows: [[true, true]]} =
             runtime_query!(
               """
               SELECT relrowsecurity, relforcerowsecurity
               FROM pg_catalog.pg_class
               WHERE oid = to_regclass($1)::oid
               """,
               ["public.#{@fixture_table}"]
             )

    assert %Postgrex.Result{rows: [[policy_name, using_expression, check_expression]]} =
             runtime_query!(
               """
               SELECT policy.polname,
                      pg_get_expr(policy.polqual, policy.polrelid),
                      pg_get_expr(policy.polwithcheck, policy.polrelid)
               FROM pg_catalog.pg_policy AS policy
               WHERE policy.polrelid = to_regclass($1)::oid
               """,
               ["public.#{@fixture_table}"]
             )

    assert policy_name == "tenant_context_isolation"
    assert String.downcase(using_expression) =~ "org_id"
    assert String.downcase(check_expression) =~ "org_id"

    assert String.downcase(using_expression) =~
             "current_setting('app.current_org_id'::text, true)"

    assert String.downcase(check_expression) =~
             "current_setting('app.current_org_id'::text, true)"

    assert String.downcase(using_expression) =~ "nullif"
    assert String.downcase(check_expression) =~ "nullif"
  end

  test "RLS hides rows and rejects writes without tenant context" do
    assert %Postgrex.Result{rows: [[0]]} =
             runtime_query!(
               "SELECT count(*)::integer FROM public.#{@fixture_table}",
               []
             )

    assert {:error,
            {:denied,
             %Postgrex.Error{postgres: %{code: :insufficient_privilege, message: message}}}} =
             Ticketing.Repo.transaction(fn ->
               case runtime_query(
                      "INSERT INTO public.#{@fixture_table} (id, org_id, value) VALUES ($1::uuid, $2::uuid, $3)",
                      [uuid!("cccccccc-cccc-4ccc-8ccc-cccccccccccc"), uuid!(@tenant_a), 3]
                    ) do
                 {:error, error} -> Ticketing.Repo.rollback({:denied, error})
                 {:ok, result} -> Ticketing.Repo.rollback({:allowed, result.num_rows})
               end
             end)

    assert message =~ "row-level security policy"
  end

  test "tenant A reads and updates A but cannot read or update B" do
    assert {:error, {:tenant_a_rows, [@row_a], 1, 0}} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = put_current_org!(@tenant_a)

               assert %Postgrex.Result{rows: rows} =
                        runtime_query!(
                          "SELECT id FROM public.#{@fixture_table} ORDER BY id",
                          []
                        )

               assert %Postgrex.Result{num_rows: updated_a} =
                        runtime_query!(
                          "UPDATE public.#{@fixture_table} SET value = $1 WHERE id = $2::uuid",
                          [11, uuid!(@row_a)]
                        )

               assert %Postgrex.Result{num_rows: updated_b} =
                        runtime_query!(
                          "UPDATE public.#{@fixture_table} SET value = $1 WHERE id = $2::uuid",
                          [22, uuid!(@row_b)]
                        )

               Ticketing.Repo.rollback(
                 {:tenant_a_rows, Enum.map(rows, fn [id] -> uuid_load!(id) end), updated_a,
                  updated_b}
               )
             end)
  end

  test "WITH CHECK rejects inserts and org_id changes to another tenant" do
    for operation <- [
          fn ->
            runtime_query(
              "INSERT INTO public.#{@fixture_table} (id, org_id, value) VALUES ($1::uuid, $2::uuid, $3)",
              [uuid!("cccccccc-cccc-4ccc-8ccc-cccccccccccc"), uuid!(@tenant_b), 4]
            )
          end,
          fn ->
            runtime_query(
              "UPDATE public.#{@fixture_table} SET org_id = $1::uuid WHERE id = $2::uuid",
              [uuid!(@tenant_b), uuid!(@row_a)]
            )
          end
        ] do
      assert {:error,
              {:denied,
               %Postgrex.Error{postgres: %{code: :insufficient_privilege, message: message}}}} =
               Ticketing.Repo.transaction(fn ->
                 assert :ok = put_current_org!(@tenant_a)

                 case operation.() do
                   {:error, error} -> Ticketing.Repo.rollback({:denied, error})
                   {:ok, result} -> Ticketing.Repo.rollback({:allowed, result.num_rows})
                 end
               end)

      assert message =~ "row-level security policy"
    end
  end

  test "FORCE RLS constrains an ordinary migration owner and catalogs the flag for every owner" do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               assert %Postgrex.Result{
                        rows: [
                          [owner, owner_superuser, owner_bypass_rls, fixture_owner, true, true]
                        ]
                      } =
                        SQL.query!(
                          repo,
                          """
                          SELECT current_user,
                                 role.rolsuper,
                                 role.rolbypassrls,
                                 relation.relowner::regrole::text,
                                 relation.relrowsecurity,
                                 relation.relforcerowsecurity
                          FROM pg_catalog.pg_roles AS role
                          CROSS JOIN pg_catalog.pg_class AS relation
                          WHERE role.rolname = current_user
                            AND relation.oid = to_regclass($1)::oid
                          """,
                          ["public.#{@fixture_table}"]
                        )

               assert fixture_owner == owner

               visible_rows =
                 SQL.query!(
                   repo,
                   "SELECT count(*)::integer FROM public.#{@fixture_table}",
                   []
                 )

               case {owner_superuser, owner_bypass_rls} do
                 {false, false} -> assert %Postgrex.Result{rows: [[0]]} = visible_rows
                 _bypass_role -> assert %Postgrex.Result{rows: [[2]]} = visible_rows
               end
             end)
  end

  test "commit clears tenant authority before a later pooled borrower" do
    assert {:ok, pid_after_set} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = put_current_org!(@tenant_a)

               assert %Postgrex.Result{rows: [[pid, @tenant_a]]} =
                        runtime_query!(
                          "SELECT pg_backend_pid(), current_setting('app.current_org_id', true)",
                          []
                        )

               pid
             end)

    assert_same_backend_has_no_tenant_and_rejects_writes(pid_after_set)
  end

  test "rollback clears tenant authority before a later pooled borrower" do
    assert {:error, {:rolled_back, pid_after_set}} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = put_current_org!(@tenant_b)

               assert %Postgrex.Result{rows: [[pid, @tenant_b]]} =
                        runtime_query!(
                          "SELECT pg_backend_pid(), current_setting('app.current_org_id', true)",
                          []
                        )

               Ticketing.Repo.rollback({:rolled_back, pid})
             end)

    assert_same_backend_has_no_tenant_and_rejects_writes(pid_after_set)
  end

  defp assert_same_backend_has_no_tenant_and_rejects_writes(previous_pid) do
    borrower =
      Task.async(fn ->
        Ticketing.Repo.put_dynamic_repo(TenantContextTestRepo)

        Ticketing.Repo.transaction(fn ->
          assert %Postgrex.Result{rows: [[backend_pid, setting, visible_rows]]} =
                   runtime_query!(
                     """
                     SELECT pg_backend_pid(),
                            current_setting('app.current_org_id', true),
                            count(*)::integer
                     FROM public.#{@fixture_table}
                     """,
                     []
                   )

          insert_result =
            runtime_query(
              "INSERT INTO public.#{@fixture_table} (id, org_id, value) VALUES ($1::uuid, $2::uuid, $3)",
              [
                uuid!("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
                uuid!(@tenant_a),
                3
              ]
            )

          rollback_expired_context_write(backend_pid, setting, visible_rows, insert_result)
        end)
      end)

    assert {:error,
            {:expired_empty_context_write_denied, ^previous_pid, "", 0,
             %Postgrex.Error{postgres: %{code: :insufficient_privilege, message: message}}}} =
             Task.await(borrower)

    assert message =~ "row-level security policy"
  end

  defp rollback_expired_context_write(backend_pid, setting, visible_rows, insert_result) do
    case insert_result do
      {:error, error} ->
        Ticketing.Repo.rollback(
          {:expired_empty_context_write_denied, backend_pid, setting, visible_rows, error}
        )

      {:ok, result} ->
        Ticketing.Repo.rollback(
          {:expired_empty_context_write_allowed, backend_pid, setting, visible_rows,
           result.num_rows}
        )
    end
  end

  defp put_current_org!(org_id) do
    TenantContext.put_current_org!(org_id)
  end

  defp runtime_query!(query, params) do
    SQL.query!(Ticketing.Repo.get_dynamic_repo(), query, params)
  end

  defp runtime_query(query, params) do
    SQL.query(Ticketing.Repo.get_dynamic_repo(), query, params)
  end

  defp uuid!(value), do: Ecto.UUID.dump!(value)
  defp uuid_load!(value), do: Ecto.UUID.load!(value)

  defp migration_fixture_owner! do
    assert {:ok, {migration_user, fixture_owner}, _repo} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               assert %Postgrex.Result{rows: [[migration_user, fixture_owner]]} =
                        SQL.query!(
                          repo,
                          """
                          SELECT current_user,
                                 relation.relowner::regrole::text
                          FROM pg_catalog.pg_class AS relation
                          WHERE relation.oid = to_regclass($1)::oid
                          """,
                          ["public.#{@fixture_table}"]
                        )

               {migration_user, fixture_owner}
             end)

    assert migration_user == fixture_owner
    fixture_owner
  end

  defp create_fixture_table! do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               SQL.query!(repo, "DROP TABLE IF EXISTS public.#{@fixture_table}", [])

               SQL.query!(
                 repo,
                 """
                 CREATE TABLE public.#{@fixture_table} (
                   id uuid PRIMARY KEY,
                   org_id uuid NOT NULL,
                   value integer NOT NULL
                 )
                 """,
                 []
               )

               SQL.query!(
                 repo,
                 """
                 INSERT INTO public.#{@fixture_table} (id, org_id, value)
                 VALUES ($1::uuid, $2::uuid, $3)
                 """,
                 [uuid!(@row_a), uuid!(@tenant_a), 1]
               )

               SQL.query!(
                 repo,
                 """
                 INSERT INTO public.#{@fixture_table} (id, org_id, value)
                 VALUES ($1::uuid, $2::uuid, $3)
                 """,
                 [uuid!(@row_b), uuid!(@tenant_b), 2]
               )

               :ok = DatabasePrivileges.apply!(repo)

               SQL.query!(
                 repo,
                 "ALTER TABLE public.#{@fixture_table} ENABLE ROW LEVEL SECURITY",
                 []
               )

               SQL.query!(
                 repo,
                 "ALTER TABLE public.#{@fixture_table} FORCE ROW LEVEL SECURITY",
                 []
               )

               SQL.query!(
                 repo,
                 """
                 CREATE POLICY tenant_context_isolation ON public.#{@fixture_table}
                 FOR ALL
                 USING (
                   org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
                 )
                 WITH CHECK (
                   org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
                 )
                 """,
                 []
               )
             end)
  end

  defp drop_fixture_table! do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               SQL.query!(repo, "DROP TABLE IF EXISTS public.#{@fixture_table}", [])
             end)
  end
end
