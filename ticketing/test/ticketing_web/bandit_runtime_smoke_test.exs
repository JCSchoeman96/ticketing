defmodule TicketingWeb.BanditRuntimeSmokeTest do
  use ExUnit.Case, async: false

  @secure_bandit_requirement ">= 1.14.0 and < 2.0.0-0"
  @tcp_options [:binary, active: false, packet: :raw]
  @recv_timeout 5_000

  setup do
    {:ok, server} =
      Bandit.start_link(
        plug: TicketingWeb.Endpoint,
        ip: {127, 0, 0, 1},
        port: 0,
        startup_log: false
      )

    {:ok, {_address, port}} = ThousandIsland.listener_info(server)

    on_exit(fn ->
      if Process.alive?(server) do
        Supervisor.stop(server)
      end
    end)

    {:ok, port: port}
  end

  test "Bandit runtime stays within the approved security floor" do
    bandit_version = Application.spec(:bandit, :vsn) |> to_string()

    assert Version.match?(bandit_version, @secure_bandit_requirement),
           "expected Bandit #{bandit_version} to satisfy #{@secure_bandit_requirement}"
  end

  test "Bandit serves the home page through a real HTTP connection", %{port: port} do
    response =
      tcp_request(port, [
        "GET / HTTP/1.1\r\n",
        "Host: localhost:",
        Integer.to_string(port),
        "\r\nConnection: close\r\n\r\n"
      ])

    assert String.starts_with?(response, "HTTP/1.1 200")
  end

  test "Bandit accepts the LiveView WebSocket upgrade through a real connection", %{port: port} do
    response =
      tcp_request(port, [
        "GET /live/websocket?vsn=2.0.0 HTTP/1.1\r\n",
        "Host: localhost:",
        Integer.to_string(port),
        "\r\n",
        "Upgrade: websocket\r\n",
        "Connection: Upgrade\r\n",
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n",
        "Sec-WebSocket-Version: 13\r\n\r\n"
      ])

    assert String.starts_with?(response, "HTTP/1.1 101")
    assert String.contains?(String.downcase(response), "upgrade: websocket")
  end

  defp tcp_request(port, request) do
    {:ok, socket} = :gen_tcp.connect({127, 0, 0, 1}, port, @tcp_options, @recv_timeout)

    try do
      :ok = :gen_tcp.send(socket, request)
      recv_headers(socket, "")
    after
      :gen_tcp.close(socket)
    end
  end

  defp recv_headers(socket, acc) do
    if String.contains?(acc, "\r\n\r\n") do
      acc
    else
      {:ok, chunk} = :gen_tcp.recv(socket, 0, @recv_timeout)
      recv_headers(socket, acc <> chunk)
    end
  end
end
