#!/usr/bin/env python3
"""Validate a set of contract candidates against accepted and peer releases."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

if __package__:
    from .build_contract_release import ReleaseError, validate_bundle
    from .contract_manifest import ManifestError, verify_manifest, verify_no_stray_contract_zips
    from .reconcile_contracts import semver_key
else:
    from build_contract_release import ReleaseError, validate_bundle
    from contract_manifest import ManifestError, verify_manifest, verify_no_stray_contract_zips
    from reconcile_contracts import semver_key


def _contract_payload(bundle_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(bundle_path, "r") as archive:
        contracts: list[dict[str, Any]] = []
        for member in archive.infolist():
            if member.is_dir() or PurePosixPath(member.filename).name == "bundle.manifest.json":
                continue
            try:
                value = json.loads(archive.read(member).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict) and value.get("artifact_kind") == "contract":
                contracts.append(value)
    if len(contracts) != 1:
        raise ReleaseError(f"expected exactly one contract artifact in {bundle_path}")
    return contracts[0]


def _schema_dependency_edge_types(cs0_path: Path) -> set[str]:
    contract = _contract_payload(cs0_path)
    try:
        edge_types = contract["schemas"]["contract"]["properties"]["dependencies"]["items"]["properties"]["edge_type"]["enum"]
    except (KeyError, TypeError) as error:
        raise ReleaseError("accepted CS-0 bundle has no dependency edge_type enum") from error
    if not isinstance(edge_types, list) or not all(isinstance(value, str) for value in edge_types):
        raise ReleaseError("accepted CS-0 dependency edge_type enum is malformed")
    return set(edge_types)


def _load_valid_bundle(path: Path, role: str) -> dict[str, Any]:
    try:
        validation = validate_bundle(path)
    except ReleaseError as error:
        return {"path": str(path), "status": "INVALID", "error": str(error)}
    try:
        contract = _contract_payload(path)
    except (OSError, zipfile.BadZipFile, ReleaseError) as error:
        return {"path": str(path), "status": "INVALID", "error": str(error)}
    return {
        "path": str(path),
        "role": role,
        "status": "VALID",
        "doc_id": validation["doc_id"],
        "version": validation["version"],
        "sha256": validation["zip_sha256"],
        "bundle_validation": validation,
        "contract": contract,
    }


def _load_verified_accepted_bundle(
    path: Path,
    accepted_record: dict[str, Any],
) -> dict[str, Any]:
    """Use the acceptance registry's validation instead of reapplying new-ZIP rules."""

    validation = accepted_record.get("bundle_validation")
    if (
        accepted_record.get("validation_status", accepted_record.get("status")) != "VALID"
        or not isinstance(validation, dict)
        or validation.get("status") not in {"VALID", "VALID_WITH_WARNING"}
    ):
        return {
            "path": str(path),
            "role": "accepted",
            "status": "INVALID",
            "error": "accepted registry did not provide a passing bundle validation",
        }
    try:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if digest != accepted_record.get("sha256") or digest != validation.get("zip_sha256"):
            raise ReleaseError("accepted registry hash does not match the accepted bundle bytes")
        contract = _contract_payload(Path(path))
    except (OSError, zipfile.BadZipFile, ReleaseError) as error:
        return {"path": str(path), "role": "accepted", "status": "INVALID", "error": str(error)}
    doc_id = accepted_record.get("doc_id")
    version = accepted_record.get("version")
    if (
        contract.get("doc_id") != doc_id
        or contract.get("version") != version
        or validation.get("doc_id") != doc_id
        or validation.get("version") != version
    ):
        return {
            "path": str(path),
            "role": "accepted",
            "status": "INVALID",
            "error": "accepted registry identity does not match the accepted bundle contents",
        }
    return {
        "path": str(path),
        "role": "accepted",
        "status": "VALID",
        "doc_id": doc_id,
        "version": version,
        "sha256": digest,
        "bundle_validation": validation,
        "contract": contract,
    }


def validate_release_set(
    candidate_paths: list[Path],
    accepted_release_paths: list[Path],
    *,
    accepted_release_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate cyclic candidates against accepted releases and each other.

    A candidate set contains at most one proposed version for each doc_id.
    Every dependency must resolve to that exact candidate version or to one
    unambiguous accepted release, and its explicit minimum must be satisfied.
    """

    errors: list[str] = []
    if not candidate_paths:
        errors.append("candidate release set must contain at least one candidate bundle")
    candidates = [_load_valid_bundle(Path(path), "candidate") for path in candidate_paths]
    if accepted_release_records is None:
        accepted = [_load_valid_bundle(Path(path), "accepted") for path in accepted_release_paths]
    elif len(accepted_release_records) != len(accepted_release_paths):
        accepted = []
        errors.append("accepted release records must correspond one-to-one with accepted paths")
    else:
        accepted = [
            _load_verified_accepted_bundle(Path(path), record)
            for path, record in zip(accepted_release_paths, accepted_release_records)
        ]
    for row in candidates + accepted:
        if row["status"] != "VALID":
            errors.append(f"invalid {row.get('role', 'release')} {row['path']}: {row.get('error')}")

    accepted_cs0 = [row for row in accepted if row.get("doc_id") == "CS-0" and row["status"] == "VALID"]
    if len(accepted_cs0) != 1:
        errors.append(
            "candidate-set validation requires exactly one valid accepted CS-0 schema authority"
        )
        allowed_edge_types: set[str] = set()
    else:
        try:
            allowed_edge_types = _schema_dependency_edge_types(Path(accepted_cs0[0]["path"]))
        except ReleaseError as error:
            errors.append(str(error))
            allowed_edge_types = set()

    candidates_by_doc: dict[str, dict[str, Any]] = {}
    candidates_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    candidate_aliases: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in candidates:
        if row["status"] != "VALID":
            continue
        doc_id = str(row["doc_id"])
        version = str(row["version"])
        identity = (doc_id, version)
        prior_identity = candidates_by_identity.get(identity)
        if prior_identity:
            if prior_identity["sha256"] != row["sha256"]:
                errors.append(
                    f"candidate identity {doc_id}@{version} has different SHA-256 values "
                    f"({prior_identity['sha256']} and {row['sha256']})"
                )
            else:
                candidate_aliases[identity].append(row["path"])
            continue
        prior_doc = candidates_by_doc.get(doc_id)
        if prior_doc and prior_doc["version"] != version:
            errors.append(
                f"candidate set contains multiple versions for {doc_id}: "
                f"{prior_doc['version']} and {version}"
            )
        candidates_by_doc[doc_id] = row
        candidates_by_identity[identity] = row

    accepted_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        if row["status"] == "VALID":
            accepted_by_doc[str(row["doc_id"])].append(row)

    for identity, candidate in candidates_by_identity.items():
        for accepted_row in accepted_by_doc.get(identity[0], []):
            if accepted_row["version"] == identity[1] and accepted_row["sha256"] != candidate["sha256"]:
                errors.append(
                    f"candidate would change immutable accepted identity {identity[0]}@{identity[1]}"
                )

    edges: list[dict[str, Any]] = []
    for referrer_id, candidate in sorted(candidates_by_doc.items()):
        dependencies = candidate["contract"].get("dependencies", [])
        if dependencies is None:
            dependencies = []
        if not isinstance(dependencies, list):
            errors.append(f"{referrer_id}@{candidate['version']} dependencies must be an array")
            continue
        for index, dependency in enumerate(dependencies):
            label = f"{referrer_id}@{candidate['version']} dependency[{index}]"
            edge: dict[str, Any] = {
                "referrer_doc_id": referrer_id,
                "referrer_version": candidate["version"],
                "dependency_index": index,
                "target_doc_id": None,
                "minimum_version": None,
                "target_version": None,
                "target_sha256": None,
                "edge_type": None,
                "status": "BLOCKED_INVALID_TARGET",
            }
            if not isinstance(dependency, dict):
                errors.append(f"{label} is not an object")
                edges.append(edge)
                continue
            target_id = dependency.get("doc_id")
            minimum = dependency.get("min_version")
            edge_type = dependency.get("edge_type")
            edge.update(
                {
                    "target_doc_id": target_id,
                    "minimum_version": minimum,
                    "edge_type": edge_type,
                }
            )
            if edge_type not in allowed_edge_types:
                edge["status"] = "BLOCKED_INVALID_EDGE_TYPE"
                errors.append(f"{label} has edge_type outside accepted CS-0 enum: {edge_type!r}")
                edges.append(edge)
                continue
            if not isinstance(target_id, str) or not isinstance(minimum, str):
                edge["status"] = "BLOCKED_INVALID_TARGET"
                errors.append(f"{label} must declare a doc_id and min_version")
                edges.append(edge)
                continue
            try:
                minimum_key = semver_key(minimum)
            except ValueError:
                edge["status"] = "BLOCKED_INVALID_MINIMUM"
                errors.append(f"{label} has invalid numeric minimum version {minimum!r}")
                edges.append(edge)
                continue

            target = candidates_by_doc.get(target_id)
            target_status = "RESOLVED_WITHIN_CANDIDATE_SET"
            if target is None:
                accepted_targets = accepted_by_doc.get(target_id, [])
                if not accepted_targets:
                    edge["status"] = "BLOCKED_INVALID_TARGET"
                    errors.append(f"{label} target {target_id} is neither a candidate nor accepted release")
                    edges.append(edge)
                    continue
                if len(accepted_targets) != 1:
                    edge["status"] = "BLOCKED_AUTHORITY"
                    errors.append(f"{label} target {target_id} has multiple accepted versions")
                    edges.append(edge)
                    continue
                target = accepted_targets[0]
                target_status = "RESOLVED_ACCEPTED"

            try:
                target_key = semver_key(str(target["version"]))
            except ValueError:
                edge["status"] = "BLOCKED_INVALID_TARGET"
                errors.append(f"{label} target {target_id} has non-numeric SemVer")
                edges.append(edge)
                continue
            edge["target_version"] = target["version"]
            edge["target_sha256"] = target["sha256"]
            if target_key < minimum_key:
                edge["status"] = "BLOCKED_BELOW_MINIMUM"
                errors.append(
                    f"{label} target {target_id}@{target['version']} is below minimum {minimum}"
                )
            else:
                edge["status"] = target_status

            artifact_pin = dependency.get("artifact_pin_sha256")
            if artifact_pin is not None and artifact_pin != target["sha256"]:
                edge["status"] = "BLOCKED_HASH_PIN"
                errors.append(f"{label} target {target_id} does not match artifact_pin_sha256")
            edges.append(edge)

    status_counts = Counter(edge["status"] for edge in edges)
    return {
        "status": "VALID" if not errors else "INVALID",
        "candidate_count": len(candidates_by_identity),
        "accepted_release_count": sum(row["status"] == "VALID" for row in accepted),
        "candidates": [
            {key: value for key, value in row.items() if key != "contract"}
            for row in candidates
        ],
        "duplicate_same_hash_representations": {
            f"{doc_id}@{version}": paths
            for (doc_id, version), paths in sorted(candidate_aliases.items())
        },
        "edges": edges,
        "edge_status_counts": dict(sorted(status_counts.items())),
        "errors": errors,
    }


def current_release_inputs(root: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    """Load verified active ZIPs as the baseline for candidate dependency checks."""

    root = Path(root).resolve()
    try:
        verify_manifest(root)
        stray = verify_no_stray_contract_zips(root)
        if stray:
            raise ManifestError("; ".join(stray))
        manifest = json.loads((root / "contracts/manifest.json").read_text(encoding="utf-8"))
    except (ManifestError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseError(f"active manifest validation failed: {error}") from error
    rows = manifest.get("contracts")
    if not isinstance(rows, list):
        raise ReleaseError("active manifest contracts must be an array")
    paths: list[Path] = []
    records: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ReleaseError("active manifest contains a malformed contract record")
        path = root / str(row["zip_path"])
        paths.append(path)
        records.append({
            "doc_id": row["doc_id"],
            "version": row["version"],
            "path": str(path),
            "sha256": row["zip_sha256"],
            "status": "VALID",
            "validation_status": "VALID",
            "bundle_validation": {
                "status": "VALID",
                "doc_id": row["doc_id"],
                "version": row["version"],
                "zip_sha256": row["zip_sha256"],
            },
        })
    return paths, records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        accepted_paths, accepted_records = current_release_inputs(args.root)
    except ReleaseError as error:
        print(json.dumps({"status": "INVALID", "active_manifest_error": str(error)}, indent=2))
        return 1
    result = validate_release_set(
        args.candidate,
        accepted_paths,
        accepted_release_records=accepted_records,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
