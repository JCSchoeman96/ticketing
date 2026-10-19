"""Tests for freezing and rendering the canonical suite selection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tools import generate_canon as canon_module
from tools.generate_canon import (
    CanonGenerationError,
    build_canon_contract,
    build_canon_test_gates,
    freeze_resolved_selection,
    generate_source_files,
    validate_selection_pin_status,
    validate_no_canon_member_dependency,
    freeze_canon_successor,
)


def test_verification_paths_include_untracked_files_under_nested_authority_root(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "ticketing"
    authority_root = repository / "authority"
    selection = authority_root / "release-src/current/CANON-1/2.0.14/resolved-selection.json"
    selection.parent.mkdir(parents=True)
    selection.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)

    paths = canon_module._verification_paths(authority_root)

    assert "release-src/current/CANON-1/2.0.14/resolved-selection.json" in paths
    assert "release-src/current/CANON-1/2.0.14/resolved-selection.json" not in canon_module._tracked_paths(
        authority_root
    )


def _candidate(doc_id: str, version: str, digest: str, path: str) -> dict[str, object]:
    return {
        "doc_id": doc_id,
        "version": version,
        "source_path": path,
        "zip_sha256": digest,
        "validation": {"status": "VALID"},
    }


def _accepted(doc_id: str, version: str, digest: str, path: str) -> dict[str, object]:
    return {
        "doc_id": doc_id,
        "version": version,
        "sha256": digest,
        "path": path,
        "status": "ACCEPTED_RELEASE",
    }


def _selection_inputs() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    old_led = _candidate(
        "LED-1", "4.4.7", "a" * 64, "ticketing-contracts/LED-1_v4.4.7.zip"
    )
    new_led = _candidate(
        "LED-1", "4.6.1", "b" * 64, "ticketing-contracts/LED-1_v4.6.1.zip"
    )
    doc = _candidate("DOC-1", "1.2.3", "c" * 64, "contracts/DOC-1.zip")
    ext = _candidate("EXT-1", "2.1.7", "d" * 64, "contracts/EXT-1.zip")
    audit = {
        "summary": {
            "scan_mode": "canonical",
            "audited_git_commit": "1" * 40,
            "dependency_edge_count": 712,
            "dependency_target_unresolved_count": 0,
            "dependency_floor_conflict_count": 0,
            "dependency_edge_invalid_count": 0,
        },
        "contracts": {
            "DOC-1": {
                "status": "selected",
                "selected_version": "1.2.3",
                "selected_candidate": doc,
                "candidates": [doc],
                "selection_basis": ["one valid tracked version"],
            },
            "LED-1": {
                "status": "ambiguous",
                "selected_version": None,
                "selected_candidate": None,
                "candidates": [old_led, new_led],
                "selection_basis": [],
            },
            "EXT-1": {
                "status": "selected",
                "selected_version": "2.1.7",
                "selected_candidate": ext,
                "candidates": [ext],
                "selection_basis": ["valid support dependency"],
            },
            "CANON-1": {
                "status": "invalid",
                "selected_version": None,
                "selected_candidate": None,
                "candidates": [],
                "selection_basis": [],
            },
        },
    }
    registry = {
        "releases": [
            _accepted("DOC-1", "1.2.3", "c" * 64, "contracts/DOC-1.zip"),
            _accepted("LED-1", "4.4.7", "a" * 64, "ticketing-contracts/LED-1_v4.4.7.zip"),
            _accepted("EXT-1", "2.1.7", "d" * 64, "contracts/EXT-1.zip"),
        ]
    }
    policy = {
        "format_version": 1,
        "generated_doc_id": "CANON-1",
        "generated_version": "2.0.2",
        "version_overrides": {
            "LED-1": {
                "version": "4.4.7",
                "sha256": "a" * 64,
                "reason": "Owner selected the validated release retaining both controls.",
            }
        },
        "excluded_contracts": [
            {
                "doc_id": "EXT-1",
                "membership_status": "ACCEPTED_DEPENDENCY_ONLY",
                "version": "2.1.7",
                "sha256": "d" * 64,
                "reason": "Accepted support dependency, not a CANON member.",
            },
            {
                "doc_id": "FR-1",
                "membership_status": "DEFERRED_NONBLOCKING",
                "reason": "Owner deferred current-suite membership.",
            },
        ],
    }
    return audit, registry, policy


def test_freeze_uses_led_owner_choice_and_excludes_dependency_only_contract() -> None:
    audit, registry, policy = _selection_inputs()

    selection = freeze_resolved_selection(
        audit,
        registry,
        policy,
        accepted_registry_sha256="e" * 64,
        policy_sha256="f" * 64,
    )

    assert [row["doc_id"] for row in selection["members"]] == ["DOC-1", "LED-1"]
    led = selection["members"][1]
    assert led["version"] == "4.4.7"
    assert led["sha256"] == "a" * 64
    assert selection["exclusions"][0]["doc_id"] == "EXT-1"
    assert selection["exclusions"][1]["doc_id"] == "FR-1"


def test_freeze_rejects_unaccepted_or_hash_mismatched_selection() -> None:
    audit, registry, policy = _selection_inputs()
    registry["releases"] = [
        row for row in registry["releases"] if row["doc_id"] != "DOC-1"
    ]

    with pytest.raises(CanonGenerationError, match="DOC-1@1.2.3.*ACCEPTED_RELEASE"):
        freeze_resolved_selection(
            audit,
            registry,
            policy,
            accepted_registry_sha256="e" * 64,
            policy_sha256="f" * 64,
        )


def test_canon_contract_pins_are_sorted_and_include_exact_hashes() -> None:
    audit, registry, policy = _selection_inputs()
    selection = freeze_resolved_selection(
        audit,
        registry,
        policy,
        accepted_registry_sha256="e" * 64,
        policy_sha256="f" * 64,
    )

    contract = build_canon_contract(
        selection,
        artifacts_by_doc={
            "DOC-1": [{"path": "DOC-1.zip/contract.json", "sha256": "1" * 64, "bytes": 10}],
            "LED-1": [{"path": "LED-1.zip/contract.json", "sha256": "2" * 64, "bytes": 20}],
        },
        generated_at_utc="2026-10-09T00:00:00Z",
    )

    assert [pin["doc_id"] for pin in contract["canonical_bundles"]] == ["DOC-1", "LED-1"]
    assert contract["canonical_bundles"][1]["version"] == "4.4.7"
    assert contract["canonical_bundles"][1]["bundle_sha256"] == "a" * 64
    assert contract["canonical_bundles"][1]["artifacts"][0]["sha256"] == "2" * 64


def test_canon_gates_assert_unique_membership_and_exclusions() -> None:
    audit, registry, policy = _selection_inputs()
    selection = freeze_resolved_selection(
        audit,
        registry,
        policy,
        accepted_registry_sha256="e" * 64,
        policy_sha256="f" * 64,
    )
    contract = build_canon_contract(
        selection,
        artifacts_by_doc={
            "DOC-1": [{"path": "DOC-1.zip/contract.json", "sha256": "1" * 64, "bytes": 10}],
            "LED-1": [{"path": "LED-1.zip/contract.json", "sha256": "2" * 64, "bytes": 20}],
        },
        generated_at_utc="2026-10-09T00:00:00Z",
    )

    gates = build_canon_test_gates(contract, generated_at_utc="2026-10-09T00:00:00Z")
    assertions = gates["gates"][0]["assertions"]
    criteria = {
        item["details"]["check"]: item["details"]
        for item in assertions
        if item["type"] == "acceptance_criteria"
    }

    assert criteria["unique_canonical_member_pins"]["expected_member_count"] == 2
    assert criteria["deferred_and_dependency_only_contracts_are_not_pinned"]["doc_ids"] == ["EXT-1", "FR-1"]
    assert criteria["no_canonical_member_depends_on_pinset"]["doc_id"] == "CANON-1"


def test_member_contract_cannot_depend_on_the_canon_pinset() -> None:
    contract = {
        "doc_id": "DOC-1",
        "dependencies": [{"doc_id": "CANON-1", "edge_type": "requires"}],
        "dependency_floors": {},
    }

    with pytest.raises(CanonGenerationError, match="DOC-1.*CANON-1"):
        validate_no_canon_member_dependency("DOC-1", contract, "CANON-1")


def test_member_contract_cannot_mirror_canon_floor() -> None:
    contract = {
        "doc_id": "DOC-1",
        "dependencies": [],
        "dependency_floors": {"CANON-1": "2.0.1"},
    }

    with pytest.raises(CanonGenerationError, match="DOC-1.*CANON-1"):
        validate_no_canon_member_dependency("DOC-1", contract, "CANON-1")


def test_source_generation_uses_accepted_registry_validation_for_legacy_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = Path("release-artifacts/accepted/acceptance.json")
    bundle_path = "legacy/DOC-1_bundle_v1.0.0.zip"
    digest = "a" * 64
    registry = {
        "releases": [
            _accepted("DOC-1", "1.0.0", digest, bundle_path),
        ]
    }
    registry_bytes = (json.dumps(registry, indent=2, sort_keys=True) + "\n").encode("utf-8")
    registry_file = tmp_path / registry_path
    registry_file.parent.mkdir(parents=True)
    registry_file.write_bytes(registry_bytes)
    (tmp_path / bundle_path).parent.mkdir(parents=True)
    (tmp_path / bundle_path).write_bytes(b"legacy ZIP bytes")
    tracked = {registry_path.as_posix(), bundle_path}

    monkeypatch.setattr(canon_module, "_tracked_paths", lambda _: tracked)
    monkeypatch.setattr(
        canon_module,
        "validate_accepted_release_registry",
        lambda *_: {"status": "VALID", "errors": []},
    )
    monkeypatch.setattr(
        canon_module,
        "validate_bundle",
        lambda *_: pytest.fail("legacy adopted ZIP must not be rebuilt or checked as a new deterministic ZIP"),
    )
    monkeypatch.setattr(
        canon_module,
        "_archive_contract_data",
        lambda *_: {"doc_id": "DOC-1", "dependencies": [], "dependency_floors": {}},
    )
    monkeypatch.setattr(
        canon_module,
        "_archive_artifacts",
        lambda *_: [{"path": "contract.json", "sha256": "b" * 64, "bytes": 10}],
    )

    result = generate_source_files(
        tmp_path,
        {
            "accepted_registry_input_sha256": hashlib.sha256(registry_bytes).hexdigest(),
            "generated_contract": {"doc_id": "CANON-1", "version": "2.0.2"},
            "members": [
                {
                    "doc_id": "DOC-1",
                    "version": "1.0.0",
                    "accepted_artifact_path": bundle_path,
                    "sha256": digest,
                    "selection_basis": ["accepted legacy release"],
                }
            ],
            "exclusions": [],
            "dependency_closure": {
                "edge_count": 0,
                "unresolved_required_edges": 0,
                "below_minimum_edges": 0,
                "invalid_dependency_records": 0,
            },
            "audit_source_commit": "1" * 40,
        },
        registry_path=registry_path,
        output_dir=tmp_path / "source",
        generated_at_utc="2026-10-09T00:00:00Z",
        generator_commit="2" * 40,
    )

    assert result["status"] == "BUILT_CANDIDATE_SOURCE"
    assert (tmp_path / "source" / "contract.json").is_file()


def test_frozen_canon_members_require_pinned_acceptance_status() -> None:
    selection = {
        "members": [
            {
                "doc_id": "DOC-1",
                "version": "1.0.0",
                "accepted_artifact_path": "DOC-1.zip",
                "sha256": "a" * 64,
            }
        ],
        "exclusions": [],
    }
    accepted = {
        ("DOC-1", "1.0.0"): {
            "doc_id": "DOC-1",
            "version": "1.0.0",
            "sha256": "a" * 64,
            "path": "DOC-1.zip",
            "status": "ACCEPTED_RELEASE",
            "canonical_pin_status": "not_pinned",
        }
    }

    with pytest.raises(CanonGenerationError, match="DOC-1.*pinned"):
        validate_selection_pin_status(selection, accepted)


def test_frozen_dependency_only_exclusion_cannot_be_marked_pinned() -> None:
    selection = {
        "members": [],
        "exclusions": [
            {
                "doc_id": "EXT-1",
                "version": "2.1.7",
                "accepted_artifact_path": "EXT-1.zip",
                "sha256": "a" * 64,
                "membership_status": "ACCEPTED_DEPENDENCY_ONLY",
            }
        ],
    }
    accepted = {
        ("EXT-1", "2.1.7"): {
            "doc_id": "EXT-1",
            "version": "2.1.7",
            "sha256": "a" * 64,
            "path": "EXT-1.zip",
            "status": "ACCEPTED_RELEASE",
            "canonical_pin_status": "pinned",
        }
    }

    with pytest.raises(CanonGenerationError, match="EXT-1.*not_pinned"):
        validate_selection_pin_status(selection, accepted)


def test_manifest_identity_lookup_ignores_historical_zip_paths() -> None:
    from tools.generate_canon import canon_selection_path, manifest_record_by_identity

    manifest = {
        "format_version": 1,
        "contracts": [
            {
                "doc_id": "DOC-1",
                "version": "1.2.3",
                "membership": "CANON_MEMBER",
                "zip_path": "contracts/DOC-1/DOC-1_bundle_v1.2.3.zip",
                "zip_sha256": "a" * 64,
            }
        ],
    }

    row = manifest_record_by_identity(manifest, "DOC-1", "1.2.3", "CANON_MEMBER")

    assert row["zip_path"] == "contracts/DOC-1/DOC-1_bundle_v1.2.3.zip"
    with pytest.raises(CanonGenerationError, match="no active manifest record"):
        manifest_record_by_identity(manifest, "DOC-1", "1.2.4", "CANON_MEMBER")

    manifest["contracts"].append(
        {
            "doc_id": "CANON-1",
            "version": "2.0.2",
            "membership": "CANON_INDEX",
            "zip_path": "contracts/CANON-1/CANON-1_bundle_v2.0.2.zip",
            "zip_sha256": "b" * 64,
        }
    )
    assert canon_selection_path(Path("."), manifest).as_posix() == (
        "release-src/current/CANON-1/2.0.2/resolved-selection.json"
    )


def _successor_inputs() -> tuple[dict[str, object], dict[str, object], list[dict[str, object]]]:
    pins = [
        {"doc_id": "DOC-1", "version": "1.0.0", "bundle_sha256": "a" * 64,
         "zip_path": "contracts/DOC-1/DOC-1_bundle_v1.0.0.zip", "membership_status": "CANON_MEMBER",
         "artifacts": []},
        {"doc_id": "SM-0", "version": "1.2.1", "bundle_sha256": "b" * 64,
         "zip_path": "contracts/SM-0/SM-0_bundle_v1.2.1.zip", "membership_status": "CANON_MEMBER",
         "artifacts": []},
    ]
    canon = {"doc_id": "CANON-1", "version": "2.0.4", "canonical_bundles": pins,
             "canonical_exclusions": [
                 {"doc_id": "EXT-1", "membership_status": "ACCEPTED_DEPENDENCY_ONLY",
                  "version": "2.1.7", "sha256": "c" * 64,
                  "accepted_artifact_path": "release-artifacts/accepted/EXT-1.zip"},
                 {"doc_id": "FR-1", "membership_status": "DEFERRED_NONBLOCKING"},
             ]}
    manifest = {"contracts": [
        {"doc_id": "DOC-1", "version": "1.0.0", "membership": "CANON_MEMBER",
         "zip_path": pins[0]["zip_path"], "zip_sha256": "a" * 64},
        {"doc_id": "SM-0", "version": "1.2.1", "membership": "CANON_MEMBER",
         "zip_path": pins[1]["zip_path"], "zip_sha256": "b" * 64},
        {"doc_id": "EXT-1", "version": "2.1.7", "membership": "DEPENDENCY_ONLY",
         "zip_path": "contracts/EXT-1/EXT-1_bundle_v2.1.7.zip", "zip_sha256": "c" * 64},
        {"doc_id": "CANON-1", "version": "2.0.4", "membership": "CANON_INDEX",
         "zip_path": "contracts/CANON-1/CANON-1_bundle_v2.0.4.zip", "zip_sha256": "9" * 64},
    ]}
    candidate = {
        "doc_id": "SM-0", "version": "1.2.2", "sha256": "e" * 64, "actual_sha256": "e" * 64,
        "zip_path": "contracts/SM-0/SM-0_bundle_v1.2.2.zip", "validation": {"status": "VALID"},
        "contract": {"doc_id": "SM-0", "version": "1.2.2", "dependencies": []},
    }
    return canon, manifest, [candidate]


def _closed_dependencies() -> dict[str, object]:
    return {
        "edge_count": 730, "unresolved_required_edges": 0,
        "below_minimum_edges": 0, "invalid_dependency_records": 0,
        "input_sha256": "f" * 64,
    }


def test_successor_preserves_membership_and_replaces_only_explicit_member_pin() -> None:
    canon, manifest, candidates = _successor_inputs()

    selection = freeze_canon_successor(
        canon, manifest, candidates, _closed_dependencies(),
        generated_version="2.0.5", base_canon_sha256="9" * 64,
        manifest_sha256="8" * 64, generator_commit="1" * 40,
    )

    assert [row["doc_id"] for row in selection["members"]] == ["DOC-1", "SM-0"]
    assert selection["members"][1]["version"] == "1.2.2"
    assert selection["members"][1]["sha256"] == "e" * 64
    assert selection["exclusions"][0]["accepted_artifact_path"] == manifest["contracts"][2]["zip_path"]
    assert len(selection["members"]) == 2
    assert "release-artifacts/accepted" not in json.dumps(selection["exclusions"])


@pytest.mark.parametrize("mutate, message", [
    (lambda c, m, d: d[0].update(sha256="0" * 64), "candidate ZIP hash mismatch"),
    (lambda c, m, d: d[0].update(validation={"status": "INVALID"}), "candidate is not valid"),
    (lambda c, m, d: d[0].update(doc_id="NEW-1"), "not an existing CANON member"),
    (lambda c, m, d: d.append(dict(d[0])), "duplicate candidate doc_id"),
    (lambda c, m, d: d[0].update(doc_id="CANON-1"), "cannot pin CANON-1"),
    (lambda c, m, d: d[0].update(version="1.2.1", contract={"doc_id": "SM-0", "version": "1.2.1"}),
     "must be newer than active"),
])
def test_successor_rejects_unsafe_candidate_changes(mutate, message: str) -> None:
    canon, manifest, candidates = _successor_inputs()
    mutate(canon, manifest, candidates)
    with pytest.raises(CanonGenerationError, match=message):
        freeze_canon_successor(
            canon, manifest, candidates, _closed_dependencies(),
            generated_version="2.0.5", base_canon_sha256="9" * 64,
            manifest_sha256="8" * 64, generator_commit="1" * 40,
        )


@pytest.mark.parametrize("field", [
    "unresolved_required_edges", "below_minimum_edges", "invalid_dependency_records",
])
def test_successor_rejects_incomplete_dependency_closure(field: str) -> None:
    canon, manifest, candidates = _successor_inputs()
    closure = _closed_dependencies()
    closure[field] = 1
    with pytest.raises(CanonGenerationError, match="dependency closure"):
        freeze_canon_successor(
            canon, manifest, candidates, closure,
            generated_version="2.0.5", base_canon_sha256="9" * 64,
            manifest_sha256="8" * 64, generator_commit="1" * 40,
        )


@pytest.mark.parametrize("version", ["2.0.4", "2.0.3", "1.99.99"])
def test_successor_rejects_same_or_older_canon_version(version: str) -> None:
    canon, manifest, candidates = _successor_inputs()
    with pytest.raises(CanonGenerationError, match="greater than base CANON version"):
        freeze_canon_successor(
            canon, manifest, candidates, _closed_dependencies(), generated_version=version,
            base_canon_sha256="9" * 64, manifest_sha256="8" * 64, generator_commit="1" * 40,
        )


@pytest.mark.parametrize("version", ["2.0.5", "2.1.0", "3.0.0"])
def test_successor_accepts_newer_canon_versions(version: str) -> None:
    canon, manifest, candidates = _successor_inputs()
    selection = freeze_canon_successor(
        canon, manifest, candidates, _closed_dependencies(), generated_version=version,
        base_canon_sha256="9" * 64, manifest_sha256="8" * 64, generator_commit="1" * 40,
    )
    assert selection["generated_contract"]["version"] == version


def test_successor_compares_canon_versions_numerically() -> None:
    canon, manifest, candidates = _successor_inputs()
    canon["version"] = "2.0.9"
    index = next(row for row in manifest["contracts"] if row["doc_id"] == "CANON-1")
    index["version"] = "2.0.9"
    index["zip_path"] = "contracts/CANON-1/CANON-1_bundle_v2.0.9.zip"
    selection = freeze_canon_successor(
        canon, manifest, candidates, _closed_dependencies(), generated_version="2.0.10",
        base_canon_sha256="9" * 64, manifest_sha256="8" * 64, generator_commit="1" * 40,
    )
    assert selection["generated_contract"]["version"] == "2.0.10"


def test_successor_output_is_deterministic_and_keeps_dependency_only_classification() -> None:
    canon, manifest, candidates = _successor_inputs()
    first = freeze_canon_successor(
        canon, manifest, candidates, _closed_dependencies(), generated_version="2.0.5",
        base_canon_sha256="9" * 64, manifest_sha256="8" * 64, generator_commit="1" * 40,
    )
    second = freeze_canon_successor(
        canon, manifest, candidates, _closed_dependencies(), generated_version="2.0.5",
        base_canon_sha256="9" * 64, manifest_sha256="8" * 64, generator_commit="1" * 40,
    )
    assert canon_module._json_bytes(first) == canon_module._json_bytes(second)
    assert first["exclusions"][0]["membership_status"] == "ACCEPTED_DEPENDENCY_ONLY"
    assert len(first["members"]) == len(canon["canonical_bundles"])
    artifacts = {
        "DOC-1": [{"path": "DOC-1_Contract_v1.0.0.json", "sha256": "1" * 64, "bytes": 1}],
        "SM-0": [{"path": "SM-0_Contract_v1.2.2.json", "sha256": "2" * 64, "bytes": 2}],
    }
    contract_a = build_canon_contract(first, artifacts, generated_at_utc="2026-10-09T00:00:00Z")
    contract_b = build_canon_contract(second, artifacts, generated_at_utc="2026-10-09T00:00:00Z")
    gates_a = build_canon_test_gates(contract_a, generated_at_utc="2026-10-09T00:00:00Z")
    gates_b = build_canon_test_gates(contract_b, generated_at_utc="2026-10-09T00:00:00Z")
    assert canon_module._json_bytes(contract_a) == canon_module._json_bytes(contract_b)
    assert canon_module._json_bytes(gates_a) == canon_module._json_bytes(gates_b)


def test_successor_rejects_silent_member_removal_and_implicit_new_release() -> None:
    canon, manifest, candidates = _successor_inputs()
    manifest["contracts"] = [row for row in manifest["contracts"] if row["doc_id"] != "DOC-1"]
    with pytest.raises(CanonGenerationError, match="member was removed"):
        freeze_canon_successor(
            canon, manifest, candidates, _closed_dependencies(), generated_version="2.0.5",
            base_canon_sha256="9" * 64, manifest_sha256="8" * 64, generator_commit="1" * 40,
        )


def test_successor_keeps_56_members_when_only_sm_pin_changes() -> None:
    canon, manifest, candidates = _successor_inputs()
    for index in range(1, 55):
        doc_id = f"DOCX-{index}"
        digest = f"{index:064x}"
        path = f"contracts/{doc_id}/{doc_id}_bundle_v1.0.0.zip"
        canon["canonical_bundles"].append({
            "doc_id": doc_id, "version": "1.0.0", "bundle_sha256": digest,
            "zip_path": path, "membership_status": "CANON_MEMBER", "artifacts": [],
        })
        manifest["contracts"].append({
            "doc_id": doc_id, "version": "1.0.0", "membership": "CANON_MEMBER",
            "zip_path": path, "zip_sha256": digest,
        })
    selection = freeze_canon_successor(
        canon, manifest, candidates, _closed_dependencies(), generated_version="2.0.5",
        base_canon_sha256="9" * 64, manifest_sha256="8" * 64, generator_commit="1" * 40,
    )
    changed = [row["doc_id"] for row in selection["members"] if row["doc_id"] == "SM-0"]
    assert len(selection["members"]) == 56
    assert changed == ["SM-0"]


def test_successor_source_uses_manifest_inputs_without_acceptance_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tools.reconcile_contracts as reconcile

    canon, manifest, _ = _successor_inputs()
    for index in range(1, 55):
        doc_id = f"DOCX-{index}"
        digest = f"{index:064x}"
        path = f"contracts/{doc_id}/{doc_id}_bundle_v1.0.0.zip"
        canon["canonical_bundles"].append({
            "doc_id": doc_id, "version": "1.0.0", "bundle_sha256": digest,
            "zip_path": path, "membership_status": "CANON_MEMBER", "artifacts": [],
        })
        manifest["contracts"].append({
            "doc_id": doc_id, "version": "1.0.0", "membership": "CANON_MEMBER",
            "zip_path": path, "zip_sha256": digest,
        })
    candidate = tmp_path / "candidate.zip"
    candidate.write_bytes(b"validated candidate bytes")
    manifest_path = tmp_path / "contracts/manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    canon_digest = "9" * 64

    monkeypatch.setattr(canon_module, "validate_bundle", lambda path: {
        "status": "VALID", "doc_id": "SM-0", "version": "1.2.2",
        "zip_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
    })
    def verify_candidate_base(*args, **kwargs):
        assert kwargs["identity_exemptions"] == {"SM-0"}
        return {"status": "VALID"}

    monkeypatch.setattr(canon_module, "verify_manifest", verify_candidate_base)
    monkeypatch.setattr(
        canon_module,
        "_contract_from_zip",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            canon_module.ActiveIdentityError("contract filename identity mismatch")
        ),
    )
    monkeypatch.setattr(
        canon_module,
        "_archive_contract_data",
        lambda path, doc_id: canon if doc_id == "CANON-1" else (
            {"doc_id": "SM-0", "version": "1.2.2", "dependencies": []}
            if str(path).endswith("candidate.zip") else
            {"doc_id": doc_id, "version": "1.0.0", "dependencies": []}
        ),
    )
    monkeypatch.setattr(
        reconcile,
        "build_dependency_closure",
        lambda *_: {
            "edge_count": 0, "unresolved_target_edge_count": 0,
            "below_minimum_edge_count": 0, "invalid_dependency_list_count": 0,
            "invalid_dependency_record_count": 0, "invalid_minimum_version_count": 0,
            "status": "resolved",
        },
    )
    monkeypatch.setattr(
        canon_module,
        "_archive_artifacts",
        lambda path: [{"path": "contract.json", "sha256": "1" * 64, "bytes": 1}],
    )
    generated_at = "2026-10-09T00:00:00Z"
    args = dict(
        root=tmp_path, candidate_paths=[candidate], generated_version="2.0.5",
        generated_at_utc=generated_at, generator_commit="1" * 40,
    )
    first = canon_module.generate_canon_successor_source(
        **args, output_dir=tmp_path / "one"
    )
    second = canon_module.generate_canon_successor_source(
        **args, output_dir=tmp_path / "two"
    )

    for filename in ("resolved-selection.json", "contract.json", "test-gates.json"):
        assert (tmp_path / "one" / filename).read_bytes() == (tmp_path / "two" / filename).read_bytes()
    selection = json.loads((tmp_path / "one/resolved-selection.json").read_text())
    provenance = json.loads((tmp_path / "one/generation-provenance.json").read_text())
    assert selection["generation_inputs"]["active_manifest_sha256"] == manifest_digest
    assert selection["generation_inputs"]["base_canon_zip_sha256"] == canon_digest
    assert provenance["generation_inputs"] == selection["generation_inputs"]
    assert selection["generation_inputs"]["superseded_identity_defects"] == [
        {"doc_id": "SM-0", "reason": "contract filename identity mismatch"}
    ]
    assert "accepted_registry_input_sha256" not in provenance
    assert first["resolved_selection_sha256"] == second["resolved_selection_sha256"]

    monkeypatch.setattr(
        canon_module,
        "_contract_from_zip",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            canon_module.ManifestError("must contain exactly one test-gates artifact")
        ),
    )
    with pytest.raises(canon_module.ManifestError, match="exactly one test-gates"):
        canon_module.generate_canon_successor_source(
            **args, output_dir=tmp_path / "structurally-invalid"
        )

    canon, manifest, candidates = _successor_inputs()
    manifest["contracts"].append({
        "doc_id": "NEW-1", "version": "1.0.0", "membership": "CANON_MEMBER",
        "zip_path": "contracts/NEW-1/NEW-1_bundle_v1.0.0.zip", "zip_sha256": "a" * 64,
    })
    with pytest.raises(CanonGenerationError, match="implicit CANON membership change"):
        freeze_canon_successor(
            canon, manifest, candidates, _closed_dependencies(), generated_version="2.0.5",
            base_canon_sha256="9" * 64, manifest_sha256="8" * 64, generator_commit="1" * 40,
        )
