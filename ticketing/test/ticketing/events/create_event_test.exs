defmodule Ticketing.Events.CreateEventTest do
  use Ticketing.DataCase, async: false

  alias Ash.Resource.Info
  alias Ash.Type.UUID
  alias Ecto.Adapters.SQL
  alias Ticketing.Events
  alias Ticketing.Events.Event
  alias Ticketing.Identity.Actor
  alias Ticketing.Identity.Authorization
  alias Ticketing.Identity.OwnerFixtures

  @org_id "11111111-1111-4111-8111-111111111111"
  @other_org_id "22222222-2222-4222-8222-222222222222"
  @user_id "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  @other_user_id "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
  @membership_id "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
  @session_id "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
  @role_assignment_id "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"

  setup do
    :ok = OwnerFixtures.reset_identity_tables!()
    :ok
  end

  test "only the complete create_event effect is public" do
    event_actions = Event |> Info.public_actions() |> Enum.map(& &1.name)

    authorization_actions =
      Authorization |> Info.public_actions() |> Enum.map(& &1.name)

    assert :create_event in event_actions
    refute :persist_draft in event_actions
    refute :authorize_event_create in authorization_actions
    refute function_exported?(Ticketing.Identity, :authorize_event_create, 8)
  end

  test "a fabricated organizer persona cannot invoke an alternate Event write action" do
    event_id = Ash.UUIDv7.generate()

    fabricated_persona = %{
      actor_kind: "human",
      capability: "evt.event.create",
      org_id: @org_id,
      user_id: "forged",
      session_id: "forged",
      org_membership_id: "forged",
      role: "org_admin"
    }

    assert_raise ArgumentError, ~r/No such create action.*persist_draft/s, fn ->
      Ash.transact(
        Event,
        fn ->
          Ash.create(
            Event,
            %{
              org_id: @org_id,
              event_id: event_id,
              public_event_key: "evt_" <> String.replace(event_id, "-", ""),
              slug: "forged-internal-event",
              visibility: "public",
              default_locale: "en",
              supported_locales: ["en"],
              featured: false,
              taxonomy_refs: []
            },
            action: :persist_draft,
            actor: fabricated_persona,
            tenant: @org_id,
            authorize?: true,
            domain: Events
          )
        end,
        tenant: @org_id
      )
    end

    action_names = Event |> Info.actions() |> Enum.map(& &1.name)
    assert action_names == [:create_event]

    assert event_count(@org_id, "forged-internal-event") == 0
  end

  test "a fabricated human organizer actor cannot skip persisted proof through create_event" do
    fabricated_persona = %{
      actor_kind: "human",
      capability: "evt.event.create",
      org_id: @org_id,
      user_id: @user_id,
      session_id: @session_id,
      org_membership_id: @membership_id,
      role: "org_admin"
    }

    assert {:error, _error} =
             Ash.create(
               Event,
               %{
                 slug: "forged-action-event",
                 visibility: "public",
                 default_locale: "en",
                 supported_locales: ["en"],
                 featured: false,
                 taxonomy_refs: [],
                 active_scope: "org",
                 active_role: "org_admin",
                 request_id: "req-forged-action-event",
                 trace_id: "trace-forged-action-event"
               },
               action: :create_event,
               actor: fabricated_persona,
               authorize?: true,
               tenant: @org_id,
               domain: Events
             )

    assert event_count(@org_id, "forged-action-event") == 0
  end

  test "authorized org_admin creates one tenant-owned canonical draft Event" do
    actor = seed_identity!(role: "org_admin")

    assert {:ok, event} = create_event(actor, role: "org_admin", slug: "launch-night")

    assert event.org_id == @org_id
    assert is_binary(event.event_id)
    assert {:ok, _} = UUID.cast_input(event.event_id, [])
    assert String.at(event.event_id, 14) == "7"
    assert is_binary(event.public_event_key)
    assert String.length(event.public_event_key) in 24..64
    assert event.public_event_key == "evt_" <> String.replace(event.event_id, "-", "")
    assert event.slug == "launch-night"
    assert event.visibility == "public"
    assert event.default_locale == "en"
    assert event.supported_locales == ["en"]
    assert event.featured == false
    assert event.taxonomy_refs == []
    assert event.status == "draft"
    assert event.version == 1
    assert event.lock_version == 1
    assert is_nil(event.published_at_utc)
    assert is_nil(event.archived_at_utc)
    assert %DateTime{} = event.created_at_utc
    assert %DateTime{} = event.updated_at_utc
    assert event_count(@org_id, "launch-night") == 1
  end

  test "authorized org_owner can create a draft Event" do
    actor = seed_identity!(role: "org_owner")

    assert {:ok, event} = create_event(actor, role: "org_owner", slug: "owner-event")
    assert event.status == "draft"
    assert event_count(@org_id, "owner-event") == 1
  end

  test "membership proof precedes liveness and Event persistence on one PostgreSQL backend" do
    actor = seed_identity!(role: "org_admin")
    handler_id = attach_repo_query_probe()

    assert {:ok, _event} = create_event(actor, role: "org_admin", slug: "ordered-create")

    queries = drain_repo_queries()
    :telemetry.detach(handler_id)

    relevant = relevant_business_queries(queries)
    labels = Enum.map(relevant, &elem(&1, 0))

    assert index_of!(labels, :membership) < index_of!(labels, :user)
    assert index_of!(labels, :membership) < index_of!(labels, :session)
    assert index_of!(labels, :membership) < index_of!(labels, :role_assignment)
    assert index_of!(labels, :role_assignment) < index_of!(labels, :event)

    connection_ids = relevant |> Enum.map(&elem(&1, 1)) |> Enum.reject(&is_nil/1) |> Enum.uniq()
    assert [_single_backend_pid] = connection_ids

    tenant_context_transitions =
      Enum.filter(queries, fn {query, _connection_id} ->
        String.contains?(query, "set_config('app.current_org_id'")
      end)

    assert [_single_tenant_context_transition] = tenant_context_transitions
  end

  test "candidate org_id without membership proof performs no later business reads" do
    actor = seed_identity!(role: "org_admin")
    handler_id = attach_repo_query_probe()

    assert {:error, %Ash.Error.Invalid{errors: errors}} =
             create_event(actor,
               org_id: @other_org_id,
               role: "org_admin",
               slug: "cross-tenant-forgery"
             )

    assert Enum.any?(errors, &match?(%Ash.Error.Query.NotFound{}, &1))

    queries = drain_repo_queries()
    :telemetry.detach(handler_id)

    labels = queries |> relevant_business_queries() |> Enum.map(&elem(&1, 0))

    assert :membership in labels
    refute :user in labels
    refute :session in labels
    refute :role_assignment in labels
    refute :event in labels
    assert event_count(@other_org_id, "cross-tenant-forgery") == 0
  end

  test "inactive membership fails closed" do
    actor = seed_identity!(role: "org_admin", membership_status: "inactive")

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "inactive-member")
    assert event_count(@org_id, "inactive-member") == 0
  end

  test "revoked membership fails closed" do
    actor = seed_identity!(role: "org_admin", membership_revoked_at_utc: DateTime.utc_now())

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "revoked-member")
    assert event_count(@org_id, "revoked-member") == 0
  end

  test "membership proof must match the authenticated user" do
    actor = seed_identity!(role: "org_admin", membership_user_id: @other_user_id)

    assert {:error, %Ash.Error.Invalid{errors: errors}} =
             create_event(actor, role: "org_admin", slug: "mismatched-membership-user")

    assert Enum.any?(errors, &match?(%Ash.Error.Query.NotFound{}, &1))

    assert event_count(@org_id, "mismatched-membership-user") == 0
  end

  test "disabled user fails liveness after membership proof" do
    actor = seed_identity!(role: "org_admin", user_status: "disabled")

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "disabled-user")
    assert event_count(@org_id, "disabled-user") == 0
  end

  test "expired session fails DB-time liveness" do
    actor =
      seed_identity!(
        role: "org_admin",
        session_expires_at_utc: DateTime.add(DateTime.utc_now(), -60, :second)
      )

    handler_id = attach_repo_query_probe()

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "expired-session")

    queries = drain_repo_queries()
    :telemetry.detach(handler_id)

    assert Enum.any?(queries, fn {query, _connection_id} ->
             normalized_query = String.downcase(query)

             String.contains?(normalized_query, "identity_sessions") and
               String.contains?(normalized_query, "now() at time zone 'utc'")
           end)

    assert event_count(@org_id, "expired-session") == 0
  end

  test "inactive session fails liveness" do
    actor = seed_identity!(role: "org_admin", session_status: "inactive")

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "inactive-session")
    assert event_count(@org_id, "inactive-session") == 0
  end

  test "revoked session fails liveness" do
    actor = seed_identity!(role: "org_admin", session_revoked_at_utc: DateTime.utc_now())

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "revoked-session")
    assert event_count(@org_id, "revoked-session") == 0
  end

  test "session evidence must match the authenticated user" do
    actor = seed_identity!(role: "org_admin", session_user_id: @other_user_id)

    assert {:error, _error} =
             create_event(actor, role: "org_admin", slug: "mismatched-session-user")

    assert event_count(@org_id, "mismatched-session-user") == 0
  end

  test "session evidence must match the proven organization" do
    actor = seed_identity!(role: "org_admin", session_org_id: @other_org_id)

    assert {:error, _error} =
             create_event(actor, role: "org_admin", slug: "mismatched-session-org")

    assert event_count(@org_id, "mismatched-session-org") == 0
  end

  test "role assignment must match the authenticated user" do
    actor = seed_identity!(role: "org_admin", role_user_id: @other_user_id)

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "mismatched-role-user")
    assert event_count(@org_id, "mismatched-role-user") == 0
  end

  test "role assignment must match the proven organization" do
    actor = seed_identity!(role: "org_admin", role_org_id: @other_org_id)

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "mismatched-role-org")
    assert event_count(@org_id, "mismatched-role-org") == 0
  end

  test "inactive role assignment fails closed" do
    actor = seed_identity!(role: "org_admin", role_status: "inactive")

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "inactive-role")
    assert event_count(@org_id, "inactive-role") == 0
  end

  test "revoked role assignment fails closed" do
    actor = seed_identity!(role: "org_admin", role_revoked_at: DateTime.utc_now())

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "revoked-role")
    assert event_count(@org_id, "revoked-role") == 0
  end

  test "forged active role is rejected when persisted assignment does not match" do
    actor = seed_identity!(role: "box_office")

    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "forged-role")
    assert event_count(@org_id, "forged-role") == 0
  end

  test "platform_support cannot satisfy the organizer Event-create capability" do
    actor = seed_identity!(role: "platform_support")

    assert {:error, _error} =
             create_event(actor,
               role: "platform_support",
               slug: "support-persona"
             )

    assert event_count(@org_id, "support-persona") == 0
  end

  test "non-org active scope is rejected" do
    actor = seed_identity!(role: "org_admin")

    assert {:error, _error} =
             create_event(actor,
               active_scope: "platform",
               role: "org_admin",
               slug: "platform-scope"
             )

    assert event_count(@org_id, "platform-scope") == 0
  end

  test "invalid active scope is rejected" do
    actor = seed_identity!(role: "org_admin")

    assert {:error, _error} =
             create_event(actor,
               active_scope: "invalid",
               role: "org_admin",
               slug: "invalid-scope"
             )

    assert event_count(@org_id, "invalid-scope") == 0
  end

  test "mixed active scope is rejected" do
    actor = seed_identity!(role: "org_admin")

    assert {:error, _error} =
             create_event(actor,
               active_scope: "org+platform",
               role: "org_admin",
               slug: "mixed-scope"
             )

    assert event_count(@org_id, "mixed-scope") == 0
  end

  test "duplicate tenant slug is rejected by the database identity" do
    actor = seed_identity!(role: "org_admin")

    assert {:ok, _event} = create_event(actor, role: "org_admin", slug: "same-slug")
    assert {:error, _error} = create_event(actor, role: "org_admin", slug: "same-slug")
    assert event_count(@org_id, "same-slug") == 1
  end

  defp seed_identity!(opts) do
    role = Keyword.fetch!(opts, :role)

    [
      Keyword.get(opts, :membership_user_id, @user_id),
      Keyword.get(opts, :session_user_id, @user_id),
      Keyword.get(opts, :role_user_id, @user_id)
    ]
    |> Enum.uniq()
    |> Enum.reject(&(&1 == @user_id))
    |> Enum.each(fn user_id -> OwnerFixtures.insert_user!(%{id: user_id}) end)

    OwnerFixtures.insert_user!(%{
      id: @user_id,
      status: Keyword.get(opts, :user_status, "active")
    })

    OwnerFixtures.insert_org_membership!(%{
      org_membership_id: @membership_id,
      org_id: Keyword.get(opts, :membership_org_id, @org_id),
      user_id: Keyword.get(opts, :membership_user_id, @user_id),
      status: Keyword.get(opts, :membership_status, "active"),
      revoked_at_utc: Keyword.get(opts, :membership_revoked_at_utc)
    })

    OwnerFixtures.insert_session!(%{
      id: @session_id,
      org_id: Keyword.get(opts, :session_org_id, @org_id),
      user_id: Keyword.get(opts, :session_user_id, @user_id),
      token_hash: "test-only-secret",
      status: Keyword.get(opts, :session_status, "active"),
      expires_at_utc:
        Keyword.get_lazy(opts, :session_expires_at_utc, fn ->
          DateTime.add(DateTime.utc_now(), 3600, :second)
        end),
      revoked_at_utc: Keyword.get(opts, :session_revoked_at_utc)
    })

    OwnerFixtures.insert_org_role_assignment!(%{
      role_assignment_id: @role_assignment_id,
      org_id: Keyword.get(opts, :role_org_id, @org_id),
      user_id: Keyword.get(opts, :role_user_id, @user_id),
      role: role,
      status: Keyword.get(opts, :role_status, "active"),
      revoked_at: Keyword.get(opts, :role_revoked_at)
    })

    Actor.authenticated_session(@user_id, @session_id)
  end

  defp create_event(actor, opts) do
    org_id = Keyword.get(opts, :org_id, @org_id)
    active_scope = Keyword.get(opts, :active_scope, "org")
    role = Keyword.fetch!(opts, :role)
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

  defp attach_repo_query_probe do
    handler_id = "tick26-repo-query-#{System.unique_integer([:positive])}"
    test_pid = self()

    :ok =
      :telemetry.attach(
        handler_id,
        [:ticketing, :repo, :query],
        fn _event, _measurements, metadata, pid ->
          connection_id =
            case metadata.result do
              {:ok, %Postgrex.Result{connection_id: connection_id}} -> connection_id
              _other -> nil
            end

          send(pid, {:tick26_repo_query, metadata.query, connection_id})
        end,
        test_pid
      )

    on_exit(fn -> :telemetry.detach(handler_id) end)
    handler_id
  end

  defp drain_repo_queries(acc \\ []) do
    receive do
      {:tick26_repo_query, query, connection_id} ->
        drain_repo_queries([{query, connection_id} | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end

  defp relevant_business_queries(queries) do
    Enum.flat_map(queries, fn {query, connection_id} ->
      case business_query_label(query) do
        nil -> []
        label -> [{label, connection_id}]
      end
    end)
  end

  defp business_query_label(query) do
    cond do
      String.contains?(query, "identity_org_memberships") -> :membership
      String.contains?(query, "identity_users") -> :user
      String.contains?(query, "identity_sessions") -> :session
      String.contains?(query, "identity_org_role_assignments") -> :role_assignment
      String.contains?(query, "events") -> :event
      true -> nil
    end
  end

  defp index_of!(labels, label) do
    Enum.find_index(labels, &(&1 == label)) ||
      flunk("missing #{inspect(label)} query in #{inspect(labels)}")
  end

  defp event_count(org_id, slug) do
    {:ok, count} =
      Repo.transaction(fn ->
        SQL.query!(Repo, "SELECT set_config('app.current_org_id', $1, true)", [org_id])

        %{rows: [[count]]} =
          SQL.query!(
            Repo,
            "SELECT count(*) FROM events WHERE org_id = $1::uuid AND slug = $2",
            [Ecto.UUID.dump!(org_id), slug]
          )

        count
      end)

    count
  end
end
