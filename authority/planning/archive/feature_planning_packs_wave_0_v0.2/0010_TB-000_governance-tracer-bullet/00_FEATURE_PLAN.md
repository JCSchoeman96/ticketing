# Feature Planning Pack: FP-TB-000 — Governance Tracer Bullet


> Status: Draft implementation handoff pack.  
> Phase: Legislative Mode -> MVP-0 only.  
> Root namespace: `Ticketing`.  
> OTP app atom: `:ticketing`.  
> Ash posture: Ash 3.x only.  
> Product work: BLOCKED unless explicitly allowed by this pack.  
> Authority rule: contracts and gates win over this planning pack.


## 1. Identity

| Field | Value |
|---|---|
| `feature_pack_id` | `FP-TB-000-governance-tracer-bullet` |
| `source_row_ids` | `TB-000` |
| `classification` | `TB` |
| `FR_ref` | `FR-MVP0-TB-000` — NEW: proposed planning handle until FR-1 exists |
| `release_phase` | `foundation` |
| `mvp_blocker` | `yes` |
| `blocked_by` | `FP-MVP0-000-repo-airlock-scaffold` |
| `blocks` | `CI-001`, `CI-002`, all feature packs |

## 2. Goal

Prove the governance airlock path from Domain Map rows to generated artifacts, code metadata, Ash/Phoenix modules, Oban metadata, trace validation, CI gate, and evidence report.

TB-000 MUST NOT deliver product value.

## 3. Governing sources

| Source | Role |
|---|---|
| `TB-000_Governance_Tracer_Bullet_v1.0.md` | Primary proof specification |
| `V42_A_to_Z_Locked_Setup_and_Ultimate_Goal_v1.2.md` | MVP-0 boundary and first legal build sequence |
| `CANON-1` and `contracts/manifest.json` | Current membership, pins, paths, and hashes |
| `TEN-1` | Tenant isolation / `org_id` posture |
| `OBQC-1` | Oban queue and async boundary posture |
| `OBS-1` | Evidence, telemetry, and trace posture |
| `GOV-0`, `LINT-0`, `CS-0`, `BP-0` | Governance/schema/lint/blueprint authority |

## 4. Required modules

```elixir
Ticketing.System.HealthCheck
Ticketing.System.AirlockTrace
Ticketing.System.AirlockTraceWorker
```

## 5. Definitely required resources

| Resource/module | Kind | Tenant scope | Purpose |
|---|---|---|---|
| `Ticketing.System.HealthCheck` | runtime module | global_system | Proves skeleton/runtime traceability only. |
| `Ticketing.System.AirlockTrace` | Ash resource | tenant_isolated | Proves non-product tenant-aware Ash persistence and migration/table parity. |
| `Ticketing.System.AirlockTraceWorker` | Oban worker | explicit `org_id` in args | Proves async boundary traceability, correlation, and idempotency metadata. |

## 6. Proposed AirlockTrace fields

The TB-000 spec requires `org_id`; the remaining fields below are NEW: proposed implementation details and must be kept minimal.

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | UUIDv7 native Postgres `uuid` | yes | Primary key. |
| `org_id` | UUID native Postgres `uuid` | yes | Tenant key. |
| `trace_key` | string | yes | Diagnostic trace identifier, non-product. |
| `correlation_id` | string | yes | Trace/evidence correlation. |
| `idempotency_key` | string | yes | Used by create/action and worker proof. |
| `status` | atom/string enum | yes | `created`, `worker_completed`, `worker_failed` only. |
| `metadata` | map/jsonb | no | Must not contain PII or product identifiers. |
| `inserted_at` | `utc_datetime_usec` | yes | Audit/evidence time. |
| `updated_at` | `utc_datetime_usec` | yes | Diagnostic update time. |

## 7. Definitely required actions

| Action | Owner | Entry points | Forbidden entry points |
|---|---|---|---|
| `health_check.status` | `HealthCheck` | runtime call/test | product route finality |
| `airlock_trace.create` | `AirlockTrace` | Ash action, optional Oban worker | direct Repo in governed flow, LiveView business logic |
| `airlock_trace_worker.perform` | `AirlockTraceWorker` | Oban worker only | request-cycle retry, provider calls, product side effects |

## 8. Policies

- `AirlockTrace` MUST be tenant-isolated by `org_id`.
- `HealthCheck` MUST NOT require database migration.
- `AirlockTraceWorker` MUST carry `org_id`, `correlation_id`, and `idempotency_key` explicitly.
- Default deny where authorization is relevant.
- No public/customer-facing route is required.

## 9. DB constraints

```text
- AirlockTrace table has id UUID primary key.
- AirlockTrace table has org_id NOT NULL.
- Unique index on {org_id, idempotency_key}.
- Index on {org_id, inserted_at} or {org_id, id} for diagnostic traversal.
- No foreign keys to product tables.
- No partitioning unless explicitly approved later.
```

## 10. Idempotency

`airlock_trace.create` and `airlock_trace_worker.perform` MUST use deterministic idempotency evidence scoped by `org_id`.

Recommended key:

```text
tb000:<org_id>:<trace_key>:<operation>
```

## 11. Oban

| Worker | Queue | Required metadata |
|---|---|---|
| `Ticketing.System.AirlockTraceWorker` | `ops` | `org_id`, `correlation_id`, `idempotency_key`, `trace_key` |

The worker must not call providers or mutate product state.

## 12. Telemetry / evidence

Minimum evidence report must prove:

```text
Domain Map row exists
generated artifact includes TB-000 rows
code metadata references TB-000
HealthCheck compiles
AirlockTrace compiles
AirlockTrace has org_id tenant key
AirlockTrace migration/table parity passes
AirlockTraceWorker exists
worker args carry org_id, correlation_id, idempotency_key
trace validator passes
CI records pass/fail evidence
```

## 13. Acceptance tests

- HealthCheck returns `%{{status: :ok, app: :ticketing}}` or equivalent.
- HealthCheck has TB-000 trace metadata.
- HealthCheck has no migration.
- AirlockTrace declares tenant scope and `org_id`.
- AirlockTrace migration/table includes `org_id`.
- AirlockTrace is not named AuditLog and is not used as audit subsystem.
- Worker declares queue `:ops`.
- Worker requires `org_id`, `correlation_id`, `idempotency_key`.
- Product contracts/resources are not referenced by TB-000 modules.
- Direct Repo calls are absent except approved health/read-only infrastructure exception.

## 14. Must-have gates

Use the TB-000 gate list as the blocking gate set:

```text
TB000-001 through TB000-016
```

## 15. Non-goals

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
real AuditLog
product telemetry
customer-visible reporting
```

## 16. Definition of done

The pack is accepted only when:

```text
- TB-000 modules exist and compile.
- Domain Map rows exist.
- generated Domain Map artifact includes the rows.
- trace validator reports TB-000 evidence.
- tests prove no product scope was introduced.
- CI or local gate output includes TB000-001..TB000-016 status.
- evidence report is written under vault/Control or equivalent.
```
