"""Regression checks for the approved T0 tax and checkout idempotency locks."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "authority-staging/t0-hardening"


def artifact(contract: str, filename: str = "contract.json") -> dict:
    return json.loads((STAGING / contract / filename).read_text())


@pytest.fixture(scope="module")
def tax_contracts() -> tuple[dict, dict, dict]:
    return artifact("OFFER-1"), artifact("TAX-1"), artifact("PRICE-1")


def test_t0_quote_uses_only_explicit_org_location_tax_basis(
    tax_contracts: tuple[dict, dict, dict],
) -> None:
    offer, tax, _ = tax_contracts
    quote = offer["domain_actions"]["build_cart_quote"]
    rules = " ".join(quote["validation_rules"])
    tax_profile = next(
        profile
        for profile in tax["resource_model"]["resources"]
        if profile["name"] == "TaxProfile"
    )
    basis = next(
        attribute
        for attribute in tax_profile["attributes"]
        if attribute["name"] == "default_tax_basis"
    )
    assert "T0 MUST require default_tax_basis=org_location" in rules
    assert "event_location" in rules and "customer_location" in rules
    assert "TAX_JURISDICTION_REQUIRED" in rules
    assert "MUST NOT infer" in rules and "Occurrence.venue" in rules
    assert "org_location" in basis["one_of"]
    assert quote["tax_context_resolution_input_mapping"]["event_jurisdiction_hint"] == (
        "null for T0 org_location quotes; do not project EVT-2 Occurrence.venue"
    )


def test_t0_single_tax_context_maps_one_rate_and_null_evidence(
    tax_contracts: tuple[dict, dict, dict],
) -> None:
    offer, _, price = tax_contracts
    quote = offer["domain_actions"]["build_cart_quote"]
    mapping = quote["price_snapshot_input_mapping"]
    assert mapping["applicable_tax_rate_revision_refs"] == (
        "[the one resolved TAX-1 tax_rate_id] for the single T0 TAXCTX-V2 context"
    )
    assert mapping["opaque_pii_jurisdiction_evidence_ref"] == "null for T0 org_location quotes"
    assert mapping["jurisdiction_evidence_sha256"] == "null for T0 org_location quotes"

    snapshot = next(
        resource
        for resource in price["resource_model"]["resources"]
        if resource["name"] == "PricingSnapshot"
    )
    attributes = {item["name"]: item for item in snapshot["attributes"]}
    assert attributes["opaque_pii_jurisdiction_evidence_ref"]["nullable"] is True
    assert attributes["jurisdiction_evidence_sha256"]["nullable"] is True
    assert snapshot["tax_context"]["t0_null_evidence_fields"] == [
        "opaque_pii_jurisdiction_evidence_ref",
        "jurisdiction_evidence_sha256",
    ]
    assert "remain present" in snapshot["tax_context"]["null_evidence_rule"]
    assert "explicit" in price["signature_spec"]["notes"].lower()
    assert "json null" in price["signature_spec"]["notes"].lower()
    assert "opaque_pii_jurisdiction_evidence_ref" in price["signature_spec"]["input_model"]["snapshot_fields_in_order"]
    assert "jurisdiction_evidence_sha256" in price["signature_spec"]["input_model"]["snapshot_fields_in_order"]

    ord_contract = artifact("ORD-1")
    order = ord_contract["data_model"]["resources"][0]
    order_attributes = {item["name"]: item for item in order["required_attributes"]}
    assert order_attributes["opaque_pii_jurisdiction_evidence_ref"]["nullable"] is True
    assert order_attributes["jurisdiction_evidence_sha256"]["nullable"] is True
    assert "draft quote" in order_attributes["opaque_pii_jurisdiction_evidence_ref"]["notes"]
    assert "does not waive" in ord_contract["t0_scope"]["provenance"]


def test_tax_t0_constraints_are_gated() -> None:
    gates = artifact("OFFER-1", "test-gates.json")["gates"]
    gate = next(item for item in gates if item["id"] == "OFFER-1-T0-QUOTE-GUARDS")
    assertions = gate["assertions"]
    assert any(
        assertion.get("mode") == "automated"
        and assertion.get("type") == "property_tests"
        and "test_t0_quote_uses_only_explicit_org_location_tax_basis"
        in assertion.get("details", {}).get("ci_task", "")
        for assertion in assertions
    )
    price_gates = artifact("PRICE-1", "test-gates.json")["gates"]
    price_gate = next(item for item in price_gates if item["id"] == "PRICE-1.GATE.T0.006")
    assert any(
        assertion.get("mode") == "automated"
        and assertion.get("type") == "property_tests"
        and "test_t0_single_tax_context_maps_one_rate_and_null_evidence"
        in assertion.get("details", {}).get("ci_task", "")
        for assertion in price_gate["assertions"]
    )
    assert any(
        assertion.get("mode") == "automated"
        and assertion.get("type") == "property_tests"
        and "test_t0_single_tax_context_maps_one_rate_and_null_evidence"
        in assertion.get("details", {}).get("ci_task", "")
        for assertion in assertions
    )


def test_checkout_hash_locks_effect_fields_and_normalization() -> None:
    ord_contract = artifact("ORD-1")
    idem = ord_contract["domain_actions"]["create_checkout"]["idempotency"]
    request_hash = idem["request_hash"]
    assert idem["persisted_identity"] == ["org_id", "operation_id", "key"]
    assert request_hash["algorithm"] == "SHA-256"
    assert request_hash["canonicalization"] == "RFC8785_JCS"
    assert request_hash["encoding"] == "UTF-8"
    assert request_hash["digest_encoding"] == "lowercase_hex"
    assert request_hash["normalized_fields"] == [
        "org_id",
        "actor_id",
        "actor_type",
        "currency",
        "pricing_snapshot_id",
        "seat_hold_proofs[].hold_id",
        "bucket_hold_proofs[].hold_id",
        "entitlement_allocations[].hold_id",
        "entitlement_allocations[].line_key",
        "entitlement_allocations[].qty",
        "entitlement_allocations[].beneficiary_customer_id",
        "entitlement_allocations[].entitlement_kind",
        "entitlement_allocations[].entitlement_grant_id",
        "entitlement_allocations[].entitlement_tier_id",
    ]
    rules = request_hash["normalization_rules"]
    assert rules["uuid"] == "lowercase RFC-4122 representation"
    assert "sort by hold_id" in rules["seat_hold_proofs"]
    assert "reject duplicate hold_id values within or across seat/bucket proof collections" in rules["seat_hold_proofs"]
    assert "sort by hold_id" in rules["bucket_hold_proofs"]
    assert "reject duplicate hold_id values within or across seat/bucket proof collections" in rules["bucket_hold_proofs"]
    assert rules["entitlement_allocations"] == "sort by unique hold_id; reject duplicate hold_id"
    assert rules["optional_collections"] == "absent and empty both normalize to []"
    assert request_hash["excluded_fields"] == [
        "idempotency_key",
        "request_id",
        "trace_id",
        "operation_id",
        "server-derived outputs",
        "mutable database state",
        "hold_signature",
    ]


def test_checkout_request_hash_vectors_cover_replay_and_effect_inputs() -> None:
    ord_contract = artifact("ORD-1")
    vectors = ord_contract["domain_actions"]["create_checkout"]["idempotency"]["request_hash"]["test_vectors"]
    expected = {
        "request_id_ignored": "same_hash",
        "trace_id_ignored": "same_hash",
        "pricing_snapshot_changed": "different_hash",
        "actor_identity_changed": "different_hash",
        "proof_collection_reordered": "same_hash",
        "proof_hold_id_changed": "different_hash",
        "hold_signature_changed": "same_hash",
        "seat_proof_hold_id_changed": "different_hash",
        "bucket_proof_hold_id_changed": "different_hash",
        "entitlement_quantity_changed": "different_hash",
        "entitlement_allocation_changed": "different_hash",
        "tenant_separation": "different_identity",
        "operation_separation": "different_identity",
    }
    assert {name: vector["expected"] for name, vector in vectors.items()} == expected


def test_checkout_replay_revalidates_proof_signature_without_mutable_hold_checks() -> None:
    ord_contract = artifact("ORD-1")
    action = ord_contract["domain_actions"]["create_checkout"]
    replay = action["idempotency"]["replay_security"]
    assert replay["authenticate_org_and_actor_before_outcome_release"] is True
    assert replay["cryptographically_validate_supplied_hold_signatures"] is True
    assert replay["signature_validation_binds_referenced_hold_id"] is True
    assert replay["recheck_mutable_hold_status_expiry_or_quantity"] is False
    allocation = action["input_schemas"]["entitlement_allocations"]["items"]
    assert allocation["properties"]["hold_id"]["type"] == "uuid_v7"
    assert "hold_id" in allocation["required"]
    assert {"entitlement_grant_id", "entitlement_tier_id"} <= set(allocation["required"])


def test_checkout_hash_and_replay_security_have_executable_gate_coverage() -> None:
    gates = artifact("ORD-1", "test-gates.json")["gates"]
    gate = next(item for item in gates if item["id"] == "ORD-1.GATE.T0.IDEM-REQUEST-HASH")
    automated = [
        assertion
        for assertion in gate["assertions"]
        if assertion.get("mode") == "automated"
        and assertion.get("type") == "property_tests"
    ]
    assert any("test_checkout_hash_locks_effect_fields_and_normalization" in item["details"]["ci_task"] for item in automated)
    assert any("test_checkout_request_hash_vectors_cover_replay_and_effect_inputs" in item["details"]["ci_task"] for item in automated)
    assert any("test_checkout_replay_revalidates_proof_signature_without_mutable_hold_checks" in item["details"]["ci_task"] for item in automated)


def test_t0_http_idempotency_authority_excludes_ext1() -> None:
    api = artifact("API-0")
    dependencies = {item["doc_id"]: item for item in api["dependencies"]}
    assert "EXT-1" not in dependencies
    assert dependencies["LOCKS-1"]["min_version"] == "3.0.0"
    assert api["dependency_floors"]["LOCKS-1"] == "3.0.0"

    corrections = api["approved_authority_corrections"]
    assert corrections["idempotency_header"] == "Idempotency-Key"
    assert corrections["durable_idempotency_authority"] == "LOCKS-1"
    rules = {item["rule_id"]: item["text"] for item in api["rules"]}
    transport_rule = rules["API-0-IDEMP-001"]
    assert "Idempotency-Key" in transport_rule
    assert "ERR_BAD_REQUEST" in transport_rule
    assert "EXT_IDEMPOTENCY_KEY_REQUIRED" in transport_rule
    assert "ERR-1" in transport_rule and "LOCKS-1" in transport_rule
    assert "EXT-1" not in transport_rule
    assert "X-Idempotency-Key" not in transport_rule

    err = artifact("ERR-1")
    missing_key = next(
        item
        for item in err["registry"]["subcodes"]
        if item["subcode"] == "EXT_IDEMPOTENCY_KEY_REQUIRED"
    )
    assert missing_key["top_level"] == "ERR_BAD_REQUEST"

    locks = artifact("LOCKS-1")["idempotency"]
    assert locks["storage"]["uniqueness"] == ["org_id", "operation_id", "key"]
    assert "request_hash" in locks["storage"]["required_fields"]
    assert locks["replay_semantics"]["same_request_hash"] == "return_original_response_when_available"
    assert locks["replay_semantics"]["different_request_hash"]["top_level"] == "ERR_CONFLICT"

    manifest = json.loads((ROOT / "contracts/manifest.json").read_text())
    ext = next(item for item in manifest["contracts"] if item["doc_id"] == "EXT-1")
    assert ext["version"] == "2.1.7"
    assert ext["membership"] == "DEPENDENCY_ONLY"
    with zipfile.ZipFile(ROOT / ext["zip_path"]) as archive:
        for item in ext["artifacts"]:
            if item["extracted_path"] == "EXT-1_Contract_v2.1.7.json":
                stage_path = STAGING / "EXT-1" / "contract.json"
            elif item["extracted_path"] == "EXT-1_Test_Gates_v2.1.7.json":
                stage_path = STAGING / "EXT-1" / "test-gates.json"
            else:
                continue
            assert stage_path.read_bytes() == archive.read(item["archive_path"])

    stale_header_refs = [
        path
        for path in STAGING.rglob("*.json")
        if path.parent.name != "EXT-1" and b"X-Idempotency-Key" in path.read_bytes()
    ]
    assert stale_header_refs == []

    api_gates = artifact("API-0", "test-gates.json")["gates"]
    authority_gate = next(
        item for item in api_gates if item["id"] == "API-0-GATE-T0-IDEMPOTENCY-AUTHORITY-001"
    )
    expected_task = "python -m pytest -q tests/test_t0_delta_final_locks.py::test_t0_http_idempotency_authority_excludes_ext1"
    assert {
        "details": {"ci_task": expected_task},
        "mode": "automated",
        "type": "property_tests",
    } in authority_gate["assertions"]
