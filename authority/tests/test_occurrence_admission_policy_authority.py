from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def selected_contract(doc_id: str) -> dict:
    manifest = json.loads((ROOT / "contracts" / "manifest.json").read_text())
    record = next(row for row in manifest["contracts"] if row["doc_id"] == doc_id)
    with zipfile.ZipFile(ROOT / record["zip_path"]) as archive:
        contracts = [
            json.loads(archive.read(path))
            for path in archive.namelist()
            if path.endswith(".json")
            and json.loads(archive.read(path)).get("artifact_kind") == "contract"
        ]
    assert len(contracts) == 1
    assert contracts[0]["version"] == record["version"]
    return contracts[0]


def test_occurrence_admission_policy_is_a_zero_or_one_org_singleton() -> None:
    evt = selected_contract("EVT-2")
    policy = evt["invariants"]["occurrence_admission_policy"]
    resource = next(
        row
        for row in evt["data_model"]["resources"]
        if row["name"] == "OccurrenceAdmissionPolicy"
    )
    attributes = {row["name"]: row for row in resource["attributes"]}

    assert policy["tenant_key"] == "org_id"
    assert policy["cardinality"] == "zero_or_one_per_org"
    assert policy["identity"] == ["org_id"]
    assert policy["implicit_platform_default"] is False
    assert set(attributes) == {
        "org_id",
        "max_check_in_early_seconds",
        "max_check_in_late_seconds",
    }
    assert attributes["org_id"]["type"] == "uuid_v7"
    for name in ("max_check_in_early_seconds", "max_check_in_late_seconds"):
        assert attributes[name]["type"] == "integer"
        assert attributes[name]["required"] is True
        assert attributes[name]["constraints"]["min"] == 0
        assert "max" not in attributes[name]["constraints"]
        assert "default" not in attributes[name]
        assert policy["required_values"][name] == {
            "minimum": 0,
            "type": "integer",
            "zero_valid": True,
        }
    assert "status" not in attributes


def test_occurrence_creation_resolves_and_enforces_same_tenant_policy() -> None:
    evt = selected_contract("EVT-2")
    action = evt["domain_actions"]["create_occurrence"]
    policy = evt["invariants"]["occurrence_admission_policy"]

    assert action["admission_policy_resolution"] == {
        "resource": "OccurrenceAdmissionPolicy",
        "tenant_key": "org_id",
        "resolution": "inside_the_same_governed_create_transaction",
        "caller_supplied_policy_override_allowed": False,
        "missing_policy": {
            "behavior": "fail_closed",
            "code": "ERR_PRECONDITION",
            "subcode": "EVT_ADMISSION_POLICY_MISSING",
        },
    }
    assert not any(
        name in action["inputs_required"]
        for name in (
            "policy",
            "policy_id",
            "max_check_in_early_seconds",
            "max_check_in_late_seconds",
        )
    )
    assert action["creation_field_sources"]["check_in_open_at_utc"] == "explicit input"
    assert action["creation_field_sources"]["check_in_close_at_utc"] == "explicit input"
    assert action["errors"] == ["ERR_PRECONDITION", "ERR_VALIDATION"]
    assert policy["check_in_window_bounds"] == [
        "check_in_open_at_utc <= check_in_close_at_utc",
        "check_in_open_at_utc >= starts_at_utc - max_check_in_early_seconds",
        "check_in_close_at_utc <= ends_at_utc + max_check_in_late_seconds",
    ]
    assert policy["out_of_policy_window_error"] == {
        "code": "ERR_VALIDATION",
        "subcode": "EVT_CHECK_IN_WINDOW_OUT_OF_POLICY",
    }
    transition = evt["state_lifecycle"]["Occurrence.sales"]["transitions"][0]
    assert any("OccurrenceAdmissionPolicy" in guard for guard in transition["guards"])
    assert "EVT_ADMISSION_POLICY_MISSING" in transition["invalid_behavior"]
    assert "EVT_CHECK_IN_WINDOW_OUT_OF_POLICY" in transition["invalid_behavior"]


def test_policy_management_is_prospective_and_uses_owner_admin_capability() -> None:
    evt = selected_contract("EVT-2")
    iam = selected_contract("IAM-1")
    action = evt["domain_actions"]["set_occurrence_admission_policy"]
    capability = "evt.occurrence.admission_policy.manage"
    action_map = iam["approved_authority_corrections"]["capability_action_map"]
    definitions = [
        row
        for row in iam["authorization_model"]["capability_definitions"]
        if row["capability"] == capability
    ]
    policy = evt["invariants"]["occurrence_admission_policy"]

    assert action_map[capability] == "EVT-2.set_occurrence_admission_policy"
    assert len(definitions) == 1
    assert definitions[0]["allowed_actor_kinds"] == ["human"]
    assert set(definitions[0]["allowed_roles"]) == {"org_owner", "org_admin"}
    assert {
        "org_id",
        "max_check_in_early_seconds",
        "max_check_in_late_seconds",
    } <= set(action["inputs_required"])
    assert action["authorization_capability"] == capability
    assert action["policy_write"] == "create_if_absent_or_replace_existing_for_same_org"
    assert action["error_mappings"] == [
        {
            "code": "ERR_VALIDATION",
            "condition": (
                "Either max_check_in_early_seconds or max_check_in_late_seconds is "
                "not an integer greater than or equal to zero."
            ),
            "subcode": "EVT_ADMISSION_POLICY_INVALID",
        }
    ]
    assert policy["changes_apply_prospectively"] is True
    assert policy["existing_occurrence_windows"] == (
        "remain_unchanged_and_continue_to_govern_admission_decisions"
    )


def test_policy_presence_lifecycle_is_explicit_and_bounded() -> None:
    evt = selected_contract("EVT-2")
    lifecycle = evt["state_lifecycle"]["OccurrenceAdmissionPolicy"]
    transitions = lifecycle["transitions"]

    assert lifecycle["origin"] == "absent"
    assert lifecycle["states"] == ["configured"]
    assert lifecycle["terminal_states"] == []
    assert len(transitions) == 2
    assert [(row["from"], row["to"]) for row in transitions] == [
        ("absent", "configured"),
        ("configured", "configured"),
    ]
    assert {row["action"] for row in transitions} == {
        "set_occurrence_admission_policy"
    }

    expected_initiator = {
        "actor_kind": "human",
        "authorization_contract": "IAM-1",
        "capability": "evt.occurrence.admission_policy.manage",
        "allowed_roles": ["org_owner", "org_admin"],
    }
    expected_invalid_behavior = (
        "Authorization failure follows canonical IAM-1/ERR-1 semantics. "
        "Invalid policy values return ERR_VALIDATION / EVT_ADMISSION_POLICY_INVALID. "
        "No partial policy write."
    )
    for transition in transitions:
        assert transition["initiator"] == expected_initiator
        assert transition["action"] == "set_occurrence_admission_policy"
        assert transition["terminal"] is False
        assert transition["invalid_behavior"] == expected_invalid_behavior

    assert transitions[0]["guards"] == [
        "authenticated active organization tenant context",
        "explicit org_id matches that tenant",
        "no same-tenant OccurrenceAdmissionPolicy currently exists",
        "both policy values are integers greater than or equal to zero",
    ]
    assert transitions[0]["side_effects"] == (
        "Persist exactly one same-tenant OccurrenceAdmissionPolicy for org_id "
        "with the supplied early and late values."
    )
    assert transitions[1]["guards"] == [
        "authenticated active organization tenant context",
        "explicit org_id matches that tenant",
        "a same-tenant OccurrenceAdmissionPolicy exists",
        "both replacement values are integers greater than or equal to zero",
    ]
    assert transitions[1]["side_effects"] == (
        "Atomically replace the configured early and late values for that same "
        "organization as one governed policy mutation. Do not mutate or recompute "
        "existing Occurrence check-in windows."
    )


def test_negative_policy_values_are_invalid_and_zero_remains_valid() -> None:
    evt = selected_contract("EVT-2")
    action = evt["domain_actions"]["set_occurrence_admission_policy"]
    attributes = next(
        row
        for row in evt["data_model"]["resources"]
        if row["name"] == "OccurrenceAdmissionPolicy"
    )["attributes"]
    constraints = {
        row["name"]: row["constraints"]
        for row in attributes
        if row["name"] in {"max_check_in_early_seconds", "max_check_in_late_seconds"}
    }

    for field in ("max_check_in_early_seconds", "max_check_in_late_seconds"):
        assert constraints[field] == {"min": 0}
        assert evt["invariants"]["occurrence_admission_policy"]["required_values"][
            field
        ]["zero_valid"] is True

    assert action["error_mappings"] == [
        {
            "code": "ERR_VALIDATION",
            "condition": (
                "Either max_check_in_early_seconds or max_check_in_late_seconds is "
                "not an integer greater than or equal to zero."
            ),
            "subcode": "EVT_ADMISSION_POLICY_INVALID",
        }
    ]


def test_occurrence_admission_errors_and_observability_operation_are_registered() -> None:
    evt = selected_contract("EVT-2")
    err = selected_contract("ERR-1")
    subcodes = {
        row["subcode"]: row["top_level"] for row in err["registry"]["subcodes"]
    }

    assert subcodes["EVT_ADMISSION_POLICY_MISSING"] == "ERR_PRECONDITION"
    assert subcodes["EVT_CHECK_IN_WINDOW_OUT_OF_POLICY"] == "ERR_VALIDATION"
    assert subcodes["EVT_ADMISSION_POLICY_INVALID"] == "ERR_VALIDATION"
    assert sum(
        row["subcode"] == "EVT_ADMISSION_POLICY_INVALID"
        for row in err["registry"]["subcodes"]
    ) == 1


def test_evt_subcode_floor_tracks_occurrence_admission_errors() -> None:
    evt = selected_contract("EVT-2")
    err = selected_contract("ERR-1")
    floor = err["registry"]["domain_subcode_floors"]["EVT-2"]
    evt_subcodes = [
        row["subcode"]
        for row in err["registry"]["subcodes"]
        if row["subcode"].startswith("EVT_")
    ]

    assert floor == {
        "min_version": evt["version"],
        "subcode_count": len(evt_subcodes),
        "subcode_prefix": "EVT_",
    }
    assert {
        "EVT_ADMISSION_POLICY_INVALID",
        "EVT_ADMISSION_POLICY_MISSING",
        "EVT_CHECK_IN_WINDOW_OUT_OF_POLICY",
    } <= set(evt_subcodes)


def test_occurrence_admission_policy_operation_is_registered_in_obs() -> None:
    evt = selected_contract("EVT-2")
    obs = selected_contract("OBS-1")
    action_id = "set_occurrence_admission_policy"
    operation = f"EVT-2.{action_id}"

    assert action_id in evt["domain_actions"]
    assert obs["operation_registry"][operation] == {
        "operation_id": operation,
        "contract_id": "EVT-2",
        "action_id": action_id,
    }
    assert operation in obs["operation_id_binding"]["t0_operation_ids"]
