# JIP-T0-01 v0.1.3 — Tenant Organizer Authorization + Event Create

- **ID:** JIP-T0-01
- **Version:** 0.1.3
- **Status:** APPROVED
- **Approved:** explicit user approval on 2026-10-22
- **Supersedes for implementation planning:** JIP-T0-01 v0.1.2; earlier versions remain historical
- **Governing spec:** SPEC-T0-01 v0.1.2
- **Roadmap horizon:** T0 — Tenant-scoped GA pending sale
- **Increment boundary:** one authorized `EVT-2.create_event` effect that persists a tenant-owned draft Event. This increment ends after that insert.

This JIP is downstream implementation planning. Installed canonical contracts, ROADMAP, and the active T0 tracer remain higher authority. It records the user-approved packet and adds no semantics beyond that packet.

## 1. Amendment and supersession history

- **v0.1.0** was the original approved packet. It established the initial T0-01 scope and implementation decisions.
- **v0.1.1** refreshed the technical baseline. It was later found to contain planning drift, including `AuthIdentity` implementation and a narrowed documentation impact.
- **v0.1.2** corrected that drift but predates the installed TEN-1 membership-probe and IAM-1 trusted active-Session requirements. It also included Event publication before the active tracer's Occurrence step.
- **v0.1.3** incorporates the approved post-repair authority and tracer boundary. It treats the already-merged database owner/runtime split, runtime grants, `TenantContext`, Repo transaction hook, and FORCE-RLS facilities as baseline. It implements canonical organizer authorization and Event creation only. Occurrence creation and Event publication remain in the tracer's order for later work.

The repository preserves earlier JIP and spec versions. This version supersedes them only for further T0-01 implementation planning.

## 2. Objective and boundary

Use persisted canonical organizer state to authorize `evt.event.create`, then create one canonical tenant-owned draft Event. The trusted authentication/session boundary supplies authoritative `user_id` and `session_id`.

One outer governed Ash/PostgreSQL effect transaction spans the complete operation:

```text
candidate-org membership proof
→ persisted User, Session, and role liveness
→ active organization persona
→ evt.event.create authorization
→ Event insert
```

The candidate `org_id` is a selector. It does not become resolved tenant authority until TEN-1 membership proof succeeds. No resolved persona may be completed in one transaction and reused later to authorize Event creation.

The increment ends after the draft Event is created. The active tracer orders `create_event → create_occurrence → publish_event`; this JIP does not move publication ahead of Occurrence.

## 3. Verified baseline

### Repository and authority snapshot

- **Repository:** `JCSchoeman96/ticketing`
- **Verified implementation and authority-tree commit:** `f43f5bebe2a9fc13d2dd1c8c8f27a0ef7397a54a`
- **Baseline tree:** `2c4ef454de570d1c230d262cb55b0875401d6249`
- **Authority snapshot:** the installed authority files in that exact repository tree; `authority/contracts/manifest.json` SHA-256 is `f44764cd8310281b7f34a2cef6e50bb67ee659e147268a65e83a86586a842dd0`
- **ROADMAP:** B0 COMPLETE; T0 NEXT
- **Active tracer:** `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`

The repository contains the installed contract tree; this packet does not claim a separate contracts-repository commit.

### Governing contracts

| Contract | Version | Use in this increment |
| --- | --- | --- |
| CANON-1 | 2.0.18 | Selects the installed canonical suite |
| TEN-1 | 2.0.1 | Membership proof before resolved-tenant reads; hide-existence behavior |
| IAM-1 | 4.1.3 | Trusted active Session, persisted persona, `evt.event.create` capability |
| IAM-2 | 1.5.0 | Authorization policy and actor posture |
| EVT-1 | 3.0.0 | Registered event vocabulary; no publication event is emitted here |
| EVT-2 | 3.0.0 | Canonical Event resource and `create_event` behavior |
| ERR-1 | 2.0.0 | Canonical errors and information hiding |

### Technical baseline

Keep the approved, locked stack:

- Elixir 1.20.4 and Erlang/OTP 29.1.2
- PostgreSQL 18.6
- Phoenix 1.8.16 and LiveView 1.2.13
- Ash 3.36.1, AshPhoenix 2.3.25, and AshPostgres 2.15.1
- Postgrex 0.22.4

The repository manifests and `ticketing/mix.lock` remain the exact package resolution. No dependency or runtime upgrade is authorized by this JIP.

### References

- **Store Blueprint Hardening:** approved JIT reference snapshot `aab23f6afb924828a6f3b3c43bf069b304b6585e`; `REFERENCE_ONLY` for implementation evidence and `NOT_APPLICABLE` as a source of IAM/Event semantics. No reference implementation is copied into this increment.
- **LiveFrames:** approved JIT reference snapshot `9f0d2df1161a715f79c526dae49fbd4c6ca97117`; `NOT_APPLICABLE` because this increment contains no UI work.

## 4. Scope and non-goals

### In scope

- Ash resources for global `User`, tenant `OrgMembership`, tenant read-only T0 `Session`, and tenant `OrgRoleAssignment`, using canonical IAM shapes and identities.
- A governed `Ticketing.Identity` interface for the membership proof and persisted liveness/persona evidence required by `create_event`.
- A governed `Ticketing.Events` Event resource and `create_event` action.
- The single outer transaction from TEN-1 membership proof through Event insert.
- Authorization of the canonical `evt.event.create` capability using the verified persisted organization persona.
- Tenant resource migrations and database enforcement needed for these resources, using the existing owner/runtime, grants, tenant-context, Repo hook, and FORCE-RLS facilities.
- Focused positive, negative, tenant-isolation, and atomicity evidence for the approved behavior.
- The documentation impact in §13 after the implementation merges.

### Explicit non-goals

- Reimplementing owner/runtime database separation, runtime grants, `TenantContext`, the Repo transaction hook, or reusable FORCE-RLS infrastructure. These are merged T0-00/T0-01 baseline.
- `AuthIdentity`, authentication providers, credentials, passwords, magic links, OAuth, login UI, or Session issuance.
- Reading or receiving raw Session credentials or token hashes; updating, refreshing, rebinding, or revoking Session; writing `last_seen_at_utc`; or emitting Session-created/revoked events.
- `create_occurrence`, `publish_event`, publication CAS, `ticketing.event.published.v1` outbox, occurrence sales lifecycle, pricing, offers, inventory, quotes, orders, payments, tickets, or ledger behavior.
- New dependency/runtime versions, UI, dispatcher, jobs, or a generic event bus.

## 5. Decision classification

### CONTRACT_LOCKED

- TEN-1 `org_membership_probe` must prove active, non-revoked membership for the authoritative user before resolved-tenant Session, role, or Event reads.
- IAM-1 `t0_trusted_active_session` consumes the trusted `user_id` and `session_id` after membership proof and requires canonical User, Session, membership, and role liveness.
- The `evt.event.create` capability and its permitted actor/role policy come from IAM-1/IAM-2. IAM-1 permits a human organization persona with `org_owner` or `org_admin` for this capability.
- EVT-2 defines the Event resource shape and draft creation behavior.
- TEN-1/IAM-1/ERR-1 define tenant scope, hide-existence, and failure behavior.

### IMPLEMENTATION_LOCKED

- One outer governed Ash/PostgreSQL transaction contains membership proof, post-proof liveness reads, persona construction, capability authorization, and the Event insert.
- Candidate `org_id`, requested `active_scope`, and requested `active_role` are selectors only. Persisted membership/session/role proof establishes authority.
- The Events action owns the complete create effect. It may call the approved Identity interface inside the same transaction. It must not rely on a separately completed organizer-resolution transaction or expose a reusable authorization result for a later Event write.
- `Ticketing.Identity` owns the four identity resources and their governed interfaces. `Ticketing.Events` owns Event and `create_event`.
- Canonical runtime state uses Ash resources, Ash Domains, Ash actions/interfaces, and `AshPostgres.DataLayer`. Existing tenant context and FORCE-RLS facilities provide database enforcement.

### IMPLEMENTATION_FREE

Module/file layout, private policy/helper decomposition, and test fixture names may vary when they preserve the locked interfaces, transaction boundary, and canonical semantics.

### AUTHORITY_GAP

None is recorded for the approved packet. Stop and capture an authority gap if implementation or current canonical evidence contradicts a locked requirement.

## 6. Ash capability and persistence posture

- **ADOPT:** Ash core, AshPhoenix, AshPostgres, Ash authorization policies, attribute multitenancy, governed actions, and PostgreSQL constraints/RLS as defense in depth.
- **DEFER:** AshAuthentication, Ash Signals, Temporal Resources, AshStateMachine, AshOban, Reactor adoption, AshPaperTrail/AshArchival, and Ash Storage. T0 consumes an already-issued Session and creates no publication outbox.
- **REJECT:** direct Repo/Ecto/raw-SQL runtime CRUD as a domain interface, `authorize?: false` on ordinary organizer behavior, and application-side tenant filtering as a substitute for RLS.

PostgreSQL-backed canonical resources use `AshPostgres.DataLayer`. Runtime reads and writes flow through approved Ash actions and domain interfaces with actor and tenant context. Direct database access is limited to the repository's approved migration, DDL/RLS, and isolated test-fixture uses. Do not add or upgrade an architectural dependency.

## 7. Resource ownership and organizer proof

### Identity domain

`Ticketing.Identity` owns:

- global, non-PII `User`;
- tenant `OrgMembership`;
- tenant `Session`, read-only for this increment;
- tenant `OrgRoleAssignment`.

Tenant resources use canonical `org_id` tenancy, identities, relationships, nullability, and liveness. The session input is the trusted authoritative `session_id`; the T0 effect does not read a raw credential or token hash.

### Events domain

`Ticketing.Events` owns the tenant-scoped `Event` and the governed `create_event` effect. Cross-domain behavior uses approved Identity interfaces. Events code does not query Identity tables directly.

### Required order

1. Trusted authentication/session infrastructure supplies authoritative `user_id` and `session_id`. The caller supplies candidate `org_id`, requested `active_scope = org`, and requested `active_role`; none grants authority by itself.
2. Within the outer effect transaction, TEN-1 `org_membership_probe` uses its system-internal candidate-org scope to read only the matching `OrgMembership`. It must match the authoritative user and be active and non-revoked. Retain the persisted `org_membership_id`. Failed proof does not establish resolved tenant authority and stops the effect.
3. Only after proof, use the proven organization tenant for the remaining reads. Require active `User`. Load the Session by authoritative `session_id` and require exact Session ID, user ID, and proven organization matches; `status = active`; `revoked_at_utc = null`; and `expires_at_utc` later than database UTC evaluation time.
4. Require an active, non-revoked same-organization `OrgRoleAssignment` for the authoritative user and requested role. Construct the active organization persona only from authoritative IDs and persisted membership, Session, and role proof. Set `active_scope = org` and the verified `active_role`.
5. Authorize `evt.event.create` for that persona under IAM-1/IAM-2. Caller-provided roles never grant authority.
6. Create one Event in the proven tenant and commit the outer transaction. Any failure rolls back the effect.

Do not read Session, role, or Event state under an unproven candidate tenant. Do not issue a Session or return an organizer persona from a completed transaction for later authorization.

## 8. Event creation and lifecycle boundary

The only Event transition in this increment is:

```text
absent → draft
```

Use the exact EVT-2 Event shape and `EVT-2.create_event` semantics. The Event belongs to the proven organization. The canonical initial state is `draft`; database-owned timestamps and EVT-2 initial version/fence values apply; `published_at_utc` is null. The caller cannot supply the authorization persona or alter the tenant proof.

There is no public generic lifecycle update in this increment. Do not publish the Event, create an Occurrence, or create an event-publication outbox row.

## 9. Tenancy, transaction, concurrency, and errors

- Reuse the already-merged runtime-role/grant setup, `TenantContext`, Repo transaction hook, and FORCE-RLS facilities. Do not create a second tenant-context mechanism.
- Membership proof is the only operation permitted in the candidate-org probe scope. Resolved tenant context for Session/role/Event reads follows successful proof.
- The complete proof-to-insert effect uses one outer Ash/PostgreSQL transaction. This prevents a completed organizer persona from authorizing a later transaction without revalidation.
- No Event publication CAS, generic idempotency behavior, or publication replay mechanism is introduced.
- Failed membership proof preserves TEN-1 hide-existence behavior at the external boundary. After proof, invalid Session liveness uses canonical unauthenticated behavior; absent, inactive, revoked, or incapable requested role uses canonical forbidden behavior. Invalid Event input follows EVT-2/ERR-1. Do not invent error codes or disclose hidden tenant existence.
- A rejected or failed effect writes no Event. Session state remains read-only.
- Preserve request/trace context when required by the owning action and existing OBS-1 implementation. Do not create new observability vocabulary.

## 10. Migration and rollback

Add only the canonical resources required by this increment. Inspect generated AshPostgres migrations and verify canonical attributes, tenant-aware identities and foreign keys, nullability, indexes, RLS, and grants. Use the existing migration-owner flow and runtime privilege system. Do not repeat the completed owner/runtime or tenant-context work.

The outer transaction must roll back any intermediate database effect if membership, Session, role, authorization, validation, or Event insertion fails. Session remains read-only; no Session migration or mutation may create a new issuance flow.

## 11. Required implementation evidence

Implementation must use TDD and prove at least:

- valid active persisted owner/admin persona can create one draft Event;
- candidate `org_id`, requested scope, and requested role do not confer authority;
- inactive/missing/revoked membership fails before resolved-tenant Session/role/Event reads;
- the Session matches authoritative Session/user/proven organization IDs and is active, unrevoked, and unexpired at database UTC time;
- missing, mismatched, inactive, revoked, or expired Session cannot authorize creation;
- requested role must match an active, non-revoked same-organization persisted assignment;
- caller-supplied or fabricated roles cannot grant `evt.event.create`;
- cross-tenant rows remain hidden under the runtime role and FORCE RLS;
- the Event has canonical tenant ownership and draft initial values;
- a denied or failed step creates no Event and leaves Session unchanged;
- transaction-local tenant context does not leak after commit/rollback or pool reuse;
- generated resources/migrations and direct Repo/Ecto/raw-SQL use comply with the Ash-native boundary;
- normal and partitioned TEST paths use the approved PostgreSQL 18.6 owner/runtime model.

These are planning requirements only. This planning pass does not run product tests or implement behavior.

## 12. Risks and stop conditions

- Stop if the system-internal TEN-1 probe cannot remain limited to the matching membership read or is treated as resolved tenant authority before proof.
- Stop if the trusted Session boundary needs issuance, token/hash handling, Session mutation, or unapproved lifecycle behavior.
- Stop if Ash/PostgreSQL cannot keep the approved proof-to-insert flow in one outer governed transaction without bypassing the Ash boundary.
- Stop if installed authority does not determine an Event resource field, identity, error, or authorization rule required by this increment.
- Stop before pulling `create_occurrence`, `publish_event`, publication CAS/outbox, or sales lifecycle into this JIP.

Capture discoveries and blockers in Plane. Do not solve an authority gap by changing this JIP or spec without the authority workflow and explicit user approval.

## 13. Documentation impact

After implementation merges:

### UPDATE

- `ticketing/docs/README.md`
- `ticketing/docs/platform/runtime.md`
- `ticketing/docs/platform/database.md`
- `ticketing/docs/platform/testing-and-quality-gates.md`

### CREATE

- `ticketing/docs/platform/tenancy-and-authorization.md`
- `ticketing/docs/domains/identity/README.md`
- `ticketing/docs/domains/events/README.md`
- `ticketing/docs/handoffs/T0-01.md`

Documentation describes merged implementation state only and cannot create semantics. The handoff records the merged SHA, governing authority/JIP, Plane items, PRs, verification, and deferred scope.

## 14. Plane execution and Definition of Done

TICK-22 remains the existing `[JIP]` execution parent. `planning/plans/2026-10-23-t0-01-v0.1.3-to-tickets.md` records the reconciled child graph. TICK-25/TICK-26's former descriptions are stale and must not guide implementation. The old publication item is deferred because the tracer places Occurrence before publication.

All active implementation children and the independent review item remain Planning until the control tower independently reviews the exact planning PR and explicitly authorizes a later READY transition. The old publication item is canceled for this increment. The to-tickets reconciliation does not mark work READY.

The JIP is complete only when:

- all in-scope child work is implemented through governed Ash interfaces;
- the one proof-to-Event-insert transaction and all required negative/tenant/rollback evidence pass;
- migrations, RLS, actor/tenant posture, and generated output are reviewed;
- the listed documentation matches merged implementation;
- required checks and exact-head CI pass;
- independent review is clean and all child PRs are merged;
- the final handoff and Plane closeout evidence are current.

No occurrence sales lifecycle, Event publication CAS, publication outbox, or later commerce work is required for this JIP.
