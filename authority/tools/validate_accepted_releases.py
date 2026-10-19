#!/usr/bin/env python3
"""Verify accepted release records against tracked, immutable ZIP artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

if __package__:
    from .build_contract_release import ReleaseError, validate_bundle
    from .reconcile_contracts import audit_repository
else:
    from build_contract_release import ReleaseError, validate_bundle
    from reconcile_contracts import audit_repository


DEFAULT_REGISTRY = Path("release-artifacts/accepted/acceptance.json")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ACCEPTANCE_ORIGINS = {
    "owner_accepted_candidate",
    "deterministic_build",
    "legacy_adoption",
}
CANON_PIN_STATUSES = {"not_pinned", "pinned"}


def _tracked_paths(root: Path) -> set[str]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=root, stderr=subprocess.PIPE
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"accepted release verification requires a Git worktree: {error}") from error
    return {path for path in output.decode("utf-8").split("\0") if path}


def _git_blob_sha256(root: Path, commit: str, path: str) -> str:
    try:
        prefix = subprocess.check_output(
            ["git", "rev-parse", "--show-prefix"], cwd=root, stderr=subprocess.PIPE
        ).decode("utf-8").strip().rstrip("/")
        git_path = f"{prefix}/{path}" if prefix else path
        payload = subprocess.check_output(
            ["git", "show", f"{commit}:{git_path}"], cwd=root, stderr=subprocess.PIPE
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"cannot read {commit}:{path}: {error}") from error
    return hashlib.sha256(payload).hexdigest()


def _safe_relative_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or "\\" in value
        or ":" in path.parts[0]
        or any(part in {".", ".."} for part in path.parts)
    ):
        return None
    return path.as_posix()


def validate_accepted_release_registry(
    root: Path,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    """Fail closed when an acceptance record is missing, untracked, or altered."""

    root = Path(root).resolve()
    registry_input = Path(registry_path)
    if registry_input.is_absolute():
        try:
            registry_input = registry_input.resolve().relative_to(root)
        except ValueError:
            registry_input = Path("../outside-registry")
    registry_relative = _safe_relative_path(registry_input.as_posix())
    errors: list[str] = []
    releases: list[dict[str, Any]] = []
    if registry_relative is None:
        return {
            "status": "INVALID",
            "registry_path": str(registry_path),
            "release_count": 0,
            "releases": [],
            "errors": ["accepted registry path must be a safe repository-relative path"],
        }

    try:
        tracked = _tracked_paths(root)
    except ValueError as error:
        return {
            "status": "INVALID",
            "registry_path": registry_relative,
            "release_count": 0,
            "releases": [],
            "errors": [str(error)],
        }

    if registry_relative not in tracked:
        errors.append(f"accepted registry is not Git-tracked: {registry_relative}")
    registry_file = root / registry_relative
    if registry_file.is_symlink():
        return {
            "status": "INVALID",
            "registry_path": registry_relative,
            "release_count": 0,
            "releases": [],
            "errors": [*errors, "accepted registry must not be a symbolic link"],
        }
    if not registry_file.resolve().is_relative_to(root):
        return {
            "status": "INVALID",
            "registry_path": registry_relative,
            "release_count": 0,
            "releases": [],
            "errors": [*errors, "accepted registry resolves outside the repository"],
        }
    try:
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return {
            "status": "INVALID",
            "registry_path": registry_relative,
            "release_count": 0,
            "releases": [],
            "errors": [*errors, f"cannot read accepted registry: {error}"],
        }

    if (
        not isinstance(registry, dict)
        or type(registry.get("format_version")) is not int
        or registry.get("format_version") != 1
    ):
        errors.append("accepted registry must be an object with format_version 1")
        rows: list[Any] = []
    else:
        rows = registry.get("releases") if isinstance(registry.get("releases"), list) else []
        if not isinstance(registry.get("releases"), list):
            errors.append("accepted registry releases must be an array")
        elif not rows:
            errors.append("accepted registry must contain at least one accepted release")
        if registry.get("acceptance_status") != "ACCEPTED_RELEASE":
            errors.append("accepted registry acceptance_status must be ACCEPTED_RELEASE")
        if registry.get("canonical_pin_status") not in CANON_PIN_STATUSES:
            errors.append("accepted registry canonical_pin_status must be not_pinned or pinned")

    seen_identities: set[tuple[str, str]] = set()
    seen_hashes: dict[tuple[str, str], str] = {}
    seen_paths: set[str] = set()
    legacy_rows = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("acceptance_origin") == "legacy_adoption"
    ]
    legacy_candidates: dict[str, dict[str, Any]] = {}
    if legacy_rows:
        try:
            audit = audit_repository(root, scan_mode="canonical")
            for contract_record in audit.get("contracts", {}).values():
                for candidate in contract_record.get("candidates", []):
                    legacy_candidates[candidate.get("source_path")] = candidate
        except (OSError, ValueError, RuntimeError) as error:
            errors.append(f"cannot audit legacy accepted bundles: {error}")

    for index, row in enumerate(rows):
        label = f"releases[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        doc_id = row.get("doc_id")
        version = row.get("version")
        path = _safe_relative_path(row.get("path"))
        digest = row.get("sha256")
        identity = (str(doc_id), str(version))
        if not isinstance(doc_id, str) or not re.fullmatch(r"[A-Z][A-Z0-9]*-\d+", doc_id):
            errors.append(f"{label} has an invalid doc_id")
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            errors.append(f"{label} has an invalid numeric SemVer version")
        if identity in seen_identities:
            errors.append(f"duplicate accepted identity: {identity[0]}@{identity[1]}")
        seen_identities.add(identity)
        if path is None:
            errors.append(f"{label} has an unsafe or missing repository-relative path")
            continue
        if path in seen_paths:
            errors.append(f"duplicate accepted artifact path: {path}")
        seen_paths.add(path)
        if row.get("status") != "ACCEPTED_RELEASE":
            errors.append(f"{label} status is not ACCEPTED_RELEASE")
        acceptance_origin = row.get("acceptance_origin")
        if acceptance_origin is not None and acceptance_origin not in ACCEPTANCE_ORIGINS:
            errors.append(f"{label} has an unsupported acceptance_origin")
        if acceptance_origin is None and not (
            row.get("builder") and row.get("acceptance_decision")
        ):
            errors.append(f"{label} has no acceptance_origin or existing release provenance")
        pin_status = row.get("canonical_pin_status")
        if pin_status is not None and pin_status not in CANON_PIN_STATUSES:
            errors.append(f"{label} has an unsupported canonical_pin_status")
        if row.get("acceptance_origin") == "legacy_adoption":
            if pin_status not in CANON_PIN_STATUSES:
                errors.append(f"{label} legacy adoption has no canonical_pin_status")
            if row.get("validation_status") not in {"VALID", "VALID_WITH_WARNING"}:
                errors.append(f"{label} legacy adoption has no passing validation_status")
            if not isinstance(row.get("selection_basis"), list) or not row.get("selection_basis"):
                errors.append(f"{label} legacy adoption has no selection_basis")
            for provenance_key in ("source_commit", "tracked_at_commit"):
                if not isinstance(row.get(provenance_key), str) or not re.fullmatch(
                    r"[a-f0-9]{40}", row[provenance_key]
                ):
                    errors.append(f"{label} legacy adoption has an invalid {provenance_key}")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{label} has an invalid SHA-256 value")
        prior_hash = seen_hashes.get(identity)
        if prior_hash is not None and isinstance(digest, str) and prior_hash != digest:
            errors.append(
                f"duplicate accepted identity {identity[0]}@{identity[1]} has different SHA-256 values"
            )
        elif isinstance(digest, str):
            seen_hashes[identity] = digest
        if path not in tracked:
            errors.append(f"accepted artifact is not Git-tracked: {path}")
        artifact_path = root / path
        if not artifact_path.resolve().is_relative_to(root):
            errors.append(f"accepted artifact resolves outside the repository: {path}")
            continue
        if artifact_path.is_symlink():
            errors.append(f"accepted artifact must not be a symbolic link: {path}")
            continue
        try:
            payload = artifact_path.read_bytes()
        except OSError as error:
            errors.append(f"accepted artifact is missing or unreadable: {path}: {error}")
            continue
        actual_digest = hashlib.sha256(payload).hexdigest()
        if isinstance(digest, str) and actual_digest != digest:
            errors.append(f"SHA-256 mismatch for {path}: recorded {digest}, actual {actual_digest}")
        if row.get("acceptance_origin") == "legacy_adoption":
            tracked_at_commit = row.get("tracked_at_commit")
            if isinstance(tracked_at_commit, str) and re.fullmatch(r"[a-f0-9]{40}", tracked_at_commit):
                try:
                    committed_digest = _git_blob_sha256(root, tracked_at_commit, path)
                except ValueError as error:
                    errors.append(f"{label} legacy adoption tracked_at_commit cannot verify {path}: {error}")
                else:
                    if committed_digest != actual_digest:
                        errors.append(
                            f"{label} legacy adoption tracked_at_commit bytes differ for {path}: "
                            f"recorded commit has {committed_digest}, accepted artifact has {actual_digest}"
                        )
        expected_size = row.get("size_bytes")
        if type(expected_size) is not int or expected_size != len(payload):
            errors.append(f"size mismatch for {path}: recorded {expected_size}, actual {len(payload)}")
        if row.get("acceptance_origin") == "legacy_adoption":
            candidate = legacy_candidates.get(path)
            validation = candidate.get("validation") if isinstance(candidate, dict) else None
            if (
                not isinstance(candidate, dict)
                or candidate.get("doc_id") != doc_id
                or candidate.get("version") != version
                or candidate.get("zip_sha256") != actual_digest
                or not isinstance(validation, dict)
                or validation.get("status") not in {"VALID", "VALID_WITH_WARNING"}
                or validation.get("errors")
            ):
                errors.append(
                    f"accepted legacy artifact failed canonical bundle validation for {path}"
                )
                bundle = None
            else:
                bundle = {
                    "status": validation["status"],
                    "doc_id": candidate["doc_id"],
                    "version": candidate["version"],
                    "suite_schema": candidate.get("current_suite_schema"),
                    "zip_sha256": candidate["zip_sha256"],
                    "artifacts": candidate.get("members", []),
                    "warnings": validation.get("warnings", []),
                }
        else:
            try:
                bundle = validate_bundle(artifact_path)
            except ReleaseError as error:
                errors.append(f"accepted artifact bundle validation failed for {path}: {error}")
                bundle = None
        if bundle is not None:
            if bundle["doc_id"] != doc_id or bundle["version"] != version:
                errors.append(
                    f"accepted identity mismatch for {path}: registry says "
                    f"{doc_id}@{version}, bundle says {bundle['doc_id']}@{bundle['version']}"
                )
            if bundle["zip_sha256"] != actual_digest:
                errors.append(f"bundle validator hash disagrees with file hash for {path}")
        releases.append(
            {
                "doc_id": doc_id,
                "version": version,
                "path": path,
                "sha256": actual_digest,
                "size_bytes": len(payload),
                "validation_status": "VALID" if bundle is not None else "INVALID",
                "bundle_validation": bundle,
            }
        )

    return {
        "status": "VALID" if not errors else "INVALID",
        "registry_path": registry_relative,
        "release_count": len(releases),
        "releases": releases,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)
    try:
        result = validate_accepted_release_registry(args.root, args.registry)
    except ValueError as error:
        print(json.dumps({"status": "INVALID", "errors": [str(error)]}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
