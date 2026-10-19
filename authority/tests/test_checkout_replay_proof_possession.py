"""Executable checks for the coordinated checkout replay successor authority."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDIVIDUAL_HOLD_FIELDS = [
    "org_id",
    "hold_id",
    "occurrence_id",
    "seat_id",
    "actor_id",
    "actor_type",
]
INDIVIDUAL_HOLD_FORMAT = "|".join(INDIVIDUAL_HOLD_FIELDS)


def manifest() -> dict:
    return json.loads((ROOT / "contracts/manifest.json").read_text())


def installed_record(doc_id: str) -> dict:
    return next(row for row in manifest()["contracts"] if row["doc_id"] == doc_id)


def installed_contract(doc_id: str) -> dict:
    record = installed_record(doc_id)
    path = ROOT / record["extracted_path"] / f"{doc_id}_Contract_v{record['version']}.json"
    contract = json.loads(path.read_text())
    assert contract["doc_id"] == doc_id
    assert contract["version"] == record["version"]

    canon_record = installed_record("CANON-1")
    canon_dir = ROOT / canon_record["extracted_path"]
    canon_path = next(canon_dir.glob("CANON-1_Contract_v*.json"))
    canon = json.loads(canon_path.read_text())
    pin = next(item for item in canon["canonical_bundles"] if item["doc_id"] == doc_id)
    assert pin["version"] == record["version"]
    assert pin["bundle_sha256"] == record["zip_sha256"]
    return contract


def installed_gates(doc_id: str) -> dict:
    record = installed_record(doc_id)
    path = ROOT / record["extracted_path"] / f"{doc_id}_Test_Gates_v{record['version']}.json"
    return json.loads(path.read_text())


def action(doc_id: str, name: str) -> dict:
    return installed_contract(doc_id)["domain_actions"][name]


def action_text(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for part in value for item in action_text(part)]
    if isinstance(value, dict):
        return [item for part in value.values() for item in action_text(part)]
    return []


def signature_bytes(context: dict, key: bytes) -> bytes:
    canonical = "|".join(str(context[name]) for name in INDIVIDUAL_HOLD_FIELDS)
    return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).digest()


def test_individual_seat_signature_vectors_use_grace_stable_basis() -> None:
    seat = installed_contract("SEAT-1")
    signature = seat["signature_security"]["hold_signature"]

    assert signature["algorithm"] == "HMAC-SHA256"
    assert signature["encoding"] == "base64url"
    assert signature["compare"] == "constant_time"
    assert signature["canonical_string_spec"]["encoding"] == "utf8"
    assert signature["canonical_string_spec"]["separator"] == "|"
    assert signature["canonical_string_spec"]["uuid_normalization"] == "lowercase_rfc4122"
    assert signature["canonical_string_spec"]["actor_type_normalization"] == "lowercase_snake_case"
    assert signature["canonical_string_spec"]["format"] == INDIVIDUAL_HOLD_FORMAT
    assert signature["derived_from"] == INDIVIDUAL_HOLD_FIELDS
    assert "expires_at_utc" not in signature["canonical_string_spec"]
    assert "expires_at_utc" not in signature["derived_from"]
    assert "MUST NOT bind expires_at_utc" in signature["rule"]
    assert "without rotating" in signature["rule"]

    test_vectors = signature["test_vectors"]
    key = test_vectors["test_key_utf8"].encode("utf-8")
    assert len(test_vectors["vectors"]) == 3
    expected = [
        (
            "018f2f6f-3d54-7b2a-8c6b-7a9c77b8b3f1|0193a3e2-0b3c-7b11-8a1b-66c2b4d7f8aa|0192d7c0-1a2b-7c3d-9e4f-1234567890ab|018f2f70-1111-7b2a-8c6b-7a9c77b8b3f2|018f2f70-2222-7b2a-8c6b-7a9c77b8b3f3|customer",
            "4413c946f26827158adae545faf18a0cd29921a9d5d49acee61b3f88cbc7a8ec",
            "RBPJRvJoJxWK2uVF-vGKDNKZIanV1JrO5hs_iMvHqOw",
        ),
        (
            "018f2f6f-3d54-7b2a-8c6b-7a9c77b8b3f1|0193a3e2-0b3c-7b11-8a1b-66c2b4d7f8ab|0192d7c0-1a2b-7c3d-9e4f-1234567890ab|018f2f70-3333-7b2a-8c6b-7a9c77b8b3f4|018f2f70-4444-7b2a-8c6b-7a9c77b8b3f5|org_support",
            "036f4388b7b6aa2e683d9b6e39b661558f206718039d314c79501f7fb4e92b95",
            "A29DiLe2qi5oPZtuObZhVY8gZxgDnTFMeVAff7TpK5U",
        ),
        (
            "01b6c9d0-aaaa-7b2a-8c6b-7a9c77b8b3f1|01b6c9d0-bbbb-7b2a-8c6b-7a9c77b8b3f2|01b6c9d0-cccc-7b2a-8c6b-7a9c77b8b3f3|01b6c9d0-dddd-7b2a-8c6b-7a9c77b8b3f4|01b6c9d0-eeee-7b2a-8c6b-7a9c77b8b3f5|scanner_device",
            "079012e8c39ac419e09417ba3d4c1e1380eadad87330f3f3f041414337c81385",
            "B5AS6MOaxBnglBe6PUweE4Dq2thzMPPz8EFBQzfIE4U",
        ),
    ]

    for vector, (canonical, expected_hex, expected_b64url) in zip(test_vectors["vectors"], expected, strict=True):
        assert vector["canonical_string"] == canonical
        assert "expires_at_utc" not in vector
        digest = signature_bytes(vector, key)
        assert digest.hex() == expected_hex
        assert vector["expected_hmac_sha256_hex"] == expected_hex
        assert base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=") == expected_b64url
        assert vector["expected_signature_base64url"] == expected_b64url

        before_extension = dict(vector, expires_at_utc="2026-02-09T18:45:12.123456Z")
        after_extension = dict(vector, expires_at_utc="2026-02-09T18:48:12.123456Z")
        assert signature_bytes(before_extension, key) == signature_bytes(after_extension, key)


def test_seat_signature_binding_and_live_verifiers_remain_separate() -> None:
    seat = installed_contract("SEAT-1")
    rules = seat["invariants"]
    assert not any(
        item.get("rule_id") == "SEAT-1-P0-HOLD-SIGNATURE-TTL-002"
        for item in rules
    )
    assert not any(
        item.get("severity") == "P0"
        and "hold_signature" in item.get("text", "")
        and "MUST bind expires_at_utc" in item.get("text", "")
        for item in rules
    )
    stability = next(item for item in rules if item.get("rule_id") == "SEAT-1-P0-HOLD-SIGNATURE-STABILITY-002")
    assert "MUST NOT bind expires_at_utc" in stability["text"]
    assert "without rotating hold_signature" in stability["text"]
    assert "independently enforce active status and current expiry" in stability["text"]

    signature_rule = "HMAC(secret, org_id || hold_id || occurrence_id || seat_id || actor_id || actor_type)"
    for name in ("verify_hold_proofs", "extend_hold_grace", "release_hold", "allocate_hold"):
        text = " ".join(action("SEAT-1", name)["validation_rules"])
        assert signature_rule in text
        assert "HMAC(secret, org_id || hold_id || occurrence_id || seat_id || actor_id || actor_type || expires_at_utc)" not in text

    verify_seat = action("SEAT-1", "verify_hold_proofs")
    seat_rules = " ".join(verify_seat["validation_rules"])
    assert "actor_id" in seat_rules and "actor_type" in seat_rules and "org_id" in seat_rules
    assert "status=active" in seat_rules and "now_utc_usec < expires_at_utc" in seat_rules
    assert "ERR_NOT_FOUND" in seat_rules

    grace_rules = " ".join(action("SEAT-1", "extend_hold_grace")["validation_rules"])
    assert "status=active" in grace_rules and "now_utc_usec < expires_at_utc" in grace_rules
    release_rules = " ".join(action("SEAT-1", "release_hold")["validation_rules"])
    assert "active -> released" in release_rules
    allocation_rules = " ".join(action("SEAT-1", "allocate_hold")["validation_rules"])
    assert "now_utc_usec >= expires_at_utc" in allocation_rules

    verify_bucket = action("SEAT-1", "verify_bucket_hold_proofs")
    bucket_rules = " ".join(verify_bucket["validation_rules"])
    assert "status" in bucket_rules and "active" in bucket_rules
    assert "database now MUST be before expires_at_utc_usec" in bucket_rules
    assert verify_seat["side_effects_separation"] == "read_only"
    assert verify_bucket["side_effects_separation"] == "read_only"


def test_signature_binding_changes_for_identity_and_actor_fields() -> None:
    seat = installed_contract("SEAT-1")
    signature = seat["signature_security"]["hold_signature"]
    key = signature["test_vectors"]["test_key_utf8"].encode("utf-8")
    original = signature["test_vectors"]["vectors"][0]
    expected = signature_bytes(original, key)

    for field in ("org_id", "hold_id", "occurrence_id", "seat_id", "actor_id", "actor_type"):
        changed = dict(original)
        changed[field] = changed[field] + ("x" if field == "actor_type" else "1")
        assert signature_bytes(changed, key) != expected


def test_replay_only_possession_actions_are_read_only_and_ignore_lifecycle() -> None:
    seat = installed_contract("SEAT-1")
    seat_possession = action("SEAT-1", "verify_hold_proof_possession")
    bucket_possession = action("SEAT-1", "verify_bucket_hold_proof_possession")

    for name, action_data, proof_input in (
        ("verify_hold_proof_possession", seat_possession, "seat_hold_proofs"),
        ("verify_bucket_hold_proof_possession", bucket_possession, "bucket_hold_proofs"),
    ):
        assert action_data["side_effects_separation"] == "read_only"
        assert {"org_id", proof_input, "actor_id", "actor_type"} <= set(action_data["inputs_required"])
        rules = " ".join(action_data["validation_rules"])
        assert "constant time" in rules
        assert "hold_id" in rules
        assert "ERR_NOT_FOUND / TEN_CROSS_TENANT_HIDDEN" in rules
        assert "ERR_FORBIDDEN / SEAT_HOLD_TOKEN_INVALID" in rules
        assert "actor_id" in rules and "actor_type" in rules
        assert "MUST NOT require status=active" in rules
        assert "MUST NOT require now < expires_at" in rules
        assert "MUST NOT mutate" in rules
        assert "MUST NOT authorize" in rules
        assert "persisted SeatHold.hold_signature" in rules or (
            "persisted InventoryBucketHold.hold_signature" in rules
        )
        assert not any(
            phrase in rules
            for phrase in (
                "MUST be status=active",
                "MUST satisfy now_utc_usec < expires_at",
                "database now MUST be before expires_at",
            )
        )
        assert "hold_ids" in action_data["output_minimum"]
        assert "hold_ids" in " ".join(action_data.get("validation_rules", []))

    seat_signature = seat["signature_security"]["hold_signature"]["canonical_string_spec"]["format"]
    bucket_signature = seat["signature_security"]["bucket_hold_signature"]["canonical_string_spec"]["format"]
    assert seat_signature == INDIVIDUAL_HOLD_FORMAT
    assert bucket_signature == "org_id|hold_id|occurrence_id|bucket_id|quantity|actor_id|actor_type"
    assert "verify_bucket_hold_proofs" in bucket_possession["purpose"]
    bucket_rules = " ".join(bucket_possession["validation_rules"])
    assert "Quantity MUST NOT be re-evaluated as inventory availability" in bucket_rules

    invariant = next(
        item for item in seat["invariants"]
        if item.get("rule_id") == "SEAT-1-P0-REPLAY-PROOF-POSSESSION-001"
    )
    assert "MUST NOT establish current inventory availability" in invariant["text"]
    assert "MUST NOT authorize any new checkout, grace extension, allocation or finalization effect" in invariant["text"]


def test_seat_replay_possession_gate_binds_regressions_and_quarantines_batch_signature() -> None:
    seat = installed_contract("SEAT-1")
    gates = installed_gates("SEAT-1")["gates"]
    gate = next(item for item in gates if item["id"] == "SEAT-1-P0-CHECKOUT-REPLAY-POSSESSION")
    assert gate["level"] == "P0" and gate["must"] is True
    ci_tasks = [
        assertion.get("details", {}).get("ci_task", "")
        for assertion in gate["assertions"]
        if assertion.get("type") == "property_tests"
    ]
    for nodeid in (
        "tests/test_checkout_replay_proof_possession.py::test_individual_seat_signature_vectors_use_grace_stable_basis",
        "tests/test_checkout_replay_proof_possession.py::test_replay_only_possession_actions_are_read_only_and_ignore_lifecycle",
        "tests/test_checkout_replay_proof_possession.py::test_seat_signature_binding_and_live_verifiers_remain_separate",
    ):
        assert any(nodeid in ci_task for ci_task in ci_tasks)

    action_texts = action_text(seat["domain_actions"])
    assert not any("hold_signature_batch" in text or "multi_seat_hold_operation" in text for text in action_texts)
    assert any(
        "hold_signature_batch" in item and "deferred non-T0 debt" in item
        for item in seat["change_log"]
        if isinstance(item, str)
    )


def test_ord_completed_replay_routes_only_to_possession_actions() -> None:
    ord_contract = installed_contract("ORD-1")
    create = action("ORD-1", "create_checkout")
    replay = create["idempotency"]["replay_security"]
    frozen_ord = json.loads(
        (ROOT / "release-src/current/ORD-1/4.0.0/contract.json").read_text()
    )
    seat_dependency = next(item for item in ord_contract["dependencies"] if item["doc_id"] == "SEAT-1")

    assert seat_dependency["min_version"] == "4.1.0"
    assert ord_contract["dependency_floors"]["SEAT-1"] == "4.1.0"
    assert ord_contract["dependency_pins"]["gc_001_chain"]["SEAT-1"] == "4.1.0"
    assert replay["recheck_mutable_hold_status_expiry_or_quantity"] is False
    assert replay["seat_proof_possession_action"] == "SEAT-1.verify_hold_proof_possession"
    assert replay["bucket_proof_possession_action"] == "SEAT-1.verify_bucket_hold_proof_possession"
    assert replay["completed_identical_replay_only"] is True
    assert replay["verified_hold_id_sets_must_match_submitted_normalized_hold_ids"] is True
    assert replay["execute_zero_checkout_side_effects"] is True
    assert "MUST withhold the stored response" in replay["failure_behavior"]
    assert "MUST NOT fall through to a new checkout" in replay["failure_behavior"]
    assert "failed/incomplete prior execution" in replay["sequence"][3]
    assert "new first execution with no prior durable record" in replay["sequence"][4]
    assert replay["rule"].find("LOCKS-1") < replay["rule"].find("verify_hold_proof_possession")
    assert "verify_bucket_hold_proof_possession" in replay["rule"]
    assert "MUST NOT invoke the full live verifiers" in replay["rule"]

    rules = create["validation_rules"]
    assert "new/effectful checkout execution" in rules[19]
    assert "SEAT-1.verify_hold_proofs" in rules[19]
    assert "completed identical replay" in rules[19]
    assert "new/effectful checkout execution" in rules[20]
    assert "SEAT-1.verify_bucket_hold_proofs" in rules[20]
    assert "completed identical replay" in rules[20]
    assert "SEAT-1.verify_hold_proofs" in create["seat_and_bucket_proof_rule"]["seat_action"]
    assert "SEAT-1.verify_bucket_hold_proofs" in create["seat_and_bucket_proof_rule"]["bucket_action"]
    assert create["seat_and_bucket_proof_rule"]["completed_replay_seat_action"] == (
        "SEAT-1.verify_hold_proof_possession"
    )
    assert create["seat_and_bucket_proof_rule"]["completed_replay_bucket_action"] == (
        "SEAT-1.verify_bucket_hold_proof_possession"
    )
    possession_inputs = replay["possession_action_inputs"]
    assert possession_inputs["org_id"] == "authenticated org_id"
    assert possession_inputs["actor_id"] == "authenticated actor_id"
    assert possession_inputs["actor_type"] == "authenticated tenancy context.actor_type"
    assert possession_inputs["request_id"] == "inputs.request_id"
    assert possession_inputs["trace_id"] == "inputs.trace_id"
    bucket_context = ord_contract["bucket_hold_actor_binding"]["seat_action_inputs"][
        "verify_bucket_hold_proof_possession"
    ]
    assert bucket_context["actor_type"] == "authenticated tenancy context.actor_type"

    cases = create["idempotency"]["test_cases"]
    assert cases["completed_replay_after_hold_expiry"]["expect"].find("original stored outcome") >= 0
    assert cases["completed_replay_after_hold_expiry"]["expect"].find("zero checkout side effects") >= 0
    assert "MUST NOT release" in cases["invalid_replacement_signature_replay"]["expect"]
    assert "LOCKS_IDEMPOTENCY_KEY_REUSE_MISMATCH" in cases["changed_hold_id_replay"]["expect"]
    assert "proof-possession" in cases["first_execution_uses_full_verifiers"]["expect"]
    assert "do not use proof-possession" in cases["failed_or_incomplete_identity"]["expect"]
    assert create["inputs_required"] == frozen_ord["domain_actions"]["create_checkout"]["inputs_required"]
    assert create["inputs_optional"] == frozen_ord["domain_actions"]["create_checkout"]["inputs_optional"]
    assert replay["forbidden_effects"] == [
        "extend_hold_grace",
        "extend_bucket_hold_grace",
        "rebind_order_lines",
        "mutate_hold_state",
        "mutate_inventory_counters",
        "create_order",
        "allocate",
    ]

    assert "SEAT-1.verify_hold_proof_possession" not in json.dumps(ord_contract["domain_actions"]["finalize_checkout"])
    assert "SEAT-1.verify_bucket_hold_proof_possession" not in json.dumps(ord_contract["domain_actions"]["finalize_checkout"])
    assert ord_contract["domain_actions"]["finalize_checkout"] == frozen_ord["domain_actions"]["finalize_checkout"]
    finalization = " ".join(ord_contract["domain_actions"]["finalize_checkout"]["validation_rules"])
    assert "SEAT-1.verify_bucket_hold_proofs" in finalization
    assert "preserve existing verify_hold_proofs" in finalization
    assert "All bound holds MUST be unexpired at commit time" in finalization


def test_ord_request_hash_is_unchanged_and_signature_stays_out_of_hash() -> None:
    ord_contract = installed_contract("ORD-1")
    frozen = json.loads(
        (ROOT / "release-src/current/ORD-1/4.0.0/contract.json").read_text()
    )
    current_hash = action("ORD-1", "create_checkout")["idempotency"]["request_hash"]
    frozen_hash = frozen["domain_actions"]["create_checkout"]["idempotency"]["request_hash"]
    assert current_hash == frozen_hash
    assert "hold_signature" in current_hash["excluded_fields"]
    assert current_hash["test_vectors"]["hold_signature_changed"]["expected"] == "same_hash"
    assert current_hash["test_vectors"]["proof_hold_id_changed"]["expected"] == "different_hash"
    assert current_hash["normalization_rules"]["proof_material"] == (
        "Hash only stable hold_id values; do not hash hold_signature. Validate the supplied signature separately before releasing an outcome."
    )
    assert action("ORD-1", "create_checkout")["idempotency"]["replay_security"][
        "recheck_mutable_hold_status_expiry_or_quantity"
    ] is False


def test_canon_membership_and_ext_dependency_release_are_unchanged() -> None:
    canon_record = installed_record("CANON-1")
    canon_path = (
        ROOT
        / canon_record["extracted_path"]
        / f"CANON-1_Contract_v{canon_record['version']}.json"
    )
    canon = json.loads(canon_path.read_text())
    assert len(canon["canonical_bundles"]) == 56
    assert not any(item["doc_id"] == "EXT-1" for item in canon["canonical_bundles"])

    ext_record = installed_record("EXT-1")
    assert ext_record["version"] == "2.1.7"
    assert ext_record["membership"] == "DEPENDENCY_ONLY"
    assert ext_record["zip_sha256"] == (
        "01d843bdfde57a719a39f110536668efad4f7fa0ff34e69fea330194e06dd6a1"
    )
    assert len(manifest()["contracts"]) == 58


def test_ord_replay_gate_binds_the_installed_successor_contract() -> None:
    gates = installed_gates("ORD-1")["gates"]
    gate = next(item for item in gates if item["id"] == "ORD-1-P0-CHECKOUT-REPLAY-POSSESSION")
    assert gate["level"] == "P0" and gate["must"] is True
    ci_tasks = [
        assertion.get("details", {}).get("ci_task", "")
        for assertion in gate["assertions"]
        if assertion.get("type") == "property_tests"
    ]
    for nodeid in (
        "tests/test_checkout_replay_proof_possession.py::test_ord_completed_replay_routes_only_to_possession_actions",
        "tests/test_checkout_replay_proof_possession.py::test_ord_request_hash_is_unchanged_and_signature_stays_out_of_hash",
    ):
        assert any(nodeid in ci_task for ci_task in ci_tasks)


def test_ord_p0_seat_dependency_gates_match_installed_contract() -> None:
    ord_contract = installed_contract("ORD-1")
    gates = installed_gates("ORD-1")["gates"]

    gate_0300 = next(item for item in gates if item["id"] == "ORD-1-GATE-0300")
    semantic_gate = next(item for item in gates if item["id"] == "ORD-1-T0-SEMANTIC-CONSISTENCY")

    def expected_version(gate: dict, pointer: str) -> str:
        assertion = next(
            item
            for item in gate["assertions"]
            if item["type"] == "json_pointer_equals"
            and item["details"].get("artifact_kind") == "contract"
            and item["details"].get("json_pointer") == pointer
        )
        return assertion["details"]["equals"]

    assert gate_0300["level"] == semantic_gate["level"] == "P0"
    assert gate_0300["must"] is semantic_gate["must"] is True
    assert expected_version(gate_0300, "/dependency_pins/gc_001_chain/SEAT-1") == "4.1.0"
    assert ord_contract["dependency_pins"]["gc_001_chain"]["SEAT-1"] == "4.1.0"
    assert expected_version(semantic_gate, "/dependency_floors/SEAT-1") == "4.1.0"
    assert ord_contract["dependency_floors"]["SEAT-1"] == "4.1.0"
