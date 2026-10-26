defmodule Ticketing.Identity.OwnerFixtures do
  @moduledoc """
  Test-only migration-owner seeding for pre-existing Identity rows.

  Not a production API. Uses `Ticketing.MigrationRepo` only.
  """

  alias Ecto.Adapters.SQL
  alias Ecto.Migrator
  alias Ticketing.MigrationRepo
  alias Ticketing.Platform.DatabasePrivileges

  @user_table "identity_users"
  @membership_table "identity_org_memberships"
  @session_table "identity_sessions"
  @role_table "identity_org_role_assignments"

  def insert_user!(attrs) do
    id = Map.fetch!(attrs, :id)
    status = Map.get(attrs, :status, "active")
    now = utc_now_usec()
    verified_at = Map.get(attrs, :verified_at_utc)
    disabled_at = Map.get(attrs, :disabled_at_utc)
    deleted_at = Map.get(attrs, :deleted_at_utc)

    owner_insert!(
      @user_table,
      """
      INSERT INTO #{@user_table} (
        id, status, created_at_utc, verified_at_utc, disabled_at_utc, deleted_at_utc
      )
      VALUES ($1::uuid, $2, $3::timestamptz, $4::timestamptz, $5::timestamptz, $6::timestamptz)
      """,
      [id, status, now, verified_at, disabled_at, deleted_at]
    )

    %{id: id, status: status, created_at_utc: now}
  end

  def insert_org_membership!(attrs) do
    org_membership_id = Map.fetch!(attrs, :org_membership_id)
    org_id = Map.fetch!(attrs, :org_id)
    user_id = Map.fetch!(attrs, :user_id)
    status = Map.get(attrs, :status, "active")
    now = utc_now_usec()
    revoked_at = Map.get(attrs, :revoked_at_utc)
    revocation_reason = Map.get(attrs, :revocation_reason)

    owner_insert_tenant!(
      org_id,
      """
      INSERT INTO #{@membership_table} (
        org_membership_id, org_id, user_id, status, created_at_utc, revoked_at_utc, revocation_reason
      )
      VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5::timestamptz, $6::timestamptz, $7)
      """,
      [org_membership_id, org_id, user_id, status, now, revoked_at, revocation_reason]
    )

    %{
      org_membership_id: org_membership_id,
      org_id: org_id,
      user_id: user_id,
      status: status
    }
  end

  def insert_session!(attrs) do
    id = Map.fetch!(attrs, :id)
    org_id = Map.fetch!(attrs, :org_id)
    user_id = Map.fetch!(attrs, :user_id)
    token_hash = Map.get(attrs, :token_hash, "test-only-token-hash")
    status = Map.get(attrs, :status, "active")
    now = utc_now_usec()
    expires_at = Map.get(attrs, :expires_at_utc, DateTime.add(now, 3600, :second))
    revoked_at = Map.get(attrs, :revoked_at_utc)
    last_seen_at = Map.get(attrs, :last_seen_at_utc)

    owner_insert_tenant!(
      org_id,
      """
      INSERT INTO #{@session_table} (
        id, org_id, user_id, token_hash, status, created_at_utc, expires_at_utc,
        revoked_at_utc, last_seen_at_utc
      )
      VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5, $6::timestamptz, $7::timestamptz, $8::timestamptz, $9::timestamptz)
      """,
      [id, org_id, user_id, token_hash, status, now, expires_at, revoked_at, last_seen_at]
    )

    %{id: id, org_id: org_id, user_id: user_id, status: status, expires_at_utc: expires_at}
  end

  def insert_org_role_assignment!(attrs) do
    role_assignment_id = Map.fetch!(attrs, :role_assignment_id)
    org_id = Map.fetch!(attrs, :org_id)
    user_id = Map.fetch!(attrs, :user_id)
    role = Map.fetch!(attrs, :role)
    status = Map.get(attrs, :status, "active")
    now = utc_now_usec()
    granted_by = Map.get(attrs, :granted_by_user_id)
    revoked_at = Map.get(attrs, :revoked_at)

    owner_insert_tenant!(
      org_id,
      """
      INSERT INTO #{@role_table} (
        role_assignment_id, org_id, user_id, role, status, granted_by_user_id, granted_at, revoked_at
      )
      VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5, $6::uuid, $7::timestamptz, $8::timestamptz)
      """,
      [role_assignment_id, org_id, user_id, role, status, granted_by, now, revoked_at]
    )

    %{role_assignment_id: role_assignment_id, org_id: org_id, user_id: user_id, role: role}
  end

  def reset_identity_tables! do
    {:ok, _, _} =
      Migrator.with_repo(MigrationRepo, fn repo ->
        ensure_identity_tables_migrated!(repo)

        SQL.query!(
          repo,
          """
          TRUNCATE TABLE
            identity_org_role_assignments,
            identity_sessions,
            identity_org_memberships,
            identity_users
          RESTART IDENTITY CASCADE
          """,
          []
        )
      end)

    :ok
  end

  defp owner_insert_tenant!(org_id, sql, params) do
    {:ok, _, _} =
      Migrator.with_repo(MigrationRepo, fn repo ->
        ensure_identity_tables_migrated!(repo)

        repo.transaction(fn ->
          SQL.query!(
            repo,
            "SELECT set_config('app.current_org_id', $1, true)",
            [org_id]
          )

          SQL.query!(repo, sql, encode_uuids(params))
        end)
      end)

    :ok
  end

  defp owner_insert!(_table, sql, params) do
    {:ok, _, _} =
      Migrator.with_repo(MigrationRepo, fn repo ->
        ensure_identity_tables_migrated!(repo)
        SQL.query!(repo, sql, encode_uuids(params))
      end)

    :ok
  end

  defp encode_uuids(params) do
    Enum.map(params, fn
      nil -> nil
      value when is_binary(value) and byte_size(value) == 36 -> Ecto.UUID.dump!(value)
      %DateTime{} = dt -> dt
      other -> other
    end)
  end

  defp ensure_identity_tables_migrated!(repo) do
    case SQL.query!(
           repo,
           "SELECT to_regclass('public.identity_users') IS NOT NULL",
           []
         ) do
      %{rows: [[true]]} ->
        :ok

      %{rows: [[false]]} ->
        raise "identity tables are missing; run migrations before Identity owner fixtures"
    end

    DatabasePrivileges.apply!(repo)
  end

  defp utc_now_usec do
    DateTime.utc_now() |> DateTime.truncate(:microsecond)
  end
end
