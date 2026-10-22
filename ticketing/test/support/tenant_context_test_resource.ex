defmodule Ticketing.TenantContextTestResource do
  @moduledoc false

  use Ash.Resource,
    domain: Ticketing.TenantContextTestDomain,
    data_layer: AshPostgres.DataLayer

  postgres do
    repo Ticketing.Repo
    table "t0_01_tenant_context_fixture"
  end

  actions do
    read :read do
      primary? true
      transaction? true
    end

    read :read_without_transaction do
      transaction? false
    end
  end

  multitenancy do
    strategy :attribute
    attribute :org_id
    global? false
  end

  attributes do
    uuid_primary_key :id
    attribute :org_id, :uuid, allow_nil?: false, public?: true
    attribute :value, :integer, allow_nil?: false, public?: true
  end
end

defmodule Ticketing.TenantContextTestDomain do
  @moduledoc false

  use Ash.Domain,
    otp_app: :ticketing,
    validate_config_inclusion?: false

  resources do
    resource Ticketing.TenantContextTestResource
  end
end
