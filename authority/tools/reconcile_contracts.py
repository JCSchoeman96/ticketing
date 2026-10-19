#!/usr/bin/env python3
"""Inventory and reconcile contract bundles without changing source artifacts.

Canonical audits read Git-tracked files only. Forensic audits can include
ignored and untracked workspace files. Both modes write only the requested
reports; ZIP payloads are never extracted or rewritten by this tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator, SchemaError
except ImportError:  # The audit stays importable, but fails closed when schemas need validation.
    Draft202012Validator = None  # type: ignore[assignment,misc]
    SchemaError = ValueError  # type: ignore[assignment,misc]


SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
CONTRACT_DOC_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
CS0_DEPENDENCY_EDGE_TYPES = {
    "requires",
    "foundation_floor",
    "registry_floor",
    "governance_floor",
    "integration_floor",
    "paired_contract",
}
DEPENDENCY_BLOCKING_STATUSES = {
    "below_minimum",
    "target_unresolved",
    "invalid_minimum_version",
    "invalid_dependency_list",
    "invalid_dependency_record",
}
FILENAME_BUNDLE_RE = re.compile(
    r"^(?P<doc_id>[A-Z][A-Z0-9]*-\d+)_bundle_v(?P<version>\d+\.\d+\.\d+)(?P<suffix>.*)\.zip$",
    re.IGNORECASE,
)
DOC_ID_RE = re.compile(r"\b([A-Z][A-Z0-9]*-\d+)\b")
VERSION_RE = re.compile(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)")
SCHEMA_REFERENCE_RE = re.compile(r"CS-0@(\d+\.\d+\.\d+)")
REQUIRED_ARTIFACT_SCHEMAS = {
    "contract": "contract-suite/1.0",
    "test_gates": "test-gates/1.0",
    "bundle_manifest": "bundle-manifest/1.0",
}
REPORT_JSON = Path("reports/contract-reconciliation.json")
REPORT_MARKDOWN = Path("reports/contract-reconciliation.md")


def semver_key(version: str) -> tuple[int, int, int]:
    """Return numeric SemVer components, rejecting non SemVer values."""

    match = SEMVER_RE.fullmatch(version)
    if not match:
        raise ValueError(f"Not a numeric semantic version: {version!r}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def semver_sort_key(version: Any) -> tuple[int, tuple[int, int, int], str]:
    """Sort valid semantic versions numerically and malformed values after them."""

    text = str(version) if version is not None else ""
    if SEMVER_RE.fullmatch(text):
        return 0, semver_key(text), ""
    return 1, (0, 0, 0), text


def strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    """Return every graph component in stable order using Tarjan's algorithm."""

    vertices = set(graph)
    for targets in graph.values():
        vertices.update(targets)

    next_index = 0
    indexes: dict[str, int] = {}
    low_links: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(vertex: str) -> None:
        nonlocal next_index
        indexes[vertex] = next_index
        low_links[vertex] = next_index
        next_index += 1
        stack.append(vertex)
        on_stack.add(vertex)

        for target in sorted(graph.get(vertex, set())):
            if target not in indexes:
                visit(target)
                low_links[vertex] = min(low_links[vertex], low_links[target])
            elif target in on_stack:
                low_links[vertex] = min(low_links[vertex], indexes[target])

        if low_links[vertex] == indexes[vertex]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == vertex:
                    break
            components.append(sorted(component))

    for vertex in sorted(vertices):
        if vertex not in indexes:
            visit(vertex)

    return sorted(components, key=lambda component: (component[0], len(component), component))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def tracked_paths(root: Path) -> set[str]:
    """Return Git tracked paths, or an empty set for temporary fixture roots."""

    try:
        output = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=root, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {item for item in output.decode("utf-8", errors="replace").split("\0") if item}


def untracked_paths(root: Path) -> set[str]:
    """Return non-ignored untracked paths relative to a nested authority root."""

    try:
        output = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("canonical audit cannot enumerate untracked authority files") from error
    return {item for item in output.decode("utf-8", errors="replace").split("\0") if item}


def workspace_files(root: Path) -> list[Path]:
    """List all regular files under root, including ignored and untracked files."""

    result: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts or ".pytest_cache" in relative.parts:
            continue
        if relative.as_posix() in {REPORT_JSON.as_posix(), REPORT_MARKDOWN.as_posix()}:
            continue
        try:
            if path.is_file():
                result.append(path)
        except OSError:
            continue
    return sorted(result, key=lambda item: relative_path(item, root))


def canonical_workspace_files(root: Path) -> tuple[list[Path], set[str], list[str]]:
    """Return authority worktree files and any tracked paths missing from disk."""

    try:
        repository_root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=root,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        ).resolve()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("canonical audit requires a Git worktree") from error
    resolved_root = root.resolve()
    if not resolved_root.is_relative_to(repository_root):
        raise ValueError(
            f"canonical audit root must be inside the Git worktree: {repository_root}"
        )

    tracked = tracked_paths(root)
    visible_paths = tracked
    if resolved_root != repository_root:
        visible_paths = tracked | untracked_paths(root)
    excluded = {REPORT_JSON.as_posix(), REPORT_MARKDOWN.as_posix()}
    files: list[Path] = []
    missing: list[str] = []
    for item in sorted(visible_paths):
        if item in excluded:
            continue
        path = root / item
        try:
            if path.is_file():
                files.append(path)
            elif item in tracked:
                missing.append(item)
        except OSError:
            if item in tracked:
                missing.append(item)
    return files, tracked, missing


def extract_json(payload: bytes) -> tuple[Any | None, str | None]:
    try:
        return json.loads(payload.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, str(error)


def safe_archive_path(name: str) -> tuple[str | None, str | None]:
    """Normalize a ZIP member name and reject paths that can escape a tree."""

    if "\x00" in name:
        return None, "ZIP member path contains a NUL byte"
    if "\\" in name:
        return None, f"ZIP member path uses a backslash separator: {name!r}"
    path = PurePosixPath(name)
    if path.is_absolute() or re.match(r"^[A-Za-z]:", name):
        return None, f"ZIP member path is absolute: {name!r}"
    if any(part == ".." for part in path.parts):
        return None, f"ZIP member path contains traversal: {name!r}"
    normalized = path.as_posix()
    if not normalized or normalized == ".":
        return None, f"ZIP member path is empty: {name!r}"
    return normalized, None


def common_archive_prefix(file_paths: list[str]) -> str | None:
    """Find a single wrapper directory shared by all archive payload files."""

    if not file_paths:
        return None
    split = [PurePosixPath(path).parts for path in file_paths]
    if not all(len(parts) > 1 for parts in split):
        return None
    prefixes = {parts[0] for parts in split}
    return next(iter(prefixes)) if len(prefixes) == 1 else None


def strip_archive_prefix(path: str, prefix: str | None) -> str:
    if prefix is None:
        return path
    parts = PurePosixPath(path).parts
    if len(parts) > 1 and parts[0] == prefix:
        return PurePosixPath(*parts[1:]).as_posix()
    return path


def artifact_kind(data: Any, member_name: str) -> str | None:
    if not isinstance(data, dict):
        return None
    value = data.get("artifact_kind")
    if value == "contract":
        return "contract"
    if value == "test_gates":
        return "test_gates"
    if value == "bundle_manifest" or PurePosixPath(member_name).name == "bundle.manifest.json":
        return "bundle_manifest"
    if isinstance(data.get("contract_ref"), dict) and isinstance(data.get("gates"), list):
        return "test_gates"
    return None


def manifest_identity(manifest: dict[str, Any]) -> tuple[str | None, str | None]:
    bundle = manifest.get("bundle")
    bundle = bundle if isinstance(bundle, dict) else {}
    doc_id = manifest.get("doc_id") or bundle.get("bundle_id") or bundle.get("doc_id")
    version = (
        manifest.get("version")
        or bundle.get("bundle_version")
        or bundle.get("version")
        or manifest.get("bundle_version")
    )
    bundle_name = doc_id if isinstance(doc_id, str) else None
    if not bundle_name:
        bundle_name = bundle.get("bundle_name") or bundle.get("name")
    if isinstance(bundle_name, str):
        match = re.match(
            r"^(?P<doc>[A-Z][A-Z0-9]*-\d+)(?:_bundle(?:_v(?P<version>\d+\.\d+\.\d+))?)?$",
            bundle_name,
        )
        if match:
            doc_id = match.group("doc")
            version = version or match.group("version")
    return (str(doc_id) if doc_id is not None else None, str(version) if version is not None else None)


def manifest_declared_identities(manifest: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return every recognized doc/version assertion inside a manifest."""

    doc_ids: set[str] = set()
    versions: set[str] = set()
    bundle = manifest.get("bundle")
    bundle = bundle if isinstance(bundle, dict) else {}
    identifier_pattern = re.compile(
        r"^(?P<doc>[A-Z][A-Z0-9]*-\d+)(?:_bundle(?:_v(?P<version>\d+\.\d+\.\d+))?)?$",
        re.IGNORECASE,
    )

    for value in (manifest.get("doc_id"), bundle.get("doc_id")):
        if isinstance(value, str) and value:
            match = identifier_pattern.fullmatch(value)
            if match:
                doc_ids.add(match.group("doc").upper())
                if match.group("version"):
                    versions.add(match.group("version"))
            else:
                doc_ids.add(value)
    for value in (manifest.get("version"), manifest.get("bundle_version"), bundle.get("version"), bundle.get("bundle_version")):
        if value is not None and str(value):
            versions.add(str(value))

    identifier_values = (
        manifest.get("bundle_id"),
        bundle.get("bundle_id"),
        bundle.get("bundle_name"),
        bundle.get("name"),
    )
    for value in identifier_values:
        if not isinstance(value, str):
            continue
        match = identifier_pattern.fullmatch(value)
        if match:
            doc_ids.add(match.group("doc").upper())
            if match.group("version"):
                versions.add(match.group("version"))
    return doc_ids, versions


def filename_identity(path: Path) -> tuple[str | None, str | None, str]:
    match = FILENAME_BUNDLE_RE.fullmatch(path.name)
    if not match:
        return None, None, ""
    return match.group("doc_id").upper(), match.group("version"), match.group("suffix")


def summarized_contract_metadata(data: dict[str, Any]) -> dict[str, Any]:
    lineage = {
        key: data[key]
        for key in data
        if any(term in key.lower() for term in ("supersed", "lineage", "predecessor", "replac"))
    }
    return {
        "doc_id": data.get("doc_id"),
        "version": data.get("version"),
        "artifact_name": data.get("artifact_name") or data.get("artifact_filename"),
        "schema_version": data.get("schema_version"),
        "suite_schema": data.get("suite_schema"),
        "status": data.get("status"),
        "canonical": data.get("canonical"),
        "dependencies": data.get("dependencies", []),
        "dependency_floors": data.get("dependency_floors", {}),
        "lineage": lineage,
    }


def gate_schema_expectations(gates: dict[str, Any]) -> list[str]:
    expectations: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            assertion_type = value.get("type")
            details = value.get("details")
            if assertion_type in {"suite_schema_matches", "suite_schema_equals"} and isinstance(details, dict):
                expected = details.get("expected") or details.get("equals") or details.get("schema")
                if isinstance(expected, str):
                    expectations.add(expected)
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(gates.get("gates", []))
    return sorted(expectations)


def canonical_manifest_value(manifest: dict[str, Any]) -> dict[str, Any]:
    """Ignore only generation timestamps and list ordering for duplicate checks."""

    ignored = {"generated_at_utc", "created_at_utc", "updated_at_utc", "last_updated_utc"}
    normalized: dict[str, Any] = {}
    for key, value in manifest.items():
        if key in ignored:
            continue
        if key in {"files", "artifacts"} and isinstance(value, list):
            normalized[key] = sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
        else:
            normalized[key] = value
    return normalized


def inspect_zip_candidate(
    path: Path,
    root: Path,
    tracked: set[str],
    current_suite_schema: str | None,
    supported_suite_schemas: set[str] | None = None,
    suite_schema_definitions: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Read ZIP members and return either a contract candidate or a non-contract ZIP."""

    relative = relative_path(path, root)
    filename_doc, filename_version, filename_suffix = filename_identity(path)
    zip_sha = sha256_file(path)
    base: dict[str, Any] = {
        "source_path": relative,
        "filename": path.name,
        "git_tracked": relative in tracked,
        "zip_sha256": zip_sha,
        "zip_size_bytes": path.stat().st_size,
        "members": [],
        "unexpected_members": [],
        "missing_required_artifacts": [],
        "validation": {"status": "INVALID", "errors": [], "warnings": []},
    }

    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            path_errors: list[str] = []
            raw_paths: list[str] = []
            for info in infos:
                normalized, error = safe_archive_path(info.filename)
                if error:
                    path_errors.append(error)
                    continue
                raw_paths.append(normalized or info.filename)
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    path_errors.append(f"ZIP member is a symbolic link: {info.filename}")
                if info.flag_bits & 0x1:
                    path_errors.append(f"ZIP member is encrypted: {info.filename}")

            prefix = common_archive_prefix(raw_paths)
            normalized_members: dict[str, dict[str, Any]] = {}
            json_records: list[dict[str, Any]] = []
            duplicate_paths: set[str] = set()
            for info in infos:
                safe_path, error = safe_archive_path(info.filename)
                if error or safe_path is None:
                    continue
                member_path = strip_archive_prefix(safe_path, prefix)
                payload = archive.read(info)
                member_record = {
                    "path": member_path,
                    "archive_path": info.filename,
                    "size_bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                }
                if member_path in normalized_members:
                    duplicate_paths.add(member_path)
                normalized_members[member_path] = member_record
                if member_path.lower().endswith(".json"):
                    parsed, json_error = extract_json(payload)
                    json_records.append(
                        {
                            "path": member_path,
                            "archive_path": info.filename,
                            "size_bytes": len(payload),
                            "sha256": member_record["sha256"],
                            "data": parsed,
                            "json_error": json_error,
                            "kind": artifact_kind(parsed, member_path),
                        }
                    )
            base["members"] = sorted(normalized_members.values(), key=lambda item: item["path"])
            contract_records = [item for item in json_records if item["kind"] == "contract"]
            gate_records = [item for item in json_records if item["kind"] == "test_gates"]
            manifest_records = [item for item in json_records if item["kind"] == "bundle_manifest"]

            # Older malformed bundles can still be recognized through a contract filename.
            if not contract_records:
                for item in json_records:
                    if "_contract" not in PurePosixPath(item["path"]).name.lower():
                        continue
                    if isinstance(item["data"], dict):
                        data = item["data"]
                        if data.get("doc_id") and data.get("version"):
                            item["kind"] = "contract"
                            contract_records.append(item)
                            break

            # Keep malformed JSON members in the candidate inventory when their
            # names identify a canonical contract artifact role.
            role_named_members = [
                PurePosixPath(item["path"]).name.lower()
                for item in json_records
            ]
            has_role_filename = any(
                name == "bundle.manifest.json"
                or "_contract" in name
                or "_test_gates" in name
                or "testgates" in name
                for name in role_named_members
            )

            # A ZIP is a bundle candidate when contents or artifact filenames
            # identify any required canonical role.
            is_candidate = bool(contract_records or gate_records or manifest_records or has_role_filename)
            if not is_candidate:
                return None, {
                    "path": relative,
                    "filename": path.name,
                    "git_tracked": relative in tracked,
                    "zip_sha256": zip_sha,
                    "zip_size_bytes": path.stat().st_size,
                    "member_count": len(infos),
                    "members": sorted(raw_paths),
                    "classification": "NON_CONTRACT",
                    "reason": "No contract, test-gates, or bundle-manifest artifact was found in ZIP contents.",
                }

            errors: list[str] = []
            warnings: list[str] = []
            doc_data = contract_records[0]["data"] if len(contract_records) == 1 else None
            gate_data = gate_records[0]["data"] if len(gate_records) == 1 else None
            manifest_data = manifest_records[0]["data"] if len(manifest_records) == 1 else None

            metadata_doc_id = doc_data.get("doc_id") if isinstance(doc_data, dict) else None
            metadata_version = doc_data.get("version") if isinstance(doc_data, dict) else None
            gate_ref = gate_data.get("contract_ref") if isinstance(gate_data, dict) else None
            gate_ref = gate_ref if isinstance(gate_ref, dict) else {}
            manifest_doc, manifest_version = (
                manifest_identity(manifest_data) if isinstance(manifest_data, dict) else (None, None)
            )
            doc_id = metadata_doc_id or manifest_doc or gate_ref.get("doc_id") or filename_doc
            version = metadata_version or manifest_version or gate_ref.get("version") or filename_version
            base.update({"doc_id": doc_id, "version": version})

            if not doc_id:
                errors.append("Contract identity could not be read from artifact contents or a bundle manifest.")
            if not version:
                errors.append("Contract version could not be read from artifact contents or a bundle manifest.")
            elif not SEMVER_RE.fullmatch(str(version)):
                errors.append(f"Contract version is not numeric semantic version: {version!r}.")
            if len(contract_records) != 1:
                errors.append(f"Expected exactly one contract artifact; found {len(contract_records)}.")
            if len(gate_records) != 1:
                errors.append(f"Expected exactly one test-gates artifact; found {len(gate_records)}.")
            if len(manifest_records) != 1:
                errors.append(f"Expected exactly one bundle manifest; found {len(manifest_records)}.")
            base["missing_required_artifacts"] = [
                name
                for name, records in (
                    ("contract", contract_records),
                    ("test_gates", gate_records),
                    ("bundle_manifest", manifest_records),
                )
                if not records
            ]
            errors.extend(path_errors)
            errors.extend(f"ZIP contains duplicate normalized member path: {name}" for name in sorted(duplicate_paths))
            canonical_payload_paths = {
                item["path"]
                for item in normalized_members.values()
                if PurePosixPath(item["path"]).name != "bundle.manifest.json"
            }
            recognized_payload_paths = {
                item["path"] for item in contract_records + gate_records
            }
            if len(canonical_payload_paths) != 2 or canonical_payload_paths != recognized_payload_paths:
                errors.append(
                    "Canonical three-artifact bundle must contain exactly one contract, one test-gates artifact, and one manifest; "
                    f"found {len(canonical_payload_paths)} non-manifest members."
                )

            if isinstance(doc_data, dict):
                if not doc_data.get("doc_id"):
                    errors.append("Contract artifact is missing doc_id.")
                if not doc_data.get("version"):
                    errors.append("Contract artifact is missing version.")
                if doc_data.get("doc_id") != doc_id:
                    errors.append(
                        f"Contract doc_id {doc_data.get('doc_id')!r} does not match resolved identity {doc_id!r}."
                    )
                if doc_data.get("version") != version:
                    errors.append(
                        f"Contract version {doc_data.get('version')!r} does not match resolved version {version!r}."
                    )
                if "artifact_kind" in doc_data and doc_data.get("artifact_kind") != "contract":
                    errors.append("Contract artifact_kind is not 'contract'.")

            if isinstance(gate_data, dict) and isinstance(doc_data, dict):
                reference = gate_data.get("contract_ref")
                if not isinstance(reference, dict):
                    errors.append("Test-gates artifact is missing contract_ref object.")
                else:
                    if reference.get("doc_id") != doc_data.get("doc_id"):
                        errors.append(
                            "Test-gates contract_ref.doc_id does not match contract doc_id."
                        )
                    if reference.get("version") != doc_data.get("version"):
                        errors.append(
                            "Test-gates contract_ref.version does not match contract version."
                        )
                if gate_data.get("version") != doc_data.get("version"):
                    errors.append("Test-gates version does not match contract version.")

            contract_suite = doc_data.get("suite_schema") if isinstance(doc_data, dict) else None
            gate_suite = gate_data.get("suite_schema") if isinstance(gate_data, dict) else None
            manifest_suite = manifest_data.get("suite_schema") if isinstance(manifest_data, dict) else None
            schemas = {value for value in (contract_suite, gate_suite, manifest_suite) if value is not None}
            if len(schemas) > 1:
                errors.append(
                    "Contract, test-gates, and manifest suite_schema values disagree: "
                    + ", ".join(sorted(str(item) for item in schemas))
                    + "."
                )
            if any(value is None for value in (contract_suite, gate_suite, manifest_suite)):
                errors.append("Contract, test-gates, and manifest must each declare suite_schema.")
            if current_suite_schema and schemas and schemas != {current_suite_schema}:
                historical_schema = next(iter(schemas)) if len(schemas) == 1 else None
                if historical_schema and historical_schema in (supported_suite_schemas or set()):
                    warnings.append(
                        f"Bundle uses supported historical suite schema {historical_schema}; current schema is {current_suite_schema}."
                    )
                else:
                    errors.append(
                        f"Bundle suite_schema {sorted(str(item) for item in schemas)!r} is neither current schema {current_suite_schema} nor a tracked compatible historical schema."
                    )

            if isinstance(doc_data, dict) and isinstance(gate_data, dict) and isinstance(manifest_data, dict):
                expected_schemas = (
                    ("contract", doc_data.get("schema_version")),
                    ("test_gates", gate_data.get("schema_version")),
                    ("bundle_manifest", manifest_data.get("schema_version")),
                )
                for role, declared in expected_schemas:
                    expected = REQUIRED_ARTIFACT_SCHEMAS[role]
                    if declared != expected:
                        errors.append(
                            f"{role} schema_version {declared!r} does not match {expected!r}."
                        )

                schema_reference = contract_suite
                definitions = (suite_schema_definitions or {}).get(str(schema_reference))
                if definitions:
                    if Draft202012Validator is None:
                        errors.append(
                            f"Cannot validate bundle against {schema_reference}: jsonschema is not installed."
                        )
                    else:
                        for role, data in (
                            ("contract", doc_data),
                            ("test_gates", gate_data),
                            ("bundle_manifest", manifest_data),
                        ):
                            schema = definitions.get(role)
                            if not isinstance(schema, dict):
                                errors.append(
                                    f"Tracked CS-0 {schema_reference} authority has no {role} JSON Schema."
                                )
                                continue
                            try:
                                Draft202012Validator.check_schema(schema)
                                schema_errors = sorted(
                                    Draft202012Validator(schema).iter_errors(data),
                                    key=lambda error: (list(error.absolute_path), error.message),
                                )
                            except SchemaError as error:
                                errors.append(
                                    f"Tracked CS-0 {schema_reference} {role} schema is invalid: {error.message}."
                                )
                                continue
                            for error in schema_errors:
                                pointer = "/" + "/".join(str(part) for part in error.absolute_path)
                                errors.append(
                                    f"{role} artifact violates {schema_reference} JSON Schema at {pointer}: {error.message}."
                                )

                for expected in gate_schema_expectations(gate_data):
                    if contract_suite and expected != contract_suite:
                        errors.append(
                            f"Test-gate suite_schema expectation {expected!r} does not match bundle suite_schema {contract_suite!r}."
                        )

            if isinstance(manifest_data, dict):
                manifest_files = manifest_data.get("files")
                if not isinstance(manifest_files, list):
                    errors.append("Canonical bundle manifest must declare a 'files' array.")
                    manifest_files = []
                manifest_identity_doc, manifest_identity_version = manifest_identity(manifest_data)
                if manifest_identity_doc != doc_id:
                    errors.append(
                        f"Manifest doc_id {manifest_identity_doc!r} does not match contract doc_id {doc_id!r}."
                    )
                if manifest_identity_version != version:
                    errors.append(
                        f"Manifest version {manifest_identity_version!r} does not match contract version {version!r}."
                    )
                manifest_doc_ids, manifest_versions = manifest_declared_identities(manifest_data)
                if len(manifest_doc_ids) > 1:
                    errors.append(
                        "Manifest identity fields disagree on doc_id: " + ", ".join(sorted(manifest_doc_ids)) + "."
                    )
                if manifest_doc_ids and manifest_doc_ids != {str(doc_id)}:
                    errors.append(
                        "Manifest declared doc_id values do not all match contract doc_id: "
                        + ", ".join(sorted(manifest_doc_ids))
                        + f" versus {doc_id}."
                    )
                if len(manifest_versions) > 1:
                    errors.append(
                        "Manifest identity fields disagree on version: " + ", ".join(sorted(manifest_versions)) + "."
                    )
                if manifest_versions and manifest_versions != {str(version)}:
                    errors.append(
                        "Manifest declared version values do not all match contract version: "
                        + ", ".join(sorted(manifest_versions))
                        + f" versus {version}."
                    )

                actual_payload_members = {
                    item["path"]: item
                    for item in normalized_members.values()
                    if PurePosixPath(item["path"]).name != "bundle.manifest.json"
                }
                if len(manifest_files) != len(actual_payload_members):
                    errors.append(
                        f"Manifest declares {len(manifest_files)} files, but the archive contains {len(actual_payload_members)} non-manifest files."
                    )
                declared_paths: set[str] = set()
                for entry in manifest_files:
                    if not isinstance(entry, dict):
                        errors.append("Manifest files array contains a non-object entry.")
                        continue
                    declared_path = entry.get("path")
                    if not isinstance(declared_path, str):
                        errors.append("Manifest file entry is missing a string path.")
                        continue
                    if PurePosixPath(declared_path).suffix.lower() != ".json":
                        errors.append(f"Canonical manifest may list only JSON artifacts: {declared_path}.")
                    normalized_path, path_error = safe_archive_path(declared_path)
                    if path_error or normalized_path is None:
                        errors.append(f"Unsafe manifest file path {declared_path!r}: {path_error}")
                        continue
                    normalized_path = strip_archive_prefix(normalized_path, prefix)
                    if normalized_path in declared_paths:
                        errors.append(f"Manifest lists the same artifact more than once: {normalized_path}.")
                    declared_paths.add(normalized_path)
                    actual = actual_payload_members.get(normalized_path)
                    if actual is None:
                        errors.append(f"Manifest lists missing archive member: {normalized_path}.")
                        continue
                    expected_sha = entry.get("sha256")
                    if expected_sha != actual["sha256"]:
                        errors.append(f"Manifest sha256 mismatch for {normalized_path}.")
                    expected_size = entry.get("bytes", entry.get("size"))
                    if expected_size != actual["size_bytes"]:
                        errors.append(f"Manifest size mismatch for {normalized_path}.")
                actual_paths = set(actual_payload_members)
                for extra in sorted(actual_paths - declared_paths):
                    base["unexpected_members"].append(extra)
                    errors.append(f"Archive contains unmanifested member: {extra}.")
                for absent in sorted(declared_paths - actual_paths):
                    if absent not in actual_paths:
                        base["unexpected_members"].append(absent)
                if manifest_data.get("doc_id") is None and not (
                    isinstance(manifest_data.get("bundle"), dict)
                    and manifest_data["bundle"].get("bundle_id")
                ):
                    warnings.append("Manifest uses a legacy identity shape without doc_id or bundle.bundle_id.")
                if "files" not in manifest_data and "artifacts" in manifest_data:
                    errors.append("Manifest uses the legacy 'artifacts' field instead of canonical 'files'.")

            # Internal artifact names and outer ZIP filenames are secondary evidence.
            for role, record, data in (
                ("contract", contract_records[0] if contract_records else None, doc_data),
                ("test-gates", gate_records[0] if gate_records else None, gate_data),
            ):
                if record and isinstance(data, dict):
                    declared_name = data.get("artifact_name") or data.get("artifact_filename")
                    if declared_name and PurePosixPath(str(declared_name)).name != PurePosixPath(record["path"]).name:
                        warnings.append(
                            f"{role} artifact name {declared_name!r} differs from archive member {record['path']!r}."
                        )
                    member_name = PurePosixPath(record["path"]).name
                    member_versions = VERSION_RE.findall(member_name)
                    if member_versions and str(data.get("version")) not in member_versions:
                        warnings.append(
                            f"{role} member filename version(s) {sorted(set(member_versions))!r} differ from internal version {data.get('version')!r}."
                        )
                    member_doc_ids = {value.upper() for value in DOC_ID_RE.findall(member_name)}
                    if member_doc_ids and doc_id not in member_doc_ids:
                        warnings.append(
                            f"{role} member filename doc_id(s) {sorted(member_doc_ids)!r} differ from internal doc_id {doc_id!r}."
                        )
            if filename_doc and doc_id and filename_doc != doc_id:
                warnings.append(
                    f"ZIP filename doc_id {filename_doc!r} differs from internal doc_id {doc_id!r}."
                )
            if filename_version and version and filename_version != version:
                warnings.append(
                    f"ZIP filename version {filename_version!r} differs from internal version {version!r}."
                )
            if filename_suffix:
                warnings.append(
                    f"ZIP filename suffix {filename_suffix!r} is legacy filename decoration; it does not define contract identity."
                )
            if not current_suite_schema:
                warnings.append("No current CS-0 schema declaration was found in the repository authority documents.")

            contract_members = [
                item for item in normalized_members.values()
                if PurePosixPath(item["path"]).name != "bundle.manifest.json"
            ]
            contract_members.sort(key=lambda item: item["path"])
            member_fingerprint = sha256_bytes(
                json.dumps(
                    [{"path": item["path"], "sha256": item["sha256"], "size_bytes": item["size_bytes"]} for item in contract_members],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            manifest_fingerprint = (
                sha256_bytes(
                    json.dumps(canonical_manifest_value(manifest_data), sort_keys=True, separators=(",", ":")).encode("utf-8")
                )
                if isinstance(manifest_data, dict)
                else None
            )
            effective_fingerprint = sha256_bytes(
                f"{member_fingerprint}:{manifest_fingerprint or 'missing'}".encode("utf-8")
            )

            base.update(
                {
                    "doc_id": doc_id,
                    "version": version,
                    "contract_artifact": artifact_record(contract_records[0]) if contract_records else None,
                    "test_gates_artifact": artifact_record(gate_records[0]) if gate_records else None,
                    "bundle_manifest": artifact_record(manifest_records[0]) if manifest_records else None,
                    "contract_metadata": summarized_contract_metadata(doc_data) if isinstance(doc_data, dict) else None,
                    "test_gates_metadata": summarize_gates(gate_data) if isinstance(gate_data, dict) else None,
                    "manifest_metadata": summarize_manifest(manifest_data) if isinstance(manifest_data, dict) else None,
                    "artifact_count": len(normalized_members),
                    "payload_artifact_count": len(contract_members),
                    "current_suite_schema": current_suite_schema,
                    "effective_payload_fingerprint": effective_fingerprint,
                    "canonical_artifacts_fingerprint": member_fingerprint,
                    "manifest_fingerprint": manifest_fingerprint,
                    "validation": {
                        "status": "INVALID" if errors else "VALID_WITH_WARNING" if warnings else "VALID",
                        "errors": sorted(set(errors)),
                        "warnings": sorted(set(warnings)),
                    },
                }
            )
            base["audit_status"] = base["validation"]["status"]
            base["lifecycle"] = (
                "rejected" if errors else "validated"
            )
            return base, None
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as error:
        if filename_doc or filename_version:
            base.update({"doc_id": filename_doc, "version": filename_version})
            base["validation"]["errors"] = [f"ZIP could not be inspected: {error}"]
            base["missing_required_artifacts"] = ["contract", "test_gates", "bundle_manifest"]
            return base, None
        return None, {
            "path": relative,
            "filename": path.name,
            "git_tracked": relative in tracked,
            "zip_sha256": zip_sha,
            "zip_size_bytes": path.stat().st_size,
            "member_count": 0,
            "members": [],
            "classification": "NON_CONTRACT",
            "reason": f"ZIP could not be inspected and its filename does not identify a bundle: {error}",
        }


def artifact_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": record["path"],
        "sha256": record["sha256"],
        "size_bytes": record["size_bytes"],
    }


def summarize_gates(data: dict[str, Any]) -> dict[str, Any]:
    reference = data.get("contract_ref")
    return {
        "doc_id": data.get("doc_id"),
        "version": data.get("version"),
        "artifact_name": data.get("artifact_name") or data.get("artifact_filename"),
        "schema_version": data.get("schema_version"),
        "suite_schema": data.get("suite_schema"),
        "contract_ref": reference,
        "gate_count": len(data.get("gates", [])) if isinstance(data.get("gates"), list) else None,
        "suite_schema_expectations": gate_schema_expectations(data),
    }


def summarize_manifest(data: dict[str, Any]) -> dict[str, Any]:
    doc_id, version = manifest_identity(data)
    listed = data.get("files")
    if not isinstance(listed, list):
        listed = data.get("artifacts") if isinstance(data.get("artifacts"), list) else []
    return {
        "doc_id": doc_id,
        "version": version,
        "bundle": data.get("bundle"),
        "schema_version": data.get("schema_version"),
        "suite_schema": data.get("suite_schema"),
        "declared_files": listed,
        "declared_file_count": len(listed),
    }


def current_suite_schema_evidence(
    root: Path,
    paths: Iterable[Path],
    index_claims: list[dict[str, Any]],
    tracked: set[str],
) -> dict[str, Any]:
    """Resolve the schema from an accepted CS-0 release or legacy index evidence."""

    index_paths = [path for path in paths if path.parent == root and path.name.startswith("CONTRACT_AUTHORITY_INDEX")]
    evidence: list[dict[str, str]] = []
    index_versions: set[str] = set()
    for path in sorted(index_paths):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if "CS-0@" not in line or "Under CS-0@" not in line:
                continue
            for version in SCHEMA_REFERENCE_RE.findall(line):
                index_versions.add(version)
                evidence.append(
                    {
                        "source_path": relative_path(path, root),
                        "line": str(line_number),
                        "claim": f"CS-0@{version}",
                        "excerpt": line.strip(),
                        "authority_level": "current_schema_declaration",
                    }
                )
    for claim in index_claims:
        if claim["doc_id"] != "CS-0" or not claim.get("git_tracked"):
            continue
        index_versions.add(claim["version"])
        evidence.append(
            {
                "source_path": claim["source_path"],
                "line": str(claim["line"]),
                "claim": f"CS-0@{claim['version']}",
                "excerpt": claim["excerpt"],
                "authority_level": "tracked_index_schema_version_claim",
            }
        )
    accepted_authority, accepted_error, accepted_recorded = _accepted_cs0_schema_authority(
        root, paths, tracked
    )
    historical_schemas = _tracked_historical_cs0_schemas(root, paths, tracked)
    if accepted_error:
        return {
            "selected_suite_schema": None,
            "claims": evidence,
            "conflicting_versions": sorted(index_versions),
            "overridden_advisory_versions": [],
            "accepted_schema_authority": accepted_recorded,
            "supported_historical_schemas": historical_schemas,
            "resolution_basis": "invalid accepted CS-0 schema authority record",
            "errors": [accepted_error],
            "status": "invalid",
        }

    if accepted_authority:
        schema = accepted_authority["suite_schema"]
        overridden_versions = sorted(index_versions - {schema.removeprefix("CS-0@")})
        evidence.append(
            {
                "source_path": accepted_authority["acceptance_record_path"],
                "line": "schema_validation_authority",
                "claim": schema,
                "excerpt": (
                    f"Accepted immutable CS-0@{accepted_authority['version']} bundle "
                    f"{accepted_authority['bundle_path']} ({accepted_authority['sha256']})."
                ),
                "authority_level": "accepted_release_schema_authority",
            }
        )
        status = "resolved"
        conflicting_versions: list[str] = []
        resolution_basis = "tracked owner-accepted CS-0 release hash; advisory index claims retained as provenance"
    else:
        versions = index_versions
        schema = f"CS-0@{next(iter(versions))}" if len(versions) == 1 else None
        overridden_versions = []
        conflicting_versions = sorted(versions) if len(versions) > 1 else []
        status = "resolved" if schema else "ambiguous" if len(versions) > 1 else "missing"
        resolution_basis = "tracked authority-index schema declaration"
    return {
        "selected_suite_schema": schema,
        "claims": evidence,
        "conflicting_versions": conflicting_versions,
        "overridden_advisory_versions": overridden_versions,
        "accepted_schema_authority": accepted_authority or accepted_recorded,
        "supported_historical_schemas": historical_schemas,
        "resolution_basis": resolution_basis,
        "status": status,
    }


def _tracked_historical_cs0_schemas(
    root: Path, paths: Iterable[Path], tracked: set[str]
) -> list[dict[str, str]]:
    """Find tracked CS-0 historical schema snapshots named by the ratified source model."""

    result: list[dict[str, str]] = []
    for path in sorted(paths):
        relative = relative_path(path, root)
        parts = PurePosixPath(relative).parts
        if (
            len(parts) != 5
            or parts[:3] != ("release-src", "ratification", "CS-0")
            or parts[4] != "contract.json"
            or relative not in tracked
        ):
            continue
        version = parts[3]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if (
            not isinstance(data, dict)
            or data.get("artifact_kind") != "contract"
            or data.get("doc_id") != "CS-0"
            or data.get("version") != version
            or data.get("suite_schema") != f"CS-0@{version}"
            or not isinstance(data.get("schemas"), dict)
        ):
            continue
        result.append({"suite_schema": f"CS-0@{version}", "source_path": relative})
    return sorted(result, key=lambda item: semver_sort_key(item["suite_schema"].split("@", 1)[1]))


def load_suite_schema_definitions(
    root: Path, schema_evidence: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Load schema families from the exact accepted and tracked historical CS-0 sources."""

    definitions: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    historical = schema_evidence.get("supported_historical_schemas", [])
    for source in historical:
        source_path = root / source["source_path"]
        try:
            contract = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append(f"Cannot load tracked historical CS-0 schema source {source['source_path']}: {error}.")
            continue
        schemas = contract.get("schemas") if isinstance(contract, dict) else None
        if isinstance(schemas, dict):
            definitions[source["suite_schema"]] = schemas
        else:
            errors.append(f"Tracked historical CS-0 source {source['source_path']} has no schema families.")

    accepted = schema_evidence.get("accepted_schema_authority")
    if isinstance(accepted, dict) and accepted.get("bundle_path"):
        bundle_path = str(accepted["bundle_path"])
        try:
            with zipfile.ZipFile(root / bundle_path, "r") as archive:
                contracts = []
                for member in archive.infolist():
                    if member.is_dir() or not member.filename.lower().endswith(".json"):
                        continue
                    data, parse_error = extract_json(archive.read(member))
                    if not parse_error and isinstance(data, dict) and data.get("artifact_kind") == "contract":
                        contracts.append(data)
        except (OSError, zipfile.BadZipFile, RuntimeError) as error:
            errors.append(f"Cannot load accepted CS-0 schema source {bundle_path}: {error}.")
        else:
            if len(contracts) != 1 or not isinstance(contracts[0].get("schemas"), dict):
                errors.append(f"Accepted CS-0 source {bundle_path} must contain one contract with schema families.")
            else:
                definitions[str(accepted["suite_schema"])] = contracts[0]["schemas"]
    return definitions, errors


def _accepted_cs0_schema_authority(
    root: Path, paths: Iterable[Path], tracked: set[str]
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any] | None]:
    """Verify the tracked acceptance record and read its exact CS-0 schema bundle."""

    record_path = "release-artifacts/accepted/acceptance.json"
    record_file = next((path for path in paths if relative_path(path, root) == record_path), None)
    if record_file is None:
        return None, None, None
    if record_path not in tracked:
        return None, "Acceptance registry is present but is not Git-tracked.", {"path": record_path}

    try:
        record = json.loads(record_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, f"Cannot read tracked acceptance registry: {error}.", {"path": record_path}
    if not isinstance(record, dict) or record.get("acceptance_status") != "ACCEPTED_RELEASE":
        return None, "Tracked acceptance registry has no ACCEPTED_RELEASE status.", {"path": record_path}

    authority = record.get("schema_validation_authority")
    if not isinstance(authority, dict) or authority.get("doc_id") != "CS-0":
        return None, "Tracked acceptance registry has no CS-0 schema_validation_authority record.", {"path": record_path}
    version = authority.get("version")
    bundle_path = authority.get("path")
    expected_hash = authority.get("sha256")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        return None, "Accepted CS-0 schema version is not numeric SemVer.", {"path": record_path}
    if not isinstance(bundle_path, str):
        return None, "Accepted CS-0 schema bundle path is missing.", {"path": record_path}
    normalized, path_error = safe_archive_path(bundle_path)
    if path_error or normalized != bundle_path or bundle_path not in tracked:
        return None, "Accepted CS-0 schema bundle path is unsafe or not Git-tracked.", {
            "path": record_path,
            "bundle_path": bundle_path,
        }
    bundle = root / bundle_path
    if not bundle.is_file():
        return None, "Accepted CS-0 schema bundle is missing from the worktree.", {
            "path": record_path,
            "bundle_path": bundle_path,
        }
    actual_hash = sha256_file(bundle)
    if not isinstance(expected_hash, str) or actual_hash != expected_hash:
        return None, "Accepted CS-0 schema bundle SHA-256 does not match its acceptance record.", {
            "path": record_path,
            "bundle_path": bundle_path,
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
        }
    releases = record.get("releases")
    matching_release = next(
        (
            item
            for item in releases
            if isinstance(item, dict)
            and item.get("doc_id") == "CS-0"
            and item.get("version") == version
            and item.get("path") == bundle_path
            and item.get("sha256") == expected_hash
            and item.get("status") == "ACCEPTED_RELEASE"
        ),
        None,
    ) if isinstance(releases, list) else None
    if matching_release is None:
        return None, "CS-0 schema authority does not match an accepted release record.", {
            "path": record_path,
            "bundle_path": bundle_path,
            "version": version,
        }

    contract_artifacts: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(bundle, "r") as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                normalized_member, member_error = safe_archive_path(member.filename)
                if member_error:
                    return None, f"Accepted CS-0 bundle contains unsafe path: {member_error}.", {
                        "path": record_path,
                        "bundle_path": bundle_path,
                    }
                if not normalized_member.lower().endswith(".json"):
                    continue
                data, error = extract_json(archive.read(member))
                if not error and isinstance(data, dict) and data.get("artifact_kind") == "contract":
                    contract_artifacts.append(data)
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        return None, f"Cannot inspect accepted CS-0 bundle: {error}.", {"path": record_path, "bundle_path": bundle_path}
    if len(contract_artifacts) != 1:
        return None, "Accepted CS-0 bundle must contain exactly one contract artifact.", {
            "path": record_path,
            "bundle_path": bundle_path,
            "contract_artifact_count": len(contract_artifacts),
        }
    contract = contract_artifacts[0]
    suite_schema = contract.get("suite_schema")
    if contract.get("doc_id") != "CS-0" or contract.get("version") != version:
        return None, "Accepted CS-0 bundle internal identity does not match the accepted release record.", {
            "path": record_path,
            "bundle_path": bundle_path,
            "version": version,
        }
    if suite_schema != f"CS-0@{version}":
        return None, "Accepted CS-0 bundle suite_schema does not match its own accepted version.", {
            "path": record_path,
            "bundle_path": bundle_path,
            "version": version,
            "suite_schema": suite_schema,
        }
    result = {
        "doc_id": "CS-0",
        "version": version,
        "bundle_path": bundle_path,
        "sha256": actual_hash,
        "suite_schema": suite_schema,
        "acceptance_record_path": record_path,
        "scope": authority.get("scope"),
    }
    return result, None, result


def accepted_release_claims(
    root: Path,
    paths: Iterable[Path],
    tracked: set[str],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Verify tracked owner-accepted exact hashes and return selection evidence."""

    record_path = "release-artifacts/accepted/acceptance.json"
    record_file = next((path for path in paths if relative_path(path, root) == record_path), None)
    if record_file is None or record_path not in tracked:
        return [], []
    try:
        record = json.loads(record_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [], [{"path": record_path, "error": f"Cannot parse acceptance registry: {error}."}]
    if not isinstance(record, dict) or record.get("acceptance_status") != "ACCEPTED_RELEASE":
        return [], [{"path": record_path, "error": "Acceptance registry status is not ACCEPTED_RELEASE."}]
    releases = record.get("releases")
    if not isinstance(releases, list):
        return [], [{"path": record_path, "error": "Acceptance registry releases must be an array."}]

    claims: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, release in enumerate(releases):
        if not isinstance(release, dict) or release.get("status") != "ACCEPTED_RELEASE":
            errors.append({"path": record_path, "index": index, "error": "Release row is malformed or not ACCEPTED_RELEASE."})
            continue
        doc_id = release.get("doc_id")
        version = release.get("version")
        bundle_path = release.get("path")
        expected_hash = release.get("sha256")
        normalized, path_error = safe_archive_path(bundle_path) if isinstance(bundle_path, str) else (None, "path is missing")
        if (
            not isinstance(doc_id, str)
            or not CONTRACT_DOC_ID_RE.fullmatch(doc_id)
            or not isinstance(version, str)
            or not SEMVER_RE.fullmatch(version)
            or not isinstance(expected_hash, str)
            or not re.fullmatch(r"[a-f0-9]{64}", expected_hash)
            or path_error
            or normalized != bundle_path
            or bundle_path not in tracked
        ):
            errors.append({"path": record_path, "index": index, "error": f"Accepted release row has invalid identity, hash, or tracked path: {release!r}."})
            continue
        bundle = root / bundle_path
        if not bundle.is_file():
            errors.append({"path": record_path, "index": index, "error": f"Accepted release artifact is missing: {bundle_path}."})
            continue
        actual_hash = sha256_file(bundle)
        actual_size = bundle.stat().st_size
        if actual_hash != expected_hash:
            errors.append({"path": record_path, "index": index, "error": f"Accepted release SHA-256 mismatch for {bundle_path}: expected {expected_hash}, got {actual_hash}."})
            continue
        if release.get("size_bytes") != actual_size:
            errors.append({"path": record_path, "index": index, "error": f"Accepted release size mismatch for {bundle_path}: expected {release.get('size_bytes')}, got {actual_size}."})
            continue
        exact_candidates = [
            candidate for candidate in candidates
            if candidate.get("doc_id") == doc_id
            and candidate.get("version") == version
            and candidate.get("source_path") == bundle_path
            and candidate.get("zip_sha256") == expected_hash
            and candidate["validation"]["status"] in {"VALID", "VALID_WITH_WARNING"}
        ]
        if not exact_candidates:
            errors.append({"path": record_path, "index": index, "error": f"Accepted release has no internally valid matching bundle candidate: {doc_id}@{version} {bundle_path}."})
            continue
        supersedes = release.get("supersedes")
        verified_supersedes: dict[str, Any] | None = None
        if supersedes is not None:
            if not isinstance(supersedes, dict):
                errors.append({"path": record_path, "index": index, "error": "Accepted release supersedes must be an object."})
                continue
            superseded_doc_id = supersedes.get("doc_id")
            superseded_version = supersedes.get("version")
            superseded_hash = supersedes.get("sha256")
            superseded_path = supersedes.get("path")
            normalized_superseded_path, superseded_path_error = (
                safe_archive_path(superseded_path)
                if isinstance(superseded_path, str)
                else (None, "path is missing")
            )
            if (
                superseded_doc_id != doc_id
                or not isinstance(superseded_version, str)
                or not SEMVER_RE.fullmatch(superseded_version)
                or not isinstance(superseded_hash, str)
                or not re.fullmatch(r"[a-f0-9]{64}", superseded_hash)
                or superseded_path_error
                or normalized_superseded_path != superseded_path
                or superseded_path not in tracked
            ):
                errors.append({"path": record_path, "index": index, "error": "Accepted release has a malformed or untracked supersedes identity."})
                continue
            predecessor_candidates = [
                candidate for candidate in candidates
                if candidate.get("doc_id") == superseded_doc_id
                and candidate.get("version") == superseded_version
                and candidate.get("source_path") == superseded_path
                and candidate.get("zip_sha256") == superseded_hash
            ]
            if len(predecessor_candidates) != 1:
                errors.append({"path": record_path, "index": index, "error": f"Accepted release supersedes link does not match one tracked predecessor candidate: {superseded_doc_id}@{superseded_version} {superseded_path}."})
                continue
            verified_supersedes = {
                "doc_id": superseded_doc_id,
                "version": superseded_version,
                "sha256": superseded_hash,
                "path": superseded_path,
                "predecessor_validation_status": predecessor_candidates[0]["validation"]["status"],
            }
        claims.append(
            {
                "doc_id": doc_id,
                "version": version,
                "source_path": record_path,
                "line": str(index),
                "authority_level": "accepted_release",
                "advisory_document": False,
                "git_tracked": True,
                "validated": True,
                "declared_zip_sha256": expected_hash,
                "matching_candidate_paths": [bundle_path],
                "excerpt": f"Owner-accepted immutable release {doc_id}@{version} with SHA-256 {expected_hash}.",
                **({"supersedes": verified_supersedes} if verified_supersedes else {}),
            }
        )
    return claims, errors


def canonical_bundle_format_evidence(
    root: Path, paths: Iterable[Path], candidates: list[dict[str, Any]], tracked: set[str]
) -> dict[str, Any]:
    """Record the checked-out CS-0/BP-0 evidence for the canonical bundle shape."""

    authority_lines: list[dict[str, Any]] = []
    for path in sorted(paths):
        if path.parent != root or not path.name.startswith("CONTRACT_AUTHORITY_INDEX"):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            lower = line.lower()
            if "canonical artifact families are" in lower or "canonical 3-artifact" in lower or "three-artifact law/proof/integrity" in lower:
                authority_lines.append(
                    {
                        "source_path": relative_path(path, root),
                        "line": line_number,
                        "excerpt": line.strip(),
                        "git_tracked": relative_path(path, root) in tracked,
                    }
                )
    standard_candidates = [
        {
            "doc_id": item.get("doc_id"),
            "version": item.get("version"),
            "source_path": item["source_path"],
            "git_tracked": item.get("git_tracked", False),
            "validation_status": item["validation"]["status"],
            "artifact_count": item.get("artifact_count"),
            "artifact_schema_versions": {
                "contract": (item.get("contract_metadata") or {}).get("schema_version"),
                "test_gates": (item.get("test_gates_metadata") or {}).get("schema_version"),
                "bundle_manifest": (item.get("manifest_metadata") or {}).get("schema_version"),
            },
            "zip_sha256": item["zip_sha256"],
        }
        for item in candidates
        if item.get("doc_id") in {"CS-0", "BP-0", "CG-0"}
    ]
    return {
        "expected_artifact_roles": ["contract", "test_gates", "bundle_manifest"],
        "required_artifact_count": 3,
        "authority_evidence": authority_lines,
        "standard_bundle_candidates": sorted(
            standard_candidates,
            key=lambda item: (str(item["doc_id"]), semver_sort_key(item.get("version")), item["source_path"]),
        ),
        "conclusion": (
            "The tracked authority index states the three-artifact model and CS-0 artifact families. "
            "Candidate inspection is reported separately and does not repair or override candidate defects."
            if authority_lines
            else "No tracked authority line confirming the canonical bundle shape was found."
        ),
    }


def extract_index_authority_claims(
    paths: Iterable[Path], root: Path, tracked: set[str]
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for path in sorted(paths):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        relative = relative_path(path, root)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        first = text[:6000].lower()
        advisory_document = "advisory" in first or "non-authoritative" in first
        if "index" not in path.name.lower() and "authority" not in path.name.lower() and "canon" not in path.name.lower():
            continue

        current_doc: str | None = None
        current_doc_version: str | None = None
        for line_number, line in enumerate(text.splitlines(), start=1):
            heading = re.match(
                r"^##\s+`?(?P<doc>[A-Z][A-Z0-9]*-\d+)`?"
                r"(?:\s|—|\b).*?(?:@\s*`?(?P<version>\d+\.\d+\.\d+)`?)?\s*$",
                line.strip(),
            )
            if heading:
                current_doc = heading.group("doc").upper()
                current_doc_version = heading.group("version")
                if current_doc_version:
                    claims.append(
                        authority_claim(
                            current_doc,
                            current_doc_version,
                            relative,
                            line_number,
                            "advisory_index_version",
                            line.strip(),
                            advisory_document,
                            relative in tracked,
                        )
                    )
            version_line = re.match(r"^\s*Version:\s*`?(\d+\.\d+\.\d+)`?,?\s*$", line, re.IGNORECASE)
            if version_line and current_doc and not current_doc_version:
                claims.append(
                    authority_claim(
                        current_doc,
                        version_line.group(1),
                        relative,
                        line_number,
                        "advisory_index_version",
                        line.strip(),
                        advisory_document,
                        relative in tracked,
                    )
                )

            # Keep explicit selection or pin statements, while ignoring general
            # prose that can mention gate IDs beside unrelated version numbers.
            direct_claim_patterns = (
                re.compile(
                    r"\b(?P<doc>[A-Z][A-Z0-9]*-\d+)\s+(?:canonical\s+pin|pinned\s+version|selected\s+(?:bundle|version)|current\s+authority)\s+v?(?P<version>\d+\.\d+\.\d+)",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(?P<doc>[A-Z][A-Z0-9]*-\d+)\s+v(?P<version>\d+\.\d+\.\d+)\s+(?:is\s+)?(?:the\s+)?(?:selected|current)\s+(?:bundle|version|authority)",
                    re.IGNORECASE,
                ),
            )
            for pattern in direct_claim_patterns:
                for match in pattern.finditer(line):
                    claims.append(
                        authority_claim(
                            match.group("doc").upper(),
                            match.group("version"),
                            relative,
                            line_number,
                            "advisory_index_current_reference",
                            line.strip(),
                            advisory_document,
                            relative in tracked,
                        )
                    )

    unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for claim in claims:
        key = (claim["doc_id"], claim["version"], claim["source_path"], claim["authority_level"])
        unique[key] = claim
    return list(unique.values())


def extract_unresolved_index_conflicts(
    paths: Iterable[Path], root: Path, known_doc_ids: set[str], tracked: set[str]
) -> list[dict[str, Any]]:
    """Capture open index issues that explicitly leave version supersession unresolved."""

    conflicts: list[dict[str, Any]] = []
    for path in sorted(paths):
        if path.parent != root or not path.name.startswith("CONTRACT_AUTHORITY_INDEX"):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            lower = line.lower()
            if "supersession review" not in lower or not re.search(r"\bopen\b", lower):
                continue
            mentioned_doc_ids = sorted(set(DOC_ID_RE.findall(line)) & known_doc_ids)
            if not mentioned_doc_ids:
                continue
            versions = sorted(set(VERSION_RE.findall(line)), key=semver_key)
            conflicts.append(
                {
                    "source_path": relative_path(path, root),
                    "line": line_number,
                    "doc_ids": mentioned_doc_ids,
                    "versions": versions,
                    "issue_type": "open_supersession_review",
                    "status": "open",
                    "authority_level": "advisory_index_unresolved_conflict",
                    "git_tracked": relative_path(path, root) in tracked,
                    "excerpt": line.strip(),
                }
            )
    unique: dict[tuple[str, tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
    for conflict in conflicts:
        key = (
            conflict["issue_type"],
            tuple(conflict["doc_ids"]),
            tuple(conflict["versions"]),
        )
        current = unique.get(key)
        if current is None or len(conflict["excerpt"]) > len(current["excerpt"]):
            unique[key] = conflict
    return list(unique.values())


def authority_claim(
    doc_id: str,
    version: str,
    source_path: str,
    line_number: int,
    authority_level: str,
    excerpt: str,
    advisory_document: bool,
    git_tracked: bool,
) -> dict[str, Any]:
    if advisory_document and authority_level == "explicit_canonical_pin":
        authority_level = "advisory_pin_claim"
    return {
        "doc_id": doc_id,
        "version": version,
        "source_path": source_path,
        "line": line_number,
        "authority_level": authority_level,
        "advisory_document": advisory_document,
        "git_tracked": git_tracked,
        "excerpt": excerpt,
        "validated": False,
    }


def canon_pin_claims(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("doc_id") != "CANON-1" or not isinstance(candidate.get("contract_metadata"), dict):
            continue
        contract_record = candidate.get("_contract_data")
        if not isinstance(contract_record, dict):
            continue
        source_valid = (
            candidate["validation"]["status"] in {"VALID", "VALID_WITH_WARNING"}
            and candidate.get("git_tracked", False)
        )
        pin_rows: list[dict[str, Any]] = []
        for field in ("pins", "canonical_bundles"):
            values = contract_record.get(field)
            if isinstance(values, list):
                pin_rows.extend(item for item in values if isinstance(item, dict))
        seen: set[tuple[str, str, str | None]] = set()
        for pin in pin_rows:
            doc_id = pin.get("doc_id")
            version = pin.get("version")
            if not doc_id or not version:
                continue
            declared_hash = pin.get("bundle_sha256")
            key = (str(doc_id), str(version), str(declared_hash) if declared_hash else None)
            if key in seen:
                continue
            seen.add(key)
            exact_candidates = [
                item for item in candidates
                if item.get("doc_id") == doc_id
                and item.get("version") == str(version)
                and declared_hash
                and item.get("zip_sha256") == declared_hash
                and item["validation"]["status"] in {"VALID", "VALID_WITH_WARNING"}
            ]
            validated = source_valid and bool(exact_candidates)
            if validated:
                reason = None
            elif not source_valid:
                reason = "The CANON-1 source bundle is untracked/ignored or failed current bundle validation."
            elif not declared_hash:
                reason = "The pin has no canonical ZIP SHA-256 value to verify against a candidate."
            elif not exact_candidates:
                reason = "No internally valid candidate ZIP matches the pinned version and SHA-256."
            else:
                reason = "The pin could not be validated against a canonical candidate."
            claims.append(
                {
                    "doc_id": str(doc_id),
                    "version": str(version),
                    "source_path": candidate["source_path"],
                    "authority_level": "validated_canon_pin" if validated else "unvalidated_canon_pin",
                    "advisory_document": False,
                    "excerpt": f"CANON-1 {candidate.get('version')} pin entry for {doc_id}@{version}.",
                    "declared_zip_sha256": declared_hash,
                    "matching_candidate_paths": [item["source_path"] for item in exact_candidates],
                    "validated": validated,
                    "source_candidate_status": candidate["validation"]["status"],
                    "source_candidate_version": candidate.get("version"),
                    "git_tracked": candidate.get("git_tracked", False),
                    "reason_unvalidated": reason,
                }
            )
    return claims


def duplicate_groups(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        if candidate["validation"]["status"] in {"VALID", "VALID_WITH_WARNING"}:
            groups[candidate.get("effective_payload_fingerprint", "")].append(candidate)
    duplicates: list[dict[str, Any]] = []
    conflicts: list[str] = []
    for fingerprint, group in groups.items():
        if len(group) < 2:
            continue
        zip_hashes = sorted({item["zip_sha256"] for item in group})
        duplicates.append(
            {
                "doc_id": group[0].get("doc_id"),
                "version": group[0].get("version"),
                "paths": sorted(item["source_path"] for item in group),
                "effective_payload_fingerprint": fingerprint,
                "canonical_artifacts_identical": len({item.get("canonical_artifacts_fingerprint") for item in group}) == 1,
                "manifest_payloads_equivalent": len({item.get("manifest_fingerprint") for item in group}) == 1,
                "payload_identical": True,
                "zip_sha256_values": zip_hashes,
                "zip_sha256_values_differ": len(zip_hashes) > 1,
                "zip_byte_identical": len(zip_hashes) == 1,
            }
        )
    by_version: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for candidate in candidates:
        if candidate["validation"]["status"] not in {"VALID", "VALID_WITH_WARNING"}:
            continue
        by_version[(str(candidate.get("doc_id")), str(candidate.get("version")))][
            str(candidate.get("effective_payload_fingerprint"))
        ].append(candidate)
    for (doc_id, version), payloads in by_version.items():
        if len(payloads) > 1:
            conflicts.append(
                f"{doc_id}@{version} has materially different validated bundle payloads with fingerprints: "
                + ", ".join(sorted(payloads))
                + "."
            )
    return duplicates, conflicts


def build_dependency_closure(
    contract_records: dict[str, dict[str, Any]],
    accepted_release_claims: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check minimum-version edges against selected or owner-accepted releases.

    The owner-ratified CS-0@3.0.1 source permits the dependencies property to be absent. When present,
    it must be an array whose entries include a valid doc_id, min_version,
    edge_type, and either reason or purpose. The edge type is constrained by
    the CS-0 P0 enum. These are structural checks; they do not infer new
    authority or change candidate bytes.

    If suite selection has no selected candidate, one unique validated
    accepted-release claim can resolve a dependency target. This does not
    change the target contract's suite selection status. Multiple accepted
    versions remain unresolved unless a candidate is selected.

    Minimum floors are compared only through ``min_version``. CS-0 rejects
    unknown dependency fields, including a generic ``version`` field, so this
    audit never assigns that field an exact-pin or range meaning.
    """

    accepted_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in accepted_release_claims or []:
        if (
            claim.get("authority_level") == "accepted_release"
            and claim.get("validated") is True
            and isinstance(claim.get("doc_id"), str)
            and isinstance(claim.get("version"), str)
            and SEMVER_RE.fullmatch(claim["version"])
            and isinstance(claim.get("declared_zip_sha256"), str)
            and re.fullmatch(r"[a-f0-9]{64}", claim["declared_zip_sha256"])
            and isinstance(claim.get("matching_candidate_paths"), list)
            and len(claim["matching_candidate_paths"]) == 1
        ):
            accepted_by_doc[claim["doc_id"]].append(claim)

    edges: list[dict[str, Any]] = []
    for referrer_doc_id, record in sorted(contract_records.items()):
        candidate = record.get("selected_candidate")
        if not candidate:
            continue
        metadata = candidate.get("contract_metadata") or {}
        dependencies = metadata.get("dependencies", [])
        if not isinstance(dependencies, list):
            edges.append(
                {
                    "referrer_doc_id": referrer_doc_id,
                    "referrer_version": record.get("selected_version"),
                    "referrer_source": candidate.get("source_path"),
                    "dependency_index": None,
                    "target_doc_id": None,
                    "constraint_type": "invalid_dependency_list",
                    "minimum_version": None,
                    "target_selected_version": None,
                    "target_status": "unresolved",
                    "status": "invalid_dependency_list",
                    "reason": "Contract dependencies must be represented as a list before version closure can be checked.",
                }
            )
            continue

        for dependency_index, dependency in enumerate(dependencies):
            if not isinstance(dependency, dict):
                edges.append(
                    {
                        "referrer_doc_id": referrer_doc_id,
                        "referrer_version": record.get("selected_version"),
                        "referrer_source": candidate.get("source_path"),
                        "dependency_index": dependency_index,
                        "target_doc_id": None,
                        "constraint_type": "invalid_dependency_record",
                        "minimum_version": None,
                        "target_selected_version": None,
                        "target_status": "unresolved",
                        "status": "invalid_dependency_record",
                        "reason": "Dependency entry is not a JSON object.",
                    }
                )
                continue

            target_doc_id = dependency.get("doc_id")
            minimum_version = dependency.get("min_version")
            missing_required_fields = sorted(
                {"doc_id", "min_version", "edge_type"} - dependency.keys()
            )
            invalid_fields: list[str] = []
            if "doc_id" in dependency and (
                not isinstance(target_doc_id, str)
                or not CONTRACT_DOC_ID_RE.fullmatch(target_doc_id)
            ):
                invalid_fields.append("doc_id")
            if "min_version" in dependency:
                if not isinstance(minimum_version, str):
                    invalid_fields.append("min_version")
                else:
                    try:
                        semver_key(minimum_version)
                    except ValueError:
                        invalid_fields.append("min_version")
            edge_type = dependency.get("edge_type")
            if "edge_type" in dependency and (
                not isinstance(edge_type, str) or edge_type not in CS0_DEPENDENCY_EDGE_TYPES
            ):
                invalid_fields.append("edge_type")
            if "reason" not in dependency and "purpose" not in dependency:
                # CS-0's oneOf accepts either field or both, but rejects neither.
                invalid_fields.append("reason_or_purpose")
            for descriptive_field in ("reason", "purpose"):
                if descriptive_field in dependency and (
                    not isinstance(dependency[descriptive_field], str)
                    or not dependency[descriptive_field]
                ):
                    invalid_fields.append(descriptive_field)
            artifact_pin = dependency.get("artifact_pin_sha256")
            if "artifact_pin_sha256" in dependency and (
                not isinstance(artifact_pin, str)
                or not re.fullmatch(r"[a-f0-9]{64}", artifact_pin)
            ):
                invalid_fields.append("artifact_pin_sha256")
            allowed_dependency_fields = {
                "artifact_pin_sha256",
                "doc_id",
                "edge_type",
                "min_version",
                "purpose",
                "reason",
            }
            unknown_fields = sorted(set(dependency) - allowed_dependency_fields)
            target_record = contract_records.get(str(target_doc_id)) if target_doc_id else None
            target_candidate = target_record.get("selected_candidate") if target_record else None
            target_version = target_record.get("selected_version") if target_record else None
            target_status = target_record.get("status") if target_record else "missing"
            target_resolution = "selected_candidate" if target_candidate else "unresolved"
            target_resolved_version = target_version if target_candidate else None
            target_source = target_candidate.get("source_path") if target_candidate else None
            target_resolved_versions = [target_version] if target_candidate and target_version else []
            target_accepted_releases: list[dict[str, Any]] = []
            target_available_accepted_versions: list[str] = []
            accepted_pin_mismatch = False
            if target_doc_id and not target_candidate:
                possible_accepted = accepted_by_doc.get(target_doc_id, [])
                accepted_hash_pin = dependency.get("artifact_pin_sha256")
                matching_accepted = [
                    claim for claim in possible_accepted
                    if accepted_hash_pin is None or accepted_hash_pin == claim["declared_zip_sha256"]
                ]
                accepted_pin_mismatch = bool(possible_accepted and not matching_accepted and accepted_hash_pin)
                if matching_accepted:
                    target_resolution = "accepted_release"
                    target_accepted_releases = sorted(
                        [
                            {
                                "version": claim["version"],
                                "sha256": claim["declared_zip_sha256"],
                                "source_path": claim["matching_candidate_paths"][0],
                            }
                            for claim in matching_accepted
                        ],
                        key=lambda item: semver_sort_key(item["version"]),
                    )
                    target_available_accepted_versions = [
                        item["version"] for item in target_accepted_releases
                    ]
                    if len(target_accepted_releases) == 1:
                        target_source = target_accepted_releases[0]["source_path"]
                elif accepted_pin_mismatch:
                    target_resolution = "accepted_release_pin_mismatch"
            edge = {
                "referrer_doc_id": referrer_doc_id,
                "referrer_version": record.get("selected_version"),
                "referrer_source": candidate.get("source_path"),
                "dependency_index": dependency_index,
                "target_doc_id": target_doc_id,
                "edge_type": dependency.get("edge_type"),
                "reason": dependency.get("reason"),
                "purpose": dependency.get("purpose"),
                "constraint_type": "minimum_version" if minimum_version is not None else "unspecified",
                "minimum_version": minimum_version,
                "target_selected_version": target_version,
                "target_resolved_version": target_resolved_version,
                "target_resolved_versions": target_resolved_versions,
                "target_available_accepted_versions": target_available_accepted_versions,
                "target_accepted_releases": target_accepted_releases,
                "target_status": target_status,
                "target_resolution": target_resolution,
                "target_source": target_source,
            }

            if missing_required_fields or invalid_fields or unknown_fields:
                edge["status"] = "invalid_dependency_record"
                edge["missing_required_fields"] = missing_required_fields
                edge["invalid_fields"] = sorted(set(invalid_fields))
                edge["unknown_fields"] = unknown_fields
                edge["closure_reason"] = (
                    "Dependency entry violates CS-0@3.0.1 structure: "
                    f"missing required fields={missing_required_fields}, "
                    f"invalid fields={sorted(set(invalid_fields))}, "
                    f"unknown fields={unknown_fields}."
                )
            elif minimum_version is None:
                # Do not interpret a generic `version` field as a minimum or
                # exact pin without a governing rule for that field.
                edge["status"] = "not_evaluated"
                edge["closure_reason"] = "No min_version was declared; constraint semantics are not inferred."
            elif not target_doc_id or (
                target_resolved_version is None and not target_accepted_releases
            ):
                edge["status"] = "target_unresolved"
                if accepted_pin_mismatch:
                    edge["closure_reason"] = (
                        f"No accepted {target_doc_id} release matches the declared artifact hash pin."
                    )
                else:
                    edge["closure_reason"] = (
                        "No deterministic validated selected or accepted target release is available for this dependency."
                    )
            else:
                try:
                    floor_key = semver_key(str(minimum_version))
                except ValueError:
                    edge["status"] = "invalid_minimum_version"
                    edge["closure_reason"] = "The declared minimum version is not numeric SemVer."
                else:
                    if target_resolution == "accepted_release":
                        compatible_releases = [
                            item for item in target_accepted_releases
                            if semver_key(item["version"]) >= floor_key
                        ]
                        edge["target_resolved_versions"] = [
                            item["version"] for item in compatible_releases
                        ]
                        edge["target_resolved_version"] = (
                            compatible_releases[0]["version"]
                            if len(compatible_releases) == 1
                            else None
                        )
                        if len(compatible_releases) == 1:
                            edge["target_source"] = compatible_releases[0]["source_path"]
                        if compatible_releases:
                            edge["status"] = "satisfied"
                            compatible_versions = ", ".join(
                                item["version"] for item in compatible_releases
                            )
                            edge["closure_reason"] = (
                                f"Accepted release version(s) {compatible_versions} for {target_doc_id} "
                                f"satisfy minimum {minimum_version}; suite selection remains {target_status}."
                            )
                        else:
                            edge["status"] = "below_minimum"
                            edge["closure_reason"] = (
                                f"Accepted {target_doc_id} version(s) "
                                f"{', '.join(target_available_accepted_versions)} are all below declared minimum {minimum_version}."
                            )
                    elif semver_key(str(target_resolved_version)) < floor_key:
                        edge["status"] = "below_minimum"
                        edge["closure_reason"] = (
                            f"Resolved target {target_doc_id}@{target_resolved_version} is below declared minimum {minimum_version}."
                        )
                    else:
                        edge["status"] = "satisfied"
                        release_kind = "selected target"
                        edge["closure_reason"] = (
                            f"{release_kind.capitalize()} {target_doc_id}@{target_resolved_version} satisfies minimum {minimum_version}."
                        )
            edges.append(edge)

    edges.sort(
        key=lambda item: (
            str(item.get("referrer_doc_id")),
            int(item.get("dependency_index") or 0),
            str(item.get("target_doc_id")),
        )
    )
    blocking_edges = [edge for edge in edges if edge.get("status") in DEPENDENCY_BLOCKING_STATUSES]
    return {
        "edge_count": len(edges),
        "declared_minimum_edge_count": sum(edge.get("minimum_version") is not None for edge in edges),
        "evaluated_minimum_edge_count": sum(edge.get("status") in {"satisfied", "below_minimum"} for edge in edges),
        "satisfied_edge_count": sum(edge.get("status") == "satisfied" for edge in edges),
        "accepted_release_resolved_edge_count": sum(
            edge.get("status") == "satisfied" and edge.get("target_resolution") == "accepted_release"
            for edge in edges
        ),
        "below_minimum_edge_count": sum(edge.get("status") == "below_minimum" for edge in edges),
        "unresolved_target_edge_count": sum(edge.get("status") == "target_unresolved" for edge in edges),
        "invalid_dependency_list_count": sum(edge.get("status") == "invalid_dependency_list" for edge in edges),
        "invalid_dependency_record_count": sum(edge.get("status") == "invalid_dependency_record" for edge in edges),
        "invalid_minimum_version_count": sum(edge.get("status") == "invalid_minimum_version" for edge in edges),
        "not_evaluated_edge_count": sum(edge.get("status") == "not_evaluated" for edge in edges),
        "blocking_edge_count": len(blocking_edges),
        "status": "blocked" if blocking_edges else "resolved",
        "rule_authority": {
            "schema_version": "CS-0@3.0.1",
            "status": "owner_ratified_successor_source_candidate",
            "schema_source": (
                "release-src/current/CS-0/3.0.1/contract.json"
                "#/schemas/contract/properties/dependencies"
            ),
            "gate_source": (
                "release-src/current/CS-0/3.0.1/test-gates.json"
                "#CS-0-P0-DEPENDENCY-EDGE-SEMANTICS"
            ),
            "owner_ratification": "reports/owner-ratification.json#decisions/D7",
            "limitation": (
                "The successor source is owner-ratified for dependency semantics but has not been released or "
                "selected by CANON-1. This rule validates dependency structure; it does not resolve suite membership."
            ),
        },
        "constraint_policy": (
            "The owner-ratified CS-0@3.0.1 dependency structure is checked when the optional dependencies array is present. "
            "Only explicit min_version fields are evaluated as lower bounds. Generic version fields are not "
            "assumed to be exact pins or ranges."
        ),
        "edges": edges,
    }


def resolve_contract(
    doc_id: str,
    candidates: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    duplicate_records: list[dict[str, Any]],
    content_conflicts: list[str],
    index_conflicts: list[dict[str, Any]],
    live_git_checkout: bool,
    suite_schema_status: str,
) -> dict[str, Any]:
    candidates = sorted(candidates, key=lambda item: item["source_path"])
    doc_claims = [claim for claim in claims if claim["doc_id"] == doc_id]
    selection_authority: str | None = None
    ambiguities: list[str] = [item for item in content_conflicts if item.startswith(f"{doc_id}@")]
    usable = [
        item for item in candidates
        if item["validation"]["status"] in {"VALID", "VALID_WITH_WARNING"}
    ]
    version_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in usable:
        version_groups[str(candidate["version"])].append(candidate)
    if usable and suite_schema_status != "resolved":
        ambiguities.append(
            f"Current CS-0 suite schema authority is {suite_schema_status}; canonical bundle eligibility cannot be finalized."
        )

    validated_pin_versions = {
        str(claim["version"])
        for claim in doc_claims
        if claim.get("authority_level") in {"explicit_canonical_pin", "validated_canon_pin"}
        and claim.get("validated", False)
        and (claim.get("git_tracked", False) or not live_git_checkout)
        and str(claim.get("version")) in version_groups
    }
    for conflict in index_conflicts:
        if doc_id not in conflict.get("doc_ids", []) or not conflict.get("git_tracked"):
            continue
        if (
            conflict.get("authority_level") == "advisory_index_unresolved_conflict"
            and len(validated_pin_versions) == 1
        ):
            # A validated, tracked CANON pin is higher authority than an
            # advisory index note. The note remains visible in the report,
            # but it cannot override the exact pinned release identity.
            continue
        conflicting_valid_versions = sorted(
            set(conflict.get("versions", [])) & set(version_groups), key=semver_key
        )
        if len(conflicting_valid_versions) > 1:
            ambiguities.append(
                f"Tracked authority index leaves supersession unresolved for {doc_id}: "
                + ", ".join(conflicting_valid_versions)
                + f" ({conflict['source_path']}:{conflict['line']})."
            )

    if ambiguities:
        status = "ambiguous"
        selected_version = None
        selected_candidate = None
        selection_basis: list[str] = []
    elif not usable:
        status = "invalid"
        selected_version = None
        selected_candidate = None
        selection_basis = []
        ambiguities.append("No candidate for this doc_id passed required structural and internal validation.")
    else:
        all_accepted_claims = [
            claim for claim in doc_claims
            if claim["authority_level"] == "accepted_release" and claim.get("validated", False)
        ]
        superseded_identities = {
            (
                claim["supersedes"]["doc_id"],
                claim["supersedes"]["version"],
                claim["supersedes"]["sha256"],
            )
            for claim in all_accepted_claims
            if isinstance(claim.get("supersedes"), dict)
        }
        accepted_claims = [
            claim for claim in all_accepted_claims
            if (
                claim["doc_id"], claim["version"], claim["declared_zip_sha256"]
            ) not in superseded_identities
        ]
        if all_accepted_claims and not accepted_claims:
            ambiguities.append(
                "Accepted release supersession links leave no current release head for this doc_id."
            )
        accepted_versions = sorted({claim["version"] for claim in accepted_claims}, key=semver_key)
        trusted_claims = [
            claim for claim in doc_claims
            if claim["authority_level"] in {"explicit_canonical_pin", "validated_canon_pin"}
            and claim.get("validated", False)
            and (claim.get("git_tracked", False) or not live_git_checkout)
        ] + accepted_claims
        current_claims = [
            claim for claim in doc_claims
            if claim["authority_level"] in {
                "explicit_canonical_pin",
                "validated_canon_pin",
                "advisory_index_current_reference",
                "advisory_index_version",
            } and (claim.get("git_tracked", False) or not live_git_checkout)
        ]
        if accepted_versions:
            # Advisory indexes help discovery but cannot override an exact,
            # hash-verified owner-accepted immutable release.
            current_claims = [
                claim for claim in current_claims
                if not claim.get("advisory_document", False)
            ] + accepted_claims
        claimed_versions = sorted({claim["version"] for claim in current_claims}, key=semver_key)
        all_valid_versions = sorted(version_groups, key=semver_key)
        highest_valid = all_valid_versions[-1]
        trusted_versions = sorted({claim["version"] for claim in trusted_claims}, key=semver_key)
        unavailable_claims = [claim for claim in current_claims if claim["version"] not in version_groups]

        if live_git_checkout and not claimed_versions and all(not item["git_tracked"] for item in usable):
            ambiguities.append(
                "All internally valid candidates exist only as untracked or ignored evidence, and no tracked current authority/index selects a version."
            )
        if len(claimed_versions) > 1:
            ambiguities.append(
                "Tracked current authority/index sources claim conflicting versions: "
                + ", ".join(claimed_versions)
                + "."
            )
        if len(trusted_versions) > 1:
            ambiguities.append(
                "Validated canonical pin sources disagree: " + ", ".join(trusted_versions) + "."
            )
        if unavailable_claims and usable:
            for claim in unavailable_claims:
                candidate_at_version = next(
                    (item for item in candidates if item.get("version") == claim["version"]),
                    None,
                )
                detail = (
                    "the matching candidate failed validation"
                    if candidate_at_version
                    else "no candidate ZIP for that version was found"
                )
                ambiguities.append(
                    f"Tracked index {claim['source_path']}:{claim.get('line', '?')} claims {doc_id}@{claim['version']}, but {detail}."
                )
        if trusted_versions and claimed_versions and set(trusted_versions) != set(claimed_versions):
            ambiguities.append(
                "Validated canonical pin and current index evidence disagree: "
                + f"pin {', '.join(trusted_versions)}; index {', '.join(claimed_versions)}."
            )

        if ambiguities:
            status = "ambiguous"
            selected_version = None
            selected_candidate = None
            selection_basis = []
        else:
            selected_version = (
                trusted_versions[0]
                if trusted_versions
                else claimed_versions[0]
                if claimed_versions
                else highest_valid
            )
            selection_authority = (
                "validated canonical pin" if any(claim["authority_level"] in {"explicit_canonical_pin", "validated_canon_pin"} for claim in trusted_claims)
                else "accepted immutable release successor" if any(claim.get("supersedes") for claim in accepted_claims)
                else "accepted immutable release" if accepted_versions
                else "current tracked index" if claimed_versions
                else "numeric semantic version fallback"
            )
            same_version = version_groups[selected_version]
            fingerprints = {item.get("effective_payload_fingerprint") for item in same_version}
            if len(fingerprints) > 1:
                status = "ambiguous"
                selected_candidate = None
                ambiguities.append(
                    f"Same doc_id/version {doc_id}@{selected_version} has materially different effective bundle contents."
                )
                selected_version = None
                selection_basis = []
            else:
                status = "selected"
                selected_candidate = sorted(
                    same_version,
                    key=lambda item: (not item["git_tracked"], item["zip_sha256"], item["source_path"]),
                )[0]
                selection_basis = []
                if trusted_claims:
                    if any(claim["authority_level"] == "accepted_release" for claim in trusted_claims):
                        successor_claim = next(
                            (claim for claim in accepted_claims if claim["version"] == selected_version and claim.get("supersedes")),
                            None,
                        )
                        if successor_claim:
                            predecessor = successor_claim["supersedes"]
                            selection_basis.append(
                                f"The exact hash-verified accepted release {selected_version} explicitly supersedes "
                                f"{predecessor['version']} at {predecessor['path']} ({predecessor['sha256']}); "
                                "this is a version-selection proposal, not CANON pinning."
                            )
                        else:
                            selection_basis.append(
                                f"An owner-accepted immutable release record matches the exact ZIP SHA-256 for version {selected_version}; this is a selection proposal, not CANON pinning."
                            )
                    if any(claim["authority_level"] in {"explicit_canonical_pin", "validated_canon_pin"} for claim in trusted_claims):
                        selection_basis.append(
                            f"Validated canonical pin evidence selects version {selected_version}."
                        )
                elif claimed_versions:
                    selection_basis.append(
                        f"Tracked current index evidence selects version {selected_version}; the bundle passed current structural validation, and a higher SemVer candidate does not override that evidence."
                    )
                else:
                    selection_basis.append(
                        f"No usable current pin or index version was found; {selected_version} is the highest numerically ordered version among internally valid candidates."
                    )
                if len(same_version) > 1:
                    selection_basis.append(
                        "Multiple ZIP representations have identical extracted payloads. A tracked path is the preferred locator; otherwise the ZIP digest/path only chooses a reproducible copy source and does not rank authority."
                    )
                if len(all_valid_versions) > 1:
                    selection_basis.append(
                        "Other candidates passed internal validation; authority evidence or numeric semantic version ordering determined the proposal."
                    )
                    if claimed_versions and selected_version != highest_valid:
                        selection_basis.append(
                            f"Higher internally valid version {highest_valid} was not selected because the tracked index selects {selected_version}."
                        )

    rejected: list[dict[str, Any]] = []
    duplicate_paths = {
        path
        for record in duplicate_records
        if record.get("doc_id") == doc_id
        for path in record.get("paths", [])
    }
    for candidate in candidates:
        if candidate["validation"]["status"] == "INVALID":
            candidate["audit_status"] = "INVALID"
            candidate["lifecycle"] = "rejected"
        elif status == "ambiguous":
            candidate["audit_status"] = "AMBIGUOUS"
            candidate["lifecycle"] = "ambiguous"
        else:
            candidate["audit_status"] = candidate["validation"]["status"]
        if selected_candidate and candidate["source_path"] == selected_candidate["source_path"]:
            candidate["resolution_outcome"] = "selected"
            candidate["lifecycle"] = "selected"
            continue
        if candidate["validation"]["status"] == "INVALID":
            reason = "; ".join(candidate["validation"]["errors"]) or "Candidate failed structural validation."
            outcome = "rejected"
        elif status == "ambiguous":
            reason = "; ".join(ambiguities) or "Candidate remains in an unresolved authority or same-version content conflict."
            outcome = "ambiguous"
            candidate["lifecycle"] = "ambiguous"
        elif candidate["source_path"] in duplicate_paths and candidate.get("version") == selected_version:
            reason = "Duplicate representation with identical canonical artifact payload and equivalent manifest."
            outcome = "duplicate_representation"
            candidate["lifecycle"] = "validated"
        elif selected_version and candidate.get("version") != selected_version:
            if selection_authority in {"validated canonical pin", "current tracked index"}:
                reason = f"Not selected because the {selection_authority} selects version {selected_version}; semantic version alone does not override it."
            elif semver_sort_key(candidate.get("version")) < semver_sort_key(selected_version):
                reason = f"Lower internally valid semantic version than selected version {selected_version}."
            else:
                reason = f"Higher semantic version candidate not selected because no higher-authority evidence supersedes the selected version {selected_version}."
            outcome = "rejected"
            candidate["lifecycle"] = "rejected"
        else:
            reason = f"Selected source is another equivalent representation of version {selected_version}."
            outcome = "duplicate_representation"
            candidate["lifecycle"] = "validated"
        candidate["resolution_outcome"] = outcome
        rejected.append({"source_path": candidate["source_path"], "version": candidate.get("version"), "reason": reason, "outcome": outcome})

    duplicates = [record for record in duplicate_records if record.get("doc_id") == doc_id]
    return {
        "doc_id": doc_id,
        "status": status,
        "lifecycle": "ambiguous" if status == "ambiguous" else "selected" if status == "selected" else "rejected",
        "selected_version": selected_version,
        "selected_source": selected_candidate["source_path"] if selected_candidate else None,
        "selected_candidate": selected_candidate,
        "selection_basis": selection_basis,
        "authority_evidence": doc_claims,
        "candidate_versions": sorted(version_groups, key=semver_key),
        "all_candidate_versions": sorted(
            {item.get("version") for item in candidates}, key=semver_sort_key
        ),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "rejected_candidates": rejected,
        "duplicate_representations": duplicates,
        "ambiguities": ambiguities,
    }


def extract_json_file(path: Path) -> tuple[Any | None, str | None, bytes]:
    payload = path.read_bytes()
    data, error = extract_json(payload)
    return data, error, payload


def discover_extracted_bundles(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    """Inspect existing extracted trees as parity evidence, never as authority."""

    json_artifact_files: dict[Path, list[tuple[Path, str, dict[str, Any], bytes]]] = defaultdict(list)
    for path in files:
        if relative_path(path, root).startswith("release-src/"):
            continue
        if path.suffix.lower() != ".json":
            continue
        try:
            data, error, payload = extract_json_file(path)
        except OSError:
            continue
        if error or not isinstance(data, dict):
            continue
        kind = artifact_kind(data, path.name)
        if kind:
            json_artifact_files[path.parent].append((path, kind, data, payload))

    records: list[dict[str, Any]] = []
    for directory, artifacts in sorted(json_artifact_files.items(), key=lambda item: relative_path(item[0], root)):
        by_kind: dict[str, list[tuple[Path, str, dict[str, Any], bytes]]] = defaultdict(list)
        for item in artifacts:
            by_kind[item[1]].append(item)
        contracts = by_kind.get("contract", [])
        gates = by_kind.get("test_gates", [])
        manifests = by_kind.get("bundle_manifest", [])
        if not (contracts or gates or manifests):
            continue
        contract_data = contracts[0][2] if len(contracts) == 1 else {}
        gate_data = gates[0][2] if len(gates) == 1 else {}
        manifest_data = manifests[0][2] if len(manifests) == 1 else {}
        doc_id = contract_data.get("doc_id") or manifest_identity(manifest_data)[0]
        version = contract_data.get("version") or manifest_identity(manifest_data)[1]
        member_records: list[dict[str, Any]] = []
        for path in files:
            try:
                path.relative_to(directory)
            except ValueError:
                continue
            try:
                member_records.append(
                    {
                        "path": path.relative_to(directory).as_posix(),
                        "size_bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
            except OSError:
                continue
        fingerprint = sha256_bytes(
            json.dumps(sorted(member_records, key=lambda item: item["path"]), sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        records.append(
            {
                "path": relative_path(directory, root),
                "doc_id": doc_id,
                "version": version,
                "artifact_count": len(member_records),
                "contract_path": relative_path(contracts[0][0], root) if contracts else None,
                "contract_sha256": sha256_bytes(contracts[0][3]) if contracts else None,
                "test_gates_path": relative_path(gates[0][0], root) if gates else None,
                "test_gates_sha256": sha256_bytes(gates[0][3]) if gates else None,
                "manifest_path": relative_path(manifests[0][0], root) if manifests else None,
                "manifest_sha256": sha256_bytes(manifests[0][3]) if manifests else None,
                "members": sorted(member_records, key=lambda item: item["path"]),
                "payload_fingerprint": fingerprint,
                "authority": "evidence_only_existing_extracted_copy",
                "selection_note": "Existing extracted content never selects contract authority; a fresh copy must be regenerated from the selected ZIP in Phase 2.",
                "validation": "VALID_SHAPE" if contracts and gates and manifests else "INCOMPLETE_EXTRACTED_COPY",
            }
        )
    return records


def extracted_parity(extracted: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [
        item for item in candidates
        if item.get("doc_id") == extracted.get("doc_id") and item.get("version") == extracted.get("version")
    ]
    if not matches:
        return {"status": "no_matching_zip_candidate", "matching_zip_paths": [], "differences": []}
    for candidate in matches:
        archive_members = {
            item["path"]: (item["size_bytes"], item["sha256"])
            for item in candidate.get("members", [])
        }
        extracted_members = {
            item["path"]: (item["size_bytes"], item["sha256"])
            for item in extracted.get("members", [])
        }
        missing = sorted(set(archive_members) - set(extracted_members))
        extra = sorted(set(extracted_members) - set(archive_members))
        different = sorted(
            path for path in set(archive_members) & set(extracted_members)
            if archive_members[path] != extracted_members[path]
        )
        if not missing and not extra and not different:
            return {
                "status": "match",
                "matching_zip_paths": [candidate["source_path"]],
                "differences": [],
            }
    return {
        "status": "mismatch",
        "matching_zip_paths": [item["source_path"] for item in matches],
        "differences": [{"path": extracted["path"], "missing": missing, "extra": extra, "different": different}],
    }


def classify_file(path: Path, root: Path, extracted_roots: set[str], zip_classes: dict[str, str]) -> str:
    relative = relative_path(path, root)
    lower = relative.lower()
    if lower.startswith("release-src/"):
        return "contract_release_source"
    if path.suffix.lower() == ".zip":
        return zip_classes.get(relative, "non_contract_zip")
    if ".staging/" in f"{lower}/" or lower.startswith(".staging/"):
        if path.suffix.lower() in {".md", ".txt"}:
            return "historical_or_staged_planning_document"
        if path.suffix.lower() in {".py", ".js", ".exs", ".yml", ".yaml"}:
            return "staged_utility_or_configuration"
    if any(relative == item or relative.startswith(item + "/") for item in extracted_roots):
        return "extracted_contract_artifact_or_support_file"
    if lower.startswith("ticketing-contracts/extracted/"):
        return "extracted_support_material"
    name = path.name.lower()
    if "index" in name and path.suffix.lower() in {".md", ".json", ".csv"}:
        if "selection" in name:
            return "contract_selection_index"
        if "canonical" in name and "pin" in name:
            return "canonical_pinning_index"
        if "authority" in name:
            return "contract_authority_index"
        if "ticketing-platform/" in lower or "/planning/" in lower:
            return "planning_document"
        return "contract_index_or_catalog"
    if path.suffix.lower() in {".py", ".js", ".sh", ".exs"}:
        return "utility_script"
    if path.suffix.lower() in {".gz", ".tar", ".tgz"}:
        return "support_archive"
    if path.suffix.lower() in {".md", ".txt"}:
        if any(term in lower for term in ("planning", "vertical_slice", "tracer_bullet", "feature_plan", "master_suite")):
            return "planning_document"
        if any(term in name for term in ("v42", "tb-000", "governance", "authority")):
            return "governance_document"
        return "documentation"
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("artifact_kind") in {"contract", "test_gates", "bundle_manifest"}:
                return "loose_contract_artifact"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        return "data_or_inventory_file"
    if path.name in {".gitattributes", ".gitignore"} or ".github/" in relative:
        return "repository_configuration"
    return "unknown_unclassified"


def document_fields(path: Path, root: Path, tracked: set[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    prefix = "\n".join(text.splitlines()[:100])
    declared: dict[str, str] = {}
    for line in prefix.splitlines():
        normalized_line = line.strip().lstrip("> ").strip()
        normalized_line = normalized_line.strip("*").strip()
        if ":" not in normalized_line:
            continue
        label, value = normalized_line.split(":", 1)
        key = re.sub(r"[^a-z]", "", label.lower())
        if key not in {"documentid", "version", "canonical", "supersedes", "status"}:
            continue
        value = value.strip()
        value = re.sub(r"^\*+\s*|\s*\*+$", "", value).strip()
        value = value.strip("`").strip()
        if key == "version" and not re.fullmatch(r"\d+(?:\.\d+){1,2}", value):
            continue
        if value:
            declared.setdefault(key, value)
    filename_version_match = re.search(
        r"(?:^|_)v(?P<version>\d+(?:\.\d+){1,2})(?:_|$)", path.stem, re.IGNORECASE
    )
    relative = relative_path(path, root)
    lower = relative.lower()
    content_lower = text[:6000].lower()
    filename_lower = path.name.lower()
    planning = any(
        item in lower
        for item in ("ticketing-platform", "planning", "vertical_slice", "master suite", "master_suite", "tracer_bullet")
    )
    if (
        "contract selection index" in content_lower
        or "contract authority index" in content_lower
        or ("contract" in filename_lower and "index" in filename_lower)
        or ("canonical" in filename_lower and "pin" in filename_lower and "index" in filename_lower)
    ):
        classification = "contract_index"
    elif "tb-000" in filename_lower:
        classification = "governance_document"
    elif planning:
        classification = "planning_document"
    elif any(item in filename_lower for item in ("v42", "governance")):
        classification = "governance_document"
    else:
        classification = "documentation"
    non_authoritative = any(
        phrase in content_lower
        for phrase in (
            "non-authoritative over contract bundles",
            "not a contract artifact",
            "not a source of new platform law",
            "not a replacement for the actual contract bundles",
            "advisory planning index",
            "this index is advisory",
        )
    )
    declared_canonical = declared.get("canonical", "").lower() == "true" if "canonical" in declared else None
    family_stem = re.sub(r"_v\d+(?:\.\d+){1,2}$", "", path.stem, flags=re.IGNORECASE)
    identity = declared.get("documentid") or ("TB-000" if "tb-000" in filename_lower else family_stem)
    return {
        "path": relative,
        "git_tracked": relative in tracked,
        "document_identity": identity,
        "version": declared.get("version") or (
            filename_version_match.group("version") if filename_version_match else None
        ),
        "declared_canonical": declared_canonical,
        "declared_status": declared.get("status"),
        "supersedes": declared.get("supersedes"),
        "authority_level": "non_authoritative" if non_authoritative else "declared_canonical" if declared_canonical else "not_declared",
        "classification": classification,
        "belongs_to_live_working_tree": relative in tracked,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def analyze_governance(paths: list[Path], root: Path, tracked: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    documents = [document_fields(path, root, tracked) for path in paths if path.suffix.lower() in {".md", ".txt"}]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in documents:
        if item["classification"] == "governance_document":
            grouped[item["document_identity"]].append(item)
    duplicates: list[dict[str, Any]] = []
    for identity, group in sorted(grouped.items()):
        versions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in group:
            versions[str(item["version"] or "unknown")].append(item)
        if len(versions) < 2 and not any(len(version_group) > 1 for version_group in versions.values()):
            continue
        duplicates.append(
            {
                "document_identity": identity,
                "versions": [
                    {
                        "version": version,
                        "paths": sorted(item["path"] for item in version_group),
                        "identical_bytes": len({item["sha256"] for item in version_group}) == 1,
                        "canonical_declarations": [item["path"] for item in version_group if item["declared_canonical"] is True],
                        "supersedes_declarations": sorted(
                            {item["supersedes"] for item in version_group if item["supersedes"]}
                        ),
                    }
                    for version, version_group in sorted(versions.items(), key=lambda pair: semver_sort_key(pair[0]))
                ],
                "authority_ordering": "explicit declarations are shown as evidence; filename or version ordering alone does not establish authority",
            }
        )
    return documents, duplicates


def build_cleanup_plan(
    candidates: list[dict[str, Any]],
    contract_records: dict[str, dict[str, Any]],
    extracted: list[dict[str, Any]],
    non_contract_zips: list[dict[str, Any]],
    files: list[Path],
    root: Path,
    tracked: set[str],
    governance_docs: list[dict[str, Any]],
    dependency_closure: dict[str, Any],
) -> dict[str, Any]:
    moves: list[dict[str, Any]] = []
    additions: list[dict[str, Any]] = []
    deletions: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    preserve_untracked: list[dict[str, Any]] = []
    extracted_roots = {item["path"] for item in extracted}
    selected_sources = {
        item["selected_source"]: (doc_id, item["selected_version"])
        for doc_id, item in contract_records.items()
        if item.get("status") == "selected" and item.get("selected_source")
    }
    for candidate in candidates:
        source = candidate["source_path"]
        doc_id = candidate.get("doc_id")
        if not candidate.get("git_tracked"):
            preserve_untracked.append(
                {
                    "path": source,
                    "reason": "Ignored or untracked ZIP evidence is not preserved by the audited Git commit; do not remove it as part of the Git-history cleanup until separately archived or reviewed.",
                }
            )
            if source in selected_sources:
                selected_doc, version = selected_sources[source]
                additions.append(
                    {
                        "source": source,
                        "target": f"contracts/{selected_doc}/{selected_doc}_bundle_v{version}.zip",
                        "reason": "Validated selected source exists only as ignored/untracked evidence; copy its bytes into the canonical tree and retain the original evidence source.",
                    }
                )
            continue
        record = contract_records.get(str(doc_id), {})
        if record.get("status") in {"ambiguous", "invalid"}:
            blocked.append({"path": source, "doc_id": doc_id, "reason": f"{doc_id} has no resolved canonical candidate."})
            continue
        if source in selected_sources:
            selected_doc, version = selected_sources[source]
            target = f"contracts/{selected_doc}/{selected_doc}_bundle_v{version}.zip"
            if source != target:
                moves.append({"source": source, "target": target, "reason": "Selected source ZIP; preserve its bytes and normalize only the outer repository path/name."})
        else:
            selection_reason = next(
                (item["reason"] for item in record.get("rejected_candidates", []) if item["source_path"] == source),
                "Rejected or duplicate candidate after evidence-based selection.",
            )
            deletions.append({"path": source, "reason": selection_reason})

    for item in extracted:
        doc_id = item.get("doc_id")
        if not item.get("git_tracked", True):
            preserve_untracked.append(
                {
                    "path": item["path"],
                    "reason": "Existing extracted evidence is ignored or untracked; retain until source and Git-history treatment is reviewed.",
                }
            )
            continue
        record = contract_records.get(str(doc_id), {})
        if record.get("status") in {"ambiguous", "invalid"}:
            blocked.append({"path": item["path"], "doc_id": doc_id, "reason": f"{doc_id} has no resolved canonical candidate."})
        else:
            deletions.append(
                {
                    "path": item["path"],
                    "reason": "Existing extracted copy is evidence only; remove and regenerate directly from the selected ZIP.",
                }
            )

    for archive in non_contract_zips:
        source = archive["path"]
        if not archive.get("git_tracked"):
            preserve_untracked.append({"path": source, "reason": "Untracked non-contract support archive; keep pending an explicit support-asset placement decision."})
        else:
            archive_name = Path(source).name
            archive_family = Path(source).stem
            moves.append({"source": source, "target": f"tools/support/{archive_family}/{archive_name}", "reason": "ZIP contents identify support tooling, not a contract bundle; preserve the archive in a support namespace."})

    for item in governance_docs:
        source = item["path"]
        if not item["git_tracked"] or item["classification"] == "documentation":
            continue
        if item["classification"] == "planning_document" and not source.startswith("planning/"):
            moves.append({"source": source, "target": "planning/" + source, "reason": "Planning material belongs outside the contract authority tree; preserve its source-relative path to avoid collisions."})
        elif item["classification"] == "governance_document" and not source.startswith("governance/"):
            moves.append({"source": source, "target": "governance/" + source, "reason": "Governance document belongs in the governance namespace; preserve its source-relative path."})
        elif item["classification"] == "contract_index" and not source.startswith(("governance/", "planning/")):
            target_root = "planning" if "selection" in source.lower() else "governance"
            moves.append({"source": source, "target": f"{target_root}/{source}", "reason": "Contract index belongs outside the contract artifact tree; its authority level remains explicit in the report."})
        elif item["classification"] == "contract_index" and not source.startswith(("governance/", "planning/")):
            target_root = "planning" if "selection" in source.lower() else "governance"
            moves.append({"source": source, "target": f"{target_root}/{source}", "reason": "Contract index belongs outside the contract artifact tree; its advisory or authority status remains explicit in the report."})

    for path in files:
        source = relative_path(path, root)
        if not source.startswith("ticketing-contracts/") or source.endswith(".zip"):
            continue
        if source in tracked:
            classification = classify_file(path, root, extracted_roots, {})
            if classification == "extracted_support_material":
                relative_support_path = source.split("ticketing-contracts/extracted/", 1)[1]
                target = "tools/support/" + relative_support_path
                reason = "These extracted files are a support runner, not a contract bundle; place them beside their support archive."
            elif classification == "utility_script":
                target = "tools/" + source
                reason = "Repository support script belongs in tools/."
            elif classification in {"contract_index_or_catalog", "contract_authority_index", "contract_selection_index", "canonical_pinning_index"}:
                target_root = "planning" if "selection" in classification else "governance"
                target = f"{target_root}/{source}"
                reason = "Index content belongs outside contract artifact directories; its authority level remains explicit in the report."
            elif classification == "data_or_inventory_file" and "/contracts/inventory/" in source:
                target = "reports/inventory/" + Path(source).name
                reason = "The raw bundle inventory is evidence, not contract law; retain it under reports."
            else:
                continue
            if source != target and not any(move.get("source") == source for move in moves):
                moves.append({"source": source, "target": target, "reason": reason})

    canonical_governance = [
        item for item in governance_docs
        if item["classification"] == "governance_document" and item["declared_canonical"] is True
    ]
    for canonical in canonical_governance:
        superseded_version = str(canonical.get("supersedes") or "").lstrip("vV")
        if not superseded_version:
            continue
        for older in governance_docs:
            if (
                older["git_tracked"]
                and older["classification"] == "governance_document"
                and older["document_identity"] == canonical["document_identity"]
                and older["version"] == superseded_version
            ):
                deletions.append(
                    {
                        "path": older["path"],
                        "reason": f"{canonical['path']} declares Canonical: true and Supersedes: {canonical['supersedes']}.",
                    }
                )

    deleted_paths = {item["path"] for item in deletions}
    moves = [item for item in moves if item["source"] not in deleted_paths]
    unique_moves: dict[tuple[str, str], dict[str, Any]] = {}
    for item in moves:
        unique_moves[(item["source"], item["target"])] = item
    unique_deletions: dict[str, dict[str, Any]] = {}
    for item in deletions:
        existing = unique_deletions.get(item["path"])
        if existing is None:
            unique_deletions[item["path"]] = item
        elif item["reason"] not in existing["reason"]:
            existing["reason"] += " Also: " + item["reason"]

    dependency_blockers = [
        {
            "referrer_doc_id": edge["referrer_doc_id"],
            "referrer_version": edge.get("referrer_version"),
            "target_doc_id": edge.get("target_doc_id"),
            "minimum_version": edge.get("minimum_version"),
            "status": edge["status"],
            "reason": edge.get("closure_reason"),
            "source_paths": [
                path for path in [edge.get("referrer_source"), edge.get("target_source")] if path
            ],
        }
        for edge in dependency_closure["edges"]
        if edge.get("status") in DEPENDENCY_BLOCKING_STATUSES
    ]
    return {
        "phase_2_status": (
            "blocked"
            if any(item.get("status") in {"ambiguous", "invalid"} for item in contract_records.values())
            or dependency_blockers
            else "eligible_for_review_only"
        ),
        "proposed_moves": sorted(unique_moves.values(), key=lambda item: item["source"]),
        "proposed_additions": sorted(additions, key=lambda item: item["target"]),
        "proposed_deletions": sorted(unique_deletions.values(), key=lambda item: item["path"]),
        "deferred_due_to_contract_blockers": sorted(blocked, key=lambda item: item["path"]),
        "dependency_blockers": dependency_blockers,
        "untracked_or_ignored_evidence_to_preserve": sorted(preserve_untracked, key=lambda item: item["path"]),
        "notes": [
            "This plan is evidence only and performs no move or deletion.",
            "A pre-cleanup recovery tag cannot preserve ignored .staging content because Git does not track it.",
            "Phase 2 must stop for every doc_id listed in deferred_due_to_contract_blockers.",
            "Phase 2 must also stop while dependency_blockers is non-empty.",
            "Selected ZIP bytes remain unchanged; extracted trees are regenerated from those ZIPs.",
        ],
    }


def build_inventory(
    files: list[Path],
    root: Path,
    tracked: set[str],
    extracted: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    non_contract_zips: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    extracted_roots = {item["path"] for item in extracted}
    zip_classes: dict[str, str] = {
        item["source_path"]: "canonical_contract_candidate" for item in candidates
    }
    zip_classes.update({item["path"]: "non_contract_zip" for item in non_contract_zips})
    inventory: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown: list[str] = []
    for path in files:
        category = classify_file(path, root, extracted_roots, zip_classes)
        record = {
            "path": relative_path(path, root),
            "size_bytes": path.stat().st_size,
            "git_tracked": relative_path(path, root) in tracked,
        }
        inventory[category].append(record)
        if category == "unknown_unclassified":
            unknown.append(record["path"])
    return {key: sorted(value, key=lambda item: item["path"]) for key, value in sorted(inventory.items())}, sorted(unknown)


def collect_canon_pin_validation(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Check old CANON bundle hashes against archive bytes and artifact payloads."""

    results: list[dict[str, Any]] = []
    for canon in candidates:
        if canon.get("doc_id") != "CANON-1" or not isinstance(canon.get("_contract_data"), dict):
            continue
        entries = canon["_contract_data"].get("canonical_bundles", [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("doc_id") or not entry.get("version"):
                continue
            matching = [
                item for item in candidates
                if item.get("doc_id") == entry.get("doc_id") and item.get("version") == entry.get("version")
            ]
            required_hash = entry.get("bundle_sha256")
            exact = [item for item in matching if required_hash and item.get("zip_sha256") == required_hash]
            artifact_entries = entry.get("artifacts", [])
            expected_artifacts = {
                PurePosixPath(str(item.get("path", ""))).name: (item.get("sha256"), item.get("size", item.get("bytes")))
                for item in artifact_entries if isinstance(item, dict)
            } if isinstance(artifact_entries, list) else {}
            artifact_matches = []
            for candidate in matching:
                actual = {
                    PurePosixPath(item["path"]).name: (item["sha256"], item["size_bytes"])
                    for item in candidate.get("members", [])
                }
                if expected_artifacts and all(actual.get(name) == value for name, value in expected_artifacts.items()):
                    artifact_matches.append(candidate["source_path"])
            if exact:
                pin_status = "bundle_hash_match"
            elif artifact_matches:
                pin_status = "artifact_hashes_match_but_zip_hash_differs"
            elif not matching:
                pin_status = "pinned_candidate_absent"
            else:
                pin_status = "hash_mismatch"
            if canon["validation"]["status"] not in {"VALID", "VALID_WITH_WARNING"}:
                reason = "CANON-1 failed bundle validation; its pin is not usable as authority."
            elif pin_status == "bundle_hash_match":
                reason = "The validated CANON bundle's exact ZIP SHA-256 matches the tracked candidate."
            elif pin_status == "artifact_hashes_match_but_zip_hash_differs":
                reason = "Pinned artifact payload hashes match, but the exact ZIP SHA-256 differs; the pin is not usable as immutable release authority."
            elif pin_status == "pinned_candidate_absent":
                reason = "No tracked candidate exists for the pinned doc_id and version."
            else:
                reason = "A tracked candidate exists for the pinned doc_id and version, but its exact ZIP and artifact hashes do not match."
            results.append(
                {
                    "canon_source_path": canon["source_path"],
                    "canon_version": canon.get("version"),
                    "canon_validation_status": canon["validation"]["status"],
                    "doc_id": entry.get("doc_id"),
                    "version": entry.get("version"),
                    "declared_zip_sha256": required_hash,
                    "matching_candidate_paths": [item["source_path"] for item in matching],
                    "exact_zip_hash_paths": [item["source_path"] for item in exact],
                    "artifact_hash_match_paths": artifact_matches,
                    "status": pin_status,
                    "authority_usable": canon["validation"]["status"] in {"VALID", "VALID_WITH_WARNING"} and bool(exact),
                    "reason": reason,
                }
            )
    return sorted(results, key=lambda item: (item["doc_id"], item["version"], item["canon_source_path"]))


def audit_repository(root: Path, *, scan_mode: str = "forensic") -> dict[str, Any]:
    """Perform a complete read-only inventory, validation, and authority audit."""

    root = root.resolve()
    if scan_mode == "canonical":
        files, tracked, missing_tracked = canonical_workspace_files(root)
    elif scan_mode == "forensic":
        files = workspace_files(root)
        tracked = tracked_paths(root)
        missing_tracked = []
    else:
        raise ValueError(f"unknown audit scan mode: {scan_mode!r}")
    git_head = None
    branch = None
    try:
        git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        pass

    index_claims = extract_index_authority_claims(files, root, tracked)
    schema_evidence = current_suite_schema_evidence(root, files, index_claims, tracked)
    current_schema = schema_evidence["selected_suite_schema"]
    supported_suite_schemas = {
        str(item["suite_schema"])
        for item in schema_evidence.get("supported_historical_schemas", [])
    }
    schema_definitions, schema_definition_errors = load_suite_schema_definitions(
        root, schema_evidence
    )
    if current_schema:
        supported_suite_schemas.add(str(current_schema))
    zip_paths = [path for path in files if path.suffix.lower() == ".zip"]
    candidates: list[dict[str, Any]] = []
    non_contract_zips: list[dict[str, Any]] = []
    for path in zip_paths:
        candidate, non_contract = inspect_zip_candidate(
            path,
            root,
            tracked,
            current_schema,
            supported_suite_schemas,
            schema_definitions,
        )
        if candidate:
            candidate["_contract_data"] = None
            # Keep the original structured contract only in memory for pin extraction.
            try:
                with zipfile.ZipFile(path, "r") as archive:
                    for member in archive.infolist():
                        if member.is_dir() or not member.filename.lower().endswith(".json"):
                            continue
                        data, error = extract_json(archive.read(member))
                        if not error and isinstance(data, dict) and data.get("artifact_kind") == "contract":
                            candidate["_contract_data"] = data
                            break
            except (OSError, zipfile.BadZipFile, RuntimeError):
                pass
            candidates.append(candidate)
        elif non_contract:
            non_contract_zips.append(non_contract)
    candidates.sort(key=lambda item: item["source_path"])
    non_contract_zips.sort(key=lambda item: item["path"])

    duplicates, content_conflicts = duplicate_groups(candidates)
    canon_claims = canon_pin_claims(candidates)
    accepted_claims, accepted_release_errors = accepted_release_claims(
        root, files, tracked, candidates
    )
    authority_claims = index_claims + canon_claims + accepted_claims

    candidates_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        if candidate.get("doc_id"):
            candidates_by_doc[str(candidate["doc_id"])].append(candidate)
    authority_doc_ids = {claim["doc_id"] for claim in authority_claims}
    all_doc_ids = sorted(set(candidates_by_doc) | authority_doc_ids)
    authority_only_doc_ids = sorted(authority_doc_ids - set(candidates_by_doc))
    index_conflicts = extract_unresolved_index_conflicts(
        files, root, set(candidates_by_doc), tracked
    )
    live_git_checkout = git_head is not None
    contract_records = {
        doc_id: resolve_contract(
            doc_id,
            candidates_by_doc.get(doc_id, []),
            authority_claims,
            duplicates,
            content_conflicts,
            index_conflicts,
            live_git_checkout,
            schema_evidence["status"],
        )
        for doc_id in all_doc_ids
    }
    # Internal raw JSON is never emitted into the machine report.
    for candidate in candidates:
        candidate.pop("_contract_data", None)

    dependency_closure = build_dependency_closure(contract_records, accepted_claims)

    extracted = discover_extracted_bundles(root, files)
    for item in extracted:
        item["git_tracked"] = any(
            tracked_path == item["path"] or tracked_path.startswith(item["path"] + "/")
            for tracked_path in tracked
        )
        item["zip_parity"] = extracted_parity(item, candidates)

    governance_documents, governance_duplicates = analyze_governance(files, root, tracked)
    inventory, unclassified = build_inventory(files, root, tracked, extracted, candidates, non_contract_zips)
    non_contract_mixed = [
        item["path"]
        for category, rows in inventory.items()
        if category not in {"canonical_contract_candidate", "extracted_contract_artifact_or_support_file"}
        for item in rows
        if item["path"].startswith("ticketing-contracts/")
    ]
    canon_validation = collect_canon_pin_validation(
        _restore_canon_raw_data(root, candidates)
    )
    cleanup = build_cleanup_plan(
        candidates,
        contract_records,
        extracted,
        non_contract_zips,
        files,
        root,
        tracked,
        governance_documents,
        dependency_closure,
    )

    status_counts = defaultdict(int)
    for record in contract_records.values():
        status_counts[record["status"]] += 1
    invalid_candidate_count = sum(item["validation"]["status"] == "INVALID" for item in candidates)
    summary = {
        "repository_root": str(root),
        "scan_mode": scan_mode,
        "audited_git_commit": git_head,
        "audited_branch": branch,
        "working_tree_file_count": len(files),
        "git_tracked_file_count": len(tracked),
        "missing_tracked_file_count": len(missing_tracked),
        "missing_tracked_paths": missing_tracked,
        "untracked_or_ignored_file_count": sum(
            1 for path in files if relative_path(path, root) not in tracked
        ),
        "zip_files_inspected": len(zip_paths),
        "contract_bundle_candidates": len(candidates),
        "unique_contract_doc_ids": len(candidates_by_doc),
        "authority_only_doc_id_count": len(authority_only_doc_ids),
        "authority_only_doc_ids": authority_only_doc_ids,
        "contract_resolution_doc_id_count": len(all_doc_ids),
        "selected_doc_ids": status_counts["selected"],
        "invalid_doc_ids": status_counts["invalid"],
        "ambiguous_doc_ids": status_counts["ambiguous"],
        "invalid_candidate_count": invalid_candidate_count,
        "accepted_release_count": len(accepted_claims),
        "accepted_release_integrity_error_count": len(accepted_release_errors),
        "schema_definition_error_count": len(schema_definition_errors),
        "non_contract_zip_count": len(non_contract_zips),
        "existing_extracted_bundle_count": len(extracted),
        "governance_document_count": len(governance_documents),
        "governance_duplicate_group_count": len(governance_duplicates),
        "unclassified_file_count": len(unclassified),
        "dependency_edge_count": dependency_closure["edge_count"],
        "dependency_edge_invalid_count": (
            dependency_closure["invalid_dependency_list_count"]
            + dependency_closure["invalid_dependency_record_count"]
        ),
        "dependency_floor_conflict_count": dependency_closure["below_minimum_edge_count"],
        "dependency_target_unresolved_count": dependency_closure["unresolved_target_edge_count"],
        "dependency_closure_blocker_count": dependency_closure["blocking_edge_count"],
        "phase_2_blocked": (
            cleanup["phase_2_status"] == "blocked"
            or schema_evidence["status"] != "resolved"
            or dependency_closure["status"] != "resolved"
            or bool(missing_tracked)
            or bool(accepted_release_errors)
            or bool(schema_definition_errors)
        ),
    }
    blockers = []
    for doc_id, record in contract_records.items():
        if record["status"] in {"ambiguous", "invalid"}:
            blockers.append(
                {
                    "doc_id": doc_id,
                    "status": record["status"],
                    "reasons": record["ambiguities"],
                    "candidate_paths": [item["source_path"] for item in record["candidates"]],
                }
            )
    if schema_evidence["status"] != "resolved":
        blockers.append(
            {
                "doc_id": None,
                "status": "ambiguous",
                "reasons": [f"Current CS-0 schema declaration status is {schema_evidence['status']}.", *schema_evidence["conflicting_versions"]],
                "candidate_paths": [],
            }
        )
    if missing_tracked:
        blockers.append(
            {
                "doc_id": None,
                "status": "missing_tracked_files",
                "reasons": ["Canonical audit could not read tracked repository paths from the worktree."],
                "candidate_paths": missing_tracked,
            }
        )
    for error in accepted_release_errors:
        blockers.append(
            {
                "doc_id": None,
                "status": "accepted_release_integrity_error",
                "reasons": [error["error"]],
                "candidate_paths": [error["path"]],
            }
        )
    for error in schema_definition_errors:
        blockers.append(
            {
                "doc_id": "CS-0",
                "status": "schema_authority_error",
                "reasons": [error],
                "candidate_paths": [],
            }
        )
    for edge in dependency_closure["edges"]:
        if edge["status"] not in DEPENDENCY_BLOCKING_STATUSES:
            continue
        blockers.append(
            {
                "doc_id": edge["referrer_doc_id"],
                "status": "dependency_unresolved",
                "reasons": [edge.get("closure_reason", "Dependency closure could not be established.")],
                "candidate_paths": [
                    path
                    for path in [edge.get("referrer_source"), edge.get("target_source")]
                    if path
                ],
                "target_doc_id": edge.get("target_doc_id"),
                "minimum_version": edge.get("minimum_version"),
                "target_selected_version": edge.get("target_selected_version"),
            }
        )

    return {
        "report_format_version": 1,
        "lifecycle_model": {
            "states": ["candidate", "validated", "selected", "canonical", "superseded", "rejected", "ambiguous"],
            "transitions": [
                {"from": "candidate", "to": "validated", "guard": "structural and internal validation succeeds"},
                {"from": "validated", "to": "selected", "guard": "authority resolution is deterministic"},
                {"from": "selected", "to": "canonical", "guard": "repository reconciliation succeeds"},
                {"from": "canonical", "to": "superseded", "guard": "a replacement is validated and selected"},
                {"from": "candidate", "to": "rejected", "guard": "required validation fails"},
                {"from": "candidate", "to": "ambiguous", "guard": "authority evidence cannot distinguish valid candidates"},
                {"from": "ambiguous", "to": "selected", "guard": "later evidence resolves authority"},
                {"from": "ambiguous", "to": "rejected", "guard": "later evidence rejects the candidates"},
            ],
            "phase_1_note": "selected means a deterministic proposal only; Phase 1 does not promote any version to canonical or supersede live files.",
        },
        "audit_scope": {
            "mode": scan_mode,
            "includes_ignored_and_untracked_files": scan_mode == "forensic",
            "authority_source": "Git index tracked paths" if scan_mode == "canonical" else "current workspace filesystem",
            "missing_tracked_paths": missing_tracked,
            "excludes": [
                ".git/",
                "__pycache__/",
                ".pytest_cache/",
                "reports/contract-reconciliation.json",
                "reports/contract-reconciliation.md",
            ],
            "selection_uses_file_timestamps": False,
            "selection_uses_git_chronology": False,
            "selection_uses_filename_order": False,
            "existing_extracted_directories_are_authority": False,
        },
        "summary": summary,
        "current_suite_schema_evidence": schema_evidence,
        "suite_schema_definitions": {
            "available_versions": sorted(schema_definitions),
            "load_errors": schema_definition_errors,
        },
        "canonical_bundle_format_evidence": canonical_bundle_format_evidence(
            root, files, candidates, tracked
        ),
        "authority_sources": {
            "index_claims": index_claims,
            "unresolved_index_conflicts": index_conflicts,
            "canon_internal_pin_claims": canon_claims,
            "canon_bundle_pin_validation": canon_validation,
            "accepted_release_claims": accepted_claims,
            "accepted_release_errors": accepted_release_errors,
            "selection_policy": [
                "Validate contract, gates, manifest, member hashes/sizes, schema declarations, and gate schema assertions before version resolution.",
                "Use only validated candidate versions for selection.",
                "Treat a pin or explicit current index version that conflicts with another valid authority claim as ambiguous.",
                "Use numeric semantic version ordering only when no usable higher-authority claim distinguishes candidates.",
                "Check explicit dependency min_version values against selected validated target candidates after per-doc authority resolution.",
                "Do not infer exact pins, ranges, or compatibility semantics from generic dependency version fields.",
                "Never use commit date, file mtime, directory order, or filename order to choose a contract version.",
            ],
        },
        "contracts": contract_records,
        "dependency_closure": dependency_closure,
        "all_contract_candidates": candidates,
        "non_contract_zips": non_contract_zips,
        "existing_extracted_bundles": extracted,
        "repository_inventory": inventory,
        "unclassified_files": unclassified,
        "non_contract_files_in_contract_directories": sorted(non_contract_mixed),
        "governance_documents": governance_documents,
        "governance_duplicate_candidates": governance_duplicates,
        "cleanup_plan": cleanup,
        "blockers_and_ambiguities": blockers,
    }


def _restore_canon_raw_data(root: Path, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reload CANON contracts for hash-pin checks after public data was sanitized."""

    restored = list(candidates)
    for candidate in restored:
        if candidate.get("doc_id") != "CANON-1":
            continue
        path = root / candidate["source_path"]
        try:
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    if member.is_dir() or not member.filename.lower().endswith(".json"):
                        continue
                    data, error = extract_json(archive.read(member))
                    if not error and isinstance(data, dict) and data.get("artifact_kind") == "contract":
                        candidate["_contract_data"] = data
                        break
        except (OSError, zipfile.BadZipFile, RuntimeError):
            continue
    return restored


def build_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Contract reconciliation report",
        "",
        f"- Audited commit: `{summary['audited_git_commit'] or 'unavailable'}`",
        f"- Branch: `{summary['audited_branch'] or 'unavailable'}`",
        f"- ZIPs inspected: {summary['zip_files_inspected']}",
        f"- Contract bundle candidates: {summary['contract_bundle_candidates']}",
        f"- Non-contract ZIPs: {summary['non_contract_zip_count']}",
        f"- Unique contract doc_ids: {summary['unique_contract_doc_ids']}",
        f"- Selected: {summary['selected_doc_ids']}",
        f"- Invalid doc_ids: {summary['invalid_doc_ids']}",
        f"- Ambiguous doc_ids: {summary['ambiguous_doc_ids']}",
        f"- Dependency floors: {summary['dependency_floor_conflict_count']} below minimum; {summary['dependency_target_unresolved_count']} unresolved target(s)",
        f"- Invalid candidates: {summary['invalid_candidate_count']}",
        f"- Existing extracted bundle copies: {summary['existing_extracted_bundle_count']}",
        f"- Phase 2 blocked: {str(summary['phase_2_blocked']).lower()}",
        "",
        "## Current suite schema",
        "",
    ]
    schema = report["current_suite_schema_evidence"]
    lines.append(f"- Status: `{schema['status']}`")
    lines.append(f"- Selected schema: `{schema['selected_suite_schema']}`")
    for evidence in schema["claims"]:
        lines.append(f"- Evidence: `{evidence['source_path']}:{evidence['line']}` states `{evidence['claim']}`.")
    dependency_closure = report["dependency_closure"]
    lines.extend(["", "## Dependency closure", ""])
    lines.append(
        f"- Status: `{dependency_closure['status']}`; declared minimums: "
        f"{dependency_closure['declared_minimum_edge_count']}; numeric comparisons completed: "
        f"{dependency_closure['evaluated_minimum_edge_count']}; blocking edges: "
        f"{dependency_closure['blocking_edge_count']}."
    )
    dependency_authority = dependency_closure["rule_authority"]
    lines.append(
        f"- Rule authority: `{dependency_authority['schema_version']}` "
        f"(`{dependency_authority['status']}`); schema `{dependency_authority['schema_source']}`; "
        f"gate `{dependency_authority['gate_source']}`."
    )
    lines.append(f"- Authority limitation: {dependency_authority['limitation']}")
    lines.append(f"- Constraint policy: {dependency_closure['constraint_policy']}")
    for edge in dependency_closure["edges"]:
        if edge["status"] not in DEPENDENCY_BLOCKING_STATUSES:
            continue
        lines.append(
            f"- `{edge['referrer_doc_id']}@{edge['referrer_version']}` -> "
            f"`{edge.get('target_doc_id')}` minimum `{edge.get('minimum_version')}`: "
            f"{edge.get('closure_reason')}"
        )
    shape = report["canonical_bundle_format_evidence"]
    lines.extend(["", "## Canonical bundle shape evidence", ""])
    lines.append(f"- Required roles: {', '.join(f'`{item}`' for item in shape['expected_artifact_roles'])}.")
    lines.append(f"- Authority conclusion: {shape['conclusion']}")
    for evidence in shape["authority_evidence"]:
        lines.append(f"- `{evidence['source_path']}:{evidence['line']}`: {evidence['excerpt']}")
    for candidate in shape["standard_bundle_candidates"]:
        lines.append(
            f"- `{candidate['doc_id']}@{candidate['version']}` at `{candidate['source_path']}`: "
            f"{candidate['validation_status']}, {candidate['artifact_count']} ZIP members, "
            f"tracked `{str(candidate['git_tracked']).lower()}`."
        )
    lifecycle = report["lifecycle_model"]
    lines.extend(["", "## Lifecycle states", ""])
    lines.append(f"- States: {', '.join(f'`{state}`' for state in lifecycle['states'])}.")
    lines.append(f"- {lifecycle['phase_1_note']}")
    for transition in lifecycle["transitions"]:
        lines.append(f"- `{transition['from']} -> {transition['to']}` when {transition['guard']}.")

    lines.extend(["", "## Contract resolutions", ""])
    for doc_id, record in report["contracts"].items():
        lines.extend([f"### {doc_id}", ""])
        if record["selected_candidate"]:
            selected = record["selected_candidate"]
            lines.extend(
                [
                    "Selected proposal:",
                    f"- version: `{record['selected_version']}`",
                    f"- source: `{record['selected_source']}`",
                    f"- ZIP SHA-256: `{selected['zip_sha256']}`",
                    f"- ZIP size: {selected['zip_size_bytes']} bytes",
                    f"- contract artifact: `{selected['contract_artifact']['path'] if selected['contract_artifact'] else 'missing'}`",
                    f"- contract artifact SHA-256: `{selected['contract_artifact']['sha256'] if selected['contract_artifact'] else 'missing'}`",
                    f"- test gates: `{selected['test_gates_artifact']['path'] if selected['test_gates_artifact'] else 'missing'}`",
                    f"- test gates SHA-256: `{selected['test_gates_artifact']['sha256'] if selected['test_gates_artifact'] else 'missing'}`",
                    f"- gate contract_ref: `{(selected['test_gates_metadata'] or {}).get('contract_ref')}`",
                    f"- manifest: `{selected['bundle_manifest']['path'] if selected['bundle_manifest'] else 'missing'}`",
                    f"- manifest SHA-256: `{selected['bundle_manifest']['sha256'] if selected['bundle_manifest'] else 'missing'}`",
                    f"- suite schema: `{selected['contract_metadata']['suite_schema'] if selected['contract_metadata'] else 'unknown'}`",
                    "",
                    "Selection basis:",
                ]
            )
            lines.extend(f"- {reason}" for reason in record["selection_basis"])
        else:
            lines.append(f"Resolution status: `{record['status']}`")
        if record["authority_evidence"]:
            lines.extend(["", "Authority evidence:"])
            for evidence in record["authority_evidence"]:
                lines.append(
                    f"- `{evidence['source_path']}`: {evidence['authority_level']} for `{evidence['version']}`. "
                    f"{evidence['excerpt']}"
                )
        if record["ambiguities"]:
            lines.extend(["", "Conflicts:"])
            lines.extend(f"- {item}" for item in record["ambiguities"])
        if record["rejected_candidates"]:
            lines.extend(["", "Rejected or duplicate candidates:"])
            for item in record["rejected_candidates"]:
                lines.append(f"- `{item['source_path']}` ({item['version']}): {item['reason']}")
        if record["duplicate_representations"]:
            lines.extend(["", "Duplicate representations:"])
            for duplicate in record["duplicate_representations"]:
                lines.append(
                    "- "
                    + ", ".join(f"`{path}`" for path in duplicate["paths"])
                    + f". Extracted payloads identical: `{str(duplicate['payload_identical']).lower()}`; "
                    + f"ZIP hashes differ: `{str(duplicate['zip_sha256_values_differ']).lower()}`."
                )
        lines.extend(["", "Candidate validation detail:"])
        for candidate in record["candidates"]:
            contract_metadata = candidate.get("contract_metadata") or {}
            gate_metadata = candidate.get("test_gates_metadata") or {}
            manifest_metadata = candidate.get("manifest_metadata") or {}
            lines.append(
                f"- `{candidate['source_path']}`: `{candidate['validation']['status']}`, "
                f"ZIP SHA-256 `{candidate['zip_sha256']}`, version `{candidate.get('version')}`, "
                f"contract `{contract_metadata.get('doc_id')}@{contract_metadata.get('version')}`, "
                f"gate ref `{gate_metadata.get('contract_ref')}`, "
                f"manifest `{manifest_metadata.get('doc_id')}@{manifest_metadata.get('version')}`, "
                f"schema `{contract_metadata.get('suite_schema')}`, members `{candidate.get('artifact_count')}`."
            )
            for error in candidate["validation"]["errors"]:
                lines.append(f"  - ERROR: {error}")
            for warning in candidate["validation"]["warnings"]:
                lines.append(f"  - WARNING: {warning}")
        lines.append("")

    lines.extend(["## BLOCKERS / AMBIGUITIES", ""])
    if report["blockers_and_ambiguities"]:
        for blocker in report["blockers_and_ambiguities"]:
            lines.append(f"### {blocker['doc_id'] or 'Repository authority'} ({blocker['status']})")
            for reason in blocker["reasons"]:
                lines.append(f"- {reason}")
            if blocker["candidate_paths"]:
                lines.append("- Candidates: " + ", ".join(f"`{path}`" for path in blocker["candidate_paths"]))
            lines.append("")
    else:
        lines.append("None.")

    lines.extend(["", "## Repository inventory", ""])
    lines.append("| Classification | Files |")
    lines.append("|---|---:|")
    for category, items in report["repository_inventory"].items():
        lines.append(f"| `{category}` | {len(items)} |")
    lines.extend(["", "### Non-contract ZIPs", ""])
    for item in report["non_contract_zips"]:
        lines.append(f"- `{item['path']}`: {item['reason']}")
    lines.extend(["", "### Existing extracted bundles", ""])
    for item in report["existing_extracted_bundles"]:
        lines.append(
            f"- `{item['path']}`: `{item['doc_id']}@{item['version']}`, "
            f"ZIP parity `{item['zip_parity']['status']}`."
        )
    lines.extend(["", "### Governance documents", ""])
    for item in report["governance_documents"]:
        if item["classification"] in {"governance_document", "contract_index"}:
            lines.append(
                f"- `{item['path']}`: identity `{item['document_identity']}`, version `{item['version']}`, "
                f"canonical `{item['declared_canonical']}`, supersedes `{item['supersedes']}`, "
                f"authority `{item['authority_level']}`, live/tracked `{str(item['belongs_to_live_working_tree']).lower()}`."
            )
    lines.extend(["", "### Governance version families and duplicate candidates", ""])
    if report["governance_duplicate_candidates"]:
        for item in report["governance_duplicate_candidates"]:
            lines.append(f"- `{item['document_identity']}`:")
            for version in item["versions"]:
                lines.append(
                    f"  - v`{version['version']}`: "
                    + ", ".join(f"`{path}`" for path in version["paths"])
                    + f"; identical bytes `{str(version['identical_bytes']).lower()}`; "
                    + f"canonical `{', '.join(version['canonical_declarations']) or 'not declared'}`; "
                    + f"supersedes `{', '.join(version['supersedes_declarations']) or 'not declared'}`."
                )
    else:
        lines.append("None detected by document identity and version metadata.")
    lines.extend(["", "### Non-contract files in contract directories", ""])
    lines.extend(f"- `{path}`" for path in report["non_contract_files_in_contract_directories"])
    lines.extend(["", "### Unclassified files", ""])
    lines.extend(f"- `{path}`" for path in report["unclassified_files"])

    cleanup = report["cleanup_plan"]
    lines.extend(["", "## Proposed Phase 2 additions", ""])
    lines.extend(f"- Copy `{item['source']}` to `{item['target']}`: {item['reason']}" for item in cleanup["proposed_additions"])
    lines.extend(["", "## Proposed Phase 2 moves", ""])
    lines.extend(f"- `{item['source']}` -> `{item['target']}`: {item['reason']}" for item in cleanup["proposed_moves"])
    lines.extend(["", "## Proposed Phase 2 deletions", ""])
    lines.extend(f"- `{item['path']}`: {item['reason']}" for item in cleanup["proposed_deletions"])
    lines.extend(["", "## Deferred paths", ""])
    lines.extend(f"- `{item['path']}`: {item['reason']}" for item in cleanup["deferred_due_to_contract_blockers"])
    lines.extend(["", "## Untracked or ignored evidence to preserve", ""])
    lines.extend(f"- `{item['path']}`: {item['reason']}" for item in cleanup["untracked_or_ignored_evidence_to_preserve"])
    lines.extend(
        [
            "",
            "## Proposed final structure",
            "",
            "```text",
            ".",
            "├── README.md",
            "├── contracts/",
            "│   ├── manifest.json",
            "│   ├── <DOC-ID>/",
            "│   │   ├── <DOC-ID>_bundle_vX.Y.Z.zip",
            "│   │   └── extracted/",
            "├── governance/",
            "├── planning/",
            "├── tools/",
            "│   ├── reconcile_contracts.py",
            "│   └── support/",
            "├── tests/",
            "└── reports/",
            "    ├── contract-reconciliation.json",
            "    └── contract-reconciliation.md",
            "```",
            "",
        ]
    )
    lines.append("This is a Phase 1 report. It does not move, rename, extract, or delete repository files.")
    return "\n".join(lines)


def write_reports(report: dict[str, Any], root: Path, json_path: Path | None = None, markdown_path: Path | None = None) -> tuple[Path, Path]:
    json_target = json_path or root / REPORT_JSON
    markdown_target = markdown_path or root / REPORT_MARKDOWN
    json_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)
    public_report = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    json_target.write_text(public_report, encoding="utf-8", newline="\n")
    markdown_target.write_text(build_markdown_report(report), encoding="utf-8", newline="\n")
    return json_target, markdown_target


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit contract bundle candidates without modifying them.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="Inventory, validate, and report contract candidates.")
    audit.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent, help="Repository root to inspect.")
    scan_mode = audit.add_mutually_exclusive_group(required=True)
    scan_mode.add_argument(
        "--canonical",
        action="store_true",
        help="Scan Git-tracked repository files only; use this mode for CI authority checks.",
    )
    scan_mode.add_argument(
        "--include-staging",
        action="store_true",
        help="Forensic scan of tracked, untracked, and ignored workspace files, including .staging.",
    )
    audit.add_argument("--strict", action="store_true", help="Exit non-zero when contract authority, suite schema, or dependency closure remains unresolved.")
    audit.add_argument("--json-output", type=Path, default=None, help="Override the JSON report path.")
    audit.add_argument("--markdown-output", type=Path, default=None, help="Override the Markdown report path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    if args.command != "audit":
        return 2
    root = args.root.resolve()
    scan_mode = "canonical" if args.canonical else "forensic"
    if args.canonical and args.strict and (root / "contracts/manifest.json").is_file():
        try:
            if __package__:
                from .contract_manifest import active_repository_audit
            else:
                from contract_manifest import active_repository_audit
            report = active_repository_audit(root)
        except (ImportError, ValueError) as error:
            print(f"Strict active audit failed: {error}", file=sys.stderr)
            return 2
        json_path = args.json_output or root / REPORT_JSON
        markdown_path = args.markdown_output or root / REPORT_MARKDOWN
        json_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary = report["summary"]
        lines = [
            "# Strict active contract audit",
            "",
            f"Status: {report['status']}",
            f"Active contract ZIPs: {summary['manifest_contract_count']}",
            f"CANON members: {summary['canon_member_count']}",
            f"Dependency-only contracts: {summary['dependency_only_contract_count']}",
            f"Dependency edges: {summary['dependency_edge_count']}",
            f"Unresolved required edges: {summary['dependency_target_unresolved_count']}",
            f"Below-minimum edges: {summary['dependency_floor_conflict_count']}",
            f"Invalid dependency records: {summary['dependency_edge_invalid_count']}",
            "",
        ]
        lines.extend(f"- ERROR: {error}" for error in report["errors"])
        markdown_path.write_text("\n".join(lines), encoding="utf-8")
        print(
            f"Strict active audit: {report['status']}, "
            f"{summary['manifest_contract_count']} ZIPs, "
            f"{summary['dependency_edge_count']} dependency edges."
        )
        print(f"JSON report: {json_path}")
        print(f"Markdown report: {markdown_path}")
        return 0 if report["status"] == "PASS" else 1
    try:
        report = audit_repository(root, scan_mode=scan_mode)
    except ValueError as error:
        print(f"Audit failed: {error}", file=sys.stderr)
        return 2
    json_path, markdown_path = write_reports(report, root, args.json_output, args.markdown_output)
    summary = report["summary"]
    print(
        f"Audit complete ({scan_mode}): "
        f"{summary['zip_files_inspected']} ZIPs, "
        f"{summary['contract_bundle_candidates']} contract candidates, "
        f"{summary['selected_doc_ids']} selected, "
        f"{summary['ambiguous_doc_ids']} ambiguous, "
        f"{summary['invalid_doc_ids']} unresolved invalid doc_ids."
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    if args.strict and summary["phase_2_blocked"]:
        print("Strict audit failed: unresolved contract, schema, or dependency closure remains.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
