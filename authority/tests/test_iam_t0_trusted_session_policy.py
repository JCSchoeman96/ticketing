from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = "tests/test_iam_t0_trusted_session_policy.py"
POLICY_POINTER = "/authorization_model/t0_trusted_active_session"
AUTH_CONTEXT_POINTER = "/authorization_model/auth_context_shape"
GATE_ID = "IAM-1-GATE-370-T0-TRUSTED-SESSION-CONSUMPTION"
SESSION_EVENTS = (
    "ticketing.iam.session.created.v1",
    "ticketing.iam.session.revoked.v1",
)

EXPECTED_POLICY = {
    "enabled": True,
    "policy_id": "t0_trusted_active_session",
    "caller_boundary": "trusted_authentication_session_infrastructure",
    "public_clients_allowed": False,
    "authoritative_user_id_required": True,
    "authoritative_session_id_required": True,
    "raw_session_token_available_to_t0": False,
    "membership_probe_policy_id": "org_membership_probe",
    "membership_proof_required_before_session_read": True,
    "membership_proof_required_before_role_read": True,
    "session_resource": "IAM-1.Session",
    "session_read_only": True,
    "session_match_fields": ["id", "user_id", "org_id"],
    "session_match_sources": {
        "id": "authoritative_session_id",
        "user_id": "authoritative_user_id",
        "org_id": "proven_org_id",
    },
    "session_status_required": "active",
    "session_revoked_at_utc_required": None,
    "session_expiry_rule": "expires_at_utc > database_evaluated_at_utc",
    "database_time_required": True,
    "user_status_required": "active",
    "membership_status_required": "active",
    "membership_revoked_at_utc_required": None,
    "active_scope_required_for_t0_tenant_capabilities": "org",
    "role_assignment_resource": "IAM-1.OrgRoleAssignment",
    "role_assignment_status_required": "active",
    "role_assignment_revoked_at_required": None,
    "active_role_is_selector_only": True,
    "active_role_must_match_persisted_assignment": True,
    "capability_evaluated_against_active_role_only": True,
    "platform_support_personas_allowed_for_t0_tenant_capabilities": False,
    "caller_supplied_role_list_authoritative": False,
    "session_mutations_allowed": False,
    "session_events_emitted": [],
    "session_failure_code": "ERR_UNAUTHENTICATED",
    "session_failure_subcode": "IAM_SESSION_EXPIRED",
    "role_failure_code": "ERR_FORBIDDEN",
}

# Keys of the IAM-1 4.1.2 auth_context_shape that must remain unchanged.
PRESERVED_AUTH_CONTEXT_KEYS = {
    "actor",
    "assurance_level",
    "assurance_source",
    "consumer_otp_verified_at_utc",
    "impersonator_info",
    "primary_auth_method",
    "request",
    "session_id",
    "step_up_grant_id",
    "step_up_verified_at_utc",
    "verification_flags",
}

PRESERVED_ACTOR = {
    "actor_kind": "human|service|system",
    "org_id": "uuid_v7|nil",
    "org_membership_id": "uuid_v7|nil",
    "roles": "string[]",
    "scopes": "object",
    "user_id": "uuid_v7|nil",
}

ACTIVE_PERSONA_RULE = (
    "When actor has multiple roles across org/platform, each request SHALL carry an explicit "
    "active_scope and active_role; authorization MUST be evaluated against the active persona only."
)

ACTIVE_ROLE_BINDING_NOTE = (
    "The requested active_role MUST match exactly one active, non-revoked OrgRoleAssignment "
    "for the authoritative user_id and proven org_id."
)
AUTH_CONTEXT_BINDING_NOTE = (
    "The constructed auth_context.actor.org_membership_id MUST equal the proven active "
    "OrgMembership id; auth_context.actor.org_id MUST equal the proven org_id; "
    "auth_context.actor.user_id MUST equal the authoritative user_id; and "
    "auth_context.session_id MUST equal the validated persisted Session id."
)


def _manifest() -> dict:
    return json.loads((ROOT / "contracts" / "manifest.json").read_text())


def _manifest_record(doc_id: str) -> dict:
    return next(row for row in _manifest()["contracts"] if row["doc_id"] == doc_id)


def _bundle_payloads(doc_id: str) -> tuple[dict, dict]:
    record = _manifest_record(doc_id)
    bundle_path = ROOT / record["zip_path"]

    with zipfile.ZipFile(bundle_path) as archive:
        contracts = []
        test_gates = []
        for name in archive.namelist():
            if not name.endswith(".json"):
                continue
            artifact = json.loads(archive.read(name))
            if artifact.get("artifact_kind") == "contract":
                contracts.append(artifact)
            elif artifact.get("artifact_kind") == "test_gates":
                test_gates.append(artifact)

    assert len(contracts) == 1
    assert len(test_gates) == 1
    contract = contracts[0]
    gates = test_gates[0]
    assert contract["doc_id"] == doc_id
    assert contract["version"] == record["version"]

    if doc_id != "CANON-1":
        canon, _ = _bundle_payloads("CANON-1")
        pin = next(row for row in canon["canonical_bundles"] if row["doc_id"] == doc_id)
        assert pin["version"] == record["version"]
        assert pin["zip_path"] == record["zip_path"]

    return contract, gates


def test_selected_iam1_defines_t0_trusted_active_session_policy() -> None:
    contract, _ = _bundle_payloads("IAM-1")
    policy = contract["authorization_model"]["t0_trusted_active_session"]

    assert set(policy) == set(EXPECTED_POLICY) | {"notes"}
    assert isinstance(policy["notes"], list) and policy["notes"]
    assert all(isinstance(note, str) and note.strip() for note in policy["notes"])
    assert ACTIVE_ROLE_BINDING_NOTE in policy["notes"]
    assert AUTH_CONTEXT_BINDING_NOTE in policy["notes"]

    comparable = {key: value for key, value in policy.items() if key != "notes"}
    assert comparable == EXPECTED_POLICY
    for key, value in EXPECTED_POLICY.items():
        assert type(policy[key]) is type(value), key
    assert type(policy["session_match_sources"]) is dict


def test_selected_iam1_auth_context_exposes_active_scope_and_role() -> None:
    contract, _ = _bundle_payloads("IAM-1")
    shape = contract["authorization_model"]["auth_context_shape"]

    assert set(shape) == PRESERVED_AUTH_CONTEXT_KEYS | {"active_scope", "active_role"}
    assert shape["active_scope"] == {"type": "atom", "constraints": ["org", "platform"]}
    assert shape["active_role"] == "string"
    assert shape["actor"] == PRESERVED_ACTOR
    assert shape["session_id"] == "uuid_v7"

    authorization = contract["domain_invariants"]["authorization"]
    assert authorization["active_persona_required"] is True
    assert authorization["active_persona_rule"] == ACTIVE_PERSONA_RULE
    assert authorization["t0_tenant_capabilities_require_active_org_persona"] is True
    assert authorization["t0_tenant_capabilities_exclude_platform_and_support_roles"] is True
    assert authorization["org_membership_identity_rule"] == (
        "When an active org persona is selected, auth_context.actor.org_membership_id MUST equal "
        "the stable, server-generated, immutable UUIDv7 identifier of that selected active "
        "OrgMembership row. When no active org persona is selected, auth_context.actor.org_membership_id "
        "MUST be nil."
    )


def test_selected_iam1_gate_370_locks_trusted_session_policy() -> None:
    _, payload = _bundle_payloads("IAM-1")
    matches = [gate for gate in payload["gates"] if gate["id"] == GATE_ID]
    assert len(matches) == 1, f"Expected exactly one {GATE_ID}"
    gate = matches[0]

    assert gate["level"] == "P0"
    assert gate["must"] is True
    assert gate["enforced_by"] == "pytest"

    test_refs = {
        assertion["details"].get("test")
        for assertion in gate["assertions"]
        if assertion["type"] == "property_tests" and assertion["mode"] == "automated"
    }
    for test_name in (
        "test_selected_iam1_defines_t0_trusted_active_session_policy",
        "test_selected_iam1_auth_context_exposes_active_scope_and_role",
        "test_t0_session_consumption_preserves_ten_and_evt_quarantine",
    ):
        assert f"{TEST_FILE}::{test_name}" in test_refs

    locks = {
        assertion["details"]["json_pointer"]: assertion["details"]["equals"]
        for assertion in gate["assertions"]
        if assertion["type"] == "json_pointer_equals"
        and assertion["mode"] == "automated"
        and assertion["details"]["artifact_kind"] == "contract"
    }
    expected = {
        f"{POLICY_POINTER}/{key}": EXPECTED_POLICY[key]
        for key in (
            "enabled",
            "policy_id",
            "caller_boundary",
            "public_clients_allowed",
            "raw_session_token_available_to_t0",
            "membership_probe_policy_id",
            "membership_proof_required_before_session_read",
            "membership_proof_required_before_role_read",
            "session_read_only",
            "session_status_required",
            "database_time_required",
            "active_scope_required_for_t0_tenant_capabilities",
            "active_role_is_selector_only",
            "active_role_must_match_persisted_assignment",
            "capability_evaluated_against_active_role_only",
            "platform_support_personas_allowed_for_t0_tenant_capabilities",
            "caller_supplied_role_list_authoritative",
            "session_mutations_allowed",
            "session_failure_code",
            "role_failure_code",
        )
    }
    expected[f"{AUTH_CONTEXT_POINTER}/active_role"] = "string"
    expected[f"{AUTH_CONTEXT_POINTER}/active_scope/type"] = "atom"
    for pointer, value in expected.items():
        assert pointer in locks, pointer
        assert type(locks[pointer]) is type(value), pointer
        assert locks[pointer] == value, pointer


def test_t0_session_consumption_preserves_ten_and_evt_quarantine() -> None:
    assert _manifest_record("TEN-1")["version"] == "2.0.1"
    assert _manifest_record("IAM-2")["version"] == "1.5.0"
    assert _manifest_record("EVT-1")["version"] == "3.0.0"

    ten, _ = _bundle_payloads("TEN-1")
    probe = ten["tenancy"]["tenant_resolution"]["system_internal_membership_probe"]
    assert probe["policy_id"] == "org_membership_probe"
    assert probe["allowed_resource"] == "IAM-1.OrgMembership"
    assert probe["read_only"] is True
    assert probe["role_lookup_before_proof_allowed"] is False
    assert probe["other_tenant_resource_access_before_proof_allowed"] is False
    assert probe["event_capability_authorization_allowed"] is False
    assert probe["session_promotion_on_failure_allowed"] is False
    global_resources = ten["tenancy"]["global_resources"]["allowed_resources"]
    assert "IAM-1.Session" not in global_resources
    assert "IAM-1.OrgMembership" not in global_resources

    iam, _ = _bundle_payloads("IAM-1")
    session = next(
        resource
        for resource in iam["data_model"]["resources"]
        if resource["name"] == "Session"
    )
    assert session["tenant_scoped"] is True
    assert session.get("global", False) is False
    outbox_names = {event["event_name"] for event in iam["outbox_events"]}
    assert set(SESSION_EVENTS) <= outbox_names

    evt, _ = _bundle_payloads("EVT-1")
    registrations = evt["t0_event_registry_dispositions"]["registrations"]
    for event_name in SESSION_EVENTS:
        registration = registrations[event_name]
        assert registration["disposition"] == "DEFERRED_EVENT_REGISTRY_DEBT"
        assert registration["producer_contract"] == "IAM-1"
        assert registration["quarantine_proof"]["Q1"] == f"T0 does not emit {event_name}."

    iam2, _ = _bundle_payloads("IAM-2")
    assert iam2["doc_id"] == "IAM-2"
