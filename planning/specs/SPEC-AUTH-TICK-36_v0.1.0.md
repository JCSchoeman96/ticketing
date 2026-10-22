# SPEC-AUTH-TICK-36 v0.1.0 — Trusted active-session consumption for T0 organizer authorization

- **ID:** SPEC-AUTH-TICK-36
- **Version:** 0.1.0
- **Status:** APPROVED
- **Approved:** user instruction on 2026-10-22 — `Accepted`
- **Nature:** noncanonical authority-repair design record; this document does not create Ticketing semantics
- **Plane:** TICK-36 — `[AUTHORITY GAP] Define minimal org Session bootstrap after membership proof`
- **Affected downstream work:** TICK-25 and downstream TICK-26+
- **Repository baseline:** `c3068a7c3f5f7192d1bc354d8bd6f4f138b01540`
- **Baseline tree:** `843023aed0f56356dee877d4d1480afc28e88578`
- **Installed CANON:** CANON-1 `2.0.17`
- **Installed governing contracts:** TEN-1 `2.0.1`, IAM-1 `4.1.2`, IAM-2 `1.5.0`, EVT-1 `3.0.0`
- **Current downstream packet:** JIP-T0-01 `0.1.2` / SPEC-T0-01 `0.1.1` (stale for implementation)
- **Prior authority repair:** TICK-35 / TEN-1 `2.0.1` / PR #25
- **Freshness caveat:** PR #25 is merged and the merge signature/tree are verified, but post-merge Authority/CI runs `39775803069` and `39775803389` failed before any job step executed on two attempts. Approval permits writing the execution plan, but authority implementation and downstream READY remain gated on fresh execution evidence under the approved plan.

## 1. Problem statement

TICK-35 repaired the first bootstrap contradiction by adding TEN-1's explicit `org_membership_probe`: a system-internal, read-only, transaction-local, FORCE-RLS-constrained candidate-organization scope that may read only `IAM-1.OrgMembership` for an already-authenticated human and that grants no role/persona/session authority by itself.

The targeted downstream re-Grill exposed the next boundary problem.

Installed IAM-1 `4.1.2` requires all of the following for T0 tenant capability authorization:

- an **active organization persona**;
- `aal1` means an **authenticated session**;
- authorization liveness requires active `User`, active `OrgMembership`, and active `Session`;
- `auth_context` carries a `session_id`;
- when an active org persona is selected, `org_membership_id` is the immutable UUIDv7 of the selected active membership;
- each request carries an explicit `active_scope` and `active_role`, and authorization is evaluated against that active persona only;
- Sessions bind `org_id` through `sign_in_with_org` after active membership validation.

At the same time, IAM-1's Session resource requires persisted session state including `id`, `org_id`, `user_id`, `token_hash`, `status`, `created_at_utc`, `expires_at_utc`, optional `revoked_at_utc`, and optional `last_seen_at_utc`.

T0-01 deliberately does not implement authentication-provider flows, AuthIdentity, password, magic-link, OAuth, service-token issuance, login UI, or full session management. Its prior packet accepted only a trusted already-authenticated `user_id` plus explicit `org_id`, which cannot prove IAM-1 Session liveness or the required active persona.

A naive fix would make T0 issue a new Session after membership proof. That is not acceptable from the installed authority:

- IAM-1 does not define a complete T0 `sign_in_with_org` creation interface, token-generation/hash rule, TTL rule, or trusted-upstream `auth_strategy` mapping;
- inventing those in a JIP or implementation would create authentication semantics below canonical authority;
- EVT-1 `3.0.0` explicitly quarantines `ticketing.iam.session.created.v1` and `ticketing.iam.session.revoked.v1` as deferred event-registry debt for T0 and records that **T0 does not emit** those events.

The narrow repair therefore must not turn T0-01 into a session issuer.

## 2. Recommended authority direction

Preserve the T0 tracer boundary: T0 begins with an already-authenticated organizer supplied by a trusted authentication/session boundary.

Define one narrow canonical consumption rule:

> T0 organizer authorization MAY consume an already-issued canonical IAM Session identified by an authoritative `session_id` supplied by the trusted authentication boundary. T0 MUST NOT issue, rebind, refresh, revoke, or otherwise mutate that Session and MUST NOT authenticate a raw session token. After TEN-1 membership proof succeeds, T0 MUST validate the persisted Session and construct the active organization persona from persisted IAM state. The session identifier is a trusted authentication result, not a client-authored grant of tenant or role authority.

This direction keeps provider/token/session issuance outside T0 while satisfying IAM-1's active-session/persona liveness requirement.

## 3. Required IAM-1 successor semantics

The intended successor is IAM-1 `4.1.3`, subject to repository tooling confirming the identity is free and valid.

The successor should add a machine-testable T0 trusted-session consumption policy under IAM authorization/org-selection authority. Exact JSON placement may follow current contract structure, but the semantics below must be explicit.

### 3.1 Boundary identity and trust

Define a stable policy identity such as `t0_trusted_active_session`.

The policy MUST state:

- caller boundary is trusted authentication/session infrastructure, not a public client;
- the trusted boundary supplies authoritative `user_id` and `session_id` only after authenticating the underlying session credential;
- T0 receives no raw session token and MUST NOT compare or derive `token_hash`;
- `session_id`, `user_id`, candidate `org_id`, requested `active_scope`, or requested `active_role` individually grant no authority;
- T0 authorization is derived only from persisted canonical IAM records after required checks;
- caller-supplied/fabricated role lists remain non-authoritative.

### 3.2 Ordering with TEN-1 membership proof

For an explicit candidate `org_id`, the required T0 order is:

1. trusted boundary supplies authoritative human `user_id` + `session_id`;
2. caller supplies explicit candidate `org_id` and requested active persona selector;
3. execute TEN-1 `org_membership_probe` exactly as installed;
4. require active/non-revoked membership matching `(org_id, user_id)`;
5. take the persisted `org_membership_id` as membership proof;
6. only after membership proof succeeds, read the candidate-org Session and role assignments;
7. validate active Session liveness and identity binding;
8. validate the requested active org role against active persisted `OrgRoleAssignment` state;
9. construct the active organization persona;
10. only then evaluate the requested T0 capability.

No Session or role read is permitted inside the pre-proof TEN-1 membership probe.

### 3.3 Session matching and liveness

After membership proof, T0 MUST validate one persisted Session row under the proven organization tenant with all of the following:

- `Session.id == authoritative session_id`;
- `Session.user_id == authoritative user_id`;
- `Session.org_id == proven org_id`;
- `Session.status == "active"`;
- `Session.revoked_at_utc IS NULL`;
- `Session.expires_at_utc > evaluated_at_utc`;
- session expiry comparison uses the platform's authoritative UTC database-time source for the authorization transaction.

A Session that is absent, expired, revoked, inactive, belongs to another user, or is not visible in the proven tenant is not a live authenticated Session for T0.

T0 MUST NOT update `last_seen_at_utc`, refresh expiry, rotate credentials, rebind `org_id`, or otherwise mutate Session state as part of this authorization check.

### 3.4 Active persona fields

IAM-1 already requires an explicit `active_scope` and `active_role`, but its current `auth_context_shape` does not make those fields explicit. The successor should close that shape gap by defining them directly in the canonical auth context.

For T0 tenant capabilities:

- `active_scope` MUST be `org`;
- `active_role` is a selector, not a grant;
- the requested `active_role` MUST resolve to exactly one active/non-revoked same-org `OrgRoleAssignment` for the authoritative `user_id`;
- authorization MUST evaluate the capability against `active_role`, not merely against the presence of some other role in a broader roles array;
- `auth_context.actor.org_membership_id` MUST equal the proven persisted membership UUID;
- `auth_context.actor.org_id` MUST equal the proven Session/membership organization;
- `auth_context.actor.user_id` MUST equal the authoritative authenticated user;
- `auth_context.session_id` MUST equal the validated persisted Session id;
- platform/support personas remain invalid for T0 tenant capabilities unless a separately governed policy explicitly allows them.

The actor may carry the set of verified active roles for informational/internal use, but only the explicit verified `active_role` defines the active persona for the current capability decision.

### 3.5 User and membership liveness

Preserve existing IAM-1 liveness rules:

- `User.status == "active"`;
- `OrgMembership.status == "active"` and membership is not revoked;
- Session satisfies the exact liveness rules in §3.3;
- requested role assignment is active and non-revoked.

No stale caller claim may override persisted liveness.

### 3.6 T0 Session operations are read-only

The policy MUST explicitly forbid T0 from:

- issuing a Session;
- implementing `sign_in_with_org` session issuance;
- generating a raw session credential;
- deriving or verifying `token_hash`;
- refreshing a Session;
- extending `expires_at_utc`;
- changing `org_id` or `user_id` on a Session;
- revoking a Session;
- writing `last_seen_at_utc`;
- emitting `ticketing.iam.session.created.v1`;
- emitting `ticketing.iam.session.revoked.v1`.

Those behaviors belong to a later governed IAM authentication/session-management increment.

### 3.7 Failure behavior

Failures MUST be deterministic and non-enumerating:

- membership-probe failure continues to use TEN-1 hide-existence semantics and must not promote candidate org state;
- after membership succeeds, missing/invalid/inactive/expired/revoked/mismatched Session MUST fail authentication uniformly as `ERR_UNAUTHENTICATED` using IAM-1's session-invalid/expired posture, without revealing whether another tenant/session exists;
- missing/inactive/revoked requested role or a role that does not authorize the capability MUST fail as `ERR_FORBIDDEN` under ordinary same-tenant authorization semantics;
- no failure path may mutate Session, membership, roles, Event state, or authorization context;
- internal diagnostics may retain stable reason data only where existing ERR/OBS policy permits it.

### 3.8 Transaction, RLS and concurrency posture

The T0 resolver remains one governed authorization transaction where practical:

- TEN-1 candidate membership proof uses the installed constrained runtime role and FORCE RLS;
- after membership proof, all Session/role reads occur under the same proven `org_id` tenant boundary;
- no owner/superuser/BYPASSRLS path is allowed;
- no session-scoped PostgreSQL GUC is allowed;
- no process-dictionary tenant truth is allowed;
- no Session write means there is no new Session CAS/idempotency surface in T0;
- authorization reads are time-of-use liveness checks immediately before the governed domain action they authorize.

## 4. EVT-1 relationship

EVT-1 `3.0.0` already records both IAM Session events as `DEFERRED_EVENT_REGISTRY_DEBT` for T0, including the quarantine claim that T0 does not emit them.

The intended repair MUST preserve that fact.

Therefore:

- no EVT-1 successor is proposed by this repair;
- IAM-1's existing registered Session event declarations are not removed or redefined;
- the new IAM-1 T0 consumption policy states that this T0 path is read-only and emits neither Session event;
- a focused cross-contract authority test should prove the IAM policy and EVT-1 T0 quarantine remain coherent.

If review finds that IAM-1 structurally requires every Session read/authorization to emit an event, or that EVT-1's quarantine cannot coexist with the new policy, stop and widen the authority repair explicitly rather than silently modifying EVT-1.

## 5. IAM-2 and provider-auth relationship

IAM-2 remains unchanged.

Its proof-token rules may serve as design evidence for safe token handling, but they MUST NOT be imported as Session semantics merely because both resources contain hashes/expiry fields.

T0 does not implement:

- AuthIdentity;
- password authentication;
- magic-link authentication;
- OAuth;
- service-token authentication;
- raw Session token issuance/verification;
- proof-token issuance/consumption;
- login/session-management UI.

The trusted upstream authentication/session boundary owns those concerns until a later approved IAM increment implements them inside Ticketing.

## 6. Paired test-gate requirements

The IAM-1 successor should add a P0/must gate for the trusted T0 Session consumption boundary. At minimum the paired gate must lock:

1. policy enabled and stable policy id;
2. trusted authentication/session caller boundary only;
3. authoritative `user_id` and `session_id` required;
4. raw session token unavailable to T0;
5. TEN-1 membership proof required before Session/role reads;
6. Session exact `id`, `user_id`, and `org_id` matching;
7. Session `status=active`;
8. `revoked_at_utc=nil`;
9. `expires_at_utc > authoritative evaluated_at_utc`;
10. Session mutation forbidden;
11. Session event emission forbidden in T0;
12. active `User` and active/non-revoked membership required;
13. `active_scope=org` for T0 tenant capabilities;
14. requested `active_role` must be backed by active same-org persisted role assignment;
15. capability evaluation uses the explicit active persona;
16. platform/support persona rejection for T0 tenant capabilities remains preserved;
17. session failures map uniformly to `ERR_UNAUTHENTICATED`;
18. no direct client role/session claims can grant authority.

A focused repository pytest should load only manifest-selected installed canonical bundles and additionally prove:

- the selected IAM-1 policy/gate exactly match;
- EVT-1 still quarantines both IAM Session events for T0 as non-emitted;
- IAM-2 selection remains unchanged;
- TEN-1 `org_membership_probe` remains selected and unchanged;
- no global-resource or RLS weakening occurs.

## 7. Intended release identities

Subject to tooling confirmation:

- IAM-1 `4.1.3` succeeding IAM-1 `4.1.2`;
- CANON-1 `2.0.18` succeeding CANON-1 `2.0.17`.

No TEN-1, IAM-2, EVT-1, ERR-1, or OBS-1 successor is intended by this narrow repair.

CANON generation must use the repository's deterministic successor tooling with IAM-1 `4.1.3` as the only explicit candidate. All unrelated member versions, paths, hashes, membership statuses, and exclusions must remain unchanged.

## 8. Release/installation evidence

If this design is approved, execution must follow `authority/AGENTS.md` and `authority/README.md`:

- author IAM-1 successor from exact immediate source `4.1.2`;
- add focused semantic RED test before successor installation;
- build IAM-1 twice and byte-compare ZIP + all members;
- validate contract candidate and release set;
- generate CANON successor through repository tooling only;
- build CANON twice and byte-compare;
- validate CANON candidate and closure;
- install exact IAM + CANON bytes together;
- regenerate extracted copies and manifest;
- reproduce generated CANON files byte-for-byte;
- run full authority pytest, manifest/CANON verification and strict reconciliation;
- run `mix contract.authority` and required application-side verification without dependency movement;
- open an authority PR and stop for independent exact-diff review;
- require exact-head CI and post-merge CI before authority closure.

The current zero-step post-merge CI failure on baseline `c3068a7c...` must be resolved or independently demonstrated as a GitHub platform/account execution issue before downstream implementation receives READY status.

## 9. Downstream JIP-T0-01 v0.1.3 consequence

Only after this authority repair is merged and fresh should JIP-T0-01 `0.1.3` become approval-ready.

The intended downstream amendment is:

- retain global `User`, tenant `OrgMembership`, tenant `OrgRoleAssignment`;
- add the minimum tenant `Session` resource/schema required to validate persisted canonical Session liveness;
- do **not** expose T0 Session create/refresh/rebind/revoke actions;
- production organizer resolution consumes authoritative `user_id + session_id` from the trusted authentication/session boundary plus explicit candidate `org_id` and active persona selector;
- execute TEN-1 membership probe first;
- after proof, validate User + Session + requested role under proven tenant;
- construct an explicit active org persona with persisted `org_membership_id`, `session_id`, `active_scope`, and `active_role`;
- authorize Event actions against that active persona only;
- do not emit IAM Session events;
- keep AuthIdentity/provider/token/login UI work out of T0-01;
- tests may seed prerequisite Session rows only through explicitly justified test infrastructure; T0 must not introduce a fake production Session-issuance API.

TICK-25 should be decomposed or updated only after JIP/spec approval. TICK-26 remains blocked until the corrected IAM substrate is merged and verified.

## 10. Decision classes

### CONTRACT_LOCKED

- TEN-1 `org_membership_probe` scope and ordering;
- active org persona requirement;
- active User/Membership/Session liveness requirement;
- stable persisted `org_membership_id` as org-persona identity;
- explicit active scope/role requirement;
- T0 tenant capabilities are human org-persona capabilities and exclude platform/support personas;
- Session is tenant-scoped;
- EVT-1 states T0 does not emit IAM Session created/revoked events.

### Proposed authority correction to become CONTRACT_LOCKED only after accepted successor

- trusted authoritative `session_id` consumption boundary;
- exact Session identity/liveness checks including expiry/revocation;
- explicit auth-context `active_scope` / `active_role` shape;
- T0 Session read-only/no-event rule;
- uniform session-validation failure mapping.

### IMPLEMENTATION_LOCKED after JIP approval

- Ash-native Identity resource/read interfaces;
- reuse merged TEN-1/TenantContext/FORCE-RLS transaction substrate;
- no second GUC path;
- no generic direct Repo runtime IAM reads;
- no T0 Session issuance endpoint/action.

### IMPLEMENTATION_FREE

- exact private module/function names;
- exact Ash read action names and code interfaces;
- internal struct shape where it does not change canonical auth-context semantics;
- test helper organization.

### AUTHORITY_GAP until successor is accepted

- exact trusted Session consumption/liveness/persona boundary described by this spec.

## 11. Non-goals

This repair does not authorize:

- Session issuance;
- `sign_in_with_org` implementation;
- raw session-token generation or verification;
- token hashing/pepper selection for Session credentials;
- Session refresh/rebind/revoke behavior;
- IAM Session event production in T0;
- AuthIdentity implementation;
- password/magic-link/OAuth/service-token implementation;
- AshAuthentication adoption;
- UI/login/session-management screens;
- support impersonation or break-glass behavior;
- Event lifecycle changes;
- dependency upgrades;
- TICK-25/TICK-26 implementation before the authority and planning gates complete.

## 12. Definition of done for TICK-36 authority phase

TICK-36 is complete only when:

- the design is explicitly accepted;
- the exact successor authority is authored, deterministically built, validated, installed, and CANON-selected;
- dependency closure and canonical reconciliation are clean;
- independent exact-diff review passes;
- exact-head and post-merge CI actually execute and pass;
- no unrelated contract member drifts;
- TICK-35/TICK-36 Plane evidence is reconciled;
- targeted re-Grill against the newly installed IAM authority finds no remaining session/persona gap;
- JIP-T0-01 `0.1.3` and SPEC-T0-01 successor are then prepared for explicit user approval;
- TICK-25 and TICK-26 remain non-READY until those approvals and freshness gates pass.

This APPROVED spec itself changes no canonical Ticketing semantics and grants no downstream READY status.