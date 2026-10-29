defmodule Ticketing.Events.Checks.TrustedSessionActor do
  @moduledoc false

  use Ash.Policy.SimpleCheck

  @impl true
  def describe(_opts), do: "actor comes from trusted human session infrastructure"

  @impl true
  def match?(
        %{user_id: user_id, session_id: session_id, actor_kind: "human"},
        _context,
        _opts
      ) do
    is_binary(user_id) and is_binary(session_id)
  end

  def match?(_actor, _context, _opts), do: false
end
