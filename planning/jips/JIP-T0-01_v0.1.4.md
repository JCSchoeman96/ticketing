# JIP-T0-01 v0.1.4 — Tenant Organizer Authorization + Event Create

- **ID:** JIP-T0-01
- **Version:** 0.1.4
- **Status:** APPROVED
- **Approved:** explicit user approval on 2026-10-25
- **Supersedes for implementation planning:** JIP-T0-01 v0.1.3; earlier versions remain historical
- **Governing spec:** SPEC-T0-01 v0.1.3
- **Roadmap horizon:** T0 — Tenant-scoped GA pending sale
- **Increment boundary:** one authorized `EVT-2.create_event` effect that persists a tenant-owned draft Event. This increment ends after that insert.

This JIP is downstream implementation planning. Installed canonical contracts, ROADMAP, and the active T0 tracer remain higher authority. It records the approved T0-01 packet plus the explicitly approved Ash policy SAT-solver prerequisite discovered during TICK-25. It adds no product/domain semantics beyond canonical authority and does not reinterpret any previously locked organizer, tenant, Session, role, Event, transaction, RLS, error, lifecycle, or concurrency rule.

## 1. Amendment and supersession history

- **v0.1.0** established the initial T0-01 implementation packet.
- **v0.1.1** refreshed the technical baseline but later proved to contain planning drift.
- **v0.1.2** corrected that drift but predated the installed TEN-1 membership-probe and IAM-1 trusted active-Session requirements.
- **v0.1.3** incorporated the repaired authority/tracer boundary and locked the current organizer-proof-to-Event transaction. It also locked the then-current dependency resolution and prohibited new dependencies.
- **v0.1.4** preserves every product/domain and transaction decision from v0.1.3 and changes only the technical prerequisite required to execute Ash authorization policies under the installed Ash 3.36.1 stack: direct runtime dependency `{:simple_sat, "~> 0.1.4"}` is explicitly approved. The blanket no-new-dependency prohibition is narrowed only for this solver prerequisite.

## 2. Objective and boundary

Use persisted canonical organizer state to authorize `evt.event.create`, then create one canonical tenant-owned draft Event. The trusted authentication/session boundary supplies authoritative `user_id` and `session_id`.

One outer governed Ash/PostgreSQL effect transaction spans:

```text
candidate-org membership proof
→ persisted User, Session, and role liveness
→ active organization persona
→ evt.event.create authorization
→ Event insert
```

The candidate `org_id` is a selector. It does not become resolved tenant authority until TEN-1 membership proof succeeds. No resolved organizer persona may be completed in one transaction and reused later to authorize Event creation.

The increment ends after the draft Event is created. The active tracer continues to order `create_event → create_occurrence → publish_event`; this JIP does not pull later work forward.

## 3. Verified baseline

### Repository and authority snapshot

- **Repository:** `JCSchoeman96/ticketing`
- **Verified current `main`:** `39b966180630c0c0dea4183358ca27f74b5eecce`
- **Authority manifest SHA-256:** `f44764cd8310281b7f34a2cef6e50bb67ee659e147268a65e83a86586a842dd0`
- **ROADMAP:** B0 COMPLETE; T0 NEXT
- **Active tracer:** `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`
- **Blocking discovery:** TICK-53 — Ash policy SAT solver prerequisite for TICK-25

The installed canonical authority tree has not changed because of this amendment.

### Governing contracts

| Contract | Version | T0-01 use |
| --- | ---: | --- |
| CANON-1 | 2.0.18 | Selects the installed canonical suite |
| TEN-1 | 2.0.1 | Membership proof before resolved-tenant reads; hide-existence behavior |
| IAM-1 | 4.1.3 | Trusted active Session, persisted organization persona, `evt.event.create` capability mapping and permitted roles |
| IAM-2 | 1.5.0 | Invitation/customer-role-grant sovereignty only; no role grant is in this increment |
| EVT-1 | 3.0.0 | Registered event vocabulary; no publication event is emitted here |
| EVT-2 | 3.0.0 | Canonical Event resource and `create_event` behavior |
| ERR-1 | 2.0.0 | Canonical errors and information hiding |

### Technical baseline

Keep the approved stack:

- Elixir 1.20.4 and Erlang/OTP 29.1.2
- PostgreSQL 18.6
- Phoenix 1.8.16 and LiveView 1.2.13
- Ash 3.36.1
- AshPhoenix 2.3.25
- AshPostgres 2.15.1
- Postgrex 0.22.4
- **SimpleSat 0.1.4 via direct runtime dependency `{:simple_sat, "~> 0.1.4"}` — approved prerequisite**

No Ash, Phoenix, LiveView, AshPostgres, Postgrex, Elixir, OTP, PostgreSQL, or unrelated package upgrade is authorized by this amendment.

### Ash capability decision: SAT solver

**PREREQUISITE / ADOPT — SimpleSat 0.1.4**

Ash 3.36.1 and its Crux dependency expose `simple_sat` and `picosat_elixir` as optional SAT backends. TICK-25 proved that `Ash.Policy.Authorizer` cannot compile policy-bearing resources when neither backend is resolved. The project already locked Ash policies as the application authorization mechanism; therefore one solver is an implementation prerequisite rather than optional feature scope.

Approve exactly one direct runtime dependency:

```elixir
{:simple_sat, "~> 0.1.4"}
```

Reasons:

- directly supported by installed Ash/Crux;
- pure Elixir and dependency-free;
- no native/NIF compiler or runtime portability requirement;
- deterministic workstation and CI setup;
- adequate for the small T0 policy surface unless measured evidence later proves otherwise.

**DEFER — `picosat_elixir 0.2.x`**

PicoSAT may offer better SAT performance for larger workloads, but it adds a native C/NIF + build-tool path. T0 has no measured authorization-solver performance requirement that justifies that operational complexity. Reconsider only from measured evidence under a later approved technical decision.

**REJECT**

- installing both SAT backends;
- removing or replacing Ash authorization policies to avoid the prerequisite;
- environment-dependent custom solver selection or `SAT_SOLVER` overrides;
- an unrelated Ash/dependency upgrade hidden inside this prerequisite.

### Reference repositories

- **Store_Blueprint_Hardening:** current inspected `main` `d90adf8a88d327b5aad68d4561ec5901de614145`; its direct `{:simple_sat, "~> 0.1"}` dependency is **ADAPT** for dependency-pattern evidence only. It is not semantic authority for Ticketing.
- **LiveFrames:** current inspected `main` `547df7da02cd090e049a9b61d172d27a937f0bb4`; **NOT_APPLICABLE** to this backend-only SAT prerequisite and T0-01 domain semantics.

## 4. Scope and non-goals

### In scope

- Ash resources for global `User`, tenant `OrgMembership`, tenant read-only T0 `Session`, and tenant `OrgRoleAssignment` using canonical shapes and identities.
- A governed `Ticketing.Identity` interface for membership proof and persisted liveness/persona evidence required by `create_event`.
- A governed `Ticketing.Events` Event resource and `create_event` action.
- One outer `Ash.transact/3` effect boundary from TEN-1 membership proof through Event insert, with deterministic same-PostgreSQL-backend transaction evidence.
- IAM-1 authorization of `evt.event.create` from the verified persisted organization persona.
- Tenant-resource migrations and database enforcement needed for those resources, using the already-merged owner/runtime split, grants, TenantContext, Repo hook and FORCE-RLS substrate.
- Positive, negative, cross-tenant, rollback and transaction-order evidence required by the approved packet.
- The narrow prerequisite addition of SimpleSat 0.1.4 required by Ash policy authorization.

### Explicit non-goals

- Reimplementing owner/runtime DB separation, runtime grants, TenantContext, the Repo transaction hook, or reusable FORCE-RLS infrastructure.
- AuthIdentity, authentication providers, credentials, passwords, magic links, OAuth, login UI, or Session issuance.
- Reading/receiving raw Session credentials or token hashes; updating, refreshing, rebinding or revoking Session; writing `last_seen_at_utc`; emitting Session lifecycle events.
- Role-grant or invitation flows.
- `create_occurrence`, `publish_event`, publication CAS/outbox, pricing, offers, inventory, quotes, orders, payments, tickets, ledger, UI or API work.
- Any dependency addition or upgrade **other than the explicitly approved `simple_sat ~> 0.1.4` prerequisite**.
- PicoSAT, dual-solver support or environment-selectable solver behavior.

## 5. Decision classification

### CONTRACT_LOCKED

Unchanged from v0.1.3:

- TEN-1 membership proof precedes resolved-tenant User/Session/role/Event business-row reads.
- Failed proof preserves hide-existence behavior.
- IAM-1 trusted active Session consumes authoritative `user_id`/`session_id` only after membership proof.
- `evt.event.create` is authorized only for the verified human organization persona with canonical permitted roles (`org_owner` or `org_admin`).
- EVT-2 defines Event identity, initial draft state and create semantics.
- TEN-1/IAM-1/ERR-1 govern external error behavior and information hiding.

### IMPLEMENTATION_LOCKED

- Use `Ash.transact/3` as the one outer effect boundary containing proof, post-proof liveness reads, persona construction, authorization and Event insert.
- Prove all stages use the same PostgreSQL backend transaction; if installed Ash/AshPostgres cannot demonstrate continuity, STOP and re-Grill.
- Candidate `org_id`, requested `active_scope` and requested `active_role` are selectors only.
- The existing Repo transaction hook sets transaction-local `app.current_org_id` to candidate `org_id`; before membership proof it may authorize only the matching OrgMembership probe. The same GUC UUID remains after proof; no second tenant-context transition is introduced.
- `active_scope` must be exactly `org`.
- `Ticketing.Identity` owns User, OrgMembership, Session and OrgRoleAssignment; `Ticketing.Events` owns Event and `create_event`.
- Runtime state uses Ash resources/domains/actions/interfaces and AshPostgres; RLS remains database defense in depth.
- **SimpleSat 0.1.4 is the single approved SAT backend required by `Ash.Policy.Authorizer`.**

### IMPLEMENTATION_FREE

Module/file layout, private policy/helper decomposition, fixture names and deterministic test-only transaction instrumentation remain implementation-free when they preserve all locked semantics and interfaces.

### AUTHORITY_GAP

None. TICK-53 is a technical prerequisite, not a canonical semantic gap. Any new semantic contradiction discovered during implementation must still stop as an authority gap.

## 6. Resource ownership and interfaces

### `Ticketing.Identity`

Owns:

- global non-PII `User`;
- tenant `OrgMembership`;
- tenant read-only T0 `Session`;
- tenant `OrgRoleAssignment`.

Tenant resources use canonical `org_id` tenancy, identities, relationships, nullability and liveness. T0 never receives, returns, derives, reads or compares a raw Session token or `token_hash`.

### `Ticketing.Events`

Owns tenant Event and the complete governed `create_event` effect. Events uses approved Identity interfaces and does not query Identity tables directly.

### Organizer proof sequence

1. Trusted authentication/session infrastructure supplies authoritative `user_id` and `session_id`; caller supplies candidate selectors.
2. Start the outer `Ash.transact/3`; the existing Repo hook sets transaction-local candidate-org context.
3. TEN-1 `org_membership_probe` is the only pre-proof tenant business-row read. Require active, non-revoked membership for authoritative user; retain persisted `org_membership_id`.
4. After proof, require active User; load Session by authoritative `session_id`; require exact user/org match, `status = active`, `revoked_at_utc = null`, and `expires_at_utc` later than authoritative database UTC time.
5. Require active, non-revoked same-org OrgRoleAssignment for requested role.
6. Construct the transient active organization persona from persisted proof only.
7. Authorize `evt.event.create` through Ash policy authorization under IAM-1.
8. Insert one draft Event in the same transaction and commit; any failure rolls back.

No completed-transaction organizer persona is exposed for later authorization.

## 7. Lifecycle, persistence and database invariants

The only Event lifecycle transition in this increment is:

```text
absent → draft
```

Use exact EVT-2 Event shape and `create_event` semantics. Event identity/public key, ownership, initial `draft` status, timestamps, versions and publication fields remain protected from caller authorship as defined by authority.

Preserve canonical Event uniqueness and tenant-aware identities. Tenant resources use Ash attribute multitenancy plus PostgreSQL ENABLE/FORCE RLS. Runtime role remains non-owner and `NOBYPASSRLS`.

SimpleSat introduces **no database schema, migration, index, FK, RLS, transaction or persistence change**.

## 8. Transactions, concurrency, idempotency and errors

- One outer `Ash.transact/3` effect transaction spans proof through Event insert.
- Deterministic tests prove required query order and one-backend transaction continuity.
- Transaction-local tenant context must clean up after commit, rollback, exception and pooled-connection reuse.
- Do not invent stronger concurrent Session/role-revocation linearization; stop if implementation requires it.
- No generic idempotency/replay contract is introduced by T0-01.
- Preserve TEN-1/IAM-1/EVT-2/ERR-1 error behavior; do not invent codes or leak hidden tenant existence.
- The SAT solver is process-local authorization machinery only and does not change transaction or concurrency semantics.

## 9. Events, outbox, jobs, audit and observability

No Event publication event, outbox, background job or dispatcher is introduced. T0-01 ends at draft Event creation.

Observability must not expose raw `org_id`, `user_id`, `session_id`, credentials or token hashes in telemetry labels or logs. The SimpleSat prerequisite adds no new application telemetry requirement; solver failures are ordinary application/compile failures and must not expose actor data.

## 10. Migration, rollout and rollback

### TICK-53 prerequisite rollout

Before TICK-25 may resume:

1. change only `ticketing/mix.exs` and `ticketing/mix.lock` for the solver prerequisite;
2. add direct runtime `{:simple_sat, "~> 0.1.4"}`;
3. resolve SimpleSat without PicoSAT and without unrelated dependency drift;
4. prove Ash/Crux detects a usable SAT implementation and policy-bearing resources can compile;
5. run the repository verification suite and exact-head CI;
6. independently review and merge the prerequisite PR;
7. verify merged `main` and post-merge CI;
8. close TICK-53 and freshness re-gate TICK-25.

### Rollback

The solver may not be removed while policy-bearing Ash resources requiring it remain. Rollback therefore means either:

- revert the policy-bearing increment together with SimpleSat; or
- separately approve and migrate to another supported SAT backend.

Do not silently fall back to an environment-dependent alternate backend.

## 11. Required tests and verification

### TICK-53 prerequisite

Require evidence that:

- diff is limited to `ticketing/mix.exs` and `ticketing/mix.lock`;
- resolver adds SimpleSat 0.1.4-compatible resolution only and no PicoSAT;
- no unrelated lock entry moves;
- installed Ash/Crux reports an available solver (for example by its supported implementation check or equivalent version-matched API);
- `mix compile --warnings-as-errors` succeeds with policy-bearing Ash resources;
- `mix hex.audit` passes;
- `mix contract.authority` passes;
- `mix precommit` passes on an isolated TEST partition;
- `mix check` passes on an isolated TEST partition;
- `mix check.types` passes;
- `git diff --check` passes;
- tracked-content secret scan passes;
- fresh exact-head CI passes.

### TICK-25/TICK-26 behavior

All positive/negative, tenant-isolation, liveness, read-only Session, transaction-order, same-backend transaction, rollback, migration and RLS tests from v0.1.3 remain required and unchanged.

## 12. Documentation impact

- **CREATE:** `planning/jips/JIP-T0-01_v0.1.4.md`
- **CREATE:** `planning/specs/SPEC-T0-01_v0.1.3.md`
- **UNAFFECTED by TICK-53:** `ticketing/docs/` implementation-state documentation; no runtime/domain behavior has merged merely by adding the prerequisite.
- Later T0-01 implementation documentation/handoff obligations remain unchanged from v0.1.3 and must describe only merged implementation state.

## 13. Risks and gaps

- SimpleSat can be slower than PicoSAT for larger SAT problems. This is accepted for T0 because no measured solver bottleneck exists. Performance must be observed before any later backend change is proposed.
- Adding both backends could make solver selection less explicit and is prohibited.
- Environment-controlled solver overrides could make behavior differ between workstation and CI and are prohibited.
- Any unrelated resolver drift is out of scope and must stop TICK-53.
- No authority gap is currently recorded.

## 14. Definition of Done

T0-01 remains complete only when all applicable v0.1.3 product/domain DoD is satisfied. This amendment additionally requires:

1. this approved JIP and derivative SPEC are merged to `main`;
2. TICK-53 implements only the approved SimpleSat prerequisite;
3. prerequisite PR receives exact-diff review, fresh CI and explicit user merge authorization;
4. merged-main verification passes;
5. TICK-53 closes;
6. TICK-25 is freshness re-gated before Identity implementation resumes;
7. no TICK-26 or later behavior is pulled forward.
