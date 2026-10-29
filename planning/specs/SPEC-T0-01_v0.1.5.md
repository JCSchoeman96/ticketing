# SPEC-T0-01 v0.1.5 — Non-Bypassable Organizer Event-Create Boundary

- **ID:** SPEC-T0-01
- **Version:** 0.1.5
- **Status:** APPROVED DERIVATIVE
- **Approved basis:** JIP-T0-01 v0.1.6, explicitly approved by the user on 2026-10-29
- **Supersedes for implementation detail:** SPEC-T0-01 v0.1.4; earlier versions remain historical
- **Authority posture:** subordinate to installed canonical authority, ROADMAP, the active T0 tracer and JIP-T0-01 v0.1.6

This specification creates no new product/domain semantics. It narrows the implementation of T0-01 so the governed organizer proof and IAM authorization cannot be bypassed by a second Event persistence action or synthetic persona.

## 1. Governing flow

The only valid production path to a new Event row is:

```text
candidate org selector
→ TEN-1 membership proof
→ post-proof User liveness
→ post-proof active Session liveness on DB UTC
→ post-proof active RoleAssignment liveness
→ persisted active organization persona validation
→ IAM-1 evt.event.create authorization
→ Event insert
```

The entire sequence MUST execute inside one outer governed `Ash.transact/3` boundary and remain on the same PostgreSQL backend transaction.

The candidate `org_id` is not authoritative until Membership proof succeeds.

## 2. Single Event-create capability

`create_event` is the single canonical production capability that may result in a new Event row.

The implementation MUST NOT expose or retain any additional Ash create/persist action whose successful authorization is sufficient to insert an Event independently of the full governing flow.

A helper used by `create_event` may be private Elixir implementation detail, but it MUST NOT constitute another independently invokable Ash write/action boundary.

## 3. Persona provenance

The active organization persona is derived only from persisted evidence read and validated in the current transaction.

A transaction-local persona MAY be represented internally as data used by the current orchestration, but it MUST NOT become a transferable bearer credential for a later Event write.

The following are insufficient proof of authorization provenance:

- a map containing expected organizer fields;
- a struct with the expected type;
- a private module constructor;
- an action marked `public? false`;
- a caller-provided capability string;
- an opaque or signed token invented solely to bridge two internal write actions.

IAM authorization results may communicate success/evidence to the current orchestration, but the result MUST NOT independently authorize a subsequent mutation.

## 4. IAM ownership

IAM-1 remains the sole authority for `evt.event.create`.

Events MUST NOT duplicate the role/capability matrix.

Only canonical permitted human organization roles may satisfy the capability under an active organization persona. Platform/support personas remain denied unless higher authority explicitly governs otherwise.

No `authorize?: false` escape hatch is permitted for the Event insert.

## 5. Tenant and RLS boundary

Before membership proof, the matching OrgMembership probe remains the only permitted tenant business-row access.

After successful proof, the same organization UUID remains transaction-local tenant context through the Event insert. The implementation MUST NOT clear/re-establish or switch tenant context.

The Event insert remains subject to attribute multitenancy plus PostgreSQL RLS/FORCE RLS under the constrained runtime role.

RLS is defense in depth and does not replace organizer proof or IAM authorization.

## 6. Event persistence invariants

A successful `create_event` produces exactly one canonical tenant-owned draft Event with the existing governed invariants:

- generated UUIDv7 Event identity;
- generated public event key;
- proven `org_id` ownership;
- canonical slug/visibility/locale/taxonomy inputs;
- `status = draft`;
- `published_at_utc = nil`;
- `version = 1`;
- `lock_version = 1`;
- database-owned timestamps;
- protected tenant/identity/status/time/version/fence fields unavailable for caller authorship;
- database-enforced uniqueness for `(org_id, public_event_key)` and `(org_id, slug)`.

No Event lifecycle semantic changes are introduced.

## 7. Transaction and rollback invariants

The outer transaction MUST include all proof and authorization stages plus the final insert.

A failure at any stage MUST prevent Event creation.

Rollback behavior MUST leave no Event row and MUST NOT mutate Session state.

No generic idempotency/replay semantic is added. Database constraints remain authoritative for duplicate/concurrent uniqueness outcomes.

No stronger concurrent Session/role-revocation linearization is introduced.

## 8. Forged-persona regression gate

The TICK-63 reproducer becomes permanent negative coverage.

The final suite MUST prove:

1. a fabricated organizer persona cannot cause an Event insert;
2. no Ash action exists that can independently persist a new Event while bypassing Membership/User/Session/role proof;
3. internal/direct invocation of the nearest persistence boundary cannot convert caller-supplied actor state into authorization provenance;
4. successful creation still requires IAM-1 authorization after persisted proof;
5. removing the bypass does not weaken tenant RLS, transaction continuity or canonical Event invariants.

If the final design removes the former `persist_draft` action entirely, the regression MUST verify the absence of an equivalent alternate write capability and exercise the closest practical bypass attempt.

## 9. Existing TICK-26 acceptance evidence

All prior TICK-26 acceptance requirements remain mandatory:

- `org_owner` success;
- `org_admin` success;
- proof-before-other-business-reads ordering;
- same PostgreSQL backend transaction through insert;
- authoritative user/session/org/membership/role binding;
- Session active/non-revoked/unexpired checks using DB UTC;
- forged role denial;
- platform/support denial;
- invalid/mixed scope denial;
- cross-tenant information hiding;
- protected-field rejection/non-writability;
- canonical initial Event values;
- rollback with no Event and no Session mutation;
- database-enforced duplicate/concurrent uniqueness behavior;
- applicable tenant-context cleanup/pool-reuse evidence in the existing T0-01 sequence.

## 10. Implementation constraints

The correction MUST NOT:

- introduce a dependency upgrade;
- adopt a new Ash 3.37 capability merely for convenience;
- use ordinary runtime Repo/Ecto/raw-SQL as a domain bypass;
- use `authorize?: false` for the insert;
- create a cryptographic/process-local bearer capability protocol;
- reopen TICK-25 semantics unless a proven contradiction requires a new Grill;
- add occurrence/publication/outbox/commerce/UI/API scope.

Exact private helper and module layout is implementation-free provided no second authorization/write capability is created.

## 11. Migration and generated-state expectations

No database schema change is expected solely from this action-boundary correction.

Ash migration/resource snapshot regeneration is permitted only where required by the corrected resource/action model. Every generated delta must be manually reviewed.

Unexpected table/column/index/constraint/default/RLS/identity drift is a STOP condition.

## 12. Errors, events and observability

ERR-1 remains unchanged; no new canonical error is introduced.

Unauthorized/cross-tenant paths preserve information hiding.

Draft Event creation emits no publication event, outbox row or job.

Logs/telemetry MUST NOT expose raw `org_id`, `user_id`, `session_id`, credentials or token hashes.

## 13. Execution sequence

1. merge JIP-T0-01 v0.1.6 and this derivative spec after independent planning review, successful planning CI and explicit user merge authorization;
2. verify merged `main` freshness;
3. refresh TICK-63 and TICK-26 Plane references;
4. move TICK-26 from Blocked to Ready only if TICK-63 has an approved recovery path and no new blocker exists;
5. issue a new Builder dispatch from that exact main SHA;
6. reconcile the local/PR #45 candidate without preserving the forgeable two-action boundary;
7. start from the failing forged-persona regression and implement the minimum boundary correction;
8. run all focused and global TICK-26 verification;
9. require fresh exact-head CI and independent exact-diff review;
10. merge implementation only after explicit user authorization;
11. verify post-merge `main` and update derived implementation docs before closure.

## 14. Stop conditions

Stop for control-tower review if:

- canonical authority must change;
- IAM/EVT semantics must change;
- the implementation requires a second Event write action;
- an authorization result must become a bearer capability;
- same-transaction continuity cannot be preserved;
- membership-first ordering cannot be preserved;
- `authorize?: false` appears necessary;
- Events must duplicate IAM authorization;
- codegen creates unexpected persistence drift;
- a dependency upgrade appears necessary;
- a new canonical lifecycle/error semantic appears necessary.

## 15. Completion criteria

This specification is satisfied when the merged implementation proves that the only production path to a new Event row is the governed `create_event` flow and the permanent forged-persona regression is green, while all pre-existing TICK-26 acceptance and repository gates also pass.