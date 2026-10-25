defmodule Ticketing.Identity do
  @moduledoc """
  Canonical IAM organizer state: global `User` and tenant membership, Session, and role assignment resources.
  """

  use Ash.Domain,
    otp_app: :ticketing

  resources do
    resource Ticketing.Identity.User do
      define :read_user_for_liveness, action: :read_for_liveness, args: [:id], get?: true
    end

    resource Ticketing.Identity.OrgMembership do
      define :probe_org_membership, action: :read_membership_proof, args: [:user_id], get?: true
    end

    resource Ticketing.Identity.Session do
      define :read_session_for_liveness, action: :read_for_liveness, args: [:id], get?: true
    end

    resource Ticketing.Identity.OrgRoleAssignment do
      define :read_active_role_assignment,
        action: :read_active_assignment,
        args: [:user_id, :role],
        get?: true
    end
  end
end
