# Feature Planning Pack: FP-CI-002 — Migration Safety Baseline


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
| `feature_pack_id` | `FP-CI-002-migration-safety-baseline` |
| `source_row_ids` | `CI-002` |
| `classification` | `CI` |
| `FR_ref` | `FR-MVP0-CI-002` — NEW: proposed planning handle until FR-1 exists |
| `release_phase` | `foundation` |
| `mvp_blocker` | `yes` |
| `blocked_by` | `FP-TB-000-governance-tracer-bullet` |
| `blocks` | all persisted tenant/domain resources |

## 2. Goal

Create the first migration-safety gate baseline before real persisted product resources are implemented.

This pack must make migration risk visible and fail closed on dangerous or tenant-unsafe migration patterns. It does not approve product migrations by itself.

## 3. Governing sources

| Source | Role |
|---|---|
| `V42-0` | Constitutional tenant/money/inventory correctness posture |
| `DMSC-1` | Deployment and migration safety authority |
| `CS-0` | Contract/gate schema posture |
| `LINT-0` | Static governance lint authority |
| `TEN-1` | Tenant key and RLS posture |
| `RP-0` | Ash 3.x resource-pattern posture |
| `DP-1` | Data plane/no-direct-Repo/RLS boundary posture, where available |

## 4. Required safety posture

Migration tooling MUST fail closed on:

```text
missing tenant key for tenant-owned resources
unsafe product migration without Feature Planning Pack reference
migration that mutates finance/inventory truth without explicit authority
raw SQL that disables RLS or constraints without approved waiver
drop/rename/destructive operations without explicit reviewed migration plan
partitioning claims without explicit partition policy
migration evidence missing from CI report
```

## 5. Definitely required resources

None. This is tooling/CI only.

## 6. Candidate modules / scripts

```text
mix ticketing.migrations.audit
Mix.Tasks.Ticketing.Migrations.Audit
tools/migrations/audit_migrations.exs
ci/migration_safety_check.sh
```

Recommended first implementation:

```elixir
Mix.Tasks.Ticketing.Migrations.Audit
```

or, if Mix task structure is not ready:

```text
tools/migrations/audit_migrations.exs
```

## 7. Definitely required actions

| Action | Purpose |
|---|---|
| `scan_migrations` | Read migration files deterministically. |
| `detect_destructive_operations` | Flag drop/rename/alter-danger patterns. |
| `detect_rls_disable` | Flag disabling RLS or unsafe session/user changes. |
| `detect_product_migration_without_pack_ref` | Require migration comments/metadata to cite a pack once product migrations begin. |
| `check_airlock_trace_migration` | Verify TB-000 AirlockTrace migration includes `org_id`. |
| `emit_report` | Produce machine-readable and human-readable report. |

## 8. DB / migrations

This pack should not create product migrations.

It may inspect the TB-000 AirlockTrace migration if already created.

## 9. Suggested migration metadata convention

NEW: proposed implementation detail.

Every non-framework migration should include a top comment like:

```elixir
# feature_pack: FP-TB-000-governance-tracer-bullet
# contracts: TB-000, TEN-1
# migration_class: diagnostic_non_product | tenant_resource | finance_sensitive | inventory_sensitive | governance_tooling
```

If this convention is not accepted yet, implement the scanner with a fail-closed warning mode first and list it as a governance decision required.

## 10. Tests

Minimum fixture tests:

- Safe non-product AirlockTrace migration with `org_id` passes.
- Migration missing pack reference fails or warns according to current enforcement mode.
- Migration disabling RLS fails.
- Migration dropping a table fails unless explicitly whitelisted in a test fixture.
- Migration creating tenant-owned table without `org_id` fails.
- Migration using raw SQL with dangerous terms fails.
- Empty/no migrations produces honest report, not fake pass.

## 11. Must-have gates

```text
CI002-001: migration audit tool exists
CI002-002: migration audit report is produced
CI002-003: destructive migration fixture fails
CI002-004: RLS-disable fixture fails
CI002-005: tenant table without org_id fixture fails
CI002-006: AirlockTrace migration includes org_id
CI002-007: product migration without pack reference fails or is explicitly reported as pending enforcement
CI002-008: migration gate is wired into CI or documented as a required local gate
```

## 12. Non-goals

- Do not build DMSC-1 fully.
- Do not build deployment orchestration.
- Do not build partition maintenance jobs.
- Do not create product resources.
- Do not create ledger/order/seat/payment migrations.
- Do not approve unsafe migrations through waivers silently.

## 13. Definition of done

```text
- Migration audit tool/script exists.
- Fixture tests prove unsafe migrations fail.
- AirlockTrace migration is checked if present.
- CI/local gate command exists.
- Report is emitted in a stable location.
- No product migrations/resources are introduced.
```
