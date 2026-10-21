# T0-01 Tenant/Auth/RLS + Event Create/Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` only for the single Plane ticket currently marked READY. Do **not** execute this whole plan in one branch. Each task below maps to one Plane child and requires its own freshness check, TDD cycle, PR, independent review, merge, and dependency release before the next task may become READY.

**Goal:** Implement JIP-T0-01 v0.1.1 as a secure Ash/PostgreSQL foundation through governed Event creation/publication and atomic durable publication outbox, stopping before Occurrence.

**Architecture:** `Ticketing.Identity` owns persisted organizer authorization state; `Ticketing.Events` owns Event lifecycle and its private publication outbox; platform infrastructure owns only database-role/bootstrap and the narrow tenant-GUC seam. Tenant resources use Ash attribute multitenancy and PostgreSQL FORCE RLS as independent guards. Normal application database access uses a least-privilege runtime role, while migrations/bootstrap use a distinct owner identity.

**Tech Stack:** Elixir 1.20.4, OTP 29.1.2, PostgreSQL 18.6, Phoenix 1.8.16, LiveView 1.2.13, Ash 3.36.1, AshPhoenix 2.3.25, AshPostgres 2.15.1, Postgrex 0.22.4.

**Spec:** `planning/specs/SPEC-T0-01_v0.1.0.md`

**Governing JIP:** `planning/jips/JIP-T0-01_v0.1.1.md`

## Global Constraints

- Canonical authority + ROADMAP + active tracer outrank this plan, the spec, Plane, and code.
- Root namespace is `Ticketing`; OTP app is `:ticketing`; never introduce `V42.*` application modules/examples.
- No dependency upgrade is authorized inside T0-01.
- No Occurrence, commerce, payment, ticketing, ledger, admission, auth-provider/login UI, outbox dispatcher, or later-horizon work.
- Governed application persistence is Ash-native; direct Repo/Ecto/raw SQL is prohibited as a domain API.
- Narrow low-level DB calls are allowed only for migration/DDL/RLS/test-fixture infrastructure and the JIP-approved tenant-context seam.
- Every tenant resource uses explicit Ash tenant context plus PostgreSQL ENABLE/FORCE RLS.
- Normal runtime DB roles are non-owner, non-superuser, `NOBYPASSRLS`, no `CREATEDB`, no `CREATEROLE`.
- `app.current_org_id` is validated and transaction-local; it must not leak across commit, rollback, Sandbox or pooled connection reuse.
- Organizer roles are derived from persisted IAM state; caller-supplied roles are never authoritative.
- Event publish correctness is state + lock/version CAS; a read-then-write implementation is insufficient.
- Event mutation and `ticketing.event.published.v1` persistence commit or roll back together.
- All generated AshPostgres migrations/snapshots must be inspected; generated output does not override tenant-first keys/FKs/RLS/constraints.
- Use current installed UsageRules/HexDocs APIs at the time each READY ticket starts. Material framework limitations are STOP conditions, not permission to weaken the JIP.

## Review Focus

1. **Owner/runtime role confusion:** setup/migration helpers must never leave the ordinary app/test Repo running as the owner role.
2. **Tenant context leakage:** a tenant GUC visible in one transaction must be absent from the next borrower after both commit and rollback.
3. **Ash identity + tenant duplication:** for attribute-multitenant identities, verify generated DB uniqueness is canonically `(org_id, ...)`; do not accidentally encode `org_id` twice merely because Ash automatically scopes identities by tenant.
4. **CAS weakening:** two concurrent `publish_event` calls from the same draft/fence must produce exactly one successful transition and exactly one publication row.
5. **Atomic outbox failure:** a forced outbox insert failure must leave the Event in its pre-publish state with unchanged version/fence and no orphan event row.

---

## Task 1 — TICK-23: Separate PostgreSQL owner and runtime identities

**Plane:** `TICK-23` — `[IMPL] T0-01.1 Separate PostgreSQL owner and runtime identities`

**Files:**
- Modify: `ticketing/config/dev.exs`
- Modify: `ticketing/config/test.exs`
- Modify: `ticketing/config/runtime.exs`
- Modify: `ticketing/mix.exs`
- Modify: `ticketing/lib/ticketing/release.ex`
- Modify: `.github/workflows/ci.yml`
- Modify as needed: `.devcore/env.local.template`
- Create: `ticketing/lib/ticketing/migration_repo.ex` if the RED/GREEN design selects a distinct migration Repo
- Create: `ticketing/lib/ticketing/platform/database_roles.ex` or equivalent owner-only bootstrap/verification helper if required
- Create/Modify tests under: `ticketing/test/ticketing/` and `ticketing/test/support/`

**Interfaces:**
- Consumes: existing DEV/TEST shared-local endpoints and owner roles; current `Ticketing.Repo` and Ecto migration path.
- Produces: ordinary `Ticketing.Repo` runtime credentials; an explicit owner/migration execution path; deterministic runtime-role posture verification used by all later tasks.

- [ ] **Step 1: Write RED configuration/role tests.**
  - Assert ordinary DEV/TEST Repo configuration resolves the dedicated runtime role rather than `ticketing_dev`/`ticketing_test`.
  - Assert owner/migration configuration is separately addressable.
  - Assert runtime role catalog flags are `rolsuper=false`, `rolbypassrls=false`, `rolcreatedb=false`, `rolcreaterole=false`.
  - Preserve existing DEV/TEST physical-cluster and partition-name guards.

- [ ] **Step 2: Run the focused tests and observe the expected failure.**
  - Run the smallest new role/config tests plus existing `repo_pool_config_test.exs`/`repo_smoke_test.exs` as applicable.
  - Expected RED: current Repo still resolves owner/bootstrap credentials or no separate migration path exists.

- [ ] **Step 3: Implement the minimal credential split.**
  - Normal `Ticketing.Repo` must use runtime credentials.
  - Migration/bootstrap must use owner credentials without making the owner the application default.
  - Prefer a dedicated unsupervised `Ticketing.MigrationRepo` sharing `priv/repo` if that keeps Mix/release migration ownership explicit; if installed Ecto/Ash tooling proves a smaller supported mechanism, use it and record why.
  - Do not lifecycle-create/rotate shared-local runtime cluster roles. Detect missing/misconfigured local roles and fail actionably.
  - CI may create its ephemeral runtime role because CI PostgreSQL is job-owned.

- [ ] **Step 4: Refactor setup/test/CI sequencing.**
  - Owner/bootstrap: create partition DB where applicable, migrate, apply allowed grants/default privileges.
  - Runtime: start ordinary app/test Repo and execute tests.
  - Preserve `MIX_TEST_PARTITION` isolation and PostgreSQL 18.6.

- [ ] **Step 5: Run GREEN focused verification.**
  - Prove `current_user` is runtime during ordinary tests.
  - Prove owner/runtime identities are distinct.
  - Prove TEST owner retains only the pre-approved CREATEDB use while runtime does not.

- [ ] **Step 6: Run full ticket gates.**
  - `mix precommit`
  - `mix check`
  - `mix check.types`
  - required PostgreSQL 18.6 partition tests
  - `git diff --check`

- [ ] **Step 7: Open the TICK-23 PR and stop.**
  - Record exact role/config changes, local infrastructure prerequisites and verification.
  - Leave unmerged for independent review; do not start TICK-24.

---

## Task 2 — TICK-24: Transaction-local tenant context + FORCE-RLS substrate

**Plane:** `TICK-24` — `[IMPL] T0-01.2 Establish transaction-local tenant context and FORCE-RLS substrate`

**Files:**
- Create: `ticketing/lib/ticketing/platform/tenant_context.ex`
- Create supporting migration/RLS helpers only if needed under: `ticketing/lib/ticketing/platform/`
- Create/Modify tests: `ticketing/test/ticketing/platform/tenant_context_test.exs`
- Create test-only Ash/RLS probe support under: `ticketing/test/support/` only if required to prove Ash same-connection behavior before canonical tenant resources exist
- Add generated/new migrations only for reusable production substrate actually required by this ticket; test-only probes must not become product schema.

**Interfaces:**
- Consumes: merged TICK-23 runtime/owner split.
- Produces: a narrow tenant-context seam and tested RLS pattern that later tenant Ash resources consume.

- [ ] **Step 1: Write RED tests for the transaction invariant before selecting the low-level integration.**
  - Valid UUID becomes visible as `current_setting('app.current_org_id', true)` only inside the governed transaction.
  - Missing/malformed UUID fails closed.
  - Commit clears the value for a later borrower.
  - Rollback clears the value for a later borrower.
  - A test-only Ash operation and the GUC setter must observe the same backend transaction/connection.

- [ ] **Step 2: Run RED and capture the specific missing capability.**
  - Do not implement a session-level shortcut to make the test pass.

- [ ] **Step 3: Implement `Ticketing.Platform.TenantContext` with one narrow responsibility.**
  - Required conceptual interface: `put_current_org!(validated_org_uuid) :: :ok` inside an already-governed transaction, or an equivalently narrow wrapper proven by the RED test.
  - It may execute only the `set_config('app.current_org_id', ..., true)`/equivalent infrastructure statement; it is not a general SQL API.
  - Use the current Ash/AshPostgres transaction integration that actually passes the same-connection proof.
  - If no supported integration can pass without turning Repo into a domain API, STOP and create a technical blocker/re-Grill.

- [ ] **Step 4: Establish the reusable FORCE-RLS migration/test pattern.**
  - ENABLE RLS + FORCE RLS.
  - `USING` and `WITH CHECK` compare tenant row `org_id` to transaction-local GUC.
  - Missing tenant, another tenant and malformed tenant all fail closed.
  - Runtime role cannot bypass the policy.

- [ ] **Step 5: Run pool/Sandbox isolation tests repeatedly.**
  - Explicitly borrow/reuse connections across tenant A, no-tenant and tenant B cases.

- [ ] **Step 6: Run full gates, open TICK-24 PR, stop.**

---

## Task 3 — TICK-25: Minimum IAM organizer authorization substrate

**Plane:** `TICK-25` — `[IMPL] T0-01.3 Implement minimum IAM organizer authorization substrate`

**Files:**
- Create: `ticketing/lib/ticketing/identity.ex`
- Create: `ticketing/lib/ticketing/identity/user.ex`
- Create: `ticketing/lib/ticketing/identity/auth_identity.ex`
- Create: `ticketing/lib/ticketing/identity/org_membership.ex`
- Create: `ticketing/lib/ticketing/identity/org_role_assignment.ex`
- Create: `ticketing/lib/ticketing/identity/organizer_actor.ex` if a typed actor struct is useful
- Create: `ticketing/lib/ticketing/identity/resolve_organizer.ex` or equivalent private Ash-interface orchestration
- Create generated migrations/snapshots through supported AshPostgres tooling
- Create tests under: `ticketing/test/ticketing/identity/`

**Interfaces:**
- Consumes: TICK-24 tenant/RLS seam.
- Produces: `Ticketing.Identity` code interface capable of resolving an organizer actor from persisted `(org_id, user_id)` state; later Events code consumes only that actor/interface, not IAM tables directly.

- [ ] **Step 1: Re-read exact installed IAM-1 4.1.2 / IAM-2 1.5.0 / TEN-1 2.0.0 resource fields and identities.**
  - Copy no fields from chat/spec when the canonical JSON is more precise.

- [ ] **Step 2: Write RED resource/actor-resolution tests.**
  - Owner and admin positive cases.
  - no membership; inactive/revoked membership; missing/revoked role.
  - forged externally supplied role does not grant authority.
  - cross-tenant membership/roles remain hidden.
  - actor carries the persisted selected `org_membership_id`.

- [ ] **Step 3: Implement the two Ash domains/resources minimally.**
  - `User`/`AuthIdentity` global; membership/role tenant-scoped.
  - Attribute multitenancy on `org_id`, `global? false`.
  - For canonical tenant identities such as `(org_id, org_membership_id)` and `(org_id, user_id)`, use current Ash tenant-aware identity semantics so the generated database uniqueness is exactly canonical. Do not blindly list `org_id` twice if Ash automatically injects the tenant attribute; inspect the generated migration.
  - No login/session/provider behavior.

- [ ] **Step 4: Generate migrations/snapshots, then inspect before applying.**
  - Tenant-first unique indexes/FKs.
  - required nullability/immutability.
  - ENABLE/FORCE RLS and policies.
  - runtime owner/grant posture.

- [ ] **Step 5: Implement organizer resolution using governed Identity actions/code interfaces.**
  - Resolve membership + active roles from persisted state under explicit tenant/RLS context.
  - Events must not query IAM tables directly.

- [ ] **Step 6: Run focused, cross-tenant and direct-runtime-role tests; then full gates.**

- [ ] **Step 7: Open TICK-25 PR and stop.**

---

## Task 4 — TICK-26: Event resource + `create_event`

**Plane:** `TICK-26` — `[IMPL] T0-01.4 Implement Event resource and create_event`

**Files:**
- Create: `ticketing/lib/ticketing/events.ex`
- Create: `ticketing/lib/ticketing/events/event.ex`
- Create private policy/check/change modules under `ticketing/lib/ticketing/events/` only as needed
- Create generated migration/snapshot files
- Create tests under: `ticketing/test/ticketing/events/event_create_test.exs`

**Interfaces:**
- Consumes: `Ticketing.Identity` organizer actor interface + TICK-24 tenant/RLS seam.
- Produces: governed `Ticketing.Events.create_event` (or current Ash code-interface equivalent) returning a canonical draft Event.

- [ ] **Step 1: Re-read installed EVT-2 3.0.0 Event/create action, IAM capability and ERR/TEN requirements.**

- [ ] **Step 2: Write RED create tests.**
  - authorized `org_owner`/`org_admin` succeeds;
  - unauthorized/missing tenant/cross-tenant cases fail correctly;
  - validation failure writes nothing;
  - initial status `draft`, version `1`, lock_version `1`, `published_at_utc=nil`;
  - database owns timestamps/fence defaults and client cannot author the fence.

- [ ] **Step 3: Implement `Ticketing.Events.Event` and explicit `create_event`.**
  - No public generic status/lifecycle update.
  - Attribute multitenancy + FORCE RLS.
  - Ash policies consume resolved actor/capability, not caller role strings.

- [ ] **Step 4: Generate/inspect migration.**
  - Tenant-aware keys/FKs/indexes, lifecycle constraints, DB defaults, RLS.

- [ ] **Step 5: Run focused Event create tests + direct runtime-role RLS tests + full gates.**

- [ ] **Step 6: Open TICK-26 PR and stop.**

---

## Task 5 — TICK-27: `publish_event` CAS + atomic durable publication outbox

**Plane:** `TICK-27` — `[IMPL] T0-01.5 Implement publish_event CAS and atomic publication outbox`

**Files:**
- Modify: `ticketing/lib/ticketing/events/event.ex`
- Create: `ticketing/lib/ticketing/events/publication_outbox.ex`
- Create private atomic/CAS/outbox changes/checks under: `ticketing/lib/ticketing/events/`
- Create generated migration/snapshot files
- Create tests: `ticketing/test/ticketing/events/event_publish_test.exs`
- Create race/rollback support under `ticketing/test/support/` only as needed

**Interfaces:**
- Consumes: existing draft Event + resolved organizer + explicit tenant/request/trace context.
- Produces: governed `publish_event(event_id, expected_lock_version, ...)` behavior and one durable `ticketing.event.published.v1` record for the committed Event version.

- [ ] **Step 1: Re-read exact EVT-2 publish guards, EVT-1 envelope/payload/dedupe rules, ERR/OBS requirements.**

- [ ] **Step 2: Write RED publish tests before implementation.**
  - happy path draft→published;
  - invalid/non-draft precondition;
  - stale fence no write;
  - DB publication time;
  - Event version + lock_version increment;
  - exactly one outbox row with canonical payload `{event_id, version}` and required envelope context;
  - forced outbox insert failure rolls the Event back.

- [ ] **Step 3: Write RED concurrent-race test.**
  - Synchronize two publishers against the same draft/fence.
  - Assert one success, one governed stale/precondition result, one committed Event version and one outbox row.

- [ ] **Step 4: Implement CAS with current supported Ash/AshPostgres atomic/filter mechanics.**
  - No read-then-write correctness.
  - If installed APIs cannot express the locked CAS behind Ash, STOP and re-Grill.

- [ ] **Step 5: Implement private Ash-backed publication outbox in the same transaction.**
  - DB unique dedupe semantic equivalent: `(event_type, org_id, event_id, version)`.
  - No worker, PubSub, broker/provider fields or generic event bus.

- [ ] **Step 6: Run race, rollback, RLS and full gates.**

- [ ] **Step 7: Open TICK-27 PR and stop.**

---

## Task 6 — TICK-28: Cross-tenant/race/replay/rollback integration proof

**Plane:** `TICK-28` — `[IMPL] T0-01.6 Verify cross-tenant, race, replay and rollback invariants`

**Files:**
- Create/Modify integration tests under: `ticketing/test/ticketing/t0_01/`
- Modify test support only where needed for deterministic race/fault injection
- Do not add new production semantics/resources/actions in this task

**Interfaces:**
- Consumes: merged TICK-23 through TICK-27 behavior.
- Produces: evidence that all JIP security/concurrency/rollback classes hold end to end.

- [ ] **Step 1: Build an explicit JIP test-coverage matrix.**
  - Map every required positive/negative/cross-tenant/race/replay/rollback/runtime-role test to an existing test or a missing RED test.

- [ ] **Step 2: Add only missing RED integration tests.**
  - Runtime direct SQL RLS isolation.
  - no/malformed GUC.
  - pooled connection reset.
  - organizer resolution + Event path cross tenant.
  - concurrent publish and duplicate outbox protection.
  - deterministic outbox-failure rollback.
  - clean partition migration/reapply evidence.

- [ ] **Step 3: Fix only implementation defects already within the approved JIP/spec.**
  - If a test requires new semantics or architecture, capture blocker and STOP instead of expanding this ticket.

- [ ] **Step 4: Audit every new direct Repo/Ecto/raw-SQL occurrence.**
  - Classify it as migration/DDL/RLS/test-fixture/approved tenant seam or remove it.

- [ ] **Step 5: Run complete verification suite and exact-head CI; open TICK-28 PR and stop.**

---

## Task 7 — TICK-29: Modular implementation docs + handoff

**Plane:** `TICK-29` — `[IMPL] T0-01.7 Update modular implementation docs and T0-01 handoff`

**Files:**
- Create: `ticketing/docs/platform/tenancy-and-authorization.md`
- Create: `ticketing/docs/domains/identity/README.md`
- Create: `ticketing/docs/domains/events/README.md`
- Create: `ticketing/docs/handoffs/T0-01.md`
- Modify: `ticketing/docs/README.md` only if navigation requires it

**Interfaces:**
- Consumes: exact merged implementation from TICK-23 through TICK-28.
- Produces: truthful derived current-state documentation and closeout record for review.

- [ ] **Step 1: Verify the current merged main SHA and exact implemented boundaries before writing.**

- [ ] **Step 2: Draft only current-state docs.**
  - Domain ownership/interfaces.
  - owner/runtime DB posture.
  - tenant propagation/RLS.
  - Event lifecycle/CAS/outbox actually implemented.
  - test/verification posture and explicit deferrals.
  - Do not document Occurrence/later T0 as current.

- [ ] **Step 3: Write `T0-01.md` handoff with governing JIP/spec, Plane tickets, PRs, known warnings/deferrals and verification evidence.**

- [ ] **Step 4: Verify every substantive statement against merged code/migrations/tests; run doc/repo gates; open TICK-29 PR and stop.**

---

## Task 8 — TICK-30: Independent implementation + closeout review

**Plane:** `TICK-30` — `[REVIEW] T0-01 Independent implementation and closeout review`

**Files:** no feature files are authored merely to make review pass; discoveries return to the owning ticket/process.

**Interfaces:**
- Consumes: approved JIP/spec, Plane ledger, exact merged implementation, migrations/snapshots, tests, docs/handoff and fresh CI.
- Produces: independent CLEAN/blocked verdict and, only when all DoD evidence passes, JIP closeout eligibility.

- [ ] **Step 1: Reverify main/CANON/manifest/ROADMAP/tracer/JIP/spec/prerequisite freshness.**

- [ ] **Step 2: Inspect exact implementation diffs and generated DB artifacts.**
  - Runtime role posture; FORCE RLS; tenant keys/FKs; IAM actor derivation; Event create/publish; CAS; outbox atomicity/dedupe.

- [ ] **Step 3: Audit bypass risk.**
  - Every direct Repo/Ecto/raw-SQL call has a narrow approved infrastructure/test classification.
  - No `authorize?: false` or tenant omission on ordinary governed paths.

- [ ] **Step 4: Verify required tests and fresh gates.**
  - `mix precommit`
  - `mix check`
  - `mix check.types`
  - migration/codegen verification
  - applicable Authority checks
  - exact-head CI

- [ ] **Step 5: Verify handoff against actual merged SHA.**

- [ ] **Step 6: Record review evidence in GitHub + Plane.**
  - If clean, close children/JIP only after merge/handoff evidence.
  - If blocked, create/link the correct BUG/BLOCKER/AUTHORITY GAP and stop; do not silently repair semantics in review.

---

## Execution Handoff

This plan is intentionally **ticket-gated**, not a single execution script.

After the planning PR containing this plan/JIP/spec is independently reviewed and merged:

1. refresh `main`, CANON, tracer, prerequisites and TICK-23;
2. mark **only TICK-23** READY if still dependency-clear;
3. hand only Task 1 to the coding agent;
4. require TDD + PR + independent review + merge + evidence;
5. close TICK-23;
6. refresh TICK-24 before marking it READY;
7. repeat through TICK-30.

No agent may use this plan to skip Plane readiness, implement future tasks early, self-approve a stale JIP/spec, or treat implementation details here as authority over installed contracts.