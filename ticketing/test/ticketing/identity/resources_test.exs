defmodule Ticketing.Identity.ResourcesTest do
  use Ticketing.DataCase, async: false

  alias Ash.Resource.Info
  alias Ticketing.Identity
  alias Ticketing.Identity.Actor
  alias Ticketing.Identity.OrgMembership
  alias Ticketing.Identity.OrgRoleAssignment
  alias Ticketing.Identity.OwnerFixtures
  alias Ticketing.Identity.Session
  alias Ticketing.Identity.User

  @org_a "11111111-1111-4111-8111-111111111111"
  @org_b "22222222-2222-4222-8222-222222222222"
  @user_id "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  @other_user_id "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
  @membership_id "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
  @session_id "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
  @role_assignment_id "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"

  setup do
    :ok = OwnerFixtures.reset_identity_tables!()
    actor = Actor.authenticated(@user_id)

    OwnerFixtures.insert_user!(%{id: @user_id})
    OwnerFixtures.insert_user!(%{id: @other_user_id})

    OwnerFixtures.insert_org_membership!(%{
      org_membership_id: @membership_id,
      org_id: @org_a,
      user_id: @user_id
    })

    OwnerFixtures.insert_org_membership!(%{
      org_membership_id: Ash.UUIDv7.generate(),
      org_id: @org_b,
      user_id: @other_user_id
    })

    OwnerFixtures.insert_session!(%{
      id: @session_id,
      org_id: @org_a,
      user_id: @user_id,
      token_hash: "super-secret-hash"
    })

    OwnerFixtures.insert_org_role_assignment!(%{
      role_assignment_id: @role_assignment_id,
      org_id: @org_a,
      user_id: @user_id,
      role: "org_admin"
    })

    %{actor: actor}
  end

  test "User is global and exposes canonical liveness fields", %{actor: actor} do
    assert {:ok, user} =
             Identity.read_user_for_liveness(@user_id, actor: actor, authorize?: true)

    assert user.id == @user_id
    assert user.status == "active"
    assert %DateTime{} = user.created_at_utc
  end

  test "membership probe returns active membership for matching user in tenant context", %{
    actor: actor
  } do
    assert {:ok, membership} =
             Identity.probe_org_membership(@user_id,
               tenant: @org_a,
               actor: actor,
               authorize?: true
             )

    assert membership.org_membership_id == @membership_id
    assert membership.org_id == @org_a
    assert membership.user_id == @user_id
    assert membership.status == "active"
    assert is_nil(membership.revoked_at_utc)
  end

  test "membership probe hides other-tenant membership under cross-tenant context", %{
    actor: actor
  } do
    assert {:error, %Ash.Error.Invalid{errors: [%Ash.Error.Query.NotFound{} | _]}} =
             Identity.probe_org_membership(@user_id,
               tenant: @org_b,
               actor: actor,
               authorize?: true
             )
  end

  test "membership probe rejects mismatched actor user_id", %{actor: _actor} do
    other_actor = Actor.authenticated(@other_user_id)

    assert {:error, %Ash.Error.Invalid{errors: [%Ash.Error.Query.NotFound{} | _]}} =
             Identity.probe_org_membership(@user_id,
               tenant: @org_a,
               actor: other_actor,
               authorize?: true
             )
  end

  test "Session read is read-only and omits token_hash from governed results", %{actor: actor} do
    session_actions = Info.actions(Session) |> Enum.map(& &1.name)
    refute :create in session_actions
    refute :update in session_actions
    refute :destroy in session_actions

    assert {:ok, session} =
             Identity.read_session_for_liveness(@session_id,
               tenant: @org_a,
               actor: actor,
               authorize?: true
             )

    assert session.id == @session_id
    assert session.user_id == @user_id
    assert match?(%Ash.NotLoaded{}, Map.get(session, :token_hash))
  end

  test "active role assignment read returns persisted role", %{actor: actor} do
    assert {:ok, assignment} =
             Identity.read_active_role_assignment(@user_id, "org_admin",
               tenant: @org_a,
               actor: actor,
               authorize?: true
             )

    assert assignment.role_assignment_id == @role_assignment_id
    assert assignment.role == "org_admin"
    assert assignment.status == "active"
    assert is_nil(assignment.revoked_at)
  end

  test "tenant resources use attribute multitenancy on org_id" do
    assert Info.multitenancy_attribute(OrgMembership) == :org_id
    assert Info.multitenancy_attribute(Session) == :org_id
    assert Info.multitenancy_attribute(OrgRoleAssignment) == :org_id
    refute Info.multitenancy_attribute(User)
  end
end
