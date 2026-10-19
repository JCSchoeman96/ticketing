# TB-000 — Governance Tracer Bullet

> Historical proposal. This document does not set the current build order or block product work. Follow [the active roadmap](../planning/ROADMAP.md) and current canonical contracts. The proposed AirlockTrace resource, worker, and proof are not T0 prerequisites.

- **Document type:** MVP-0 governance tracer specification
- **Status:** Historical proposal, superseded as execution order
- **Scope:** Non-product airlock proof
- **Root module namespace:** `Ticketing`
- **OTP app atom:** `:ticketing`

---

## 1. Purpose

TB-000 is the **Governance Tracer Bullet** for MVP-0.

It exists to prove that the governance airlock works from source law to code evidence before any real product feature development starts.

TB-000 does **not** deliver product value. It proves the chain:

```text
Domain Map row
  -> generated YAML/JSON
  -> contract/reference metadata
  -> code trace metadata
  -> Ash/Phoenix module or runtime module
  -> trace validator
  -> CI gate
  -> evidence report
```

TB-000 MUST test stable interfaces and metadata contracts, not fragile product-shaped data structures.

---

## 2. Naming rule

Use:

```text
TB-000 — Governance Tracer Bullet
```

Do **not** call it:

```text
VS-000
```

Reason: `VS-*` means vertical product slice. TB-000 is an airlock proof, not a product slice.

---

## 3. Recommended tracer scope

TB-000 MUST be non-product, but it MUST NOT be trivial.

Recommended composite proof:

```elixir
Ticketing.System.HealthCheck
Ticketing.System.AirlockTrace
Ticketing.System.AirlockTraceWorker
```

### 3.1 `Ticketing.System.HealthCheck`

Proves:

```text
skeleton/runtime metadata
basic application visibility
non-product module traceability
```

It MUST NOT require a database migration.

### 3.2 `Ticketing.System.AirlockTrace`

Proves:

```text
Ash resource traceability
non-product persistence
org_id tenant key declaration
migration/table parity
Domain Map -> generated YAML/JSON -> code mapping
trace metadata validation
```

It is permanent, low-volume diagnostic infrastructure. It is **not** the real platform `AuditLog` and MUST NOT be promoted into the audit subsystem without a separate contract-backed dossier.

### 3.3 `Ticketing.System.AirlockTraceWorker`

Proves:

```text
Oban async boundary metadata
tenant carried explicitly in job args
correlation_id propagation
idempotency metadata
job-to-resource traceability
```

---

## 4. Forbidden tracer domains

TB-000 MUST NOT implement or simulate product behaviour involving:

```text
orders
payments
seats
tickets
refunds
payouts
scanner admission
ledger posting
tenant switching
dynamic pricing
```

---

## 5. Minimum code metadata

### 5.1 HealthCheck metadata

```elixir
defmodule Ticketing.System.HealthCheck do
  @moduledoc """
  TB-000 Governance Tracer Bullet runtime check.

  This module proves skeleton/runtime traceability only. It does not implement product behaviour.
  """

  @contract_refs ["TB-000"]
  @slice_refs ["TB-000"]
  @dossier_ref "Ticketing.System.HealthCheck"
  @governance_tracer_bullet true

  def status do
    %{status: :ok, app: :ticketing}
  end
end
```

### 5.2 AirlockTrace metadata

```elixir
defmodule Ticketing.System.AirlockTrace do
  @moduledoc """
  TB-000 non-product Ash resource used to prove governance airlock mechanics.

  This resource exists only to prove traceability, tenant schema parity, migration parity,
  and CI failure behaviour. It is not the platform audit log and MUST NOT be promoted into
  the real audit subsystem without a separate contract-backed dossier.
  """

  @contract_refs ["TB-000", "TEN-1"]
  @slice_refs ["TB-000"]
  @dossier_ref "Ticketing.System.AirlockTrace"
  @governance_tracer_bullet true
  @tenant_scope :tenant_isolated
  @tenant_key :org_id

  # Ash resource definition may be introduced during MVP-0 only.
end
```

### 5.3 AirlockTraceWorker metadata

```elixir
defmodule Ticketing.System.AirlockTraceWorker do
  @moduledoc """
  TB-000 non-product Oban worker used to prove async boundary traceability.

  This worker must carry org_id, correlation_id, and idempotency_key explicitly.
  It must not call providers, issue tickets, move money, reserve seats, or perform product work.
  """

  @contract_refs ["TB-000", "TEN-1", "OBQC-1", "OBS-1"]
  @slice_refs ["TB-000"]
  @dossier_ref "Ticketing.System.AirlockTraceWorker"
  @governance_tracer_bullet true
  @oban_queue :ops
  @idempotency_required true
end
```

---

## 6. TB-000 gates

```text
TB000-001: Domain Map contains Ticketing.System.HealthCheck row
TB000-002: generated YAML/JSON contains matching HealthCheck row
TB000-003: code module declares @governance_tracer_bullet true
TB000-004: @contract_refs resolve to TB-000 or approved roadmap reference
TB000-005: @slice_refs resolve to TB-000
TB000-006: no product contracts are referenced by TB-000
TB000-007: CI trace report includes TB-000 evidence
TB000-008: TB-000 HealthCheck has no database migration
TB000-009: TB-000 AirlockTrace has exactly one non-product migration/table if persistence is enabled
TB000-010: TB-000 AirlockTrace declares org_id tenant key and tenant_isolated scope
TB000-011: TB-000 AirlockTrace migration/table includes org_id
TB000-012: TB-000 AirlockTraceWorker declares Oban queue and idempotency metadata
TB000-013: TB-000 async proof carries org_id, correlation_id, and idempotency_key explicitly
TB000-014: TB-000 contains no direct Repo call except explicitly approved HealthCheck/read-only infrastructure exception
TB000-015: TB-000 contains no Phoenix context generator output claim
TB000-016: TB-000 AirlockTrace is not named AuditLog and is not treated as the real platform audit subsystem
```

---

## 7. Required Domain Map rows

`00_DOMAIN_MAP.md` MUST include explicit TB-000 rows for:

```text
Ticketing.System.HealthCheck
Ticketing.System.AirlockTrace
Ticketing.System.AirlockTraceWorker
```

### 7.1 Minimum Resource Ownership Matrix rows

```markdown
| resource | owner_domain | elixir_module | tenant_scope | tenant_key | tenant_strategy | rls_required | cross_tenant_allowed | source_of_truth | contract_refs | state_group | hot_path | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HealthCheck | system | Ticketing.System.HealthCheck | global_system | none | none | no | yes | system_runtime | TB-000 | none | no | active |
| AirlockTrace | system | Ticketing.System.AirlockTrace | tenant_isolated | org_id | ash_attribute | yes | no | postgres_ash_rls | TB-000, TEN-1 | none | no | active |
| AirlockTraceWorker | system | Ticketing.System.AirlockTraceWorker | tenant_isolated | org_id | explicit_job_arg | no | no | oban_job_metadata | TB-000, TEN-1, OBQC-1, OBS-1 | none | no | active |
```

### 7.2 Minimum Action Execution Matrix rows

```markdown
| action | owner_domain | resource | execution_layer | authority_store | advisory_accelerators | side_effect_boundary | realtime_boundary | optimistic_ui_allowed | optimistic_state_name | confirmation_event | failure_event | pubsub_topic | timeout_behavior | compensation_behavior | allowed_entrypoints | forbidden_entrypoints | contract_refs | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| airlock_trace.create | system | AirlockTrace | cold_write | postgres_ash_rls | none | oban_optional_airlock_worker | pubsub_ids_only | no | none | airlock_trace.created | airlock_trace.failed | system:airlock_trace | fail_fast | write_error_evidence | ash_action, oban_worker | direct_repo, liveview_business_logic | TB-000, TEN-1 | active |
| airlock_trace_worker.perform | system | AirlockTraceWorker | async_side_effect | postgres_ash_rls | none | oban_worker | pubsub_ids_only | no | none | airlock_trace.worker_completed | airlock_trace.worker_failed | system:airlock_trace | retry_by_oban | quarantine_or_fail_evidence | oban_worker | request_cycle_retry, liveview_business_logic | TB-000, OBQC-1, OBS-1 | active |
```

---

## 8. Lifecycle and retention

`Ticketing.System.AirlockTrace` is permanent low-volume diagnostic infrastructure.

It MUST:

```text
remain non-product
remain ops/diagnostic only
use a diagnostic org_id or governed diagnostic tenant
have a retention policy
have a pruning mechanism
never become the real AuditLog
never run on buyer checkout, scanning, payment, refund, payout, or inventory hot paths
```

Recommended retention:

```text
local/dev: 7 days
CI/staging: 14–30 days
production: 30–90 days configurable
```

---

## 9. MVP-0 relationship

TB-000 is required for MVP-0 exit.

MVP-0 exits only when TB-000 proves the airlock path and CI can fail closed on:

```text
missing contracts
stale generated outputs
missing traceability
tenant parity drift
product claims without contract/slice references
```

TB-000 does not approve product development by itself. Product vertical slices remain blocked until MVP-0 and VS-001 evidence pass.

---

## 10. One-line definition

TB-000 is the non-product governance tracer bullet that proves the platform can trace law -> generated architecture -> code metadata -> tenant-aware Ash persistence -> Oban async metadata -> CI evidence before any real ticketing feature is built.
