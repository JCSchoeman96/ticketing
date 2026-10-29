defmodule Ticketing.Identity.Checks.CanCreateEvent do
  @moduledoc false

  use Ash.Policy.SimpleCheck

  @event_create_roles ["org_admin", "org_owner"]

  @impl true
  def describe(_opts), do: "trusted persisted organizer may create an Event"

  @impl true
  def match?(
        %{user_id: user_id, session_id: session_id, actor_kind: "human"},
        %{action_input: %{arguments: arguments}},
        _opts
      ) do
    scope_and_role_valid?(arguments) and
      user_valid?(arguments.user, user_id) and
      membership_valid?(arguments.membership, arguments.org_id, user_id) and
      session_valid?(arguments.session, arguments.org_id, user_id, session_id) and
      role_assignment_valid?(
        arguments.role_assignment,
        arguments.org_id,
        user_id,
        arguments.active_role
      )
  end

  def match?(_actor, _context, _opts), do: false

  defp scope_and_role_valid?(arguments) do
    arguments.active_scope == "org" and arguments.active_role in @event_create_roles
  end

  defp user_valid?(user, user_id) do
    user.id == user_id and user.status == "active"
  end

  defp membership_valid?(membership, org_id, user_id) do
    membership.org_id == org_id and
      membership.user_id == user_id and
      membership.status == "active" and
      is_nil(membership.revoked_at_utc)
  end

  defp session_valid?(session, org_id, user_id, session_id) do
    session.id == session_id and
      session.org_id == org_id and
      session.user_id == user_id and
      session.status == "active" and
      is_nil(session.revoked_at_utc)
  end

  defp role_assignment_valid?(role_assignment, org_id, user_id, active_role) do
    role_assignment.org_id == org_id and
      role_assignment.user_id == user_id and
      role_assignment.role == active_role and
      role_assignment.status == "active" and
      is_nil(role_assignment.revoked_at)
  end
end
