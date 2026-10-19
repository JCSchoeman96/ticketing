#!/usr/bin/env python3
"""Build and validate deterministic three-artifact contract bundles.

Contract, test-gate, and manifest rules come from the owner-ratified CS-0
successor source. Candidate bundles require explicit opt-in and remain
unreleased.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import io
import json
import os
import re
import stat
import struct
import tempfile
from pathlib import Path, PurePosixPath
import zipfile

from jsonschema import Draft202012Validator, SchemaError


DOC_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SUITE_SCHEMA_PATTERN = re.compile(r"^CS-0@\d+\.\d+\.\d+$")
UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
MANIFEST_SCHEMA_VERSION = "bundle-manifest/1.0"
CONTRACT_SCHEMA_VERSION = "contract-suite/1.0"
GATE_SCHEMA_VERSION = "test-gates/1.0"
OWNER_APPROVED_CS0_SCHEMA = "CS-0@3.0.1"
CS0_SUCCESSOR_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "release-src/current/CS-0/3.0.1"
)
CONTRACT_STATUSES = {"draft", "active", "deprecated", "retired"}
GATE_LEVELS = {"P0", "P1", "P2"}
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FIXED_ZIP_MODE = stat.S_IFREG | 0o644


class ReleaseError(ValueError):
    """Raised when source metadata or a release bundle violates the profile."""


def _read_json(path: Path, description: str) -> tuple[dict[str, object], bytes]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ReleaseError(f"cannot read {description}: {path}: {error}") from error
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseError(f"{description} is not valid UTF-8 JSON: {path}") from error
    if not isinstance(value, dict):
        raise ReleaseError(f"{description} must be a JSON object: {path}")
    return value, payload


def _require_string(value: object, field: str, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value:
        raise ReleaseError(f"{field} must be a non-empty string")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ReleaseError(f"{field} has an invalid value: {value!r}")
    return value


def _validate_explicit_timestamp(value: object, field: str = "generated_at_utc") -> str:
    timestamp = _require_string(value, field, UTC_TIMESTAMP_PATTERN)
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ReleaseError(f"{field} is not a valid UTC timestamp: {timestamp!r}") from error
    return timestamp


def _safe_archive_path(name: str) -> PurePosixPath:
    if not name or "\x00" in name or "\\" in name or name.startswith("/"):
        raise ReleaseError(f"unsafe archive path: {name!r}")
    raw_parts = name.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ReleaseError(f"unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or (path.parts and ":" in path.parts[0]):
        raise ReleaseError(f"unsafe archive path: {name!r}")
    return path


def _expected_identity(
    release: dict[str, object], *, allow_reproduction: bool, allow_candidate: bool
) -> tuple[str, str, str, str]:
    doc_id = _require_string(release.get("doc_id"), "release doc_id", DOC_ID_PATTERN)
    version = _require_string(release.get("version"), "release version", VERSION_PATTERN)
    suite_schema = _require_string(
        release.get("suite_schema"), "release suite_schema", SUITE_SCHEMA_PATTERN
    )
    _require_string(release.get("release_intent"), "release_intent")
    release_status = release.get("release_status")
    if release_status == "candidate" and not allow_candidate:
        raise ReleaseError("candidate build requires explicit opt-in")
    if release_status != "approved" and not (
        (allow_reproduction and release_status == "reproduction")
        or (allow_candidate and release_status == "candidate")
    ):
        raise ReleaseError("release_status must be 'approved' before building")
    provenance = release.get("source_provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise ReleaseError("source_provenance must be a non-empty object")
    _require_string(provenance.get("kind"), "source_provenance.kind")
    timestamp = _validate_explicit_timestamp(release.get("generated_at_utc"))
    return doc_id, version, suite_schema, timestamp


def _artifact_names(doc_id: str, version: str) -> tuple[str, str, str]:
    return (
        f"{doc_id}_Contract_v{version}.json",
        f"{doc_id}_Test_Gates_v{version}.json",
        "bundle.manifest.json",
    )


def _validate_bootstrap_provenance(
    source_dir: Path,
    contract_bytes: bytes,
    gates_bytes: bytes,
    source_provenance: dict[str, object],
) -> None:
    """Bind an optional bootstrap record to the editable source payloads."""

    provenance_path = source_dir / "provenance.json"
    if not provenance_path.exists():
        if source_provenance.get("kind") == "staging-bundle-bootstrap":
            raise ReleaseError("staging-bundle-bootstrap source requires provenance.json")
        return
    provenance, _ = _read_json(provenance_path, "source provenance")
    bootstrap_commit = _require_string(
        provenance.get("bootstrap_commit"), "provenance bootstrap_commit"
    )
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", bootstrap_commit) is None:
        raise ReleaseError("provenance bootstrap_commit must be a full Git object ID")
    _require_string(provenance.get("source_bundle_path"), "provenance source_bundle_path")
    source_zip_hash = _require_string(
        provenance.get("source_zip_sha256"), "provenance source_zip_sha256"
    )
    if re.fullmatch(r"[0-9a-f]{64}", source_zip_hash) is None:
        raise ReleaseError("provenance source_zip_sha256 must be a SHA-256 hex digest")
    if source_provenance.get("kind") == "staging-bundle-bootstrap":
        if source_provenance.get("path") != "provenance.json":
            raise ReleaseError("release source_provenance.path must reference provenance.json")
        if source_provenance.get("source_zip_sha256") != source_zip_hash:
            raise ReleaseError("release source_provenance hash disagrees with provenance.json")
    source_zip_bytes = provenance.get("source_zip_bytes")
    if type(source_zip_bytes) is not int or source_zip_bytes <= 0:
        raise ReleaseError("provenance source_zip_bytes must be a positive integer")

    members = provenance.get("source_members")
    if not isinstance(members, list):
        raise ReleaseError("provenance source_members must be an array")
    expected_payloads = {
        "contract.json": contract_bytes,
        "test-gates.json": gates_bytes,
    }
    records_by_path: dict[str, dict[str, object]] = {}
    for record in members:
        if not isinstance(record, dict):
            raise ReleaseError("provenance source member entries must be objects")
        path = record.get("tracked_source_path")
        if not isinstance(path, str) or path in records_by_path:
            raise ReleaseError("provenance tracked_source_path values must be unique strings")
        if path not in expected_payloads:
            raise ReleaseError(f"unexpected provenance source member path: {path!r}")
        records_by_path[path] = record
    if set(records_by_path) != set(expected_payloads):
        raise ReleaseError("provenance must record contract.json and test-gates.json")

    for path, payload in expected_payloads.items():
        record = records_by_path[path]
        if record.get("sha256") != hashlib.sha256(payload).hexdigest():
            raise ReleaseError(f"provenance hash mismatch for {path}")
        if type(record.get("bytes")) is not int or record["bytes"] != len(payload):
            raise ReleaseError(f"provenance size mismatch for {path}")
        _require_string(record.get("source_member_path"), f"provenance {path} source_member_path")


def _validate_contract_schema_fields(contract: dict[str, object]) -> None:
    """Check the required root fields and enums in the ratified CS-0 v3 profile."""

    if contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise ReleaseError(f"contract schema_version must be {CONTRACT_SCHEMA_VERSION!r}")
    _require_string(contract.get("title"), "contract title")
    if contract.get("status") not in CONTRACT_STATUSES:
        raise ReleaseError("contract status must be draft, active, deprecated, or retired")


def _validate_gate_schema_fields(gates: dict[str, object]) -> None:
    """Check required root and gate fields in the ratified CS-0 v3 profile."""

    if gates.get("schema_version") != GATE_SCHEMA_VERSION:
        raise ReleaseError(f"test-gates schema_version must be {GATE_SCHEMA_VERSION!r}")
    _require_string(gates.get("title"), "test-gates title")
    if gates.get("status") not in CONTRACT_STATUSES:
        raise ReleaseError("test-gates status must be draft, active, deprecated, or retired")
    gate_records = gates.get("gates")
    if not isinstance(gate_records, list) or not gate_records:
        raise ReleaseError("test-gates gates must be a non-empty array")
    for index, gate in enumerate(gate_records):
        label = f"test-gates gates[{index}]"
        if not isinstance(gate, dict):
            raise ReleaseError(f"{label} must be an object")
        _require_string(gate.get("id"), f"{label}.id")
        if gate.get("level") not in GATE_LEVELS:
            raise ReleaseError(f"{label}.level must be P0, P1, or P2")
        if type(gate.get("must")) is not bool:
            raise ReleaseError(f"{label}.must must be a boolean")
        _require_string(gate.get("description"), f"{label}.description")
        assertions = gate.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            raise ReleaseError(f"{label}.assertions must be a non-empty array")
        for assertion_index, assertion in enumerate(assertions):
            assertion_label = f"{label}.assertions[{assertion_index}]"
            if not isinstance(assertion, dict):
                raise ReleaseError(f"{assertion_label} must be an object")
            if assertion.get("mode") not in {"manual", "automated"}:
                raise ReleaseError(f"{assertion_label}.mode must be manual or automated")
            _require_string(assertion.get("type"), f"{assertion_label}.type")
            if not isinstance(assertion.get("details"), dict):
                raise ReleaseError(f"{assertion_label}.details must be an object")


def _validate_suite_schema_gate_descriptions(gates: dict[str, object]) -> None:
    """Reject normative suite-schema claims that contradict automated assertions."""

    claim_pattern = re.compile(
        r"\bsuite_schema\s+MUST\s+equal\s+(CS-0@\d+\.\d+\.\d+)\b",
        re.IGNORECASE,
    )
    gate_records = gates.get("gates")
    if not isinstance(gate_records, list):
        return
    for gate in gate_records:
        if not isinstance(gate, dict):
            continue
        description = gate.get("description")
        assertions = gate.get("assertions")
        if not isinstance(description, str) or not isinstance(assertions, list):
            continue
        asserted_values: set[str] = set()
        locked_artifacts: set[str] = set()
        for assertion in assertions:
            if not isinstance(assertion, dict) or assertion.get("mode") != "automated":
                continue
            details = assertion.get("details")
            if not isinstance(details, dict):
                continue
            if assertion.get("type") == "suite_schema_matches":
                expected = details.get("expected")
                if isinstance(expected, str):
                    asserted_values.add(expected)
            elif (
                assertion.get("type") == "json_pointer_equals"
                and details.get("json_pointer") == "/suite_schema"
            ):
                artifact_kind = details.get("artifact_kind")
                if isinstance(artifact_kind, str):
                    locked_artifacts.add(artifact_kind)
                expected = details.get("equals")
                if isinstance(expected, str):
                    asserted_values.add(expected)
        described_values = set(claim_pattern.findall(description))
        all_bundle_artifacts = {"contract", "test_gates", "bundle_manifest"}
        if all_bundle_artifacts <= locked_artifacts and asserted_values and described_values and (
            len(asserted_values) != 1 or asserted_values != described_values
        ):
            raise ReleaseError(
                f"gate {gate.get('id', 'unknown')} description suite_schema conflicts with its automated assertion"
            )


def _json_pointer_value(document: dict[str, object], pointer: str) -> object:
    value: object = document
    for encoded_part in pointer.lstrip("/").split("/"):
        part = encoded_part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if part not in value:
                raise ReleaseError(f"CS-0 gate points to missing field {pointer}")
            value = value[part]
        elif isinstance(value, list):
            try:
                value = value[int(part)]
            except (ValueError, IndexError) as error:
                raise ReleaseError(f"CS-0 gate points to missing field {pointer}") from error
        else:
            raise ReleaseError(f"CS-0 gate points through a non-container at {pointer}")
    return value


def _validate_json_schema(
    instance: object,
    schema: object,
    *,
    artifact_name: str,
    schema_version: str = OWNER_APPROVED_CS0_SCHEMA,
) -> None:
    """Validate an artifact with its ratified Draft 2020-12 schema."""

    if not isinstance(schema, dict):
        raise ReleaseError(f"{schema_version} does not define a schema for {artifact_name}")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ReleaseError(
            f"{schema_version} contains an invalid schema for {artifact_name}: {error.message}"
        ) from error
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            error.message,
        ),
    )
    if errors:
        error = errors[0]
        pointer = "/" + "/".join(
            str(part).replace("~", "~0").replace("/", "~1")
            for part in error.absolute_path
        )
        raise ReleaseError(
            f"{artifact_name} violates {schema_version} schema at {pointer}: {error.message}"
        )


def _dependency_edge_types_from_cs0(
    contract: dict[str, object], gates: dict[str, object]
) -> None:
    """Read owner-approved dependency rules from the tracked CS-0 successor source."""

    if contract.get("doc_id") != "CS-0" or contract.get("version") != "3.0.1":
        raise ReleaseError("dependency authority must be tracked CS-0 v3.0.1 source")
    if contract.get("suite_schema") != OWNER_APPROVED_CS0_SCHEMA:
        raise ReleaseError("CS-0 dependency authority suite_schema does not match its version")
    if gates.get("doc_id") != "CS-0-GATE" or gates.get("version") != "3.0.1":
        raise ReleaseError("CS-0 dependency authority gates do not match v3.0.1")
    if gates.get("suite_schema") != OWNER_APPROVED_CS0_SCHEMA:
        raise ReleaseError("CS-0 dependency authority gate suite_schema does not match v3.0.1")
    if gates.get("contract_ref") != {"doc_id": "CS-0", "version": "3.0.1"}:
        raise ReleaseError("CS-0 dependency authority gate contract_ref does not match v3.0.1")

    try:
        schemas = contract["schemas"]
        contract_schema = schemas["contract"]
        gate_schema = schemas["test_gates"]
        manifest_schema = schemas["bundle_manifest"]
    except (KeyError, TypeError) as error:
        raise ReleaseError("CS-0 v3.0.1 must define contract, test-gates, and manifest schemas") from error
    for name, schema in (
        ("contract", contract_schema),
        ("test-gates", gate_schema),
        ("bundle manifest", manifest_schema),
    ):
        if not isinstance(schema, dict):
            raise ReleaseError(f"CS-0 v3.0.1 {name} schema must be an object")
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            raise ReleaseError(f"CS-0 v3.0.1 {name} schema is invalid: {error.message}") from error
    _validate_json_schema(contract, contract_schema, artifact_name="CS-0 contract")
    _validate_json_schema(gates, gate_schema, artifact_name="CS-0 test-gates")

    try:
        dependency_schema = contract["schemas"]["contract"]["properties"]["dependencies"]
        edge_type_schema = dependency_schema["items"]["properties"]["edge_type"]
        raw_edge_types = edge_type_schema["enum"]
        semantics_schema = contract["schemas"]["contract"]["properties"][
            "dependency_edge_type_semantics"
        ]
        semantics = contract["dependency_edge_type_semantics"]
    except (KeyError, TypeError) as error:
        raise ReleaseError("CS-0 dependency schema or semantics are missing") from error
    if (
        not isinstance(raw_edge_types, list)
        or not raw_edge_types
        or any(not isinstance(edge_type, str) or not edge_type for edge_type in raw_edge_types)
        or len(set(raw_edge_types)) != len(raw_edge_types)
    ):
        raise ReleaseError("CS-0 dependency edge enum must contain unique strings")
    edge_types = set(raw_edge_types)
    if "foundation" in edge_types:
        raise ReleaseError("CS-0 v3.0.1 must reject the legacy foundation edge")
    if not isinstance(semantics, list):
        raise ReleaseError("CS-0 dependency edge semantics must be an array")
    semantic_types: set[str] = set()
    for definition in semantics:
        if not isinstance(definition, dict):
            raise ReleaseError("CS-0 dependency edge semantics entries must be objects")
        edge_type = definition.get("edge_type")
        meaning = definition.get("meaning")
        exclusions = definition.get("does_not_imply")
        if (
            not isinstance(edge_type, str)
            or edge_type in semantic_types
            or edge_type not in edge_types
            or not isinstance(meaning, str)
            or not meaning.strip()
            or not isinstance(exclusions, list)
            or any(not isinstance(item, str) or not item.strip() for item in exclusions)
        ):
            raise ReleaseError("CS-0 dependency edge semantics are incomplete or inconsistent")
        semantic_types.add(edge_type)
    if semantic_types != {"requires", "governance_floor", "foundation_floor"}:
        raise ReleaseError("CS-0 must define requires, governance_floor, and foundation_floor")
    if (
        not isinstance(semantics_schema, dict)
        or semantics_schema.get("type") != "array"
        or semantics_schema.get("minItems") != 3
        or semantics_schema.get("maxItems") != 3
    ):
        raise ReleaseError("CS-0 dependency edge semantics must be constrained by its contract schema")

    gate_records = gates.get("gates")
    if not isinstance(gate_records, list):
        raise ReleaseError("CS-0 dependency authority gates are missing")
    semantic_gate = next(
        (
            gate
            for gate in gate_records
            if isinstance(gate, dict)
            and gate.get("id") == "CS-0-P0-DEPENDENCY-EDGE-SEMANTICS"
        ),
        None,
    )
    if not isinstance(semantic_gate, dict):
        raise ReleaseError("CS-0 dependency edge semantics gate is missing")
    assertions = semantic_gate.get("assertions")
    if not isinstance(assertions, list):
        raise ReleaseError("CS-0 dependency edge semantics gate has no assertions")
    locked_pointers: set[str] = set()
    for assertion in assertions:
        if not isinstance(assertion, dict) or assertion.get("type") != "json_pointer_equals":
            continue
        details = assertion.get("details")
        if not isinstance(details, dict):
            continue
        pointer = details.get("json_pointer")
        if pointer in {
            "/dependency_edge_type_semantics",
            "/schemas/contract/properties/dependencies/items/properties/edge_type/enum",
        }:
            if _json_pointer_value(contract, str(pointer)) != details.get("equals"):
                raise ReleaseError(f"CS-0 dependency gate does not lock {pointer}")
            locked_pointers.add(str(pointer))
    if len(locked_pointers) != 2:
        raise ReleaseError("CS-0 dependency edge gate must lock semantics and the current enum")
    return None


def _owner_approved_cs0_authority(
    doc_id: str,
    version: str,
    contract: dict[str, object],
    gates: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    if doc_id == "CS-0" and version == "3.0.1":
        authority_contract, authority_gates = contract, gates
    else:
        authority_contract, _ = _read_json(
            CS0_SUCCESSOR_SOURCE / "contract.json", "owner-approved CS-0 successor schema"
        )
        authority_gates, _ = _read_json(
            CS0_SUCCESSOR_SOURCE / "test-gates.json", "owner-approved CS-0 successor gates"
        )
    _dependency_edge_types_from_cs0(authority_contract, authority_gates)
    return authority_contract, authority_gates


def _validate_source(
    source_dir: Path, *, allow_reproduction: bool, allow_candidate: bool
) -> tuple[dict[str, object], str, str, str, str, bytes, bytes]:
    release, _ = _read_json(source_dir / "release.json", "release metadata")
    doc_id, version, suite_schema, timestamp = _expected_identity(
        release,
        allow_reproduction=allow_reproduction,
        allow_candidate=allow_candidate,
    )
    contract, contract_bytes = _read_json(source_dir / "contract.json", "contract artifact")
    gates, gates_bytes = _read_json(source_dir / "test-gates.json", "test-gates artifact")
    source_provenance = release.get("source_provenance")
    assert isinstance(source_provenance, dict)
    _validate_bootstrap_provenance(
        source_dir, contract_bytes, gates_bytes, source_provenance
    )

    _validate_contract_schema_fields(contract)
    if contract.get("artifact_kind") != "contract":
        raise ReleaseError("contract artifact_kind must be 'contract'")
    if contract.get("doc_id") != doc_id:
        raise ReleaseError("contract doc_id does not match release doc_id")
    if contract.get("version") != version:
        raise ReleaseError("contract version does not match release version")
    if contract.get("suite_schema") != suite_schema:
        raise ReleaseError("contract suite_schema does not match release suite_schema")

    _validate_gate_schema_fields(gates)
    if gates.get("artifact_kind") != "test_gates":
        raise ReleaseError("test-gates artifact_kind must be 'test_gates'")
    if gates.get("doc_id") != f"{doc_id}-GATE":
        raise ReleaseError("test-gates doc_id must be the contract doc_id plus '-GATE'")
    if gates.get("version") != version:
        raise ReleaseError("test-gates version does not match release version")
    if gates.get("suite_schema") != suite_schema:
        raise ReleaseError("test-gates suite_schema does not match release suite_schema")
    _validate_suite_schema_gate_descriptions(gates)
    contract_ref = gates.get("contract_ref")
    if not isinstance(contract_ref, dict):
        raise ReleaseError("test-gates contract_ref must be an object")
    if contract_ref.get("doc_id") != doc_id:
        raise ReleaseError("test-gates contract_ref doc_id does not match release doc_id")
    if contract_ref.get("version") != version:
        raise ReleaseError("test-gates contract_ref version does not match release version")

    if suite_schema == OWNER_APPROVED_CS0_SCHEMA:
        authority_contract, _ = _owner_approved_cs0_authority(
            doc_id, version, contract, gates
        )
        schemas = authority_contract.get("schemas")
        assert isinstance(schemas, dict)
        _validate_json_schema(
            contract, schemas.get("contract"), artifact_name="contract.json"
        )
        _validate_json_schema(
            gates, schemas.get("test_gates"), artifact_name="test-gates.json"
        )
    elif release.get("release_status") == "candidate":
        raise ReleaseError(
            f"candidate source must target owner-approved suite schema {OWNER_APPROVED_CS0_SCHEMA}"
        )

    return release, doc_id, version, suite_schema, timestamp, contract_bytes, gates_bytes


def _manifest_bytes(
    doc_id: str,
    version: str,
    suite_schema: str,
    timestamp: str,
    artifacts: dict[str, bytes],
) -> bytes:
    file_records = [
        {
            "bytes": len(payload),
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for path, payload in sorted(artifacts.items())
    ]
    manifest = {
        "artifact_kind": "bundle_manifest",
        "bundle": {"bundle_id": doc_id, "bundle_version": version},
        "doc_id": doc_id,
        "files": file_records,
        "generated_at_utc": timestamp,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "suite_schema": suite_schema,
        "version": version,
    }
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=FIXED_ZIP_TIMESTAMP)
    info.create_system = 3
    info.external_attr = FIXED_ZIP_MODE << 16
    info.internal_attr = 0
    info.compress_type = zipfile.ZIP_STORED
    info.extra = b""
    info.comment = b""
    return info


def _validate_zip_framing(archive_data: bytes) -> None:
    """Reject ZIP prefixes, comments, ZIP64, and trailing bytes for this profile."""

    end_signature = b"PK\x05\x06"
    end_offset = archive_data.rfind(end_signature)
    if end_offset < 0 or end_offset + 22 > len(archive_data):
        raise ReleaseError("invalid ZIP archive: missing end record")
    if end_offset + 22 != len(archive_data):
        raise ReleaseError("ZIP archive contains trailing bytes or an unsupported comment")
    (
        signature,
        disk_number,
        central_disk,
        disk_entries,
        total_entries,
        central_size,
        central_offset,
        comment_length,
    ) = struct.unpack_from("<4s4H2LH", archive_data, end_offset)
    if signature != end_signature or comment_length != 0:
        raise ReleaseError("ZIP archive has a malformed end record")
    if disk_number != 0 or central_disk != 0 or disk_entries != total_entries:
        raise ReleaseError("multi-disk ZIP archives are not supported")
    if disk_entries == 0xFFFF or total_entries == 0xFFFF:
        raise ReleaseError("ZIP64 archives are not supported by this release profile")
    if central_size == 0xFFFFFFFF or central_offset == 0xFFFFFFFF:
        raise ReleaseError("ZIP64 archives are not supported by this release profile")
    if central_offset + central_size != end_offset:
        raise ReleaseError("ZIP archive contains a prefix, gap, or trailing bytes")


def _build_zip_bytes(
    doc_id: str,
    version: str,
    artifact_payloads: dict[str, bytes],
    manifest_payload: bytes,
) -> bytes:
    bundle_root = f"{doc_id}_bundle_v{version}"
    members = {
        f"{bundle_root}/{path}": payload for path, payload in artifact_payloads.items()
    }
    members[f"{bundle_root}/bundle.manifest.json"] = manifest_payload
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(members):
            archive.writestr(_zip_info(path), members[path])
    return output.getvalue()


def _load_archive(archive_data: bytes) -> dict[str, object]:
    _validate_zip_framing(archive_data)
    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_data), "r")
    except (OSError, zipfile.BadZipFile) as error:
        raise ReleaseError(f"invalid ZIP archive: {error}") from error

    with archive:
        names = [member.filename for member in archive.infolist()]
        if archive.comment:
            raise ReleaseError("bundle ZIP comment must be empty")
        seen: set[str] = set()
        for name in names:
            if name in seen:
                raise ReleaseError(f"duplicate archive path: {name}")
            seen.add(name)
            _safe_archive_path(name)
        if names != sorted(names):
            raise ReleaseError("archive members must be in sorted order")
        for member in archive.infolist():
            if member.flag_bits != 0:
                raise ReleaseError(f"archive member has unsupported flags: {member.filename}")
            if member.is_dir():
                raise ReleaseError("bundle must not contain directory entries")
            if member.comment or member.extra:
                raise ReleaseError(f"archive member has non-canonical metadata: {member.filename}")
            if member.date_time != FIXED_ZIP_TIMESTAMP:
                raise ReleaseError(f"archive member has non-canonical timestamp: {member.filename}")
            if member.compress_type != zipfile.ZIP_STORED:
                raise ReleaseError(f"archive member has non-canonical compression: {member.filename}")
            if member.create_system != 3 or member.external_attr >> 16 != FIXED_ZIP_MODE:
                raise ReleaseError(f"archive member has non-canonical permissions: {member.filename}")

        manifests = [name for name in names if PurePosixPath(name).name == "bundle.manifest.json"]
        if len(manifests) != 1:
            raise ReleaseError("bundle must contain exactly one bundle.manifest.json")
        manifest_path = manifests[0]
        try:
            manifest_payload = archive.read(manifest_path)
        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
            raise ReleaseError(f"cannot read bundle manifest: {error}") from error
        try:
            manifest = json.loads(manifest_payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReleaseError("bundle manifest is not valid UTF-8 JSON") from error
        if not isinstance(manifest, dict):
            raise ReleaseError("bundle manifest must be a JSON object")
        expected_manifest_keys = {
            "artifact_kind",
            "bundle",
            "doc_id",
            "files",
            "generated_at_utc",
            "schema_version",
            "suite_schema",
            "version",
        }
        if set(manifest) != expected_manifest_keys:
            raise ReleaseError("manifest keys do not match the deterministic release profile")

        doc_id = _require_string(manifest.get("doc_id"), "manifest doc_id", DOC_ID_PATTERN)
        version = _require_string(manifest.get("version"), "manifest version", VERSION_PATTERN)
        suite_schema = _require_string(
            manifest.get("suite_schema"), "manifest suite_schema", SUITE_SCHEMA_PATTERN
        )
        _validate_explicit_timestamp(manifest.get("generated_at_utc"))
        bundle = manifest.get("bundle")
        if not isinstance(bundle, dict):
            raise ReleaseError("manifest bundle must be an object")
        if set(bundle) != {"bundle_id", "bundle_version"}:
            raise ReleaseError("manifest bundle keys do not match the release profile")
        if bundle.get("bundle_id") != doc_id or bundle.get("bundle_version") != version:
            raise ReleaseError("manifest bundle identity does not match manifest identity")
        if manifest.get("artifact_kind") != "bundle_manifest":
            raise ReleaseError("manifest artifact_kind must be 'bundle_manifest'")
        if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
            raise ReleaseError(f"manifest schema_version must be {MANIFEST_SCHEMA_VERSION!r}")
        canonical_manifest = (
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        if manifest_payload != canonical_manifest:
            raise ReleaseError("bundle manifest JSON is not canonically serialized")

        bundle_root = f"{doc_id}_bundle_v{version}"
        if manifest_path != f"{bundle_root}/bundle.manifest.json":
            raise ReleaseError("manifest path does not match bundle identity")
        expected_contract, expected_gates, _ = _artifact_names(doc_id, version)
        artifact_records = manifest.get("files")
        if not isinstance(artifact_records, list) or len(artifact_records) != 2:
            raise ReleaseError("manifest files must declare exactly contract and test-gates artifacts")

        records_by_path: dict[str, dict[str, object]] = {}
        for record in artifact_records:
            if not isinstance(record, dict):
                raise ReleaseError("manifest file entries must be objects")
            if set(record) != {"bytes", "path", "sha256"}:
                raise ReleaseError("manifest file entry keys do not match the release profile")
            path = record.get("path")
            if not isinstance(path, str) or path in records_by_path:
                raise ReleaseError("manifest file paths must be unique strings")
            if "/" in path or "\\" in path or path in {".", ".."}:
                raise ReleaseError(f"manifest artifact path must be a filename: {path!r}")
            records_by_path[path] = record
        if set(records_by_path) != {expected_contract, expected_gates}:
            raise ReleaseError("manifest paths do not match contract and test-gates identities")
        if list(records_by_path) != sorted(records_by_path):
            raise ReleaseError("manifest file records must be in sorted order")

        expected_members = {
            f"{bundle_root}/{expected_contract}",
            f"{bundle_root}/{expected_gates}",
            f"{bundle_root}/bundle.manifest.json",
        }
        if set(names) != expected_members:
            raise ReleaseError("archive members do not match the three-artifact bundle shape")
        artifact_payloads: dict[str, bytes] = {}
        for path, record in records_by_path.items():
            member_path = f"{bundle_root}/{path}"
            try:
                payload = archive.read(member_path)
            except (OSError, RuntimeError, zipfile.BadZipFile) as error:
                raise ReleaseError(f"cannot read archive member {member_path}: {error}") from error
            expected_hash = record.get("sha256")
            expected_size = record.get("bytes")
            actual_hash = hashlib.sha256(payload).hexdigest()
            if expected_hash != actual_hash:
                raise ReleaseError(f"manifest hash mismatch for {path}")
            if type(expected_size) is not int or expected_size != len(payload):
                raise ReleaseError(f"manifest size mismatch for {path}")
            artifact_payloads[path] = payload

    contract_payload = artifact_payloads[expected_contract]
    gates_payload = artifact_payloads[expected_gates]
    try:
        contract = json.loads(contract_payload.decode("utf-8"))
        gates = json.loads(gates_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseError("contract and test-gates artifacts must be UTF-8 JSON") from error
    if not isinstance(contract, dict) or not isinstance(gates, dict):
        raise ReleaseError("contract and test-gates artifacts must be JSON objects")
    authority = _validate_bundle_artifact_identity(
        contract, gates, doc_id=doc_id, version=version, suite_schema=suite_schema
    )
    if authority is not None:
        authority_contract, _ = authority
        schemas = authority_contract.get("schemas")
        assert isinstance(schemas, dict)
        _validate_json_schema(
            manifest,
            schemas.get("bundle_manifest"),
            artifact_name="bundle.manifest.json",
        )
    canonical_archive = _build_zip_bytes(doc_id, version, artifact_payloads, manifest_payload)
    if archive_data != canonical_archive:
        raise ReleaseError("ZIP bytes do not match the deterministic canonical layout")
    return {
        "status": "VALID",
        "doc_id": doc_id,
        "version": version,
        "suite_schema": suite_schema,
        "manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "zip_sha256": hashlib.sha256(archive_data).hexdigest(),
        "artifacts": [
            {
                "path": path,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
            for path, payload in sorted(artifact_payloads.items())
        ],
    }


def _validate_bundle_artifact_identity(
    contract: dict[str, object],
    gates: dict[str, object],
    *,
    doc_id: str,
    version: str,
    suite_schema: str,
) -> tuple[dict[str, object], dict[str, object]] | None:
    _validate_contract_schema_fields(contract)
    if contract.get("artifact_kind") != "contract":
        raise ReleaseError("contract artifact_kind must be 'contract'")
    if contract.get("doc_id") != doc_id or contract.get("version") != version:
        raise ReleaseError("contract identity does not match manifest identity")
    if contract.get("suite_schema") != suite_schema:
        raise ReleaseError("contract suite_schema does not match manifest suite_schema")
    _validate_gate_schema_fields(gates)
    if gates.get("artifact_kind") != "test_gates":
        raise ReleaseError("test-gates artifact_kind must be 'test_gates'")
    if gates.get("doc_id") != f"{doc_id}-GATE" or gates.get("version") != version:
        raise ReleaseError("test-gates identity does not match manifest identity")
    if gates.get("suite_schema") != suite_schema:
        raise ReleaseError("test-gates suite_schema does not match manifest suite_schema")
    _validate_suite_schema_gate_descriptions(gates)
    contract_ref = gates.get("contract_ref")
    if not isinstance(contract_ref, dict):
        raise ReleaseError("test-gates contract_ref must be an object")
    if contract_ref.get("doc_id") != doc_id:
        raise ReleaseError("test-gates contract_ref doc_id does not match manifest identity")
    if contract_ref.get("version") != version:
        raise ReleaseError("test-gates contract_ref version does not match manifest identity")
    if suite_schema == OWNER_APPROVED_CS0_SCHEMA:
        authority_contract, authority_gates = _owner_approved_cs0_authority(
            doc_id, version, contract, gates
        )
        schemas = authority_contract.get("schemas")
        assert isinstance(schemas, dict)
        _validate_json_schema(
            contract, schemas.get("contract"), artifact_name="contract.json"
        )
        _validate_json_schema(
            gates, schemas.get("test_gates"), artifact_name="test-gates.json"
        )
        return authority_contract, authority_gates
    return None


def validate_bundle(bundle_path: Path) -> dict[str, object]:
    """Validate one ZIP against the proposed deterministic bundle profile."""

    try:
        archive_data = bundle_path.read_bytes()
    except OSError as error:
        raise ReleaseError(f"cannot read bundle: {bundle_path}: {error}") from error
    return _load_archive(archive_data)


def build_contract_release(
    source_dir: Path,
    output_dir: Path,
    *,
    allow_reproduction: bool = False,
    allow_candidate: bool = False,
) -> Path:
    """Build a deterministic ZIP from authored contract/gate source files."""

    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    release, doc_id, version, suite_schema, timestamp, contract_bytes, gates_bytes = (
        _validate_source(
            source_dir,
            allow_reproduction=allow_reproduction,
            allow_candidate=allow_candidate,
        )
    )
    contract_name, gates_name, _ = _artifact_names(doc_id, version)
    artifacts = {contract_name: contract_bytes, gates_name: gates_bytes}
    manifest_payload = _manifest_bytes(doc_id, version, suite_schema, timestamp, artifacts)
    archive_data = _build_zip_bytes(doc_id, version, artifacts, manifest_payload)
    validation = _load_archive(archive_data)
    if validation["status"] != "VALID":
        raise ReleaseError("built archive did not pass validation")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{doc_id}_bundle_v{version}.zip"
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.", suffix=".tmp", dir=output_dir
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as output:
            output.write(archive_data)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary_path, output_path)
        except FileExistsError:
            if output_path.is_symlink() or not output_path.is_file():
                raise ReleaseError(
                    f"refusing to accept a non-regular output path: {output_path}"
                )
            if output_path.read_bytes() != archive_data:
                raise ReleaseError(
                    f"refusing to replace existing release with different bytes: {output_path}"
                )
    except FileExistsError:
        if output_path.exists() and output_path.read_bytes() == archive_data:
            pass
        else:
            raise ReleaseError(f"cannot reserve release path without replacement: {output_path}")
    except OSError as error:
        raise ReleaseError(f"cannot write release bundle: {output_path}: {error}") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="authored release source directory")
    parser.add_argument("--output", required=True, type=Path, help="directory for the ZIP output")
    parser.add_argument(
        "--allow-candidate",
        action="store_true",
        help="build a review-only candidate bundle without marking it released",
    )
    args = parser.parse_args(argv)
    try:
        bundle_path = build_contract_release(
            args.source, args.output, allow_candidate=args.allow_candidate
        )
        result = validate_bundle(bundle_path)
    except ReleaseError as error:
        parser.error(str(error))
    print(f"{bundle_path}: sha256={result['zip_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
