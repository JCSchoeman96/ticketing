from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ORGANIZER_CAPABILITIES = {
    "evt.event.create",
    "evt.event.publish",
    "evt.occurrence.create",
    "evt.occurrence.admission_policy.manage",
    "evt.occurrence.sales_open",
    "evt.occurrence.sales_close",
    "offer.offer.create",
    "offer.product.create",
    "offer.product_revision.create",
    "offer.offer_window.create",
    "offer.offer.activate",
    "offer.product.activate",
    "price.program.create",
    "price.program.revision.create",
    "price.program.revision.activate",
    "price.program.phase.create",
    "price.program.rule.create",
    "seat.inventory_bucket.create",
}

BUYER_CAPABILITIES = {
    "offer.quote.create",
    "seat.inventory_bucket.claim",
    "ord.checkout.create",
}

TENANT_TAX_CAPABILITIES = {
    "tax.profile.create",
    "tax.profile.activate",
}

PLATFORM_CAPABILITIES = {"platform.tax_rate.create"}

EXPECTED_ROLE_SETS = {
    **{capability: {"org_owner", "org_admin"} for capability in ORGANIZER_CAPABILITIES},
    **{capability: {"customer"} for capability in BUYER_CAPABILITIES},
    **{
        capability: {"org_owner", "org_admin", "org_finance_manager"}
        for capability in TENANT_TAX_CAPABILITIES
    },
    "platform.tax_rate.create": {"platform_finance_admin", "super_admin"},
}

EXPECTED_ACTION_MAP = {
    "evt.event.create": "EVT-2.create_event",
    "evt.event.publish": "EVT-2.publish_event",
    "evt.occurrence.create": "EVT-2.create_occurrence",
    "evt.occurrence.admission_policy.manage": "EVT-2.set_occurrence_admission_policy",
    "evt.occurrence.sales_open": "EVT-2.open_occurrence_sales",
    "evt.occurrence.sales_close": "EVT-2.close_occurrence_sales",
    "offer.offer.create": "OFFER-1.create_offer",
    "offer.product.create": "OFFER-1.create_product",
    "offer.product_revision.create": "OFFER-1.create_product_revision",
    "offer.offer_window.create": "OFFER-1.create_offer_window",
    "offer.offer.activate": "OFFER-1.activate_offer",
    "offer.product.activate": "OFFER-1.activate_product",
    "offer.quote.create": "OFFER-1.build_cart_quote",
    "price.program.create": "PRICE-1.create_program",
    "price.program.revision.create": "PRICE-1.create_revision",
    "price.program.revision.activate": "PRICE-1.activate_revision",
    "price.program.phase.create": "PRICE-1.create_phase",
    "price.program.rule.create": "PRICE-1.create_rule",
    "seat.inventory_bucket.create": "SEAT-1.create_inventory_bucket",
    "seat.inventory_bucket.claim": "SEAT-1.claim_bucket_inventory",
    "tax.profile.create": "TAX-1.create_tax_profile",
    "tax.profile.activate": "TAX-1.activate_tax_profile",
    "platform.tax_rate.create": "TAX-1.create_platform_tax_rate",
    "ord.checkout.create": "ORD-1.create_checkout",
}


def _manifest() -> dict:
    return json.loads((ROOT / "contracts" / "manifest.json").read_text())


def _bundle_payloads(doc_id: str) -> tuple[dict, dict]:
    manifest = _manifest()
    record = next(row for row in manifest["contracts"] if row["doc_id"] == doc_id)
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


def _iam1() -> tuple[dict, dict]:
    return _bundle_payloads("IAM-1")


def test_manifest_selected_iam_defines_each_mapped_capability_once() -> None:
    iam, _ = _iam1()
    action_map = iam["approved_authority_corrections"]["capability_action_map"]
    counts = Counter(
        definition["capability"]
        for definition in iam["authorization_model"]["capability_definitions"]
    )

    assert set(action_map) == set(EXPECTED_ACTION_MAP)
    assert action_map == EXPECTED_ACTION_MAP
    assert {capability: counts[capability] for capability in action_map} == {
        capability: 1 for capability in action_map
    }


def test_mapped_capabilities_have_exact_typed_least_privilege_policies() -> None:
    iam, _ = _iam1()
    authorization = iam["authorization_model"]
    definitions = {
        definition["capability"]: definition
        for definition in authorization["capability_definitions"]
    }
    role_definitions = {
        definition["role"]: definition
        for definition in authorization["role_definitions"]
    }
    known_actor_kinds = {actor["kind"] for actor in authorization["actor_kinds"]}

    assert set(EXPECTED_ROLE_SETS) == set(EXPECTED_ACTION_MAP)
    assert len(role_definitions) == len(authorization["role_definitions"])
    for role in authorization["role_definitions"]:
        assert all(assigner in role_definitions for assigner in role["assignable_by"])
    for capability, expected_roles in EXPECTED_ROLE_SETS.items():
        definition = definitions[capability]
        actor_kinds = definition["allowed_actor_kinds"]
        roles = definition["allowed_roles"]
        assert isinstance(actor_kinds, list) and actor_kinds
        assert isinstance(roles, list) and roles
        assert len(actor_kinds) == len(set(actor_kinds))
        assert len(roles) == len(set(roles))
        assert all(isinstance(value, str) and value.strip() for value in actor_kinds)
        assert all(isinstance(value, str) and value.strip() for value in roles)
        assert set(actor_kinds) <= known_actor_kinds
        assert actor_kinds == ["human"]
        assert set(roles) == expected_roles
        assert all(role in role_definitions for role in roles)

    customer = role_definitions["customer"]
    assert customer["scope"] == "org"
    assert set(customer["assignable_by"]) == {"org_owner", "org_admin"}
    assert customer["grant_via"] == ["IAM-2.accept_invite_intent"]
    assert all(
        role_definitions[role]["scope"] == "org"
        for capability in ORGANIZER_CAPABILITIES | BUYER_CAPABILITIES | TENANT_TAX_CAPABILITIES
        for role in EXPECTED_ROLE_SETS[capability]
    )
    assert all(
        role_definitions[role]["scope"] == "platform"
        for role in EXPECTED_ROLE_SETS["platform.tax_rate.create"]
    )

    authorization_policy = iam["domain_invariants"]["authorization"]
    assert authorization_policy["active_persona_required"] is True
    assert authorization_policy["active_persona_rule"] == (
        "When actor has multiple roles across org/platform, each request SHALL carry an explicit active_scope and active_role; "
        "authorization MUST be evaluated against the active persona only."
    )
    assert iam["domain_invariants"]["org_selection"]["active_scope_binding"] == (
        "Requests MUST include org_id for org-scoped actions; platform-scoped actions MUST have org_id=nil. "
        "Mixed-scope requests MUST be rejected."
    )
    assert authorization_policy["orgs_must_not_grant_platform_roles"] is True
    assert authorization_policy["platform_roles_must_not_be_assigned_by_org_admin"] is True
    assert (
        "System automatic sales close is an EVT-2 system initiator policy and is not an IAM organizer capability; "
        "never authorize system through a human capability"
        in iam["approved_authority_corrections"]["constraints"]
    )


def test_session_revoke_capability_uses_the_canonical_org_worker_role() -> None:
    iam, _ = _iam1()
    authorization = iam["authorization_model"]
    session_revoke = next(
        definition
        for definition in authorization["capability_definitions"]
        if definition["capability"] == "iam.session.revoke_self"
    )

    assert "org_worker" in session_revoke["allowed_roles"]
    assert "org_staff" not in session_revoke["allowed_roles"]


def test_tax_capability_uses_exact_platform_action_name_and_scope() -> None:
    iam, _ = _iam1()
    action_map = iam["approved_authority_corrections"]["capability_action_map"]
    tax, _ = _bundle_payloads("TAX-1")

    assert action_map["platform.tax_rate.create"] == "TAX-1.create_platform_tax_rate"
    matches = [
        action
        for action in tax["domain_actions"]
        if action.get("action") == "create_platform_tax_rate"
    ]
    assert len(matches) == 1
    assert matches[0]["capability"] == "platform.tax_rate.create"
    assert matches[0]["authorization_scope"] == "platform"


def test_customer_role_is_granted_only_by_org_scoped_invite_acceptance() -> None:
    iam, _ = _iam1()
    iam2, iam2_gates = _bundle_payloads("IAM-2")
    customer = next(
        role
        for role in iam["authorization_model"]["role_definitions"]
        if role["role"] == "customer"
    )
    invite = next(
        resource
        for resource in iam2["data_model"]["resources"]
        if resource["name"] == "invite_intent"
    )
    policy = iam2["workflows"]["silent_link_invite_flow"]["role_assignment_policy"]

    assert customer["scope"] == "org"
    assert set(customer["assignable_by"]) == {"org_owner", "org_admin"}
    assert customer["grant_via"] == ["IAM-2.accept_invite_intent"]
    assert "target_org_role" in invite["optional_fields"]
    assert policy["target_field"] == "target_org_role"
    assert policy["allowed_target_roles"] == ["customer"]
    assert policy["grant_channel"] == "IAM-2.accept_invite_intent"
    assert policy["invitation_authorization"] == {
        "capability": "iam.member.invite",
        "actor_kind": "human",
        "active_scope": "org",
        "allowed_roles": ["org_admin", "org_owner"],
    }
    assert policy["acceptance_effects"] == {
        "create_org_membership": "if_absent",
        "create_org_role_assignment": {
            "org_id_source": "invite_intent.org_id",
            "role_source": "invite_intent.target_org_role",
            "status": "active",
            "granted_by_user_id_source": "invite_intent.created_by_actor_id",
            "create_if_absent": True,
        },
        "atomic_with_membership": True,
        "idempotency_key": "token_hash",
    }
    assert policy["membership_only_when_target_role_omitted"] is True
    assert policy["platform_role_targets_forbidden"] is True
    assert policy["role_definition_assignable_by_must_include_active_role"] is True
    assert policy["direct_assignment_forbidden"] is True
    assert (
        "Customer role assignments MUST be created through IAM-2 invite acceptance only; "
        "IAM-1 iam.role.assign MUST NOT create a customer assignment directly."
        in iam["approved_authority_corrections"]["constraints"]
    )
    iam1_dependency = next(dep for dep in iam2["dependencies"] if dep["doc_id"] == "IAM-1")
    assert iam1_dependency["min_version"] == "4.1.0"
    invite_gate = next(
        gate
        for gate in iam2_gates["gates"]
        if gate["id"] == "IAM-2-GATE-CUSTOMER-ROLE-INVITE-ASSIGNMENT"
    )
    assert invite_gate["level"] == "P0"
    assert invite_gate["must"] is True
    assert invite_gate["enforced_by"] == "pytest"
    assert any(
        assertion.get("mode") == "automated"
        and assertion.get("type") == "property_tests"
        and assertion.get("details", {}).get("test")
        == "tests/test_iam_t0_authority_closure.py::test_customer_role_is_granted_only_by_org_scoped_invite_acceptance"
        for assertion in invite_gate["assertions"]
    )


def test_customer_invite_handles_existing_and_revoked_org_records() -> None:
    iam2, iam2_gates = _bundle_payloads("IAM-2")
    policy = iam2["workflows"]["silent_link_invite_flow"]["role_assignment_policy"]
    acceptance = policy["acceptance_effects"]
    lifecycle = policy["customer_role_acceptance_lifecycle"]
    gate = next(
        gate
        for gate in iam2_gates["gates"]
        if gate["id"] == "IAM-2-GATE-CUSTOMER-ROLE-INVITE-ASSIGNMENT"
    )

    assert acceptance["create_org_membership"] == "if_absent"
    assert acceptance["create_org_role_assignment"]["create_if_absent"] is True
    assert "existing_state_policy" not in policy
    assert lifecycle["atomicity"] == (
        "Read both resource states before any writes; if either is revoked, reject the entire "
        "acceptance without mutation. Otherwise apply create transitions atomically with invite "
        "acceptance."
    )
    assert lifecycle["common_guards"] == {
        "valid_scoped_invite_token": [
            "invite_intent.status=pending",
            "invite_intent.expires_at_utc > acceptance_time",
            "proof_token.purpose=invite_accept",
            "proof_token.status=active",
            "proof_token.expires_at_utc > acceptance_time",
        ],
        "same_org_id": [
            "proof_token.invite_id=invite_intent.invite_id",
            "proof_token.org_id=invite_intent.org_id",
            (
                "Look up OrgMembership by "
                "(org_id=invite_intent.org_id, user_id=proof_token.subject_user_id)"
            ),
            (
                "Look up OrgRoleAssignment by "
                "(user_id=proof_token.subject_user_id, role=customer, "
                "org_id=invite_intent.org_id)"
            ),
        ],
        "resolved_subject": [
            "proof_token.subject_user_id resolves to a User",
        ],
        "customer_role_target": [
            "invite_intent.target_org_role=customer",
        ],
    }
    common_guard_names = set(lifecycle["common_guards"])
    transitions = lifecycle["transitions"]
    assert [
        (transition["resource"], transition["from"], transition["to"],
         transition["result"], transition["terminal"])
        for transition in transitions
    ] == [
        ("OrgMembership", "absent", "active", "create", False),
        ("OrgMembership", "active", "active", "reuse_without_write", False),
        ("OrgMembership", "revoked", "revoked", "reject_without_write", True),
        ("OrgRoleAssignment", "absent", "active", "create", False),
        ("OrgRoleAssignment", "active", "active", "reuse_without_write", False),
        ("OrgRoleAssignment", "revoked", "revoked", "reject_without_write", True),
    ]
    assert [transition["side_effects"] for transition in transitions] == [
        [
            "Create one active OrgMembership keyed by (org_id=invite_intent.org_id, "
            "user_id=proof_token.subject_user_id) in the atomic invite-accept transaction."
        ],
        ["No OrgMembership write; reuse the matching active row."],
        ["Do not write invite_intent, proof_token, OrgMembership, or OrgRoleAssignment rows."],
        [
            "Create one active customer OrgRoleAssignment using the canonical by_user_role_org "
            "identity (user_id=proof_token.subject_user_id, role=customer, "
            "org_id=invite_intent.org_id) and granted_by_user_id=invite_intent.created_by_actor_id "
            "in the atomic invite-accept transaction."
        ],
        ["No OrgRoleAssignment write; reuse the matching active row."],
        ["Do not write invite_intent, proof_token, OrgMembership, or OrgRoleAssignment rows."],
    ]
    expected_transition_guards = [
        {"OrgMembership=absent", "OrgRoleAssignment!=revoked"},
        {"OrgMembership=active", "OrgRoleAssignment!=revoked"},
        {"OrgMembership=revoked"},
        {"OrgRoleAssignment=absent", "OrgMembership!=revoked"},
        {"OrgRoleAssignment=active", "OrgMembership!=revoked"},
        {"OrgRoleAssignment=revoked"},
    ]
    for transition, state_guards in zip(transitions, expected_transition_guards, strict=True):
        assert common_guard_names <= set(transition["guards"])
        assert state_guards <= set(transition["guards"])
        if transition["from"] == "revoked":
            assert transition["failure_mapping"] == "revoked_state_error_mapping"
    assert lifecycle["revoked_state_error_mapping"] == {
        "internal": {
            "top_level_code": "ERR_FORBIDDEN",
            "exposure": "internal_only",
            "subcode": None,
        },
        "public_invite_accept": {
            "response_class": "uniform_success_or_invalid_token",
            "http_status": 404,
            "top_level_code": "ERR_NOT_FOUND",
            "omit_fields": ["detail"],
            "omit_extensions": ["subcode"],
        },
    }
    assert gate["description"] == (
        "Customer role invite acceptance MUST use explicit OrgMembership and "
        "OrgRoleAssignment transitions with shared guards, atomic side effects, terminal "
        "revoked rejection, and internal/public error mapping."
    )
    assert gate["level"] == "P0"
    assert any(
        assertion.get("mode") == "automated"
        and assertion.get("type") == "property_tests"
        and assertion.get("details", {}).get("test")
        == "tests/test_iam_t0_authority_closure.py::test_customer_invite_handles_existing_and_revoked_org_records"
        for assertion in gate["assertions"]
    )


def test_iam2_dependency_gates_match_the_candidate_and_keep_inheritance_floor() -> None:
    iam2, gates = _bundle_payloads("IAM-2")
    actual_dependency = next(
        dependency for dependency in iam2["dependencies"] if dependency["doc_id"] == "IAM-1"
    )
    gate_040 = next(gate for gate in gates["gates"] if gate["id"] == "IAM-2-GATE-040")
    gate_190 = next(gate for gate in gates["gates"] if gate["id"] == "IAM-2-GATE-190")

    def values(gate: dict, pointer: str) -> list[str]:
        return [
            assertion["details"]["equals"]
            for assertion in gate["assertions"]
            if assertion.get("details", {}).get("json_pointer") == pointer
        ]

    assert actual_dependency["min_version"] == "4.1.0"
    assert values(gate_040, "/dependencies/0/min_version") == ["4.1.0"]
    assert values(gate_190, "/dependencies/0/min_version") == ["4.1.0"]
    assert values(
        gate_190,
        "/security/enumeration_hardening/inherits_from/min_version",
    ) == ["3.4.0"]


def test_manifest_selected_iam1_has_executable_p0_capability_closure_gate() -> None:
    _, gates = _iam1()
    closure = next(
        gate
        for gate in gates["gates"]
        if gate["id"] == "IAM-1-GATE-T0-CAPABILITY-DEFINITION-CLOSURE"
    )

    assert closure["level"] == "P0"
    assert closure["must"] is True
    assert closure["enforced_by"] == "pytest"
    assert any(
        assertion.get("mode") == "automated"
        and assertion.get("type") == "property_tests"
        and assertion.get("details", {}).get("test")
        == "tests/test_iam_t0_authority_closure.py::test_manifest_selected_iam_defines_each_mapped_capability_once"
        for assertion in closure["assertions"]
    )
