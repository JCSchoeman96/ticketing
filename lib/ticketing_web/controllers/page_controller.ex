defmodule TicketingWeb.PageController do
  use TicketingWeb, :controller

  def home(conn, _params) do
    render(conn, :home)
  end
end
