defmodule Ticketing.Identity.LivenessNegativesTest do
  use Ticketing.DataCase, async: false

  alias Ticketing.Identity
  alias Ticketing.Identity.Actor
  alias Ticketing.Identity.OwnerFixtures

  @org_a "11111111-1111-4111-8111-111111111111"

  setup do
    :ok = OwnerFixtures.reset_identity_tables!()
    :ok
  end

  test "inactive, disabled, or deleted User fails liveness read" do
    for {attrs, label} <- [
          {%{status: "inactive"}, "inactive"},
          {%{disabled_at_utc: DateTime.utc_now()}, "disabled"},
          {%{deleted_at_utc: DateTime.utc_now()}, "deleted"}
        ] do
      user_id = Ecto.UUID.generate()
      OwnerFixtures.insert_user!(Map.put(attrs, :id, user_id))
      actor = Actor.authenticated(user_id)

      assert {:error, %Ash.Error.Invalid{errors: [%Ash.Error.Query.NotFound{} | _]}} =
               Identity.read_user_for_liveness(user_id, actor: actor, authorize?: true),
             "expected liveness failure for #{label} user"
    end
  end

  test "revoked or inactive OrgMembership fails membership probe" do
    for {attrs, label} <- [
          {%{status: "inactive"}, "inactive"},
          {%{revoked_at_utc: DateTime.utc_now()}, "revoked"}
        ] do
      user_id = Ecto.UUID.generate()
      membership_id = Ecto.UUID.generate()
      OwnerFixtures.insert_user!(%{id: user_id})
      actor = Actor.authenticated(user_id)

      OwnerFixtures.insert_org_membership!(
        Map.merge(
          %{
            org_membership_id: membership_id,
            org_id: @org_a,
            user_id: user_id
          },
          attrs
        )
      )

      assert {:error, %Ash.Error.Invalid{errors: [%Ash.Error.Query.NotFound{} | _]}} =
               Identity.probe_org_membership(user_id,
                 tenant: @org_a,
                 actor: actor,
                 authorize?: true
               ),
             "expected membership probe failure for #{label} membership"
    end
  end

  test "revoked, inactive, or expired Session fails liveness read" do
    user_id = Ecto.UUID.generate()
    OwnerFixtures.insert_user!(%{id: user_id})
    actor = Actor.authenticated(user_id)
    now = DateTime.utc_now()

    for {attrs, label} <- [
          {%{status: "inactive"}, "inactive"},
          {%{revoked_at_utc: now}, "revoked"},
          {%{expires_at_utc: DateTime.add(now, -60, :second)}, "expired"}
        ] do
      session_id = Ecto.UUID.generate()

      OwnerFixtures.insert_session!(
        Map.merge(
          %{
            id: session_id,
            org_id: @org_a,
            user_id: user_id
          },
          attrs
        )
      )

      assert {:error, %Ash.Error.Invalid{errors: [%Ash.Error.Query.NotFound{} | _]}} =
               Identity.read_session_for_liveness(session_id,
                 tenant: @org_a,
                 actor: actor,
                 authorize?: true
               ),
             "expected session liveness failure for #{label} session"
    end
  end

  test "revoked or inactive OrgRoleAssignment fails active role read" do
    for {attrs, label} <- [
          {%{status: "inactive"}, "inactive"},
          {%{revoked_at: DateTime.utc_now()}, "revoked"}
        ] do
      user_id = Ecto.UUID.generate()
      role_assignment_id = Ecto.UUID.generate()
      OwnerFixtures.insert_user!(%{id: user_id})
      actor = Actor.authenticated(user_id)

      OwnerFixtures.insert_org_role_assignment!(
        Map.merge(
          %{
            role_assignment_id: role_assignment_id,
            org_id: @org_a,
            user_id: user_id,
            role: "org_admin"
          },
          attrs
        )
      )

      assert {:error, %Ash.Error.Invalid{errors: [%Ash.Error.Query.NotFound{} | _]}} =
               Identity.read_active_role_assignment(user_id, "org_admin",
                 tenant: @org_a,
                 actor: actor,
                 authorize?: true
               ),
             "expected role read failure for #{label} assignment"
    end
  end
end
