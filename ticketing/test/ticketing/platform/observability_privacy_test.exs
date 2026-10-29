defmodule Ticketing.Platform.ObservabilityPrivacyTest do
  use ExUnit.Case, async: true

  @sensitive_labels [:org_id, :user_id, :session_id, :token_hash, :credential, :credentials]

  test "configured telemetry metric tags exclude raw tenant and identity identifiers" do
    for metric <- TicketingWeb.Telemetry.metrics() do
      tags = Map.get(metric, :tags, [])
      refute Enum.any?(tags, &(&1 in @sensitive_labels))
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
end
