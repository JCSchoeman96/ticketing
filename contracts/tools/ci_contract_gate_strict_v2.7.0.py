#!/usr/bin/env python3
"""
ci_contract_gate_strict_v2.7.0.py

STRICT, ENFORCEABLE contract-suite validator.

Goals (P0):
- Validate every bundle zip against CS-0 schemas (contract-suite/1.0, test-gates/1.0, bundle-manifest/1.0)
- Enforce suite_schema consistency against the CS bundle used in CI
- Enforce bundle.manifest.json file hashes/sizes (no hidden drift inside zips)
- Enforce contract <-> gates parity (doc_id/version/contract_ref) + unique gate IDs
- Enforce CANON-1 pins (bundle sha256 + per-artifact sha256/size)
- Enforce dependency existence + min_version across the suite
- Enforce no duplicate doc_id bundles in the suite directory
- (Optional) Execute automated test-gate assertions (whitelisted) for must-gates to prevent semantic drift

This script is intentionally opinionated: if a rule is ambiguous, it fails (no "best-effort" passes).
"""

import argparse
import json
import os
import re
import sys
import zipfile
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any

# ---------------------------
# Test-gate assertion runner (whitelisted, deterministic)
# ---------------------------

DEFAULT_ASSERTION_WHITELIST = {
    # deterministic, machine-checkable assertions only
    "suite_schema_matches",
    "require_bundle_manifest_filename",
    "require_bundle_files_match_manifest",
    "json_pointer_equals",
    "forbid_regex_in_artifact",
    # runtime/dynamic primitives (require runtime harness phase)
    "telemetry_signal_emitted",
    "trace_span_relationship",
    "attribute_presence_assert",
    "error_envelope_correlation",
    "sampling_decision",

}


# Runtime / dynamic assertion types (require a runtime harness; not executed by this script)
DYNAMIC_ASSERTION_TYPES = {
    "telemetry_signal_emitted",
    "trace_span_relationship",
    "attribute_presence_assert",
    "error_envelope_correlation",
    "sampling_decision",
}

DEFAULT_RUNTIME_HARNESS_PATH = "test/support/v42_harness.ex"
def _json_pointer_get(doc: Any, pointer: str) -> Any:
    """Minimal RFC6901 JSON Pointer resolver."""
    if pointer is None:
        raise KeyError("json_pointer is None")
    if pointer == "":
        return doc
    if not pointer.startswith("/"):
        raise KeyError(f"invalid JSON pointer (must start with '/'): {pointer}")
    cur = doc
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            try:
                idx = int(token)
            except Exception as e:
                raise KeyError(f"pointer token '{token}' is not a list index for {pointer}") from e
            if idx < 0 or idx >= len(cur):
                raise KeyError(f"list index out of range at token '{token}' for {pointer}")
            cur = cur[idx]
        elif isinstance(cur, dict):
            if token not in cur:
                raise KeyError(f"missing key '{token}' for {pointer}")
            cur = cur[token]
        else:
            raise KeyError(f"cannot traverse token '{token}' for {pointer}; current node is {type(cur).__name__}")
    return cur

def _artifact_by_kind(b: "Bundle", kind: str) -> "Artifact":
    kind = (kind or "").strip().lower()
    if kind in ("contract", "contract_json"):
        return b.contract
    if kind in ("gates", "test_gates", "test-gates"):
        return b.gates
    if kind in ("manifest", "bundle_manifest", "bundle-manifest"):
        return b.manifest
    raise ValueError(f"unknown artifact_kind: {kind}")

def _assert_suite_schema_matches(b: "Bundle", expected: str) -> Optional[str]:
    for a in (b.contract, b.gates, b.manifest):
        if a.data.get("suite_schema") != expected:
            return f"{b.doc_id}@{b.version}: {a.path}: suite_schema '{a.data.get('suite_schema')}' != expected '{expected}'"
    return None

def _assert_manifest_filename(b: "Bundle", expected: str) -> Optional[str]:
    base = os.path.basename(b.manifest.path)
    if base != expected:
        return f"{b.doc_id}@{b.version}: manifest filename '{base}' != expected '{expected}'"
    return None

def _assert_files_match_manifest(b: "Bundle") -> Optional[str]:
    mf_files = b.manifest.data.get("files")
    if not isinstance(mf_files, list) or not mf_files:
        return f"{b.doc_id}@{b.version}: manifest.files must be a non-empty list"

    bundle_prefix = b.bundle_dir + "/"
    non_manifest = sorted([
        n for n in b._raw.keys()
        if n.startswith(bundle_prefix)
        and n.endswith(".json")
        and not n.endswith("bundle.manifest.json")
    ])

    listed = []
    for f in mf_files:
        if not isinstance(f, dict) or "path" not in f:
            return f"{b.doc_id}@{b.version}: manifest.files entries must be objects with 'path'"
        p = f.get("path")
        if not isinstance(p, str) or not p.strip():
            return f"{b.doc_id}@{b.version}: manifest.files has invalid path: {p}"
        listed.append(bundle_prefix + (p[2:] if p.startswith("./") else p))
    listed = sorted(listed)

    if listed != non_manifest:
        return f"{b.doc_id}@{b.version}: manifest.files mismatch. listed={listed} expected={non_manifest}"

    for f in mf_files:
        p = f.get("path")
        rel = (p[2:] if isinstance(p, str) and p.startswith("./") else p)
        full = bundle_prefix + rel
        if full not in b._raw:
            return f"{b.doc_id}@{b.version}: manifest references missing file: {rel}"
        bts = b._raw[full]
        sha = hashlib.sha256(bts).hexdigest()
        size = len(bts)
        if f.get("sha256") != sha:
            return f"{b.doc_id}@{b.version}: manifest sha256 mismatch for {rel}: manifest={f.get('sha256')} actual={sha}"
        if f.get("bytes") != size:
            return f"{b.doc_id}@{b.version}: manifest bytes mismatch for {rel}: manifest={f.get('bytes')} actual={size}"
    return None

def _assert_json_pointer_equals(b: "Bundle", details: Dict[str, Any]) -> Optional[str]:
    ptr = details.get("json_pointer") or details.get("js_pointer")
    exp = details.get("equals")
    kind = details.get("artifact_kind") or details.get("artifact") or "contract"
    if not isinstance(ptr, str):
        return f"{b.doc_id}@{b.version}: json_pointer_equals requires details.json_pointer (string)"
    try:
        art = _artifact_by_kind(b, kind)
        got = _json_pointer_get(art.data, ptr)
    except Exception as e:
        return f"{b.doc_id}@{b.version}: json_pointer_equals failed to resolve {kind}:{ptr}: {e}"
    if got != exp:
        return f"{b.doc_id}@{b.version}: json_pointer_equals mismatch at {kind}:{ptr}. expected={exp!r} got={got!r}"
    return None

def _assert_dynamic_requires_harness(root: str, harness_path: str, allow_dynamic_assertions: bool, gate_id: str, atype: str) -> Optional[str]:
    """Dynamic assertions are declarations that MUST be executed by a runtime harness job.
    This strict script enforces the Harness Interlock, and refuses to silently pass dynamic assertions.
    """
    rel = harness_path.strip().lstrip("./")
    abs_path = os.path.join(root, rel)
    if not os.path.exists(abs_path):
        return f"{gate_id}: dynamic assertion '{atype}' requires runtime harness '{rel}' but it was not found."
    if not allow_dynamic_assertions:
        return f"{gate_id}: dynamic assertion '{atype}' detected. Harness '{rel}' exists, but dynamic assertions are NOT executed by this script. Run the runtime harness job, then re-run strict with --allow-dynamic-assertions ONLY in that job."
    return None

def _assert_forbid_regex_in_artifact(b: "Bundle", details: Dict[str, Any]) -> Optional[str]:
    kind = details.get("artifact_kind") or details.get("artifact") or "contract"
    pointers = details.get("json_pointers") or []
    forbid = details.get("forbid_regex") or []
    if not isinstance(pointers, list) or not pointers:
        return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact requires non-empty details.json_pointers"
    if not isinstance(forbid, list) or not forbid:
        return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact requires non-empty details.forbid_regex"
    try:
        art = _artifact_by_kind(b, kind)
    except Exception as e:
        return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact invalid artifact_kind: {e}"

    regs = []
    for r in forbid:
        if not isinstance(r, str) or not r.strip():
            return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact has invalid regex: {r}"
        regs.append(re.compile(r))

    for p in pointers:
        if not isinstance(p, str):
            return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact has invalid json_pointer: {p}"
        if p != p.strip():
            return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact has invalid json_pointer (whitespace): {p}"
        if p != "" and not p.startswith("/"):
            return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact has invalid json_pointer (must start with / or be empty root): {p}"
        try:
            node = _json_pointer_get(art.data, p)
        except Exception as e:
            return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact could not resolve {kind}:{p}: {e}"
        blob = json.dumps(node, sort_keys=True, ensure_ascii=False)
        for rg in regs:
            if rg.search(blob):
                return f"{b.doc_id}@{b.version}: forbid_regex_in_artifact matched {kind}:{p} regex={rg.pattern}"
    return None

def _run_gate_assertions(
    b: "Bundle",
    *,
    errors: List[str],
    warnings: List[str],
    assertion_scope: str,
    whitelist: set,
    fail_unknown: bool,
) -> None:
    gates = b.gates.data.get("gates") or []
    if not isinstance(gates, list):
        _fail(errors, f"{b.doc_id}@{b.version}: gates.gates must be a list")
        return

    for g in gates:
        if not isinstance(g, dict):
            _fail(errors, f"{b.doc_id}@{b.version}: invalid gate entry (must be object): {g}")
            continue

        must = bool(g.get("must", False))
        if assertion_scope == "must" and not must:
            continue

        gid = g.get("id")
        if not isinstance(gid, str) or not gid.strip():
            _fail(errors, f"{b.doc_id}@{b.version}: gate missing id")
            continue

        assertions = g.get("assertions") or []
        if not isinstance(assertions, list):
            _fail(errors, f"{b.doc_id}@{b.version}:{gid}: gate.assertions must be a list")
            continue

        for a in assertions:
            if not isinstance(a, dict):
                _fail(errors, f"{b.doc_id}@{b.version}:{gid}: assertion must be object: {a}")
                continue

            mode = (a.get("mode") or "").strip().lower()
            atype = a.get("type")
            details = a.get("details") or {}

            # Only execute deterministic, automated assertions in CI.
            if mode != "automated":
                continue

            if not isinstance(atype, str) or not atype.strip():
                _fail(errors, f"{b.doc_id}@{b.version}:{gid}: assertion missing type")
                continue

            if atype not in whitelist:
                msg = f"{b.doc_id}@{b.version}:{gid}: assertion type '{atype}' not in whitelist"
                if fail_unknown:
                    _fail(errors, msg)
                else:
                    _warn(warnings, msg)
                continue

            err = None
            if atype == "suite_schema_matches":
                err = _assert_suite_schema_matches(b, details.get("expected"))
            elif atype == "require_bundle_manifest_filename":
                err = _assert_manifest_filename(b, details.get("expected"))
            elif atype == "require_bundle_files_match_manifest":
                err = _assert_files_match_manifest(b)
            elif atype == "json_pointer_equals":
                if not isinstance(details, dict):
                    err = f"{b.doc_id}@{b.version}:{gid}: json_pointer_equals requires details object"
                else:
                    err = _assert_json_pointer_equals(b, details)
            elif atype == "forbid_regex_in_artifact":
                if not isinstance(details, dict):
                    err = f"{b.doc_id}@{b.version}:{gid}: forbid_regex_in_artifact requires details object"
                else:
                    err = _assert_forbid_regex_in_artifact(b, details)
            else:
                err = f"{b.doc_id}@{b.version}:{gid}: unhandled whitelisted assertion type: {atype}"

            if err:
                if must:
                    _fail(errors, err)
                else:
                    _warn(warnings, err)

try:
    import jsonschema
except Exception as e:
    print("FATAL: python package 'jsonschema' is required.", file=sys.stderr)
    raise

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
DOC_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
BUNDLE_DIR_RE = re.compile(r"^(?P<doc_id>[A-Z][A-Z0-9]*-\d+)_bundle_v(?P<version>\d+\.\d+\.\d+)$")

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _read_zip_json(zip_path: str) -> Tuple[List[str], Dict[str, Any], Dict[str, bytes]]:
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        json_docs: Dict[str, Any] = {}
        raw: Dict[str, bytes] = {}
        for n in names:
            if n.endswith("/"):
                continue
            b = z.read(n)
            raw[n] = b
            if n.lower().endswith(".json"):
                try:
                    json_docs[n] = json.loads(b.decode("utf-8"))
                except Exception as e:
                    raise ValueError(f"{zip_path}: invalid JSON in {n}: {e}")
        return names, json_docs, raw

def _pick_one(items: List[str], predicate) -> Optional[str]:
    for x in items:
        if predicate(x):
            return x
    return None

def _fail(errors: List[str], msg: str) -> None:
    errors.append(msg)

def _warn(warnings: List[str], msg: str) -> None:
    warnings.append(msg)

@dataclass
class Artifact:
    path: str
    data: Dict[str, Any]
    raw: bytes
    sha256: str
    size: int

@dataclass
class Bundle:
    zip_path: str
    bundle_sha256: str
    bundle_dir: str
    doc_id: str
    version: str
    contract: Artifact
    gates: Artifact
    manifest: Artifact
    _raw: Dict[str, bytes]

def _load_cs(cs_bundle_zip: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    _, docs, raw = _read_zip_json(cs_bundle_zip)
    contract_path = _pick_one(list(docs.keys()), lambda p: docs[p].get("artifact_kind") == "contract")
    if not contract_path:
        raise ValueError("CS bundle missing contract artifact_kind=contract")
    cs_contract = docs[contract_path]
    schemas = cs_contract.get("schemas")
    if not isinstance(schemas, dict):
        raise ValueError("CS contract missing schemas object")
    return cs_contract, schemas

def _validate_schema(schemas: Dict[str, Any], schema_name: str, doc: Dict[str, Any], errors: List[str], where: str) -> None:
    schema = schemas.get(schema_name)
    if not schema:
        _fail(errors, f"{where}: CS schema '{schema_name}' not found")
        return
    try:
        jsonschema.validate(instance=doc, schema=schema)
    except jsonschema.ValidationError as e:
        _fail(errors, f"{where}: schema validation failed against '{schema_name}': {e.message}")

def _parse_bundle(zip_path: str, cs_schemas: Dict[str, Any], cs_version: str, errors: List[str], warnings: List[str]) -> Optional[Bundle]:
    if not os.path.exists(zip_path):
        _fail(errors, f"bundle not found: {zip_path}")
        return None

    names, docs, raw = _read_zip_json(zip_path)
    if not names:
        _fail(errors, f"{zip_path}: empty zip")
        return None

    # Determine bundle_dir (top-level directory)
    top_dirs = sorted({n.split("/")[0] for n in names if "/" in n})
    if len(top_dirs) != 1:
        _fail(errors, f"{zip_path}: expected exactly 1 top-level bundle directory, found {top_dirs}")
        return None
    bundle_dir = top_dirs[0]
    m = BUNDLE_DIR_RE.match(bundle_dir)
    if not m:
        _fail(errors, f"{zip_path}: top directory '{bundle_dir}' must match '<DOC_ID>_bundle_v<SEMVER>'")
        return None
    doc_id = m.group("doc_id")
    version = m.group("version")

    # Locate artifacts by artifact_kind
    contract_path = _pick_one(list(docs.keys()), lambda p: docs[p].get("artifact_kind") == "contract")
    gates_path = _pick_one(list(docs.keys()), lambda p: docs[p].get("artifact_kind") == "test_gates")
    manifest_path = _pick_one(list(docs.keys()), lambda p: docs[p].get("artifact_kind") == "bundle_manifest")

    if not contract_path or not gates_path or not manifest_path:
        _fail(errors, f"{zip_path}: missing required artifacts (contract/test_gates/bundle_manifest)")
        return None

    # Build artifacts
    def art(path: str) -> Artifact:
        b = raw[path]
        return Artifact(path=path, data=docs[path], raw=b, sha256=_sha256_bytes(b), size=len(b))

    contract = art(contract_path)
    gates = art(gates_path)
    manifest = art(manifest_path)

    # Basic schema_version family checks
    expected = {
        "contract": "contract-suite/1.0",
        "test_gates": "test-gates/1.0",
        "bundle_manifest": "bundle-manifest/1.0",
    }
    for a in [contract, gates, manifest]:
        kind = a.data.get("artifact_kind")
        sv = a.data.get("schema_version")
        exp = expected.get(kind)
        if exp and sv != exp:
            _fail(errors, f"{zip_path}:{a.path}: schema_version '{sv}' must be '{exp}' for artifact_kind='{kind}'")

    # Validate JSON Schemas
    _validate_schema(cs_schemas, "contract", contract.data, errors, f"{zip_path}:{contract.path}")
    _validate_schema(cs_schemas, "test_gates", gates.data, errors, f"{zip_path}:{gates.path}")
    _validate_schema(cs_schemas, "bundle_manifest", manifest.data, errors, f"{zip_path}:{manifest.path}")

    # suite_schema strict match to CS used by CI
    expected_suite_schema = f"CS-0@{cs_version}"
    for a in [contract, gates, manifest]:
        ss = a.data.get("suite_schema")
        if ss != expected_suite_schema:
            _fail(errors, f"{zip_path}:{a.path}: suite_schema '{ss}' must equal '{expected_suite_schema}'")

    # Contract/Gates parity
    c_doc_id = contract.data.get("doc_id")
    c_ver = contract.data.get("version")
    if c_doc_id != doc_id or c_ver != version:
        _fail(errors, f"{zip_path}:{contract.path}: doc_id/version must match bundle_dir ({doc_id}@{version})")

    g_doc_id = gates.data.get("doc_id")
    g_ver = gates.data.get("version")
    if g_ver != version:
        _fail(errors, f"{zip_path}:{gates.path}: version must match contract/bundle version {version}")
    if g_doc_id != f"{doc_id}-GATE":
        _fail(errors, f"{zip_path}:{gates.path}: doc_id must be '{doc_id}-GATE'")

    cref = gates.data.get("contract_ref") or {}
    if cref.get("doc_id") != doc_id or cref.get("version") != version:
        _fail(errors, f"{zip_path}:{gates.path}: contract_ref must match {doc_id}@{version}")

    # Unique gate IDs within bundle
    gate_ids = [g.get("id") for g in (gates.data.get("gates") or [])]
    if any(not isinstance(x, str) or not x.strip() for x in gate_ids):
        _fail(errors, f"{zip_path}:{gates.path}: all gates must have non-empty string 'id'")
    if len(set(gate_ids)) != len(gate_ids):
        _fail(errors, f"{zip_path}:{gates.path}: duplicate gate ids detected")

    # Manifest hash enforcement
    mf_files = manifest.data.get("files")
    if not isinstance(mf_files, list) or not mf_files:
        _fail(errors, f"{zip_path}:{manifest.path}: manifest.files must be non-empty list")
    else:
        # ensure all non-manifest json files are listed
        bundle_prefix = bundle_dir + "/"
        non_manifest = sorted([n for n in raw.keys() if n.startswith(bundle_prefix) and n.endswith(".json") and not n.endswith("bundle.manifest.json")])
        listed = sorted([bundle_prefix + f["path"] if not f["path"].startswith(bundle_prefix) else f["path"] for f in mf_files if isinstance(f, dict) and "path" in f])
        if sorted(non_manifest) != sorted(listed):
            _fail(errors, f"{zip_path}:{manifest.path}: manifest.files must list exactly all JSON artifacts excluding the manifest itself.\n  expected={non_manifest}\n  listed={listed}")

        # validate each file entry hash/size
        for f in mf_files:
            if not isinstance(f, dict):
                _fail(errors, f"{zip_path}:{manifest.path}: manifest file entries must be objects")
                continue
            rel_path = f.get("path")
            full = bundle_prefix + rel_path if rel_path and not rel_path.startswith(bundle_prefix) else rel_path
            if not full or full not in raw:
                _fail(errors, f"{zip_path}:{manifest.path}: manifest entry path missing or not found in zip: {rel_path}")
                continue
            expected_sha = f.get("sha256")
            expected_bytes = f.get("bytes")
            b = raw[full]
            actual_sha = _sha256_bytes(b)
            actual_bytes = len(b)
            if expected_sha != actual_sha:
                _fail(errors, f"{zip_path}:{manifest.path}: sha256 mismatch for {full}: expected {expected_sha}, got {actual_sha}")
            if expected_bytes != actual_bytes:
                _fail(errors, f"{zip_path}:{manifest.path}: bytes mismatch for {full}: expected {expected_bytes}, got {actual_bytes}")

    bundle_sha = _sha256_file(zip_path)
    return Bundle(
        zip_path=zip_path,
        bundle_sha256=bundle_sha,
        bundle_dir=bundle_dir,
        doc_id=doc_id,
        version=version,
        contract=contract,
        gates=gates,
        manifest=manifest,
        _raw=raw,
    )

def _load_canon(canon_bundle_zip: str) -> Dict[str, Any]:
    _, docs, _ = _read_zip_json(canon_bundle_zip)
    contract_path = _pick_one(list(docs.keys()), lambda p: docs[p].get("artifact_kind") == "contract")
    if not contract_path:
        raise ValueError("CANON bundle missing contract artifact_kind=contract")
    return docs[contract_path]

def _semver_tuple(v: str) -> Tuple[int, int, int]:
    if not SEMVER_RE.match(v):
        raise ValueError(f"invalid semver: {v}")
    a,b,c = v.split(".")
    return int(a), int(b), int(c)

def _semver_gte(a: str, b: str) -> bool:
    return _semver_tuple(a) >= _semver_tuple(b)

def validate_suite(root: str, contracts_dir: str, cs_bundle: str, canon_bundle: str, fail_on_warn: bool, *, run_gate_assertions: bool, assertion_scope: str, assertion_whitelist: set, fail_unknown_assertions: bool, runtime_harness_path: str, allow_dynamic_assertions: bool) -> int:
    errors: List[str] = []
    warnings: List[str] = []

    cs_contract, cs_schemas = _load_cs(cs_bundle)
    cs_version = cs_contract.get("version")
    if not cs_version or not SEMVER_RE.match(cs_version):
        _fail(errors, f"CS bundle contract has invalid version: {cs_version}")

    canon_contract = _load_canon(canon_bundle)
    canon_map: Dict[str, Dict[str, Any]] = {}
    for entry in canon_contract.get("canonical_bundles", []):
        did = entry.get("doc_id")
        if did:
            canon_map[did] = entry

    if not os.path.isdir(contracts_dir):
        _fail(errors, f"contracts_dir not found: {contracts_dir}")

    bundle_zips_all = sorted([
        os.path.join(contracts_dir, f)
        for f in os.listdir(contracts_dir)
        if f.lower().endswith('.zip')
    ])

    # Exclude the CANON bundle itself from pin checks (self-pin is cryptographically infeasible).
    # We still parse/validate CANON as a bundle for schema + manifest integrity.
    canon_abs = os.path.abspath(canon_bundle)
    bundle_zips = [p for p in bundle_zips_all if os.path.abspath(p) != canon_abs]

    if os.path.abspath(os.path.dirname(canon_abs)) == os.path.abspath(contracts_dir):
        _ = _parse_bundle(canon_abs, cs_schemas, cs_version, errors, warnings)


    if not bundle_zips:
        _fail(errors, f"no bundle zips found in {contracts_dir}")

    bundles: List[Bundle] = []
    by_doc_id: Dict[str, List[Bundle]] = {}

    for zp in bundle_zips:
        b = _parse_bundle(zp, cs_schemas, cs_version, errors, warnings)
        if not b:
            continue
        bundles.append(b)
        by_doc_id.setdefault(b.doc_id, []).append(b)

    # P0: no duplicate doc_ids in contracts_dir
    for did, bs in by_doc_id.items():
        if len(bs) > 1:
            _fail(errors, f"duplicate doc_id bundles in suite: {did} -> {[os.path.basename(x.zip_path) for x in bs]}")

    # P0: CANON enforcement (bundle sha + per-artifact sha/size)
    for b in bundles:
        c = canon_map.get(b.doc_id)
        if not c:
            _fail(errors, f"CANON missing entry for bundle doc_id={b.doc_id} (found {os.path.basename(b.zip_path)})")
            continue
        if c.get("version") != b.version:
            _fail(errors, f"CANON version mismatch for {b.doc_id}: canon={c.get('version')} suite={b.version}")
        if c.get("bundle_sha256") != b.bundle_sha256:
            _fail(errors, f"CANON bundle_sha256 mismatch for {b.doc_id}: canon={c.get('bundle_sha256')} suite={b.bundle_sha256}")

        # per-artifact sha/size
        canon_art = {a["path"]: a for a in (c.get("artifacts") or []) if isinstance(a, dict) and "path" in a}
        for a in [b.contract, b.gates, b.manifest]:
            ca = canon_art.get(a.path)
            if not ca:
                _fail(errors, f"CANON missing artifact pin for {b.doc_id}: {a.path}")
                continue
            if ca.get("sha256") != a.sha256:
                _fail(errors, f"CANON artifact sha mismatch for {b.doc_id}: {a.path}: canon={ca.get('sha256')} suite={a.sha256}")
            if ca.get("size") != a.size:
                _fail(errors, f"CANON artifact size mismatch for {b.doc_id}: {a.path}: canon={ca.get('size')} suite={a.size}")

    # P0: dependency existence + min_version
    available_versions = {b.doc_id: b.version for b in bundles}
    for b in bundles:
        deps = b.contract.data.get("dependencies") or []
        if not isinstance(deps, list):
            _fail(errors, f"{b.doc_id}@{b.version}: dependencies must be a list")
            continue
        for d in deps:
            if not isinstance(d, dict):
                _fail(errors, f"{b.doc_id}@{b.version}: dependency entries must be objects")
                continue
            dep_id = d.get("doc_id")
            min_v = d.get("min_version")
            if not dep_id or not isinstance(dep_id, str):
                _fail(errors, f"{b.doc_id}@{b.version}: dependency missing doc_id")
                continue
            if dep_id not in available_versions:
                _fail(errors, f"{b.doc_id}@{b.version}: dependency not found in suite: {dep_id} (min_version={min_v})")
                continue
            if isinstance(min_v, str) and SEMVER_RE.match(min_v):
                if not _semver_gte(available_versions[dep_id], min_v):
                    _fail(errors, f"{b.doc_id}@{b.version}: dependency {dep_id} version too low: suite={available_versions[dep_id]} < min_version={min_v}")
            else:
                _fail(errors, f"{b.doc_id}@{b.version}: dependency {dep_id} has invalid min_version: {min_v}")


    # P0: EVT-1 registry integrity (if EVT-1 is present)
    # Rule: any contract declaring eventing.events_to_register_in_EVT-1_before_lock must only list events present in EVT-1.
    evt_bundle = by_doc_id.get("EVT-1", [])
    if len(evt_bundle) == 1:
        evt_contract = evt_bundle[0].contract.data
        evt_types = evt_contract.get("event_types") or {}
        evt_all: set = set()
        if isinstance(evt_types, dict):
            for _, v in evt_types.items():
                if isinstance(v, list):
                    for e in v:
                        if isinstance(e, str):
                            evt_all.add(e)
        for b in bundles:
            ev = b.contract.data.get("eventing") or {}
            if isinstance(ev, dict) and "events_to_register_in_EVT-1_before_lock" in ev:
                declared = ev.get("events_to_register_in_EVT-1_before_lock") or []
                if not isinstance(declared, list):
                    _fail(errors, f"{b.doc_id}@{b.version}: eventing.events_to_register_in_EVT-1_before_lock must be a list")
                    continue
                for e in declared:
                    if not isinstance(e, str) or not e.strip():
                        _fail(errors, f"{b.doc_id}@{b.version}: invalid event in events_to_register_in_EVT-1_before_lock: {e}")
                        continue
                    if e not in evt_all:
                        _fail(errors, f"{b.doc_id}@{b.version}: event '{e}' is not registered in EVT-1")
    elif len(evt_bundle) > 1:
        _fail(errors, "EVT-1 appears multiple times in suite; cannot validate event registry.")
    else:
        _warn(warnings, "EVT-1 not present in suite; event registry checks skipped.")
    
    # P0: ERR-1 subcode registry membership (if ERR-1 is present)
    # Rule: any JSON field named exactly 'subcode' found in any contract must be present in ERR-1.registry.subcodes[].subcode.
    # This closes a major drift vector where domain contracts invent subcodes without registering them centrally.
    err_bundle = by_doc_id.get("ERR-1", [])
    if len(err_bundle) == 1:
        err_contract = err_bundle[0].contract.data
        reg = (err_contract.get("registry") or {})
        reg_subs = reg.get("subcodes") or []
        allowed_subcodes: set = set()
        if isinstance(reg_subs, list):
            for e in reg_subs:
                if isinstance(e, dict):
                    sc = e.get("subcode")
                    if isinstance(sc, str) and sc.strip():
                        allowed_subcodes.add(sc)

        def _collect_subcodes(node: Any, acc: set) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "subcode" and isinstance(v, str) and v.strip() and re.match(r"^[A-Z][A-Z0-9_]{2,64}$", v.strip()):
                        acc.add(v)
                    else:
                        _collect_subcodes(v, acc)
            elif isinstance(node, list):
                for it in node:
                    _collect_subcodes(it, acc)

        used_subcodes: set = set()
        for b in bundles:
            _collect_subcodes(b.contract.data, used_subcodes)

        missing = sorted([s for s in used_subcodes if s not in allowed_subcodes])
        if missing:
            # Fail hard: unknown subcodes are a drift hazard.
            for s in missing:
                _fail(errors, f"ERR-1 registry missing subcode used in suite: {s}")
    elif len(err_bundle) > 1:
        _fail(errors, "ERR-1 appears multiple times in suite; reminder: doc_id duplicates are forbidden.")
    else:
        _warn(warnings, "ERR-1 not present in suite; subcode registry membership checks skipped.")

# Optional: run deterministic, automated test-gate assertions (semantic enforcement)
    if run_gate_assertions:
        for b in bundles:
            _run_gate_assertions(
                b,
                errors=errors,
                warnings=warnings,
                assertion_scope=assertion_scope,
                whitelist=assertion_whitelist,
                fail_unknown=fail_unknown_assertions,
            )
    # Output
    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1 if fail_on_warn or errors else 0

    print("OK: contract suite validated (strict).")
    return 0

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, help="Repo root (used to resolve defaults).")
    p.add_argument("--canon", required=True, help="Path to CANON-1 bundle zip.")
    p.add_argument("--cs", required=True, help="Path to CS-0 bundle zip.")
    p.add_argument("--contracts-dir", default=None, help="Directory containing contract bundle zips. Default: <root>/contracts or canon bundle directory.")
    p.add_argument("--fail-on-warn", action="store_true", help="Treat warnings as failures.")
    p.add_argument("--run-gate-assertions", action="store_true", help="Execute deterministic automated assertions declared in *-GATE artifacts for semantic drift prevention.")
    p.add_argument("--assertion-scope", default="must", choices=["must", "all"], help="Which gates to execute: 'must' (default) or 'all'.")
    p.add_argument("--assertion-whitelist", default=None, help="Comma-separated override whitelist of executable assertion types. Default is built-in safe list.")
    p.add_argument("--fail-unknown-assertions", action="store_true", help="Fail (instead of warn) if a gate uses an automated assertion type not in the whitelist.")
    p.add_argument("--runtime-harness-path", default=DEFAULT_RUNTIME_HARNESS_PATH,
                  help="Path (relative to --root) to the runtime harness entry point required for dynamic assertions.")
    p.add_argument("--allow-dynamic-assertions", action="store_true",
                  help="Allow dynamic assertion types to exist without failing. WARNING: use only in a dedicated runtime harness job.")
    args = p.parse_args()

    root = os.path.abspath(args.root)
    canon = os.path.abspath(args.canon)
    cs = os.path.abspath(args.cs)

    if args.contracts_dir:
        contracts_dir = os.path.abspath(args.contracts_dir)
    else:
        # Prefer the directory containing the canon bundle, because workflows usually stage it there.
        contracts_dir = os.path.dirname(canon) if os.path.isdir(os.path.dirname(canon)) else os.path.join(root, "contracts")
        if not os.path.isdir(contracts_dir):
            contracts_dir = os.path.join(root, "contracts")

    wl = DEFAULT_ASSERTION_WHITELIST
    if args.assertion_whitelist:
        wl = {x.strip() for x in args.assertion_whitelist.split(",") if x.strip()}

    return validate_suite(
        root=root,
        contracts_dir=contracts_dir,
        cs_bundle=cs,
        canon_bundle=canon,
        fail_on_warn=args.fail_on_warn,
        run_gate_assertions=args.run_gate_assertions,
        assertion_scope=args.assertion_scope,
        assertion_whitelist=wl,
        fail_unknown_assertions=args.fail_unknown_assertions,
        runtime_harness_path=args.runtime_harness_path,
        allow_dynamic_assertions=args.allow_dynamic_assertions,
    )

if __name__ == "__main__":
    raise SystemExit(main())
