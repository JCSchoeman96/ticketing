# JIP-T0-01 v0.1.5 — Tenant Organizer Authorization + Event Create

- **ID:** JIP-T0-01
- **Version:** 0.1.5
- **Status:** APPROVED
- **Approved:** explicit user approval on 2026-10-26
- **Supersedes for implementation planning:** JIP-T0-01 v0.1.4; earlier versions remain historical
- **Governing spec:** SPEC-T0-01 v0.1.4
- **Roadmap horizon:** T0 — Tenant-scoped GA pending sale
- **Increment boundary:** one authorized `EVT-2.create_event` effect that persists a tenant-owned draft Event. This increment ends after that insert.

This JIP is downstream implementation planning. Installed canonical contracts, ROADMAP, and the active T0 tracer remain higher authority. It preserves the approved T0-01 product/domain behavior while resolving two implementation-governance blockers discovered during TICK-25 review: the security-driven Ash/AshPostgres baseline update and the explicit TEN-1 tenant-primary-key exception selection. It does not create new product/domain semantics.

## 1. Amendment and supersession history

- **v0.1.0** established the initial T0-01 implementation packet.
- **v0.1.1** refreshed the technical baseline but later proved to contain planning drift.
- **v0.1.2** corrected that drift but predated the installed TEN-1 membership-probe and IAM-1 trusted active-Session requirements.
- **v0.1.3** incorporated the repaired authority/tracer boundary and locked the organizer-proof-to-Event transaction.
- **v0.1.4** preserved those semantics and explicitly approved direct runtime `{:simple_sat, "~> 0.1.4"}` as the Ash policy SAT prerequisite.
- **v0.1.5** preserves all locked product/domain, transaction, authorization and lifecycle decisions while: (1) replacing the now-known-vulnerable Ash 3.36.1 / AshPostgres 2.15.1 baseline with Ash 3.37.2 / AshPostgres 2.15.2 as a separate security prerequisite; and (2) explicitly selecting TEN-1's narrow single-column tenant-PK exception for exactly three TICK-25 physical UUIDv7 primary keys.

## 2. Objective and boundary

Use persisted canonical organizer state to authorize `evt.event.create`, then create one canonical tenant-owned draft Event. Trusted authentication/session infrastructure supplies authoritative `user_id` and `session_id`.

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

## 3. Verified freshness baseline

### Repository and authority snapshot

- **Repository:** `JCSchoeman96/ticketing`
- **Verified current `main`:** `5e0d86dba47d6b4531cbf4b09cb61fa46c9c5695`
- **Verified tree:** `0e74f2223ac3090b5c8afb4e67b9a4ae969dee10`
- **CANON-1:** 2.0.18
- **ROADMAP:** B0 COMPLETE; T0 NEXT
- **Active tracer:** `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`
- **Implementation candidate evidence:** PR #40 head `1f80fcb294f34ba0959cb58bbefa78263716eaee`; exact-head CI run `40278579711` succeeded. PR #40 remains non-authoritative and blocked until this approved planning amendment and its prerequisites are merged and re-gated.

No canonical authority change is required by this amendment.

### Governing contracts

| Contract | Version | T0-01 use |
| --- | ---: | --- |
| CANON-1 | 2.0.18 | Selects the installed canonical suite |
| TEN-1 | 2.0.1 | Membership proof, tenant isolation, RLS/index rules and explicit tenant-PK exception criteria |
| IAM-1 | 4.1.3 | Trusted active Session, persisted organization persona and `evt.event.create` authorization |
| IAM-2 | 1.5.0 | Invitation/customer-role-grant sovereignty only |
| EVT-1 | 3.0.0 | Registered event vocabulary |
| EVT-2 | 3.0.0 | Canonical Event resource and `create_event` behavior |
| ERR-1 | 2.0.0 | Canonical errors and information hiding |

## 4. Technical baseline

Retain:

- Elixir 1.20.4
- Erlang/OTP 29.1.2
- PostgreSQL 18.6
- Phoenix 1.8.16
- Phoenix LiveView 1.2.13
- AshPhoenix 2.3.25
- Postgrex 0.22.4
- SimpleSat 0.1.4

Amend:

- **Ash 3.36.1 → 3.37.2**
- **AshPostgres 2.15.1 → 2.15.2**
- **ash_sql 0.8.4 accepted as required transitive resolution for AshPostgres 2.15.2**

No other direct platform dependency upgrade is approved by this amendment.

## 5. Ash capability/version decision

### PREREQUISITE / ADOPT — Ash 3.37.2 + AshPostgres 2.15.2

The previous approved combination can no longer satisfy the repository security gate. Predecessor CI run `40273689321` reported MEDIUM advisories affecting Ash 3.36.1 and AshPostgres 2.15.1, including tenant/multitenancy-sensitive relationship and upsert behavior:

- Ash 3.36.1: `EEF-CVE-2026-114214` / `CVE-2026-114214` / `GHSA-g2h4-xp57-q863`.
- AshPostgres 2.15.1: `EEF-CVE-2026-115627` / `CVE-2026-115627` / `GHSA-gr2r-f49c-9gm2`.
- AshPostgres 2.15.1: `EEF-CVE-2026-115635` / `CVE-2026-115635` / `GHSA-36hg-wwp2-fg8w`.

Ash 3.37.2 and AshPostgres 2.15.2 are therefore adopted as a **security prerequisite**, not as feature scope. Do not revert merely to match stale v0.1.4.

### Capability posture

The upgrade does **not** approve newly available Ash 3.37 APIs, DSL constructs, authorization mechanisms, transaction mechanisms or architectural patterns. Existing T0-01 semantics remain locked.

Existing decisions remain:

- Ash core — ADOPT.
- AshPostgres — ADOPT.
- Ash policies — ADOPT.
- attribute multitenancy — ADOPT.
- `Ash.transact/3` for the integrated T0-01 effect boundary — ADOPT.
- AshPhoenix for new T0-01 behavior — DEFER; this increment has no new Phoenix/LiveView/API boundary.
- SimpleSat 0.1.4 — ADOPT as previously approved.
- PicoSAT — DEFER.

### Resolver discipline

TICK-54 MUST minimize dependency movement. Intended direct changes are Ash 3.37.2 and AshPostgres 2.15.2. AshPostgres 2.15.2 requires Ash >= 3.37.1 and ash_sql >= 0.8.4, therefore ash_sql 0.8.4 is accepted as necessary transitive movement.

Additional transitive movements, including any changes to `crux`, `igniter`, `sourceror`, `spark`, `spitfire` or `splode`, are not blanket-approved. Each must be demonstrated as resolver-required or retained at its existing compatible version. Generated UsageRules/agent-skill changes are permitted only when attributable to the approved dependency resolution.

### REJECT

- reverting to known-vulnerable Ash 3.36.1 / AshPostgres 2.15.1 merely to match v0.1.4;
- hiding the dependency upgrade inside TICK-25;
- opportunistically adopting Ash 3.37 features;
- unrelated dependency upgrades;
- arbitrary resolver churn without evidence;
- environment-dependent Ash versions;
- maintaining two supported Ash baselines.

## 6. Reference repositories

- **Store_Blueprint_Hardening:** verified `main` `52e9166c2905ffc756c874860736ca014616249d`; dependency/security evidence and UUIDv7 resource-ID patterns are **REFERENCE_ONLY**. It is not Ticketing tenant authority and cannot grant the TEN-1 exception.
- **LiveFrames:** verified `main` `547df7da02cd090e049a9b61d172d27a937f0bb4`; **NOT_APPLICABLE** to this backend dependency-security and tenant-PK amendment.

## 7. Decision classification

### CONTRACT_LOCKED

Unchanged:

- TEN-1 membership proof precedes other tenant business-row reads.
- Candidate `org_id` is not proven tenant authority before membership proof.
- Failed proof preserves hide-existence behavior.
- One outer `Ash.transact/3` effect boundary spans membership proof through Event insert.
- Post-proof User, Session and role liveness remain required.
- The organizer persona is persisted-evidence-derived and transaction-local.
- IAM-1 owns `evt.event.create`; only canonical permitted human organization roles may satisfy it.
- Session raw token/token_hash is outside T0 application behavior; Session remains read-only.
- TEN-1 tenant index isolation and its exception criteria remain authoritative.
- RLS/FORCE-RLS and constrained runtime-role isolation remain required.
- EVT-2 draft Event invariants and ERR-1 error semantics remain unchanged.

### IMPLEMENTATION_LOCKED

This amendment locks:

- Ash 3.37.2;
- AshPostgres 2.15.2;
- required ash_sql 0.8.4 transitive resolution;
- TICK-54 as a separate security prerequisite before TICK-25 merge;
- the exact TEN-1 physical-PK exception in section 11;
- preservation of org-first tenant natural/domain identities;
- no global ID-only authorization path.

### IMPLEMENTATION_FREE

Subject to all locked rules:

- exact prerequisite branch/commit structure;
- exact test-helper implementation;
- exact generated migration filenames;
- exact PostgreSQL catalog-query mechanics used to prove index order;
- internal fixture helper shape;
- dependency-resolution command sequence;
- mechanical UsageRules regeneration attributable to the approved versions.

### AUTHORITY_GAP

None known. A new semantic contradiction discovered during implementation stops affected work.

## 8. Scope and non-goals

### In scope

- `Ticketing.Identity` Ash Domain resources for global `User`, tenant `OrgMembership`, tenant read-only T0 `Session`, and tenant `OrgRoleAssignment`.
- Governed read/probe interfaces required by the later integrated Event effect.
- `Ticketing.Events` Event resource and `create_event` action in downstream TICK-26 only.
- One outer `Ash.transact/3` boundary from membership proof through Event insert.
- IAM-1 `evt.event.create` authorization from verified persisted organization persona.
- Existing owner/runtime split, grants, TenantContext, Repo hook and FORCE-RLS substrate reuse.
- Required positive, negative, cross-tenant, rollback, race and transaction-order evidence.
- Separate TICK-54 secure dependency prerequisite.
- The explicit tenant-PK exception described below.

### Explicit non-goals

- Reworking owner/runtime DB separation, runtime grants, TenantContext, Repo hook or generic RLS substrate.
- AuthIdentity, authentication providers, credentials, passwords, magic links, OAuth, login UI or Session issuance.
- Session issuance, refresh, rebind, revoke, `last_seen` mutation or lifecycle events.
- Reading, comparing, returning or accepting raw Session credentials/token hashes.
- Production role-grant/activation convenience APIs.
- `create_occurrence`, `publish_event`, publication CAS/outbox, pricing, offers, inventory, quotes, orders, payments, tickets, ledger, UI or API work.
- Composite-PK redesign while the approved TEN-1 exception predicates remain satisfied.
- Any dependency upgrade beyond the approved security prerequisite and resolver-required transitives.

## 9. Resource ownership and interfaces

### `Ticketing.Identity`

Owns:

- global non-PII `User`;
- tenant `OrgMembership`;
- tenant read-only T0 `Session`;
- tenant `OrgRoleAssignment`.

Required T0 interfaces are limited to governed User liveness, matching membership proof, post-proof Session liveness, and post-proof active role-assignment reads.

Authentication/session infrastructure supplies authoritative `user_id` and `session_id`. Caller `org_id`, `active_scope` and `active_role` are selectors.

The membership probe is the only tenant business-row read permitted before proof in the integrated flow. T0 exposes no completed-transaction organizer persona.

Session remains read-only. T0 does not issue, refresh, rebind, revoke, mutate `last_seen`, emit Session lifecycle events, or receive/read/compare/derive/return raw token/token_hash.

Production adds no Session issuance or role-grant/activation convenience API.

### Test setup

Pre-existing User, Membership, Session and role state may be seeded only through the narrow owner/test fixture boundary. That boundary is not a production API and does not authorize production caller-supplied identifiers.

### `Ticketing.Events`

Owns tenant Event and the complete governed `create_event` effect. Events consumes approved Identity interfaces and does not query Identity tables directly.

## 10. Tenancy, actor and RLS invariants

The existing TICK-24 substrate remains the implementation baseline.

The outer transaction establishes candidate `org_id` in transaction-local tenant context. Before proof, that value may authorize only the matching TEN-1 OrgMembership probe. Successful proof promotes the same UUID from candidate selector to proven organization context for the remainder of that transaction.

The transaction MUST NOT:

- clear and re-establish tenant context between proof and authorization;
- change to another organization;
- permit User/Session/Role/Event business-row access before membership proof;
- permit another tenant's data to satisfy liveness or capability checks.

Tenant resources remain protected with RLS and FORCE RLS under the constrained runtime role. Cross-tenant absence remains information-hiding behavior, not a global existence oracle.

## 11. Explicit TEN-1 tenant primary-key exception

### Canonical rule

TEN-1 v2.0.1 requires tenant-table PRIMARY KEY and UNIQUE constraints to include `org_id` first unless an explicit exception is granted. TEN-1 permits an exception only where the identifier is unguessable, server-generated and never client supplied, and its uniqueness is not tenant-observable at a system boundary. The exception must be explicit.

### ADOPT — resource-specific exception

This JIP explicitly grants that exception to exactly these three physical primary keys:

- `identity_org_memberships(org_membership_id)`
- `identity_sessions(id)`
- `identity_org_role_assignments(role_assignment_id)`

No other current or future tenant resource inherits this exception.

### Required predicates

For all three excepted keys:

- production generation MUST use the database `uuidv7()` default;
- the Ash PK attribute MUST remain non-writable through production actions/interfaces;
- no tenant/client production interface may supply the PK;
- global PK uniqueness MUST NOT become a tenant authorization mechanism;
- read-by-PK still requires correct tenant context/RLS;
- no tenant-visible global uniqueness oracle may be introduced.

The TICK-25 test-only owner fixture may inject deterministic identifiers for fixtures. This is outside the production/client boundary and MUST remain test-only.

### Required org-first identities remain

The exception does not relax these tenant indexes:

- Membership: `(org_id, org_membership_id)`
- Membership: `(org_id, user_id)`
- RoleAssignment: `(org_id, user_id, role)`
- Session: `(org_id, id)`

Their exact catalog order MUST be verified.

### Future foreign-key posture

The exception applies only to the physical PK constraints. It does not waive TEN-1 requirements for tenant-to-tenant relationships or foreign keys. A future tenant relationship referencing one of these resources MUST carry the tenant dimension required by TEN-1; a globally unique UUID alone must not create a cross-tenant relationship path.

### Tenant-observable collision posture

TICK-25 exposes no tenant-invokable production create path for these resources. If later work introduces production issuance, creation, import, mutation, replay or another boundary that could expose uniqueness behavior, that work MUST re-Grill the TEN-1 exception and implement the contract's required masked/audited behavior before exposure.

### Fallback

If final evidence fails any exception predicate, the exception MUST NOT be silently assumed. Affected work stops and re-Grills a composite-PK design.

## 12. Persistence and database invariants

TICK-25 MUST retain:

- global User storage outside tenant RLS semantics;
- tenant `org_id` on Membership, Session and RoleAssignment;
- database-generated UUIDv7 physical PKs as explicitly excepted above;
- required org-first composite tenant identities;
- canonical nullability and liveness fields;
- required relationships/FKs;
- RLS and FORCE RLS;
- constrained runtime grants;
- owner/runtime separation;
- database-owned defaults/timestamps where governed.

Generated migrations are implementation evidence and MUST be manually reviewed.

Ordinary runtime domain CRUD remains Ash-native. Direct Repo/Ecto/raw-SQL domain bypass is prohibited; low-level owner/Repo mechanics remain limited to infrastructure or the governed test-fixture boundary.

## 13. Transactions, concurrency, idempotency and errors

TICK-25 itself introduces no multi-resource business effect.

TICK-26 later retains one outer `Ash.transact/3` boundary covering:

```text
membership proof
→ User/Session/role liveness
→ persisted persona
→ IAM authorization
→ Event insert
```

Deterministic evidence MUST prove membership proof precedes other tenant business reads and the operation remains on the same PostgreSQL backend transaction. Tenant context must clean up after commit, rollback, exception and pooled-connection reuse.

Do not invent stronger concurrent Session/role-revocation linearization. No generic idempotency/replay contract is introduced. Database constraints remain authoritative for uniqueness races. Preserve TEN-1/IAM-1/EVT-2/ERR-1 error behavior and information hiding.

## 14. Event, outbox, jobs, audit and observability

T0-01 ends at one tenant-owned draft Event creation. No Event publication event, outbox, background job or dispatcher is introduced.

Observability must not expose raw `org_id`, `user_id`, `session_id`, credentials or token hashes in telemetry labels or logs.

TICK-54 emits no domain event. Dependency-security evidence consists of exact dependency diff, clean `hex.audit`, generated-code check, tests/CI, Plane closure evidence and post-merge main verification.

## 15. TICK-54 prerequisite execution

TICK-54 MUST be implemented separately from TICK-25.

Required sequence:

1. start from freshly verified `main`;
2. change only the approved secure dependency baseline and required generated UsageRules material;
3. minimize transitive lock movement;
4. run dependency/security and generated-code checks;
5. confirm no unexpected migration/schema/snapshot drift;
6. run all applicable repository gates;
7. open a dedicated PR;
8. independently review the exact diff and exact-head CI;
9. merge only after user merge authorization;
10. verify post-merge CI on the resulting `main` SHA;
11. close TICK-54 only when evidence is recorded.

No database schema/data migration is expected solely because of TICK-54. If Ash codegen reveals generated schema/migration/snapshot changes attributable to the version change, stop for targeted re-Grill before merge.

Do not roll back to the known-vulnerable versions. If the selected secure combination breaks governed behavior, stop and select another patched supported combination under a targeted re-Grill.

## 16. Required tests and verification

### TICK-54

Require:

- `mix hex.audit` clean;
- UsageRules sync clean;
- minimum necessary dependency resolution inspected;
- `mix ash.codegen --check` or repository equivalent clean;
- no unexpected migration/snapshot/schema drift;
- formatting and warnings-as-errors checks;
- `mix check`;
- `mix precommit`;
- `mix check.types`;
- canonical authority verification;
- isolated PostgreSQL-backed tests where applicable;
- existing tenant/RLS/transaction tests remain green;
- exact-head CI green;
- post-merge `main` CI green;
- exact diff independently reviewed.

### TICK-55 / TICK-25

Require positive/structural evidence that:

- all three physical PKs are database-generated UUIDv7;
- production PK attributes are non-writable;
- no production T0 write interface accepts them;
- all four required org-scoped unique indexes exist in exact catalog order;
- same-tenant reads succeed under correct tenant context;
- cross-tenant reads are hidden/rejected as governed;
- Session remains read-only;
- raw token/token_hash remains outside the T0 interface surface;
- deterministic identifier injection remains isolated to test-owner infrastructure.

Require negative evidence that:

- wrong tenant cannot retrieve another tenant's Membership, Session or RoleAssignment;
- missing tenant context exposes no tenant rows;
- global UUID alone is insufficient to authorize/read a tenant resource;
- no production create/update/destroy interface is accidentally exposed;
- no Event/TICK-26 behavior enters TICK-25.

All approved T0-01 positive, negative, cross-tenant, transaction-continuity, rollback and race tests remain required downstream.

## 17. Documentation impact

### Planning/governance

**CREATE**

- `planning/jips/JIP-T0-01_v0.1.5.md`
- `planning/specs/SPEC-T0-01_v0.1.4.md`

**UPDATE after planning merge**

- TICK-22 governing packet reference;
- TICK-25 governing packet reference;
- TICK-54;
- TICK-55;
- affected downstream ticket references where they name the superseded packet.

### TICK-54 derived implementation docs

**UPDATE**

- `ticketing/docs/platform/runtime.md`
- `ticketing/docs/platform/testing-and-quality-gates.md`

Those documents currently describe an older merged implementation baseline. TICK-54 closure must reconcile them to the actual merged secure baseline and fresh verification evidence. They remain derived documentation and cannot create semantics.

### Existing T0-01 documentation impact retained

**UPDATE**

- `ticketing/docs/README.md`
- `ticketing/docs/platform/runtime.md`
- `ticketing/docs/platform/database.md`
- `ticketing/docs/platform/testing-and-quality-gates.md`

**CREATE**

- `ticketing/docs/platform/tenancy-and-authorization.md`
- `ticketing/docs/domains/identity/README.md`
- `ticketing/docs/domains/events/README.md`
- `ticketing/docs/handoffs/T0-01.md`

The final handoff must identify the merged secure dependency baseline and explicit TEN-1 PK exception.

## 18. Risks and stop conditions

Stop and re-Grill if:

- canonical authority, manifest, ROADMAP or tracer changes materially;
- a security-fixed dependency combination requires a semantic change;
- Ash 3.37 changes alter locked authorization/transaction/tenant behavior;
- TICK-54 generates unexpected schema/migration drift;
- any TEN-1 exception predicate cannot be proven;
- a production write interface begins accepting an excepted PK;
- global uniqueness becomes tenant-observable;
- a tenant relationship would rely on ID-only cross-tenant linkage;
- TICK-25 requires Event behavior;
- TICK-26 requires reopening a locked TICK-25 choice.

## 19. Sequencing after approval

1. Merge this JIP/spec planning amendment after independent planning review and explicit user merge authorization.
2. Resolve TICK-55 as the approved explicit TEN-1 decision; no schema redesign is authorized while exception predicates remain satisfied.
3. Implement TICK-54 as a separate security-baseline prerequisite PR.
4. Independently review and merge TICK-54 after user authorization.
5. Verify post-merge `main` CI.
6. Rebase PR #40 onto the new secure `main` baseline.
7. Remove duplicate dependency/UsageRules changes from PR #40 where inherited from TICK-54.
8. Re-verify main/CANON/manifest/ROADMAP/tracer/JIP/spec/Plane state.
9. Run a fresh full-diff independent review of TICK-25.
10. Require fresh exact-head CI.
11. Merge TICK-25 only after DoD/evidence pass and explicit user merge authorization.
12. Only then freshness-gate TICK-26.

## 20. Definition of Done for this amendment

The planning amendment is accepted when:

- this JIP is explicitly approved by the user;
- SPEC-T0-01 v0.1.4 is accepted as its subordinate derivative;
- the planning artifacts merge to verified `main`;
- Plane references are refreshed to the current packet;
- no unresolved authority gap remains.

T0-01 itself remains open until its implementation, independent review, CI, documentation and handoff requirements are complete.
