#!/usr/bin/env python3
"""
canon_sync_from_bundles.py (pinned)

- CANON entries live at: /planned_docs
- We sync /planned_docs to include each bundle zip in contracts/bundles
- We do NOT touch /planned_docs[*]/dependencies
"""

import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

BUNDLE_ZIP_RE = re.compile(r".+_bundle_v.+_JSON_ONLY\.zip$")

def die(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def read_bundle_doc_id_version(zip_path: Path) -> Tuple[str, str]:
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        contract_files = [n for n in names if n.endswith(".json") and "_Contract_v" in n]
        if not contract_files:
            die(f"no *_Contract_v*.json found inside bundle: {zip_path.name}")

        # Prefer shortest contract path
        contract_files.sort(key=len)
        contract_name = contract_files[0]
        data = json.loads(z.read(contract_name).decode("utf-8"))

        doc_id = data.get("doc_id")
        version = data.get("version")

        if not isinstance(doc_id, str) or not doc_id:
            die(f"{zip_path.name}: contract missing doc_id")
        if not isinstance(version, str) or not version:
            die(f"{zip_path.name}: contract missing version")

        return doc_id, version

def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: canon_sync_from_bundles.py <canon_contract_json_path> <bundles_dir>", file=sys.stderr)
        return 2

    canon_path = Path(sys.argv[1]).resolve()
    bundles_dir = Path(sys.argv[2]).resolve()

    if not canon_path.exists():
        die(f"canon contract not found: {canon_path}")
    if not bundles_dir.exists():
        die(f"bundles dir not found: {bundles_dir}")

    canon = load_json(canon_path)

    planned_docs = canon.get("planned_docs")
    if not isinstance(planned_docs, list):
        die("CANON contract missing 'planned_docs' list at top level")

    # Map existing entries by doc_id
    existing: Dict[str, Dict[str, Any]] = {}
    for e in planned_docs:
        if isinstance(e, dict) and isinstance(e.get("doc_id"), str):
            existing[e["doc_id"]] = e

    bundle_zips = sorted([p for p in bundles_dir.iterdir() if p.is_file() and BUNDLE_ZIP_RE.match(p.name)])
    if not bundle_zips:
        die(f"no bundle zips found in {bundles_dir}")

    changed = 0

    for z in bundle_zips:
        doc_id, version = read_bundle_doc_id_version(z)

        # Optional: keep CANON self-listing off unless you explicitly want it
        if doc_id == "CANON-1":
            continue

        if doc_id not in existing:
            # Minimal safe shape: doc_id + version (DON'T invent more fields)
            new_entry = {"doc_id": doc_id, "version": version}
            planned_docs.append(new_entry)
            existing[doc_id] = new_entry
            changed += 1
            print(f"ADD: {doc_id}@{version}")
        else:
            if existing[doc_id].get("version") != version:
                old = existing[doc_id].get("version")
                existing[doc_id]["version"] = version
                changed += 1
                print(f"UPDATE: {doc_id} {old} -> {version}")

    # Stable sort planned_docs by doc_id then version (keeps diffs clean)
    def sort_key(e: Any) -> Tuple[str, str]:
        if not isinstance(e, dict):
            return ("~", "~")
        return (str(e.get("doc_id") or ""), str(e.get("version") or ""))

    planned_docs.sort(key=sort_key)

    if changed:
        save_json(canon_path, canon)
        print(f"OK: updated planned_docs ({changed} changes)")
    else:
        print("OK: planned_docs already up to date")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
