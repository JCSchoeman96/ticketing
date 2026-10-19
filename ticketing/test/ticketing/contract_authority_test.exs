defmodule Ticketing.ContractAuthorityTest do
  use ExUnit.Case

  alias Ticketing.ContractAuthority

  @authority_path Path.expand("../../../authority", __DIR__)

  test "verifies the in-repository authority without a sibling checkout" do
    previous_path = System.get_env("TICKETING_CONTRACTS_PATH")
    System.put_env("TICKETING_CONTRACTS_PATH", "/path/that/does/not/exist")

    on_exit(fn ->
      if previous_path do
        System.put_env("TICKETING_CONTRACTS_PATH", previous_path)
      else
        System.delete_env("TICKETING_CONTRACTS_PATH")
      end
    end)

    assert {:ok, result} = ContractAuthority.verify()
    assert result.path == @authority_path
    assert result.canon_version == manifest_canon_version()
    assert File.regular?(Path.join(@authority_path, result.active_tracer))
  end

  test "reports a missing in-repository authority directory" do
    assert {:error, message} = ContractAuthority.verify("/path/that/does/not/exist")
    assert message =~ "authority directory is missing"
  end

  test "selects the tracer explicitly marked active in the roadmap" do
    roadmap = """
    Historical: [an earlier tracer](tracers/T0-old.md).
    Current: [the active T0 tracer](tracers/T0-current.md).
    """

    assert {:ok, "tracers/T0-current.md"} = ContractAuthority.active_tracer_link(roadmap)
  end

  test "rejects a roadmap with no unique active tracer link" do
    assert {:error, :missing_active_tracer} =
             ContractAuthority.active_tracer_link("No tracer link here.")

    roadmap = """
    [active tracer one](tracers/one.md)
    [active tracer two](tracers/two.md)
    """

    assert {:error, :multiple_active_tracers} = ContractAuthority.active_tracer_link(roadmap)
  end

  test "rejects an active tracer link that escapes the tracer directory" do
    roadmap = "[active tracer](tracers/../README.md)"

    assert {:error, :invalid_tracer_path} = ContractAuthority.active_tracer_link(roadmap)
  end

  defp manifest_canon_version do
    manifest_path = Path.join(@authority_path, "contracts/manifest.json")
    {:ok, manifest} = manifest_path |> File.read!() |> Jason.decode()
    canon = Enum.find(manifest["contracts"], &(&1["doc_id"] == "CANON-1"))
    canon["version"]
  end
end
