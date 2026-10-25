defmodule Ticketing.Identity.OrgMembership do
  @moduledoc false

  use Ash.Resource,
    domain: Ticketing.Identity,
    data_layer: AshPostgres.DataLayer,
    authorizers: [Ash.Policy.Authorizer]

  postgres do
    repo Ticketing.Repo
    table "identity_org_memberships"

    custom_statements do
      statement :tenant_rls do
        up """
        ALTER TABLE identity_org_memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE identity_org_memberships FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_context_isolation ON identity_org_memberships
        FOR ALL
        USING (
          org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
        )
        WITH CHECK (
          org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
        );
        """

        down """
        DROP POLICY IF EXISTS tenant_context_isolation ON identity_org_memberships;
        ALTER TABLE identity_org_memberships NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE identity_org_memberships DISABLE ROW LEVEL SECURITY;
        """
      end
    end
  end

  actions do
    defaults []

    read :read_membership_proof do
      get? true
      transaction? true
      argument :user_id, :uuid_v7, allow_nil?: false

      filter expr(
               user_id == ^arg(:user_id) and
                 status == "active" and
                 is_nil(revoked_at_utc)
             )
    end
  end

  policies do
    policy action(:read_membership_proof) do
      forbid_unless expr(user_id == ^actor(:user_id))
      authorize_if always()
    end
  end

  multitenancy do
    strategy :attribute
    attribute :org_id
    global? false
  end

  attributes do
    uuid_v7_primary_key :org_membership_id

    attribute :org_id, :uuid_v7 do
      allow_nil? false
      public? true
    end

    attribute :user_id, :uuid_v7 do
      allow_nil? false
      public? true
    end

    attribute :status, :string do
      allow_nil? false
      public? true
    end

    create_timestamp :created_at_utc, public?: true
    attribute :revoked_at_utc, :utc_datetime_usec, public?: true
    attribute :revocation_reason, :string, public?: true
  end

  relationships do
    belongs_to :user, Ticketing.Identity.User do
      attribute_type :uuid_v7
      define_attribute? false
    end
  end

  identities do
    identity :unique_user_per_org, [:org_id, :user_id]
    identity :unique_membership_id_per_org, [:org_id, :org_membership_id]
  end
end
