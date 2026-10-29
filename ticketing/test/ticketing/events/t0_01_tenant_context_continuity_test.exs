defmodule Ticketing.Events.T001TenantContextContinuityTest do
  use ExUnit.Case, async: false

  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.Events
  alias Ticketing.Identity.Actor
  alias Ticketing.Identity.OwnerFixtures
  alias Ticketing.MigrationRepo
  alias Ticketing.TenantContextTestRepo

  @org_id "11111111-1111-4111-8111-111111111111"
  @user_id "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  @membership_id "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
  @session_id "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
  @role_assignment_id "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
  @runtime_repo Ticketing.T001TenantContextContinuityRepo

  setup do
    reset_state!()
    start_runtime_repo!()
    Ticketing.Repo.put_dynamic_repo(@runtime_repo)
    on_exit(fn -> Ticketing.Repo.put_dynamic_repo(Ticketing.Repo) end)
    :ok
  end

  test "the same tenant UUID remains on the same transaction backend through proof and Event insert" do
    actor = seed_complete_identity!()
    handler_id = attach_tenant_stage_probe()

    assert {:ok, event} = create_event(actor, "tick28-tenant-continuity")
    assert event.org_id == @org_id

    observations = drain_stage_observations()
    queries = drain_observed_queries()
    :telemetry.detach(handler_id)

    assert [
             {:membership_proven, membership_backend_pid, @org_id},
             {:event_inserted, event_backend_pid, @org_id}
           ] = observations

    assert event_backend_pid == membership_backend_pid

    tenant_context_transitions =
      Enum.filter(queries, &String.contains?(&1, "set_config('app.current_org_id'"))

    assert [_single_tenant_context_transition] = tenant_context_transitions
  end

  defp attach_tenant_stage_probe do
    handler_id = "tick28-tenant-stage-#{System.unique_integer([:positive])}"
    test_pid = self()

    :ok =
      :telemetry.attach(
        handler_id,
        [:ticketing, :repo, :query],
        fn _event, _measurements, metadata, pid ->
          send(pid, {:tick28_observed_query, metadata.query})

          case tenant_stage(metadata.query) do
            nil ->
              :ok

            stage ->
              assert %Postgrex.Result{rows: [[backend_pid, tenant_setting]]} =
                       SQL.query!(
                         Ticketing.Repo.get_dynamic_repo(),
                         "SELECT pg_backend_pid(), current_setting('app.current_org_id', true)",
                         []
                       )

              send(pid, {:tick28_tenant_stage, stage, backend_pid, tenant_setting})
          end
        end,
        test_pid
      )

    on_exit(fn -> :telemetry.detach(handler_id) end)
    handler_id
  end

  defp tenant_stage(query) do
    normalized = String.downcase(query)

    cond do
      String.contains?(normalized, "identity_org_memberships") -> :membership_proven
      String.contains?(normalized, "insert into \"events\"") -> :event_inserted
      true -> nil
    end
  end

  defp drain_stage_observations(acc \\ []) do
    receive do
      {:tick28_tenant_stage, stage, backend_pid, tenant_setting} ->
        drain_stage_observations([{stage, backend_pid, tenant_setting} | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end

  defp drain_observed_queries(acc \\ []) do
    receive do
      {:tick28_observed_query, query} -> drain_observed_queries([query | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end

  defp seed_complete_identity! do
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
      token_hash: "tick28-continuity-test-only-secret"
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
end
