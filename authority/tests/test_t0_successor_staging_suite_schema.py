from __future__ import annotations

import json
from pathlib import Path


OWNED_T0_SUCCESSORS = frozenset({
    "API-0",
    "DP-1",
    "ERR-1",
    "EVT-1",
    "EVT-2",
    "IAM-1",
    "IAM-2",
    "LOCKS-1",
    "OBS-1",
    "OFFER-1",
    "ORD-1",
    "PII-1",
    "PRICE-1",
    "RP-0",
    "SEAT-1",
    "SEC-1",
    "SM-0",
    "TAX-1",
    "TEN-1",
})
DEPENDENCY_ONLY_DOC_IDS = frozenset({"EXT-1"})
OWNER_APPROVED_SUITE_SCHEMA = "CS-0@3.0.1"


def test_owned_t0_successor_staging_pairs_use_owner_approved_cs_0_schema() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    staging_root = repo_root / "authority-staging/t0-hardening"
    staged_doc_ids = {
        path.name for path in staging_root.iterdir()
        if path.is_dir() and (path / "contract.json").is_file()
    }
    owned_doc_ids = staged_doc_ids - DEPENDENCY_ONLY_DOC_IDS

    assert owned_doc_ids == OWNED_T0_SUCCESSORS
    assert len(owned_doc_ids) == 19
    assert DEPENDENCY_ONLY_DOC_IDS == {"EXT-1"}

    manifest = json.loads((repo_root / "contracts/manifest.json").read_text(encoding="utf-8"))
    ext_release = next(row for row in manifest["contracts"] if row["doc_id"] == "EXT-1")
    assert ext_release["version"] == "2.1.7"
    assert ext_release["membership"] == "DEPENDENCY_ONLY"

    mismatches = []
    for doc_id in sorted(owned_doc_ids):
        for artifact_name in ("contract.json", "test-gates.json"):
            artifact_path = staging_root / doc_id / artifact_name
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            if artifact.get("suite_schema") != OWNER_APPROVED_SUITE_SCHEMA:
                mismatches.append(
                    f"{doc_id}/{artifact_name}: {artifact.get('suite_schema')!r}"
                )

    assert not mismatches, "Owned T0 successor staging pairs have stale suite_schema values:\n" + "\n".join(mismatches)
