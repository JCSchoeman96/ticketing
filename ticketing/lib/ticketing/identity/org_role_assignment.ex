defmodule Ticketing.Identity.OrgRoleAssignment do
  @moduledoc false

  use Ash.Resource,
    domain: Ticketing.Identity,
    data_layer: AshPostgres.DataLayer,
    authorizers: [Ash.Policy.Authorizer]

  postgres do
    repo Ticketing.Repo
    table "identity_org_role_assignments"

    custom_statements do
      statement :tenant_rls do
        up """
        ALTER TABLE identity_org_role_assignments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE identity_org_role_assignments FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_context_isolation ON identity_org_role_assignments
        FOR ALL
        USING (
          org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
        )
        WITH CHECK (
          org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
        );
        """

        down """
        DROP POLICY IF EXISTS tenant_context_isolation ON identity_org_role_assignments;
        ALTER TABLE identity_org_role_assignments NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE identity_org_role_assignments DISABLE ROW LEVEL SECURITY;
        """
      end
    end
  end

  actions do
    defaults []

    read :read_active_assignment do
      get? true
      transaction? true
      argument :user_id, :uuid_v7, allow_nil?: false
      argument :role, :string, allow_nil?: false

      filter expr(
               user_id == ^arg(:user_id) and
                 role == ^arg(:role) and
                 status == "active" and
                 is_nil(revoked_at)
             )
    end
  end

  policies do
    policy action(:read_active_assignment) do
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
    uuid_v7_primary_key :role_assignment_id

    attribute :org_id, :uuid_v7 do
      allow_nil? false
      public? true
    end

    attribute :user_id, :uuid_v7 do
      allow_nil? false
      public? true
    end

    attribute :role, :string do
      allow_nil? false
      public? true
    end

    attribute :status, :string do
      allow_nil? false
      public? true
    end

    attribute :granted_by_user_id, :uuid_v7, public?: true
    attribute :granted_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :revoked_at, :utc_datetime_usec, public?: true
  end

  relationships do
    belongs_to :user, Ticketing.Identity.User do
      attribute_type :uuid_v7
      define_attribute? false
    end
  end

  identities do
    identity :by_user_role_org, [:user_id, :role, :org_id]
  end
end
