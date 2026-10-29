defmodule Ticketing.Identity.Authorization do
  @moduledoc false

  use Ash.Resource,
    domain: Ticketing.Identity,
    data_layer: Ash.DataLayer.Simple,
    authorizers: [Ash.Policy.Authorizer]

  actions do
    defaults []

    action :authorize_event_create, :boolean do
      public? false

      argument :org_id, :uuid_v7, allow_nil?: false
      argument :active_scope, :string, allow_nil?: false
      argument :active_role, :string, allow_nil?: false

      argument :user, :struct,
        allow_nil?: false,
        constraints: [instance_of: Ticketing.Identity.User]

      argument :membership, :struct,
        allow_nil?: false,
        constraints: [instance_of: Ticketing.Identity.OrgMembership]

      argument :session, :struct,
        allow_nil?: false,
        constraints: [instance_of: Ticketing.Identity.Session]

      argument :role_assignment, :struct,
        allow_nil?: false,
        constraints: [instance_of: Ticketing.Identity.OrgRoleAssignment]

      run fn _input, _context -> {:ok, true} end
    end
  end

  policies do
    bypass private_action?() do
      authorize_if Ticketing.Identity.Checks.CanCreateEvent
    end
  end
end
