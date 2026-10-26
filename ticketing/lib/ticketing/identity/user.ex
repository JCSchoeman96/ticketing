defmodule Ticketing.Identity.User do
  @moduledoc false

  use Ash.Resource,
    domain: Ticketing.Identity,
    data_layer: AshPostgres.DataLayer,
    authorizers: [Ash.Policy.Authorizer]

  postgres do
    repo Ticketing.Repo
    table "identity_users"
  end

  actions do
    defaults []

    read :read_for_liveness do
      get? true
      transaction? true
      argument :id, :uuid_v7, allow_nil?: false

      filter expr(
               id == ^arg(:id) and
                 status == "active" and
                 is_nil(disabled_at_utc) and
                 is_nil(deleted_at_utc)
             )
    end
  end

  policies do
    policy action(:read_for_liveness) do
      forbid_unless expr(id == ^actor(:user_id))
      authorize_if always()
    end
  end

  attributes do
    uuid_v7_primary_key :id

    attribute :status, :string do
      allow_nil? false
      public? true
    end

    create_timestamp :created_at_utc, public?: true

    attribute :verified_at_utc, :utc_datetime_usec, public?: true
    attribute :disabled_at_utc, :utc_datetime_usec, public?: true
    attribute :deleted_at_utc, :utc_datetime_usec, public?: true
  end

  relationships do
    has_many :org_memberships, Ticketing.Identity.OrgMembership do
      destination_attribute :user_id
    end

    has_many :sessions, Ticketing.Identity.Session do
      destination_attribute :user_id
    end

    has_many :org_role_assignments, Ticketing.Identity.OrgRoleAssignment do
      destination_attribute :user_id
    end
  end
end
