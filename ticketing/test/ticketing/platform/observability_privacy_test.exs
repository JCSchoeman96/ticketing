defmodule Ticketing.Platform.ObservabilityPrivacyTest do
  use ExUnit.Case, async: false

  import ExUnit.CaptureLog

  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.Events
  alias Ticketing.Identity.Actor
  alias Ticketing.Identity.OwnerFixtures
  alias Ticketing.MigrationRepo
  alias Ticketing.TenantContextTestRepo

  @sensitive_labels [:org_id, :user_id, :session_id, :token_hash, :credential, :credentials]
  @org_id "f1f1f1f1-f1f1-41f1-81f1-f1f1f1f1f1f1"
  @user_id "a7a7a7a7-a7a7-47a7-87a7-a7a7a7a7a7a7"
  @membership_id "b8b8b8b8-b8b8-48b8-88b8-b8b8b8b8b8b8"
  @session_id "d9d9d9d9-d9d9-49d9-89d9-d9d9d9d9d9d9"
  @role_assignment_id "e6e6e6e6-e6e6-46e6-86e6-e6e6e6e6e6e6"
  @token_hash "TICK28_TOKEN_HASH_SENTINEL_71f6d386"
  @runtime_repo Ticketing.T001ObservabilityPrivacyRepo

  setup do
    reset_state!()
    start_runtime_repo!()
    Ticketing.Repo.put_dynamic_repo(@runtime_repo)

    assert :ok = Logger.put_application_level(:ticketing, :info)

    on_exit(fn ->
      Ticketing.Repo.put_dynamic_repo(Ticketing.Repo)
      Logger.delete_application_level(:ticketing)
    end)

    :ok
  end

  test "integrated success and failure paths do not emit raw sensitive values in metric labels or production-level logs" do
    actor = seed_complete_identity!()
    metrics = TicketingWeb.Telemetry.metrics()
    handler_id = attach_metric_probe(metrics)

    log_output =
      capture_log([level: :info, metadata: :all, format: "$metadata $message\n"], fn ->
        assert {:ok, event} =
                 create_event(actor,
                   slug: "tick28-observability-success",
                   role: "org_admin"
                 )

        assert event.org_id == @org_id

        assert {:error, _error} =
                 create_event(actor,
                   slug: "tick28-observability-failure",
                   role: "org_owner"
                 )
      end)

    emissions = drain_metric_emissions()
    :telemetry.detach(handler_id)

    assert Enum.any?(emissions, fn {event_name, _metadata} ->
             event_name == [:ticketing, :repo, :query]
           end)

    label_maps = emitted_label_maps(metrics, emissions)

    refute Enum.any?(label_maps, fn labels ->
             Enum.any?(Map.keys(labels), &(&1 in @sensitive_labels))
           end)

    serialized_labels = inspect(label_maps, limit: :infinity, printable_limit: :infinity)

    for needle <- sensitive_needles() do
      refute String.contains?(serialized_labels, needle),
             "emitted telemetry label leaked sensitive sentinel #{inspect(needle)}"

      refute String.contains?(log_output, needle),
             "production-level log output leaked sensitive sentinel #{inspect(needle)}"
    end
  end

  test "default Logger metadata excludes raw tenant and identity identifiers" do
    logger_metadata =
      :logger
      |> Application.fetch_env!(:default_formatter)
      |> Keyword.get(:metadata, [])

    refute Enum.any?(logger_metadata, &(&1 in @sensitive_labels))
    assert :request_id in logger_metadata
  end

  defp attach_metric_probe(metrics) do
    handler_id = "tick28-observability-#{System.unique_integer([:positive])}"
    test_pid = self()

    event_names =
      metrics
      |> Enum.map(&Map.fetch!(&1, :event_name))
      |> Enum.uniq()

    :ok =
      :telemetry.attach_many(
        handler_id,
        event_names,
        fn event_name, _measurements, metadata, pid ->
          send(pid, {:tick28_metric_event, event_name, metadata})
        end,
        test_pid
      )

    on_exit(fn -> :telemetry.detach(handler_id) end)
    handler_id
  end

  defp emitted_label_maps(metrics, emissions) do
    Enum.flat_map(emissions, fn {event_name, metadata} ->
      metrics
      |> Enum.filter(&(Map.fetch!(&1, :event_name) == event_name))
      |> Enum.map(&metric_label_map(&1, metadata))
    end)
  end

  defp metric_label_map(metric, metadata) do
    tags = Map.get(metric, :tags, [])
    tag_values = Map.get(metric, :tag_values)

    values =
      if is_function(tag_values, 1) do
        tag_values.(metadata)
      else
        metadata
      end

    Map.take(values, tags)
  end

  defp drain_metric_emissions(acc \\ []) do
    receive do
      {:tick28_metric_event, event_name, metadata} ->
        drain_metric_emissions([{event_name, metadata} | acc])
    after
      0 -> Enum.reverse(acc)
    end
  end

  defp sensitive_needles do
    uuid_needles =
      Enum.flat_map(
        [@org_id, @user_id, @session_id, @membership_id, @role_assignment_id],
        fn uuid ->
          [
            uuid,
            String.replace(uuid, "-", ""),
            inspect(Ecto.UUID.dump!(uuid), limit: :infinity, printable_limit: :infinity)
          ]
        end
      )

    [@token_hash | uuid_needles]
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
      token_hash: @token_hash
    })

    OwnerFixtures.insert_org_role_assignment!(%{
      role_assignment_id: @role_assignment_id,
      org_id: @org_id,
      user_id: @user_id,
      role: "org_admin"
    })

    Actor.authenticated_session(@user_id, @session_id)
  end

  defp create_event(actor, opts) do
    slug = Keyword.fetch!(opts, :slug)
    role = Keyword.fetch!(opts, :role)

    Events.create_event(
      %{
        org_id: @org_id,
        active_scope: "org",
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
