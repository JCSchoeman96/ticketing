defmodule Ticketing.Application do
  # See https://hexdocs.pm/elixir/Application.html
  # for more information on OTP Applications
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      TicketingWeb.Telemetry,
      Ticketing.Repo,
      {DNSCluster, query: Application.get_env(:ticketing, :dns_cluster_query) || :ignore},
      {Phoenix.PubSub, name: Ticketing.PubSub},
      # Start a worker by calling: Ticketing.Worker.start_link(arg)
      # {Ticketing.Worker, arg},
      # Start to serve requests, typically the last entry
      TicketingWeb.Endpoint
    ]

    # See https://hexdocs.pm/elixir/Supervisor.html
    # for other strategies and supported options
    opts = [strategy: :one_for_one, name: Ticketing.Supervisor]
    Supervisor.start_link(children, opts)
  end

  # Tell Phoenix to update the endpoint configuration
  # whenever the application is updated.
  @impl true
  def config_change(changed, _new, removed) do
    TicketingWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
