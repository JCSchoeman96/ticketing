defmodule Ticketing.Events.Event do
  @moduledoc false

  use Ash.Resource,
    domain: Ticketing.Events,
    data_layer: AshPostgres.DataLayer,
    authorizers: [Ash.Policy.Authorizer]

  postgres do
    repo Ticketing.Repo
    table "events"

    migration_types taxonomy_refs: :jsonb,
                    version: :integer,
                    lock_version: :integer

    migration_defaults created_at_utc: "fragment(\"(now() AT TIME ZONE 'utc')\")",
                       updated_at_utc: "fragment(\"(now() AT TIME ZONE 'utc')\")"

    storage_types taxonomy_refs: :jsonb

    custom_statements do
      statement :tenant_rls do
        up """
        ALTER TABLE events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_context_isolation ON events
        FOR ALL
        USING (
          org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
        )
        WITH CHECK (
          org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
        );
        """

        down """
        DROP POLICY IF EXISTS tenant_context_isolation ON events;
        ALTER TABLE events NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE events DISABLE ROW LEVEL SECURITY;
        """
      end
    end
  end

  actions do
    defaults []

    create :create_event do
      transaction? true
      accept [:slug, :visibility, :default_locale, :supported_locales, :featured, :taxonomy_refs]

      argument :active_scope, :string, allow_nil?: false
      argument :active_role, :string, allow_nil?: false

      argument :request_id, :string, allow_nil?: false
      argument :trace_id, :string, allow_nil?: false

      validate one_of(:visibility, ["public", "unlisted", "private"])
      validate one_of(:default_locale, ["en", "af"])

      change Ticketing.Events.Actions.CreateEvent
    end
  end

  policies do
    policy action(:create_event) do
      authorize_if Ticketing.Events.Checks.TrustedSessionActor
    end
  end

  validations do
    validate one_of(:visibility, ["public", "unlisted", "private"])
    validate one_of(:status, ["draft", "published", "archived"])
    validate one_of(:default_locale, ["en", "af"])
  end

  multitenancy do
    strategy :attribute
    attribute :org_id
    global? false
  end

  attributes do
    attribute :org_id, :uuid_v7 do
      allow_nil? false
      primary_key? true
      public? true
      writable? false
    end

    attribute :event_id, :uuid_v7 do
      allow_nil? false
      primary_key? true
      public? true
      writable? false
    end

    attribute :public_event_key, :string do
      allow_nil? false
      public? true
      writable? false
      constraints min_length: 24, max_length: 64
    end

    attribute :slug, :string do
      allow_nil? false
      public? true
      constraints min_length: 3, max_length: 128, match: ~r/^[a-z0-9]+(?:-[a-z0-9]+)*$/
    end

    attribute :visibility, :string do
      allow_nil? false
      public? true
    end

    attribute :status, :string do
      allow_nil? false
      public? true
      writable? false
      default "draft"
    end

    attribute :default_locale, :string do
      allow_nil? false
      public? true
    end

    attribute :supported_locales, {:array, :string} do
      allow_nil? false
      public? true
      constraints min_length: 1, max_length: 10
    end

    attribute :featured, :boolean do
      allow_nil? false
      public? true
      default false
    end

    attribute :taxonomy_refs, {:array, :map} do
      allow_nil? false
      public? true
      default []
    end

    attribute :created_at_utc, :utc_datetime_usec do
      allow_nil? false
      public? true
      writable? false
      generated? true
    end

    attribute :updated_at_utc, :utc_datetime_usec do
      allow_nil? false
      public? true
      writable? false
      generated? true
    end

    attribute :archived_at_utc, :utc_datetime_usec do
      public? true
      writable? false
    end

    attribute :published_at_utc, :utc_datetime_usec do
      public? true
      writable? false
    end

    attribute :version, :integer do
      allow_nil? false
      public? true
      writable? false
      default 1
    end

    attribute :lock_version, :integer do
      allow_nil? false
      public? true
      writable? false
      default 1
    end
  end

  identities do
    identity :unique_public_event_key_per_org, [:org_id, :public_event_key]
    identity :unique_slug_per_org, [:org_id, :slug]
  end
end
