"""Executable regression checks for the integrated T0 authority delta."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "authority-staging" / "t0-hardening"

TAXCTX_V2_FIELDS = [
    "org_id",
    "jurisdiction_code",
    "inclusion_mode",
    "rounding_mode",
    "tax_class",
    "rate_basis_points",
    "tax_scope",
    "tax_basis",
    "provider_mode",
    "provider_name",
    "tax_point_strategy",
]


def contract(doc_id: str) -> dict:
    return json.loads((STAGING / doc_id / "contract.json").read_text())


def gates(doc_id: str) -> dict:
    return json.loads((STAGING / doc_id / "test-gates.json").read_text())


def repository_test_assertion(nodeid: str) -> dict:
    return {
        "details": {"ci_task": f"python -m pytest -q {nodeid}"},
        "mode": "automated",
        "type": "property_tests",
    }


def require_repository_test(doc_id: str, gate_id: str, nodeid: str) -> None:
    gate = next(g for g in gates(doc_id)["gates"] if g["id"] == gate_id)
    assert repository_test_assertion(nodeid) in gate["assertions"]


def invalid_ordering_key_refs(event_types: dict, envelope: dict) -> list[tuple[str, str]]:
    extension_rules = envelope["extensions"]
    permitted_extensions = set(extension_rules["required"]) | set(extension_rules["optional"])
    field_rules = set(extension_rules["field_rules"])
    invalid: list[tuple[str, str]] = []

    for event_id, event in event_types.items():
        required_data = set(event.get("required_data_keys", []))
        required_extensions = set(event.get("required_extensions", []))
        ordering = event.get("ordering", {})
        ordering_keys = [
            key
            for field in ("key", "ordering_key")
            for key in ordering.get(field, [])
        ]
        for key in ordering_keys:
            is_payload_field = key in required_data
            is_valid_extension = (
                key in required_extensions
                and key in permitted_extensions
                and key in field_rules
            )
            if not (is_payload_field or is_valid_extension):
                invalid.append((event_id, key))
    return invalid


def test_ash_class_mappings_target_registered_top_level_errors() -> None:
    err = contract("ERR-1")
    registered = {item["code"] for item in err["registry"]["top_level_codes"]}
    mappings = err["mappings"]["ash_3"]["class_to_top_level"]

    assert mappings
    assert all(item["top_level_code"] in registered for item in mappings)
    framework = next(item for item in mappings if item["ash_error_class"] == "Ash.Error.Framework")
    assert framework["top_level_code"] == "ERR_INTERNAL"
    require_repository_test(
        "ERR-1",
        "ERR_1_GATE_130_ASH_TARGETS_REGISTERED",
        "tests/test_t0_delta_authority_gates.py::test_ash_class_mappings_target_registered_top_level_errors",
    )


def test_dp_actor_context_mapping_matches_err1_registry() -> None:
    err = contract("ERR-1")
    dp = contract("DP-1")
    registry = {item["subcode"]: item["top_level"] for item in err["registry"]["subcodes"]}
    actor_subcode = "AUTH_ACTOR_CONTEXT_MISSING"
    dp_mapping = next(item for item in dp["err_1_mappings"] if item["subcode"] == actor_subcode)
    assert registry[actor_subcode] == "ERR_UNAUTHENTICATED"
    assert dp_mapping["top_level"] == registry[actor_subcode]
    require_repository_test(
        "DP-1",
        "DP-1-GATE-ERR-REGISTRY-MAPPING-001",
        "tests/test_t0_delta_authority_gates.py::test_dp_actor_context_mapping_matches_err1_registry",
    )


def test_err1_tenant_redaction_gate_points_to_named_registry_rows() -> None:
    err = contract("ERR-1")
    gate = next(
        item
        for item in gates("ERR-1")["gates"]
        if item["id"] == "ERR_1_GATE_120_TENANT_HTTP_REDACTION_PRECEDENCE"
    )
    registry = err["registry"]["subcodes"]
    rows_by_code = {item["subcode"]: (index, item) for index, item in enumerate(registry)}
    gate_assertions = {
        assertion["details"]["json_pointer"]: assertion["details"]["equals"]
        for assertion in gate["assertions"]
        if assertion["type"] == "json_pointer_equals"
    }

    for subcode in (
        "TEN_TENANT_CONTEXT_MISSING",
        "TEN_TENANT_MISMATCH",
        "TEN_RLS_DENIED",
        "TEN_CROSS_TENANT_HIDDEN",
        "TEN_SUPPORT_MODE_UNAUTHORIZED",
    ):
        index, entry = rows_by_code[subcode]
        assert gate_assertions[f"/registry/subcodes/{index}/subcode"] == subcode
        assert gate_assertions[f"/registry/subcodes/{index}/top_level"] == entry["top_level"]

    require_repository_test(
        "ERR-1",
        "ERR_1_GATE_120_TENANT_HTTP_REDACTION_PRECEDENCE",
        "tests/test_t0_delta_authority_gates.py::test_err1_tenant_redaction_gate_points_to_named_registry_rows",
    )


def test_missing_tenant_internal_code_matches_err_registry_and_seat_authority() -> None:
    err = contract("ERR-1")
    seat = contract("SEAT-1")
    ten = contract("TEN-1")
    subcode = "TEN_TENANT_CONTEXT_MISSING"
    registry_entry = next(
        item for item in err["registry"]["subcodes"] if item["subcode"] == subcode
    )
    leaf_mapping = next(
        item
        for item in err["mappings"]["ash_3"]["leaf_error_overrides"]
        if item["ash_error_leaf"] == "Ash.Error.Invalid.TenantRequired"
    )
    translation_rule = next(
        rule
        for rule in err["mappings"]["ash_3"]["translation_algorithm"]
        if "Ash.Error.Invalid.TenantRequired" in rule
    )
    ten_mapping = ten["tenancy"]["hide_existence"]["when_missing_tenant"]
    external = err["mappings"]["tenant_hidden_http_boundary"]["external_response"]

    assert registry_entry["top_level"] == "ERR_FORBIDDEN"
    assert leaf_mapping["top_level_code"] == registry_entry["top_level"]
    assert leaf_mapping["subcode"] == subcode
    assert "ERR_FORBIDDEN" in translation_rule
    assert seat["tenancy"]["missing_tenant_context"]["error_code"] == registry_entry["top_level"]
    assert ten_mapping["top_level"] == "ERR_NOT_FOUND"
    assert external["top_level_code"] == "ERR_NOT_FOUND"
    assert external["subcode"] is None
    require_repository_test(
        "ERR-1",
        "ERR_1_GATE_120_TENANT_HTTP_REDACTION_PRECEDENCE",
        "tests/test_t0_delta_authority_gates.py::test_missing_tenant_internal_code_matches_err_registry_and_seat_authority",
    )


def test_new_tax_subcodes_are_registered_once_with_declared_top_level() -> None:
    err = contract("ERR-1")
    tax = contract("TAX-1")
    subcodes = err["registry"]["subcodes"]
    top_level_codes = [item["code"] for item in err["registry"]["top_level_codes"]]
    assert len(top_level_codes) == len(set(top_level_codes))
    registered_subcodes = [item["subcode"] for item in subcodes]
    assert len(registered_subcodes) == len(set(registered_subcodes))
    for subcode, declaration in tax["subcodes_declared"].items():
        matches = [item for item in subcodes if item["subcode"] == subcode]
        assert len(matches) == 1
        declared_top_level = declaration.get("top_level", declaration.get("code"))
        assert matches[0]["top_level"] == declared_top_level
    for subcode in ("TAX_ITEM_REF_TYPE_UNKNOWN", "TAX_CONTEXT_DIGEST_MISMATCH"):
        assert next(item for item in subcodes if item["subcode"] == subcode)["top_level"] == "ERR_VALIDATION"
    require_repository_test(
        "ERR-1",
        "ERR_1_GATE_140_TAX_SUBCODES_REGISTERED",
        "tests/test_t0_delta_authority_gates.py::test_new_tax_subcodes_are_registered_once_with_declared_top_level",
    )


def test_evt_ordering_keys_exist_in_payload_or_permitted_required_extensions() -> None:
    evt = contract("EVT-1")
    assert invalid_ordering_key_refs(evt["event_types"], evt["event_envelope"]) == []

    event_types = {
        "valid.payload": {
            "ordering": {"key": ["order_id"]},
            "required_data_keys": ["order_id"],
            "required_extensions": [],
        },
        "valid.envelope": {
            "ordering": {"ordering_key": ["org_id"]},
            "required_data_keys": [],
            "required_extensions": ["org_id"],
        },
        "invalid.phantom": {
            "ordering": {"ordering_key": ["phantom_id"]},
            "required_data_keys": [],
            "required_extensions": [],
        },
    }
    assert invalid_ordering_key_refs(event_types, evt["event_envelope"]) == [
        ("invalid.phantom", "phantom_id")
    ]
    require_repository_test(
        "EVT-1",
        "EVT-1-P0-ORDERING-KEY-VALIDITY-001",
        "tests/test_t0_delta_authority_gates.py::test_evt_ordering_keys_exist_in_payload_or_permitted_required_extensions",
    )


def test_t0_evt2_setup_action_errors_are_registered_and_unique() -> None:
    err = contract("ERR-1")
    evt = contract("EVT-2")
    registered = {item["code"] for item in err["registry"]["top_level_codes"]}
    actions = evt["domain_actions"]
    for action_name in (
        "create_event",
        "create_occurrence",
        "publish_event",
        "open_occurrence_sales",
        "close_occurrence_sales",
    ):
        action_errors = actions[action_name]["errors"]
        assert action_errors
        assert len(action_errors) == len(set(action_errors))
        assert set(action_errors) <= registered
    require_repository_test(
        "EVT-2",
        "EVT2_T0_SETUP_ACTION_ERROR_CODES",
        "tests/test_t0_delta_authority_gates.py::test_t0_evt2_setup_action_errors_are_registered_and_unique",
    )


def test_seat_bucket_creation_uses_registered_authorization_error() -> None:
    err = contract("ERR-1")
    seat = contract("SEAT-1")
    registered = {item["code"] for item in err["registry"]["top_level_codes"]}
    action_errors = seat["domain_actions"]["create_inventory_bucket"]["errors"]
    assert len(action_errors) == len(set(action_errors))
    assert set(action_errors) <= registered
    assert "ERR_FORBIDDEN" in action_errors
    require_repository_test(
        "SEAT-1",
        "SEAT-1-GATE-NEW-001",
        "tests/test_t0_delta_authority_gates.py::test_seat_bucket_creation_uses_registered_authorization_error",
    )


def test_t0_offer_action_errors_are_registered_and_unique() -> None:
    err = contract("ERR-1")
    offer = contract("OFFER-1")
    registered = {item["code"] for item in err["registry"]["top_level_codes"]}
    for action_name in (
        "create_offer",
        "create_product",
        "create_product_revision",
        "create_offer_window",
        "activate_offer",
        "activate_product",
        "archive_offer",
        "archive_product",
    ):
        action_errors = offer["domain_actions"][action_name]["errors"]
        assert action_errors
        assert len(action_errors) == len(set(action_errors))
        assert set(action_errors) <= registered
    require_repository_test(
        "OFFER-1",
        "OFFER-1-T0-ACTION-ERRORS",
        "tests/test_t0_delta_authority_gates.py::test_t0_offer_action_errors_are_registered_and_unique",
    )


def test_obs_registry_includes_t0_checkout_operation() -> None:
    obs = contract("OBS-1")
    iam = contract("IAM-1")
    ord_contract = contract("ORD-1")
    operation_id = "ORD-1.create_checkout"
    assert operation_id in obs["operation_id_binding"]["t0_operation_ids"]
    assert ord_contract["domain_actions"]["create_checkout"]["idempotency"]["operation_id"] == operation_id
    assert iam["approved_authority_corrections"]["capability_action_map"]["ord.checkout.create"] == operation_id
    assert obs["operation_registry"][operation_id] == {
        "operation_id": operation_id,
        "contract_id": "ORD-1",
        "action_id": "create_checkout",
    }
    require_repository_test(
        "OBS-1",
        "OBS1-T0-OPERATION-IDS",
        "tests/test_t0_delta_authority_gates.py::test_obs_registry_includes_t0_checkout_operation",
    )


def test_obs_registry_includes_t0_bucket_claim_operation() -> None:
    obs = contract("OBS-1")
    iam = contract("IAM-1")
    seat = contract("SEAT-1")
    operation_id = "SEAT-1.claim_bucket_inventory"
    assert operation_id in obs["operation_id_binding"]["t0_operation_ids"]
    assert seat["domain_actions"]["claim_bucket_inventory"]["idempotency"]["operation_id"] == operation_id
    assert iam["approved_authority_corrections"]["capability_action_map"]["seat.inventory_bucket.claim"] == operation_id
    assert obs["operation_registry"][operation_id] == {
        "operation_id": operation_id,
        "contract_id": "SEAT-1",
        "action_id": "claim_bucket_inventory",
    }
    require_repository_test(
        "OBS-1",
        "OBS1-T0-OPERATION-IDS",
        "tests/test_t0_delta_authority_gates.py::test_obs_registry_includes_t0_bucket_claim_operation",
    )


def test_obs_registry_covers_t0_required_domain_actions() -> None:
    obs = contract("OBS-1")
    expected = {
        "EVT-2.create_event",
        "EVT-2.create_occurrence",
        "EVT-2.publish_event",
        "EVT-2.open_occurrence_sales",
        "EVT-2.close_occurrence_sales",
        "OFFER-1.create_offer",
        "OFFER-1.create_product",
        "OFFER-1.create_product_revision",
        "OFFER-1.create_offer_window",
        "OFFER-1.activate_offer",
        "OFFER-1.activate_product",
        "OFFER-1.archive_offer",
        "OFFER-1.archive_product",
        "OFFER-1.build_cart_quote",
        "OFFER-1.emit_ord_line_items",
        "ORD-1.create_checkout",
        "PRICE-1.create_program",
        "PRICE-1.create_revision",
        "PRICE-1.activate_revision",
        "PRICE-1.create_phase",
        "PRICE-1.create_rule",
        "PRICE-1.create_snapshot",
        "PRICE-1.activate_snapshot",
        "PRICE-1.consume_snapshot",
        "SEAT-1.create_inventory_bucket",
        "SEAT-1.claim_bucket_inventory",
        "SEAT-1.verify_bucket_hold_proofs",
        "SEAT-1.extend_bucket_hold_grace",
        "SEAT-1.release_bucket_hold",
        "SEAT-1.expire_bucket_holds",
    }
    operation_ids = obs["operation_id_binding"]["t0_operation_ids"]
    assert len(operation_ids) == len(expected)
    assert set(operation_ids) == expected
    assert set(obs["operation_registry"]) == expected
    for operation_id in expected:
        contract_id, action_id = operation_id.split(".", 1)
        assert obs["operation_registry"][operation_id] == {
            "operation_id": operation_id,
            "contract_id": contract_id,
            "action_id": action_id,
        }
        owner = contract(contract_id)
        if contract_id == "PRICE-1":
            action_names = {
                action["name"]
                for resource in owner["ash_3x_surface"]["resources"]
                for action in resource.get("actions", [])
            }
        else:
            action_names = set(owner["domain_actions"])
        assert action_id in action_names
    require_repository_test(
        "OBS-1",
        "OBS1-T0-OPERATION-IDS",
        "tests/test_t0_delta_authority_gates.py::test_obs_registry_covers_t0_required_domain_actions",
    )


def test_price_tax_jurisdiction_error_matches_tax_and_err_registries() -> None:
    err = contract("ERR-1")
    tax = contract("TAX-1")
    price = contract("PRICE-1")
    subcode = "TAX_JURISDICTION_REQUIRED"
    err_entry = [item for item in err["registry"]["subcodes"] if item["subcode"] == subcode]
    assert len(err_entry) == 1
    assert err_entry[0]["top_level"] == tax["subcodes_declared"][subcode]["top_level"] == "ERR_PRECONDITION"
    assert price["subcodes_declared"][subcode]["top_level"] == err_entry[0]["top_level"]


def _check_taxctx_vector(vector: dict, field_order: list[str]) -> None:
    transcript = vector["expected_canonical_string"]
    components = transcript.split("|")
    assert [component.partition("=")[0] for component in components] == field_order
    assert all("=" in component for component in components)
    actual_digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    assert actual_digest == vector["expected_sha256_hex"]


def _taxctx_transcript(context: dict, field_order: list[str]) -> str:
    values = []
    for field in field_order:
        value = context.get(field)
        values.append(f"{field}={'' if value is None else value}")
    return "|".join(values)


def test_taxctx_v2_has_one_exact_transcript_and_verified_vectors() -> None:
    tax = contract("TAX-1")
    invariant = tax["invariants"]["tax_context_digest"]
    canonical = invariant["canonical_string_TAXCTX_V2"]
    assert canonical["field_order"] == TAXCTX_V2_FIELDS
    assert canonical["delimiter"] == "|"
    assert "SHA-256" in canonical["digest"] and "UTF-8" in canonical["digest"]
    assert "test_vectors_TAXCTX_V1" not in invariant

    vectors = tax["conformance_vectors"]["TAXCTX_V2"]["vectors"]
    invariant_vectors = invariant["test_vectors_TAXCTX_V2"]
    assert len(vectors) >= 3
    conformance_by_id = {vector["id"]: vector for vector in vectors}
    invariant_by_id = {vector["id"]: vector for vector in invariant_vectors}
    assert set(conformance_by_id) == set(invariant_by_id)
    for vector in vectors:
        _check_taxctx_vector(vector, TAXCTX_V2_FIELDS)
        invariant_vector = invariant_by_id[vector["id"]]
        assert set(invariant_vector["context"]) == set(TAXCTX_V2_FIELDS)
        assert invariant_vector["expected_canonical_string"] == vector["expected_canonical_string"]
        assert invariant_vector["expected_digest_sha256_hex"] == vector["expected_sha256_hex"]
        assert _taxctx_transcript(invariant_vector["context"], TAXCTX_V2_FIELDS) == vector["expected_canonical_string"]
    resolver = tax["domain_actions"][0]
    tax_point_strategies = tax["resource_model"]["resources"][0]["attributes"][13]["enum"]
    assert all(
        vector["context"]["tax_point_strategy"] in tax_point_strategies
        for vector in invariant_vectors
    )
    rounding_modes = next(
        output["enum"]
        for output in resolver["outputs"]
        if output["name"] == "rounding_mode"
    )
    general_rounding_modes = ["half_even_minor_units", "half_up_minor_units"]
    assert tax["tax_defaults"]["rounding_mode"] == "half_even_minor_units"
    assert rounding_modes == general_rounding_modes
    compute_rounding_modes = next(
        input_["enum"]
        for input_ in tax["domain_actions"][1]["inputs"]
        if input_["name"] == "rounding_mode"
    )
    assert compute_rounding_modes == general_rounding_modes
    assert all(
        vector["context"]["rounding_mode"] in rounding_modes
        for vector in invariant_vectors
    )
    assert {vector["context"]["rounding_mode"] for vector in invariant_vectors} == set(general_rounding_modes)
    profile_id_output = next(
        output for output in resolver["outputs"] if output["name"] == "tax_profile_id"
    )
    assert "used for tax computation and digest" not in profile_id_output["description"].lower()
    assert "not a TAXCTX-V2 digest field" in profile_id_output["description"]
    rounding_output = next(
        output for output in resolver["outputs"] if output["name"] == "rounding_mode"
    )
    assert "tax_defaults" not in rounding_output.get("description", "")

    offer = contract("OFFER-1")
    t0_rounding = offer["domain_actions"]["build_cart_quote"]["tax_context_t0_lock"]
    assert t0_rounding["required_rounding_mode"] == "half_even_minor_units"
    require_repository_test(
        "TAX-1",
        "TAX-1-P0-TAXCTX-V2-PITIC-001",
        "tests/test_t0_delta_authority_gates.py::test_taxctx_v2_has_one_exact_transcript_and_verified_vectors",
    )


def test_price_signature_separates_provenance_fields_from_taxctx_transcript() -> None:
    price = contract("PRICE-1")
    tax = contract("TAX-1")
    input_model = price["signature_spec"]["input_model"]
    value_mapping = input_model["quote_value_mapping"]
    assert value_mapping["fields"] == [
        "tax_profile_id",
        "applicable_tax_rate_revision_refs",
        "tax_pricing_mode",
        "evaluated_at_utc",
        "digest_version",
        "digest_sha256",
        "opaque_pii_jurisdiction_evidence_ref",
        "jurisdiction_evidence_sha256",
    ]
    assert value_mapping["digest_wrapper_fields"] == {
        "digest_version": "tax_context_digest_version",
        "digest_sha256": "tax_context_digest_sha256",
    }
    assert value_mapping["digest_values_are_identical"] is True
    digest_fields = tax["invariants"]["tax_context_digest"]["canonical_string_TAXCTX_V2"]["field_order"]
    assert digest_fields == TAXCTX_V2_FIELDS
    assert set(value_mapping["fields"]).isdisjoint(digest_fields)
    require_repository_test(
        "PRICE-1",
        "PRICE-1.GATE.T0.002",
        "tests/test_t0_delta_authority_gates.py::test_price_signature_separates_provenance_fields_from_taxctx_transcript",
    )


def test_product_revision_pins_tax_profile_and_quote_uses_exact_active_profile() -> None:
    offer = contract("OFFER-1")
    tax = contract("TAX-1")
    create_revision = offer["domain_actions"]["create_product_revision"]
    creation_guard = " ".join(create_revision["validation_rules"])
    assert "TaxProfile MUST exist and belong to inputs.org_id" in creation_guard
    assert "does not require the profile to be active" in creation_guard

    quote_rules = " ".join(offer["domain_actions"]["build_cart_quote"]["validation_rules"])
    assert "ProductRevision.tax_profile_id" in quote_rules
    assert "MUST be active and usable for selling at quote time" in quote_rules
    assert "MUST NOT substitute another profile" in quote_rules

    resolver = next(
        item
        for item in tax["domain_actions"]
        if any(output.get("name") == "tax_profile_id" for output in item.get("outputs", []))
        and any(input_.get("name") == "tax_profile_id" for input_ in item.get("inputs", []))
    )
    inputs = {item["name"]: item for item in resolver["inputs"]}
    outputs = {item["name"]: item for item in resolver["outputs"]}
    assert inputs["tax_profile_id"]["required"] is True
    assert outputs["tax_profile_id"]["required"] is True
    assert outputs["inclusion_mode"]["required"] is True
    assert outputs["evaluated_at_utc"]["required"] is True
    assert outputs["digest_version"]["enum"] == ["TAXCTX-V2"]
    assert outputs["digest_sha256"]["type"] == "sha256_hex"


def test_t0_tax_quote_uses_locked_rate_and_null_evidence_mappings() -> None:
    offer = contract("OFFER-1")
    quote = offer["domain_actions"]["build_cart_quote"]
    mappings = quote["price_snapshot_input_mapping"]
    assert mappings["applicable_tax_rate_revision_refs"] == (
        "[the one resolved TAX-1 tax_rate_id] for the single T0 TAXCTX-V2 context"
    )
    assert mappings["opaque_pii_jurisdiction_evidence_ref"] == "null for T0 org_location quotes"
    assert mappings["jurisdiction_evidence_sha256"] == "null for T0 org_location quotes"
    assert quote["tax_context_resolution_input_mapping"]["event_jurisdiction_hint"] == (
        "null for T0 org_location quotes; do not project EVT-2 Occurrence.venue"
    )
    lock = quote["tax_context_t0_lock"]
    assert lock["required_tax_profile_default_tax_basis"] == "org_location"
    assert lock["unsupported_tax_bases"] == ["event_location", "customer_location"]
    assert lock["evidence_fields_are_signed_nulls"] is True
    rules = " ".join(quote["validation_rules"])
    assert "T0 MUST require default_tax_basis=org_location" in rules
    assert "TAX_JURISDICTION_REQUIRED" in rules
    assert "MUST NOT infer" in rules and "Occurrence.venue" in rules
    require_repository_test(
        "OFFER-1",
        "OFFER-1-T0-QUOTE-GUARDS",
        "tests/test_t0_delta_authority_gates.py::test_t0_tax_quote_uses_locked_rate_and_null_evidence_mappings",
    )


def test_price_signature_binds_tax_provenance_outside_taxctx_digest() -> None:
    price = contract("PRICE-1")
    signed_fields = set(price["signature_spec"]["input_model"]["snapshot_fields_in_order"])
    assert {
        "tax_profile_id",
        "applicable_tax_rate_revision_refs",
        "evaluated_at_utc",
        "opaque_pii_jurisdiction_evidence_ref",
        "jurisdiction_evidence_sha256",
        "tax_context_digest_version",
        "tax_context_digest_sha256",
    } <= signed_fields
