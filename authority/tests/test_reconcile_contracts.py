"""Synthetic ZIP fixtures for the read-only contract reconciliation tool."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

import pytest

from tools.reconcile_contracts import (
    audit_repository,
    build_dependency_closure,
    classify_file,
    CS0_DEPENDENCY_EDGE_TYPES,
    collect_canon_pin_validation,
    discover_extracted_bundles,
    document_fields,
    main,
    resolve_contract,
    safe_archive_path,
    semver_key,
    workspace_files,
)


SUITE_SCHEMA = "CS-0@3.0.1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_reconciler_dependency_rules_match_ratified_cs0_candidate() -> None:
    contract = json.loads(
        (REPOSITORY_ROOT / "release-src/current/CS-0/3.0.1/contract.json").read_bytes()
    )
    gates = json.loads(
        (REPOSITORY_ROOT / "release-src/current/CS-0/3.0.1/test-gates.json").read_bytes()
    )
    expected_edge_types = set(
        contract["schemas"]["contract"]["properties"]["dependencies"]["items"]["properties"]["edge_type"]["enum"]
    )
    dependency_report = build_dependency_closure({})

    assert CS0_DEPENDENCY_EDGE_TYPES == expected_edge_types
    assert "foundation" not in expected_edge_types
    assert dependency_report["rule_authority"]["schema_version"] == "CS-0@3.0.1"
    assert dependency_report["rule_authority"]["status"] == "owner_ratified_successor_source_candidate"
    assert dependency_report["rule_authority"]["schema_source"].startswith(
        "release-src/current/CS-0/3.0.1/"
    )
    assert any(
        gate["id"] == "CS-0-P0-DEPENDENCY-EDGE-SEMANTICS"
        for gate in gates["gates"]
    )


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _artifact_record(path: str, payload: bytes) -> dict[str, object]:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def make_bundle(
    root: Path,
    *,
    doc_id: str = "DOC-1",
    version: str = "1.0.0",
    filename: str | None = None,
    contract_doc_id: str | None = None,
    contract_version: str | None = None,
    contract_filename_version: str | None = None,
    gate_doc_id: str | None = None,
    gate_version: str | None = None,
    gate_contract_ref_doc_id: str | None = None,
    gate_contract_ref_version: str | None = None,
    manifest_doc_id: str | None = None,
    manifest_version: str | None = None,
    manifest_bundle_id: str | None = None,
    manifest_bundle_version: str | None = None,
    suite_schema: str = SUITE_SCHEMA,
    gate_suite_schema: str | None = None,
    manifest_suite_schema: str | None = None,
    manifest_hash_override: str | None = None,
    manifest_size_override: int | None = None,
    contract_summary: str = "same contract body",
    dependencies: list[dict[str, object]] | None = None,
    dependencies_is_null: bool = False,
    dependencies_omitted: bool = False,
    missing: set[str] | None = None,
    extra_files: dict[str, bytes] | None = None,
    unmanifested_files: dict[str, bytes] | None = None,
    zip_year: int = 2026,
) -> Path:
    """Create a real three-artifact bundle ZIP with selectable defects."""

    missing = missing or set()
    extra_files = extra_files or {}
    unmanifested_files = unmanifested_files or {}
    bundle_name = f"{doc_id}_bundle_v{version}"
    bundle_root = f"{bundle_name}/"
    contract_path = f"{doc_id}_Contract_v{contract_filename_version or contract_version or version}.json"
    gates_path = f"{doc_id}_Test_Gates_v{gate_version or version}.json"

    contract = {
        "artifact_kind": "contract",
        "artifact_name": contract_path,
        "doc_id": contract_doc_id or doc_id,
        "version": contract_version or version,
        "schema_version": "contract-suite/1.0",
        "suite_schema": suite_schema,
        "summary": contract_summary,
        "supersedes": "0.9.0",
    }
    if not dependencies_omitted:
        contract["dependencies"] = None if dependencies_is_null else (dependencies or [])
    contract_bytes = _json_bytes(contract)

    gates = {
        "artifact_kind": "test_gates",
        "artifact_name": gates_path,
        "doc_id": gate_doc_id or f"{doc_id}-GATE",
        "version": gate_version or version,
        "contract_ref": {
            "doc_id": gate_contract_ref_doc_id or doc_id,
            "version": gate_contract_ref_version or version,
        },
        "schema_version": "test-gates/1.0",
        "suite_schema": gate_suite_schema or suite_schema,
        "gates": [
            {
                "id": "DOC-1-001",
                "assertions": [
                    {
                        "type": "suite_schema_matches",
                        "details": {"expected": gate_suite_schema or suite_schema},
                    }
                ],
            }
        ],
    }
    gates_bytes = _json_bytes(gates)

    manifest_file_records = [
        _artifact_record(contract_path, contract_bytes),
        _artifact_record(gates_path, gates_bytes),
    ]
    for name, payload in sorted(extra_files.items()):
        manifest_file_records.append(_artifact_record(name, payload))
    if manifest_hash_override:
        manifest_file_records[0]["sha256"] = manifest_hash_override
    if manifest_size_override is not None:
        manifest_file_records[0]["bytes"] = manifest_size_override

    manifest = {
        "artifact_kind": "bundle_manifest",
        "schema_version": "bundle-manifest/1.0",
        "doc_id": manifest_doc_id or doc_id,
        "version": manifest_version or version,
        "bundle": {
            "bundle_id": manifest_bundle_id or doc_id,
            "bundle_version": manifest_bundle_version or manifest_version or version,
        },
        "suite_schema": manifest_suite_schema or suite_schema,
        "files": manifest_file_records,
    }
    manifest_bytes = _json_bytes(manifest)

    archive_name = filename or f"{doc_id}_bundle_v{version}.zip"
    archive_path = root / archive_name
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    date_time = (zip_year, 1, 2, 3, 4, 6)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if "contract" not in missing:
            info = zipfile.ZipInfo(bundle_root + contract_path, date_time=date_time)
            archive.writestr(info, contract_bytes)
        if "gates" not in missing:
            info = zipfile.ZipInfo(bundle_root + gates_path, date_time=date_time)
            archive.writestr(info, gates_bytes)
        if "manifest" not in missing:
            info = zipfile.ZipInfo(bundle_root + "bundle.manifest.json", date_time=date_time)
            archive.writestr(info, manifest_bytes)
        for name, payload in sorted(extra_files.items()):
            info = zipfile.ZipInfo(bundle_root + name, date_time=date_time)
            archive.writestr(info, payload)
        for name, payload in sorted(unmanifested_files.items()):
            info = zipfile.ZipInfo(bundle_root + name, date_time=date_time)
            archive.writestr(info, payload)
    return archive_path


def write_current_schema_authority(root: Path) -> None:
    (root / "CONTRACT_AUTHORITY_INDEX_v1.39.0.md").write_text(
        "# Contract Authority Index\n\n"
        "This index is advisory. Under CS-0@3.0.1, canonical artifact families are defined.\n",
        encoding="utf-8",
    )


def initialize_git_fixture(root: Path, tracked_files: list[str] | None = None) -> None:
    """Commit a minimal fixture so canonical scans have a tracked file set."""

    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Contract Fixture"], cwd=root, check=True)
    (root / ".gitignore").write_text(".staging/\n", encoding="utf-8")
    files = tracked_files or [
        ".gitignore",
        "CONTRACT_AUTHORITY_INDEX_v1.39.0.md",
        "DOC-1_bundle_v1.0.0.zip",
    ]
    subprocess.run(["git", "add", *files], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "tracked canonical fixture"],
        cwd=root,
        check=True,
    )


def contract_record(report: dict[str, object], doc_id: str = "DOC-1") -> dict[str, object]:
    return report["contracts"][doc_id]  # type: ignore[index,return-value]


def test_selects_single_valid_bundle(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path)

    report = audit_repository(tmp_path)

    selected = contract_record(report)
    assert selected["selected_version"] == "1.0.0"
    assert selected["status"] == "selected"
    candidate = selected["selected_candidate"]
    assert candidate["validation"]["status"] == "VALID"


def test_canonical_audit_ignores_ignored_staging_and_untracked_zips(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    tracked_zip = make_bundle(tmp_path, version="1.0.0")
    initialize_git_fixture(tmp_path)

    before = audit_repository(tmp_path, scan_mode="canonical")
    make_bundle(tmp_path / ".staging", doc_id="STAGED-1", version="9.9.9")
    make_bundle(tmp_path, doc_id="UNTRACKED-1", version="9.9.9")
    after = audit_repository(tmp_path, scan_mode="canonical")
    forensic = audit_repository(tmp_path, scan_mode="forensic")

    assert before["summary"] == after["summary"]
    assert set(before["contracts"]) == set(after["contracts"]) == {"DOC-1"}
    assert after["summary"]["zip_files_inspected"] == 1
    assert forensic["summary"]["zip_files_inspected"] == 3
    assert tracked_zip.name in after["all_contract_candidates"][0]["source_path"]


def test_canonical_audit_requires_git_repository(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path)

    with pytest.raises(ValueError, match="Git worktree"):
        audit_repository(tmp_path, scan_mode="canonical")


def test_accepted_cs0_schema_release_overrides_advisory_index_claim(tmp_path: Path) -> None:
    (tmp_path / "CONTRACT_AUTHORITY_INDEX_v1.39.0.md").write_text(
        "# Contract Authority Index\n\n"
        "This index is advisory. Under CS-0@3.0.0, canonical artifact families are defined.\n",
        encoding="utf-8",
    )
    cs_zip = make_bundle(
        tmp_path / "release-artifacts/accepted",
        doc_id="CS-0",
        version="3.0.1",
        suite_schema="CS-0@3.0.1",
    )
    make_bundle(tmp_path, doc_id="DOC-1", suite_schema="CS-0@3.0.1")
    from tools.reconcile_contracts import sha256_file

    accepted_path = "release-artifacts/accepted/CS-0_bundle_v3.0.1.zip"
    (tmp_path / "release-artifacts/accepted/acceptance.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "acceptance_status": "ACCEPTED_RELEASE",
                "schema_validation_authority": {
                    "doc_id": "CS-0",
                    "version": "3.0.1",
                    "path": accepted_path,
                    "sha256": sha256_file(cs_zip),
                    "scope": "schema validation only",
                },
                "releases": [
                    {
                        "doc_id": "CS-0",
                        "version": "3.0.1",
                        "path": accepted_path,
                        "sha256": sha256_file(cs_zip),
                        "status": "ACCEPTED_RELEASE",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    initialize_git_fixture(
        tmp_path,
        [
            ".gitignore",
            "CONTRACT_AUTHORITY_INDEX_v1.39.0.md",
            "DOC-1_bundle_v1.0.0.zip",
            accepted_path,
            "release-artifacts/accepted/acceptance.json",
        ],
    )

    report = audit_repository(tmp_path, scan_mode="canonical")

    assert report["current_suite_schema_evidence"]["status"] == "resolved"
    assert report["current_suite_schema_evidence"]["selected_suite_schema"] == "CS-0@3.0.1"
    assert report["current_suite_schema_evidence"]["overridden_advisory_versions"] == ["3.0.0"]
    assert contract_record(report)["selected_candidate"]["validation"]["status"] == "VALID"
    assert report["contracts"]["CS-0"]["status"] == "selected"
    assert report["contracts"]["CS-0"]["selected_version"] == "3.0.1"
    assert report["contracts"]["CS-0"]["selected_candidate"]["validation"]["status"] == "VALID"


def test_tracked_historical_suite_schema_is_accepted_with_warning(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, suite_schema="CS-0@3.0.0")
    historical_source = tmp_path / "release-src/ratification/CS-0/3.0.0/contract.json"
    historical_source.parent.mkdir(parents=True)
    historical_source.write_text(
        json.dumps(
            {
                "artifact_kind": "contract",
                "doc_id": "CS-0",
                "version": "3.0.0",
                "suite_schema": "CS-0@3.0.0",
                "schemas": {"contract": {}, "test_gates": {}, "bundle_manifest": {}},
            }
        ),
        encoding="utf-8",
    )
    initialize_git_fixture(
        tmp_path,
        [
            ".gitignore",
            "CONTRACT_AUTHORITY_INDEX_v1.39.0.md",
            "DOC-1_bundle_v1.0.0.zip",
            "release-src/ratification/CS-0/3.0.0/contract.json",
        ],
    )

    report = audit_repository(tmp_path, scan_mode="canonical")
    candidate = contract_record(report)["selected_candidate"]

    assert candidate["validation"]["status"] == "VALID_WITH_WARNING"
    assert any("supported historical suite schema CS-0@3.0.0" in item for item in candidate["validation"]["warnings"])


def test_historical_bundle_is_validated_against_its_tracked_schema(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, suite_schema="CS-0@3.0.0")
    historical_source = tmp_path / "release-src/ratification/CS-0/3.0.0/contract.json"
    historical_source.parent.mkdir(parents=True)
    historical_source.write_text(
        json.dumps(
            {
                "artifact_kind": "contract",
                "doc_id": "CS-0",
                "version": "3.0.0",
                "suite_schema": "CS-0@3.0.0",
                "schemas": {
                    "contract": {"type": "object", "required": ["required_by_historical_schema"]},
                    "test_gates": {"type": "object"},
                    "bundle_manifest": {"type": "object"},
                },
            }
        ),
        encoding="utf-8",
    )
    initialize_git_fixture(
        tmp_path,
        [
            ".gitignore",
            "CONTRACT_AUTHORITY_INDEX_v1.39.0.md",
            "DOC-1_bundle_v1.0.0.zip",
            "release-src/ratification/CS-0/3.0.0/contract.json",
        ],
    )

    report = audit_repository(tmp_path, scan_mode="canonical")
    candidate = contract_record(report)["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("required_by_historical_schema" in error for error in candidate["validation"]["errors"])


def test_selects_highest_valid_semver_not_newer_file_timestamp(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    older = make_bundle(tmp_path, version="4.9.9")
    newer = make_bundle(tmp_path, version="4.10.0")
    os.utime(older, (2_000_000_000, 2_000_000_000))
    os.utime(newer, (1_000_000_000, 1_000_000_000))

    report = audit_repository(tmp_path)

    assert contract_record(report)["selected_version"] == "4.10.0"
    assert semver_key("3.7.10") > semver_key("3.7.9")
    assert semver_key("2.16.9") > semver_key("2.6.2")


def test_current_index_evidence_outranks_a_higher_valid_semver(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, version="4.9.9")
    make_bundle(tmp_path, version="4.10.0")
    (tmp_path / "CONTRACT_SELECTION_INDEX_COMBINED.md").write_text(
        "# Contract Selection Index\n\nStatus: Advisory\n\n"
        "## DOC-1 — Documented contract\n\nVersion: 4.9.9\n",
        encoding="utf-8",
    )

    selected = contract_record(audit_repository(tmp_path))

    assert selected["status"] == "selected"
    assert selected["selected_version"] == "4.9.9"
    assert any("index selects 4.9.9" in item.lower() for item in selected["selection_basis"])


def test_index_version_without_valid_candidate_blocks_fallback(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, version="1.0.0")
    (tmp_path / "CONTRACT_SELECTION_INDEX_COMBINED.md").write_text(
        "# Contract Selection Index\n\nStatus: Advisory\n\n"
        "## DOC-1 — Documented contract\n\nVersion: 2.0.0\n",
        encoding="utf-8",
    )

    selected = contract_record(audit_repository(tmp_path))

    assert selected["status"] == "ambiguous"
    assert selected["selected_version"] is None
    assert any("no candidate ZIP" in item for item in selected["ambiguities"])


def test_ignores_newer_git_commit_when_it_contains_lower_semver(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Contract Audit Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "contract-audit@example.invalid"], cwd=tmp_path, check=True)
    write_current_schema_authority(tmp_path)
    subprocess.run(["git", "add", "CONTRACT_AUTHORITY_INDEX_v1.39.0.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "add schema authority"],
        cwd=tmp_path,
        check=True,
        env={**os.environ, "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00"},
    )

    make_bundle(tmp_path, version="2.0.0")
    subprocess.run(["git", "add", "DOC-1_bundle_v2.0.0.zip"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "add higher contract version"],
        cwd=tmp_path,
        check=True,
        env={**os.environ, "GIT_AUTHOR_DATE": "2026-01-02T00:00:00+00:00", "GIT_COMMITTER_DATE": "2026-01-02T00:00:00+00:00"},
    )

    make_bundle(tmp_path, version="1.9.9")
    subprocess.run(["git", "add", "DOC-1_bundle_v1.9.9.zip"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "add lower contract version later"],
        cwd=tmp_path,
        check=True,
        env={**os.environ, "GIT_AUTHOR_DATE": "2026-01-03T00:00:00+00:00", "GIT_COMMITTER_DATE": "2026-01-03T00:00:00+00:00"},
    )

    report = audit_repository(tmp_path)

    assert report["summary"]["audited_git_commit"] is not None  # type: ignore[index]
    assert contract_record(report)["selected_version"] == "2.0.0"


def test_untracked_stage_only_candidate_is_not_promoted_without_index_evidence(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Contract Audit Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "contract-audit@example.invalid"], cwd=tmp_path, check=True)
    write_current_schema_authority(tmp_path)
    subprocess.run(["git", "add", "CONTRACT_AUTHORITY_INDEX_v1.39.0.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add schema authority"], cwd=tmp_path, check=True)
    make_bundle(tmp_path / ".staging/raw", version="1.0.0")

    selected = contract_record(audit_repository(tmp_path))

    assert selected["status"] == "ambiguous"
    assert selected["selected_version"] is None
    assert any("untracked" in item.lower() for item in selected["ambiguities"])


def test_rejects_higher_version_with_stale_gate_contract_ref(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, version="1.0.0")
    make_bundle(tmp_path, version="2.0.0", gate_contract_ref_version="1.0.0")

    report = audit_repository(tmp_path)

    selected = contract_record(report)
    assert selected["selected_version"] == "1.0.0"
    rejected = next(item for item in selected["candidates"] if item["version"] == "2.0.0")
    assert rejected["validation"]["status"] == "INVALID"
    assert any("contract_ref.version" in reason for reason in rejected["validation"]["errors"])


def test_rejects_manifest_hash_mismatch(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, manifest_hash_override="0" * 64)

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("sha256" in reason.lower() for reason in candidate["validation"]["errors"])


def test_rejects_manifest_size_mismatch(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, manifest_size_override=1)

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("size mismatch" in reason.lower() for reason in candidate["validation"]["errors"])


def test_rejects_manifest_version_mismatch(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, version="1.0.0", manifest_version="1.1.0")

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("manifest" in reason.lower() and "version" in reason.lower() for reason in candidate["validation"]["errors"])


def test_rejects_conflicting_manifest_bundle_identity_fields(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, manifest_bundle_id="OTHER-1", manifest_bundle_version="2.0.0")

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("Manifest identity fields disagree on doc_id" in reason for reason in candidate["validation"]["errors"])
    assert any("Manifest identity fields disagree on version" in reason for reason in candidate["validation"]["errors"])


def test_rejects_contract_version_mismatch_with_gates_and_manifest(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, version="1.0.0", contract_version="2.0.0")

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("contract_ref.version" in reason for reason in candidate["validation"]["errors"])


def test_rejects_test_gate_contract_ref_doc_id_mismatch(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, gate_contract_ref_doc_id="OTHER-1")

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("contract_ref.doc_id" in reason for reason in candidate["validation"]["errors"])


def test_rejects_stale_suite_schema_gate_assertion(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, gate_suite_schema="CS-0@2.2.0")

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("suite_schema expectation" in reason for reason in candidate["validation"]["errors"])


def test_rejects_extra_manifest_listed_payload_member(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, extra_files={"extra.json": b"{}\n"})

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("three-artifact bundle" in reason for reason in candidate["validation"]["errors"])


def test_safe_archive_paths_keep_dotfiles_and_reject_traversal() -> None:
    assert safe_archive_path("bundle/.well-known/artifact.json") == (
        "bundle/.well-known/artifact.json",
        None,
    )
    normalized, error = safe_archive_path("bundle/../../escape.json")
    assert normalized is None
    assert error and "traversal" in error


def test_governance_front_matter_captures_canonical_and_supersedes(tmp_path: Path) -> None:
    path = tmp_path / "V42_Enterprise_Ticketing_Core_Foundation_Spec_v1.3.md"
    path.write_text(
        "# Foundation Spec v1.3\n"
        "**Status:** LOCKED\n"
        "**Canonical:** true\n"
        "**Supersedes:** v1.2.1\n",
        encoding="utf-8",
    )

    fields = document_fields(path, tmp_path, {path.name})

    assert fields["version"] == "1.3"
    assert fields["declared_canonical"] is True
    assert fields["supersedes"] == "v1.2.1"
    assert fields["declared_status"] == "LOCKED"
    assert fields["authority_level"] == "declared_canonical"


def test_operating_guide_is_not_mislabeled_as_contract_authority(tmp_path: Path) -> None:
    path = tmp_path / "V42_A_to_Z_Locked_Setup_v1.2.md"
    path.write_text(
        "**Document ID:** `V42-A2Z-SETUP-1`\n"
        "**Version:** `1.2.0`\n"
        "**Status:** Controlled operating guide — non-authoritative over contract bundles\n",
        encoding="utf-8",
    )

    fields = document_fields(path, tmp_path, {path.name})

    assert fields["document_identity"] == "V42-A2Z-SETUP-1"
    assert fields["version"] == "1.2.0"
    assert fields["authority_level"] == "non_authoritative"


def test_malformed_contract_json_is_still_inventoried_as_a_candidate(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    archive_path = make_bundle(tmp_path)
    with zipfile.ZipFile(archive_path) as archive:
        members = {item.filename: archive.read(item) for item in archive.infolist() if not item.is_dir()}
    contract_member = next(name for name in members if "_Contract_" in name)
    members[contract_member] = b"not-json\n"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)

    selected = contract_record(audit_repository(tmp_path))

    assert selected["candidates"][0]["validation"]["status"] == "INVALID"
    assert "contract" in selected["candidates"][0]["missing_required_artifacts"]


def test_same_version_same_payload_is_duplicate_even_if_zip_metadata_differs(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    first = make_bundle(tmp_path / "first", version="1.0.0", zip_year=2024)
    second = make_bundle(tmp_path / "second", version="1.0.0", zip_year=2025)

    report = audit_repository(tmp_path)

    selected = contract_record(report)
    assert selected["status"] == "selected"
    assert selected["selected_version"] == "1.0.0"
    assert selected["duplicate_representations"][0]["payload_identical"] is True
    assert selected["duplicate_representations"][0]["zip_sha256_values_differ"] is True
    assert first != second


def test_same_version_different_contract_payload_is_ambiguous(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path / "one", version="1.0.0", contract_summary="first body")
    make_bundle(tmp_path / "two", version="1.0.0", contract_summary="second body")

    selected = contract_record(audit_repository(tmp_path))

    assert selected["status"] == "ambiguous"
    assert selected["selected_version"] is None
    assert "materially different" in " ".join(selected["ambiguities"])


def test_classifies_non_contract_zip_by_contents(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    support_zip = tmp_path / "ORD-1_bundle_v99.0.0_tools.zip"
    with zipfile.ZipFile(support_zip, "w") as archive:
        archive.writestr("README.md", "Support tooling, not a contract")
        archive.writestr("runner.py", "print('runner')\n")

    report = audit_repository(tmp_path)

    assert report["summary"]["non_contract_zip_count"] == 1  # type: ignore[index]
    assert report["non_contract_zips"][0]["path"] == str(support_zip.relative_to(tmp_path))  # type: ignore[index]


@pytest.mark.parametrize("missing", [{"contract"}, {"gates"}, {"manifest"}])
def test_missing_required_bundle_artifact_is_invalid(tmp_path: Path, missing: set[str]) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, missing=missing)

    report = audit_repository(tmp_path)

    assert contract_record(report)["status"] == "invalid"
    candidate = contract_record(report)["candidates"][0]
    assert candidate["validation"]["status"] == "INVALID"
    assert candidate["missing_required_artifacts"]


def test_legacy_filename_decoration_does_not_change_identity(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(
        tmp_path,
        version="1.2.3",
        filename="DOC-1_bundle_v1.2.3_CS-0_v3.0.0_refactored.zip",
    )

    selected = contract_record(audit_repository(tmp_path))

    assert selected["selected_version"] == "1.2.3"
    candidate = selected["selected_candidate"]
    assert candidate["doc_id"] == "DOC-1"
    assert any("filename suffix" in warning.lower() for warning in candidate["validation"]["warnings"])


def test_internal_artifact_filename_version_drift_is_reported_as_warning(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, version="1.0.0", contract_filename_version="0.9.9")

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "VALID_WITH_WARNING"
    assert any("member filename version" in warning.lower() for warning in candidate["validation"]["warnings"])


def test_conflicting_pin_and_current_index_authority_is_ambiguous(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, version="1.0.0")
    make_bundle(tmp_path, version="2.0.0")
    (tmp_path / "CONTRACT_AUTHORITY_INDEX_v1.39.0.md").write_text(
        "# Contract Authority Index\n\nUnder CS-0@3.0.1, current suite schema.\n"
        "DOC-1 selected bundle v1.0.0 (current authority).\n",
        encoding="utf-8",
    )
    (tmp_path / "CANONICAL_PIN_INDEX.md").write_text(
        "# Canonical pins\n\nDOC-1 canonical pin v2.0.0.\n",
        encoding="utf-8",
    )

    selected = contract_record(audit_repository(tmp_path))

    assert selected["status"] == "ambiguous"
    assert selected["selected_version"] is None
    assert any("authority" in item.lower() for item in selected["ambiguities"])


def test_open_tracked_supersession_review_blocks_selection(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Contract Audit Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "contract-audit@example.invalid"], cwd=tmp_path, check=True)
    write_current_schema_authority(tmp_path)
    index_path = tmp_path / "CONTRACT_AUTHORITY_INDEX_v1.39.0.md"
    index_path.write_text(
        index_path.read_text(encoding="utf-8")
        + "\n| CAI-DOC-001 | supersession review | P1 | DOC-1 v1.0.0 vs DOC-1 v2.0.0 | DOC-1 | confirm | open |\n",
        encoding="utf-8",
    )
    make_bundle(tmp_path, version="1.0.0")
    make_bundle(tmp_path, version="2.0.0")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add candidates and open review"], cwd=tmp_path, check=True)

    selected = contract_record(audit_repository(tmp_path))

    assert selected["status"] == "ambiguous"
    assert any("supersession unresolved" in item.lower() for item in selected["ambiguities"])


def test_validated_canon_pin_resolves_open_advisory_supersession_review() -> None:
    candidates = [
        {
            "doc_id": "DOC-1",
            "version": version,
            "source_path": f"DOC-1_bundle_v{version}.zip",
            "git_tracked": True,
            "zip_sha256": digest,
            "effective_payload_fingerprint": digest,
            "validation": {"status": "VALID"},
        }
        for version, digest in (("1.0.0", "a" * 64), ("2.0.0", "b" * 64))
    ]
    claims = [
        {
            "doc_id": "DOC-1",
            "version": "1.0.0",
            "authority_level": "validated_canon_pin",
            "validated": True,
            "git_tracked": True,
            "advisory_document": False,
        }
    ]
    conflicts = [
        {
            "doc_ids": ["DOC-1"],
            "versions": ["1.0.0", "2.0.0"],
            "source_path": "CONTRACT_AUTHORITY_INDEX_v1.0.0.md",
            "line": 10,
            "git_tracked": True,
            "authority_level": "advisory_index_unresolved_conflict",
        }
    ]

    resolved = resolve_contract(
        "DOC-1",
        candidates,
        claims,
        duplicate_records=[],
        content_conflicts=[],
        index_conflicts=conflicts,
        live_git_checkout=True,
        suite_schema_status="resolved",
    )

    assert resolved["status"] == "selected"
    assert resolved["selected_version"] == "1.0.0"
    assert any("validated canonical pin" in item.lower() for item in resolved["selection_basis"])


def test_new_exact_canon_pin_reports_current_hash_validation_reason() -> None:
    canon = {
        "doc_id": "CANON-1",
        "version": "2.0.2",
        "source_path": "contracts/CANON-1/CANON-1_bundle_v2.0.2.zip",
        "validation": {"status": "VALID"},
        "_contract_data": {
            "canonical_bundles": [
                {
                    "doc_id": "DOC-1",
                    "version": "1.0.0",
                    "bundle_sha256": "a" * 64,
                    "artifacts": [{"path": "contract.json", "sha256": "b" * 64, "bytes": 4}],
                }
            ]
        },
    }
    selected = {
        "doc_id": "DOC-1",
        "version": "1.0.0",
        "zip_sha256": "a" * 64,
        "source_path": "contracts/DOC-1/DOC-1_bundle_v1.0.0.zip",
        "members": [{"path": "contract.json", "sha256": "b" * 64, "size_bytes": 4}],
    }

    result = collect_canon_pin_validation([canon, selected])[0]

    assert result["authority_usable"] is True
    assert "exact zip sha-256 matches" in result["reason"].lower()
    assert "outdated" not in result["reason"].lower()


def test_conflicting_tracked_cs0_index_versions_block_selection(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Contract Audit Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "contract-audit@example.invalid"], cwd=tmp_path, check=True)
    write_current_schema_authority(tmp_path)
    (tmp_path / "CONTRACT_SELECTION_INDEX_COMBINED.md").write_text(
        "# Contract Selection Index\n\nStatus: Advisory\n\n"
        "## CS-0 — Contract Suite Schema\n\nVersion: 2.2.0\n",
        encoding="utf-8",
    )
    make_bundle(tmp_path, version="1.0.0")
    subprocess.run(["git", "add", "CONTRACT_AUTHORITY_INDEX_v1.39.0.md", "CONTRACT_SELECTION_INDEX_COMBINED.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add conflicting schema indexes"], cwd=tmp_path, check=True)

    report = audit_repository(tmp_path)

    assert report["current_suite_schema_evidence"]["status"] == "ambiguous"  # type: ignore[index]
    assert contract_record(report)["status"] == "ambiguous"


def test_strict_audit_exits_nonzero_for_ambiguity(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path / "one", version="1.0.0", contract_summary="first body")
    make_bundle(tmp_path / "two", version="1.0.0", contract_summary="second body")

    exit_code = main(["audit", "--include-staging", "--strict", "--root", str(tmp_path)])

    assert exit_code != 0
    assert (tmp_path / "reports/contract-reconciliation.json").is_file()
    assert (tmp_path / "reports/contract-reconciliation.md").is_file()


def test_dependency_closure_reports_target_below_declared_minimum(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(
        tmp_path / "referrer",
        doc_id="REF-1",
        dependencies=[
            {
                "doc_id": "DEP-1",
                "min_version": "2.1.1",
                "edge_type": "requires",
                "reason": "consumer compatibility floor",
            }
        ],
    )
    make_bundle(tmp_path / "dependency", doc_id="DEP-1", version="1.8.2")

    report = audit_repository(tmp_path)

    edge = next(
        item
        for item in report["dependency_closure"]["edges"]  # type: ignore[index]
        if item["referrer_doc_id"] == "REF-1"
    )
    assert edge["minimum_version"] == "2.1.1"
    assert edge["target_selected_version"] == "1.8.2"
    assert edge["status"] == "below_minimum"
    assert report["summary"]["dependency_floor_conflict_count"] == 1  # type: ignore[index]
    assert report["summary"]["phase_2_blocked"] is True  # type: ignore[index]
    assert report["cleanup_plan"]["phase_2_status"] == "blocked"  # type: ignore[index]
    assert len(report["cleanup_plan"]["dependency_blockers"]) == 1  # type: ignore[index]


def test_dependency_closure_resolves_compatible_floor_and_reports_missing_target(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(
        tmp_path / "compatible",
        doc_id="COMPAT-1",
        dependencies=[
            {
                "doc_id": "DEP-1",
                "min_version": "1.8.2",
                "edge_type": "requires",
                "reason": "test floor",
            }
        ],
    )
    make_bundle(
        tmp_path / "missing",
        doc_id="MISSING-1",
        dependencies=[
            {
                "doc_id": "MISSING-99",
                "min_version": "1.0.0",
                "edge_type": "requires",
                "reason": "test floor",
            }
        ],
    )
    make_bundle(tmp_path / "dependency", doc_id="DEP-1", version="2.1.1")

    report = audit_repository(tmp_path)

    edges = report["dependency_closure"]["edges"]  # type: ignore[index]
    compatible = next(item for item in edges if item["referrer_doc_id"] == "COMPAT-1")
    missing = next(item for item in edges if item["referrer_doc_id"] == "MISSING-1")
    assert compatible["status"] == "satisfied"
    assert compatible["target_selected_version"] == "2.1.1"
    assert missing["status"] == "target_unresolved"
    assert missing["target_selected_version"] is None


def test_dependency_closure_uses_unique_accepted_release_without_resolving_suite_selection() -> None:
    dependency = {
        "doc_id": "LED-1",
        "min_version": "4.4.7",
        "edge_type": "requires",
        "reason": "approved ledger semantic baseline",
    }
    records = {
        "REF-1": {
            "status": "selected",
            "selected_version": "1.0.0",
            "selected_candidate": {
                "source_path": "referrer.zip",
                "contract_metadata": {"dependencies": [dependency]},
            },
        },
        "LED-1": {
            "status": "ambiguous",
            "selected_version": None,
            "selected_candidate": None,
        },
    }
    accepted_claims = [
        {
            "doc_id": "LED-1",
            "version": "4.4.7",
            "authority_level": "accepted_release",
            "validated": True,
            "declared_zip_sha256": "a" * 64,
            "matching_candidate_paths": ["accepted/LED-1_bundle_v4.4.7.zip"],
        }
    ]

    report = build_dependency_closure(records, accepted_claims)

    edge = next(item for item in report["edges"] if item["referrer_doc_id"] == "REF-1")
    assert edge["status"] == "satisfied"
    assert edge["target_resolution"] == "accepted_release"
    assert edge["target_resolved_version"] == "4.4.7"
    assert edge["target_resolved_versions"] == ["4.4.7"]
    assert edge["target_selected_version"] is None
    assert edge["target_status"] == "ambiguous"
    assert records["LED-1"]["status"] == "ambiguous"


def test_dependency_closure_uses_accepted_versions_that_satisfy_the_floor_without_selecting_one() -> None:
    dependency = {
        "doc_id": "DEP-1",
        "min_version": "2.0.0",
        "edge_type": "requires",
        "reason": "minimum capability floor",
    }
    pinned_dependency = {
        "doc_id": "DEP-1",
        "min_version": "1.0.0",
        "edge_type": "requires",
        "artifact_pin_sha256": "a" * 64,
        "reason": "exact accepted artifact identity",
    }
    too_high_dependency = {
        "doc_id": "DEP-1",
        "min_version": "3.0.0",
        "edge_type": "requires",
        "reason": "unmet capability floor",
    }
    records = {
        "REF-1": {
            "status": "selected",
            "selected_version": "1.0.0",
            "selected_candidate": {
                "source_path": "referrer.zip",
                "contract_metadata": {
                    "dependencies": [dependency, pinned_dependency, too_high_dependency]
                },
            },
        },
        "DEP-1": {
            "status": "ambiguous",
            "selected_version": None,
            "selected_candidate": None,
        },
    }
    accepted_claims = [
        {
            "doc_id": "DEP-1",
            "version": version,
            "authority_level": "accepted_release",
            "validated": True,
            "declared_zip_sha256": digest,
            "matching_candidate_paths": [path],
        }
        for version, digest, path in (
            ("1.9.9", "a" * 64, "accepted/DEP-1_bundle_v1.9.9.zip"),
            ("2.0.3", "b" * 64, "accepted/DEP-1_bundle_v2.0.3.zip"),
        )
    ]

    report = build_dependency_closure(records, accepted_claims)

    edges = report["edges"]
    edge, pinned_edge, too_high_edge = edges
    assert edge["status"] == "satisfied"
    assert edge["target_resolution"] == "accepted_release"
    assert edge["target_available_accepted_versions"] == ["1.9.9", "2.0.3"]
    assert edge["target_resolved_versions"] == ["2.0.3"]
    assert edge["target_resolved_version"] == "2.0.3"
    assert edge["target_selected_version"] is None
    assert edge["target_status"] == "ambiguous"
    assert pinned_edge["status"] == "satisfied"
    assert pinned_edge["target_available_accepted_versions"] == ["1.9.9"]
    assert pinned_edge["target_resolved_versions"] == ["1.9.9"]
    assert pinned_edge["target_resolved_version"] == "1.9.9"
    assert too_high_edge["status"] == "below_minimum"
    assert too_high_edge["target_available_accepted_versions"] == ["1.9.9", "2.0.3"]
    assert too_high_edge["target_resolved_versions"] == []
    assert records["DEP-1"]["status"] == "ambiguous"


def test_release_selection_uses_exact_accepted_successor_lineage_not_version_order() -> None:
    old_hash = "a" * 64
    successor_hash = "b" * 64
    candidates = [
        {
            "doc_id": "DOC-1",
            "version": version,
            "source_path": f"{version}.zip",
            "zip_sha256": digest,
            "validation": {"status": "VALID", "errors": [], "warnings": []},
            "git_tracked": True,
            "effective_payload_fingerprint": digest,
        }
        for version, digest in (("4.10.0", old_hash), ("4.10.1", successor_hash))
    ]
    claims = [
        {
            "doc_id": "DOC-1",
            "version": "4.10.0",
            "authority_level": "accepted_release",
            "validated": True,
            "git_tracked": True,
            "declared_zip_sha256": old_hash,
            "advisory_document": False,
        },
        {
            "doc_id": "DOC-1",
            "version": "4.10.1",
            "authority_level": "accepted_release",
            "validated": True,
            "git_tracked": True,
            "declared_zip_sha256": successor_hash,
            "advisory_document": False,
            "supersedes": {
                "doc_id": "DOC-1",
                "version": "4.10.0",
                "sha256": old_hash,
                "path": "4.10.0.zip",
            },
        },
    ]

    result = resolve_contract("DOC-1", candidates, claims, [], [], [], True, "resolved")

    assert result["status"] == "selected"
    assert result["selected_version"] == "4.10.1"
    assert result["selected_candidate"]["zip_sha256"] == successor_hash
    assert any("explicitly supersedes" in line for line in result["selection_basis"])
    assert any("not CANON pinning" in line for line in result["selection_basis"])


def test_release_selection_keeps_unrelated_accepted_branches_ambiguous() -> None:
    hashes = {version: letter * 64 for version, letter in (
        ("4.10.0", "a"), ("4.10.1", "b"), ("4.11.0", "c")
    )}
    candidates = [
        {
            "doc_id": "DOC-1",
            "version": version,
            "source_path": f"{version}.zip",
            "zip_sha256": digest,
            "validation": {"status": "VALID", "errors": [], "warnings": []},
            "git_tracked": True,
            "effective_payload_fingerprint": digest,
        }
        for version, digest in hashes.items()
    ]
    claims = [
        {
            "doc_id": "DOC-1",
            "version": version,
            "authority_level": "accepted_release",
            "validated": True,
            "git_tracked": True,
            "declared_zip_sha256": hashes[version],
            "advisory_document": False,
            **({"supersedes": {"doc_id": "DOC-1", "version": "4.10.0", "sha256": hashes["4.10.0"], "path": "4.10.0.zip"}}
               if version == "4.10.1" else {}),
        }
        for version in hashes
    ]

    result = resolve_contract("DOC-1", candidates, claims, [], [], [], True, "resolved")

    assert result["status"] == "ambiguous"
    assert result["selected_version"] is None
    assert any("4.10.1, 4.11.0" in line for line in result["ambiguities"])


def test_dependency_closure_rejects_missing_cs0_required_dependency_fields(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(
        tmp_path,
        dependencies=[{"doc_id": "DEP-1", "reason": "incomplete dependency fixture"}],
    )

    report = audit_repository(tmp_path)

    edge = report["dependency_closure"]["edges"][0]  # type: ignore[index]
    assert edge["status"] == "invalid_dependency_record"
    assert set(edge["missing_required_fields"]) == {"min_version", "edge_type"}
    assert report["dependency_closure"]["blocking_edge_count"] == 1  # type: ignore[index]


def test_dependency_closure_rejects_unknown_cs0_edge_type(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(
        tmp_path,
        dependencies=[
            {
                "doc_id": "DEP-1",
                "min_version": "1.0.0",
                "edge_type": "invented",
                "reason": "invalid edge type fixture",
            }
        ],
    )
    make_bundle(tmp_path / "dependency", doc_id="DEP-1", version="1.0.0")

    report = audit_repository(tmp_path)

    edge = next(
        item
        for item in report["dependency_closure"]["edges"]  # type: ignore[index]
        if item["referrer_doc_id"] == "DOC-1"
    )
    assert edge["status"] == "invalid_dependency_record"
    assert edge["edge_type"] == "invented"
    assert "edge_type" in edge["invalid_fields"]
    assert report["summary"]["dependency_edge_invalid_count"] == 1  # type: ignore[index]


def test_dependency_closure_rejects_null_dependency_array(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, dependencies_is_null=True)

    report = audit_repository(tmp_path)

    edge = report["dependency_closure"]["edges"][0]  # type: ignore[index]
    assert edge["status"] == "invalid_dependency_list"


def test_dependency_closure_allows_optional_dependencies_member_to_be_absent(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, dependencies_omitted=True)

    report = audit_repository(tmp_path)

    assert contract_record(report)["status"] == "selected"
    assert report["dependency_closure"]["edges"] == []  # type: ignore[index]
    assert report["dependency_closure"]["status"] == "resolved"  # type: ignore[index]


def test_dependency_closure_accepts_cs0_purpose_only_dependency(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(
        tmp_path,
        dependencies=[
            {
                "doc_id": "DEP-1",
                "min_version": "1.0.0",
                "edge_type": "requires",
                "purpose": "consumer floor",
            }
        ],
    )
    make_bundle(tmp_path / "dependency", doc_id="DEP-1", version="1.0.0")

    report = audit_repository(tmp_path)

    edge = next(
        item
        for item in report["dependency_closure"]["edges"]  # type: ignore[index]
        if item["referrer_doc_id"] == "DOC-1"
    )
    assert edge["status"] == "satisfied"
    assert edge["purpose"] == "consumer floor"


def test_strict_audit_exits_nonzero_for_unresolved_dependency_target(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(
        tmp_path,
        dependencies=[
            {
                "doc_id": "MISSING-99",
                "min_version": "1.0.0",
                "edge_type": "requires",
                "reason": "strict closure test",
            }
        ],
    )

    exit_code = main(["audit", "--include-staging", "--strict", "--root", str(tmp_path)])

    assert exit_code != 0


def test_bundle_with_unmanifested_extra_member_is_invalid(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, unmanifested_files={"unregistered.json": b"{}\n"})

    candidate = contract_record(audit_repository(tmp_path))["candidates"][0]

    assert candidate["validation"]["status"] == "INVALID"
    assert any("unmanifested" in reason.lower() for reason in candidate["validation"]["errors"])


def test_existing_extracted_copy_does_not_select_a_version(tmp_path: Path) -> None:
    write_current_schema_authority(tmp_path)
    make_bundle(tmp_path, version="1.0.0")
    make_bundle(
        tmp_path / "source",
        version="2.0.0",
        filename="DOC-1_bundle_v2.0.0.zip",
    )
    archive_path = tmp_path / "source/DOC-1_bundle_v2.0.0.zip"
    extracted_root = tmp_path / "extracted-evidence/DOC-1_bundle_v2.0.0"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extracted_root)
    archive_path.unlink()

    selected = contract_record(audit_repository(tmp_path))

    assert selected["selected_version"] == "1.0.0"
    assert any(
        item["version"] == "2.0.0" and item["authority"] == "evidence_only_existing_extracted_copy"
        for item in audit_repository(tmp_path)["existing_extracted_bundles"]
    )


def test_authored_release_sources_are_not_extracted_bundle_evidence(tmp_path: Path) -> None:
    source_dir = tmp_path / "release-src/ratification/DOC-1/1.0.0"
    source_dir.mkdir(parents=True)
    (source_dir / "contract.json").write_text(
        _json_bytes({"artifact_kind": "contract", "doc_id": "DOC-1", "version": "1.0.0"}).decode(),
        encoding="utf-8",
    )
    (source_dir / "test-gates.json").write_text(
        _json_bytes({"artifact_kind": "test_gates", "doc_id": "DOC-1-GATE", "version": "1.0.0"}).decode(),
        encoding="utf-8",
    )
    source_file = source_dir / "contract.json"

    extracted_evidence = discover_extracted_bundles(tmp_path, workspace_files(tmp_path))
    audit = audit_repository(tmp_path)

    assert extracted_evidence == []
    assert classify_file(source_file, tmp_path, set(), {}) == "contract_release_source"
    assert audit["existing_extracted_bundles"] == []
    assert any(
        item["path"].endswith("release-src/ratification/DOC-1/1.0.0/contract.json")
        for item in audit["repository_inventory"]["contract_release_source"]
    )


def test_cleanup_plan_rebuilds_contract_extractions_instead_of_moving_them(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Contract Audit Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "contract-audit@example.invalid"], cwd=tmp_path, check=True)
    write_current_schema_authority(tmp_path)
    archive_path = make_bundle(
        tmp_path / "ticketing-contracts/CS3.0-REFACTORED",
        version="1.0.0",
    )
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(tmp_path / "ticketing-contracts/extracted")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add tracked contract and extraction"], cwd=tmp_path, check=True)

    plan = audit_repository(tmp_path)["cleanup_plan"]

    assert any(item["path"].startswith("ticketing-contracts/extracted/") for item in plan["proposed_deletions"])
    assert not any(item["source"].startswith("ticketing-contracts/extracted/") for item in plan["proposed_moves"])


def test_canonical_audit_accepts_nested_authority_root_with_untracked_files(tmp_path: Path) -> None:
    repository = tmp_path / "ticketing"
    authority_root = repository / "authority"
    authority_root.mkdir(parents=True)
    write_current_schema_authority(authority_root)
    make_bundle(authority_root)
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)

    report = audit_repository(authority_root, scan_mode="canonical")

    assert report["summary"]["zip_files_inspected"] == 1
    assert set(report["contracts"]) == {"DOC-1"}
