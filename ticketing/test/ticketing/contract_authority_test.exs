defmodule Ticketing.ContractAuthorityTest do
  use ExUnit.Case, async: true

  alias Ticketing.ContractAuthority

  @pin_path Path.expand("../../../contracts/authority.json", __DIR__)

  test "checked-in pin names the implementation's reviewed contract authority" do
    assert {:ok, pin} = ContractAuthority.load_pin(@pin_path)
    assert pin["repository"] == "JCSchoeman96/ticketing-contracts"
    assert pin["reviewed_commit"] == "cc335793e7a542e44938883f87cc96f796a4fe32"
    assert pin["canon_doc_id"] == "CANON-1"
    assert pin["canon_version"] == "2.0.10"
    assert pin["manifest_path"] == "contracts/manifest.json"
    assert pin["t0_tracer_path"] == "planning/tracers/T0-tenant-scoped-ga-pending-sale.md"
  end

  test "active implementation authority does not include the retired CANON 0.9.41 suite" do
    root = Path.expand("../../..", __DIR__)

    refute File.exists?(Path.join(root, "contracts/bundles/CANON-1_bundle_v0.9.41_JSON_ONLY.zip"))
    refute File.exists?(Path.join(root, "contracts/working/canon_patch/CANON-1_bundle_v0.9.41"))
    refute File.exists?(Path.join(root, "contracts/tools/ci_contract_gate_strict_v2.7.0.py"))
    refute File.exists?(Path.join(root, "Makefile"))
  end

  test "authority verification reports a missing configured checkout" do
    assert {:error, message} = ContractAuthority.verify_checkout("/path/that/does/not/exist", %{})
    assert message =~ "not a Git repository"
  end

  test "authority verification rejects a manifest with the wrong CANON version" do
    {checkout, pin} = fixture_checkout("0.9.41")
    on_exit(fn -> File.rm_rf!(checkout) end)

    assert {:error, message} = ContractAuthority.verify_checkout(checkout, pin)
    assert message =~ "CANON-1 version mismatch"
    assert message =~ "expected 2.0.10"
    assert message =~ "found 0.9.41"
  end

  test "authority verification accepts the pinned commit and required tracer" do
    {checkout, pin} = fixture_checkout("2.0.10")
    on_exit(fn -> File.rm_rf!(checkout) end)

    assert {:ok, result} = ContractAuthority.verify_checkout(checkout, pin)
    assert result.commit == pin["reviewed_commit"]
    assert result.canon_version == "2.0.10"
    assert result.path == checkout
  end

  defp fixture_checkout(canon_version) do
    checkout =
      Path.join(System.tmp_dir!(), "ticketing-contracts-#{System.unique_integer([:positive])}")

    File.mkdir_p!(Path.join(checkout, "contracts"))
    File.mkdir_p!(Path.join(checkout, "planning/tracers"))

    manifest = %{
      "contracts" => [
        %{"doc_id" => "CANON-1", "version" => canon_version}
      ]
    }

    File.write!(Path.join(checkout, "contracts/manifest.json"), Jason.encode!(manifest))
    File.write!(Path.join(checkout, "planning/tracers/T0-tenant-scoped-ga-pending-sale.md"), "T0")

    git!(checkout, ["init", "--quiet"])
    git!(checkout, ["config", "user.email", "test@example.invalid"])
    git!(checkout, ["config", "user.name", "Ticketing test"])
    git!(checkout, ["add", "."])
    git!(checkout, ["commit", "--quiet", "-m", "fixture"])
    {commit, 0} = git!(checkout, ["rev-parse", "HEAD"])

    pin = %{
      "reviewed_commit" => String.trim(commit),
      "manifest_path" => "contracts/manifest.json",
      "canon_doc_id" => "CANON-1",
      "canon_version" => "2.0.10",
      "t0_tracer_path" => "planning/tracers/T0-tenant-scoped-ga-pending-sale.md"
    }

    {checkout, pin}
  end

  defp git!(directory, args) do
    System.cmd("git", args, cd: directory, stderr_to_stdout: true)
  end
end
