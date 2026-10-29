defmodule Ticketing.Events.T001IntegrationInvariantsTest do
  use ExUnit.Case, async: false

  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.Events
  alias Ticketing.Identity.Actor
  alias Ticketing.Identity.OwnerFixtures
  alias Ticketing.MigrationRepo
  alias Ticketing.Platform.TenantContext
  alias Ticketing.TenantContextTestRepo

  @org_a "11111111-1111-4111-8111-111111111111"
  @org_b "22222222-2222-4222-8222-222222222222"
  @user_a "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  @user_b "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
  @membership_a "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
  @membership_b "cccccccc-cccc-4ccc-8ccc-dddddddddddd"
  @session_a "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
  @session_b "dddddddd-dddd-4ddd-8ddd-eeeeeeeeeeee"
  @role_a "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
  @role_b "eeeeeeee-eeee-4eee-8eee-ffffffffffff"
  @runtime_repo Ticketing.T001IntegrationRepo

  setup do
    reset_state!()
    start_runtime_repo!()
    Ticketing.Repo.put_dynamic_repo(@runtime_repo)
    on_exit(fn -> Ticketing.Repo.put_dynamic_repo(Ticketing.Repo) end)
    :ok
  end

  test "organizer proof failure matrix leaves no Event and does not mutate Session state" do
    cases = [
      {"missing-membership", [membership?: false]},
      {"mismatched-membership", [membership_org_id: @org_b]},
      {"inactive-membership", [membership_status: "inactive"]},
      {"revoked-membership", [membership_revoked_at_utc: DateTime.utc_now()]},
      {"missing-session", [session?: false]},
      {"mismatched-session", [session_org_id: @org_b]},
      {"inactive-session", [session_status: "inactive"]},
      {"revoked-session", [session_revoked_at_utc: DateTime.utc_now()]},
      {"expired-session",
       [session_expires_at_utc: DateTime.add(DateTime.utc_now(), -60, :second)]},
      {"missing-role", [role?: false]},
      {"mismatched-role", [persisted_role: "box_office", requested_role: "org_admin"]},
      {"inactive-role", [role_status: "inactive"]},
      {"revoked-role", [role_revoked_at: DateTime.utc_now()]},
      {"invalid-scope", [active_scope: "invalid"]},
      {"mixed-scope", [active_scope: "org+platform"]}
    ]

    for {label, opts} <- cases do
      reset_state!()
      {actor, requested_role, active_scope} = seed_failure_case!(opts)
      sessions_before = session_snapshots()

      assert {:error, _error} =
               create_event(actor,
                 org_id: @org_a,
                 role: requested_role,
                 active_scope: active_scope,
                 slug: "tick28-#{label}"
               ),
             "expected #{label} to fail closed"

      assert tenant_event_count(@org_a, "tick28-#{label}") == 0
      assert tenant_event_count(@org_b, "tick28-#{label}") == 0
      assert session_snapshots() == sessions_before
    end
  end

  test "successful Event creation clears tenant context before pooled backend reuse" do
    actor = seed_complete_identity!(@org_a, @user_a, @membership_a, @session_a, @role_a)

    assert %Postgrex.Result{rows: [[backend_pid_before]]} =
             runtime_query!("SELECT pg_backend_pid()", [])

    assert {:ok, event} =
             create_event(actor,
               org_id: @org_a,
               role: "org_admin",
               active_scope: "org",
               slug: "tick28-commit-cleanup"
             )

    assert event.org_id == @org_a

    assert %Postgrex.Result{rows: [[backend_pid_after, tenant_setting, visible_rows]]} =
             runtime_query!(
               """
               SELECT pg_backend_pid(),
                      current_setting('app.current_org_id', true),
                      count(*)::integer
               FROM events
               """,
               []
             )

    assert backend_pid_after == backend_pid_before
    assert tenant_setting in [nil, ""]
    assert visible_rows == 0
    assert tenant_event_count(@org_a, "tick28-commit-cleanup") == 1
  end

  test "proof failure clears tenant context before pooled backend reuse" do
    {actor, requested_role, active_scope} = seed_failure_case!(session?: false)

    assert %Postgrex.Result{rows: [[backend_pid_before]]} =
             runtime_query!("SELECT pg_backend_pid()", [])

    assert {:error, _error} =
             create_event(actor,
               org_id: @org_a,
               role: requested_role,
               active_scope: active_scope,
               slug: "tick28-proof-rollback"
             )

    assert %Postgrex.Result{rows: [[backend_pid_after, tenant_setting, visible_rows]]} =
             runtime_query!(
               """
               SELECT pg_backend_pid(),
                      current_setting('app.current_org_id', true),
                      count(*)::integer
               FROM events
               """,
               []
             )

    assert backend_pid_after == backend_pid_before
    assert tenant_setting in [nil, ""]
    assert visible_rows == 0
    assert tenant_event_count(@org_a, "tick28-proof-rollback") == 0
  end

  test "exception rollback clears tenant context before pooled backend reuse" do
    assert %Postgrex.Result{rows: [[backend_pid_before]]} =
             runtime_query!("SELECT pg_backend_pid()", [])

    assert_raise RuntimeError, "tick28-exception", fn ->
      Ticketing.Repo.transaction(fn ->
        assert :ok = TenantContext.put_current_org!(@org_a)

        assert %Postgrex.Result{rows: [[^backend_pid_before, @org_a]]} =
                 runtime_query!(
                   "SELECT pg_backend_pid(), current_setting('app.current_org_id', true)",
                   []
                 )

        raise "tick28-exception"
      end)
    end

    assert %Postgrex.Result{rows: [[backend_pid_after, tenant_setting, visible_rows]]} =
             runtime_query!(
               """
               SELECT pg_backend_pid(),
                      current_setting('app.current_org_id', true),
                      count(*)::integer
               FROM events
               """,
               []
             )

    assert backend_pid_after == backend_pid_before
    assert tenant_setting in [nil, ""]
    assert visible_rows == 0
  end

  test "real tenant tables enforce direct-SQL isolation under the constrained runtime role" do
    actor_a = seed_complete_identity!(@org_a, @user_a, @membership_a, @session_a, @role_a)
    actor_b = seed_complete_identity!(@org_b, @user_b, @membership_b, @session_b, @role_b)

    assert {:ok, event_a} =
             create_event(actor_a,
               org_id: @org_a,
               role: "org_admin",
               active_scope: "org",
               slug: "tick28-org-a"
             )

    assert {:ok, event_b} =
             create_event(actor_b,
               org_id: @org_b,
               role: "org_admin",
               active_scope: "org",
               slug: "tick28-org-b"
             )

    assert %Postgrex.Result{rows: [[runtime_user, false, false, event_owner]]} =
             runtime_query!(
               """
               SELECT current_user,
                      role.rolsuper,
                      role.rolbypassrls,
                      relation.relowner::regrole::text
               FROM pg_catalog.pg_roles AS role
               CROSS JOIN pg_catalog.pg_class AS relation
               WHERE role.rolname = current_user
                 AND relation.oid = to_regclass('public.events')::oid
               """,
               []
             )

    refute runtime_user == event_owner

    assert {:error,
            {:rls_evidence, 0, 0, 0, 0, 0,
             %Postgrex.Error{postgres: %{code: :insufficient_privilege, message: message}}}} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = TenantContext.put_current_org!(@org_a)

               assert %Postgrex.Result{rows: [[event_rows]]} =
                        runtime_query!(
                          "SELECT count(*)::integer FROM events WHERE event_id = $1::uuid",
                          [uuid!(event_b.event_id)]
                        )

               assert %Postgrex.Result{rows: [[membership_rows]]} =
                        runtime_query!(
                          """
                          SELECT count(*)::integer
                          FROM identity_org_memberships
                          WHERE org_membership_id = $1::uuid
                          """,
                          [uuid!(@membership_b)]
                        )

               assert %Postgrex.Result{rows: [[session_rows]]} =
                        runtime_query!(
                          "SELECT count(*)::integer FROM identity_sessions WHERE id = $1::uuid",
                          [uuid!(@session_b)]
                        )

               assert %Postgrex.Result{rows: [[role_rows]]} =
                        runtime_query!(
                          """
                          SELECT count(*)::integer
                          FROM identity_org_role_assignments
                          WHERE role_assignment_id = $1::uuid
                          """,
                          [uuid!(@role_b)]
                        )

               assert %Postgrex.Result{num_rows: cross_tenant_updates} =
                        runtime_query!(
                          "UPDATE events SET slug = $1 WHERE event_id = $2::uuid",
                          ["tick28-forbidden-update", uuid!(event_b.event_id)]
                        )

               case SQL.query(
                      @runtime_repo,
                      "UPDATE events SET org_id = $1::uuid WHERE event_id = $2::uuid",
                      [uuid!(@org_b), uuid!(event_a.event_id)]
                    ) do
                 {:error, error} ->
                   Ticketing.Repo.rollback(
                     {:rls_evidence, event_rows, membership_rows, session_rows, role_rows,
                      cross_tenant_updates, error}
                   )

                 {:ok, result} ->
                   Ticketing.Repo.rollback(
                     {:rls_write_unexpectedly_allowed, result.num_rows}
                   )
               end
             end)

    assert message =~ "row-level security policy"
    assert tenant_event_count(@org_a, "tick28-org-a") == 1
    assert tenant_event_count(@org_b, "tick28-org-b") == 1
    assert tenant_event_count(@org_b, "tick28-forbidden-update") == 0
  end

  defp seed_failure_case!(opts) do
    OwnerFixtures.insert_user!(%{id: @user_a})

    if Keyword.get(opts, :membership?, true) do
      OwnerFixtures.insert_org_membership!(%{
        org_membership_id: @membership_a,
        org_id: Keyword.get(opts, :membership_org_id, @org_a),
        user_id: @user_a,
        status: Keyword.get(opts, :membership_status, "active"),
        revoked_at_utc: Keyword.get(opts, :membership_revoked_at_utc)
      })
    end

    if Keyword.get(opts, :session?, true) do
      OwnerFixtures.insert_session!(%{
        id: @session_a,
        org_id: Keyword.get(opts, :session_org_id, @org_a),
        user_id: @user_a,
        token_hash: "tick28-test-only-secret",
        status: Keyword.get(opts, :session_status, "active"),
        expires_at_utc:
          Keyword.get_lazy(opts, :session_expires_at_utc, fn ->
            DateTime.add(DateTime.utc_now(), 3600, :second)
          end),
        revoked_at_utc: Keyword.get(opts, :session_revoked_at_utc)
      })
    end

    if Keyword.get(opts, :role?, true) do
      OwnerFixtures.insert_org_role_assignment!(%{
        role_assignment_id: @role_a,
        org_id: @org_a,
        user_id: @user_a,
        role: Keyword.get(opts, :persisted_role, "org_admin"),
        status: Keyword.get(opts, :role_status, "active"),
        revoked_at: Keyword.get(opts, :role_revoked_at)
      })
    end

    {
      Actor.authenticated_session(@user_a, @session_a),
      Keyword.get(opts, :requested_role, "org_admin"),
      Keyword.get(opts, :active_scope, "org")
    }
  end

  defp seed_complete_identity!(org_id, user_id, membership_id, session_id, role_id) do
    OwnerFixtures.insert_user!(%{id: user_id})

    OwnerFixtures.insert_org_membership!(%{
      org_membership_id: membership_id,
      org_id: org_id,
      user_id: user_id
    })

    OwnerFixtures.insert_session!(%{
      id: session_id,
      org_id: org_id,
      user_id: user_id,
      token_hash: "tick28-test-only-secret"
    })

    OwnerFixtures.insert_org_role_assignment!(%{
      role_assignment_id: role_id,
      org_id: org_id,
      user_id: user_id,
      role: "org_admin"
    })

    Actor.authenticated_session(user_id, session_id)
  end

  defp create_event(actor, opts) do
    org_id = Keyword.fetch!(opts, :org_id)
    role = Keyword.fetch!(opts, :role)
    active_scope = Keyword.fetch!(opts, :active_scope)
    slug = Keyword.fetch!(opts, :slug)

    Events.create_event(
      %{
        org_id: org_id,
        active_scope: active_scope,
        active_role: role,
        slug: slug,
        visibility: "public",
        default_locale: "en",
        supported_locales: ["en"],
        featured: false,
        taxonomy_refs: [],
        request_id: "req-#{slug}",
        trace_id: "trace-#{slug}"
      },
      actor: actor
    )
  end

  defp session_snapshots do
    %{
      @org_a => session_snapshot(@org_a),
      @org_b => session_snapshot(@org_b)
    }
  end

  defp session_snapshot(org_id) do
    assert {:error, {:session_snapshot, rows}} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = TenantContext.put_current_org!(org_id)

               assert %Postgrex.Result{rows: rows} =
                        runtime_query!(
                          """
                          SELECT id::text,
                                 org_id::text,
                                 user_id::text,
                                 status,
                                 created_at_utc,
                                 expires_at_utc,
                                 revoked_at_utc,
                                 last_seen_at_utc
                          FROM identity_sessions
                          ORDER BY id
                          """,
                          []
                        )

               Ticketing.Repo.rollback({:session_snapshot, rows})
             end)

    rows
  end

  defp tenant_event_count(org_id, slug) do
    assert {:error, {:event_count, count}} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = TenantContext.put_current_org!(org_id)

               assert %Postgrex.Result{rows: [[count]]} =
                        runtime_query!(
                          "SELECT count(*)::integer FROM events WHERE slug = $1",
                          [slug]
                        )

               Ticketing.Repo.rollback({:event_count, count})
             end)

    count
  end

  defp runtime_query!(query, params) do
    SQL.query!(@runtime_repo, query, params)
  end

  defp start_runtime_repo! do
    repo_config =
      Ticketing.Repo.config()
      |> Keyword.put(:pool, DBConnection.ConnectionPool)
      |> Keyword.put(:pool_size, 1)
      |> Keyword.put(:name, @runtime_repo)

    start_supervised!({TenantContextTestRepo, repo_config}, id: @runtime_repo)
  end

  defp reset_state! do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               SQL.query!(repo, "TRUNCATE TABLE events", [])
             end)

    :ok = OwnerFixtures.reset_identity_tables!()
  end

  defp uuid!(value), do: Ecto.UUID.dump!(value)
end
