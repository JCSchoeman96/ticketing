"""Tests for immutable accepted-release registry verification."""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import zipfile

import pytest

from tools.build_contract_release import build_contract_release
from tools.adopt_legacy_releases import (
    LegacyAdoptionError,
    _git_blob_sha256 as legacy_git_blob_sha256,
    build_legacy_adoption_record,
)
from tools.validate_accepted_releases import (
    _git_blob_sha256 as accepted_git_blob_sha256,
    validate_accepted_release_registry,
)

from test_build_contract_release import _source_tree


def test_git_blob_hashes_resolve_paths_from_nested_authority_root(tmp_path: Path) -> None:
    repository = tmp_path / "ticketing"
    authority_root = repository / "authority"
    relative_path = "contracts/CANON-1/CANON-1_bundle_v2.0.14.zip"
    artifact = authority_root / relative_path
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"accepted release bytes")
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Release Fixture"], cwd=repository, check=True)
    subprocess.run(["git", "add", "authority/contracts/CANON-1/CANON-1_bundle_v2.0.14.zip"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "accepted authority fixture"], cwd=repository, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
    expected = hashlib.sha256(artifact.read_bytes()).hexdigest()

    assert accepted_git_blob_sha256(authority_root, commit, relative_path) == expected
    assert legacy_git_blob_sha256(authority_root, commit, relative_path) == expected


def _repository_with_release(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    artifact = build_contract_release(
        _source_tree(root / "source", doc_id="DOC-1", version="1.2.3"),
        root / "build",
    )
    tracked_artifact = root / "release-artifacts/accepted/DOC-1_bundle_v1.2.3.zip"
    tracked_artifact.parent.mkdir(parents=True)
    tracked_artifact.write_bytes(artifact.read_bytes())
    digest = hashlib.sha256(tracked_artifact.read_bytes()).hexdigest()
    registry = {
        "format_version": 1,
        "acceptance_status": "ACCEPTED_RELEASE",
        "canonical_pin_status": "not_pinned",
        "releases": [
            {
                "doc_id": "DOC-1",
                "version": "1.2.3",
                "path": "release-artifacts/accepted/DOC-1_bundle_v1.2.3.zip",
                "sha256": digest,
                "size_bytes": tracked_artifact.stat().st_size,
                "status": "ACCEPTED_RELEASE",
                "acceptance_origin": "deterministic_build",
                "canonical_pin_status": "not_pinned",
            }
        ],
    }
    registry_path = root / "release-artifacts/accepted/acceptance.json"
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Release Fixture"], cwd=root, check=True)
    subprocess.run(
        ["git", "add", "release-artifacts/accepted/acceptance.json", str(tracked_artifact.relative_to(root))],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "commit", "-q", "-m", "accepted artifact fixture"], cwd=root, check=True)
    return root, tracked_artifact, registry_path


def _rewrite_zip_timestamps(artifact: Path) -> None:
    with zipfile.ZipFile(artifact, "r") as source:
        entries = [(info.filename, source.read(info)) for info in source.infolist()]
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as target:
        for name, payload in entries:
            info = zipfile.ZipInfo(name, date_time=(2023, 5, 6, 7, 8, 10))
            info.compress_type = zipfile.ZIP_STORED
            target.writestr(info, payload)
    artifact.write_bytes(output.getvalue())


def test_accepted_release_registry_validates_tracked_hash_and_bundle(tmp_path: Path) -> None:
    root, _, _ = _repository_with_release(tmp_path)

    report = validate_accepted_release_registry(root)

    assert report["status"] == "VALID"
    assert report["release_count"] == 1
    assert report["releases"][0]["doc_id"] == "DOC-1"
    assert report["releases"][0]["bundle_validation"]["status"] == "VALID"


def test_accepted_release_registry_rejects_modified_bytes(tmp_path: Path) -> None:
    root, artifact, _ = _repository_with_release(tmp_path)
    artifact.write_bytes(artifact.read_bytes() + b"changed")

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert any("SHA-256 mismatch" in error for error in report["errors"])


def test_accepted_release_registry_rejects_untracked_artifact(tmp_path: Path) -> None:
    root, artifact, _ = _repository_with_release(tmp_path)
    payload = artifact.read_bytes()
    subprocess.run(["git", "rm", "-q", str(artifact.relative_to(root))], cwd=root, check=True)
    artifact.write_bytes(payload)

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert any("not Git-tracked" in error for error in report["errors"])


def test_accepted_release_registry_rejects_duplicate_identity(tmp_path: Path) -> None:
    root, _, registry_path = _repository_with_release(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["releases"].append(dict(registry["releases"][0]))
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert any("duplicate accepted identity" in error for error in report["errors"])


def test_accepted_release_registry_requires_acceptance_origin_and_pin_status(tmp_path: Path) -> None:
    root, _, registry_path = _repository_with_release(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["releases"][0].pop("acceptance_origin")
    registry["releases"][0].pop("canonical_pin_status")
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert any("acceptance_origin" in error for error in report["errors"])


def test_legacy_adoption_requires_explicit_noncanonical_pin_status(tmp_path: Path) -> None:
    root, _, registry_path = _repository_with_release(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    record = registry["releases"][0]
    record.update(
        {
            "acceptance_origin": "legacy_adoption",
            "validation_status": "VALID",
            "selection_basis": ["synthetic selected release"],
            "source_commit": "a" * 40,
            "tracked_at_commit": "b" * 40,
        }
    )
    record.pop("canonical_pin_status")
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert any("canonical_pin_status" in error for error in report["errors"])


def test_accepted_release_registry_rejects_same_identity_with_different_hashes(tmp_path: Path) -> None:
    root, artifact, registry_path = _repository_with_release(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    alternate = build_contract_release(
        _source_tree(
            root / "alternate-source",
            doc_id="DOC-1",
            version="1.2.3",
            contract_summary="A different artifact with the same release identity",
        ),
        root / "alternate-build",
    )
    alternate_path = root / "release-artifacts/accepted/DOC-1_bundle_v1.2.3_alternate.zip"
    alternate_path.write_bytes(alternate.read_bytes())
    digest = hashlib.sha256(alternate_path.read_bytes()).hexdigest()
    registry["releases"].append(
        {
            **registry["releases"][0],
            "path": str(alternate_path.relative_to(root)),
            "sha256": digest,
            "size_bytes": alternate_path.stat().st_size,
        }
    )
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", str(alternate_path.relative_to(root))], cwd=root, check=True
    )
    subprocess.run(["git", "commit", "-q", "-m", "alternate release identity fixture"], cwd=root, check=True)

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert any("duplicate accepted identity" in error for error in report["errors"])
    assert any("different SHA-256" in error for error in report["errors"])


def test_legacy_adopted_bundle_does_not_require_deterministic_zip_metadata(tmp_path: Path) -> None:
    root, artifact, registry_path = _repository_with_release(tmp_path)
    _rewrite_zip_timestamps(artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    record = registry["releases"][0]
    record.update(
        {
            "sha256": digest,
            "size_bytes": artifact.stat().st_size,
            "acceptance_origin": "legacy_adoption",
            "validation_status": "VALID_WITH_WARNING",
            "selection_basis": ["selected tracked historical release"],
            "tracked_provenance": "adopted without rebuilding",
        }
    )
    subprocess.run(["git", "add", str(artifact.relative_to(root))], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "legacy artifact metadata fixture"], cwd=root, check=True)
    tracked_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    record["source_commit"] = tracked_commit
    record["tracked_at_commit"] = tracked_commit
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(registry_path.relative_to(root))], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "legacy adoption record fixture"], cwd=root, check=True)

    report = validate_accepted_release_registry(root)

    assert report["status"] == "VALID", report["errors"]
    assert report["releases"][0]["bundle_validation"]["status"] in {"VALID", "VALID_WITH_WARNING"}


def test_legacy_acceptance_rejects_tracked_commit_with_different_artifact_bytes(tmp_path: Path) -> None:
    root, artifact, registry_path = _repository_with_release(tmp_path)
    original_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    _rewrite_zip_timestamps(artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    subprocess.run(["git", "add", str(artifact.relative_to(root))], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "legacy bytes fixture"], cwd=root, check=True)
    artifact_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    record = registry["releases"][0]
    record.update(
        {
            "sha256": digest,
            "size_bytes": artifact.stat().st_size,
            "acceptance_origin": "legacy_adoption",
            "validation_status": "VALID_WITH_WARNING",
            "selection_basis": ["selected tracked historical release"],
            "source_commit": artifact_commit,
            "tracked_at_commit": original_commit,
            "tracked_provenance": "adopted without rebuilding",
        }
    )
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(registry_path.relative_to(root))], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "legacy adoption record fixture"], cwd=root, check=True)

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert any("tracked_at_commit" in error for error in report["errors"])


def test_legacy_adoption_records_exact_tracked_zip_without_rebuilding(tmp_path: Path) -> None:
    root, artifact, _ = _repository_with_release(tmp_path)
    _rewrite_zip_timestamps(artifact)
    subprocess.run(["git", "add", str(artifact.relative_to(root))], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "legacy metadata fixture"], cwd=root, check=True)
    original_bytes = artifact.read_bytes()
    original_hash = hashlib.sha256(original_bytes).hexdigest()
    candidate = {
        "doc_id": "DOC-1",
        "version": "1.2.3",
        "source_path": str(artifact.relative_to(root)),
        "git_tracked": True,
        "audit_status": "VALID_WITH_WARNING",
        "resolution_outcome": "selected",
        "zip_sha256": original_hash,
        "validation": {"status": "VALID_WITH_WARNING", "errors": [], "warnings": ["legacy name"]},
    }

    record = build_legacy_adoption_record(
        root,
        candidate,
        selection_basis=["tracked selection evidence"],
        tracked_at_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        accepted_on="2026-10-09",
    )

    assert artifact.read_bytes() == original_bytes
    assert record["sha256"] == original_hash
    assert record["acceptance_origin"] == "legacy_adoption"
    assert record["canonical_pin_status"] == "not_pinned"
    assert record["validation_status"] == "VALID_WITH_WARNING"
    assert record["source_commit"]
    assert "builder" not in record


def test_legacy_adoption_rejects_invalid_or_unselected_candidate(tmp_path: Path) -> None:
    root, artifact, _ = _repository_with_release(tmp_path)
    candidate = {
        "doc_id": "DOC-1",
        "version": "1.2.3",
        "source_path": str(artifact.relative_to(root)),
        "git_tracked": True,
        "audit_status": "INVALID",
        "resolution_outcome": "selected",
        "zip_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "validation": {"status": "INVALID", "errors": ["known defect"]},
    }

    with pytest.raises(LegacyAdoptionError, match="not individually valid"):
        build_legacy_adoption_record(
            root,
            candidate,
            selection_basis=["synthetic test"],
            tracked_at_commit="a" * 40,
            accepted_on="2026-10-09",
        )


def test_accepted_release_registry_rejects_traversal_path(tmp_path: Path) -> None:
    root, _, registry_path = _repository_with_release(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["releases"][0]["path"] = "../outside.zip"
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert any("unsafe or missing repository-relative path" in error for error in report["errors"])


def test_accepted_release_registry_rejects_empty_registry(tmp_path: Path) -> None:
    root, _, registry_path = _repository_with_release(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["releases"] = []
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert "accepted registry must contain at least one accepted release" in report["errors"]


def test_accepted_release_registry_rejects_symlinked_registry(tmp_path: Path) -> None:
    root, _, registry_path = _repository_with_release(tmp_path)
    outside_registry = tmp_path / "outside-acceptance.json"
    outside_registry.write_bytes(registry_path.read_bytes())
    registry_path.unlink()
    registry_path.symlink_to(outside_registry)

    report = validate_accepted_release_registry(root)

    assert report["status"] == "INVALID"
    assert "accepted registry must not be a symbolic link" in report["errors"]
