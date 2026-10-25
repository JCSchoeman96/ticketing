# SPEC-T0-01 v0.1.3 — Trusted Organizer Effect Boundary and Draft Event Creation

- **ID:** SPEC-T0-01
- **Version:** 0.1.3
- **Status:** APPROVED
- **Approved:** explicit user approval on 2026-10-25
- **Governing JIP:** JIP-T0-01 v0.1.4 — APPROVED
- **Supersedes for implementation planning:** SPEC-T0-01 v0.1.2; earlier versions remain historical
- **Repository baseline:** `39b966180630c0c0dea4183358ca27f74b5eecce`
- **Manifest:** `authority/contracts/manifest.json`, SHA-256 `f44764cd8310281b7f34a2cef6e50bb67ee659e147268a65e83a86586a842dd0`
- **Active tracer:** `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`

This spec derives from JIP-T0-01 v0.1.4. It cannot create or override canonical semantics. The only change from SPEC-T0-01 v0.1.2 is the explicitly approved SimpleSat prerequisite required to execute Ash authorization policies under the installed Ash 3.36.1 stack. All organizer, Session, role, tenant, RLS, transaction, lifecycle, error and Event-create semantics remain unchanged.

## 1. Objective and baseline

Implement canonical organizer authorization for one `EVT-2.create_event` operation. Trusted authentication/session infrastructure supplies authoritative `user_id` and `session_id`. Ticketing proves organization membership, validates persisted Session and requested role, constructs the transient active organization persona, authorizes IAM-1 4.1.3's `evt.event.create`, and inserts one tenant-owned draft Event inside one outer `Ash.transact/3` transaction sharing one PostgreSQL backend.

Already-merged baseline remains separate migration-owner/runtime DB identities, runtime grants, transaction-local TenantContext, the Repo transaction hook and reusable FORCE-RLS infrastructure. Reuse these facilities; do not reimplement them.

Locked technical baseline:

- Elixir 1.20.4 / OTP 29.1.2
- PostgreSQL 18.6
- Phoenix 1.8.16 / LiveView 1.2.13
- Ash 3.36.1
- AshPhoenix 2.3.25
- AshPostgres 2.15.1
- Postgrex 0.22.4
- **SimpleSat 0.1.4-compatible direct runtime dependency: `{:simple_sat, "~> 0.1.4"}`**

No other dependency or runtime upgrade is authorized by this spec.

## 2. SAT-solver prerequisite

Ash policy authorization is part of the approved architecture. Under the installed Ash 3.36.1/Crux stack, policy-bearing resources require one supported SAT backend to be resolved. TICK-25 proved that the current lock has neither backend installed and compilation stops with no SAT solver available.

### Adopt

Add exactly:

```elixir
{:simple_sat, "~> 0.1.4"}
```

as a direct runtime dependency.

SimpleSat is selected because it is directly supported by installed Ash/Crux, pure Elixir, dependency-free and avoids native/NIF build requirements. It is adequate for the current T0 policy surface absent measured evidence of solver cost.

### Defer

`picosat_elixir 0.2.x` is deferred. It may offer better performance for larger SAT workloads but introduces C/NIF and native-build complexity not justified by current T0 evidence.

### Reject

Do not:

- install both solvers;
- remove or replace Ash policies to avoid the prerequisite;
- add environment-dependent custom solver selection or `SAT_SOLVER` overrides;
- hide unrelated dependency upgrades in the prerequisite.

The solver supplies boolean-policy evaluation machinery only. It does not change domain semantics, persistence, tenancy, RLS, actor construction, transactions, errors, events or lifecycle behavior.

## 3. Owned domains and interfaces

### `Ticketing.Identity`

Owns canonical global `User` and tenant `OrgMembership`, read-only T0 `Session`, and `OrgRoleAssignment` resources. It exposes only governed interfaces required to prove membership and read persisted authorization state.

T0 never receives, returns, derives, reads, compares or logs a raw Session credential or `token_hash`. Session remains read-only: no issuance, refresh, rebind, revoke, `last_seen_at_utc` update or Session lifecycle event.

### `Ticketing.Events`

Owns tenant-scoped Event and governed `create_event`. Events calls approved Identity interfaces inside the same outer transaction and does not query Identity tables directly.

No public interface may return an organizer persona from one completed transaction for later Event authorization.

## 4. Organizer inputs and proof sequence

The required order remains:

1. Trusted authentication/session infrastructure authenticates its own credential and supplies authoritative `user_id` and `session_id`. Caller `org_id`, `active_scope` and `active_role` are selectors only. Require `active_scope = org`.
2. Start one outer `Ash.transact/3`. The existing Repo hook sets transaction-local `app.current_org_id` to candidate `org_id`.
3. Before proof, the only tenant business-row read is TEN-1 `org_membership_probe` for the candidate org and authoritative user. Require active, non-revoked membership and retain persisted `org_membership_id`.
4. If proof fails, stop and preserve hide-existence behavior. Do not read User, Session, role assignment or Event business rows.
5. After successful proof, keep the same GUC UUID. Require active User. Load Session by authoritative `session_id`; require exact user/org match, `status = active`, null `revoked_at_utc`, and `expires_at_utc` later than authoritative database UTC time.
6. Require active, non-revoked same-org OrgRoleAssignment for requested role.
7. Construct the transient organization persona only from authoritative/persisted proof.
8. Authorize `evt.event.create` through Ash policy authorization under IAM-1. Only canonical permitted human organization roles (`org_owner`, `org_admin`) satisfy the capability.
9. Insert one draft Event through the governed Events action and commit. Any failure rolls back the effect.
10. Deterministic test-only evidence proves required query order and that proof, post-proof reads, authorization and Event insert share one PostgreSQL backend transaction.

The SimpleSat prerequisite changes none of these steps.

## 5. Event creation boundary

The only Event transition in this increment is:

```text
absent → draft
```

Use exact EVT-2 3.0.0 resource shape and `create_event` semantics. Generate canonical Event identity/public key, bind the proven organization, initialize canonical draft state, database-owned timestamps, version/fence fields and null publication time. Caller may not author protected identity, ownership, lifecycle or version fields.

Preserve EVT-2 uniqueness and tenant-aware identities. Do not add Event publication, Occurrence creation, outbox or lifecycle update behavior.

## 6. Tenancy, RLS and persistence

- Reuse `Ticketing.Repo`, `Ticketing.MigrationRepo`, `Ticketing.Platform.TenantContext`, runtime grants and FORCE-RLS substrate.
- Tenant resources use Ash attribute multitenancy plus PostgreSQL ENABLE/FORCE RLS.
- Runtime role remains non-owner and `NOBYPASSRLS`.
- Ordinary runtime reads/writes use Ash resources/actions/interfaces with actor and tenant context; no direct Repo/Ecto/raw-SQL domain API.
- Test fixtures may use the approved narrow owner/fixture boundary only.
- Transaction-local GUC cleanup must be proved after commit, rollback, exception and pooled-connection reuse.
- SimpleSat adds no database table, migration, index, FK, constraint, RLS policy or data migration.

## 7. Authorization and actor posture

Ash policies remain the application authorization mechanism and PostgreSQL RLS remains defense in depth.

SimpleSat is an implementation dependency of `Ash.Policy.Authorizer`; it does not become an application/domain interface and must not receive Ticketing-specific semantics.

Do not use `authorize?: false` for ordinary organizer behavior. Do not substitute caller role claims, application-side tenant filtering or custom authorization shortcuts for persisted proof and Ash authorization.

## 8. Transactions, concurrency and idempotency

- Use one outer `Ash.transact/3` from membership proof through Event insert.
- Prove one PostgreSQL backend transaction and required read ordering.
- Do not add a second tenant-context transition.
- Do not invent stronger concurrent Session/role-revocation linearization.
- No generic idempotency or replay contract is introduced.
- SAT solving is process-local authorization evaluation and changes no transaction or locking semantics.

## 9. Errors, events and observability

Preserve installed TEN-1, IAM-1, EVT-2 and ERR-1 behavior:

- failed membership proof: hide-existence external not-found behavior;
- invalid/non-live Session after proof: unauthenticated behavior;
- missing/inactive/revoked/incapable requested role: forbidden behavior;
- invalid Event input: canonical validation behavior.

Do not invent new product error codes for solver operation. A missing solver is a build/configuration failure, not a domain result.

No publication event, outbox or job is introduced. Telemetry/logging must not expose raw `org_id`, `user_id`, `session_id`, credentials or token hashes.

## 10. TICK-53 prerequisite implementation

Before TICK-25 resumes, implement a dependency-only prerequisite:

- modify only `ticketing/mix.exs` and `ticketing/mix.lock`;
- add direct runtime `{:simple_sat, "~> 0.1.4"}`;
- resolve SimpleSat only; no PicoSAT and no unrelated lock drift;
- prove installed Ash/Crux can select an available SAT implementation;
- prove policy-bearing resources compile under `mix compile --warnings-as-errors`;
- run `mix hex.audit`, `mix contract.authority`, `mix precommit`, `mix check`, `mix check.types`, `git diff --check`, tracked-content secret scan and fresh exact-head CI;
- use isolated TEST partitions for DB-backed local gates;
- obtain independent review and explicit user merge authorization;
- after merge, verify merged-main CI, close TICK-53 and freshness re-gate TICK-25.

No migration belongs to TICK-53.

## 11. Rollback

Do not remove SimpleSat while policy-bearing resources requiring a solver remain. Rollback options are:

1. revert the policy-bearing increment and solver together; or
2. separately approve a different supported SAT backend and migrate explicitly.

No automatic/environment-dependent fallback is permitted.

## 12. Verification requirements for T0-01

The prerequisite does not reduce existing behavioral verification. The implementation still requires, as applicable:

- canonical resource shapes, identities, nullability and relationships;
- global User versus tenant resources;
- Session read-only posture and token-hash exclusion;
- governed membership/read interfaces;
- positive/negative organizer authorization;
- cross-tenant and FORCE-RLS denial;
- membership-first read ordering including failure path;
- same-backend one-transaction proof;
- transaction rollback and tenant-context cleanup;
- canonical Event insert and uniqueness behavior;
- migration/generated-code inspection;
- full repository gates and fresh exact-head CI.

## 13. Reference posture

- Store_Blueprint_Hardening current inspected `main` `d90adf8a88d327b5aad68d4561ec5901de614145`: **ADAPT** only for the direct `simple_sat` dependency pattern; never semantic authority.
- LiveFrames current inspected `main` `547df7da02cd090e049a9b61d172d27a937f0bb4`: **NOT_APPLICABLE**.

## 14. Documentation impact and completion

- This spec is created alongside `planning/jips/JIP-T0-01_v0.1.4.md`.
- TICK-53 does not update `ticketing/docs/` because it adds no merged domain/runtime behavior beyond dependency availability.
- Later implementation docs/handoff must continue to describe merged implementation state only.

T0-01 cannot resume TICK-25 until this approved packet is merged, TICK-53 is implemented and merged with green merged-main verification, and TICK-25 is freshness re-gated. TICK-26 and later work remain out of scope until TICK-25 completes.
