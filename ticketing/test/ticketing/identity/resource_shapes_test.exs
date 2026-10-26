defmodule Ticketing.Identity.ResourceShapesTest do
  use ExUnit.Case, async: true

  alias Ash.Resource.Info
  alias Ticketing.Identity.OrgMembership
  alias Ticketing.Identity.OrgRoleAssignment
  alias Ticketing.Identity.Session
  alias Ticketing.Identity.User

  @nullable_user_fields ~w(verified_at_utc disabled_at_utc deleted_at_utc)a
  @nullable_membership_fields ~w(revoked_at_utc revocation_reason)a
  @nullable_session_fields ~w(revoked_at_utc last_seen_at_utc)a
  @nullable_role_fields ~w(granted_by_user_id revoked_at)a

  test "User exposes IAM-1 global attributes and nullability" do
    assert Info.multitenancy_attribute(User) == nil

    assert Info.attribute(User, :id)

    for name <- ~w(status created_at_utc)a do
      refute Info.attribute(User, name).allow_nil?
    end

    for name <- @nullable_user_fields do
      assert Info.attribute(User, name).allow_nil?
    end

    assert Info.primary_key(User) == [:id]
    assert Info.relationship(User, :org_memberships)
    assert Info.relationship(User, :sessions)
    assert Info.relationship(User, :org_role_assignments)
  end

  test "OrgMembership exposes IAM-1 identities and tenant attributes" do
    assert Info.multitenancy_attribute(OrgMembership) == :org_id
    assert Info.primary_key(OrgMembership) == [:org_membership_id]

    identity_fields =
      Info.identities(OrgMembership)
      |> Enum.map(fn identity -> {identity.name, identity.keys} end)
      |> Map.new()

    assert identity_fields.unique_user_per_org == [:org_id, :user_id]
    assert identity_fields.unique_membership_id_per_org == [:org_id, :org_membership_id]

    for name <- ~w(org_id org_membership_id user_id status created_at_utc)a do
      refute Info.attribute(OrgMembership, name).allow_nil?
    end

    for name <- @nullable_membership_fields do
      assert Info.attribute(OrgMembership, name).allow_nil?
    end

    assert Info.relationship(OrgMembership, :user)
  end

  test "Session exposes IAM-1 attributes, tenant identity, and private token_hash" do
    assert Info.multitenancy_attribute(Session) == :org_id
    assert Info.primary_key(Session) == [:id]

    identity_fields =
      Info.identities(Session)
      |> Enum.map(fn identity -> {identity.name, identity.keys} end)
      |> Map.new()

    assert identity_fields.unique_id_per_org == [:org_id, :id]

    refute Info.attribute(Session, :token_hash).public?

    for name <-
          ~w(id org_id user_id token_hash status created_at_utc expires_at_utc)a do
      refute Info.attribute(Session, name).allow_nil?
    end

    for name <- @nullable_session_fields do
      assert Info.attribute(Session, name).allow_nil?
    end
  end

  test "OrgRoleAssignment exposes IAM-1 identity and attributes" do
    assert Info.multitenancy_attribute(OrgRoleAssignment) == :org_id
    assert Info.primary_key(OrgRoleAssignment) == [:role_assignment_id]

    identity_fields =
      Info.identities(OrgRoleAssignment)
      |> Enum.map(fn identity -> {identity.name, identity.keys} end)
      |> Map.new()

    assert identity_fields.by_user_role_org == [:user_id, :role, :org_id]

    for name <- ~w(role_assignment_id org_id user_id role status granted_at)a do
      refute Info.attribute(OrgRoleAssignment, name).allow_nil?
    end

    for name <- @nullable_role_fields do
      assert Info.attribute(OrgRoleAssignment, name).allow_nil?
    end
  end
end
