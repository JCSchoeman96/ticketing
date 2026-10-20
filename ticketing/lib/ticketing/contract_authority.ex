defmodule Ticketing.ContractAuthority do
  @moduledoc """
  Verifies the canonical authority stored in this repository.
  """

  @repository_root Path.expand("../../..", __DIR__)
  @authority_root Path.join(@repository_root, "authority")

  def verify(authority_root \\ @authority_root) when is_binary(authority_root) do
    authority_root = Path.expand(authority_root)

    with :ok <- ensure_authority_directory(authority_root),
         {:ok, canon_version} <- manifest_canon_version(authority_root),
         {:ok, active_tracer} <- active_tracer(authority_root),
         :ok <- run_validators(authority_root) do
      {:ok,
       %{
         path: authority_root,
         canon_version: canon_version,
         active_tracer: active_tracer
       }}
    end
  end

  defp ensure_authority_directory(path) do
    if File.dir?(path) do
      :ok
    else
      {:error, "authority directory is missing: #{path}"}
    end
  end

  defp manifest_canon_version(authority_root) do
    manifest_path = Path.join(authority_root, "contracts/manifest.json")

    with {:ok, contents} <- File.read(manifest_path),
         {:ok, %{"contracts" => contracts}} when is_list(contracts) <- Jason.decode(contents),
         %{"version" => version, "membership" => "CANON_INDEX"} when is_binary(version) <-
           Enum.find(contracts, &(&1["doc_id"] == "CANON-1")) do
      {:ok, version}
    else
      {:ok, _} ->
        {:error, "contract manifest has no valid CANON-1 record at #{manifest_path}"}

      {:error, :enoent} ->
        {:error, "contract manifest is missing at #{manifest_path}"}

      {:error, %Jason.DecodeError{} = error} ->
        {:error, "contract manifest is invalid at #{manifest_path}: #{Exception.message(error)}"}

      {:error, reason} when is_atom(reason) ->
        {:error,
         "could not read contract manifest at #{manifest_path}: #{:file.format_error(reason)}"}

      nil ->
        {:error, "CANON-1 record is missing from #{manifest_path}"}

      _ ->
        {:error, "contract manifest has no valid CANON-1 record at #{manifest_path}"}
    end
  end

  defp active_tracer(authority_root) do
    roadmap_path = Path.join(authority_root, "planning/ROADMAP.md")

    with {:ok, roadmap} <- File.read(roadmap_path),
         {:ok, tracer} <- active_tracer_link(roadmap),
         :ok <- ensure_tracer_links(authority_root, roadmap_path, roadmap) do
      {:ok, Path.join("planning", tracer)}
    else
      {:error, :missing_active_tracer} ->
        {:error, "ROADMAP does not mark an active tracer link in #{roadmap_path}"}

      {:error, :multiple_active_tracers} ->
        {:error, "ROADMAP marks multiple tracer links active in #{roadmap_path}"}

      {:error, :invalid_tracer_path} ->
        {:error,
         "ROADMAP active tracer link must stay within planning/tracers/ in #{roadmap_path}"}

      {:error, :enoent} ->
        {:error, "ROADMAP is missing at #{roadmap_path}"}

      {:error, reason} when is_atom(reason) ->
        {:error, "could not read ROADMAP at #{roadmap_path}: #{:file.format_error(reason)}"}

      {:error, message} ->
        {:error, message}
    end
  end

  defp roadmap_tracer_links(roadmap) do
    Regex.scan(~r/\]\((tracers\/[^)\s]+\.md)\)/, roadmap, capture: :all_but_first)
    |> Enum.map(&List.first/1)
    |> Enum.uniq()
  end

  @doc false
  def active_tracer_link(roadmap) when is_binary(roadmap) do
    case Regex.scan(
           ~r/\[([^\]]*\bactive\b[^\]]*)\]\((tracers\/[^)\s]+\.md)\)/i,
           roadmap,
           capture: :all_but_first
         ) do
      [[_label, tracer]] ->
        if safe_tracer_path?(tracer) do
          {:ok, tracer}
        else
          {:error, :invalid_tracer_path}
        end

      [] ->
        {:error, :missing_active_tracer}

      _ ->
        {:error, :multiple_active_tracers}
    end
  end

  defp safe_tracer_path?(tracer) do
    segments = String.split(tracer, "/", trim: false)

    not String.contains?(tracer, "\\") and
      match?(["tracers", _ | _], segments) and
      Enum.all?(Enum.drop(segments, 1), &(&1 not in ["", ".", ".."]))
  end

  defp ensure_tracer_links(authority_root, roadmap_path, roadmap) do
    missing =
      roadmap
      |> roadmap_tracer_links()
      |> Enum.reject(&File.regular?(Path.join([authority_root, "planning", &1])))

    case missing do
      [] ->
        :ok

      _ ->
        {:error,
         "ROADMAP references missing tracer files: #{Enum.join(missing, ", ")} in #{roadmap_path}"}
    end
  end

  defp run_validators(authority_root) do
    with {:ok, python} <- python_executable() do
      audit_id = System.unique_integer([:positive])
      audit_json = Path.join(System.tmp_dir!(), "ticketing-authority-audit-#{audit_id}.json")
      audit_markdown = Path.join(System.tmp_dir!(), "ticketing-authority-audit-#{audit_id}.md")

      validators = [
        {"contract manifest verification",
         ["tools/contract_manifest.py", "verify", "--root", "."]},
        {"CANON verification", ["tools/generate_canon.py", "verify", "--root", "."]},
        {"strict canonical audit",
         [
           "tools/reconcile_contracts.py",
           "audit",
           "--canonical",
           "--strict",
           "--root",
           ".",
           "--json-output",
           audit_json,
           "--markdown-output",
           audit_markdown
         ]}
      ]

      result =
        Enum.reduce_while(validators, :ok, fn validator, :ok ->
          run_validator(validator, python, authority_root)
        end)

      File.rm(audit_json)
      File.rm(audit_markdown)
      result
    end
  rescue
    error in ErlangError ->
      {:error, "could not run authority validation: #{Exception.message(error)}"}
  end

  defp run_validator({label, args}, python, authority_root) do
    case System.cmd(python, args, cd: authority_root, stderr_to_stdout: true) do
      {_output, 0} ->
        {:cont, :ok}

      {output, status} ->
        {:halt, {:error, "#{label} failed with exit code #{status}:\n#{String.trim(output)}"}}
    end
  end

  defp python_executable do
    executable =
      System.get_env("PYTHON") || System.find_executable("python3") ||
        System.find_executable("python")

    if executable do
      {:ok, executable}
    else
      {:error, "Python is required to run canonical authority validation"}
    end
  end
end
