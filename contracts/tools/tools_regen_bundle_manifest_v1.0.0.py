#!/usr/bin/env python3
"""
tools_regen_bundle_manifest_v1.0.0.py

Utility to regenerate bundle.manifest.json with sha256 + bytes for all JSON artifacts
(excluding the manifest itself), and optionally normalize suite_schema across artifacts.

This is intended as a mechanical step during mass regeneration after CS/TG/CG changes.

Usage:
  python tools_regen_bundle_manifest_v1.0.0.py \
    --in  contracts/LED-1_bundle_v1.3.1_JSON_ONLY.zip \
    --out contracts/LED-1_bundle_v1.3.1_JSON_ONLY.zip \
    --suite-schema CS-0@2.2.0

Notes:
- This tool does NOT change doc_id/version or rename files. If you bump versions,
  do that first (or regenerate the artifacts) and then run this tool on the final zip.
- The manifest lists only JSON artifacts (excluding itself), as paths relative to the bundle root.
"""

import argparse
import json
import os
import zipfile
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def read_zip(zip_path: str) -> Tuple[List[str], Dict[str, bytes]]:
    with zipfile.ZipFile(zip_path, "r") as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        raw = {n: z.read(n) for n in names}
        return names, raw

def write_zip(zip_path: str, entries: Dict[str, bytes]) -> None:
    tmp = zip_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in entries.items():
            z.writestr(name, content)
    os.replace(tmp, zip_path)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_zip", required=True, help="Input bundle zip path.")
    p.add_argument("--out", dest="out_zip", required=True, help="Output bundle zip path (can overwrite input).")
    p.add_argument("--suite-schema", dest="suite_schema", required=False, help="If set, overwrite suite_schema in all JSON artifacts.")
    args = p.parse_args()

    names, raw = read_zip(args.in_zip)
    top_dirs = sorted({n.split("/")[0] for n in names if "/" in n})
    if len(top_dirs) != 1:
        raise SystemExit(f"Expected exactly 1 top-level dir in zip, found: {top_dirs}")
    bundle_dir = top_dirs[0]
    prefix = bundle_dir + "/"

    # Parse JSON artifacts
    json_docs: Dict[str, Any] = {}
    for name, b in raw.items():
        if name.endswith(".json"):
            json_docs[name] = json.loads(b.decode("utf-8"))

    manifest_name = next((n for n,d in json_docs.items() if d.get("artifact_kind") == "bundle_manifest"), None)
    if not manifest_name:
        raise SystemExit("No bundle_manifest found in zip.")

    # Update suite_schema (optional)
    if args.suite_schema:
        for name, doc in json_docs.items():
            if name.endswith(".json"):
                doc["suite_schema"] = args.suite_schema

    # Build manifest.files: every JSON except the manifest itself
    artifact_names = sorted([n for n in names if n.startswith(prefix) and n.endswith(".json") and n != manifest_name])
    files = []
    for full in artifact_names:
        rel = full[len(prefix):]
        b = raw[full]
        files.append({"path": rel, "sha256": sha256_bytes(b), "bytes": len(b)})

    manifest = json_docs[manifest_name]
    manifest["files"] = files
    manifest["generated_at_utc"] = now_utc()
    if args.suite_schema:
        manifest["suite_schema"] = args.suite_schema

    # Re-encode updated JSON files back into raw entries (deterministic: sort_keys + indent)
    for name, doc in json_docs.items():
        if name.endswith(".json"):
            raw[name] = json.dumps(doc, indent=2, sort_keys=True).encode("utf-8")

    write_zip(args.out_zip, raw)
    print(f"OK: updated manifest + suite_schema in {args.out_zip}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
