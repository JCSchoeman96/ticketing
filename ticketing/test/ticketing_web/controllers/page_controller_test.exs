defmodule TicketingWeb.PageControllerTest do
  use TicketingWeb.ConnCase

  test "GET /", %{conn: conn} do
    conn = get(conn, ~p"/")
    assert html_response(conn, 200) =~ "Peace of mind from prototype to production"
  end

  test "GET / allows only its inline theme script through the content security policy", %{
    conn: conn
  } do
    conn = get(conn, ~p"/")
    response = html_response(conn, 200)

    assert [policy] = get_resp_header(conn, "content-security-policy")
    assert policy =~ "default-src 'self'"

    assert [script] = Regex.run(~r/<script>(.*?)<\/script>/s, response, capture: :all_but_first)
    script_hash = script |> then(&:crypto.hash(:sha256, &1)) |> Base.encode64()

    assert policy =~ "'sha256-#{script_hash}'"
  end
end
