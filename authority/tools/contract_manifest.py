#!/usr/bin/env python3
"""Generate and verify the active contract ZIP and extracted-file inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


MANIFEST_PATH = Path("contracts/manifest.json")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
DOC_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
MEMBERSHIPS = {"CANON_MEMBER", "CANON_INDEX", "DEPENDENCY_ONLY"}


class ManifestError(ValueError):
    """Raised when active contract artifacts do not match the manifest model."""


class ActiveIdentityError(ManifestError):
    """Raised only when an otherwise readable release has inconsistent identity metadata."""


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _safe_member_name(name: str) -> tuple[str, ...]:
    if not name or "\\" in name or "\x00" in name:
        raise ManifestError(f"unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in name.rstrip("/").split("/")):
        raise ManifestError(f"unsafe archive path: {name!r}")
    if path.parts and ":" in path.parts[0]:
        raise ManifestError(f"unsafe archive path: {name!r}")
    return path.parts


def _archive_files(bundle: Path) -> tuple[list[tuple[str, bytes]], str | None]:
    if Path(bundle).is_symlink():
        raise ManifestError(f"contract ZIP must not be a symbolic link: {bundle}")
    try:
        archive = zipfile.ZipFile(bundle, "r")
    except (OSError, zipfile.BadZipFile) as error:
        raise ManifestError(f"cannot read ZIP {bundle}: {error}") from error
    with archive:
        rows: list[tuple[str, bytes]] = []
        raw_names: set[str] = set()
        for info in archive.infolist():
            parts = _safe_member_name(info.filename)
            if info.filename in raw_names:
                raise ManifestError(f"duplicate archive member: {info.filename}")
            raw_names.add(info.filename)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ManifestError(f"unsafe symlink archive member: {info.filename}")
            if info.is_dir():
                continue
            file_type = stat.S_IFMT(mode)
            if file_type and file_type not in {stat.S_IFREG, stat.S_IFLNK}:
                raise ManifestError(f"unsupported archive member type: {info.filename}")
            rows.append((info.filename, archive.read(info)))
        names = [name for name, _ in rows]
        wrapper = None
        if names:
            parsed = [_safe_member_name(name) for name in names]
            first = {parts[0] for parts in parsed}
            if len(first) == 1 and all(len(parts) >= 2 for parts in parsed):
                wrapper = next(iter(first))
        return rows, wrapper


def _mapped_path(name: str, wrapper: str | None) -> str:
    parts = _safe_member_name(name)
    if wrapper is not None:
        if parts[0] != wrapper or len(parts) < 2:
            raise ManifestError(f"archive member does not map through common wrapper: {name}")
        parts = parts[1:]
    path = PurePosixPath(*parts).as_posix()
    if path in {"", "."}:
        raise ManifestError(f"archive member maps to an empty path: {name}")
    return path


def extract_bundle(bundle: Path, destination: Path) -> list[dict[str, Any]]:
    """Safely extract one wrapper-normalized archive and return its file map."""

    rows, wrapper = _archive_files(bundle)
    mappings: list[tuple[str, str, bytes]] = []
    seen: set[str] = set()
    for archive_path, payload in rows:
        output_path = _mapped_path(archive_path, wrapper)
        if output_path in seen:
            raise ManifestError(f"duplicate normalized output path: {output_path}")
        seen.add(output_path)
        mappings.append((archive_path, output_path, payload))
    destination = Path(destination)
    if destination.is_symlink():
        raise ManifestError(f"unsafe extracted directory symlink: {destination}")
    if destination.exists():
        for child in destination.iterdir():
            if child.is_dir() and not child.is_symlink():
                import shutil
                shutil.rmtree(child)
            else:
                child.unlink()
    destination.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    for archive_path, output_path, payload in sorted(mappings, key=lambda row: row[1]):
        target = destination.joinpath(*PurePosixPath(output_path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        artifacts.append({
            "archive_path": archive_path,
            "extracted_path": output_path,
            "size": len(payload),
            "sha256": _digest(payload),
        })
    return artifacts


def _contract_from_zip(
    bundle: Path, *, validate_identity: bool = False
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows, wrapper = _archive_files(bundle)
    artifacts: list[dict[str, Any]] = []
    contracts: list[dict[str, Any]] = []
    for archive_path, payload in rows:
        extracted_path = _mapped_path(archive_path, wrapper)
        artifacts.append({
            "archive_path": archive_path,
            "extracted_path": extracted_path,
            "size": len(payload),
            "sha256": _digest(payload),
        })
        if not archive_path.lower().endswith(".json"):
            continue
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("artifact_kind") == "contract":
            contracts.append(value)
    if len(contracts) != 1:
        raise ManifestError(f"{bundle} must contain exactly one contract JSON artifact")
    contract = contracts[0]
    if not DOC_ID_RE.fullmatch(str(contract.get("doc_id", ""))):
        raise ManifestError(f"{bundle} has an invalid contract doc_id")
    if not VERSION_RE.fullmatch(str(contract.get("version", ""))):
        raise ManifestError(f"{bundle} has an invalid contract version")
    if validate_identity:
        _validate_active_release_identity(bundle, rows, wrapper, contract)
    return contract, sorted(artifacts, key=lambda row: row["extracted_path"])


def _validate_active_release_identity(
    bundle: Path,
    rows: list[tuple[str, bytes]],
    wrapper: str | None,
    contract: dict[str, Any],
) -> None:
    """Check that active ZIP names, metadata, and manifest paths share one identity."""

    doc_id, version = str(contract["doc_id"]), str(contract["version"])
    expected_outer = f"{doc_id}_bundle_v{version}.zip"
    if bundle.name != expected_outer or bundle.parent.name != doc_id:
        raise ActiveIdentityError(
            f"outer ZIP identity mismatch for {bundle}: expected contracts/{doc_id}/{expected_outer}"
        )
    expected_wrapper = f"{doc_id}_bundle_v{version}"
    if wrapper is not None and wrapper != expected_wrapper:
        raise ActiveIdentityError(
            f"archive wrapper identity mismatch: expected {expected_wrapper}, got {wrapper}"
        )

    contract_rows: list[tuple[str, dict[str, Any]]] = []
    gates_rows: list[tuple[str, dict[str, Any]]] = []
    manifest_rows: list[tuple[str, dict[str, Any]]] = []
    for archive_path, payload in rows:
        if not archive_path.lower().endswith(".json"):
            continue
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict):
            continue
        if value.get("artifact_kind") == "contract":
            contract_rows.append((archive_path, value))
        elif value.get("artifact_kind") == "test_gates":
            gates_rows.append((archive_path, value))
        elif value.get("artifact_kind") == "bundle_manifest":
            manifest_rows.append((archive_path, value))
    if len(contract_rows) != 1 or len(gates_rows) != 1 or len(manifest_rows) != 1:
        raise ManifestError(
            f"{bundle} must contain one contract, one test-gates artifact, and one bundle manifest"
        )

    def member_basename(archive_path: str) -> str:
        return PurePosixPath(archive_path).name

    contract_path, contract_value = contract_rows[0]
    contract_name = member_basename(contract_path)
    expected_contract_name = f"{doc_id}_Contract_v{version}.json"
    if (
        contract_name != expected_contract_name
        or contract_value.get("doc_id") != doc_id
        or contract_value.get("version") != version
    ):
        raise ActiveIdentityError(
            f"contract filename identity mismatch: expected {expected_contract_name} for {doc_id}@{version}"
        )

    gates_path, gates = gates_rows[0]
    gates_name = member_basename(gates_path)
    gates_name_pattern = re.compile(
        rf"^(?:{re.escape(doc_id)}_Test_Gates|{re.escape(doc_id)}-GATE_TestGates)_v"
        rf"(?P<version>\d+\.\d+\.\d+)\.json$"
    )
    gates_name_match = gates_name_pattern.fullmatch(gates_name)
    contract_ref = gates.get("contract_ref")
    if (
        gates_name_match is None
        or gates_name_match.group("version") != version
        or gates.get("version") != version
        or gates.get("doc_id") != f"{doc_id}-GATE"
        or not isinstance(contract_ref, dict)
        or contract_ref.get("doc_id") != doc_id
        or contract_ref.get("version") != version
    ):
        raise ActiveIdentityError(
            f"test-gates identity, filename, or contract_ref mismatch for {doc_id}@{version}"
        )

    manifest_path, manifest = manifest_rows[0]
    if PurePosixPath(_mapped_path(manifest_path, wrapper)).as_posix() != "bundle.manifest.json":
        raise ActiveIdentityError(
            f"bundle manifest filename mismatch: expected bundle.manifest.json, got {manifest_path}"
        )
    bundle_identity = manifest.get("bundle")
    manifest_doc_id = manifest.get("doc_id")
    manifest_version = manifest.get("version")
    if isinstance(bundle_identity, dict):
        manifest_doc_id = manifest_doc_id or bundle_identity.get("bundle_id")
        manifest_version = manifest_version or bundle_identity.get("bundle_version")
    if (
        manifest_doc_id != doc_id
        or manifest_version != version
        or (
            bundle_identity is not None
            and (
                not isinstance(bundle_identity, dict)
                or bundle_identity.get("bundle_id") != doc_id
                or bundle_identity.get("bundle_version") != version
            )
        )
    ):
        raise ActiveIdentityError(f"bundle manifest identity mismatch for {doc_id}@{version}")
    records = manifest.get("files")
    expected_paths = {
        _mapped_path(contract_path, wrapper),
        _mapped_path(gates_path, wrapper),
    }
    if not isinstance(records, list):
        raise ManifestError("bundle manifest files must be an array")
    paths = [row.get("path") for row in records if isinstance(row, dict)]
    if len(paths) != len(records) or len(paths) != 2:
        raise ManifestError("bundle manifest files must contain two object records with paths")
    if set(paths) != expected_paths:
        raise ActiveIdentityError(
            f"bundle manifest file paths do not name the actual contract and gate members for {doc_id}@{version}"
        )
    for name in paths:
        match = re.search(r"_v(\d+\.\d+\.\d+)\.json$", str(name))
        if match is None or match.group(1) != version:
            raise ActiveIdentityError(f"manifest file identity mismatch for {name}")


def _canon_contract(root: Path, index_record: dict[str, Any] | None = None) -> tuple[dict[str, Any], Path, str]:
    if index_record is not None:
        path = root / index_record["zip_path"]
    else:
        folder = root / "contracts/CANON-1"
        zips = sorted(folder.glob("*.zip")) if folder.exists() else []
        if len(zips) != 1:
            raise ManifestError("CANON-1 must have exactly one active ZIP")
        path = zips[0]
    contract, _ = _contract_from_zip(path)
    if contract.get("doc_id") != "CANON-1":
        raise ManifestError("CANON index ZIP does not contain CANON-1")
    return contract, path, _digest(path.read_bytes())


def _read_existing_manifest(root: Path) -> dict[str, Any] | None:
    path = root / MANIFEST_PATH
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ManifestError(f"cannot read active manifest: {error}") from error
    return value if isinstance(value, dict) else None


def _membership_records(canon: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    pins = canon.get("canonical_bundles")
    exclusions = canon.get("canonical_exclusions")
    if not isinstance(pins, list) or not isinstance(exclusions, list):
        raise ManifestError("CANON-1 has no canonical bundle and exclusion arrays")
    members: dict[str, dict[str, Any]] = {}
    dependencies: dict[str, dict[str, Any]] = {}
    for row in pins:
        if not isinstance(row, dict):
            raise ManifestError("CANON pin is malformed")
        doc_id = row.get("doc_id")
        if not isinstance(doc_id, str) or doc_id in members:
            raise ManifestError(f"duplicate or invalid CANON member: {doc_id!r}")
        digest = row.get("bundle_sha256")
        version = row.get("version")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ManifestError(f"CANON pin has invalid hash for {doc_id}")
        if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
            raise ManifestError(f"CANON pin has invalid version for {doc_id}")
        members[doc_id] = row
    for row in exclusions:
        if not isinstance(row, dict):
            raise ManifestError("CANON exclusion is malformed")
        doc_id = row.get("doc_id")
        status = row.get("membership_status")
        if status == "ACCEPTED_DEPENDENCY_ONLY":
            if not isinstance(doc_id, str) or doc_id in dependencies:
                raise ManifestError(f"duplicate or invalid dependency-only contract: {doc_id!r}")
            dependencies[doc_id] = row
    return members, dependencies


def _verify_extracted(root: Path, zip_path: Path, extracted_root: Path) -> list[dict[str, Any]]:
    contract, expected = _contract_from_zip(zip_path)
    actual: list[dict[str, Any]] = []
    if not extracted_root.is_dir() or extracted_root.is_symlink():
        raise ManifestError(f"missing or unsafe extracted representation: {extracted_root}")
    for path in sorted(extracted_root.rglob("*")):
        if path.is_symlink():
            raise ManifestError(f"unsafe extracted symlink: {path}")
        if path.is_file():
            rel = path.relative_to(extracted_root).as_posix()
            actual.append({"extracted_path": rel, "size": path.stat().st_size, "sha256": _digest(path.read_bytes())})
        elif not path.is_dir():
            raise ManifestError(f"unsupported extracted object: {path}")
    expected_by_path = {row["extracted_path"]: row for row in expected}
    actual_by_path = {row["extracted_path"]: row for row in actual}
    if set(expected_by_path) != set(actual_by_path):
        raise ManifestError(f"ZIP/extracted member set differs for {contract['doc_id']}")
    for relative, row in expected_by_path.items():
        actual_row = actual_by_path[relative]
        if (row["size"], row["sha256"]) != (actual_row["size"], actual_row["sha256"]):
            raise ManifestError(f"ZIP/extracted byte mismatch for {contract['doc_id']}/{relative}")
    return expected


def build_manifest(
    root: Path, *, identity_exemptions: set[str] | None = None
) -> dict[str, Any]:
    """Build deterministic manifest data from active ZIPs and their CANON pins."""

    root = Path(root).resolve()
    identity_exemptions = identity_exemptions or set()
    canon, canon_path, canon_sha = _canon_contract(root)
    members, dependencies = _membership_records(canon)
    active: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    contract_root = root / "contracts"
    if not contract_root.is_dir():
        raise ManifestError("contracts/ is missing")
    dirs = sorted((p for p in contract_root.iterdir() if p.is_dir()), key=lambda p: p.name)
    zip_paths = []
    for directory in dirs:
        if directory.name == "extracted":
            continue
        zips = sorted(directory.glob("*.zip"))
        if len(zips) != 1:
            raise ManifestError(f"{directory.relative_to(root)} must contain exactly one active ZIP")
        if any(p.is_dir() and p.name != "extracted" for p in directory.iterdir()):
            raise ManifestError(f"unexpected directory under {directory.relative_to(root)}")
        zip_paths.extend(zips)
    for zip_path in zip_paths:
        if zip_path.is_symlink() or not zip_path.is_file():
            raise ManifestError(f"active contract ZIP must be a regular file: {zip_path.relative_to(root)}")
        contract, artifacts = _contract_from_zip(zip_path)
        doc_id, version = str(contract["doc_id"]), str(contract["version"])
        if doc_id not in identity_exemptions:
            rows, wrapper = _archive_files(zip_path)
            _validate_active_release_identity(zip_path, rows, wrapper, contract)
        if zip_path.parent.name != doc_id:
            raise ManifestError(f"{zip_path.relative_to(root)} is stored under the wrong doc_id")
        if doc_id in seen:
            raise ManifestError(f"more than one active ZIP exists for {doc_id}")
        digest = _digest(zip_path.read_bytes())
        if doc_id == "CANON-1":
            membership = "CANON_INDEX"
            if version != str(canon.get("version")) or digest != canon_sha:
                raise ManifestError("CANON-1 active ZIP changed while building manifest")
        elif doc_id in members:
            pin = members[doc_id]
            if version != pin.get("version") or digest != pin.get("bundle_sha256"):
                raise ManifestError(f"CANON pin mismatch for {doc_id}@{version}")
            membership = "CANON_MEMBER"
        elif doc_id in dependencies:
            dependency = dependencies[doc_id]
            if version != dependency.get("version") or digest != dependency.get("sha256"):
                raise ManifestError(f"dependency-only hash mismatch for {doc_id}@{version}")
            membership = "DEPENDENCY_ONLY"
        else:
            raise ManifestError(f"unregistered live contract ZIP: {doc_id}@{version}")
        extracted_root = zip_path.parent / "extracted"
        extracted_path = extracted_root.relative_to(root).as_posix()
        parity_artifacts = _verify_extracted(root, zip_path, extracted_root)
        record = {
            "doc_id": doc_id,
            "version": version,
            "membership": membership,
            "canon_pinned": membership == "CANON_MEMBER",
            "zip_path": zip_path.relative_to(root).as_posix(),
            "zip_sha256": digest,
            "extracted_path": extracted_path,
            "artifacts": parity_artifacts,
        }
        seen[doc_id] = record
        active.append(record)
    for doc_id in sorted(set(members) - set(seen)):
        raise ManifestError(f"CANON member is missing: {doc_id}")
    for doc_id in sorted(set(dependencies) - set(seen)):
        raise ManifestError(f"required dependency-only contract is missing: {doc_id}")
    for deferred in canon.get("canonical_exclusions", []):
        if isinstance(deferred, dict) and deferred.get("membership_status") == "DEFERRED_NONBLOCKING":
            if deferred.get("doc_id") in seen:
                raise ManifestError(f"deferred contract is active: {deferred['doc_id']}")
    active.sort(key=lambda row: row["doc_id"])
    return {"format_version": 1, "contracts": active}


def verify_manifest(
    root: Path,
    manifest: dict[str, Any] | None = None,
    *,
    identity_exemptions: set[str] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    expected = build_manifest(root, identity_exemptions=identity_exemptions)
    if manifest is None:
        path = root / MANIFEST_PATH
        try:
            payload = path.read_bytes()
            manifest = json.loads(payload.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ManifestError(f"cannot read {MANIFEST_PATH}: {error}") from error
        if payload != _json_bytes(expected):
            raise ManifestError(f"{MANIFEST_PATH} is not the deterministic active inventory")
    if manifest != expected:
        raise ManifestError("manifest records differ from active ZIPs, CANON pins, or extracted files")
    return {"status": "VALID", "contract_count": len(expected["contracts"]), "manifest_sha256": _digest(_json_bytes(expected))}


def write_manifest(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    stray = verify_no_stray_contract_zips(root)
    if stray:
        raise ManifestError("; ".join(stray))
    manifest = build_manifest(root)
    target = root / MANIFEST_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_json_bytes(manifest))
    return verify_manifest(root, manifest)


def _is_contract_zip(path: Path) -> bool:
    try:
        contract, _ = _contract_from_zip(path)
        return bool(contract.get("doc_id"))
    except (ManifestError, OSError):
        return False


def verify_no_stray_contract_zips(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors = []
    allowed_support = (Path("tools/support"), Path("tools"))
    for path in sorted(root.rglob("*.zip")):
        if any(part in {".git", ".venv", ".staging", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(root)
        if path.is_symlink():
            errors.append(f"ZIP path must not be a symbolic link: {relative.as_posix()}")
            continue
        in_contract_tree = (
            len(relative.parts) == 3
            and relative.parts[0] == "contracts"
            and (root / "contracts" / relative.parts[1]).is_dir()
        )
        if _is_contract_zip(path) and not in_contract_tree:
            errors.append(f"contract ZIP outside contracts/<DOC-ID>/: {relative.as_posix()}")
        elif not _is_contract_zip(path) and not any(
            relative == allowed or allowed in relative.parents for allowed in allowed_support
        ):
            errors.append(f"non-contract ZIP outside tools/: {relative.as_posix()}")
    return errors


def dependency_closure(root: Path, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check the closed active set with the dependency rules used by strict audit."""

    root = Path(root).resolve()
    if manifest is None:
        manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    rows = manifest.get("contracts")
    if not isinstance(rows, list):
        raise ManifestError("active manifest has no contracts array")
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ManifestError("active manifest contains a malformed record")
        contract, _ = _contract_from_zip(root / row["zip_path"])
        doc_id = str(row["doc_id"])
        if contract.get("doc_id") != doc_id or contract.get("version") != row.get("version"):
            raise ManifestError(f"active ZIP identity changed for {doc_id}")
        candidate = {
            "version": row["version"],
            "source_path": row["zip_path"],
            "contract_metadata": contract,
        }
        records[doc_id] = {
            "status": "selected",
            "selected_version": row["version"],
            "selected_candidate": candidate,
            "candidates": [candidate],
        }
    if __package__:
        from .reconcile_contracts import build_dependency_closure
    else:
        from reconcile_contracts import build_dependency_closure

    return build_dependency_closure(records, [])


def active_repository_audit(root: Path) -> dict[str, Any]:
    """Return strict audit results for the manifest-backed active repository."""

    root = Path(root).resolve()
    errors: list[str] = []
    try:
        manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
        validation = verify_manifest(root, manifest)
        errors.extend(verify_no_stray_contract_zips(root))
        closure = dependency_closure(root, manifest)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ManifestError, ValueError) as error:
        errors.append(str(error))
        manifest = {"contracts": []}
        validation = {"status": "INVALID", "contract_count": 0}
        closure = {
            "edge_count": 0,
            "unresolved_target_edge_count": 0,
            "below_minimum_edge_count": 0,
            "invalid_dependency_list_count": 0,
            "invalid_dependency_record_count": 0,
            "status": "blocked",
            "edges": [],
        }
    rows = manifest.get("contracts", [])
    canonical_count = sum(row.get("membership") == "CANON_MEMBER" for row in rows if isinstance(row, dict))
    dependency_only_count = sum(row.get("membership") == "DEPENDENCY_ONLY" for row in rows if isinstance(row, dict))
    unresolved = closure.get("unresolved_target_edge_count", 0)
    below_minimum = closure.get("below_minimum_edge_count", 0)
    invalid = closure.get("invalid_dependency_list_count", 0) + closure.get("invalid_dependency_record_count", 0)
    blocked = bool(errors) or validation.get("status") != "VALID" or closure.get("status") != "resolved"
    summary = {
        "manifest_status": validation.get("status"),
        "manifest_contract_count": validation.get("contract_count", 0),
        "canon_member_count": canonical_count,
        "dependency_only_contract_count": dependency_only_count,
        "dependency_edge_count": closure.get("edge_count", 0),
        "dependency_target_unresolved_count": unresolved,
        "dependency_floor_conflict_count": below_minimum,
        "dependency_edge_invalid_count": invalid,
        "phase_2_blocked": blocked,
    }
    return {
        "status": "BLOCKED" if blocked else "PASS",
        "summary": summary,
        "dependency_closure": closure,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "verify", "extract"))
    parser.add_argument("doc_id", nargs="?")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            result = write_manifest(args.root)
        elif args.command == "extract":
            if not isinstance(args.doc_id, str) or not DOC_ID_RE.fullmatch(args.doc_id):
                raise ManifestError("extract requires a valid DOC-ID")
            folder = args.root.resolve() / "contracts" / args.doc_id
            zips = sorted(folder.glob("*.zip"))
            if len(zips) != 1:
                raise ManifestError(f"{args.doc_id} must have exactly one active ZIP before extraction")
            artifacts = extract_bundle(zips[0], folder / "extracted")
            result = {"status": "EXTRACTED", "doc_id": args.doc_id, "artifact_count": len(artifacts)}
        else:
            errors = verify_no_stray_contract_zips(args.root)
            if errors:
                raise ManifestError("; ".join(errors))
            result = verify_manifest(args.root)
        print(json.dumps(result, sort_keys=True))
    except (ManifestError, OSError, ValueError) as error:
        print(f"Contract manifest validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
