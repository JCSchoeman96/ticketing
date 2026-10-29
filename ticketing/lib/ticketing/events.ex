defmodule Ticketing.Events do
  @moduledoc false

  use Ash.Domain, otp_app: :ticketing

  resources do
    resource Ticketing.Events.Event
  end

  def create_event(attributes, opts \\ []) do
    org_id = Map.fetch!(attributes, :org_id)
    actor = Keyword.get(opts, :actor)
    changeset_opts = [actor: actor, authorize?: true, tenant: org_id]
    create_opts = [actor: actor, authorize?: true, tenant: org_id, domain: __MODULE__]

    attributes_and_arguments = Map.drop(attributes, [:org_id])

    Ash.transact(
      Ticketing.Events.Event,
      fn ->
        changeset =
          Ash.Changeset.for_create(
            Ticketing.Events.Event,
            :create_event,
            attributes_and_arguments,
            changeset_opts
          )

        with {:ok, event} <- Ash.create(changeset, create_opts) do
          event
        end
      end,
      tenant: org_id
    )
  end
end
