"""Contract-content gates for the coordinated T0 successor set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def contract(doc_id: str) -> dict:
    path = next((ROOT / "contracts" / doc_id / "extracted").glob("*Contract*.json"))
    return json.loads(path.read_text())


def action(doc_id: str, name: str) -> dict:
    return contract(doc_id)["domain_actions"][name]


def text_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for part in value for item in text_values(part)]
    if isinstance(value, dict):
        return [item for part in value.values() for item in text_values(part)]
    return []


def _contract_version_identity_mismatches(gates_pack: dict) -> list[tuple[str, object, object]]:
    expected_version = gates_pack.get("contract_ref", {}).get("version")
    mismatches = []
    for gate in gates_pack.get("gates", []):
        for assertion in gate.get("assertions", []):
            details = assertion.get("details", {})
            if (
                assertion.get("mode") == "automated"
                and assertion.get("type") == "json_pointer_equals"
                and details.get("artifact_kind") == "contract"
                and details.get("json_pointer") == "/version"
                and details.get("equals") != expected_version
            ):
                mismatches.append((gate.get("id", "<unknown>"), details.get("equals"), expected_version))
    return mismatches


def test_offer_setup_is_governed_and_activation_is_guarded() -> None:
    offer = contract("OFFER-1")
    actions = offer["domain_actions"]
    assert {
        "create_offer",
        "create_product",
        "create_product_revision",
        "create_offer_window",
        "activate_offer",
        "activate_product",
        "archive_offer",
        "archive_product",
    } <= set(actions)
    for name in ("activate_offer", "activate_product"):
        assert "ERR_PRECONDITION" in actions[name]["errors"]
        assert actions[name]["state_transition"]["from"] == "draft"
        assert actions[name]["state_transition"]["to"] == "active"
        assert actions[name]["validation_rules"]
    for name in ("archive_offer", "archive_product"):
        assert actions[name]["state_transition"]["terminal"] is True
    assert offer["state_lifecycle"]["Offer"]["states"] == ["draft", "active", "archived"]
    assert offer["state_lifecycle"]["Product"]["states"] == ["draft", "active", "archived"]


def test_product_revision_uses_reusable_price_program_revision() -> None:
    offer = contract("OFFER-1")
    revision = next(r for r in offer["data_model"]["resources"] if r["name"] == "ProductRevision")
    fields = {a["name"] for a in revision["required_attributes"]}
    assert "pricing_program_revision_id" in fields
    assert "price_snapshot_id" not in fields
    quote_rules = " ".join(action("OFFER-1", "build_cart_quote")["validation_rules"])
    assert "transaction-specific" in quote_rules
    assert "consumed_by_order_id" in quote_rules
    assert "PRICE-1.create_snapshot" in " ".join(action("OFFER-1", "build_cart_quote")["price_snapshot_lifecycle"].values())
    price = contract("PRICE-1")
    snapshot = next(x for x in price["ash_3x_surface"]["resources"] if x["resource"] == "Ticketing.Pricing.PricingSnapshot")
    price_actions = {x["name"] for x in snapshot["actions"]}
    assert {"create_snapshot", "activate_snapshot", "consume_snapshot"} <= price_actions


def test_bucket_setup_derives_capacity_and_initializes_shards_deterministically() -> None:
    seat = contract("SEAT-1")
    create = action("SEAT-1", "create_inventory_bucket")
    assert "effective_capacity_ceiling" not in create["inputs_required"]
    guards = " ".join(create["validation_rules"])
    assert "base_capacity + oversell_allowance_fixed" in guards
    assert "EVT-2" in guards and "org_id" in guards
    protocol = " ".join(create["concurrency_protocol"]["sequence"])
    assert "current_version=0" in protocol
    assert "sold_count=held_count=0" in protocol
    assert "InventoryBucketCursor" in protocol and "InventoryBucketShard" in protocol
    formula = seat["law_constants"]["bucket_shard_capacity_distribution"]["formula"]
    assert "floor(total_ceiling / shard_count)" in formula
    assert "total_ceiling mod shard_count" in formula


def test_bucket_claim_and_read_only_proof_are_tenant_and_actor_bound() -> None:
    claim = action("SEAT-1", "claim_bucket_inventory")
    assert "hold_signature" in claim["output_minimum"]
    verify = action("SEAT-1", "verify_bucket_hold_proofs")
    assert verify["side_effects_separation"] == "read_only"
    rules = " ".join(verify["validation_rules"])
    assert "org_id" in rules and "actor_id" in rules and "actor_type" in rules
    assert "constant time" in rules
    assert "ERR_NOT_FOUND / TEN_CROSS_TENANT_HIDDEN" in rules
    assert "now" in rules and "expires_at_utc_usec" in rules
    assert "No seat_id is returned or inferred" in rules
    basis = contract("SEAT-1")["signature_security"]["bucket_hold_signature"]
    assert "expires_at_utc_usec" not in basis["derived_from"]
    assert "Expiry is intentionally excluded" in basis["rule"]


def test_bucket_lifecycle_updates_counters_and_uses_existing_grace_limits() -> None:
    seat = contract("SEAT-1")
    lifecycle = seat["bucket_hold_lifecycle"]
    actions = {row["action"]: row for row in lifecycle["transitions"]}
    assert set(actions) == {
        "claim_bucket_inventory",
        "release_bucket_hold",
        "expire_bucket_holds",
        "allocate_bucket_hold",
        "extend_bucket_hold_grace",
    }
    assert "decrement held_count once" in actions["release_bucket_hold"]["side_effects"]
    assert "decrement held_count once" in actions["expire_bucket_holds"]["side_effects"]
    allocated = actions["allocate_bucket_hold"]["side_effects"]
    assert "decrement held_count" in allocated and "increment sold_count" in allocated
    assert "InventoryBucketAllocation" in allocated
    grace = action("SEAT-1", "extend_bucket_hold_grace")
    assert "hold_grace_extension_count_max" in " ".join(grace["validation_rules"])
    assert "hold_grace_extension_seconds_max" in " ".join(grace["validation_rules"])
    assert "hold_total_ttl_seconds_cap" in " ".join(grace["validation_rules"])
    limits = seat["limits_and_budgets"]
    assert limits["hold_grace_extension_count_max"] == 1
    assert limits["hold_grace_extension_seconds_max"] == 180
    assert "inventory counters remain unchanged" in " ".join(grace["side_effects"])
    grace_protocol = grace["concurrency_protocol"]
    assert grace_protocol["locks_1_namespace"] == 103
    assert "SM-0 CAS" in " ".join(grace_protocol["required_sequence"])
    assert "Do not change shard counters." in " ".join(grace_protocol["required_sequence"])
    for action_name in ("release_bucket_hold", "expire_bucket_holds", "allocate_bucket_hold"):
        protocol = action("SEAT-1", action_name)["concurrency_protocol"]
        assert protocol["locks_1_namespace"] == 103
        assert "SM-0 CAS" in " ".join(protocol["required_sequence"])


def test_bucket_exhaustion_uses_registered_err1_conflict() -> None:
    seat = contract("SEAT-1")
    mapping = action("SEAT-1", "claim_bucket_inventory")["errors"]["capacity_exhausted"]
    assert mapping == {"top_level": "ERR_CONFLICT", "subcode": "SEAT_CAPACITY_EXHAUSTED"}
    assert "ERR_INSUFFICIENT_INVENTORY" not in " ".join(text_values(seat))
    err = contract("ERR-1")
    registered = {x["subcode"]: x["top_level"] for x in err["registry"]["subcodes"]}
    assert registered[mapping["subcode"]] == mapping["top_level"]


def test_bucket_claim_race_uses_atomic_capacity_predicate() -> None:
    seat = contract("SEAT-1")
    claim = action("SEAT-1", "claim_bucket_inventory")
    predicate = claim["concurrency_protocol"]["atomic_predicate"]
    assert "held_count = held_count + :qty" in predicate
    assert "sold_count + held_count + :qty" in predicate
    assert "<= capacity_limit" in predicate
    assert seat["law_constants"]["max_shard_probe_attempts"] == "shard_count (probe all shards exactly once)"
    assert "secondary_hash_permutation" in seat["law_constants"]["bucket_shard_overflow"]["strategy"]


def test_order_accepts_bucket_proofs_and_preserves_seat_checkout_path() -> None:
    order = contract("ORD-1")
    checkout = action("ORD-1", "create_checkout")
    assert "pricing_snapshot_id" in checkout["inputs_required"]
    assert "seat_hold_proofs" in checkout["inputs_optional"]
    assert "bucket_hold_proofs" in checkout["inputs_optional"]
    assert checkout["seat_and_bucket_proof_rule"]["at_least_one_set_nonempty"] is True
    rules = " ".join(checkout["validation_rules"])
    for expected in ("SEAT-1.verify_hold_proofs", "SEAT-1.verify_bucket_hold_proofs", "bucket_id", "quantity", "occurrence_id"):
        assert expected in rules
    assert "MUST NOT invent a seat_id" in rules
    order_resource = next(r for r in order["data_model"]["resources"] if r["name"] == "Order")
    assert "bucket_hold_ids" in {a["name"] for a in order_resource["required_attributes"]}
    line_items = next(a for a in order_resource["required_attributes"] if a["name"] == "line_items")
    assert "inventory_claims" in line_items["items"]["required"]
    finalize = action("ORD-1", "finalize_checkout")
    assert "bucket_hold_ids" in finalize["output_minimum"]
    paired = order["paired_inventory_finalization"]
    assert paired["bucket_allocation_action"] == "SEAT-1.allocate_bucket_hold"
    assert "commit or roll back together" in paired["atomicity"]
    assert any("same Postgres transaction" in rule for rule in finalize["validation_rules"])
    quote_binding = order["quote_snapshot_binding"]
    assert quote_binding["checkout_input"] == "ORD-1.create_checkout.pricing_snapshot_id"
    assert quote_binding["persisted_order_field"] == "Order.price_snapshot_id"
    assert quote_binding["consume_action"] == "PRICE-1.consume_snapshot"
    assert "PRICE-1 owns snapshot activation, expiry, and consumed_by_order_id transitions" in quote_binding["ownership"]
    assert "pricing_snapshot_id" not in checkout["output_minimum"]


def test_order_rejects_invalid_bucket_proofs_and_bounds_expiry() -> None:
    rules = " ".join(action("SEAT-1", "verify_bucket_hold_proofs")["validation_rules"])
    for invalid in ("constant time", "actor_id", "actor_type", "org_id", "status", "expires_at_utc_usec"):
        assert invalid in rules
    order_rules = " ".join(action("ORD-1", "create_checkout")["validation_rules"])
    assert "occurrence_id, bucket_id and quantity exactly" in order_rules
    assert "active quote expiry" in order_rules
    assert "every bound bucket hold expiry" in order_rules
    assert "extend_bucket_hold_grace" in order_rules


def test_single_order_checkout_does_not_emit_unregistered_event() -> None:
    checkout = action("ORD-1", "create_checkout")
    assert checkout["event_emission"]["emitted_events"] == []
    assert "does not register" in checkout["event_emission"]["reason"]
    ord_contract = contract("ORD-1")
    group_action = ord_contract["domain_actions"]["create_checkout_group"]
    group_text = " ".join(text_values(group_action))
    assert "ticketing.order.checkout_created.v1" in group_text
    assert "ticketing.order.checkout_created.v1" not in contract("EVT-1")["event_types"]


def test_event_publication_and_sale_window_transitions_are_governed() -> None:
    evt = contract("EVT-2")
    publish = action("EVT-2", "publish_event")
    assert {key: publish["state_transition"][key] for key in ("from", "to", "terminal")} == {"from": "draft", "to": "published", "terminal": False}
    assert "published_at_utc=database_now" in publish["state_transition"]["side_effects"]
    assert publish["outbox_event"] == "ticketing.event.published.v1"
    registry = contract("EVT-1")["event_types"]
    assert registry[publish["outbox_event"]]["required_data_keys"] == ["event_id", "version"]
    open_sales = action("EVT-2", "open_occurrence_sales")
    close_sales = action("EVT-2", "close_occurrence_sales")
    assert open_sales["state_transition"]["from"] == "scheduled"
    assert open_sales["state_transition"]["to"] == "sales_open"
    assert close_sales["state_transition"]["from"] == "sales_open"
    assert close_sales["state_transition"]["to"] == "sales_closed"
    assert "Parent Event MUST be published" in " ".join(open_sales["validation_rules"])
    assert "sales_open_at_utc < sales_close_at_utc" in " ".join(open_sales["validation_rules"])
    assert "database UTC" in evt["state_lifecycle"]["buyer_eligibility"]


def test_illegal_lifecycle_transitions_fail_closed() -> None:
    offer = contract("OFFER-1")
    for resource in ("Offer", "Product"):
        rows = offer["state_lifecycle"][resource]["transitions"]
        activate = next(x for x in rows if x["to"] == "active")
        assert activate["invalid_behavior"] == "ERR_PRECONDITION with no write"
    evt = contract("EVT-2")["state_lifecycle"]
    publish = next(x for x in evt["Event"]["transitions"] if x["to"] == "published")
    assert publish["invalid_behavior"].startswith("ERR_PRECONDITION")
    sales_open = next(x for x in evt["Occurrence.sales"]["transitions"] if x["to"] == "sales_open")
    assert sales_open["invalid_behavior"] == "ERR_PRECONDITION; no write"


def test_product_revision_create_can_produce_every_required_field() -> None:
    offer = contract("OFFER-1")
    revision = next(row for row in offer["data_model"]["resources"] if row["name"] == "ProductRevision")
    action_spec = action("OFFER-1", "create_product_revision")
    inputs = set(action_spec["inputs_required"])
    derived = set(action_spec["persisted_attribute_sources"])
    required = {row["name"] for row in revision["required_attributes"]}
    assert required <= inputs | derived
    assert {"is_bundle", "bundle_apportionment_map", "rounding_strategy", "primary_entitlement_id"} <= inputs
    rules = " ".join(action_spec["validation_rules"])
    assert "is_bundle=false requires bundle_apportionment_map=null" in rules
    assert "MUST be supplied explicitly" in rules
    assert "MUST NOT infer a primary entitlement" in rules
    assert "database clock at insert" in action_spec["persisted_attribute_sources"]["created_at_utc"]
    deps = {row["doc_id"]: row["min_version"] for row in offer["dependencies"]}
    assert deps["PRICE-1"] == "3.5.6"
    assert deps["EVT-2"] == "2.6.2"


def test_offer_quote_fails_closed_for_inactive_or_ineligible_sale_authority() -> None:
    quote = action("OFFER-1", "build_cart_quote")
    guards = quote["quote_preconditions"]
    assert guards["offer_status"] == "active"
    assert guards["product_status"] == "active"
    assert guards["product_revision"]["belongs_to_product"] is True
    assert guards["offer_window"]["belongs_to_offer"] is True
    assert guards["offer_window"]["database_utc_interval"] == "starts_at_utc <= now < ends_at_utc"
    assert "EVT-2" in guards["occurrence_eligibility"]
    assert "active" in guards["pricing_program_revision"]
    assert "same org_id supplied as inputs.org_id" in guards["tenant_binding"]
    assert guards["invalid_behavior"] == {
        "error": "ERR_PRECONDITION",
        "quote_created": False,
        "pricing_snapshot_created": False,
        "no_quote_or_snapshot": True,
    }
    assert {
        "draft-offer", "archived-offer", "draft-product", "archived-product",
        "database-utc-before-window", "database-utc-at-or-after-window-end",
        "occurrence-not-sale-eligible", "pricing-program-revision-not-active",
    } <= set(guards["rejected_cases"])


def test_offer_archival_timestamp_matches_resource_and_transition() -> None:
    offer = contract("OFFER-1")
    for resource_name, action_name in (("Offer", "archive_offer"), ("Product", "archive_product")):
        resource = next(row for row in offer["data_model"]["resources"] if row["name"] == resource_name)
        archived = next(row for row in resource["required_attributes"] if row["name"] == "archived_at_utc")
        assert archived["type"] == "utc_datetime_usec_nullable"
        transition = action("OFFER-1", action_name)["state_transition"]
        assert "archived_at_utc=database_now" in transition["side_effects"]
        assert action_name in [row["action"] for row in offer["state_lifecycle"][resource_name]["transitions"]]


def test_order_quote_uses_one_persisted_price_snapshot_and_price_owned_consumption() -> None:
    order = contract("ORD-1")
    checkout = action("ORD-1", "create_checkout")
    field_names = {row["name"] for row in next(r for r in order["data_model"]["resources"] if r["name"] == "Order")["required_attributes"]}
    assert "price_snapshot_id" in field_names
    assert "pricing_snapshot_id" not in field_names
    assert checkout["inputs_required"].count("pricing_snapshot_id") == 1
    assert "price_snapshot_id" in checkout["output_minimum"]
    assert "pricing_snapshot_id" not in checkout["output_minimum"]
    binding = order["quote_snapshot_binding"]
    assert binding["equality"] == "Order.price_snapshot_id MUST equal ORD-1.create_checkout.inputs.pricing_snapshot_id."
    assert binding["consume_action"] == "PRICE-1.consume_snapshot"
    rules = " ".join(checkout["validation_rules"])
    assert "PRICE-1.create_snapshot" not in rules
    assert "ORD MUST NOT create or request another snapshot" in rules
    assert "ORD MUST NOT mutate consumed_by_order_id directly" in rules
    assert "PRICE-1.consume_snapshot" in rules
    price_law = next(x["text"] for x in order["invariants"] if x.get("id") == "ORD-INV-PRICE-SIG-004")
    assert "ORD MUST NOT request or create a replacement snapshot" in price_law
    assert "PRICE-SIG-V4" in price_law


def test_order_ttl_hold_and_atomicity_laws_cover_both_inventory_types() -> None:
    order = contract("ORD-1")
    ttl = next(x["text"] for x in order["invariants"] if x.get("rule_id") == "ORD-1-P0-TTL-001")
    assert all(term in ttl for term in ("database_now", "quote snapshot expiry", "seat hold expiry", "bucket hold expiry"))
    hold = next(x["text"] for x in order["invariants"] if x.get("rule_id") == "ORD-1-P0-HOLD-001")
    assert "if Order.seat_hold_ids is non-empty" in hold
    assert "if Order.bucket_hold_ids is non-empty" in hold
    assert "Bucket-only Orders do not require seat proofs" in hold
    assert "Mixed Orders require both exact proof sets" in hold
    atomic = next(x["text"] for x in order["invariants"] if x.get("rule_id") == "ORD-1-P0-ATOMIC-001")
    assert "every inventory claim" in atomic and "bucket allocation action" in atomic
    boundary = next(x["text"] for x in order["rules"] if x.get("rule_id") == "ORD-1-P0-FINALIZE-ATOMIC-BOUNDARY")
    assert "SEAT-1.allocate_hold" in boundary and "SEAT-1.allocate_bucket_hold" in boundary
    assert "LED-1.post_intent" in boundary and "single Postgres transaction" in boundary
    line_shape = next(x["text"] for x in order["rules"] if x.get("rule_id") == "ORD-1-P0-LINE-ITEMS-SHAPE")
    assert "immutable price-and-inventory snapshot" in line_shape
    assert "GA bucket claims MUST include bucket_id and quantity" in line_shape
    norms = " ".join(text_values([order["domain_actions"], order["invariants"], order["rules"], order["quote_snapshot_binding"]]))
    assert "When creating a PRICE snapshot for a checkout" not in norms
    assert "ORD MUST request PRICE-1 signature_version" not in norms


def test_order_finalization_proof_sets_cover_seat_bucket_and_mixed_orders() -> None:
    rule = action("ORD-1", "finalize_checkout")["bound_hold_proof_rule"]
    assert rule["at_least_one_persisted_set_nonempty"] is True
    assert rule["seat"]["verified_set_equals"] == "Order.seat_hold_ids"
    assert rule["bucket"]["verified_set_equals"] == "Order.bucket_hold_ids"
    assert rule["accepted_shapes"] == ["seat-only", "bucket-only", "mixed seat and bucket"]
    assert rule["mixed_order"] == "Both proof inputs are required and each verified set MUST equal its persisted Order set exactly."
    assert {
        "mixed-order-missing-seat-proofs", "mixed-order-missing-bucket-proofs",
        "extra-seat-proof", "extra-bucket-proof", "changed-seat-proof", "changed-bucket-proof",
    } <= set(rule["rejected_cases"])
    assert "Missing, extra, or changed" in rule["invalid_behavior"]


def test_order_inventory_claim_identity_is_inside_immutable_snapshot() -> None:
    order = contract("ORD-1")
    resource = next(r for r in order["data_model"]["resources"] if r["name"] == "Order")
    immutable = resource["immutability"]["rule"]
    assert "bucket_hold_ids" in immutable
    assert "line_items[].inventory_claims" in immutable
    assert "MUST NOT replace a bound seat or bucket hold" in immutable
    assert any(x.get("rule_id") == "ORD-1-P0-INVENTORY-CLAIMS-IMMUTABLE" for x in order["rules"])


def test_order_dependency_floor_covers_new_seat_authority() -> None:
    order = contract("ORD-1")
    dep = next(x for x in order["dependencies"] if x["doc_id"] == "SEAT-1")
    assert dep["min_version"] == "4.1.0"
    assert order["dependency_floors"]["SEAT-1"] == "4.1.0"
    assert order["dependency_pins"]["gc_001_chain"]["SEAT-1"] == "4.1.0"
    price_dep = next(x for x in order["dependencies"] if x["doc_id"] == "PRICE-1")
    assert price_dep["min_version"] == "3.5.6"
    assert order["dependency_floors"]["PRICE-1"] == "3.5.6"
    assert order["dependency_pins"]["gc_001_chain"]["PRICE-1"] == "3.5.6"
    called = " ".join(text_values([action("ORD-1", "create_checkout"), action("ORD-1", "finalize_checkout")]))
    assert all(name in called for name in (
        "SEAT-1.verify_bucket_hold_proofs", "SEAT-1.extend_bucket_hold_grace", "SEAT-1.allocate_bucket_hold"
    ))


def test_event_publication_timestamp_and_outbox_metadata_agree() -> None:
    evt = contract("EVT-2")
    event = next(x for x in evt["data_model"]["resources"] if x["name"] == "Event")
    published = next(x for x in event["attributes"] if x["name"] == "published_at_utc")
    assert published["nullable"] is True
    assert evt["emits_events"] is True
    publications = [
        row for row in evt["outbox_events"]
        if row["event_name"] == "ticketing.event.published.v1"
    ]
    assert len(publications) == 1
    publication = publications[0]
    assert publication["event_name"] == "ticketing.event.published.v1"
    assert publication["required_keys"] == ["event_id", "version"]
    publish = action("EVT-2", "publish_event")
    assert publish["outbox_event"] == publication["event_name"]
    assert "published_at_utc=null" in " ".join(action("EVT-2", "create_event")["validation_rules"])
    assert "published_at_utc=database_now" in " ".join(publish["validation_rules"])
    assert "version" in publish["state_transition"]["side_effects"]
    temporal = next(x["text"] for x in evt["rules"] if x.get("rule_id") == "EVT-2-T0-PUBLICATION-TEMPORAL-001")
    assert "draft MUST imply published_at_utc=null" in temporal
    assert "published MUST imply published_at_utc is non-null" in temporal
    assert "Archival MUST preserve" in temporal


def test_successor_artifact_identity_matches_each_candidate_version() -> None:
    versions = {"OFFER-1": "2.0.0", "SEAT-1": "4.1.0", "ORD-1": "4.0.1", "EVT-2": "3.0.0"}
    stale = {
        "OFFER-1": ("1.2.0", "1.3.2", "1.3.4"),
        "SEAT-1": ("3.6.1", "3.6.2", "3.7.1", "3.7.2", "4.0.0"),
        "ORD-1": ("3.7.10", "3.8.2", "3.8.4", "4.0.0"),
        "EVT-2": ("2.5.2", "2.5.4", "2.6.1", "2.6.2"),
    }
    for doc_id, version in versions.items():
        current = contract(doc_id)
        assert current["version"] == version
        expected_contract = f"{doc_id}_Contract_v{version}.json"
        assert (ROOT / "contracts" / doc_id / "extracted" / expected_contract).is_file()
        if current.get("artifact_name") is not None:
            assert current["artifact_name"] == expected_contract
        gates_path = next((ROOT / "contracts" / doc_id / "extracted").glob("*_Test_Gates_v*.json"))
        gates = json.loads(gates_path.read_text())
        assert gates["version"] == version
        assert gates["contract_ref"] == {"doc_id": doc_id, "version": version}
        expected_gates = f"{doc_id}_Test_Gates_v{version}.json"
        if gates.get("artifact_name") is not None:
            assert gates["artifact_name"] == expected_gates
        bundle_path = ROOT / "contracts" / doc_id / "extracted" / "bundle.manifest.json"
        bundle = json.loads(bundle_path.read_text())
        assert bundle["doc_id"] == doc_id
        assert bundle["bundle"] == {"bundle_id": doc_id, "bundle_version": version}
        assert bundle["version"] == version
        assert {row["path"] for row in bundle["files"]} == {expected_contract, expected_gates}
        for metadata in (current, gates):
            for key in ("title", "description"):
                value = metadata.get(key, "")
                for previous in stale[doc_id]:
                    assert previous not in value
        for previous in stale[doc_id]:
            assert previous not in current.get("artifact_name", "")
            assert previous not in gates.get("artifact_name", "")
            assert previous not in gates["title"]


def test_offer_quote_passes_explicit_idempotency_to_price_snapshot_creation() -> None:
    offer = contract("OFFER-1")
    quote = action("OFFER-1", "build_cart_quote")
    price = contract("PRICE-1")
    snapshot = next(
        resource for resource in price["ash_3x_surface"]["resources"]
        if resource["resource"] == "Ticketing.Pricing.PricingSnapshot"
    )
    create = next(item for item in snapshot["actions"] if item["name"] == "create_snapshot")
    mapping = quote["price_snapshot_input_mapping"]

    assert "idempotency_key" in quote["inputs"]
    assert set(create["accepts"]) <= set(mapping)
    assert mapping["idempotency_key"] == "inputs.idempotency_key (pass through unchanged)"
    rules = " ".join(quote["validation_rules"])
    assert "same (org_id, operation_id, key)" in rules
    assert "identical canonical request_hash" in rules
    assert "EXT_IDEMPOTENCY_REPLAY" in rules
    assert "MUST NOT derive or replace idempotency_key" in rules


def test_ord_supplies_actor_type_to_each_seat_bucket_action() -> None:
    order = contract("ORD-1")
    seat = contract("SEAT-1")
    binding = order["bucket_hold_actor_binding"]
    for action_name in ("create_checkout", "finalize_checkout"):
        order_action = action("ORD-1", action_name)
        assert "actor_type" in order_action["inputs_required"]
        assert "authenticated tenancy context" in order_action["actor_type_source"]
    for name in ("verify_bucket_hold_proofs", "extend_bucket_hold_grace", "allocate_bucket_hold"):
        required = set(seat["domain_actions"][name]["inputs_required"])
        mapping = binding["seat_action_inputs"][name]
        assert required <= set(mapping)
        assert mapping["actor_type"] == "authenticated tenancy context.actor_type"


def test_offer_ord_dependency_is_one_way_and_ord_quote_contract_is_generic() -> None:
    offer = contract("OFFER-1")
    order = contract("ORD-1")
    offer_ord = next(dep for dep in offer["dependencies"] if dep["doc_id"] == "ORD-1")
    assert offer_ord["min_version"] == "3.8.3"
    assert not any(dep["doc_id"] == "OFFER-1" for dep in order["dependencies"])
    assert "paired_quote_binding" not in order
    checkout = action("ORD-1", "create_checkout")
    rules = " ".join(checkout["validation_rules"])
    assert "exact active, unexpired PRICE-1 quote snapshot" in rules
    assert "OFFER-1.build_cart_quote" not in rules
    assert "ORD MUST NOT create or request another snapshot" in rules


def test_t0_planning_snapshot_matches_current_installed_authority() -> None:
    manifest = json.loads((ROOT / "contracts" / "manifest.json").read_text())
    records = {row["doc_id"]: row for row in manifest["contracts"]}
    canon = contract("CANON-1")
    tracer = (ROOT / "planning" / "tracers" / "T0-tenant-scoped-ga-pending-sale.md").read_text()
    roadmap = (ROOT / "planning" / "ROADMAP.md").read_text()

    assert canon["version"] == records["CANON-1"]["version"]
    assert len(canon["canonical_bundles"]) == 56
    assert f"**Authority snapshot:** CANON-1 {canon['version']}" in tracer
    assert f"CANON-1 {canon['version']} pins {len(canon['canonical_bundles'])} CANON members" in tracer
    assert "**Contracts baseline:** `ea6ebbb84664aeb383d21ccbd92d30dd1a93939f`" in tracer
    assert "**Implementation baseline:** `9bbec7e5c926f8036ef32e261fbeb8ae9377e0ac`" in tracer
    snapshot_versions = {row["doc_id"]: row["version"] for row in canon["canonical_bundles"]}
    snapshot_versions["CANON-1"] = canon["version"]
    for doc_id in (
        "CANON-1", "V42-0", "CS-0", "BP-0", "EVT-2", "TEN-1", "IAM-1", "IAM-2",
        "OFFER-1", "SEAT-1", "PRICE-1", "ORD-1", "TAX-1", "PII-1", "API-0", "ERR-1",
        "OBS-1", "EVT-1", "LOCKS-1",
    ):
        assert f"| {doc_id} | {snapshot_versions[doc_id]} |" in tracer
    assert records["EXT-1"]["membership"] == "DEPENDENCY_ONLY"
    assert f"| EXT-1 | {records['EXT-1']['version']} | DEPENDENCY_ONLY |" in tracer
    assert "EXT-1 does not own T0 HTTP idempotency or durable idempotency semantics" in tracer

    assert "**Status: COMPLETE**" in roadmap.split("## B0", 1)[1].split("## T0", 1)[0]
    assert "JCSchoeman96/ticketing" in roadmap
    assert "ticketing/" in roadmap
    assert "Phoenix, Ash, and AshPostgres bootstrap exists" in roadmap
    assert "PostgreSQL and migration bootstrap" in roadmap
    assert "contract-authority verification" in roadmap
    assert "B0 no longer blocks T0" in roadmap
    assert "**Status: NEXT**" in roadmap.split("## T0", 1)[1].split("## T1", 1)[0]
    assert "not an authority gap" in roadmap
    for stale in (
        "does not yet define a complete GA-hold-to-order path",
        "implementation repository is unresolved",
        "`mix.exs` is absent",
        "B0 must locate the implementation home",
        "CANON-1 v2.0.10",
    ):
        assert stale not in roadmap + tracer


def test_t0_tracer_records_api_locks_and_ord_idempotency_ownership() -> None:
    api = contract("API-0")
    locks = contract("LOCKS-1")
    checkout = action("ORD-1", "create_checkout")
    idem = checkout["idempotency"]
    tracer = (ROOT / "planning" / "tracers" / "T0-tenant-scoped-ga-pending-sale.md").read_text()

    assert any("HTTP Idempotency-Key header" in row["text"] for row in api["rules"])
    assert locks["idempotency"]["storage"]["uniqueness"] == ["org_id", "operation_id", "key"]
    assert "request_hash" in locks["idempotency"]["storage"]["required_fields"]
    assert idem["operation_id"] == "ORD-1.create_checkout"
    assert idem["persisted_identity"] == ["org_id", "operation_id", "key"]
    assert idem["request_hash"]["formula"] == "lowercase_hex(SHA-256(UTF-8(RFC8785_JCS(normalized_request))))"
    assert "hold_signature" in idem["request_hash"]["excluded_fields"]
    assert idem["request_hash"]["normalization_rules"]["proof_material"] == (
        "Hash only stable hold_id values; do not hash hold_signature. Validate the supplied signature separately before releasing an outcome."
    )
    assert "API-0 owns the required HTTP `Idempotency-Key` header" in tracer
    assert "LOCKS-1 owns durable idempotency identity `(org_id, operation_id, key)`" in tracer
    assert "a separately persisted canonical `request_hash`" in tracer
    assert "`ORD-1.create_checkout`" in tracer
    assert idem["request_hash"]["formula"] in tracer
    for field in idem["request_hash"]["normalized_fields"]:
        assert f"- `{field}`" in tracer
    assert "Proof identity reduces to `hold_id`" in tracer
    assert "`hold_signature` is excluded from request hashing" in tracer
    assert "LOCKS_IDEMPOTENCY_KEY_REUSE_MISMATCH" in tracer
    assert "EXT_IDEMPOTENCY_REPLAY" in tracer


def test_t0_tracer_records_offer_quote_authorization_delegation_and_eligibility_locks() -> None:
    offer = contract("OFFER-1")
    manifest = json.loads((ROOT / "contracts" / "manifest.json").read_text())
    installed_offer = next(row for row in manifest["contracts"] if row["doc_id"] == "OFFER-1")
    quote = action("OFFER-1", "build_cart_quote")
    delegation = quote["delegation_context"]
    eligibility = next(rule for rule in offer["rules"] if rule["rule_id"] == "OFFER-1-LAW-ELIGIBILITY-SIGNED")
    prerequisites = next(rule for rule in offer["rules"] if rule["rule_id"] == "OFFER-1-LAW-PREREQ-001")
    claim_quarantine = next(
        rule for rule in offer["rules"] if rule.get("id") == "OFFER-1-LAW-T0-KEY-CLAIM-QUARANTINE"
    )
    quote_rules = " ".join(quote["validation_rules"])
    tracer = (ROOT / "planning" / "tracers" / "T0-tenant-scoped-ga-pending-sale.md").read_text()

    assert installed_offer["version"] == offer["version"] == "2.0.0"
    assert "Authorize offer.quote.create for OFFER-1.build_cart_quote" in quote["purpose"]
    assert delegation["capability"] == "offer.quote.create"
    assert delegation["buyer_action"] == "OFFER-1.build_cart_quote"
    assert delegation["subordinate_actions"] == ["PRICE-1.create_snapshot", "PRICE-1.activate_snapshot"]
    assert delegation["mechanism"] == "scoped_authenticated_delegation"
    assert delegation["generic_bypass_allowed"] is False
    assert delegation["preserved"] == [
        "originating_actor_id", "org_id", "request_id", "trace_id", "Idempotency-Key"
    ]
    assert "Buyer authorization is offer.quote.create" in quote_rules
    assert "PRICE-1 actions are subordinate governed actions and are not buyer-authorized endpoints" in quote_rules
    assert "Generic bypass and authorize?: false are forbidden" in quote_rules
    assert "OFFER MUST NOT write PRICE resources directly" in quote_rules

    assert eligibility["level"] == "P0"
    assert "T0 MUST use public eligibility" in eligibility["text"]
    assert "T0 MUST use public eligibility and MUST NOT validate or consume SignedEligibilityClaim" in eligibility["text"]
    assert prerequisites["level"] == "P0"
    assert "T0 does not support child occurrences or prerequisite claims" in prerequisites["text"]
    assert claim_quarantine["level"] == "P0"
    assert "T0 create_offer_window MUST accept only eligibility_policy.mode=public" in claim_quarantine["must"]
    assert "prerequisite_policy.mode=none or null" in claim_quarantine["must"]
    assert "T0 build_cart_quote MUST fail closed if a claim or prerequisite proof is required" in claim_quarantine["must"]

    assert "`offer.quote.create`" in tracer
    assert "`OFFER-1.build_cart_quote` owns the buyer-facing quote boundary" in tracer
    assert "`PRICE-1.create_snapshot` and `PRICE-1.activate_snapshot` are subordinate governed actions" in tracer
    assert "They are not buyer-authorized endpoints" in tracer
    for context in ("originating actor attribution", "`org_id`", "`request_id`", "`trace_id`", "boundary `Idempotency-Key`"):
        assert context in tracer
    assert "scoped authenticated delegation" in tracer
    assert "Generic authorization bypass, including `authorize?: false`, is forbidden" in tracer
    assert "OFFER owns eligibility, ProductRevision validation, tax/pricing binding, and quote invariants" in tracer
    assert "PRICE owns snapshot construction, signature, activation, and pricing invariants" in tracer
    assert "OFFER MUST NOT write PRICE resources directly" in tracer
    assert "T0 MUST use `public` eligibility" in tracer
    assert "MUST NOT validate or consume `SignedEligibilityClaim`" in tracer
    assert "EligibilityIssuerKey" in tracer and "claim nonce" in tracer
    assert "fail closed" in tracer
    assert "T0 does not support child occurrences or prerequisite claims" in tracer
    assert "Do not implement entitlement or prerequisite eligibility machinery as part of T0" in tracer


def test_t0_tracer_separates_live_proof_validation_from_completed_replay_possession() -> None:
    seat = contract("SEAT-1")
    checkout = action("ORD-1", "create_checkout")
    finalization = action("ORD-1", "finalize_checkout")
    replay = checkout["idempotency"]["replay_security"]
    transcript = seat["signature_security"]["hold_signature"]
    tracer = (ROOT / "planning" / "tracers" / "T0-tenant-scoped-ga-pending-sale.md").read_text()

    assert replay["completed_identical_replay_only"] is True
    assert replay["seat_proof_possession_action"] == "SEAT-1.verify_hold_proof_possession"
    assert replay["bucket_proof_possession_action"] == "SEAT-1.verify_bucket_hold_proof_possession"
    assert "SEAT-1.verify_hold_proof_possession" not in json.dumps(finalization)
    assert "SEAT-1.verify_bucket_hold_proof_possession" not in json.dumps(finalization)
    for name in ("verify_hold_proofs", "verify_bucket_hold_proofs"):
        live_rules = " ".join(action("SEAT-1", name)["validation_rules"])
        assert "active" in live_rules
        assert "expires" in live_rules
    for name in ("verify_hold_proof_possession", "verify_bucket_hold_proof_possession"):
        assert "already-completed identical LOCKS-1 replay" in seat["domain_actions"][name]["purpose"]
    assert transcript["canonical_string_spec"]["format"] == (
        "org_id|hold_id|occurrence_id|seat_id|actor_id|actor_type"
    )
    assert "expires_at_utc" not in transcript["derived_from"]
    assert "grace_extension_count" in action("SEAT-1", "extend_hold_grace")["validation_rules"][3]
    assert not any("hold_signature_batch" in json.dumps(value) for value in seat["domain_actions"].values())

    for phrase in (
        "New/effectful checkout",
        "SEAT-1.verify_hold_proofs",
        "SEAT-1.verify_bucket_hold_proofs",
        "Completed-identical replay",
        "SEAT-1.verify_hold_proof_possession",
        "SEAT-1.verify_bucket_hold_proof_possession",
        "Authenticate tenant context and actor context again",
        "Cryptographically verify every supplied signature",
        "signature binds to its referenced `hold_id`",
        "verified hold-ID sets to equal the normalized submitted proof-ID sets",
        "Do not check mutable hold status, expiry, inventory availability, or quantity",
        "Do not extend grace, rebind lines, or mutate hold, inventory, Order, allocation, or grace state",
        "Return only the stored original outcome",
        "invalid replacement signature",
        "must not execute checkout again",
        "org_id|hold_id|occurrence_id|seat_id|actor_id|actor_type",
        "grace extension does not rotate",
        "hold_signature_batch",
        "Finalization remains bound to full live proof verification",
    ):
        assert phrase in tracer

    action_section = tracer.split("## Required actions", 1)[1].split("\n## ", 1)[0]
    for name in (
        "create_inventory_bucket", "claim_bucket_inventory", "verify_hold_proofs",
        "verify_bucket_hold_proofs", "extend_bucket_hold_grace", "release_bucket_hold",
        "expire_bucket_holds", "allocate_bucket_hold", "verify_hold_proof_possession",
        "verify_bucket_hold_proof_possession",
    ):
        assert f"`{name}`" in action_section
    assert "completed-identical replay only" in action_section
    assert "They do not replace either full live verifier" in action_section


def test_t0_tracer_records_tax_profile_taxctx_and_rounding_authority() -> None:
    tax = contract("TAX-1")
    offer = contract("OFFER-1")
    quote = action("OFFER-1", "build_cart_quote")
    digest = tax["invariants"]["canonical_string_TAXCTX-V2"]
    expected_fields = [
        "org_id", "jurisdiction_code", "inclusion_mode", "rounding_mode", "tax_class",
        "rate_basis_points", "tax_scope", "tax_basis", "provider_mode", "provider_name",
        "tax_point_strategy",
    ]
    tracer = (ROOT / "planning" / "tracers" / "T0-tenant-scoped-ga-pending-sale.md").read_text()

    assert digest["field_order"] == expected_fields
    assert digest["delimiter"] == "|"
    assert "SHA-256" in digest["digest"] and "lowercase hexadecimal" in digest["digest"]
    assert tax["tax_defaults"]["rounding_mode"] == "half_even_minor_units"
    resolver = next(row for row in tax["domain_actions"] if row["action"] == "resolve_tax_context_for_event")
    resolver_modes = next(output["enum"] for output in resolver["outputs"] if output["name"] == "rounding_mode")
    assert {"half_even_minor_units", "half_up_minor_units"} <= set(resolver_modes)
    assert quote["tax_context_t0_lock"]["required_rounding_mode"] == "half_even_minor_units"
    assert quote["tax_context_t0_lock"]["rate_reference_mapping"] == (
        "Set applicable_tax_rate_revision_refs to a one-element list containing the exact TAX-1 tax_rate_id returned for the single resolved T0 TAXCTX-V2 context."
    )
    tax_rules = " ".join(quote["validation_rules"])
    assert "exact ProductRevision.tax_profile_id" in tax_rules
    assert "same tenant-owned, active profile" in tax_rules
    assert tax["emits_events"] is False and tax["outbox_events"] == []

    assert "ProductRevision immutably pins `tax_profile_id`" in tracer
    assert "same-tenant, active TaxProfile" in tracer
    assert "`default_tax_basis = org_location`" in tracer
    assert "`event_location` and `customer_location` are unsupported" in tracer
    assert "MUST NOT infer jurisdiction from `Occurrence.venue`" in tracer
    assert "No new raw PII storage" in tracer
    assert "`applicable_tax_rate_revision_refs = [TAX-1.tax_rate_id]`" in tracer
    assert "`opaque_pii_jurisdiction_evidence_ref = null`" in tracer
    assert "`jurisdiction_evidence_sha256 = null`" in tracer
    assert "signed PRICE-SIG-V4 snapshot" in tracer
    assert "half_even_minor_units" in tracer and "half_up_minor_units" in tracer
    assert "TAXCTX-V2 field order" in tracer
    field_positions = [tracer.index(f"{index}. `{field}`") for index, field in enumerate(expected_fields, 1)]
    assert field_positions == sorted(field_positions)
    assert "Encode every field as `key=value`" in tracer
    assert "join fields with `|`" in tracer
    assert "encode as UTF-8" in tracer
    assert "null or missing optional values as an empty value after `=`" in tracer
    assert "Hash the bytes with SHA-256" in tracer
    assert "TAXCTX-V2-0002" in tracer
    assert "PRICE-1 preserves both explicit nulls inside the signed PRICE-SIG-V4 snapshot" in tracer
    assert "TAX-1 remains eventless" in tracer


def test_t0_tracer_end_to_end_sequence_and_boundary_match_installed_authority() -> None:
    ordc = contract("ORD-1")
    evt1 = contract("EVT-1")
    tax = contract("TAX-1")
    ten = contract("TEN-1")
    tracer = (ROOT / "planning" / "tracers" / "T0-tenant-scoped-ga-pending-sale.md").read_text()
    sequence_start = tracer.index("End-to-end sequence")
    sequence_end = tracer.find("\n## ", sequence_start)
    sequence = tracer[sequence_start:sequence_end if sequence_end >= 0 else len(tracer)]

    required_sequence = (
        "Trusted authentication/session infrastructure", "underlying session credential",
        "authoritative `user_id`", "authoritative `session_id`", "candidate `org_id`",
        "requested `active_scope = org`", "requested `active_role`", "TEN-1 `org_membership_probe`",
        "system-internal, transaction-local candidate-org scope", "read only the matching `OrgMembership`",
        "active, non-revoked membership", "persisted `org_membership_id`", "external `ERR_NOT_FOUND`",
        "IAM-1 `t0_trusted_active_session`", "active `User`", "persisted Session",
        "Session.id = session_id", "Session.user_id = user_id", "Session.org_id = proven org_id",
        "revoked_at_utc = null", "expires_at_utc > evaluated_at_utc", "active, non-revoked same-org",
        "Build the active organization persona", "persisted `org_membership_id`, `active_scope = org`, and verified `active_role`",
        "ERR_UNAUTHENTICATED", "ERR_FORBIDDEN",
        "EVT-2.create_event", "EVT-2.create_occurrence",
        "EVT-2.publish_event", "open_occurrence_sales", "PricingProgramRevision",
        "OFFER-1.create_offer", "OFFER-1.create_product_revision", "pricing_program_revision_id",
        "T0-compatible pinned TaxProfile", "SEAT-1.create_inventory_bucket", "buyer sellability",
        "OFFER-1.build_cart_quote", "transaction-specific signed PRICE-SIG-V4 PricingSnapshot",
        "SEAT-1.claim_bucket_inventory", "InventoryBucketHold", "signed bucket hold proof",
        "SEAT-1.verify_bucket_hold_proofs", "ORD-1.create_checkout", "persisted tenant-scoped `draft` Order",
        "same-tenant retrieval", "completed-identical replay",
    )
    positions = [sequence.index(phrase) for phrase in required_sequence]
    assert positions == sorted(positions)
    assert "ProductRevision binds to reusable pricing-program revision authority" in tracer
    assert "It does not bind directly to the transaction-specific PricingSnapshot" in tracer

    assert ordc["domain_actions"]["create_checkout"]["event_emission"]["emitted_events"] == []
    assert evt1["t0_event_registry_dispositions"]["totals"]["DEFERRED_EVENT_REGISTRY_DEBT"] == 53
    assert tax["emits_events"] is False
    assert "53 deferred EVT registry-debt entries remain deferred" in tracer
    assert "single-order `ord-1.create_checkout` emits no event" in tracer.lower()
    assert "T0 stops at the ORD-1 `draft` Order" in tracer
    assert "`finalize_checkout` is a later boundary, outside T0" in tracer
    assert "provider payment confirmation" in tracer
    assert "ticket issuance" in tracer
    assert "ledger work" in tracer
    assert "read-only consumer of an already-issued canonical Session" in tracer
    assert "does not issue a Session or implement `sign_in_with_org` issuance" in tracer
    assert "derive or verify `token_hash`" in tracer
    assert "ticketing.iam.session.created.v1" in tracer
    assert "ticketing.iam.session.revoked.v1" in tracer
    tenant_rules = {row["rule_id"]: row["text"] for row in ten["rules"]}
    assert "hide existence" in tenant_rules["TEN-1-HIDE-001"]
    assert "MUST NOT include the optional 'subcode'" in tenant_rules["TEN-1-BOUNDARY-OMIT-SUBCODE"]
    assert "ERR_NOT_FOUND" in tracer
    assert "TEN_TENANT_CONTEXT_MISSING" in tracer
    assert "Do not leak internal tenant-context subcodes" in tracer


def test_t0_tracer_lifecycle_tables_use_installed_states_and_fences() -> None:
    evt = contract("EVT-2")
    offer = contract("OFFER-1")
    seat = contract("SEAT-1")
    tracer = (ROOT / "planning" / "tracers" / "T0-tenant-scoped-ga-pending-sale.md").read_text()
    event_states = evt["state_lifecycle"]["Event"]["states"]
    occurrence_states = evt["state_lifecycle"]["Occurrence.sales"]["states"]
    offer_states = offer["state_lifecycle"]["Offer"]["states"]
    product_states = offer["state_lifecycle"]["Product"]["states"]
    bucket_states = seat["bucket_hold_lifecycle"]["states"]

    for state in event_states + occurrence_states + offer_states + product_states + bucket_states:
        assert f"`{state}`" in tracer
    for action_name in (
        "create_event", "publish_event", "archive_event", "create_occurrence", "open_occurrence_sales",
        "close_occurrence_sales", "create_offer", "activate_offer", "archive_offer", "create_product",
        "activate_product", "archive_product", "create_product_revision", "create_offer_window",
        "claim_bucket_inventory", "release_bucket_hold", "expire_bucket_holds", "extend_bucket_hold_grace",
        "allocate_bucket_hold",
    ):
        assert action_name in tracer
    assert "Compare-and-swap on lock version and current state" in tracer
    assert "LOCKS-1 namespace 103 and SM-0 CAS" in tracer
    assert "T0 performs no allocation" in tracer
    assert "No Order → `draft`" in tracer


def test_contract_version_identity_checker_reports_a_stale_assertion() -> None:
    gates_pack = {
        "contract_ref": {"doc_id": "OFFER-1", "version": "1.3.4"},
        "gates": [
            {
                "id": "OFFER-1.GATE.0004",
                "assertions": [
                    {
                        "mode": "automated",
                        "type": "json_pointer_equals",
                        "details": {
                            "artifact_kind": "contract",
                            "json_pointer": "/version",
                            "equals": "1.3.2",
                        },
                    }
                ],
            }
        ],
    }

    assert _contract_version_identity_mismatches(gates_pack) == [
        ("OFFER-1.GATE.0004", "1.3.2", "1.3.4")
    ]


def test_p0_gate_contract_version_assertions_match_gate_pack_identity() -> None:
    manifest = json.loads((ROOT / "contracts" / "manifest.json").read_text())
    records = {row["doc_id"]: row for row in manifest["contracts"]}
    canon_record = records["CANON-1"]
    selection_path = (
        ROOT
        / "release-src"
        / "current"
        / "CANON-1"
        / canon_record["version"]
        / "resolved-selection.json"
    )
    selection = json.loads(selection_path.read_text())
    candidate_identities = set()
    for candidate in selection["generation_inputs"]["candidate_releases"]:
        identity = f"{candidate['doc_id']}@{candidate['version']}"
        source_dir = ROOT / "release-src" / "current" / candidate["doc_id"] / candidate["version"]
        release = json.loads((source_dir / "release.json").read_text())
        assert release.get("release_status") == "candidate", f"{identity} is not marked as a candidate"
        gates_path = source_dir / "test-gates.json"
        gates_pack = json.loads(gates_path.read_text())
        candidate_identities.add(identity)
        assert gates_pack["contract_ref"] == {
            "doc_id": candidate["doc_id"],
            "version": candidate["version"],
        }, f"{identity} gate pack contract_ref does not match its candidate"
        assert _contract_version_identity_mismatches(gates_pack) == [], (
            f"{identity} has automated contract /version identity assertions that differ from contract_ref"
        )

    assert candidate_identities
    for candidate in selection["generation_inputs"]["candidate_releases"]:
        selected = records[candidate["doc_id"]]
        assert candidate["version"] == selected["version"]
        assert candidate["sha256"] == selected["zip_sha256"]


def test_installed_tax_rounding_modes_drive_arithmetic_and_keep_t0_lock() -> None:
    tax = contract("TAX-1")
    gates_path = next((ROOT / "contracts" / "TAX-1" / "extracted").glob("*Test_Gates*.json"))
    gate_pack = json.loads(gates_path.read_text())
    general_modes = ["half_even_minor_units", "half_up_minor_units"]

    resolver = next(action for action in tax["domain_actions"] if action["action"] == "resolve_tax_context_for_event")
    resolver_modes = next(output["enum"] for output in resolver["outputs"] if output["name"] == "rounding_mode")
    calculator = next(action for action in tax["domain_actions"] if action["action"] == "compute_tax_for_price_line")
    calculator_modes = next(input_["enum"] for input_ in calculator["inputs"] if input_["name"] == "rounding_mode")
    assert resolver_modes == general_modes
    assert calculator_modes == general_modes
    assert tax["tax_defaults"]["rounding_mode"] == "half_even_minor_units"

    vectors = tax["conformance_vectors"]["TAXCTX_V2"]["vectors"]
    half_up_vector = next(vector for vector in vectors if vector["id"] == "TAXCTX-V2-0002")
    invariant_vectors = tax["invariants"]["tax_context_digest"]["test_vectors_TAXCTX_V2"]
    half_up_invariant_vector = next(vector for vector in invariant_vectors if vector["id"] == "TAXCTX-V2-0002")
    assert {vector["context"]["rounding_mode"] for vector in invariant_vectors} == set(general_modes)
    assert half_up_invariant_vector["context"]["rounding_mode"] == "half_up_minor_units"
    assert half_up_invariant_vector["expected_canonical_string"] == half_up_vector["expected_canonical_string"]
    assert half_up_invariant_vector["expected_digest_sha256_hex"] == half_up_vector["expected_sha256_hex"]
    assert hashlib.sha256(half_up_vector["expected_canonical_string"].encode("utf-8")).hexdigest() == (
        half_up_vector["expected_sha256_hex"]
    )
    assert half_up_vector["expected_sha256_hex"] == "211a958157c02160a2fa33225624166a6ac4493ce8e7385f42998ac5110f8098"

    rounding_rule = tax["invariants"]["rounding"][0]
    assert "resolved TAXCTX-V2 rounding_mode" in rounding_rule
    assert all(mode in rounding_rule for mode in general_modes)
    assert "tax_defaults.rounding_mode=half_even_minor_units is the default" in rounding_rule
    assert "does not prohibit an explicitly resolved half_up_minor_units context" in rounding_rule

    exclusive_rule = tax["invariants"]["calculation_arithmetic"][2]
    assert "round_half_even" not in exclusive_rule
    assert "using the resolved TAXCTX-V2 rounding_mode" in exclusive_rule
    assert "gross_total_minor MUST equal net_total_minor + tax_amount_minor" in exclusive_rule

    offer = contract("OFFER-1")
    quote = offer["domain_actions"]["build_cart_quote"]
    assert quote["tax_context_t0_lock"]["required_rounding_mode"] == "half_even_minor_units"
    t0_rounding_rule = next(
        rule for rule in quote["validation_rules"] if rule.startswith("For T0 quotes, the resolved rounding_mode")
    )
    assert "MUST equal half_even_minor_units" in t0_rounding_rule
    assert "This T0 restriction does not narrow general TAX-1 rounding modes." in t0_rounding_rule

    p0_gate = next(gate for gate in gate_pack["gates"] if gate["id"] == "TAX-1-P0-TAXCTX-V2-PITIC-001")
    assert p0_gate["level"] == "P0" and p0_gate["must"] is True
    expected_gate_values = {
        "/tax_defaults/rounding_mode": "half_even_minor_units",
        "/invariants/rounding/0": rounding_rule,
        "/invariants/calculation_arithmetic/2": exclusive_rule,
        "/invariants/tax_context_digest/test_vectors_TAXCTX_V2/1/context/rounding_mode": "half_up_minor_units",
    }
    for pointer, expected in expected_gate_values.items():
        assert any(
            assertion.get("mode") == "automated"
            and assertion.get("type") == "json_pointer_equals"
            and assertion.get("details", {}).get("artifact_kind") == "contract"
            and assertion["details"].get("json_pointer") == pointer
            and assertion["details"].get("equals") == expected
            for assertion in p0_gate["assertions"]
        )
    assert {
        "details": {
            "ci_task": "python -m pytest -q tests/test_t0_canonical_enablement_contracts.py::test_installed_tax_rounding_modes_drive_arithmetic_and_keep_t0_lock"
        },
        "mode": "automated",
        "type": "property_tests",
    } in p0_gate["assertions"]
