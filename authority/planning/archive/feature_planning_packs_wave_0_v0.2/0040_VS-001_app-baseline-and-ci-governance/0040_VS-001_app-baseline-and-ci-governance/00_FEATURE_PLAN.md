# Feature Planning Pack: FP-VS-001 — App Baseline and CI Governance

> Status: Draft implementation handoff pack.  
> Phase: Legislative Mode -> MVP-0 foundation proof only.  
> Root namespace: `Ticketing`.  
> OTP app atom: `:ticketing`.  
> Ash posture: Ash 3.x only.  
> Product work: BLOCKED unless explicitly allowed by this pack.  
> Authority rule: contracts and gates win over this planning pack.

## 1. Identity

| Field | Value |
|---|---|
| `feature_pack_id` | `FP-VS-001-app-baseline-and-ci-governance` |
| `source_row_ids` | `VS-001` |
| `classification` | `VS` |
| `FR_ref` | `FR-MVP0-VS-001` — NEW: proposed planning handle until FR-1 exists |
| `release_phase` | `foundation` |
| `mvp_blocker` | `yes` |
| `ordered_folder` | `0040_VS-001_app-baseline-and-ci-governance` |
| `blocked_by` | `FP-MVP0-000-repo-airlock-scaffold`, `FP-TB-000-governance-tracer-bullet`, `FP-CI-001-deterministic-uuid-binary-sort`, `FP-CI-002-migration-safety-baseline` |
| `blocks` | `FP-TB-001-tenant-context-rls-denial`, `FP-TB-038-cross-tenant-red-team-test`, identity/org/audit/error foundation packs |

## 2. Goal

Establish the first **coding-safe app and CI governance baseline** for the `Ticketing` Phoenix/Ash repository.

This pack proves that the project can compile, run tests, execute governance checks, emit baseline evidence, and fail closed when required governance gates are missing or stale.

This pack MUST NOT implement product features. It prepares the repository and CI spine so later TB/VS packs can land safely.

## 3. Governing sources

| Source | Role in this pack |
|---|---|
| `V42-0` | Constitutional fail-closed, tenancy, reliability, and no-drift posture. |
| `CS-0` | Contract-suite schema posture and artifact-family expectations. |
| `BP-0` | Bundle/authoring blueprint and law/proof/integrity discipline. |
| `GOV-0` | Ash 3.x governance and project-canon posture. |
| `LINT-0` | Static governance lint authority. |
| `TG-0` | Test-gate severity and gate authoring taxonomy. |
| `CG-0` | CI contract-gate enforcement expectations. |
| `QA-0` | Repository QA, ExUnit, `mix check`, and regression-prevention posture. |
| `ATP-1` | Governance anti-pattern scanner posture. |
| `DMSC-1` | Migration safety baseline and deployment-change caution. |
| `TEN-1` | Tenant isolation posture that downstream resources must obey. |
| `ERR-1` | Error-envelope posture for CI/tooling failure reports and future boundary errors. |
| `OBS-1` | Evidence, telemetry, and release-blocking observability posture. |
| `RP-0` | Ash 3.x resource-pattern posture for later resources. |
| `DP-1` | Data-plane/no-direct-Repo/RLS boundary posture where available. |

## 4. Scope

This pack MAY implement or verify:

```text
Phoenix/Ash project baseline
Ticketing root namespace
:ticketing OTP app atom
basic Repo configuration
basic test harness
mix aliases for compile/test/check
static governance lint wiring
contract gate script wiring or documented invocation
migration safety gate wiring or documented invocation
baseline CI workflow or local gate command
baseline evidence report location
README/AGENTS instructions for running the foundation gates
```

This pack MUST NOT implement:

```text
real users / identities
organization membership
tenant switching
business auth flows
audit subsystem
order/payment/seat/ticket/refund/payout/scanning resources
production LightRAG/full agent harness
full contract ingestion rewrite
```

## 5. Required posture

The implementation MUST prove:

```text
root module namespace is Ticketing
OTP app atom is :ticketing
Ash 3.x is the only Ash posture
no V42.* module prefixes are introduced
project compiles
core tests run
CI/local gate command exists
existing Wave 0 pack evidence locations are documented
migration safety command is callable or documented as pending with blocker
UUID binary sort gate is callable or documented as pending with blocker
lint/governance gate is callable or documented as pending with blocker
contract bundle strict gate is callable or documented as pending with blocker
```

## 6. Definitely required resources

None.

This pack is repository/CI/governance foundation only.

Do not create `User`, `Organization`, `OrgMembership`, `AuditEvent`, `Session`, or domain resources in this pack. Those appear in the catalogue seed row as future candidate resources, but they are intentionally deferred to later packs.

## 7. Candidate modules / files

The coding agent may create or modify files in these areas only if they do not already exist or need minimal alignment:

```text
mix.exs
config/*.exs
lib/ticketing/application.ex
lib/ticketing/repo.ex
lib/ticketing_web/* baseline files if Phoenix already exists
test/test_helper.exs
test/support/*
.github/workflows/*
justfile or Makefile
AGENTS.md
README.md
ci/*
tools/*
```

Recommended commands to establish or preserve:

```text
mix compile
mix test
mix format --check-formatted
mix check
mix ticketing.governance.lint
mix ticketing.contracts.strict
mix ticketing.migrations.audit
mix ticketing.uuid_sort.check
```

If a command is not yet implemented, the agent must not fake it. It must either implement the smallest safe wrapper or report a blocker/pending gate.

## 8. Actions / commands to prove

| Command/action | Purpose | Required status |
|---|---|---|
| `mix compile` | Proves the app compiles. | MUST pass. |
| `mix test` | Proves baseline test harness runs. | MUST pass or honestly report blockers. |
| `mix check` | One command for foundation checks. | MUST exist or be added. |
| `governance_lint` | Runs LINT-0/ATP-style scanner or wrapper. | MUST be wired or reported pending. |
| `contract_gate_strict` | Runs strict contract bundle validator where inputs exist. | MUST be wired or reported pending. |
| `migration_safety_check` | Runs CI-002 gate/tooling. | MUST be wired or reported pending. |
| `uuid_binary_sort_check` | Runs CI-001 property/vector checks. | MUST be wired or reported pending. |
| `emit_foundation_report` | Produces a human-readable implementation evidence report. | MUST be created. |

## 9. DB / migrations

This pack MAY verify the Repo and migration infrastructure.

It MUST NOT create product tables.

Allowed migration work:

```text
no new migration
or non-product diagnostic migration already introduced by TB-000
or migration safety fixtures under test/support or test fixtures only
```

If the repo has no database yet, the pack may document the required configuration and stop with a blocker rather than inventing product schemas.

## 10. Policies and tenancy

No production tenant policies are implemented in this pack.

However, the baseline must make future tenant enforcement testable by ensuring:

```text
org_id remains the canonical tenant key in docs/gates
no current_org/process-dictionary convention is introduced
direct Repo usage is not normalized for governed flows
future tenant-resource checks can be wired into CI
```

## 11. Telemetry / evidence

Minimum evidence report location:

```text
reports/foundation/vs_001_foundation_report.md
```

Optional machine-readable report:

```text
reports/foundation/vs_001_foundation_report.json
```

Report MUST include:

```text
pack id
source row id
git sha if available
commands run
pass/fail/pending status per gate
tests run
known blockers
non-goals not touched
```

## 12. Tests

Minimum tests/checks:

```text
compile check
baseline ExUnit smoke test
root namespace check
OTP app atom check
no V42.* module prefix scan
no product resource creation scan for this pack
mix check command exists
foundation evidence report fixture/check
```

## 13. Must-have gates

```text
VS001-001: project compiles under Ticketing root namespace
VS001-002: OTP app atom is :ticketing
VS001-003: Ash posture is Ash 3.x only
VS001-004: no V42.* module prefixes introduced
VS001-005: mix check or equivalent foundation gate exists
VS001-006: baseline tests run and report honestly
VS001-007: governance lint wrapper exists or pending blocker is explicit
VS001-008: contract strict gate wrapper exists or pending blocker is explicit
VS001-009: migration safety gate wrapper exists or pending blocker is explicit
VS001-010: UUID binary sort gate wrapper exists or pending blocker is explicit
VS001-011: VS-001 evidence report is produced
VS001-012: no product domain resource is created by this pack
```

## 14. Non-goals

- Do not implement `User`, `Identity`, `Session`, `Organization`, `OrgMembership`, or `AuditEvent`.
- Do not implement login, registration, org switching, or RBAC/ABAC.
- Do not implement tenant RLS proof; that belongs to `FP-TB-001`.
- Do not implement cross-tenant red-team tests; that belongs to `FP-TB-038`.
- Do not implement audit event subsystem; that belongs to `FP-TB-006`.
- Do not implement error envelope; that belongs to `FP-TB-033`.
- Do not implement any product feature.

## 15. Definition of done

```text
- The app baseline compiles.
- Foundation tests run.
- `mix check` or equivalent exists.
- Governance/contract/migration/UUID gate commands are wired or explicitly reported pending.
- Evidence report is produced.
- No product resources are introduced.
- Agent handoff notes identify the next pack as FP-TB-001-tenant-context-rls-denial.
```
