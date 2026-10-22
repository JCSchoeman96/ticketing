defmodule Ticketing.Platform.DatabasePrivileges do
  @moduledoc """
  Applies the application runtime role's object privileges after owner migrations.

  This module is infrastructure-only. It does not provide application persistence.
  Each migration path applies grants after new objects exist, keeping Ecto's
  `schema_migrations` table outside runtime access.
  """

  alias Ecto.Adapters.SQL

  @application_schema "public"
  @migration_table "schema_migrations"

  def apply!(Ticketing.MigrationRepo = repo) do
    runtime_role = runtime_role!()

    %{rows: [[database, owner_role]]} =
      SQL.query!(repo, "SELECT current_database(), current_user", [])

    if runtime_role == owner_role do
      raise ArgumentError,
            "Ticketing.Repo runtime role must differ from the Ticketing.MigrationRepo owner role"
    end

    grant!(
      repo,
      "GRANT CONNECT ON DATABASE #{quote_identifier(database)} TO #{quote_identifier(runtime_role)}"
    )

    grant!(
      repo,
      "GRANT USAGE ON SCHEMA #{quote_identifier(@application_schema)} TO #{quote_identifier(runtime_role)}"
    )

    # PostgreSQL 18 grants EXECUTE on functions and USAGE on types to PUBLIC by
    # default. This pass does not add function or type grants.
    owned_tables(repo)
    |> Enum.each(fn table ->
      grant!(
        repo,
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE " <>
          qualified_identifier(@application_schema, table) <>
          " TO #{quote_identifier(runtime_role)}"
      )
    end)

    owned_sequences(repo)
    |> Enum.each(fn sequence ->
      grant!(
        repo,
        "GRANT USAGE ON SEQUENCE " <>
          qualified_identifier(@application_schema, sequence) <>
          " TO #{quote_identifier(runtime_role)}"
      )
    end)

    :ok
  end

  def apply!(_repo) do
    raise ArgumentError, "runtime privileges must be applied through Ticketing.MigrationRepo"
  end

  defp owned_tables(repo) do
    %{rows: rows} =
      SQL.query!(
        repo,
        """
        SELECT relation.relname
        FROM pg_catalog.pg_class AS relation
        JOIN pg_catalog.pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = $1
          AND relation.relkind IN ('r', 'p')
          AND relation.relname <> $2
          AND relation.relowner = (
            SELECT role.oid
            FROM pg_catalog.pg_roles AS role
            WHERE role.rolname = current_user
          )
        ORDER BY relation.relname
        """,
        [@application_schema, @migration_table]
      )

    Enum.map(rows, fn [name] -> name end)
  end

  defp owned_sequences(repo) do
    %{rows: rows} =
      SQL.query!(
        repo,
        """
        SELECT relation.relname
        FROM pg_catalog.pg_class AS relation
        JOIN pg_catalog.pg_namespace AS namespace
          ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = $1
          AND relation.relkind = 'S'
          AND relation.relowner = (
            SELECT role.oid
            FROM pg_catalog.pg_roles AS role
            WHERE role.rolname = current_user
          )
        ORDER BY relation.relname
        """,
        [@application_schema]
      )

    Enum.map(rows, fn [name] -> name end)
  end

  defp runtime_role! do
    case Keyword.get(Ticketing.Repo.config(), :username) do
      username when is_binary(username) -> username
      nil -> runtime_role_from_url!(Keyword.fetch!(Ticketing.Repo.config(), :url))
    end
  end

  defp runtime_role_from_url!(url) do
    case URI.parse(url) do
      %URI{userinfo: userinfo} when is_binary(userinfo) ->
        userinfo
        |> String.split(":", parts: 2)
        |> hd()
        |> URI.decode()

      _ ->
        raise ArgumentError, "Ticketing.Repo must have a runtime role in its URL"
    end
  end

  defp qualified_identifier(schema, name) do
    quote_identifier(schema) <> "." <> quote_identifier(name)
  end

  defp quote_identifier(identifier) when is_binary(identifier) do
    if identifier == "" or byte_size(identifier) > 63 or String.contains?(identifier, <<0>>) do
      raise ArgumentError, "PostgreSQL identifiers must be non-empty and at most 63 bytes"
    end

    "\"" <> String.replace(identifier, "\"", "\"\"") <> "\""
  end

  defp grant!(repo, statement), do: SQL.query!(repo, statement, [])
end
