from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from tools.contract_manifest import (
    ManifestError,
    active_repository_audit,
    build_manifest,
    dependency_closure,
    extract_bundle,
    verify_manifest,
    _contract_from_zip,
)


def _bundle(path: Path, members: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)


def _canon_zip(root: Path, pin: dict[str, object]) -> Path:
    bundle = root / "contracts/CANON-1/CANON-1_bundle_v2.0.2.zip"
    _valid_release_bundle(root, "CANON-1", "2.0.2", {
        "canonical_bundles": [pin], "canonical_exclusions": [],
    })
    return bundle


def _valid_release_bundle(
    root: Path, doc_id: str, version: str, contract_extra: dict[str, object] | None = None
) -> Path:
    bundle = root / f"contracts/{doc_id}/{doc_id}_bundle_v{version}.zip"
    wrapper = f"{doc_id}_bundle_v{version}"
    contract_name = f"{doc_id}_Contract_v{version}.json"
    gates_name = f"{doc_id}_Test_Gates_v{version}.json"
    contract_value = {
        "artifact_kind": "contract", "doc_id": doc_id, "version": version,
        **(contract_extra or {}),
    }
    gates_value = {
        "artifact_kind": "test_gates", "doc_id": f"{doc_id}-GATE", "version": version,
        "contract_ref": {"doc_id": doc_id, "version": version},
    }
    contract = json.dumps(contract_value).encode()
    gates = json.dumps(gates_value).encode()
    records = [
        {"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        for name, payload in ((contract_name, contract), (gates_name, gates))
    ]
    manifest = json.dumps({
        "artifact_kind": "bundle_manifest", "doc_id": doc_id, "version": version,
        "bundle": {"bundle_id": doc_id, "bundle_version": version}, "files": records,
    }).encode()
    _bundle(bundle, {
        f"{wrapper}/{contract_name}": contract,
        f"{wrapper}/{gates_name}": gates,
        f"{wrapper}/bundle.manifest.json": manifest,
    })
    return bundle


def test_extract_bundle_strips_one_common_wrapper_and_preserves_bytes(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.zip"
    payload = b'{"contract":true}\n'
    _bundle(bundle, {"x/contract.json": payload, "x/gates.json": b"{}"})

    artifacts = extract_bundle(bundle, tmp_path / "out")

    assert [row["extracted_path"] for row in artifacts] == ["contract.json", "gates.json"]
    assert (tmp_path / "out/contract.json").read_bytes() == payload


def test_extract_bundle_rejects_traversal_and_normalized_duplicates(tmp_path: Path) -> None:
    traversal = tmp_path / "traversal.zip"
    _bundle(traversal, {"root/../../escape": b"bad"})
    with pytest.raises(ManifestError, match="unsafe archive path"):
        extract_bundle(traversal, tmp_path / "out1")

    duplicate = tmp_path / "duplicate.zip"
    _bundle(duplicate, {"root/a/../same.json": b"one", "root/same.json": b"two"})
    with pytest.raises(ManifestError, match="unsafe archive path|duplicate normalized"):
        extract_bundle(duplicate, tmp_path / "out2")

    symlink = tmp_path / "symlink.zip"
    link = zipfile.ZipInfo("root/link")
    link.create_system = 3
    link.external_attr = (0o120777 << 16)
    with zipfile.ZipFile(symlink, "w") as archive:
        archive.writestr(link, "../../outside")
    with pytest.raises(ManifestError, match="unsafe symlink"):
        extract_bundle(symlink, tmp_path / "out3")


def test_manifest_is_deterministic_and_verifies_pins_and_parity(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    member_zip = _valid_release_bundle(root, "DOC-1", "1.0.0")
    digest = hashlib.sha256(member_zip.read_bytes()).hexdigest()
    canon = _canon_zip(root, {
        "doc_id": "DOC-1", "version": "1.0.0", "bundle_sha256": digest,
        "membership_status": "CANON_MEMBER",
        "artifacts": [],
    })
    (root / "contracts/DOC-1/extracted").mkdir(parents=True)
    (root / "contracts/CANON-1/extracted").mkdir(parents=True)
    # This test asks the builder to materialize extracts from the exact ZIP bytes.
    for path in (member_zip, canon):
        extract_bundle(path, path.parent / "extracted")

    first = build_manifest(root)
    second = build_manifest(root)

    assert first == second
    assert verify_manifest(root, first)["status"] == "VALID"
    doc = next(row for row in first["contracts"] if row["doc_id"] == "DOC-1")
    assert doc["membership"] == "CANON_MEMBER"
    assert all(row["sha256"] for row in doc["artifacts"])
    assert dependency_closure(root, first)["edge_count"] == 0
    (root / "contracts/manifest.json").write_text(
        json.dumps(first, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    audit = active_repository_audit(root)
    assert audit["status"] == "PASS"
    assert audit["summary"]["canon_member_count"] == 1

    extra = root / "contracts/DOC-1/extracted/extra.json"
    extra.write_bytes(b"extra")
    with pytest.raises(ManifestError, match="member set differs"):
        verify_manifest(root)


def test_manifest_rejects_pin_hash_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    doc = _valid_release_bundle(root, "DOC-1", "1.0.0")
    canon = _canon_zip(root, {
        "doc_id": "DOC-1", "version": "1.0.0", "bundle_sha256": "0" * 64,
        "membership_status": "CANON_MEMBER", "artifacts": [],
    })
    for path in (doc, canon):
        extract_bundle(path, path.parent / "extracted")

    with pytest.raises(ManifestError, match="CANON pin mismatch"):
        build_manifest(root)


def _identity_bundle(
    root: Path,
    *,
    version: str = "1.2.1",
    contract_filename_version: str = "1.2.1",
    gate_filename_version: str = "1.2.1",
    gate_ref_version: str = "1.2.1",
    outer_version: str = "1.2.1",
    wrapper_version: str = "1.2.1",
    gate_style: str = "modern",
) -> Path:
    doc_id = "DOC-1"
    bundle = root / f"contracts/{doc_id}/{doc_id}_bundle_v{outer_version}.zip"
    wrapper = f"{doc_id}_bundle_v{wrapper_version}"
    contract_name = f"{doc_id}_Contract_v{contract_filename_version}.json"
    gate_prefix = f"{doc_id}_Test_Gates" if gate_style == "modern" else f"{doc_id}-GATE_TestGates"
    gate_name = f"{gate_prefix}_v{gate_filename_version}.json"
    contract = json.dumps({
        "artifact_kind": "contract", "doc_id": doc_id, "version": version,
    }).encode()
    gates = json.dumps({
        "artifact_kind": "test_gates", "doc_id": f"{doc_id}-GATE", "version": version,
        "contract_ref": {"doc_id": doc_id, "version": gate_ref_version},
    }).encode()
    files = [
        {"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        for name, payload in ((contract_name, contract), (gate_name, gates))
    ]
    manifest = json.dumps({
        "artifact_kind": "bundle_manifest", "doc_id": doc_id, "version": version,
        "bundle": {"bundle_id": doc_id, "bundle_version": version}, "files": files,
    }).encode()
    _bundle(bundle, {
        f"{wrapper}/{contract_name}": contract,
        f"{wrapper}/{gate_name}": gates,
        f"{wrapper}/bundle.manifest.json": manifest,
    })
    return bundle


def test_active_identity_accepts_current_contract_and_both_gate_filename_styles(tmp_path: Path) -> None:
    for style in ("modern", "legacy"):
        bundle = _identity_bundle(tmp_path / style, gate_style=style)
        contract, _ = _contract_from_zip(bundle, validate_identity=True)
        assert contract["doc_id"] == "DOC-1"


@pytest.mark.parametrize("kwargs, message", [
    ({"contract_filename_version": "1.2.0"}, "contract filename identity"),
    ({"gate_filename_version": "1.2.0"}, "test-gates identity"),
    ({"gate_ref_version": "1.2.0"}, "test-gates identity"),
    ({"outer_version": "1.2.0"}, "outer ZIP identity"),
    ({"wrapper_version": "1.2.0"}, "archive wrapper identity"),
])
def test_active_identity_rejects_identity_mismatch(
    tmp_path: Path, kwargs: dict[str, str], message: str
) -> None:
    bundle = _identity_bundle(tmp_path, **kwargs)
    with pytest.raises(ManifestError, match=message):
        _contract_from_zip(bundle, validate_identity=True)


def test_active_identity_rejects_manifest_paths_with_wrong_version(tmp_path: Path) -> None:
    bundle = _identity_bundle(tmp_path)
    with zipfile.ZipFile(bundle, "r") as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    manifest_path = "DOC-1_bundle_v1.2.1/bundle.manifest.json"
    manifest = json.loads(entries[manifest_path])
    manifest["files"][0]["path"] = "DOC-1_Contract_v1.2.0.json"
    entries[manifest_path] = json.dumps(manifest).encode()
    _bundle(bundle, entries)
    with pytest.raises(ManifestError, match="bundle manifest file paths"):
        _contract_from_zip(bundle, validate_identity=True)


def test_active_identity_rejects_wrong_gate_doc_id(tmp_path: Path) -> None:
    bundle = _identity_bundle(tmp_path)
    with zipfile.ZipFile(bundle, "r") as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    gates_path = "DOC-1_bundle_v1.2.1/DOC-1_Test_Gates_v1.2.1.json"
    gates = json.loads(entries[gates_path])
    gates["doc_id"] = "OTHER-GATE"
    entries[gates_path] = json.dumps(gates).encode()
    _bundle(bundle, entries)
    with pytest.raises(ManifestError, match="test-gates identity"):
        _contract_from_zip(bundle, validate_identity=True)


@pytest.mark.parametrize("mutate", ["manifest_filename", "manifest_member_path"])
def test_active_identity_rejects_manifest_paths_that_do_not_name_actual_members(
    tmp_path: Path, mutate: str
) -> None:
    bundle = _identity_bundle(tmp_path)
    with zipfile.ZipFile(bundle, "r") as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    manifest_path = "DOC-1_bundle_v1.2.1/bundle.manifest.json"
    manifest = json.loads(entries[manifest_path])
    if mutate == "manifest_filename":
        entries.pop(manifest_path)
        entries["DOC-1_bundle_v1.2.1/other.manifest.json"] = json.dumps(manifest).encode()
    else:
        manifest["files"][0]["path"] = "elsewhere/DOC-1_Contract_v1.2.1.json"
        entries[manifest_path] = json.dumps(manifest).encode()
    _bundle(bundle, entries)
    with pytest.raises(ManifestError, match="manifest"):
        _contract_from_zip(bundle, validate_identity=True)
