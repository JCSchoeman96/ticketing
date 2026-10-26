defmodule Ticketing.Repo.Migrations.Tick25SessionIdentitySnapshots do
  @moduledoc """
  Adds IAM-aligned `(org_id, id)` uniqueness for tenant Session rows.

  Generated from Ash snapshots. Single-column UUIDv7 primary keys on tenant IAM
  tables remain subject to an explicit TEN-1 index_isolation exception pin in JIP.
  """

  use Ecto.Migration

  def up do
    create unique_index(:identity_sessions, [:org_id, :id],
             name: "identity_sessions_unique_id_per_org_index"
           )
  end

  def down do
    drop_if_exists unique_index(:identity_sessions, [:org_id, :id],
                     name: "identity_sessions_unique_id_per_org_index"
                   )
  end
end
