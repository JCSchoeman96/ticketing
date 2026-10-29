defmodule Ticketing.Identity.Actor do
  @moduledoc false

  @type t :: %{
          required(:user_id) => String.t(),
          optional(:session_id) => String.t(),
          optional(:actor_kind) => String.t()
        }

  @doc """
  Trusted authentication boundary actor carrying authoritative `user_id` only.
  """
  @spec authenticated(String.t()) :: t()
  def authenticated(user_id) when is_binary(user_id) do
    %{user_id: user_id}
  end

  @doc """
  Trusted authentication/session boundary actor carrying authoritative user and Session identifiers.
  """
  @spec authenticated_session(String.t(), String.t()) :: t()
  def authenticated_session(user_id, session_id)
      when is_binary(user_id) and is_binary(session_id) do
    %{user_id: user_id, session_id: session_id, actor_kind: "human"}
  end
end
