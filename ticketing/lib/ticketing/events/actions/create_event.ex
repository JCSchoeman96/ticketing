defmodule Ticketing.Events.Actions.CreateEvent do
  @moduledoc false

  use Ash.Resource.Change

  alias Ticketing.Identity
  alias Ticketing.Identity.Authorization

  @impl true
  def change(changeset, _opts, context) do
    Ash.Changeset.before_action(changeset, fn changeset ->
      create_event(changeset, context.actor, context.tenant)
    end)
  end

  defp create_event(changeset, actor, org_id) do
    arguments = %{
      org_id: org_id,
      active_scope: Ash.Changeset.get_argument(changeset, :active_scope),
      active_role: Ash.Changeset.get_argument(changeset, :active_role)
    }

    with {:ok, membership} <-
           Identity.probe_org_membership(actor.user_id,
             actor: actor,
             tenant: org_id,
             authorize?: true
           ),
         {:ok, user} <-
           Identity.read_user_for_liveness(actor.user_id,
             actor: actor,
             authorize?: true
           ),
         {:ok, session} <-
           Identity.read_session_for_liveness(actor.session_id,
             actor: actor,
             tenant: org_id,
             authorize?: true
           ),
         {:ok, role_assignment} <-
           Identity.read_active_role_assignment(actor.user_id, arguments.active_role,
             actor: actor,
             tenant: org_id,
             authorize?: true
           ),
         {:ok, true} <-
           authorize_event_create(arguments, actor, user, membership, session, role_assignment) do
      event_id = Ash.UUIDv7.generate()

      changeset
      |> Ash.Changeset.force_change_attribute(:org_id, org_id)
      |> Ash.Changeset.force_change_attribute(:event_id, event_id)
      |> Ash.Changeset.force_change_attribute(:public_event_key, public_event_key(event_id))
    else
      {:error, error} -> Ash.Changeset.add_error(changeset, error)
    end
  end

  defp authorize_event_create(arguments, actor, user, membership, session, role_assignment) do
    Authorization
    |> Ash.ActionInput.for_action(
      :authorize_event_create,
      %{
        org_id: arguments.org_id,
        active_scope: arguments.active_scope,
        active_role: arguments.active_role,
        user: user,
        membership: membership,
        session: session,
        role_assignment: role_assignment
      },
      actor: actor,
      authorize?: true,
      domain: Ticketing.Identity
    )
    |> Ash.run_action()
  end

  defp public_event_key(event_id), do: "evt_" <> String.replace(event_id, "-", "")
end
