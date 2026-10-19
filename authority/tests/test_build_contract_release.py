"""Tests for deterministic contract release construction and validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

import pytest

from tools.build_contract_release import ReleaseError, build_contract_release, validate_bundle


DOC_ID = "DOC-1"
VERSION = "1.2.3"
SUITE_SCHEMA = "CS-0@3.0.1"
MANIFEST_TIMESTAMP = "2026-01-02T03:04:05Z"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _source_tree(
    root: Path,
    *,
    doc_id: str = DOC_ID,
    version: str = VERSION,
    manifest_timestamp: str | None = MANIFEST_TIMESTAMP,
    contract_doc_id: str | None = None,
    contract_version: str | None = None,
    gate_contract_ref_doc_id: str | None = None,
    gate_contract_ref_version: str | None = None,
    suite_schema: str = SUITE_SCHEMA,
    gate_suite_schema: str | None = None,
    release_suite_schema: str | None = None,
    contract_summary: str = "Deterministic fixture contract",
    release_status: str = "approved",
    dependencies: list[dict[str, object]] | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    actual_contract_version = contract_version or version
    actual_gate_ref_version = gate_contract_ref_version or version
    contract_name = "contract.json"
    gates_name = "test-gates.json"

    contract = {
        "artifact_kind": "contract",
        "schema_version": "contract-suite/1.0",
        "title": "Deterministic fixture contract",
        "status": "active",
        "doc_id": contract_doc_id or doc_id,
        "version": actual_contract_version,
        "suite_schema": suite_schema,
        "summary": contract_summary,
    }
    if dependencies is not None:
        contract["dependencies"] = dependencies
    gates = {
        "artifact_kind": "test_gates",
        "schema_version": "test-gates/1.0",
        "title": "Deterministic fixture gates",
        "status": "active",
        "doc_id": f"{doc_id}-GATE",
        "version": version,
        "contract_ref": {
            "doc_id": gate_contract_ref_doc_id or doc_id,
            "version": actual_gate_ref_version,
        },
        "suite_schema": gate_suite_schema or suite_schema,
        "gates": [
            {
                "id": "GATE-001",
                "level": "P1",
                "must": True,
                "description": "Fixture gate",
                "assertions": [
                    {"mode": "automated", "type": "acceptance_criteria", "details": {}}
                ],
            }
        ],
    }
    release = {
        "doc_id": doc_id,
        "version": version,
        "suite_schema": release_suite_schema or suite_schema,
        "release_intent": "synthetic test fixture",
        "release_status": release_status,
        "source_provenance": {"kind": "synthetic"},
    }
    if manifest_timestamp is not None:
        release["generated_at_utc"] = manifest_timestamp

    (root / contract_name).write_bytes(_json_bytes(contract))
    (root / gates_name).write_bytes(_json_bytes(gates))
    (root / "release.json").write_bytes(_json_bytes(release))
    return root


def _manifest_bytes(archive_path: Path) -> bytes:
    with zipfile.ZipFile(archive_path) as archive:
        return archive.read(f"{DOC_ID}_bundle_v{VERSION}/bundle.manifest.json")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_identical_source_builds_identical_manifest_and_zip_bytes(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source")

    first = build_contract_release(source, tmp_path / "build-one")
    second = build_contract_release(source, tmp_path / "build-two")

    assert first.read_bytes() == second.read_bytes()
    assert _manifest_bytes(first) == _manifest_bytes(second)
    assert validate_bundle(first)["status"] == "VALID"


def test_suite_schema_gate_description_must_match_automated_assertion(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source")
    gates_path = source / "test-gates.json"
    gates = json.loads(gates_path.read_text(encoding="utf-8"))
    gates["gates"][0] = {
        "id": "GATE-001",
        "level": "P0",
        "must": True,
        "description": "suite_schema MUST equal CS-0@2.2.0 across contract, test_gates, and bundle_manifest.",
        "assertions": [
            {"mode": "automated", "type": "suite_schema_matches", "details": {"expected": "CS-0@3.0.1"}},
            {"mode": "automated", "type": "json_pointer_equals", "details": {
                "artifact_kind": "contract", "json_pointer": "/suite_schema", "equals": "CS-0@3.0.1",
            }},
            {"mode": "automated", "type": "json_pointer_equals", "details": {
                "artifact_kind": "test_gates", "json_pointer": "/suite_schema", "equals": "CS-0@3.0.1",
            }},
            {"mode": "automated", "type": "json_pointer_equals", "details": {
                "artifact_kind": "bundle_manifest", "json_pointer": "/suite_schema", "equals": "CS-0@3.0.1",
            }},
        ],
    }
    gates_path.write_bytes(_json_bytes(gates))

    with pytest.raises(ReleaseError, match="description.*suite_schema.*automated assertion"):
        build_contract_release(source, tmp_path / "candidate", allow_candidate=True)


def test_build_preserves_contract_and_gate_source_payloads(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source")
    contract_name = "contract.json"
    gates_name = "test-gates.json"
    archive_path = build_contract_release(source, tmp_path / "dist")

    with zipfile.ZipFile(archive_path) as archive:
        root = f"{DOC_ID}_bundle_v{VERSION}/"
        assert archive.read(root + f"{DOC_ID}_Contract_v{VERSION}.json") == (source / contract_name).read_bytes()
        assert archive.read(root + f"{DOC_ID}_Test_Gates_v{VERSION}.json") == (source / gates_name).read_bytes()


def test_zip_members_are_sorted_and_use_fixed_metadata(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )

    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert all(not name.endswith("/") for name in names)
        for member in archive.infolist():
            assert member.date_time == FIXED_ZIP_TIME
            assert member.compress_type == zipfile.ZIP_STORED
            assert member.create_system == 3
            assert stat.S_IMODE(member.external_attr >> 16) == 0o644


def test_manifest_hashes_and_sizes_match_archive_payloads(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )

    with zipfile.ZipFile(archive_path) as archive:
        root = f"{DOC_ID}_bundle_v{VERSION}/"
        manifest = json.loads(archive.read(root + "bundle.manifest.json"))
        assert manifest["generated_at_utc"] == MANIFEST_TIMESTAMP
        assert manifest["doc_id"] == DOC_ID
        assert manifest["version"] == VERSION
        assert manifest["bundle"] == {
            "bundle_id": DOC_ID,
            "bundle_version": VERSION,
        }
        assert [record["path"] for record in manifest["files"]] == sorted(
            record["path"] for record in manifest["files"]
        )
        for record in manifest["files"]:
            payload = archive.read(root + record["path"])
            assert record["sha256"] == _sha256(payload)
            assert record["bytes"] == len(payload)


def test_different_payload_changes_manifest_hash(tmp_path: Path) -> None:
    first_source = _source_tree(tmp_path / "source-one", contract_summary="first")
    second_source = _source_tree(tmp_path / "source-two", contract_summary="second")

    first = build_contract_release(first_source, tmp_path / "dist-one")
    second = build_contract_release(second_source, tmp_path / "dist-two")

    first_manifest = _manifest_bytes(first)
    second_manifest = _manifest_bytes(second)
    assert first_manifest != second_manifest
    assert _sha256(first_manifest) != _sha256(second_manifest)


@pytest.mark.parametrize(
    ("source_options", "message"),
    [
        ({"contract_doc_id": "OTHER-1"}, "contract doc_id"),
        ({"contract_version": "1.2.2"}, "contract version"),
        ({"gate_contract_ref_doc_id": "OTHER-1"}, "contract_ref doc_id"),
        ({"gate_contract_ref_version": "1.2.2"}, "contract_ref version"),
        ({"gate_suite_schema": "CS-0@2.2.0"}, "suite_schema"),
        ({"release_suite_schema": "CS-0@2.2.0"}, "suite_schema"),
    ],
)
def test_builder_rejects_contract_and_gate_identity_mismatches(
    tmp_path: Path, source_options: dict[str, str], message: str
) -> None:
    source = _source_tree(tmp_path / "source", **source_options)

    with pytest.raises(ReleaseError, match=message):
        build_contract_release(source, tmp_path / "dist")


def test_missing_explicit_manifest_timestamp_is_rejected(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source", manifest_timestamp=None)

    with pytest.raises(ReleaseError, match="generated_at_utc"):
        build_contract_release(source, tmp_path / "dist")


def test_builder_refuses_unapproved_ratification_source(tmp_path: Path) -> None:
    source = _source_tree(
        tmp_path / "source", release_status="ratification_pending"
    )

    with pytest.raises(ReleaseError, match="release_status must be 'approved'"):
        build_contract_release(source, tmp_path / "dist")


def test_candidate_source_requires_explicit_candidate_build_opt_in(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source", release_status="candidate")

    with pytest.raises(ReleaseError, match="candidate build requires explicit opt-in"):
        build_contract_release(source, tmp_path / "ordinary-build")

    archive_path = build_contract_release(
        source, tmp_path / "candidate-build", allow_candidate=True
    )

    assert validate_bundle(archive_path)["status"] == "VALID"


def test_current_cs_schema_rejects_legacy_foundation_edge(tmp_path: Path) -> None:
    source = _source_tree(
        tmp_path / "source",
        suite_schema="CS-0@3.0.1",
        dependencies=[
            {
                "doc_id": "ORD-1",
                "edge_type": "foundation",
                "min_version": "1.0.0",
                "reason": "Legacy overloaded edge must be migrated.",
            }
        ],
    )

    with pytest.raises(
        ReleaseError,
        match=r"contract\.json violates CS-0@3\.0\.1 schema at /dependencies/0/edge_type",
    ):
        build_contract_release(source, tmp_path / "dist")


def test_current_cs_schema_requires_edge_type_on_each_dependency(tmp_path: Path) -> None:
    source = _source_tree(
        tmp_path / "source",
        dependencies=[
            {
                "doc_id": "ORD-1",
                "min_version": "1.0.0",
                "reason": "The current profile requires an explicit relationship.",
            }
        ],
    )

    with pytest.raises(
        ReleaseError,
        match=r"contract\.json violates CS-0@3\.0\.1 schema at /dependencies/0",
    ):
        build_contract_release(source, tmp_path / "dist")


@pytest.mark.parametrize(
    "edge_type",
    [
        "requires",
        "governance_floor",
        "foundation_floor",
        "registry_floor",
        "integration_floor",
        "paired_contract",
    ],
)
def test_current_cs_schema_accepts_only_declared_edge_types(
    tmp_path: Path, edge_type: str
) -> None:
    source = _source_tree(
        tmp_path / "source",
        dependencies=[
            {
                "doc_id": "ORD-1",
                "edge_type": edge_type,
                "min_version": "1.0.0",
                "reason": "Fixture dependency under the current schema.",
            }
        ],
    )

    archive_path = build_contract_release(source, tmp_path / "dist")

    assert validate_bundle(archive_path)["status"] == "VALID"


def test_cs_candidate_locks_owner_approved_dependency_semantics() -> None:
    contract_path = (
        REPOSITORY_ROOT
        / "release-src/current/CS-0/3.0.1/contract.json"
    )
    gates_path = (
        REPOSITORY_ROOT
        / "release-src/current/CS-0/3.0.1/test-gates.json"
    )
    contract = json.loads(contract_path.read_bytes())
    gates = json.loads(gates_path.read_bytes())
    definitions = {
        item["edge_type"]: item["meaning"]
        for item in contract["dependency_edge_type_semantics"]
    }

    assert contract["version"] == "3.0.1"
    assert contract["canonical"] is False
    assert set(definitions) == {
        item["edge_type"] for item in contract["dependency_edge_type_semantics"]
    }
    assert "foundation" not in contract["schemas"]["contract"]["properties"]["dependencies"]["items"]["properties"]["edge_type"]["enum"]
    assert set(definitions) == {"requires", "governance_floor", "foundation_floor"}
    assert definitions["requires"] == (
        "A direct dependency required for the consuming contract's own structural, "
        "semantic, schema, or executable validity. Use this when the consumer cannot "
        "correctly satisfy its own contract without the target dependency. This does "
        "not merely establish a platform-wide minimum version."
    )
    assert definitions["governance_floor"] == (
        "A minimum version of a governance, test, lint, change-control, or compliance "
        "contract that governs how the consuming contract or suite is validated and "
        "controlled. The target establishes governance constraints rather than "
        "domain/runtime functionality."
    )
    assert definitions["foundation_floor"] == (
        "A minimum version of a governed platform/domain subsystem required by the "
        "constitutional/platform baseline. This establishes the minimum acceptable "
        "subsystem contract for suite/V42 compliance."
    )
    gate = next(
        item
        for item in gates["gates"]
        if item["id"] == "CS-0-P0-DEPENDENCY-EDGE-SEMANTICS"
    )
    pointers = {
        assertion["details"]["json_pointer"]
        for assertion in gate["assertions"]
        if assertion["type"] == "json_pointer_equals"
    }
    assert "/dependency_edge_type_semantics" in pointers
    assert "/schemas/contract/properties/dependencies/items/properties/edge_type/enum" in pointers


@pytest.mark.parametrize(
    ("doc_id", "version"),
    [
        ("CS-0", "3.0.1"),
        ("BP-0", "3.0.1"),
        ("CG-0", "2.2.2"),
        ("V42-0", "1.8.2"),
    ],
)
def test_owner_approved_successor_candidates_build_and_validate(
    tmp_path: Path, doc_id: str, version: str
) -> None:
    source = (
        REPOSITORY_ROOT
        / "release-src/current"
        / doc_id
        / version
    )

    archive_path = build_contract_release(
        source, tmp_path / f"{doc_id}-output", allow_candidate=True
    )

    result = validate_bundle(archive_path)
    assert result["status"] == "VALID"
    assert result["doc_id"] == doc_id
    assert result["version"] == version


def test_v42_candidate_applies_the_ratified_twenty_edge_mapping() -> None:
    source = REPOSITORY_ROOT / "release-src/current/V42-0/1.8.2"
    contract = json.loads((source / "contract.json").read_bytes())
    gates = json.loads((source / "test-gates.json").read_bytes())
    expected_types = {
        "CS-0": "requires",
        "TG-0": "governance_floor",
        "CG-0": "governance_floor",
        "GOV-0": "governance_floor",
        "LINT-0": "governance_floor",
        "TEN-1": "foundation_floor",
        "ERR-1": "foundation_floor",
        "LED-1": "foundation_floor",
        "SEAT-1": "foundation_floor",
        "PRICE-1": "foundation_floor",
        "ORD-1": "foundation_floor",
        "PSC-1": "foundation_floor",
        "IAM-1": "foundation_floor",
        "IAM-2": "foundation_floor",
        "IAM-3": "foundation_floor",
        "PII-1": "foundation_floor",
        "CONSENT-1": "foundation_floor",
        "DSAR-1": "foundation_floor",
        "TRK-1": "foundation_floor",
        "BI-1": "foundation_floor",
    }
    dependencies = contract["dependencies"]
    assert {item["doc_id"]: item["edge_type"] for item in dependencies} == expected_types
    assert contract["dependencies"][0]["min_version"] == "3.0.1"
    assert contract["dependency_floors"]["CS-0"] == "3.0.1"
    assert contract["suite_schema"] == "CS-0@3.0.1"
    assert contract["canonical"] is False
    dependency_gate = next(gate for gate in gates["gates"] if gate["id"] == "V42-DEP-010")
    assertion = dependency_gate["assertions"][0]
    assert assertion["details"]["json_pointer"] == "/dependencies"
    assert assertion["details"]["equals"] == dependencies
    assert all(item["edge_type"] != "foundation" for item in dependencies)

    assert any(
        row["doc_id"] == "BI-1" and row["edge_type"] == "foundation_floor"
        for row in contract["dependencies"]
    )


def test_historical_reproduction_requires_explicit_opt_in(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source", release_status="reproduction")

    with pytest.raises(ReleaseError, match="release_status must be 'approved'"):
        build_contract_release(source, tmp_path / "ordinary-build")

    archive_path = build_contract_release(
        source, tmp_path / "reproduction-build", allow_reproduction=True
    )
    assert validate_bundle(archive_path)["status"] == "VALID"


@pytest.mark.parametrize(
    ("artifact_name", "field"),
    [
        ("contract.json", "schema_version"),
        ("contract.json", "title"),
        ("contract.json", "status"),
        ("test-gates.json", "schema_version"),
        ("test-gates.json", "title"),
        ("test-gates.json", "status"),
        ("test-gates.json", "gates"),
    ],
)
def test_builder_rejects_missing_foundation_schema_fields(
    tmp_path: Path, artifact_name: str, field: str
) -> None:
    source = _source_tree(tmp_path / "source")
    artifact_path = source / artifact_name
    artifact = json.loads(artifact_path.read_bytes())
    artifact.pop(field)
    artifact_path.write_bytes(_json_bytes(artifact))

    with pytest.raises(ReleaseError, match=field):
        build_contract_release(source, tmp_path / "dist")


def test_builder_validates_contract_against_ratified_json_schema(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source")
    contract_path = source / "contract.json"
    contract = json.loads(contract_path.read_bytes())
    contract["summary"] = ["wrong type"]
    contract_path.write_bytes(_json_bytes(contract))

    with pytest.raises(ReleaseError, match="contract.json violates CS-0@3.0.1 schema at /summary"):
        build_contract_release(source, tmp_path / "dist")


def test_builder_rejects_gate_fields_outside_ratified_json_schema(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source")
    gates_path = source / "test-gates.json"
    gates = json.loads(gates_path.read_bytes())
    gates["gates"][0]["unrecognized_field"] = "must be rejected"
    gates_path.write_bytes(_json_bytes(gates))

    with pytest.raises(ReleaseError, match="test-gates.json violates CS-0@3.0.1 schema"):
        build_contract_release(source, tmp_path / "dist")


def test_bootstrap_provenance_hashes_must_match_authored_source(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source")
    provenance = {
        "bootstrap_commit": "a" * 40,
        "source_bundle_path": "historical/source.zip",
        "source_zip_sha256": "b" * 64,
        "source_zip_bytes": 123,
        "source_members": [
            {
                "tracked_source_path": "contract.json",
                "bytes": 1,
                "sha256": "0" * 64,
            },
            {
                "tracked_source_path": "test-gates.json",
                "bytes": len((source / "test-gates.json").read_bytes()),
                "sha256": _sha256((source / "test-gates.json").read_bytes()),
            },
        ],
    }
    (source / "provenance.json").write_bytes(_json_bytes(provenance))

    with pytest.raises(ReleaseError, match="provenance hash mismatch for contract.json"):
        build_contract_release(source, tmp_path / "dist")


def _write_matching_bootstrap_provenance(source: Path, *, source_zip_hash: str) -> None:
    members = []
    for tracked_path in ("contract.json", "test-gates.json"):
        payload = (source / tracked_path).read_bytes()
        members.append(
            {
                "tracked_source_path": tracked_path,
                "source_member_path": f"historical/{tracked_path}",
                "bytes": len(payload),
                "sha256": _sha256(payload),
            }
        )
    provenance = {
        "bootstrap_commit": "a" * 40,
        "source_bundle_path": "historical/source.zip",
        "source_zip_sha256": source_zip_hash,
        "source_zip_bytes": 123,
        "source_members": members,
    }
    (source / "provenance.json").write_bytes(_json_bytes(provenance))
    release_path = source / "release.json"
    release = json.loads(release_path.read_bytes())
    release["source_provenance"] = {
        "kind": "staging-bundle-bootstrap",
        "path": "provenance.json",
        "source_zip_sha256": source_zip_hash,
    }
    release_path.write_bytes(_json_bytes(release))


def test_bootstrap_provenance_is_required_and_matches_release_metadata(
    tmp_path: Path,
) -> None:
    missing_source = _source_tree(tmp_path / "missing-source")
    missing_release_path = missing_source / "release.json"
    missing_release = json.loads(missing_release_path.read_bytes())
    missing_release["source_provenance"] = {"kind": "staging-bundle-bootstrap"}
    missing_release_path.write_bytes(_json_bytes(missing_release))
    with pytest.raises(ReleaseError, match="requires provenance.json"):
        build_contract_release(missing_source, tmp_path / "missing-dist")

    source = _source_tree(tmp_path / "source")
    _write_matching_bootstrap_provenance(source, source_zip_hash="b" * 64)
    archive_path = build_contract_release(source, tmp_path / "dist")
    assert validate_bundle(archive_path)["status"] == "VALID"


def test_bootstrap_provenance_source_hash_must_match_release_metadata(
    tmp_path: Path,
) -> None:
    source = _source_tree(tmp_path / "source")
    _write_matching_bootstrap_provenance(source, source_zip_hash="b" * 64)
    release_path = source / "release.json"
    release = json.loads(release_path.read_bytes())
    release["source_provenance"]["source_zip_sha256"] = "c" * 64
    release_path.write_bytes(_json_bytes(release))

    with pytest.raises(ReleaseError, match="source_provenance hash disagrees"):
        build_contract_release(source, tmp_path / "dist")


def test_same_output_path_accepts_only_identical_release_bytes(tmp_path: Path) -> None:
    source = _source_tree(tmp_path / "source")
    first = build_contract_release(source, tmp_path / "dist")
    first_bytes = first.read_bytes()

    second = build_contract_release(source, tmp_path / "dist")

    assert second == first
    assert second.read_bytes() == first_bytes


def test_validator_rejects_trailing_bytes_after_zip_end_record(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    tailed = tmp_path / "tailed.zip"
    tailed.write_bytes(archive_path.read_bytes() + b"untracked trailing data")

    with pytest.raises(ReleaseError, match="trailing bytes"):
        validate_bundle(tailed)


def test_validator_rejects_valid_zip_with_adjusted_prefix_offsets(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    original = archive_path.read_bytes()
    prefix = b"prefix"
    prefixed = bytearray(prefix + original)
    eocd = prefixed.rfind(b"PK\x05\x06")
    central_offset = int.from_bytes(prefixed[eocd + 16 : eocd + 20], "little")
    prefixed[eocd + 16 : eocd + 20] = (central_offset + len(prefix)).to_bytes(4, "little")
    entry_count = int.from_bytes(prefixed[eocd + 10 : eocd + 12], "little")
    cursor = central_offset + len(prefix)
    for _ in range(entry_count):
        assert prefixed[cursor : cursor + 4] == b"PK\x01\x02"
        local_offset = int.from_bytes(prefixed[cursor + 42 : cursor + 46], "little")
        prefixed[cursor + 42 : cursor + 46] = (local_offset + len(prefix)).to_bytes(4, "little")
        name_length = int.from_bytes(prefixed[cursor + 28 : cursor + 30], "little")
        extra_length = int.from_bytes(prefixed[cursor + 30 : cursor + 32], "little")
        comment_length = int.from_bytes(prefixed[cursor + 32 : cursor + 34], "little")
        cursor += 46 + name_length + extra_length + comment_length
    prefixed_path = tmp_path / "prefixed.zip"
    prefixed_path.write_bytes(prefixed)
    with zipfile.ZipFile(prefixed_path) as archive:
        assert archive.namelist() == sorted(archive.namelist())

    with pytest.raises(ReleaseError, match="deterministic canonical layout"):
        validate_bundle(prefixed_path)


def test_validator_rejects_encrypted_archive_members(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    encrypted = bytearray(archive_path.read_bytes())
    # The manifest is the last sorted member; validation must reject its flag
    # before attempting to read the encrypted JSON payload.
    local_header = encrypted.rfind(b"PK\x03\x04")
    central_header = encrypted.rfind(b"PK\x01\x02")
    assert local_header >= 0 and central_header >= 0
    encrypted[local_header + 6] |= 0x01
    encrypted[central_header + 8] |= 0x01
    encrypted_path = tmp_path / "encrypted.zip"
    encrypted_path.write_bytes(encrypted)

    with pytest.raises(ReleaseError, match="unsupported flags"):
        validate_bundle(encrypted_path)


def test_validator_wraps_archive_crc_errors(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    corrupted = bytearray(archive_path.read_bytes())
    local_header = corrupted.find(b"PK\x03\x04")
    filename_length = int.from_bytes(corrupted[local_header + 26 : local_header + 28], "little")
    extra_length = int.from_bytes(corrupted[local_header + 28 : local_header + 30], "little")
    payload_offset = local_header + 30 + filename_length + extra_length
    corrupted[payload_offset] ^= 0x01
    corrupted_path = tmp_path / "corrupted.zip"
    corrupted_path.write_bytes(corrupted)

    with pytest.raises(ReleaseError, match="cannot read archive member"):
        validate_bundle(corrupted_path)


def test_manifest_timestamp_is_explicit_source_input(tmp_path: Path) -> None:
    first = build_contract_release(
        _source_tree(tmp_path / "source-one", manifest_timestamp="2026-01-02T03:04:05Z"),
        tmp_path / "dist-one",
    )
    second = build_contract_release(
        _source_tree(tmp_path / "source-two", manifest_timestamp="2026-01-03T03:04:05Z"),
        tmp_path / "dist-two",
    )

    assert json.loads(_manifest_bytes(first))["generated_at_utc"] == "2026-01-02T03:04:05Z"
    assert json.loads(_manifest_bytes(second))["generated_at_utc"] == "2026-01-03T03:04:05Z"
    assert _manifest_bytes(first) != _manifest_bytes(second)


def test_validator_rejects_unsafe_archive_paths(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    unsafe_archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path) as source, zipfile.ZipFile(unsafe_archive, "w") as target:
        for member in source.infolist():
            target.writestr(member, source.read(member.filename))
        target.writestr(f"{DOC_ID}_bundle_v{VERSION}/../escape.json", b"{}")

    with pytest.raises(ReleaseError, match="unsafe archive path"):
        validate_bundle(unsafe_archive)


def test_validator_rejects_duplicate_archive_paths(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    duplicate_archive = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(archive_path) as source, zipfile.ZipFile(duplicate_archive, "w") as target:
        for member in source.infolist():
            target.writestr(member, source.read(member.filename))
        contract_member = f"{DOC_ID}_bundle_v{VERSION}/{DOC_ID}_Contract_v{VERSION}.json"
        with pytest.warns(UserWarning, match="Duplicate name"):
            target.writestr(contract_member, source.read(contract_member))

    with pytest.raises(ReleaseError, match="duplicate archive path"):
        validate_bundle(duplicate_archive)


def test_validator_rejects_payload_that_disagrees_with_manifest(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    altered_archive = tmp_path / "altered.zip"
    with zipfile.ZipFile(archive_path) as source, zipfile.ZipFile(altered_archive, "w") as target:
        for member in source.infolist():
            payload = source.read(member.filename)
            if member.filename.endswith(f"{DOC_ID}_Contract_v{VERSION}.json"):
                payload += b" "
            target.writestr(member, payload)

    with pytest.raises(ReleaseError, match="manifest hash mismatch"):
        validate_bundle(altered_archive)


def test_validator_rejects_manifest_size_mismatch(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    altered_archive = tmp_path / "wrong-size.zip"
    with zipfile.ZipFile(archive_path) as source, zipfile.ZipFile(altered_archive, "w") as target:
        for member in source.infolist():
            payload = source.read(member.filename)
            if member.filename.endswith("bundle.manifest.json"):
                manifest = json.loads(payload)
                manifest["files"][0]["bytes"] += 1
                payload = _json_bytes(manifest)
            target.writestr(member, payload)

    with pytest.raises(ReleaseError, match="manifest size mismatch"):
        validate_bundle(altered_archive)


def test_validator_rejects_unordered_archive_members(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    unordered_archive = tmp_path / "unordered.zip"
    with zipfile.ZipFile(archive_path) as source, zipfile.ZipFile(unordered_archive, "w") as target:
        for member in reversed(source.infolist()):
            target.writestr(member, source.read(member.filename))

    with pytest.raises(ReleaseError, match="members must be in sorted order"):
        validate_bundle(unordered_archive)


def test_validator_rejects_symlink_encoded_as_regular_mode(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )
    symlink_archive = tmp_path / "symlink.zip"
    with zipfile.ZipFile(archive_path) as source, zipfile.ZipFile(symlink_archive, "w") as target:
        for member in source.infolist():
            if member.filename.endswith(f"{DOC_ID}_Contract_v{VERSION}.json"):
                symlink_info = zipfile.ZipInfo(member.filename, date_time=member.date_time)
                symlink_info.create_system = 3
                symlink_info.external_attr = (stat.S_IFLNK | 0o644) << 16
                symlink_info.compress_type = zipfile.ZIP_STORED
                target.writestr(symlink_info, source.read(member.filename))
            else:
                target.writestr(member, source.read(member.filename))

    with pytest.raises(ReleaseError, match="non-canonical permissions"):
        validate_bundle(symlink_archive)


def test_builder_refuses_to_replace_different_bytes_at_same_identity(tmp_path: Path) -> None:
    output_dir = tmp_path / "dist"
    first_source = _source_tree(tmp_path / "source-one", contract_summary="first")
    second_source = _source_tree(tmp_path / "source-two", contract_summary="second")
    first_path = build_contract_release(first_source, output_dir)
    original_bytes = first_path.read_bytes()

    with pytest.raises(ReleaseError, match="refusing to replace existing release"):
        build_contract_release(second_source, output_dir)

    assert first_path.read_bytes() == original_bytes


def test_validator_script_runs_from_a_different_working_directory(tmp_path: Path) -> None:
    archive_path = build_contract_release(
        _source_tree(tmp_path / "source"), tmp_path / "dist"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "tools/validate_contract_release.py"),
            str(archive_path),
        ],
        check=False,
        capture_output=True,
        cwd=tmp_path,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "VALID"


def test_quorum_successor_candidate_builds_as_valid_deterministic_bundle(tmp_path: Path) -> None:
    source = REPOSITORY_ROOT / "release-src/current/QUORUM-1/1.0.1"

    first = build_contract_release(
        source, tmp_path / "quorum-build-one", allow_candidate=True
    )
    second = build_contract_release(
        source, tmp_path / "quorum-build-two", allow_candidate=True
    )

    assert _sha256(first.read_bytes()) == _sha256(second.read_bytes())
    assert validate_bundle(first)["status"] == "VALID"
