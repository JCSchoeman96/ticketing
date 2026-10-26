defmodule Ticketing.Identity.Actor do
  @moduledoc false

  @type t :: %{user_id: String.t()}

  @doc """
  Trusted authentication boundary actor carrying authoritative `user_id` only.
  """
  @spec authenticated(String.t()) :: t()
  def authenticated(user_id) when is_binary(user_id) do
    %{user_id: user_id}
  end
end
