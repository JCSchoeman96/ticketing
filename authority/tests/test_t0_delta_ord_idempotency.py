"""Executable checks for the staged T0 ORD-1 idempotency contract and gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ORD = ROOT / "authority-staging/t0-hardening/ORD-1"


@pytest.fixture(scope="module")
def artifacts() -> tuple[dict, dict]:
    contract = json.loads((ORD / "contract.json").read_text())
    gates = json.loads((ORD / "test-gates.json").read_text())
    return contract, gates


CASES = {
    "identical_replay": {
        "given": "same org_id, operation_id, key, and request_hash",
        "expect": "existing idempotency record is reused; side effect executes once",
    },
    "changed_input_conflict": {
        "given": "same org_id, operation_id, and key with a different request_hash",
        "expect": "ERR_CONFLICT / LOCKS_IDEMPOTENCY_KEY_REUSE_MISMATCH; side effect does not execute again",
    },
    "concurrent_duplicate": {
        "given": "concurrent calls with same org_id, operation_id, key, and request_hash",
        "expect": "one side effect; both calls resolve to the same outcome",
    },
    "original_outcome_replay": {
        "given": "a completed record and a replay with same identity and request_hash",
        "expect": "return the original stored outcome",
    },
    "tenant_separation": {
        "given": "same operation_id and key under different org_id values",
        "expect": "separate idempotency records and effects",
    },
    "operation_separation": {
        "given": "same org_id and key under different operation_id values",
        "expect": "separate idempotency records and effects",
    },
}


@pytest.mark.parametrize(("case_id", "expected"), CASES.items())
def test_create_checkout_idempotency_case_has_executable_gate(
    artifacts: tuple[dict, dict], case_id: str, expected: dict
) -> None:
    contract, gates = artifacts
    idempotency = contract["domain_actions"]["create_checkout"]["idempotency"]
    assert idempotency["test_cases"][case_id] == expected

    pointer = f"/domain_actions/create_checkout/idempotency/test_cases/{case_id}"
    assert any(
        gate.get("must") is True
        and any(
            assertion.get("mode") == "automated"
            and assertion.get("type") == "json_pointer_equals"
            and assertion.get("details", {}).get("artifact_kind") == "contract"
            and assertion.get("details", {}).get("json_pointer") == pointer
            and assertion.get("details", {}).get("equals") == expected
            for assertion in gate.get("assertions", [])
        )
        for gate in gates["gates"]
    )


def test_create_checkout_uses_locks_identity_and_canonical_operation_id(
    artifacts: tuple[dict, dict],
) -> None:
    contract, _ = artifacts
    idem = contract["domain_actions"]["create_checkout"]["idempotency"]
    assert idem["operation_id"] == "ORD-1.create_checkout"
    assert idem["persisted_identity"] == ["org_id", "operation_id", "key"]
    assert idem["request_hash"]["algorithm"] == "SHA-256"


def test_checkout_order_has_no_actor_bound_idempotency_unique_constraint(
    artifacts: tuple[dict, dict],
) -> None:
    contract, _ = artifacts
    order = next(r for r in contract["data_model"]["resources"] if r["name"] == "Order")
    assert all(i.get("name") != "idempotency_per_actor_unique" for i in order["identities"])
    assert "MUST NOT define checkout identity or uniqueness" in order["notes"]


def test_changed_hash_conflict_uses_locks_registered_subcode(
    artifacts: tuple[dict, dict],
) -> None:
    contract, _ = artifacts
    locks = json.loads(
        (ROOT / "authority-staging/t0-hardening/LOCKS-1/contract.json").read_text()
    )
    mismatch = locks["idempotency"]["replay_semantics"]["different_request_hash"]
    expected_subcode = mismatch["subcode"]
    expected_error = mismatch["top_level"]
    case = contract["domain_actions"]["create_checkout"]["idempotency"]["test_cases"][
        "changed_input_conflict"
    ]
    assert expected_subcode == "LOCKS_IDEMPOTENCY_KEY_REUSE_MISMATCH"
    assert expected_error == "ERR_CONFLICT"
    assert case["expect"].startswith(f"{expected_error} / {expected_subcode};")
    assert contract["errors"]["subcodes"][expected_subcode] == {
        "base": expected_error,
        "retryable": False,
    }
