"""Paired OBQC-1 gates for standard and AshOban generated job arguments."""

import json
import re
from pathlib import Path


AUTHORITY_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = AUTHORITY_ROOT.parent
PROFILE_FIXTURE = AUTHORITY_ROOT / "tests/fixtures/ash_oban_0.10.3_build_trigger_signature.json"


def _installed_obqc_artifacts():
    manifest = json.loads((AUTHORITY_ROOT / "contracts/manifest.json").read_text())
    record = next(contract for contract in manifest["contracts"] if contract["doc_id"] == "OBQC-1")
    version = record["version"]
    extracted = AUTHORITY_ROOT / record["extracted_path"]
    contract = json.loads((extracted / f"OBQC-1_Contract_v{version}.json").read_text())
    gates = json.loads((extracted / f"OBQC-1_Test_Gates_v{version}.json").read_text())
    return version, contract, gates


def test_standard_oban_workers_keep_the_exact_versioned_wrapper():
    _, contract, _ = _installed_obqc_artifacts()
    standard = contract["job_versioning"]["standard_oban_worker"]

    assert standard["outer_shape"] == "%{version: integer | string, args: map}"
    assert standard["exact_outer_keys"] == ["version", "args"]
    assert standard["payload_path"] == "args"


def test_ashoban_workers_use_certified_framework_keys_and_nested_payload():
    _, contract, _ = _installed_obqc_artifacts()
    policy = contract["ash_oban_integration"]["ash_oban_generated_args"]
    trigger = policy["trigger_worker"]
    scheduled = policy["scheduled_action_worker"]

    assert policy["policy"] == "framework_aware_allowlist"
    assert trigger["required_framework_keys"] == [
        "primary_key",
        "metadata",
        "action_arguments",
        "tenant",
    ]
    assert trigger["optional_framework_keys"] == ["actor"]
    assert set(trigger["outer_key_allowlist"]) == {
        "primary_key",
        "metadata",
        "action_arguments",
        "tenant",
        "actor",
    }
    assert scheduled["required_framework_keys"] == ["action_arguments"]
    assert set(scheduled["outer_key_allowlist"]) == {
        "action_arguments",
        "tenant",
        "actor",
    }

    for worker in (trigger, scheduled):
        assert worker["ticketing_payload_path"] == "action_arguments.ticketing_payload"
        assert worker["ticketing_payload_shape"] == "%{version: integer | string, args: map}"
        assert worker["ticketing_controlled_input_location"] == "action_arguments.ticketing_payload.args"
        assert worker["arbitrary_extra_args_allowed"] is False

    assert policy["shared_rules"]["no_unlisted_top_level_keys"] is True
    assert contract["job_versioning"]["ash_oban_generated_worker"]["unknown_payload_version"] == "fail_closed"
    assert contract["job_versioning"]["ash_oban_generated_worker"]["compatibility_requirement"].startswith(
        "Current and immediately previous"
    )


def test_scheduler_control_jobs_are_the_only_payload_free_ashoban_exception():
    _, contract, _ = _installed_obqc_artifacts()
    scheduler = contract["ash_oban_integration"]["ash_oban_generated_args"]["scheduler_control_job"]

    assert scheduler["outer_key_allowlist"] == ["actor"]
    assert scheduler["ticketing_payload_required"] is False
    assert scheduler["ticketing_payload_allowed"] is False
    assert "MUST NOT perform a Ticketing domain mutation or external side effect" in scheduler["purpose"]
    assert "current and immediately previous" in scheduler["compatibility"]


def test_compatibility_uses_actual_prior_deployed_source_not_uninstalled_art_registry():
    _, contract, _ = _installed_obqc_artifacts()
    evidence = contract["job_versioning"]["compatibility_evidence"]

    assert evidence["previous_version_source"] == (
        "deployment_metadata:previous_deployed_source_commit:versioned_job_payload_fixtures"
    )
    assert "ART-0" not in evidence["description"]
    assert "release_registry" not in evidence["previous_version_source"]
    assert "immutable commit SHA" in evidence["description"]
    assert "no earlier worker deployment and no queued legacy jobs" in evidence["first_deployment"]
    assert evidence["unknown_version_behavior"] == "fail_closed"
    assert contract["planned_contracts"] == []


def test_tenant_payload_limits_actor_security_and_module_names_remain_locked():
    _, contract, _ = _installed_obqc_artifacts()
    policy = contract["ash_oban_integration"]["ash_oban_generated_args"]
    shared = policy["shared_rules"]
    capability = contract["ash_oban_integration"]["ash_oban_capabilities"]
    versioning = contract["job_versioning"]

    assert "MUST match or the job MUST fail closed" in shared["framework_key_values"]["tenant"]
    assert "complete persisted Oban job args map" in shared["size_accounting"]
    assert contract["payload_strategy"]["max_args_bytes"] == 8192
    assert contract["payload_strategy"]["recommended_default_max_args_bytes"] == 2048
    assert "raw PII" in shared["security"]
    assert "bearer tokens" in shared["security"]
    assert "full permission snapshots" in shared["security"]
    assert "AUTH-030" in shared["framework_key_values"]["actor"]
    assert ":none" in shared["framework_key_values"]["actor"]
    assert policy["capability_verification"]["required"] is True
    assert capability["supports_triggers"] is True
    assert capability["supports_scheduled_actions"] is True
    assert capability["supports_module_name_verifier"] is True
    signatures = {
        (signature["module"], signature["function"], signature["arity"])
        for signature in capability["capability_signatures"]
    }
    assert ("AshOban", "trigger", 2) in signatures
    assert ("AshOban", "scheduled_action", 2) in signatures
    assert ("AshOban", "build_trigger", 3) in signatures
    assert "worker_module_name and scheduler_module_name" in " ".join(capability["notes"])
    assert versioning["compatibility_evidence"]["requires_compat_test_task"] == "obqc1.verify_job_versioning"


def test_ashoban_0103_source_signature_is_pinned_and_future_dependency_drift_fails():
    _, contract, _ = _installed_obqc_artifacts()
    fixture = json.loads(PROFILE_FIXTURE.read_text())
    profile = contract["ash_oban_integration"]["ash_oban_generated_args"]["capability_profile"]
    observed = fixture["observed_behavior"]

    assert profile["version"] == fixture["profile_id"].split("@", 1)[1]
    assert profile["tag_commit"] == fixture["upstream"]["tag_commit"]
    assert profile["build_trigger_source_sha256"] == fixture["upstream"]["source_file_sha256"]
    assert profile["generated_worker_source_files"] == fixture["upstream"]["generated_worker_source_files"]
    assert observed["trigger_worker_framework_keys"] == contract[
        "ash_oban_integration"
    ]["ash_oban_generated_args"]["trigger_worker"]["required_framework_keys"]
    assert observed["reserved_keys"] == ["primary_key", "metadata", "action_arguments", "tenant", "actor"]
    assert "Reserved keys are removed" in observed["extra_args_behavior"]
    assert observed["run_trigger"].startswith("AshOban.run_trigger/3 calls AshOban.build_trigger/3")

    app_manifest = (REPOSITORY_ROOT / "ticketing/mix.exs").read_text()
    app_lock = (REPOSITORY_ROOT / "ticketing/mix.lock").read_text()
    declared = re.search(r"\{:ash_oban,\s*\"([^\"]+)\"", app_manifest)
    locked = re.search(r'"ash_oban": \{:hex, :ash_oban, "([^"]+)"', app_lock)
    if declared:
        assert locked, "AshOban dependency must have a reproducible Hex lock entry"
        assert locked.group(1) == profile["version"], (
            "A new AshOban version requires an explicitly reviewed capability profile and authority gate"
        )
    else:
        assert not locked, "AshOban lock entry without a declared dependency is not an accepted baseline"


def test_paired_gate_requires_job_envelope_and_generated_worker_drift_checks():
    version, contract, gates = _installed_obqc_artifacts()
    assert gates["contract_ref"] == {"doc_id": "OBQC-1", "version": version}
    gate = next(item for item in gates["gates"] if item["id"] == "OBQC1-JOB-ARGS-001")
    assertion = gate["assertions"][0]

    assert assertion["mode"] == "automated"
    assert assertion["type"] == "property_tests"
    assert assertion["details"]["contract_pointer"] == "/job_versioning"
    assert assertion["details"]["ashoban_policy_pointer"] == "/ash_oban_integration/ash_oban_generated_args"
    assert assertion["details"]["upstream_profile_fixture"] == str(
        PROFILE_FIXTURE.relative_to(REPOSITORY_ROOT)
    )
    assert contract["version"] == version
