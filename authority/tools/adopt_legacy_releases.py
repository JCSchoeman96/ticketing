#!/usr/bin/env python3
"""Adopt exact tracked legacy bundle bytes into the accepted-release registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

if __package__:
    from .reconcile_contracts import audit_repository
    from .validate_accepted_releases import validate_accepted_release_registry
else:
    from reconcile_contracts import audit_repository
    from validate_accepted_releases import validate_accepted_release_registry


class LegacyAdoptionError(ValueError):
    """Raised when a legacy bundle does not meet adoption requirements."""


def _tracked_paths(root: Path) -> set[str]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    return {item for item in output.decode("utf-8").split("\0") if item}


def _source_commit(root: Path, relative_path: str) -> str:
    try:
        commit = subprocess.check_output(
            ["git", "log", "--follow", "-1", "--format=%H", "--", relative_path],
            cwd=root,
            stderr=subprocess.PIPE,
        ).decode("ascii").strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise LegacyAdoptionError(f"cannot determine tracked source commit for {relative_path}: {error}") from error
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise LegacyAdoptionError(f"no Git source commit found for {relative_path}")
    return commit


def _git_blob_sha256(root: Path, commit: str, relative_path: str) -> str:
    try:
        prefix = subprocess.check_output(
            ["git", "rev-parse", "--show-prefix"], cwd=root, stderr=subprocess.PIPE
        ).decode("utf-8").strip().rstrip("/")
        git_path = f"{prefix}/{relative_path}" if prefix else relative_path
        payload = subprocess.check_output(
            ["git", "show", f"{commit}:{git_path}"], cwd=root, stderr=subprocess.PIPE
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise LegacyAdoptionError(
            f"cannot read tracked release bytes at {commit}:{relative_path}: {error}"
        ) from error
    return hashlib.sha256(payload).hexdigest()


def build_legacy_adoption_record(
    root: Path,
    candidate: dict[str, Any],
    *,
    selection_basis: list[str],
    tracked_at_commit: str,
    accepted_on: str,
) -> dict[str, Any]:
    """Build provenance for an existing selected release without rebuilding it."""

    root = Path(root).resolve()
    if candidate.get("resolution_outcome") != "selected":
        raise LegacyAdoptionError("candidate is not the selected proposal")
    if candidate.get("audit_status") not in {"VALID", "VALID_WITH_WARNING"}:
        raise LegacyAdoptionError("candidate is not individually valid")
    validation = candidate.get("validation")
    if not isinstance(validation, dict) or validation.get("status") not in {
        "VALID",
        "VALID_WITH_WARNING",
    } or validation.get("errors"):
        raise LegacyAdoptionError("candidate is not individually valid")
    if not isinstance(selection_basis, list) or not selection_basis or not all(
        isinstance(item, str) and item.strip() for item in selection_basis
    ):
        raise LegacyAdoptionError("selection_basis must contain at least one non-empty reason")
    if not re.fullmatch(r"[a-f0-9]{40}", tracked_at_commit):
        raise LegacyAdoptionError("tracked_at_commit must be a full Git commit SHA")
    try:
        date.fromisoformat(accepted_on)
    except ValueError as error:
        raise LegacyAdoptionError("accepted_on must be an ISO date") from error

    source_path = candidate.get("source_path")
    if not isinstance(source_path, str):
        raise LegacyAdoptionError("selected candidate has no source_path")
    relative = PurePosixPath(source_path)
    if (
        relative.is_absolute()
        or not relative.parts
        or "\\" in source_path
        or any(part in {".", ".."} for part in relative.parts)
    ):
        raise LegacyAdoptionError("selected candidate source_path must be repository-relative")
    normalized_path = relative.as_posix()
    if candidate.get("git_tracked") is not True or normalized_path not in _tracked_paths(root):
        raise LegacyAdoptionError("legacy release is not Git-tracked")
    artifact_path = root / normalized_path
    if artifact_path.is_symlink() or not artifact_path.resolve().is_relative_to(root):
        raise LegacyAdoptionError("legacy release path is a symlink or resolves outside the repository")
    try:
        payload = artifact_path.read_bytes()
    except OSError as error:
        raise LegacyAdoptionError(f"cannot read selected legacy release: {error}") from error
    digest = hashlib.sha256(payload).hexdigest()
    if digest != candidate.get("zip_sha256"):
        raise LegacyAdoptionError(
            f"legacy release hash differs from audited selection: {candidate.get('zip_sha256')} != {digest}"
        )
    committed_digest = _git_blob_sha256(root, tracked_at_commit, normalized_path)
    if committed_digest != digest:
        raise LegacyAdoptionError(
            "legacy release bytes at tracked_at_commit differ from the audited selected bytes"
        )

    return {
        "doc_id": candidate["doc_id"],
        "version": candidate["version"],
        "path": normalized_path,
        "sha256": digest,
        "size_bytes": len(payload),
        "status": "ACCEPTED_RELEASE",
        "acceptance_origin": "legacy_adoption",
        "acceptance_decision": "VALIDATED_SELECTED_TRACKED_LEGACY_RELEASE",
        "accepted_on": accepted_on,
        "canonical_pin_status": "not_pinned",
        "validation_status": candidate["audit_status"],
        "bundle_validation_status": validation["status"],
        "validation_warnings": validation.get("warnings", []),
        "selection_basis": selection_basis,
        "source_commit": _source_commit(root, normalized_path),
        "tracked_at_commit": tracked_at_commit,
        "tracked_provenance": "Exact ZIP bytes were Git-tracked and adopted without rebuilding.",
    }


def _classify_selected_releases(
    root: Path,
    audit: dict[str, Any],
    accepted_registry: dict[str, Any],
    exclusions: dict[str, str],
    tracked_at_commit: str,
    accepted_on: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    accepted_by_identity = {
        (release["doc_id"], release["version"]): release
        for release in accepted_registry.get("releases", [])
    }
    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    already_accepted: list[dict[str, str]] = []

    for doc_id, record in sorted(audit.get("contracts", {}).items()):
        candidate = record.get("selected_candidate")
        if candidate is None:
            candidates = record.get("candidates", [])
            if candidates:
                reasons = sorted(
                    {
                        error
                        for item in candidates
                        for error in (item.get("validation") or {}).get("errors", [])
                    }
                )
                reason = "; ".join(reasons) or "; ".join(record.get("ambiguities", [])) or record.get("status", "no selected candidate")
                excluded.append({"doc_id": doc_id, "reason": reason})
            continue

        identity = (doc_id, str(candidate.get("version")))
        if identity in accepted_by_identity:
            accepted = accepted_by_identity[identity]
            if accepted.get("sha256") != candidate.get("zip_sha256"):
                excluded.append({
                    "doc_id": doc_id,
                    "reason": "selected identity conflicts with the accepted SHA-256",
                })
            else:
                already_accepted.append({"doc_id": doc_id, "version": identity[1]})
            continue
        if doc_id in exclusions:
            excluded.append({"doc_id": doc_id, "reason": exclusions[doc_id]})
            continue
        try:
            adoption = build_legacy_adoption_record(
                root,
                candidate,
                selection_basis=record.get("selection_basis", []),
                tracked_at_commit=tracked_at_commit,
                accepted_on=accepted_on,
            )
        except LegacyAdoptionError as error:
            excluded.append({"doc_id": doc_id, "reason": str(error)})
            continue
        eligible.append(adoption)

    return eligible, excluded, already_accepted


def _atomic_write_registry(registry_path: Path, payload: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=registry_path.parent, prefix=".acceptance-", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, registry_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def adopt_eligible_releases(
    root: Path,
    *,
    exclusions: dict[str, str],
    accepted_on: str,
    apply: bool,
    registry_path: Path = Path("release-artifacts/accepted/acceptance.json"),
) -> dict[str, Any]:
    """Report eligible selected releases and optionally adopt them in one write."""

    root = Path(root).resolve()
    registry_file = root / registry_path
    old_payload = registry_file.read_bytes()
    registry = json.loads(old_payload.decode("utf-8"))
    current_verification = validate_accepted_release_registry(root, registry_path)
    if current_verification["status"] != "VALID":
        return {
            "status": "INVALID",
            "errors": ["current accepted registry must validate before adoption", *current_verification["errors"]],
            "eligible": [],
            "excluded": [],
            "already_accepted": [],
        }

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.PIPE
    ).decode("ascii").strip()
    audit = audit_repository(root, scan_mode="canonical")
    eligible, excluded, already_accepted = _classify_selected_releases(
        root, audit, current_verification, exclusions, head, accepted_on
    )
    result: dict[str, Any] = {
        "status": "READY" if eligible else "NO_ELIGIBLE_RELEASES",
        "accepted_before": current_verification["release_count"],
        "eligible": eligible,
        "excluded": excluded,
        "already_accepted": already_accepted,
        "audit_commit": head,
        "applied": False,
    }
    if not apply:
        return result
    if not eligible:
        return result

    for row in registry["releases"]:
        if row.get("acceptance_origin") is None:
            decision = row.get("acceptance_decision")
            if decision == "OWNER_ACCEPTED_EXACT_SHA256":
                row["acceptance_origin"] = "owner_accepted_candidate"
            else:
                row["acceptance_origin"] = "deterministic_build"
        row.setdefault("canonical_pin_status", "not_pinned")
    registry["acceptance_basis"] = (
        "Owner-approved exact candidate hashes and validated Git-tracked legacy releases; "
        "per-release acceptance_origin and selection_basis record provenance."
    )
    registry["releases"].extend(eligible)
    registry["releases"].sort(key=lambda row: (row["doc_id"], tuple(int(x) for x in row["version"].split("."))))
    encoded = (json.dumps(registry, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_write_registry(registry_file, encoded)
    verification = validate_accepted_release_registry(root, registry_path)
    if verification["status"] != "VALID":
        _atomic_write_registry(registry_file, old_payload)
        return {
            **result,
            "status": "INVALID",
            "applied": False,
            "errors": verification["errors"],
            "accepted_after": current_verification["release_count"],
        }
    result["applied"] = True
    result["accepted_after"] = verification["release_count"]
    result["verification"] = verification
    return result


def _parse_exclusion(value: str) -> tuple[str, str]:
    doc_id, separator, reason = value.partition("=")
    if not separator or not doc_id or not reason.strip():
        raise argparse.ArgumentTypeError("exclusion must be DOC-ID=reason")
    return doc_id, reason.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--registry", type=Path, default=Path("release-artifacts/accepted/acceptance.json"))
    parser.add_argument("--accepted-on", required=True)
    parser.add_argument("--exclude", action="append", type=_parse_exclusion, default=[])
    parser.add_argument("--apply", action="store_true", help="write all eligible records atomically")
    args = parser.parse_args(argv)
    exclusions: dict[str, str] = {}
    for doc_id, reason in args.exclude:
        if doc_id in exclusions:
            parser.error(f"duplicate exclusion for {doc_id}")
        exclusions[doc_id] = reason
    result = adopt_eligible_releases(
        args.root,
        exclusions=exclusions,
        accepted_on=args.accepted_on,
        apply=args.apply,
        registry_path=args.registry,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"READY", "NO_ELIGIBLE_RELEASES"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
