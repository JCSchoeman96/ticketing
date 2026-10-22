defmodule Ticketing.Platform.TenantContext do
  @moduledoc false

  alias Ecto.Adapters.SQL

  @current_org_setting "app.current_org_id"

  def put_current_org!(org_id) do
    validated_org_id = validate_org_id!(org_id)
    require_transaction!()

    SQL.query!(
      Ticketing.Repo.get_dynamic_repo(),
      "SELECT set_config('#{@current_org_setting}', $1, true)",
      [validated_org_id]
    )

    :ok
  end

  defp validate_org_id!(org_id) do
    case Ecto.UUID.cast(org_id) do
      {:ok, validated_org_id} -> validated_org_id
      :error -> raise ArgumentError, "current org id must be a valid UUID"
    end
  end

  defp require_transaction! do
    unless Ticketing.Repo.in_transaction?() do
      raise ArgumentError, "current org context requires an active Repo transaction"
    end
  end
end
