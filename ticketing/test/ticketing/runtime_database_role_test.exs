defmodule Ticketing.RuntimeDatabaseRoleTest do
  use Ticketing.DataCase, async: false

  alias Ecto.Adapters.SQL

  test "ordinary TEST Repo uses the distinct constrained runtime role" do
    runtime_config = Application.fetch_env!(:ticketing, Ticketing.Repo)

    owner_user =
      System.get_env(
        "TICKETING_TEST_MIGRATION_DB_USER",
        System.get_env("TICKETING_TEST_DB_USER", "ticketing_test")
      )

    expected_runtime_user =
      System.get_env("TICKETING_TEST_RUNTIME_DB_USER", "ticketing_test_runtime")

    assert %{
             rows: [
               [
                 current_user,
                 can_login,
                 superuser,
                 bypass_rls,
                 createdb,
                 createrole,
                 owner_member,
                 privileged_member,
                 owned_tables
               ]
             ]
           } =
             SQL.query!(
               Ticketing.Repo,
               """
               SELECT current_user,
                      role.rolcanlogin,
                      role.rolsuper,
                      role.rolbypassrls,
                      role.rolcreatedb,
                      role.rolcreaterole,
                      pg_has_role(current_user, $1::name, 'MEMBER'),
                      EXISTS (
                        SELECT 1
                        FROM pg_roles AS inherited_role
                        WHERE pg_has_role(current_user, inherited_role.oid, 'MEMBER')
                          AND (
                            inherited_role.rolsuper
                            OR inherited_role.rolbypassrls
                            OR inherited_role.rolcreatedb
                            OR inherited_role.rolcreaterole
                          )
                      ),
                      (
                        SELECT count(*)::integer
                        FROM pg_class AS owned_relation
                        JOIN pg_namespace AS namespace
                          ON namespace.oid = owned_relation.relnamespace
                        WHERE owned_relation.relkind IN ('r', 'p')
                          AND namespace.nspname NOT IN ('pg_catalog', 'information_schema')
                          AND owned_relation.relowner = role.oid
                      )
               FROM pg_roles AS role
               WHERE role.rolname = current_user
               """,
               [owner_user]
             )

    assert current_user == expected_runtime_user
    refute current_user == owner_user
    assert current_user == runtime_config[:username]
    assert can_login
    refute superuser
    refute bypass_rls
    refute createdb
    refute createrole
    refute owner_member
    refute privileged_member
    assert owned_tables == 0
  end

  test "local TEST owner retains only its approved cluster role flags" do
    owner_user =
      System.get_env(
        "TICKETING_TEST_MIGRATION_DB_USER",
        System.get_env("TICKETING_TEST_DB_USER", "ticketing_test")
      )

    if owner_user == "ticketing_test" do
      assert %{
               rows: [
                 [superuser, createdb, createrole, bypass_rls, inherited_privileged_role]
               ]
             } =
               SQL.query!(
                 Ticketing.Repo,
                 """
                 SELECT owner.rolsuper,
                        owner.rolcreatedb,
                        owner.rolcreaterole,
                        owner.rolbypassrls,
                        EXISTS (
                          SELECT 1
                          FROM pg_roles AS inherited_role
                          WHERE pg_has_role(owner.rolname, inherited_role.oid, 'MEMBER')
                            AND (
                              inherited_role.rolsuper
                              OR inherited_role.rolcreaterole
                              OR inherited_role.rolbypassrls
                            )
                        )
                 FROM pg_roles AS owner
                 WHERE owner.rolname = $1
                 """,
                 [owner_user]
               )

      refute superuser
      assert createdb
      refute createrole
      refute bypass_rls
      refute inherited_privileged_role
    end
  end
end
