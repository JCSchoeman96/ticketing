"""Regression checks for dependency minimum and floor alignment in T0 staging."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "authority-staging/t0-hardening"


def contract(doc_id: str) -> dict:
    return json.loads((STAGING / doc_id / "contract.json").read_text())


def dependency_minimum(document: dict, dependency_id: str) -> str:
    dependency = next(
        item for item in document["dependencies"] if item["doc_id"] == dependency_id
    )
    return dependency["min_version"]


def test_ord_and_rp_dependency_minima_match_floors() -> None:
    order = contract("ORD-1")
    tax_floor = order["dependency_floors"]["TAX-1"]
    assert tax_floor == "2.1.1"
    assert dependency_minimum(order, "TAX-1") == tax_floor

    refund_policy = contract("RP-0")
    event_floor = refund_policy["dependency_floors"]["EVT-1"]
    assert event_floor == "2.16.4"
    assert dependency_minimum(refund_policy, "EVT-1") == event_floor
    assert refund_policy["events_and_ordering"]["event_registry_authority"][
        "min_version"
    ] == event_floor
