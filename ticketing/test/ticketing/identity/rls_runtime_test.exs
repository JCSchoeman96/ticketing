defmodule Ticketing.Identity.RlsRuntimeTest do
  use Ticketing.DataCase, async: false

  alias Ecto.Adapters.SQL
  alias Ticketing.Identity.OwnerFixtures
  alias Ticketing.Platform.TenantContext

  @org_a "11111111-1111-4111-8111-111111111111"
  @org_b "22222222-2222-4222-8222-222222222222"
  @user_id "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  @membership_id "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

  setup do
    :ok = OwnerFixtures.reset_identity_tables!()

    OwnerFixtures.insert_user!(%{id: @user_id})

    OwnerFixtures.insert_org_membership!(%{
      org_membership_id: @membership_id,
      org_id: @org_a,
      user_id: @user_id
    })

    :ok
  end

  test "runtime role cannot read tenant membership rows without transaction-local org context" do
    assert %Postgrex.Result{rows: [[0]]} =
             runtime_query!(
               "SELECT count(*)::integer FROM public.identity_org_memberships",
               []
             )
  end

  test "runtime role hides membership rows under a mismatched tenant GUC" do
    assert {:error, {:visible_rows, 0}} =
             Ticketing.Repo.transaction(fn ->
               TenantContext.put_current_org!(@org_b)

               assert %Postgrex.Result{rows: [[visible_rows]]} =
                        runtime_query!(
                          """
                          SELECT count(*)::integer
                          FROM public.identity_org_memberships
                          WHERE user_id = $1::uuid
                          """,
                          [uuid!(@user_id)]
                        )

               Ticketing.Repo.rollback({:visible_rows, visible_rows})
             end)
  end

  test "runtime role reads membership only when transaction-local org context matches" do
    assert {:ok, 1} =
             Ticketing.Repo.transaction(fn ->
               TenantContext.put_current_org!(@org_a)

               assert %Postgrex.Result{rows: [[1]]} =
                        runtime_query!(
                          """
                          SELECT count(*)::integer
                          FROM public.identity_org_memberships
                          WHERE user_id = $1::uuid
                          """,
                          [uuid!(@user_id)]
                        )

               1
             end)
  end

  defp runtime_query!(query, params) do
    SQL.query!(Ticketing.Repo.get_dynamic_repo(), query, params)
  end

  defp uuid!(value), do: Ecto.UUID.dump!(value)
end
