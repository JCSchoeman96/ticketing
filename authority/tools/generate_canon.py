#!/usr/bin/env python3
"""Freeze, build, and verify the generated CANON-1 suite pinset."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


if __package__:
    from .build_contract_release import ReleaseError, build_contract_release, validate_bundle
    from .contract_manifest import ActiveIdentityError, ManifestError, _contract_from_zip, verify_manifest
    from .validate_accepted_releases import validate_accepted_release_registry
else:
    from build_contract_release import ReleaseError, build_contract_release, validate_bundle
    from contract_manifest import ActiveIdentityError, ManifestError, _contract_from_zip, verify_manifest
    from validate_accepted_releases import validate_accepted_release_registry


GENERATOR_VERSION = "2.0.0"
DEFAULT_REGISTRY = Path("release-artifacts/accepted/acceptance.json")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
GIT_COMMIT_PATTERN = re.compile(r"^[a-f0-9]{40}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class CanonGenerationError(ValueError):
    """Raised when the resolved suite cannot safely produce a CANON pinset."""


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _read_json(path: Path, description: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CanonGenerationError(f"cannot read {description} at {path}: {error}") from error
    if not isinstance(value, dict):
        raise CanonGenerationError(f"{description} must be a JSON object: {path}")
    return value, payload


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise CanonGenerationError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _safe_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise CanonGenerationError(f"{label} must be a safe repository-relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or ":" in path.parts[0]
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise CanonGenerationError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _accepted_by_identity(registry: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = registry.get("releases")
    if not isinstance(rows, list):
        raise CanonGenerationError("accepted registry releases must be an array")
    accepted: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CanonGenerationError(f"accepted registry releases[{index}] must be an object")
        identity = (str(row.get("doc_id")), str(row.get("version")))
        if identity in accepted:
            raise CanonGenerationError(f"duplicate accepted release identity: {identity[0]}@{identity[1]}")
        accepted[identity] = row
    return accepted


def manifest_record_by_identity(
    manifest: dict[str, Any],
    doc_id: str,
    version: str,
    membership: str,
) -> dict[str, Any]:
    """Resolve a current release by identity and hash inventory, never by its old path."""

    rows = manifest.get("contracts")
    if not isinstance(rows, list):
        raise CanonGenerationError("active contract manifest has no contracts array")
    matches = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("doc_id") == doc_id
        and row.get("version") == version
        and row.get("membership") == membership
    ]
    if len(matches) != 1:
        raise CanonGenerationError(
            f"{doc_id}@{version} has no active manifest record with membership {membership}"
        )
    return matches[0]


def freeze_canon_successor(
    canon_contract: dict[str, Any],
    manifest: dict[str, Any],
    candidates: list[dict[str, Any]],
    dependency_closure: dict[str, Any],
    *,
    generated_version: str,
    base_canon_sha256: str,
    manifest_sha256: str,
    generator_commit: str,
) -> dict[str, Any]:
    """Resolve an explicit CANON successor from current pins and validated overrides."""

    if not VERSION_RE.fullmatch(generated_version):
        raise CanonGenerationError("generated CANON version must be semantic X.Y.Z")
    base_canon_sha256 = _require_sha256(base_canon_sha256, "base CANON ZIP hash")
    manifest_sha256 = _require_sha256(manifest_sha256, "active manifest hash")
    if not GIT_COMMIT_PATTERN.fullmatch(generator_commit):
        raise CanonGenerationError("generator commit must be a full 40-character Git SHA")
    pins = canon_contract.get("canonical_bundles")
    exclusions = canon_contract.get("canonical_exclusions")
    rows = manifest.get("contracts")
    if not isinstance(pins, list) or not pins or not isinstance(exclusions, list):
        raise CanonGenerationError("base CANON must contain current members and exclusions")
    if not isinstance(rows, list):
        raise CanonGenerationError("active manifest has no contracts array")
    if not isinstance(candidates, list):
        raise CanonGenerationError("candidate releases must be an array")
    canon_rows = [
        row for row in rows
        if isinstance(row, dict) and row.get("doc_id") == "CANON-1" and row.get("membership") == "CANON_INDEX"
    ]
    if (
        len(canon_rows) != 1
        or canon_rows[0].get("version") != canon_contract.get("version")
        or canon_rows[0].get("zip_sha256") != base_canon_sha256
    ):
        raise CanonGenerationError("base CANON identity or hash does not match active manifest")
    base_version = canon_contract.get("version")
    if not isinstance(base_version, str) or not VERSION_RE.fullmatch(base_version):
        raise CanonGenerationError("base CANON version must be semantic X.Y.Z")
    if tuple(map(int, generated_version.split("."))) <= tuple(map(int, base_version.split("."))):
        raise CanonGenerationError("generated CANON version must be greater than base CANON version")
    if type(dependency_closure.get("edge_count")) is not int or any(
        type(dependency_closure.get(key)) is not int
        for key in ("unresolved_required_edges", "below_minimum_edges", "invalid_dependency_records")
    ):
        raise CanonGenerationError("dependency closure summary is malformed")
    if any(dependency_closure[key] != 0 for key in (
        "unresolved_required_edges", "below_minimum_edges", "invalid_dependency_records"
    )):
        raise CanonGenerationError("candidate dependency closure is incomplete")
    closure_sha = _require_sha256(dependency_closure.get("input_sha256"), "dependency closure input hash")

    members_by_id: dict[str, dict[str, Any]] = {}
    for pin in pins:
        if not isinstance(pin, dict) or not isinstance(pin.get("doc_id"), str):
            raise CanonGenerationError("base CANON member pin is malformed")
        doc_id = pin["doc_id"]
        if doc_id in members_by_id:
            raise CanonGenerationError(f"duplicate base CANON member: {doc_id}")
        members_by_id[doc_id] = pin
    exclusions_by_id: dict[str, dict[str, Any]] = {}
    for exclusion in exclusions:
        if not isinstance(exclusion, dict) or not isinstance(exclusion.get("doc_id"), str):
            raise CanonGenerationError("base CANON exclusion is malformed")
        doc_id = exclusion["doc_id"]
        if doc_id in exclusions_by_id or doc_id in members_by_id:
            raise CanonGenerationError(f"duplicate or overlapping CANON classification: {doc_id}")
        exclusions_by_id[doc_id] = exclusion

    candidate_by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("doc_id"), str):
            raise CanonGenerationError("candidate release is malformed")
        doc_id = candidate["doc_id"]
        if doc_id in candidate_by_id:
            raise CanonGenerationError(f"duplicate candidate doc_id: {doc_id}")
        if doc_id == "CANON-1":
            raise CanonGenerationError("candidate set cannot pin CANON-1")
        if doc_id not in members_by_id:
            raise CanonGenerationError(f"{doc_id} is not an existing CANON member")
        validation = candidate.get("validation")
        if not isinstance(validation, dict) or validation.get("status") != "VALID":
            raise CanonGenerationError(f"candidate is not valid: {doc_id}")
        contract = candidate.get("contract")
        version = candidate.get("version")
        if (
            not isinstance(version, str)
            or not VERSION_RE.fullmatch(version)
            or not isinstance(contract, dict)
            or contract.get("doc_id") != doc_id
            or contract.get("version") != version
        ):
            raise CanonGenerationError(f"candidate identity does not match contract metadata: {doc_id}")
        digest = _require_sha256(candidate.get("sha256"), f"{doc_id} candidate ZIP hash")
        actual_digest = _require_sha256(candidate.get("actual_sha256"), f"{doc_id} candidate byte hash")
        if digest != actual_digest:
            raise CanonGenerationError(f"candidate ZIP hash mismatch for {doc_id}")
        normalized_candidate = dict(candidate)
        normalized_candidate["zip_path"] = _safe_relative_path(
            candidate.get("zip_path"), f"{doc_id} candidate active path"
        )
        candidate_by_id[doc_id] = normalized_candidate

    manifest_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("doc_id"), str):
            raise CanonGenerationError("active manifest contains a malformed release")
        doc_id = row["doc_id"]
        if doc_id in manifest_by_id:
            raise CanonGenerationError(f"duplicate active manifest doc_id: {doc_id}")
        manifest_by_id[doc_id] = row

    resolved_members: list[dict[str, Any]] = []
    for doc_id in sorted(members_by_id):
        old_pin = members_by_id[doc_id]
        current = manifest_by_id.get(doc_id)
        if current is None or current.get("membership") != "CANON_MEMBER":
            raise CanonGenerationError(f"existing CANON member was removed or reclassified: {doc_id}")
        candidate = candidate_by_id.get(doc_id)
        if candidate is None:
            if (
                current.get("version") != old_pin.get("version")
                or current.get("zip_sha256") != old_pin.get("bundle_sha256")
            ):
                raise CanonGenerationError(f"existing member changed without a candidate override: {doc_id}")
            version, digest, path = old_pin["version"], old_pin["bundle_sha256"], current["zip_path"]
            basis = ["preserved from validated current CANON pin"]
        else:
            version = candidate["version"]
            digest = candidate["sha256"]
            path = candidate["zip_path"]
            try:
                active_version = tuple(int(part) for part in str(current.get("version", "")).split("."))
                candidate_version = tuple(int(part) for part in version.split("."))
            except ValueError as error:
                raise CanonGenerationError(f"candidate version is malformed for {doc_id}") from error
            if len(active_version) != 3 or candidate_version <= active_version:
                raise CanonGenerationError(f"candidate version for {doc_id} must be newer than active")
            basis = [f"explicit validated successor candidate for {doc_id}"]
        resolved_members.append({
            "doc_id": doc_id,
            "version": version,
            "accepted_artifact_path": path,
            "sha256": digest,
            "selection_basis": basis,
        })

    for doc_id, exclusion in exclusions_by_id.items():
        current = manifest_by_id.get(doc_id)
        if exclusion.get("membership_status") == "ACCEPTED_DEPENDENCY_ONLY":
            if current is None or current.get("membership") != "DEPENDENCY_ONLY":
                raise CanonGenerationError(f"dependency-only classification changed for {doc_id}")
            if current.get("version") != exclusion.get("version") or current.get("zip_sha256") != exclusion.get("sha256"):
                raise CanonGenerationError(f"dependency-only release changed without membership authorization: {doc_id}")
            exclusion = dict(exclusion)
            exclusion["accepted_artifact_path"] = current["zip_path"]
            exclusions_by_id[doc_id] = exclusion
        elif exclusion.get("membership_status") == "DEFERRED_NONBLOCKING" and current is not None:
            raise CanonGenerationError(f"deferred contract is active: {doc_id}")

    for doc_id in manifest_by_id:
        if doc_id != "CANON-1" and doc_id not in members_by_id and doc_id not in exclusions_by_id:
            raise CanonGenerationError(f"implicit CANON membership change: unclassified active release {doc_id}")
    if "CANON-1" not in manifest_by_id or manifest_by_id["CANON-1"].get("membership") != "CANON_INDEX":
        raise CanonGenerationError("active manifest must contain exactly one CANON_INDEX")
    if len([row for row in rows if isinstance(row, dict) and row.get("membership") == "CANON_INDEX"]) != 1:
        raise CanonGenerationError("active manifest must contain exactly one CANON_INDEX")

    candidate_identities = [
        {"doc_id": doc_id, "version": row["version"], "sha256": row["sha256"]}
        for doc_id, row in sorted(candidate_by_id.items())
    ]
    return {
        "generated_contract": {"doc_id": "CANON-1", "version": generated_version},
        "members": resolved_members,
        "exclusions": [exclusions_by_id[key] for key in sorted(exclusions_by_id)],
        "not_current_versions": canon_contract.get("not_current_versions", []),
        "dependency_closure": {
            key: dependency_closure[key]
            for key in ("edge_count", "unresolved_required_edges", "below_minimum_edges", "invalid_dependency_records")
        },
        "generation_inputs": {
            "generator_version": GENERATOR_VERSION,
            "generator_commit": generator_commit,
            "base_canon_version": canon_contract.get("version"),
            "base_canon_zip_sha256": base_canon_sha256,
            "active_manifest_sha256": manifest_sha256,
            "dependency_closure_sha256": closure_sha,
            "candidate_releases": candidate_identities,
        },
    }


def canon_selection_path(root: Path, manifest: dict[str, Any]) -> Path:
    """Find the reproducibility input for the CANON version recorded as active."""

    canon_rows = [
        row for row in manifest.get("contracts", [])
        if isinstance(row, dict) and row.get("membership") == "CANON_INDEX"
    ]
    if len(canon_rows) != 1:
        raise CanonGenerationError("active manifest must contain exactly one CANON_INDEX")
    row = canon_rows[0]
    return Path("release-src/current") / str(row["doc_id"]) / str(row["version"]) / "resolved-selection.json"


def _candidate_by_identity(
    record: dict[str, Any], doc_id: str, version: str, digest: str
) -> dict[str, Any]:
    candidates = record.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
    matches = [
        item
        for item in candidates
        if isinstance(item, dict)
        and item.get("doc_id") == doc_id
        and item.get("version") == version
        and item.get("zip_sha256") == digest
        and isinstance(item.get("validation"), dict)
        and item["validation"].get("status") in {"VALID", "VALID_WITH_WARNING"}
    ]
    selected = record.get("selected_candidate")
    if (
        isinstance(selected, dict)
        and selected.get("doc_id") == doc_id
        and selected.get("version") == version
        and selected.get("zip_sha256") == digest
        and isinstance(selected.get("validation"), dict)
        and selected["validation"].get("status") in {"VALID", "VALID_WITH_WARNING"}
    ):
        matches.append(selected)
    unique = {item.get("source_path"): item for item in matches}
    if len(unique) != 1:
        raise CanonGenerationError(
            f"selection policy cannot identify one validated bundle for {doc_id}@{version} with the approved hash"
        )
    return next(iter(unique.values()))


def _require_accepted_match(
    accepted: dict[tuple[str, str], dict[str, Any]],
    doc_id: str,
    version: str,
    digest: str,
    path: str | None = None,
) -> dict[str, Any]:
    row = accepted.get((doc_id, version))
    if row is None or row.get("status") != "ACCEPTED_RELEASE":
        raise CanonGenerationError(f"{doc_id}@{version} has no ACCEPTED_RELEASE record")
    if row.get("sha256") != digest:
        raise CanonGenerationError(f"{doc_id}@{version} accepted hash does not match selection")
    row_path = _safe_relative_path(row.get("path"), f"{doc_id}@{version} accepted path")
    if path is not None and row_path != path:
        raise CanonGenerationError(f"{doc_id}@{version} accepted path does not match selection")
    return row


def validate_selection_pin_status(
    selection: dict[str, Any], accepted: dict[tuple[str, str], dict[str, Any]]
) -> None:
    """Require the acceptance registry to agree with frozen CANON membership."""

    members = selection.get("members")
    exclusions = selection.get("exclusions")
    if not isinstance(members, list) or not isinstance(exclusions, list):
        raise CanonGenerationError("frozen selection members and exclusions must be arrays")
    for member in members:
        if not isinstance(member, dict):
            raise CanonGenerationError("frozen selection member is malformed")
        doc_id, version = str(member.get("doc_id")), str(member.get("version"))
        row = _require_accepted_match(
            accepted,
            doc_id,
            version,
            _require_sha256(member.get("sha256"), f"{doc_id} member hash"),
            _safe_relative_path(member.get("accepted_artifact_path"), f"{doc_id} accepted path"),
        )
        if row.get("canonical_pin_status") != "pinned":
            raise CanonGenerationError(f"CANON member {doc_id}@{version} is not marked pinned in the accepted registry")
    for exclusion in exclusions:
        if not isinstance(exclusion, dict):
            raise CanonGenerationError("frozen selection exclusion is malformed")
        if "version" not in exclusion and "sha256" not in exclusion:
            continue
        doc_id, version = str(exclusion.get("doc_id")), str(exclusion.get("version"))
        row = _require_accepted_match(
            accepted,
            doc_id,
            version,
            _require_sha256(exclusion.get("sha256"), f"{doc_id} exclusion hash"),
            _safe_relative_path(exclusion.get("accepted_artifact_path"), f"{doc_id} exclusion path"),
        )
        if row.get("canonical_pin_status") != "not_pinned":
            raise CanonGenerationError(
                f"excluded contract {doc_id}@{version} must be marked not_pinned in the accepted registry"
            )


def freeze_resolved_selection(
    audit_report: dict[str, Any],
    acceptance_registry: dict[str, Any],
    policy: dict[str, Any],
    *,
    accepted_registry_sha256: str,
    policy_sha256: str,
) -> dict[str, Any]:
    """Freeze valid audit selections plus explicit owner decisions."""

    if audit_report.get("summary", {}).get("scan_mode") != "canonical":
        raise CanonGenerationError("resolved selection must come from a canonical tracked-only audit")
    audit_commit = audit_report.get("summary", {}).get("audited_git_commit")
    if not isinstance(audit_commit, str) or not GIT_COMMIT_PATTERN.fullmatch(audit_commit):
        raise CanonGenerationError("canonical audit must record a full Git commit SHA")
    registry_hash = _require_sha256(accepted_registry_sha256, "accepted registry input hash")
    policy_hash = _require_sha256(policy_sha256, "selection policy hash")
    if policy.get("format_version") != 1:
        raise CanonGenerationError("selection policy format_version must be 1")

    summary = audit_report.get("summary")
    if not isinstance(summary, dict):
        raise CanonGenerationError("canonical audit has no summary")
    closure = {
        "edge_count": summary.get("dependency_edge_count"),
        "unresolved_required_edges": summary.get("dependency_target_unresolved_count"),
        "below_minimum_edges": summary.get("dependency_floor_conflict_count"),
        "invalid_dependency_records": summary.get("dependency_edge_invalid_count"),
    }
    for field in ("edge_count", "unresolved_required_edges", "below_minimum_edges", "invalid_dependency_records"):
        if type(closure[field]) is not int:
            raise CanonGenerationError(f"canonical audit dependency count {field} is missing")
    if any(closure[field] != 0 for field in (
        "unresolved_required_edges", "below_minimum_edges", "invalid_dependency_records"
    )):
        raise CanonGenerationError("canonical audit dependency closure is not complete")

    generated_doc_id = policy.get("generated_doc_id")
    generated_version = policy.get("generated_version")
    if not isinstance(generated_doc_id, str) or not generated_doc_id:
        raise CanonGenerationError("selection policy generated_doc_id is required")
    if not isinstance(generated_version, str) or not generated_version:
        raise CanonGenerationError("selection policy generated_version is required")

    contracts = audit_report.get("contracts")
    if not isinstance(contracts, dict):
        raise CanonGenerationError("canonical audit contracts must be an object")
    accepted = _accepted_by_identity(acceptance_registry)
    overrides = policy.get("version_overrides", {})
    exclusions = policy.get("excluded_contracts", [])
    if not isinstance(overrides, dict) or not isinstance(exclusions, list):
        raise CanonGenerationError("selection policy overrides and exclusions have invalid shapes")
    excluded_by_id: dict[str, dict[str, Any]] = {}
    for index, exclusion in enumerate(exclusions):
        if not isinstance(exclusion, dict) or not isinstance(exclusion.get("doc_id"), str):
            raise CanonGenerationError(f"selection policy excluded_contracts[{index}] is invalid")
        doc_id = exclusion["doc_id"]
        if doc_id in excluded_by_id:
            raise CanonGenerationError(f"duplicate suite exclusion for {doc_id}")
        if exclusion.get("membership_status") not in {
            "ACCEPTED_DEPENDENCY_ONLY", "DEFERRED_NONBLOCKING"
        }:
            raise CanonGenerationError(f"unsupported exclusion status for {doc_id}")
        excluded_by_id[doc_id] = exclusion

    if generated_doc_id in excluded_by_id or generated_doc_id in overrides:
        raise CanonGenerationError("generated CANON-1 identity cannot be an exclusion or version override")

    members: list[dict[str, Any]] = []
    handled: set[str] = {generated_doc_id, *excluded_by_id}
    for doc_id in sorted(contracts):
        if doc_id in handled:
            continue
        record = contracts[doc_id]
        if not isinstance(record, dict):
            raise CanonGenerationError(f"audit contract record for {doc_id} is malformed")
        override = overrides.get(doc_id)
        if override is not None:
            if not isinstance(override, dict):
                raise CanonGenerationError(f"version override for {doc_id} must be an object")
            version = override.get("version")
            digest = _require_sha256(override.get("sha256"), f"{doc_id} override hash")
            reason = override.get("reason")
            if not isinstance(version, str) or not isinstance(reason, str) or not reason.strip():
                raise CanonGenerationError(f"version override for {doc_id} needs version and reason")
            candidate = _candidate_by_identity(record, doc_id, version, digest)
            selection_basis = [reason]
        else:
            if record.get("status") != "selected":
                raise CanonGenerationError(
                    f"{doc_id} is {record.get('status')!r} and has no explicit version override or membership exclusion"
                )
            candidate = record.get("selected_candidate")
            if not isinstance(candidate, dict):
                raise CanonGenerationError(f"selected audit record for {doc_id} has no candidate")
            version = str(record.get("selected_version"))
            digest = _require_sha256(candidate.get("zip_sha256"), f"{doc_id}@{version} selected hash")
            if candidate.get("version") != version:
                raise CanonGenerationError(f"selected candidate version mismatch for {doc_id}")
            validation = candidate.get("validation")
            if not isinstance(validation, dict) or validation.get("status") not in {"VALID", "VALID_WITH_WARNING"}:
                raise CanonGenerationError(f"selected candidate is not internally valid: {doc_id}@{version}")
            selection_basis = record.get("selection_basis")
            if not isinstance(selection_basis, list) or not selection_basis:
                raise CanonGenerationError(f"selected audit record for {doc_id} has no selection basis")

        path = _safe_relative_path(candidate.get("source_path"), f"{doc_id}@{version} candidate path")
        _require_accepted_match(accepted, doc_id, version, digest, path)
        members.append(
            {
                "doc_id": doc_id,
                "version": version,
                "accepted_artifact_path": path,
                "sha256": digest,
                "membership_status": "CANON_MEMBER",
                "selection_basis": [str(item) for item in selection_basis],
            }
        )
        handled.add(doc_id)

    unused_overrides = set(overrides) - {row["doc_id"] for row in members}
    if unused_overrides:
        raise CanonGenerationError("selection policy contains unused version override(s): " + ", ".join(sorted(unused_overrides)))

    frozen_exclusions: list[dict[str, Any]] = []
    for doc_id in sorted(excluded_by_id):
        exclusion = excluded_by_id[doc_id]
        status = exclusion["membership_status"]
        reason = exclusion.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise CanonGenerationError(f"exclusion for {doc_id} needs a reason")
        row: dict[str, Any] = {
            "doc_id": doc_id,
            "membership_status": status,
            "reason": reason,
        }
        if "version" in exclusion or "sha256" in exclusion:
            version = exclusion.get("version")
            digest = _require_sha256(exclusion.get("sha256"), f"{doc_id} exclusion hash")
            if not isinstance(version, str):
                raise CanonGenerationError(f"versioned exclusion for {doc_id} needs a version")
            accepted_row = _require_accepted_match(accepted, doc_id, version, digest)
            row["version"] = version
            row["accepted_artifact_path"] = _safe_relative_path(
                accepted_row.get("path"), f"{doc_id}@{version} exclusion path"
            )
            row["sha256"] = digest
        frozen_exclusions.append(row)

    return {
        "format_version": 1,
        "audit_source_commit": audit_commit,
        "selection_policy_sha256": policy_hash,
        "accepted_registry_input_sha256": registry_hash,
        "generated_contract": {"doc_id": generated_doc_id, "version": generated_version},
        "members": sorted(members, key=lambda row: row["doc_id"]),
        "exclusions": frozen_exclusions,
        "not_current_versions": policy.get("not_current_versions", []),
        "dependency_closure": closure,
    }


def build_canon_contract(
    selection: dict[str, Any],
    artifacts_by_doc: dict[str, list[dict[str, Any]]],
    *,
    generated_at_utc: str,
    generator_commit: str | None = None,
    generator_version: str = GENERATOR_VERSION,
) -> dict[str, Any]:
    """Create the contract payload from a frozen membership and version set."""

    generated = selection.get("generated_contract")
    if not isinstance(generated, dict):
        raise CanonGenerationError("resolved selection has no generated contract identity")
    doc_id, version = generated.get("doc_id"), generated.get("version")
    if not isinstance(doc_id, str) or not isinstance(version, str):
        raise CanonGenerationError("resolved selection generated contract identity is malformed")
    members = selection.get("members")
    if not isinstance(members, list) or not members:
        raise CanonGenerationError("resolved selection must contain at least one canonical member")
    selection_bytes = _json_bytes(selection)
    pins: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for member in members:
        if not isinstance(member, dict):
            raise CanonGenerationError("resolved selection member entries must be objects")
        member_id = member.get("doc_id")
        if not isinstance(member_id, str) or member_id in seen_ids:
            raise CanonGenerationError(f"duplicate or invalid CANON member: {member_id!r}")
        seen_ids.add(member_id)
        artifact_rows = artifacts_by_doc.get(member_id)
        if not isinstance(artifact_rows, list) or not artifact_rows:
            raise CanonGenerationError(f"no archive artifacts were recorded for {member_id}")
        sorted_artifacts = sorted(artifact_rows, key=lambda row: row["path"])
        for artifact in sorted_artifacts:
            _safe_relative_path(artifact.get("path"), f"{member_id} pinned artifact path")
            _require_sha256(artifact.get("sha256"), f"{member_id} pinned artifact hash")
            if type(artifact.get("bytes")) is not int or artifact["bytes"] < 0:
                raise CanonGenerationError(f"{member_id} pinned artifact size must be a non-negative integer")
        pins.append(
            {
                "doc_id": member_id,
                "version": member["version"],
                "zip_path": member["accepted_artifact_path"],
                "bundle_sha256": _require_sha256(member.get("sha256"), f"{member_id} bundle hash"),
                "membership_status": "CANON_MEMBER",
                "selection_basis": member["selection_basis"],
                "artifacts": sorted_artifacts,
            }
        )
    pins.sort(key=lambda row: row["doc_id"])
    exclusions = selection.get("exclusions")
    if not isinstance(exclusions, list):
        raise CanonGenerationError("resolved selection exclusions must be an array")
    if seen_ids & {row.get("doc_id") for row in exclusions if isinstance(row, dict)}:
        raise CanonGenerationError("CANON membership overlaps an explicit exclusion")
    closure = selection.get("dependency_closure")
    if not isinstance(closure, dict):
        raise CanonGenerationError("resolved selection has no dependency closure summary")
    generation = {
        "generator": "tools/generate_canon.py",
        "generator_version": generator_version,
        "generator_commit": generator_commit,
        "resolved_selection_sha256": hashlib.sha256(selection_bytes).hexdigest(),
    }
    if isinstance(selection.get("generation_inputs"), dict):
        generation["generation_inputs"] = selection["generation_inputs"]
    else:
        generation["accepted_registry_input_sha256"] = selection.get("accepted_registry_input_sha256")
        generation["audit_source_commit"] = selection.get("audit_source_commit")
    return {
        "artifact_kind": "contract",
        "canonical": True,
        "doc_id": doc_id,
        "title": "CANON-1 Contract Suite Canonical Index",
        "version": version,
        "schema_version": "contract-suite/1.0",
        "suite_schema": "CS-0@3.0.1",
        "status": "active",
        "generated_at_utc": generated_at_utc,
        "summary": "Generated exact-hash pinset for the resolved current ticketing contract suite.",
        "dependencies": [],
        "dependency_floors": {},
        "canonical_bundles": pins,
        "canonical_exclusions": exclusions,
        "not_current_versions": selection.get("not_current_versions", []),
        "suite_closure": {
            "dependency_edge_count": closure.get("edge_count"),
            "unresolved_required_edges": closure.get("unresolved_required_edges"),
            "below_minimum_edges": closure.get("below_minimum_edges"),
            "invalid_dependency_records": closure.get("invalid_dependency_records"),
        },
        "generation": generation,
        "emits_events": False,
        "outbox_events": [],
    }


def build_canon_test_gates(
    canon_contract: dict[str, Any], *, generated_at_utc: str
) -> dict[str, Any]:
    """Create gate assertions for exact pins, archive artifacts, and closure."""

    doc_id = canon_contract["doc_id"]
    version = canon_contract["version"]
    suite_schema = canon_contract["suite_schema"]
    pins = canon_contract.get("canonical_bundles")
    if not isinstance(pins, list) or not pins:
        raise CanonGenerationError("CANON gates require a non-empty pin list")
    assertions: list[dict[str, Any]] = [
        {
            "type": "acceptance_criteria",
            "mode": "automated",
            "details": {
                "check": "unique_canonical_member_pins",
                "expected_member_count": len(pins),
            },
        },
        {
            "type": "acceptance_criteria",
            "mode": "automated",
            "details": {
                "check": "deferred_and_dependency_only_contracts_are_not_pinned",
                "doc_ids": sorted(
                    exclusion["doc_id"]
                    for exclusion in canon_contract.get("canonical_exclusions", [])
                )
            },
        },
        {
            "type": "acceptance_criteria",
            "mode": "automated",
            "details": {
                "check": "no_canonical_member_depends_on_pinset",
                "doc_id": doc_id,
            },
        },
        {
            "type": "suite_schema_matches",
            "mode": "automated",
            "details": {"expected": suite_schema},
        },
        {
            "type": "require_bundle_manifest_filename",
            "mode": "automated",
            "details": {"expected": "bundle.manifest.json"},
        },
        {
            "type": "require_bundle_files_match_manifest",
            "mode": "automated",
            "details": {},
        },
    ]
    for pin in pins:
        assertions.append(
            {
                "type": "canon_bundle_sha_match",
                "mode": "automated",
                "details": {
                    "doc_id": pin["doc_id"],
                    "version": pin["version"],
                    "expected_sha256": pin["bundle_sha256"],
                    "accepted_path": pin["zip_path"],
                },
            }
        )
        for artifact in pin["artifacts"]:
            assertions.append(
                {
                    "type": "canon_artifact_sha_match",
                    "mode": "automated",
                    "details": {
                        "doc_id": pin["doc_id"],
                        "version": pin["version"],
                        "path": artifact["path"],
                        "expected_sha256": artifact["sha256"],
                        "expected_bytes": artifact["bytes"],
                    },
                }
            )
    closure = canon_contract["suite_closure"]
    assertions.append(
        {
            "type": "dependency_min_version_satisfied",
            "mode": "automated",
            "details": {
                "scope": "resolved canonical suite",
                "dependency_edge_count": closure["dependency_edge_count"],
                "unresolved_required_edges": closure["unresolved_required_edges"],
                "below_minimum_edges": closure["below_minimum_edges"],
                "invalid_dependency_records": closure["invalid_dependency_records"],
            },
        }
    )
    gates = {
        "artifact_kind": "test_gates",
        "doc_id": f"{doc_id}-GATE",
        "version": version,
        "schema_version": "test-gates/1.0",
        "suite_schema": suite_schema,
        "status": "active",
        "title": "CANON-1 Test Gates",
        "generated_at_utc": generated_at_utc,
        "contract_ref": {"doc_id": doc_id, "version": version},
        "gates": [
            {
                "id": "CANON-1-P0-SUITE-PINS",
                "level": "P0",
                "must": True,
                "title": "Every current member has one accepted exact-hash pin.",
                "description": "Every canonical member pin resolves to one accepted, tracked bundle and all archive member hashes match.",
                "enforced_by": "tools/generate_canon.py verify and canonical strict audit",
                "acceptance_criteria": [
                    "Each canonical doc_id appears exactly once.",
                    "Each pin matches one accepted artifact path, version, and ZIP SHA-256.",
                    "Every declared artifact path, byte size, and SHA-256 matches the accepted ZIP payload.",
                    "FR-1 and accepted dependency-only EXT-1 are not pinned.",
                    "The resolved suite has no unresolved required edges, below-minimum edges, or invalid dependency records.",
                ],
                "assertions": assertions,
            }
        ],
    }
    return gates


def _archive_artifacts(bundle_path: Path) -> list[dict[str, Any]]:
    try:
        with zipfile.ZipFile(bundle_path, "r") as archive:
            names: set[str] = set()
            artifacts: list[dict[str, Any]] = []
            for info in archive.infolist():
                if info.is_dir():
                    continue
                path = _safe_relative_path(info.filename, "ZIP member path")
                if path in names:
                    raise CanonGenerationError(f"duplicate ZIP member path {path} in {bundle_path}")
                names.add(path)
                payload = archive.read(info)
                artifacts.append(
                    {"path": path, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
                )
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise CanonGenerationError(f"cannot inspect accepted bundle {bundle_path}: {error}") from error
    return sorted(artifacts, key=lambda row: row["path"])


def _archive_contract_data(bundle_path: Path, doc_id: str) -> dict[str, Any]:
    """Read the unique contract payload from an already validated ZIP."""

    contracts: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(bundle_path, "r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                _safe_relative_path(info.filename, "ZIP member path")
                if not info.filename.lower().endswith(".json"):
                    continue
                try:
                    value = json.loads(archive.read(info).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if (
                    isinstance(value, dict)
                    and value.get("artifact_kind") == "contract"
                    and value.get("doc_id") == doc_id
                ):
                    contracts.append(value)
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise CanonGenerationError(f"cannot read contract payload from {bundle_path}: {error}") from error
    if len(contracts) != 1:
        raise CanonGenerationError(
            f"expected one {doc_id} contract payload in {bundle_path}, found {len(contracts)}"
        )
    return contracts[0]


def validate_no_canon_member_dependency(
    member_doc_id: str, contract: dict[str, Any], canon_doc_id: str
) -> None:
    """Reject a suite member that depends on the pinset generated from that suite."""

    dependencies = contract.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise CanonGenerationError(f"{member_doc_id} dependencies must be an array")
    if any(
        isinstance(dependency, dict) and dependency.get("doc_id") == canon_doc_id
        for dependency in dependencies
    ):
        raise CanonGenerationError(
            f"{member_doc_id} depends on {canon_doc_id}; a CANON pinset cannot be a suite-member prerequisite"
        )
    floors = contract.get("dependency_floors", {})
    if not isinstance(floors, dict):
        raise CanonGenerationError(f"{member_doc_id} dependency_floors must be an object")
    if canon_doc_id in floors:
        raise CanonGenerationError(
            f"{member_doc_id} mirrors a dependency floor for {canon_doc_id}; remove the CANON bootstrap reference"
        )


def _tracked_paths(root: Path) -> set[str]:
    try:
        output = subprocess.check_output(["git", "ls-files", "-z"], cwd=root, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError) as error:
        raise CanonGenerationError(f"CANON generation requires a Git worktree: {error}") from error
    return {item for item in output.decode("utf-8").split("\0") if item}


def _verification_paths(root: Path) -> set[str]:
    """Include untracked files when verifying authority nested in the application repository."""

    tracked = _tracked_paths(root)
    try:
        repository_root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], cwd=root, stderr=subprocess.PIPE
            )
            .decode()
            .strip()
        ).resolve()
    except (OSError, subprocess.CalledProcessError) as error:
        raise CanonGenerationError(f"CANON verification requires a Git worktree: {error}") from error

    resolved_root = root.resolve()
    if not resolved_root.is_relative_to(repository_root):
        raise CanonGenerationError("CANON verification root must be inside the Git worktree")
    if resolved_root == repository_root:
        return tracked

    try:
        output = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=root,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise CanonGenerationError(f"cannot enumerate nested authority files: {error}") from error
    untracked = {item for item in output.decode("utf-8").split("\0") if item}
    return tracked | untracked


def _registry_records(root: Path, registry_path: Path) -> tuple[dict[str, Any], bytes, dict[tuple[str, str], dict[str, Any]]]:
    relative = _safe_relative_path(registry_path.as_posix(), "accepted registry path")
    registry, raw = _read_json(root / relative, "accepted registry")
    if relative not in _tracked_paths(root):
        raise CanonGenerationError(f"accepted registry is not Git-tracked: {relative}")
    return registry, raw, _accepted_by_identity(registry)


def generate_source_files(
    root: Path,
    selection: dict[str, Any],
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    output_dir: Path,
    generated_at_utc: str,
    generator_commit: str,
) -> dict[str, Any]:
    """Write deterministic CANON source files from accepted bundles."""

    if not GIT_COMMIT_PATTERN.fullmatch(generator_commit):
        raise CanonGenerationError("generator commit must be a full 40-character Git SHA")
    registry, registry_bytes, accepted = _registry_records(root, registry_path)
    accepted_validation = validate_accepted_release_registry(root, registry_path)
    if accepted_validation.get("status") != "VALID":
        errors = "; ".join(accepted_validation.get("errors", []))
        raise CanonGenerationError("accepted registry validation failed: " + errors)
    if hashlib.sha256(registry_bytes).hexdigest() != selection.get("accepted_registry_input_sha256"):
        raise CanonGenerationError("accepted registry changed since the resolved selection was frozen")
    members = selection.get("members")
    if not isinstance(members, list) or not members:
        raise CanonGenerationError("resolved selection must contain canonical members")
    artifacts_by_doc: dict[str, list[dict[str, Any]]] = {}
    for member in members:
        if not isinstance(member, dict):
            raise CanonGenerationError("resolved selection member entry is malformed")
        doc_id, version = member.get("doc_id"), member.get("version")
        digest = _require_sha256(member.get("sha256"), f"{doc_id} member hash")
        path = _safe_relative_path(member.get("accepted_artifact_path"), f"{doc_id} accepted path")
        accepted_row = _require_accepted_match(accepted, str(doc_id), str(version), digest, path)
        if path not in _tracked_paths(root):
            raise CanonGenerationError(f"selected accepted artifact is not Git-tracked: {path}")
        bundle_path = root / path
        # The accepted registry validator uses the reconciler's historical
        # compatibility rules for legacy-adopted ZIPs. The deterministic
        # release validator is reserved for newly built canonical bundles;
        # it correctly rejects old ZIP metadata such as variable timestamps.
        if accepted_row.get("sha256") != digest:
            raise CanonGenerationError(f"accepted bundle bytes changed for {doc_id}@{version}")
        validate_no_canon_member_dependency(
            str(doc_id), _archive_contract_data(bundle_path, str(doc_id)), "CANON-1"
        )
        artifacts_by_doc[str(doc_id)] = _archive_artifacts(bundle_path)

    contract = build_canon_contract(
        selection,
        artifacts_by_doc,
        generated_at_utc=generated_at_utc,
        generator_commit=generator_commit,
    )
    gates = build_canon_test_gates(contract, generated_at_utc=generated_at_utc)
    generated = selection["generated_contract"]
    release = {
        "doc_id": generated["doc_id"],
        "version": generated["version"],
        "suite_schema": "CS-0@3.0.1",
        "generated_at_utc": generated_at_utc,
        "release_status": "candidate",
        "release_intent": "Generated exact-hash suite pinset from the frozen resolved selection.",
        "source_provenance": {
            "kind": "resolved-canonical-suite-selection",
            "path": "generation-provenance.json",
            "generator": "tools/generate_canon.py",
            "generator_version": GENERATOR_VERSION,
            "generator_commit": generator_commit,
            "selection_sha256": hashlib.sha256(_json_bytes(selection)).hexdigest(),
            "accepted_registry_sha256": selection["accepted_registry_input_sha256"],
            "audit_source_commit": selection["audit_source_commit"],
        },
    }
    provenance = {
        "format_version": 1,
        "generation_status": "BUILT_CANDIDATE_SOURCE",
        "generator": "tools/generate_canon.py",
        "generator_version": GENERATOR_VERSION,
        "generator_commit": generator_commit,
        "audit_source_commit": selection["audit_source_commit"],
        "resolved_selection_path": (
            Path("release-src/current")
            / str(generated["doc_id"])
            / str(generated["version"])
            / "resolved-selection.json"
        ).as_posix(),
        "resolved_selection_sha256": hashlib.sha256(_json_bytes(selection)).hexdigest(),
        "accepted_registry_path": registry_path.as_posix(),
        "accepted_registry_input_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "accepted_registry_release_count_at_generation": len(registry.get("releases", [])),
        "canonical_member_count": len(members),
        "generated_release": generated,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, document in (
        ("release.json", release),
        ("contract.json", contract),
        ("test-gates.json", gates),
        ("generation-provenance.json", provenance),
    ):
        (output_dir / name).write_bytes(_json_bytes(document))
    return {
        "status": "BUILT_CANDIDATE_SOURCE",
        "doc_id": generated["doc_id"],
        "version": generated["version"],
        "member_count": len(members),
        "contract_sha256": hashlib.sha256(_json_bytes(contract)).hexdigest(),
        "test_gates_sha256": hashlib.sha256(_json_bytes(gates)).hexdigest(),
        "accepted_registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "selection_sha256": hashlib.sha256(_json_bytes(selection)).hexdigest(),
    }


def generate_canon_successor_source(
    root: Path,
    candidate_paths: list[Path],
    *,
    generated_version: str,
    output_dir: Path,
    generated_at_utc: str,
    generator_commit: str,
) -> dict[str, Any]:
    """Generate a successor from current CANON, manifest, closure, and explicit candidates."""

    root = root.resolve()
    output_dir = output_dir if output_dir.is_absolute() else root / output_dir
    if not candidate_paths:
        raise CanonGenerationError("successor requires at least one explicit validated candidate")
    candidate_rows: list[dict[str, Any]] = []
    candidate_paths_by_id: dict[str, Path] = {}
    for supplied_path in candidate_paths:
        path = supplied_path if supplied_path.is_absolute() else root / supplied_path
        try:
            validation = validate_bundle(path)
        except ReleaseError as error:
            raise CanonGenerationError(f"candidate release is invalid at {path}: {error}") from error
        doc_id, version = str(validation.get("doc_id")), str(validation.get("version"))
        if doc_id in candidate_paths_by_id:
            raise CanonGenerationError(f"duplicate candidate doc_id: {doc_id}")
        digest = _require_sha256(validation.get("zip_sha256"), f"{doc_id} candidate ZIP hash")
        contract = _archive_contract_data(path, doc_id)
        candidate_paths_by_id[doc_id] = path
        candidate_rows.append({
            "doc_id": doc_id,
            "version": version,
            "sha256": digest,
            "actual_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "zip_path": f"contracts/{doc_id}/{doc_id}_bundle_v{version}.zip",
            "validation": validation,
            "contract": contract,
        })

    manifest_path = root / "contracts/manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CanonGenerationError(f"cannot read active contract manifest: {error}") from error
    if not isinstance(manifest, dict):
        raise CanonGenerationError("active contract manifest must be a JSON object")
    manifest_rows = manifest.get("contracts")
    if not isinstance(manifest_rows, list):
        raise CanonGenerationError("active manifest has no contracts array")
    identity_overrides: list[dict[str, str]] = []
    for candidate_id in candidate_paths_by_id:
        active = [
            row for row in manifest_rows
            if isinstance(row, dict) and row.get("doc_id") == candidate_id
        ]
        if len(active) != 1:
            continue
        try:
            _contract_from_zip(root / _safe_relative_path(active[0].get("zip_path"), "candidate base ZIP path"),
                               validate_identity=True)
        except ActiveIdentityError as error:
            reason = str(error).replace(str(root) + "/", "")
            identity_overrides.append({"doc_id": candidate_id, "reason": reason})
    try:
        # A valid explicit candidate may supersede its own identity defect.
        manifest_validation = verify_manifest(
            root, manifest, identity_exemptions={row["doc_id"] for row in identity_overrides}
        )
    except ManifestError as error:
        raise CanonGenerationError(f"active contract manifest validation failed: {error}") from error
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    canon_row = next(
        (
            row for row in manifest["contracts"]
            if isinstance(row, dict) and row.get("membership") == "CANON_INDEX"
        ),
        None,
    )
    if not isinstance(canon_row, dict):
        raise CanonGenerationError("active manifest must contain exactly one CANON_INDEX")
    canon_path = root / _safe_relative_path(canon_row.get("zip_path"), "active CANON ZIP path")
    canon_contract = _archive_contract_data(canon_path, "CANON-1")

    if __package__:
        from .reconcile_contracts import build_dependency_closure
    else:
        from reconcile_contracts import build_dependency_closure

    candidate_by_id = {row["doc_id"]: row for row in candidate_rows}
    records: dict[str, dict[str, Any]] = {}
    selected_bundle_paths: dict[str, Path] = {}
    for row in manifest["contracts"]:
        if not isinstance(row, dict) or row.get("membership") == "CANON_INDEX":
            continue
        doc_id = str(row.get("doc_id"))
        candidate = candidate_by_id.get(doc_id)
        if candidate is None:
            path = root / _safe_relative_path(row.get("zip_path"), f"{doc_id} active ZIP path")
            contract = _archive_contract_data(path, doc_id)
            version = str(row.get("version"))
            source_path = row["zip_path"]
        else:
            path = candidate_paths_by_id[doc_id]
            contract = candidate["contract"]
            version = candidate["version"]
            source_path = candidate["zip_path"]
        validate_no_canon_member_dependency(doc_id, contract, "CANON-1")
        selected = {
            "version": version,
            "source_path": source_path,
            "contract_metadata": contract,
        }
        records[doc_id] = {
            "status": "selected",
            "selected_version": version,
            "selected_candidate": selected,
            "candidates": [selected],
        }
        selected_bundle_paths[doc_id] = path
    raw_closure = build_dependency_closure(records, [])
    closure = {
        "edge_count": raw_closure["edge_count"],
        "unresolved_required_edges": raw_closure["unresolved_target_edge_count"],
        "below_minimum_edges": raw_closure["below_minimum_edge_count"],
        "invalid_dependency_records": (
            raw_closure["invalid_dependency_list_count"]
            + raw_closure["invalid_dependency_record_count"]
            + raw_closure["invalid_minimum_version_count"]
        ),
        "input_sha256": hashlib.sha256(_json_bytes(raw_closure)).hexdigest(),
    }
    canon_sha = str(canon_row.get("zip_sha256"))
    selection = freeze_canon_successor(
        canon_contract,
        manifest,
        candidate_rows,
        closure,
        generated_version=generated_version,
        base_canon_sha256=canon_sha,
        manifest_sha256=manifest_sha,
        generator_commit=generator_commit,
    )
    if len(canon_contract.get("canonical_bundles", [])) != 56 or len(selection["members"]) != 56:
        raise CanonGenerationError("CANON successor must preserve the 56-member suite")
    selection["generation_inputs"]["manifest_validation_status"] = manifest_validation["status"]
    selection["generation_inputs"]["superseded_identity_defects"] = identity_overrides
    artifacts_by_doc = {
        doc_id: _archive_artifacts(path)
        for doc_id, path in selected_bundle_paths.items()
        if any(member.get("doc_id") == doc_id for member in selection["members"])
    }
    contract = build_canon_contract(
        selection,
        artifacts_by_doc,
        generated_at_utc=generated_at_utc,
        generator_commit=generator_commit,
    )
    gates = build_canon_test_gates(contract, generated_at_utc=generated_at_utc)
    selection_bytes = _json_bytes(selection)
    selection_sha = hashlib.sha256(selection_bytes).hexdigest()
    generation_inputs = selection["generation_inputs"]
    release = {
        "doc_id": "CANON-1",
        "version": generated_version,
        "suite_schema": "CS-0@3.0.1",
        "generated_at_utc": generated_at_utc,
        "release_status": "candidate",
        "release_intent": "Generated exact-hash suite pinset from current CANON, manifest, and validated candidates.",
        "source_provenance": {
            "kind": "manifest-backed-canonical-successor",
            "path": "generation-provenance.json",
            "generator": "tools/generate_canon.py",
            "generator_version": GENERATOR_VERSION,
            "generator_commit": generator_commit,
            "selection_sha256": selection_sha,
            "generation_inputs": generation_inputs,
        },
    }
    provenance = {
        "format_version": 1,
        "generation_status": "BUILT_CANDIDATE_SOURCE",
        "generator": "tools/generate_canon.py",
        "generator_version": GENERATOR_VERSION,
        "generator_commit": generator_commit,
        "resolved_selection_path": (
            Path("release-src/current/CANON-1") / generated_version / "resolved-selection.json"
        ).as_posix(),
        "resolved_selection_sha256": selection_sha,
        "generation_inputs": generation_inputs,
        "canonical_member_count": len(selection["members"]),
        "generated_release": {"doc_id": "CANON-1", "version": generated_version},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, document in (
        ("resolved-selection.json", selection),
        ("release.json", release),
        ("contract.json", contract),
        ("test-gates.json", gates),
        ("generation-provenance.json", provenance),
    ):
        (output_dir / name).write_bytes(_json_bytes(document))
    return {
        "status": "BUILT_CANDIDATE_SOURCE",
        "doc_id": "CANON-1",
        "version": generated_version,
        "member_count": len(selection["members"]),
        "resolved_selection_sha256": selection_sha,
        "contract_sha256": hashlib.sha256(_json_bytes(contract)).hexdigest(),
        "test_gates_sha256": hashlib.sha256(_json_bytes(gates)).hexdigest(),
        "base_canon_sha256": canon_sha,
        "active_manifest_sha256": manifest_sha,
        "dependency_closure_sha256": closure["input_sha256"],
    }


def verify_canon_release(
    root: Path,
    *,
    selection_path: Path,
    bundle_path: Path | None = None,
) -> dict[str, Any]:
    """Verify CANON pins against the current manifest and exact active ZIP bytes."""

    root = root.resolve()
    supplied_selection = Path(selection_path)
    if supplied_selection.is_absolute():
        try:
            supplied_selection = supplied_selection.resolve().relative_to(root)
        except ValueError as error:
            raise CanonGenerationError("resolved selection must be inside the repository") from error
    selection_relative = _safe_relative_path(supplied_selection.as_posix(), "resolved selection path")
    verification_paths = _verification_paths(root)
    if selection_relative not in verification_paths:
        raise CanonGenerationError(f"resolved selection is missing from the authority worktree: {selection_relative}")
    selection, selection_bytes = _read_json(root / selection_relative, "resolved selection")
    manifest_path = root / "contracts/manifest.json"
    try:
        manifest_validation = verify_manifest(root)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ManifestError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CanonGenerationError(f"active contract manifest validation failed: {error}") from error

    generated = selection.get("generated_contract")
    if not isinstance(generated, dict):
        raise CanonGenerationError("resolved selection has no CANON identity")
    doc_id, version = generated.get("doc_id"), generated.get("version")
    canon_row = manifest_record_by_identity(manifest, str(doc_id), str(version), "CANON_INDEX")
    canon_path = _safe_relative_path(canon_row.get("zip_path"), "active CANON path")
    if bundle_path is not None:
        supplied_path = Path(bundle_path)
        if supplied_path.is_absolute():
            supplied_path = supplied_path.resolve().relative_to(root)
        if supplied_path.as_posix() != canon_path:
            raise CanonGenerationError("supplied CANON bundle path disagrees with active manifest")
    if canon_path not in verification_paths:
        raise CanonGenerationError(f"accepted CANON bundle is missing from the authority worktree: {canon_path}")
    path = root / canon_path
    validation = validate_bundle(path)
    if validation.get("doc_id") != doc_id or validation.get("version") != version:
        raise CanonGenerationError("accepted CANON bundle identity disagrees with resolved selection")
    if validation.get("zip_sha256") != canon_row.get("zip_sha256"):
        raise CanonGenerationError("active CANON bundle hash disagrees with active manifest")

    member_rows = selection.get("members")
    if not isinstance(member_rows, list) or not member_rows:
        raise CanonGenerationError("resolved selection has no canonical members")
    member_ids = [row.get("doc_id") for row in member_rows if isinstance(row, dict)]
    if len(member_ids) != len(member_rows) or len(set(member_ids)) != len(member_ids):
        raise CanonGenerationError("resolved selection contains duplicate or malformed canonical members")
    if str(doc_id) in member_ids:
        raise CanonGenerationError("CANON-1 cannot pin itself as a current suite member")
    exclusions = selection.get("exclusions")
    if not isinstance(exclusions, list):
        raise CanonGenerationError("resolved selection exclusions must be an array")
    excluded_ids = [row.get("doc_id") for row in exclusions if isinstance(row, dict)]
    if len(excluded_ids) != len(exclusions) or len(set(excluded_ids)) != len(excluded_ids):
        raise CanonGenerationError("resolved selection contains duplicate or malformed exclusions")
    if set(member_ids) & set(excluded_ids):
        raise CanonGenerationError("resolved selection both pins and excludes the same contract")
    closure = selection.get("dependency_closure")
    if not isinstance(closure, dict) or any(
        closure.get(key) != 0
        for key in (
            "unresolved_required_edges",
            "below_minimum_edges",
            "invalid_dependency_records",
        )
    ):
        raise CanonGenerationError("resolved selection does not have complete required dependency closure")
    artifacts_by_doc: dict[str, list[dict[str, Any]]] = {}
    for member in member_rows:
        if not isinstance(member, dict):
            raise CanonGenerationError("resolved selection member is malformed")
        member_id, member_version = str(member.get("doc_id")), str(member.get("version"))
        member_hash = _require_sha256(member.get("sha256"), f"{member_id} accepted hash")
        active = manifest_record_by_identity(manifest, member_id, member_version, "CANON_MEMBER")
        if active.get("zip_sha256") != member_hash:
            raise CanonGenerationError(f"{member_id}@{member_version} hash does not match active manifest")
        member_path = _safe_relative_path(active.get("zip_path"), f"{member_id} active ZIP path")
        if member_path not in verification_paths:
            raise CanonGenerationError(f"selected active artifact is missing from the authority worktree: {member_path}")
        validate_no_canon_member_dependency(
            member_id, _archive_contract_data(root / member_path, member_id), str(doc_id)
        )
        artifacts_by_doc[member_id] = _archive_artifacts(root / member_path)

    for exclusion in exclusions:
        if not isinstance(exclusion, dict):
            raise CanonGenerationError("resolved selection exclusion is malformed")
        exclusion_id = str(exclusion.get("doc_id"))
        membership = exclusion.get("membership_status")
        if membership == "ACCEPTED_DEPENDENCY_ONLY":
            active = manifest_record_by_identity(
                manifest, exclusion_id, str(exclusion.get("version")), "DEPENDENCY_ONLY"
            )
            if active.get("zip_sha256") != exclusion.get("sha256"):
                raise CanonGenerationError(f"dependency-only hash mismatch for {exclusion_id}")
        elif membership == "DEFERRED_NONBLOCKING":
            if any(row.get("doc_id") == exclusion_id for row in manifest["contracts"]):
                raise CanonGenerationError(f"deferred contract is active: {exclusion_id}")

    release_source = root / "release-src/current" / str(doc_id) / str(version)
    release, _ = _read_json(release_source / "release.json", "CANON release metadata")
    provenance, _ = _read_json(release_source / "generation-provenance.json", "CANON generation provenance")
    contract = build_canon_contract(
        selection,
        artifacts_by_doc,
        generated_at_utc=str(release.get("generated_at_utc")),
        generator_commit=str(release.get("source_provenance", {}).get("generator_commit")),
        generator_version=str(release.get("source_provenance", {}).get("generator_version", GENERATOR_VERSION)),
    )
    gates = build_canon_test_gates(contract, generated_at_utc=str(release.get("generated_at_utc")))
    actual_contract: dict[str, Any] | None = None
    actual_gates: dict[str, Any] | None = None
    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if PurePosixPath(info.filename).name == f"{doc_id}_Contract_v{version}.json":
                actual_contract = json.loads(archive.read(info).decode("utf-8"))
            elif PurePosixPath(info.filename).name == f"{doc_id}_Test_Gates_v{version}.json":
                actual_gates = json.loads(archive.read(info).decode("utf-8"))
    if actual_contract != contract:
        raise CanonGenerationError("accepted CANON contract payload differs from frozen selection output")
    if actual_gates != gates:
        raise CanonGenerationError("accepted CANON test-gates payload differs from generated gate expectations")
    if provenance.get("resolved_selection_sha256") != hashlib.sha256(selection_bytes).hexdigest():
        raise CanonGenerationError("CANON provenance selection hash does not match frozen selection bytes")
    generation_inputs = selection.get("generation_inputs")
    if isinstance(generation_inputs, dict):
        if provenance.get("generation_inputs") != generation_inputs:
            raise CanonGenerationError("CANON provenance inputs do not match resolved selection")
        source_provenance = release.get("source_provenance", {})
        if source_provenance.get("generation_inputs") != generation_inputs:
            raise CanonGenerationError("CANON release metadata inputs do not match resolved selection")
        if generation_inputs.get("generator_version") != provenance.get("generator_version"):
            raise CanonGenerationError("CANON provenance generator version does not match resolved inputs")
        if generation_inputs.get("generator_commit") != provenance.get("generator_commit"):
            raise CanonGenerationError("CANON provenance generator commit does not match resolved inputs")
    elif provenance.get("accepted_registry_input_sha256") != selection.get("accepted_registry_input_sha256"):
        raise CanonGenerationError("CANON provenance acceptance-input hash does not match frozen selection")

    return {
        "status": "VALID",
        "doc_id": doc_id,
        "version": version,
        "path": canon_path,
        "sha256": validation["zip_sha256"],
        "pin_count": len(member_rows),
        "active_release_count": manifest_validation["contract_count"],
        "validation": validation,
        "manifest_validation": manifest_validation,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _current_commit(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise CanonGenerationError(f"cannot identify generator commit: {error}") from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    successor = subparsers.add_parser(
        "successor", help="generate CANON source from current pins, manifest, and validated candidates"
    )
    successor.add_argument("--root", type=Path, default=Path.cwd())
    successor.add_argument("--candidate", type=Path, action="append", required=True)
    successor.add_argument("--version", required=True)
    successor.add_argument("--output-dir", type=Path, required=True)
    successor.add_argument("--generated-at-utc", required=True)
    successor.add_argument("--generator-commit", default=None)

    build = subparsers.add_parser("build", help="build a deterministic CANON candidate ZIP")
    build.add_argument("--source", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify", help="verify accepted CANON pins and ZIP bytes")
    verify.add_argument("--root", type=Path, default=Path.cwd())
    verify.add_argument("--selection", type=Path, default=None)
    verify.add_argument("--bundle", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    root = args.root.resolve() if hasattr(args, "root") else Path.cwd().resolve()
    try:
        if args.command == "successor":
            result = generate_canon_successor_source(
                root,
                args.candidate,
                generated_version=args.version,
                output_dir=args.output_dir,
                generated_at_utc=args.generated_at_utc,
                generator_commit=args.generator_commit or _current_commit(root),
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "build":
            bundle = build_contract_release(args.source, args.output, allow_candidate=True)
            print(json.dumps(validate_bundle(bundle), indent=2, sort_keys=True))
            return 0
        if args.command == "verify":
            selection_path = args.selection
            if selection_path is None:
                try:
                    manifest = json.loads((root / "contracts/manifest.json").read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise CanonGenerationError(f"cannot read active contract manifest: {error}") from error
                selection_path = canon_selection_path(root, manifest)
            result = verify_canon_release(
                root,
                selection_path=selection_path,
                bundle_path=args.bundle,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
    except (CanonGenerationError, ReleaseError, ValueError) as error:
        print(f"CANON generation failed: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
