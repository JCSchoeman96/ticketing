defmodule Ticketing.Identity.Session do
  @moduledoc false

  use Ash.Resource,
    domain: Ticketing.Identity,
    data_layer: AshPostgres.DataLayer,
    authorizers: [Ash.Policy.Authorizer]

  postgres do
    repo Ticketing.Repo
    table "identity_sessions"

    custom_statements do
      statement :tenant_rls do
        up """
        ALTER TABLE identity_sessions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE identity_sessions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_context_isolation ON identity_sessions
        FOR ALL
        USING (
          org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
        )
        WITH CHECK (
          org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
        );
        """

        down """
        DROP POLICY IF EXISTS tenant_context_isolation ON identity_sessions;
        ALTER TABLE identity_sessions NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE identity_sessions DISABLE ROW LEVEL SECURITY;
        """
      end
    end
  end

  actions do
    defaults []

    read :read_for_liveness do
      get? true
      transaction? true
      argument :id, :uuid_v7, allow_nil?: false

      prepare build(
                select: [
                  :id,
                  :org_id,
                  :user_id,
                  :status,
                  :created_at_utc,
                  :expires_at_utc,
                  :revoked_at_utc,
                  :last_seen_at_utc
                ]
              )

      filter expr(
               id == ^arg(:id) and
                 status == "active" and
                 is_nil(revoked_at_utc) and
                 expires_at_utc > fragment("now() at time zone 'utc'")
             )
    end
  end

  policies do
    policy action(:read_for_liveness) do
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
    uuid_v7_primary_key :id

    attribute :org_id, :uuid_v7 do
      allow_nil? false
      public? true
    end

    attribute :user_id, :uuid_v7 do
      allow_nil? false
      public? true
    end

    attribute :token_hash, :string do
      allow_nil? false
      public? false
      sensitive? true
    end

    attribute :status, :string do
      allow_nil? false
      public? true
    end

    create_timestamp :created_at_utc, public?: true

    attribute :expires_at_utc, :utc_datetime_usec do
      allow_nil? false
      public? true
    end

    attribute :revoked_at_utc, :utc_datetime_usec, public?: true
    attribute :last_seen_at_utc, :utc_datetime_usec, public?: true
  end

  relationships do
    belongs_to :user, Ticketing.Identity.User do
      attribute_type :uuid_v7
      define_attribute? false
    end
  end

  identities do
    identity :unique_id_per_org, [:org_id, :id]
  end
end
