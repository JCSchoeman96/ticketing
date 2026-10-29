defmodule Ticketing.Events.CreateEventTransactionTest do
  use ExUnit.Case, async: false

  alias Ash.Resource.Info
  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.Events
  alias Ticketing.Events.Event
  alias Ticketing.Identity.Actor
  alias Ticketing.Identity.OwnerFixtures
  alias Ticketing.MigrationRepo
  alias Ticketing.Platform.TenantContext
  alias Ticketing.TenantContextTestRepo

  @org_id "11111111-1111-4111-8111-111111111111"
  @user_id "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  @membership_id "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
  @session_id "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
  @role_assignment_id "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
  @runtime_repo_a Ticketing.EventCreateTransactionRepoA
  @runtime_repo_b Ticketing.EventCreateTransactionRepoB

  setup do
    reset_events!()
    :ok = OwnerFixtures.reset_identity_tables!()
    actor = seed_identity!()

    start_runtime_repo!(@runtime_repo_a)
    Ticketing.Repo.put_dynamic_repo(@runtime_repo_a)

    %{actor: actor}
  end

  test "public create_event surface cannot author protected Event fields", %{actor: actor} do
    create_event_action =
      Event
      |> Info.public_actions()
      |> Enum.find(&(&1.name == :create_event))

    argument_names = Enum.map(create_event_action.arguments, & &1.name)
    accepted_fields = create_event_action.accept

    protected_fields = [
      :org_id,
      :event_id,
      :public_event_key,
      :status,
      :version,
      :lock_version,
      :created_at_utc,
      :updated_at_utc,
      :published_at_utc,
      :archived_at_utc
    ]

    refute Enum.any?(protected_fields, &(&1 in argument_names))
    refute Enum.any?(protected_fields, &(&1 in accepted_fields))

    event_id = Ash.UUIDv7.generate()
    now = DateTime.utc_now()

    assert {:error, _error} =
             Ash.create(
               Event,
               %{
                 org_id: @org_id,
                 event_id: event_id,
                 public_event_key: "evt_" <> String.replace(event_id, "-", ""),
                 slug: "caller-protected-fields",
                 visibility: "public",
                 status: "published",
                 default_locale: "en",
                 supported_locales: ["en"],
                 featured: false,
                 taxonomy_refs: [],
                 version: 7,
                 lock_version: 7,
                 created_at_utc: now,
                 updated_at_utc: now,
                 published_at_utc: now,
                 archived_at_utc: now,
                 active_scope: "org",
                 active_role: "org_admin",
                 request_id: "req-protected-fields",
                 trace_id: "trace-protected-fields"
               },
               action: :create_event,
               actor: actor,
               authorize?: true,
               tenant: @org_id,
               domain: Events
             )

    assert tenant_event_count(@runtime_repo_a, "caller-protected-fields") == 0
  end

  test "Event timestamps are database-generated rather than application-clock defaults" do
    for attribute_name <- [:created_at_utc, :updated_at_utc] do
      attribute = Info.attribute(Event, attribute_name)

      assert attribute.generated?
      assert is_nil(attribute.default)
      refute attribute.writable?
    end
  end

  test "duplicate Event failure rolls back tenant context before pooled backend reuse", %{
    actor: actor
  } do
    assert {:ok, _event} = create_event(actor, "rollback-cleanup")
    assert tenant_event_count(@runtime_repo_a, "rollback-cleanup") == 1
    session_before = session_snapshot(@runtime_repo_a)

    assert %Postgrex.Result{rows: [[backend_pid_before]]} =
             SQL.query!(@runtime_repo_a, "SELECT pg_backend_pid()", [])

    assert {:error, _error} = create_event(actor, "rollback-cleanup")

    assert %Postgrex.Result{rows: [[backend_pid_after, tenant_setting, visible_rows]]} =
             SQL.query!(
               @runtime_repo_a,
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
    assert tenant_event_count(@runtime_repo_a, "rollback-cleanup") == 1
    assert session_snapshot(@runtime_repo_a) == session_before
  end

  test "concurrent same-tenant slug creation has exactly one database-constrained winner", %{
    actor: actor
  } do
    start_runtime_repo!(@runtime_repo_b)
    parent = self()
    release_ref = make_ref()

    task_a = race_task(parent, release_ref, @runtime_repo_a, actor)
    task_b = race_task(parent, release_ref, @runtime_repo_b, actor)

    {task_pid_a, backend_pid_a} = await_race_ready()
    {task_pid_b, backend_pid_b} = await_race_ready()

    refute backend_pid_a == backend_pid_b

    send(task_pid_a, {:release_event_race, release_ref})
    send(task_pid_b, {:release_event_race, release_ref})

    results = [Task.await(task_a, 10_000), Task.await(task_b, 10_000)]

    assert Enum.count(results, &match?({:ok, _event}, &1)) == 1
    assert Enum.count(results, &match?({:error, _error}, &1)) == 1
    assert tenant_event_count(@runtime_repo_a, "concurrent-slug") == 1
  end

  defp race_task(parent, release_ref, repo_name, actor) do
    Task.async(fn ->
      Ticketing.Repo.put_dynamic_repo(repo_name)

      assert %Postgrex.Result{rows: [[backend_pid]]} =
               SQL.query!(repo_name, "SELECT pg_backend_pid()", [])

      send(parent, {:event_race_ready, self(), backend_pid})

      receive do
        {:release_event_race, ^release_ref} -> create_event(actor, "concurrent-slug")
      after
        5_000 -> flunk("timed out waiting to release concurrent Event creation")
      end
    end)
  end

  defp await_race_ready do
    assert_receive {:event_race_ready, task_pid, backend_pid}, 5_000
    {task_pid, backend_pid}
  end

  defp start_runtime_repo!(repo_name) do
    repo_config =
      Ticketing.Repo.config()
      |> Keyword.put(:pool, DBConnection.ConnectionPool)
      |> Keyword.put(:pool_size, 1)
      |> Keyword.put(:name, repo_name)

    start_supervised!({TenantContextTestRepo, repo_config}, id: repo_name)
  end

  defp seed_identity! do
    OwnerFixtures.insert_user!(%{id: @user_id})

    OwnerFixtures.insert_org_membership!(%{
      org_membership_id: @membership_id,
      org_id: @org_id,
      user_id: @user_id
    })

    OwnerFixtures.insert_session!(%{
      id: @session_id,
      org_id: @org_id,
      user_id: @user_id,
      token_hash: "test-only-secret"
    })

    OwnerFixtures.insert_org_role_assignment!(%{
      role_assignment_id: @role_assignment_id,
      org_id: @org_id,
      user_id: @user_id,
      role: "org_admin"
    })

    Actor.authenticated_session(@user_id, @session_id)
  end

  defp create_event(actor, slug) do
    Events.create_event(
      %{
        org_id: @org_id,
        active_scope: "org",
        active_role: "org_admin",
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

  defp tenant_event_count(repo_name, slug) do
    Ticketing.Repo.put_dynamic_repo(repo_name)

    assert {:error, {:event_count, count}} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = TenantContext.put_current_org!(@org_id)

               assert %Postgrex.Result{rows: [[count]]} =
                        SQL.query!(
                          repo_name,
                          "SELECT count(*)::integer FROM events WHERE slug = $1",
                          [slug]
                        )

               Ticketing.Repo.rollback({:event_count, count})
             end)

    count
  end

  defp session_snapshot(repo_name) do
    Ticketing.Repo.put_dynamic_repo(repo_name)

    assert {:error, {:session_snapshot, snapshot}} =
             Ticketing.Repo.transaction(fn ->
               assert :ok = TenantContext.put_current_org!(@org_id)

               assert %Postgrex.Result{rows: [snapshot]} =
                        SQL.query!(
                          repo_name,
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
                          """,
                          []
                        )

               Ticketing.Repo.rollback({:session_snapshot, snapshot})
             end)

    snapshot
  end

  defp reset_events! do
    assert {:ok, _, _} =
             Migrator.with_repo(MigrationRepo, fn repo ->
               SQL.query!(repo, "TRUNCATE TABLE events", [])
             end)

    :ok
  end
end
