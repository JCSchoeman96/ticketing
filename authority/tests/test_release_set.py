"""Tests for dependency validation across cyclic release candidate sets."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import hashlib
import zipfile

from tools.build_contract_release import build_contract_release, validate_bundle
from tools.dependency_graph import candidate_dependency_graph, summarize_strongly_connected_components
from tools.reconcile_contracts import strongly_connected_components
from tools.validate_release_set import validate_release_set

from test_build_contract_release import REPOSITORY_ROOT, _source_tree


CS0_RELEASE = REPOSITORY_ROOT / "contracts/CS-0/CS-0_bundle_v3.0.1.zip"


def _candidate(
    root: Path,
    doc_id: str,
    version: str,
    dependencies: list[dict[str, str]],
    *,
    summary: str = "Deterministic fixture contract",
) -> Path:
    source = _source_tree(
        root / f"source-{doc_id}",
        doc_id=doc_id,
        version=version,
        dependencies=dependencies,
        contract_summary=summary,
    )
    output_key = hashlib.sha256(summary.encode("utf-8")).hexdigest()[:8]
    return build_contract_release(source, root / f"dist-{doc_id}-{output_key}")


def _dependency(target: str, minimum: str = "1.0.0") -> dict[str, str]:
    return {
        "doc_id": target,
        "min_version": minimum,
        "edge_type": "requires",
        "reason": "synthetic candidate-set test dependency",
    }


def test_candidate_set_resolves_cycle_as_one_unit(tmp_path: Path) -> None:
    candidate_a = _candidate(tmp_path, "AAA-1", "1.0.0", [_dependency("BBB-1")])
    candidate_b = _candidate(tmp_path, "BBB-1", "1.0.0", [_dependency("AAA-1")])

    result = validate_release_set([candidate_a, candidate_b], [CS0_RELEASE])

    assert result["status"] == "VALID"
    assert result["candidate_count"] == 2
    assert result["edge_status_counts"] == {"RESOLVED_WITHIN_CANDIDATE_SET": 2}


def test_candidate_set_resolves_external_dependency_from_accepted_release(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path, "AAA-1", "1.0.0", [_dependency("CS-0", "3.0.1")])

    result = validate_release_set([candidate], [CS0_RELEASE])

    assert result["status"] == "VALID", result["errors"]
    assert result["edge_status_counts"] == {"RESOLVED_ACCEPTED": 1}


def test_candidate_set_uses_audit_validation_for_adopted_legacy_releases(tmp_path: Path) -> None:
    accepted_path = _candidate(tmp_path, "DOC-1", "1.2.3", [])
    with zipfile.ZipFile(accepted_path, "r") as source:
        entries = [(info.filename, source.read(info)) for info in source.infolist()]
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as target_archive:
        for name, payload in entries:
            info = zipfile.ZipInfo(name, date_time=(2023, 5, 6, 7, 8, 10))
            info.compress_type = zipfile.ZIP_STORED
            target_archive.writestr(info, payload)
    accepted_path.write_bytes(output.getvalue())
    accepted_hash = hashlib.sha256(accepted_path.read_bytes()).hexdigest()
    accepted_record = {
        "doc_id": "DOC-1",
        "version": "1.2.3",
        "path": str(accepted_path),
        "sha256": accepted_hash,
        "status": "VALID",
        "bundle_validation": {
            "status": "VALID_WITH_WARNING",
            "doc_id": "DOC-1",
            "version": "1.2.3",
            "zip_sha256": accepted_hash,
        },
    }
    cs0_validation = validate_bundle(CS0_RELEASE)
    cs0_record = {
        "doc_id": "CS-0",
        "version": "3.0.1",
        "path": str(CS0_RELEASE),
        "sha256": cs0_validation["zip_sha256"],
        "status": "VALID",
        "bundle_validation": cs0_validation,
    }
    candidate = _candidate(
        tmp_path,
        "AAA-1",
        "1.0.0",
        [_dependency("DOC-1", "1.2.3")],
    )

    result = validate_release_set(
        [candidate],
        [CS0_RELEASE, accepted_path],
        accepted_release_records=[cs0_record, accepted_record],
    )

    assert result["status"] == "VALID", result["errors"]
    assert result["edge_status_counts"] == {"RESOLVED_ACCEPTED": 1}


def test_candidate_set_coalesces_same_identity_same_hash_representations(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path, "AAA-1", "1.0.0", [])
    duplicate_path = tmp_path / "same-payload.zip"
    duplicate_path.write_bytes(candidate.read_bytes())

    result = validate_release_set([candidate, duplicate_path], [CS0_RELEASE])

    assert result["status"] == "VALID"
    assert result["candidate_count"] == 1
    assert result["duplicate_same_hash_representations"] == {
        "AAA-1@1.0.0": [str(duplicate_path)]
    }


def test_candidate_set_requires_each_target_to_be_accepted_or_in_set(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path, "AAA-1", "1.0.0", [_dependency("MISSING-1")])

    result = validate_release_set([candidate], [CS0_RELEASE])

    assert result["status"] == "INVALID"
    assert result["edges"][0]["status"] == "BLOCKED_INVALID_TARGET"


def test_release_set_rejects_empty_candidate_list() -> None:
    result = validate_release_set([], [CS0_RELEASE])

    assert result["status"] == "INVALID"
    assert "candidate release set must contain at least one candidate bundle" in result["errors"]


def test_candidate_set_checks_minimum_versions_numerically(tmp_path: Path) -> None:
    candidate_a = _candidate(tmp_path, "AAA-1", "1.0.0", [_dependency("BBB-1", "4.9.9")])
    candidate_b = _candidate(tmp_path, "BBB-1", "4.10.0", [])

    result = validate_release_set([candidate_a, candidate_b], [CS0_RELEASE])

    assert result["status"] == "VALID"
    assert result["edges"][0]["target_version"] == "4.10.0"


def test_candidate_set_rejects_target_below_minimum(tmp_path: Path) -> None:
    candidate_a = _candidate(tmp_path, "AAA-1", "1.0.0", [_dependency("BBB-1", "1.0.1")])
    candidate_b = _candidate(tmp_path, "BBB-1", "1.0.0", [])

    result = validate_release_set([candidate_a, candidate_b], [CS0_RELEASE])

    assert result["status"] == "INVALID"
    assert result["edges"][0]["status"] == "BLOCKED_BELOW_MINIMUM"


def test_candidate_set_rejects_duplicate_doc_identity_versions(tmp_path: Path) -> None:
    candidate_a = _candidate(tmp_path, "AAA-1", "1.0.0", [])
    candidate_a_duplicate = _candidate(
        tmp_path, "AAA-1", "1.0.0", [], summary="different payload"
    )

    result = validate_release_set(
        [candidate_a, candidate_a_duplicate], [CS0_RELEASE]
    )

    assert result["status"] == "INVALID"
    assert any("candidate identity AAA-1@1.0.0 has different SHA-256" in error for error in result["errors"])


def test_scc_analysis_reports_cycle_and_singletons_deterministically() -> None:
    components = strongly_connected_components(
        {
            "AAA-1": {"BBB-1"},
            "BBB-1": {"AAA-1", "CCC-1"},
            "CCC-1": set(),
            "DDD-1": set(),
        }
    )

    assert components == [["AAA-1", "BBB-1"], ["CCC-1"], ["DDD-1"]]


def test_candidate_graph_reports_internal_and_boundary_edges() -> None:
    records = {
        "AAA-1": {
            "status": "invalid",
            "selected_candidate": None,
            "candidates": [
                {
                    "version": "1.0.0",
                    "source_path": "AAA-1.zip",
                    "zip_sha256": "a" * 64,
                    "validation": {"status": "INVALID"},
                    "contract_metadata": {
                        "dependencies": [
                            {"doc_id": "BBB-1", "min_version": "1.0.0", "edge_type": "requires"},
                            {"doc_id": "OUT-1", "min_version": "1.0.0", "edge_type": "requires"},
                        ]
                    },
                }
            ],
        },
        "BBB-1": {
            "status": "selected",
            "selected_candidate": {
                "version": "1.0.0",
                "source_path": "BBB-1.zip",
                "zip_sha256": "b" * 64,
                "validation": {"status": "VALID"},
                "contract_metadata": {
                    "dependencies": [{"doc_id": "AAA-1", "min_version": "1.0.0", "edge_type": "requires"}]
                },
            },
            "candidates": [],
        },
    }

    graph = candidate_dependency_graph(records)
    components = summarize_strongly_connected_components(graph)

    cycle = next(item for item in components if item["cyclic"])
    assert cycle["members"] == ["AAA-1", "BBB-1"]
    assert len(cycle["internal_edges"]) == 2
    assert [edge["target_doc_id"] for edge in cycle["external_outbound_edges"]] == ["OUT-1"]


def test_current_release_inputs_come_from_manifest() -> None:
    from tools.validate_release_set import current_release_inputs

    paths, records = current_release_inputs(REPOSITORY_ROOT)

    assert len(paths) == 58
    canon = next(row for row in records if row["doc_id"] == "CANON-1")
    assert canon["path"].endswith("contracts/CANON-1/CANON-1_bundle_v2.0.15.zip")
    assert canon["sha256"] == "e79446900cdbade57cf72bf5278b68c0b1c49fe873b894766b4086c15206ed6b"
