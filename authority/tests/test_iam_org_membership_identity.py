from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _iam_contract() -> dict:
    path = next((ROOT / "contracts" / "IAM-1" / "extracted").glob("*Contract*.json"))
    return json.loads(path.read_text(encoding="utf-8"))


def test_auth_context_membership_id_is_defined_by_org_membership_resource() -> None:
    iam = _iam_contract()

    assert iam["authorization_model"]["auth_context_shape"]["actor"]["org_membership_id"] == "uuid_v7|nil"

    membership = next(
        resource for resource in iam["data_model"]["resources"] if resource["name"] == "OrgMembership"
    )
    attributes = {attribute["name"]: attribute for attribute in membership["attributes"]}

    assert attributes["org_membership_id"]["type"] == "uuid_v7"

    identity_fields = {tuple(identity["fields"]) for identity in membership.get("identities", [])}
    assert ("org_id", "org_membership_id") in identity_fields
    assert ("org_id", "user_id") in identity_fields
