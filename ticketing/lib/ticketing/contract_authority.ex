defmodule Ticketing.ContractAuthority do
  @moduledoc """
  Verifies the implementation's pin to the canonical contracts checkout.
  """

  @required_pin_fields ~w(
    repository
    reviewed_commit
    canon_doc_id
    canon_version
    manifest_path
    t0_tracer_path
  )

  def load_pin(path) do
    with {:ok, contents} <- File.read(path),
         {:ok, pin} <- Jason.decode(contents),
         :ok <- validate_pin(pin) do
      {:ok, pin}
    else
      {:error, %Jason.DecodeError{} = error} ->
        {:error, "could not parse contract authority pin at #{path}: #{Exception.message(error)}"}

      {:error, :enoent} ->
        {:error, "contract authority pin is missing at #{path}"}

      {:error, reason} when is_atom(reason) ->
        {:error,
         "could not read contract authority pin at #{path}: #{:file.format_error(reason)}"}

      {:error, message} ->
        {:error, message}
    end
  end

  def verify_checkout(path, pin) when is_binary(path) and is_map(pin) do
    expanded_path = Path.expand(path)

    with :ok <- ensure_git_repository(expanded_path),
         {:ok, commit} <- git_head(expanded_path),
         :ok <- ensure_commit(commit, pin["reviewed_commit"]),
         {:ok, version} <- manifest_version(expanded_path, pin),
         :ok <- ensure_tracer(expanded_path, pin["t0_tracer_path"]) do
      {:ok, %{path: expanded_path, commit: commit, canon_version: version}}
    end
  end

  def default_checkout_path do
    System.get_env("TICKETING_CONTRACTS_PATH") ||
      Path.expand("../../ticketing-contracts", File.cwd!())
  end

  defp validate_pin(pin) when is_map(pin) do
    missing_fields = Enum.reject(@required_pin_fields, &Map.has_key?(pin, &1))

    cond do
      missing_fields != [] ->
        {:error,
         "contract authority pin is missing required fields: #{Enum.join(missing_fields, ", ")}"}

      Enum.any?(@required_pin_fields, &(not is_binary(pin[&1]))) ->
        {:error, "contract authority pin fields must be strings"}

      pin["repository"] != "JCSchoeman96/ticketing-contracts" ->
        {:error, "contract authority pin repository must be JCSchoeman96/ticketing-contracts"}

      not Regex.match?(~r/\A[0-9a-f]{40}\z/, pin["reviewed_commit"]) ->
        {:error, "contract authority reviewed_commit must be a 40-character lowercase Git SHA"}

      pin["canon_doc_id"] != "CANON-1" ->
        {:error, "contract authority canon_doc_id must be CANON-1"}

      pin["canon_version"] != "2.0.10" ->
        {:error, "contract authority canon_version must be 2.0.10"}

      true ->
        :ok
    end
  end

  defp validate_pin(_), do: {:error, "contract authority pin must be a JSON object"}

  defp ensure_git_repository(path) do
    if File.dir?(path) do
      case System.cmd("git", ["-C", path, "rev-parse", "--is-inside-work-tree"],
             stderr_to_stdout: true
           ) do
        {"true\n", 0} ->
          :ok

        {_output, _status} ->
          {:error, "configured contracts checkout is not a Git repository: #{path}"}
      end
    else
      {:error, "configured contracts checkout is not a Git repository: #{path}"}
    end
  end

  defp git_head(path) do
    case System.cmd("git", ["-C", path, "rev-parse", "HEAD"], stderr_to_stdout: true) do
      {commit, 0} -> {:ok, String.trim(commit)}
      {_output, _status} -> {:error, "could not resolve HEAD in contracts checkout: #{path}"}
    end
  end

  defp ensure_commit(commit, expected_commit) when commit == expected_commit, do: :ok

  defp ensure_commit(commit, expected_commit) do
    {:error,
     "contracts checkout commit mismatch: expected #{expected_commit}, found #{commit}; update contracts/authority.json only after reviewing a new canonical release"}
  end

  defp manifest_version(path, pin) do
    manifest_path = Path.join(path, pin["manifest_path"])

    with {:ok, contents} <- File.read(manifest_path),
         {:ok, %{"contracts" => contracts}} when is_list(contracts) <- Jason.decode(contents),
         contract when is_map(contract) <-
           Enum.find(contracts, &(&1["doc_id"] == pin["canon_doc_id"])) do
      version = contract["version"]

      if version == pin["canon_version"] do
        {:ok, version}
      else
        {:error,
         "CANON-1 version mismatch: expected #{pin["canon_version"]}, found #{version || "missing"} in #{manifest_path}"}
      end
    else
      {:ok, _} ->
        {:error, "contract manifest has an invalid structure at #{manifest_path}"}

      {:error, reason} ->
        {:error, "could not read contract manifest at #{manifest_path}: #{inspect(reason)}"}

      nil ->
        {:error, "CANON-1 entry is missing from #{manifest_path}"}

      _ ->
        {:error, "contract manifest has an invalid structure at #{manifest_path}"}
    end
  end

  defp ensure_tracer(path, tracer_path) do
    if File.regular?(Path.join(path, tracer_path)) do
      :ok
    else
      {:error, "required T0 tracer is missing from contracts checkout: #{tracer_path}"}
    end
  end
end
