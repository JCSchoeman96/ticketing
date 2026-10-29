defmodule Ticketing.Repo.Migrations.Tick26Events do
  use Ecto.Migration

  def up do
    create table(:events, primary_key: false) do
      add :org_id, :uuid, null: false, primary_key: true
      add :event_id, :uuid, null: false, primary_key: true
      add :public_event_key, :text, null: false
      add :slug, :text, null: false
      add :visibility, :text, null: false
      add :status, :text, null: false, default: "draft"
      add :default_locale, :text, null: false
      add :supported_locales, {:array, :text}, null: false
      add :featured, :boolean, null: false, default: false
      add :taxonomy_refs, :map, null: false, default: fragment("'[]'::jsonb")

      add :created_at_utc, :utc_datetime_usec,
        null: false,
        default: fragment("(now() AT TIME ZONE 'utc')")

      add :updated_at_utc, :utc_datetime_usec,
        null: false,
        default: fragment("(now() AT TIME ZONE 'utc')")

      add :archived_at_utc, :utc_datetime_usec
      add :published_at_utc, :utc_datetime_usec
      add :version, :integer, null: false, default: 1
      add :lock_version, :integer, null: false, default: 1
    end

    create unique_index(:events, [:org_id, :public_event_key],
             name: "events_unique_public_event_key_per_org_index"
           )

    create unique_index(:events, [:org_id, :slug], name: "events_unique_slug_per_org_index")

    execute("ALTER TABLE events ENABLE ROW LEVEL SECURITY")
    execute("ALTER TABLE events FORCE ROW LEVEL SECURITY")

    execute("""
    CREATE POLICY tenant_context_isolation ON events
    FOR ALL
    USING (
      org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
    )
    WITH CHECK (
      org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
    )
    """)
  end

  def down do
    execute("DROP POLICY IF EXISTS tenant_context_isolation ON events")
    execute("ALTER TABLE events NO FORCE ROW LEVEL SECURITY")
    execute("ALTER TABLE events DISABLE ROW LEVEL SECURITY")

    drop_if_exists unique_index(:events, [:org_id, :slug],
                     name: "events_unique_slug_per_org_index"
                   )

    drop_if_exists unique_index(:events, [:org_id, :public_event_key],
                     name: "events_unique_public_event_key_per_org_index"
                   )

    drop table(:events)
  end
end
