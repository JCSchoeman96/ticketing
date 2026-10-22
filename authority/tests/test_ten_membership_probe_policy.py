from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = "/tenancy/tenant_resolution/system_internal_membership_probe"
EXPECTED_PROBE = {'enabled': True,
 'policy_id': 'org_membership_probe',
 'caller_boundary': 'system_internal_only',
 'public_clients_allowed': False,
 'requires_authenticated_human': True,
 'authoritative_user_id_required': True,
 'candidate_org_authoritative_before_proof': False,
 'preproof_candidate_scope_allowed': True,
 'transaction_local_required': True,
 'same_backend_transaction_required': True,
 'constrained_runtime_role_required': True,
 'force_rls_required': True,
 'superuser_forbidden': True,
 'bypassrls_forbidden': True,
 'table_owner_execution_forbidden': True,
 'allowed_resource': 'IAM-1.OrgMembership',
 'allowed_operation': 'read_membership_proof',
 'read_only': True,
 'membership_match_fields': ['org_id', 'user_id'],
 'active_membership_required': True,
 'role_lookup_before_proof_allowed': False,
 'other_tenant_resource_access_before_proof_allowed': False,
 'writes_allowed': False,
 'event_capability_authorization_allowed': False,
 'persona_promotion_on_failure_allowed': False,
 'session_promotion_on_failure_allowed': False,
 'persist_candidate_org_on_failure_allowed': False,
 'hide_existence_on_failure_required': True,
 'org_membership_id_is_proof_output': True,
 'role_resolution_after_success_allowed': True,
 'notes': ["Candidate org scope exists only to prove the already-authenticated human's "
           "active membership and is not the human's resolved tenant or active "
           'persona.',
           'Successful membership proof permits downstream IAM-1 '
           'organization-persona/session establishment; the probe itself grants no '
           'role or tenant capability.',
           'Failure discards candidate scope and MUST preserve TEN-1 hide-existence '
           'behavior.']}


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



def test_selected_ten1_defines_system_internal_membership_probe_policy() -> None:
    contract, _ = _bundle_payloads("TEN-1")
    resolution = contract["tenancy"]["tenant_resolution"]
    assert "system_internal_membership_probe" in resolution
    assert resolution["system_internal_membership_probe"] == EXPECTED_PROBE
    assert resolution["membership_validation"]["required"] is True
    assert resolution["membership_validation"]["enforced_before_setting_tenant"] is True


def test_selected_ten1_gate_145_locks_probe_and_preserves_gate_140() -> None:
    _, payload = _bundle_payloads("TEN-1")
    for gate_id in ("TEN-1-GATE-140", "TEN-1-GATE-145"):
        matches = [gate for gate in payload["gates"] if gate["id"] == gate_id]
        assert len(matches) == 1, f"Expected exactly one {gate_id}"
        gate = matches[0]
        assert gate["level"] == "P0"
        assert gate["must"] is True
        assertions = [
            assertion["details"]
            for assertion in gate["assertions"]
            if assertion["type"] == "json_pointer_equals"
            and assertion["mode"] == "automated"
            and assertion["details"]["artifact_kind"] == "contract"
        ]
        locks = {item["json_pointer"]: item["equals"] for item in assertions}
        assert len(locks) == len(assertions), "Duplicate pointer locks"
        expected = {
            "/tenancy/tenant_resolution/membership_validation/required": True,
            "/tenancy/tenant_resolution/membership_validation/enforced_before_setting_tenant": True,
        }
        if gate_id == "TEN-1-GATE-145":
            expected.update({
                f"{PROBE_PATH}/{key}": value
                for key, value in EXPECTED_PROBE.items()
                if not isinstance(value, list)
            })
        for pointer, value in expected.items():
            assert pointer in locks
            assert type(locks[pointer]) is type(value)
            assert locks[pointer] == value


def test_org_membership_remains_tenant_scoped_not_global() -> None:
    contract, _ = _bundle_payloads("TEN-1")
    assert "IAM-1.OrgMembership" not in contract["tenancy"]["global_resources"]["allowed_resources"]
