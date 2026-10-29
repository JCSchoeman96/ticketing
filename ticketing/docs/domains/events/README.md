# Events domain

> Nature and status: Derived implementation documentation. This dossier describes the merged `Ticketing.Events` implementation and does not define product semantics.
>
> Last verified main SHA: `a1e3c663ca50e0bf7a92e8860a3d40c452d1368f`
>
> Governing JIP: JIP-T0-01 v0.1.6 / Plane TICK-26.
>
> Merged implementation PR: [#45](https://github.com/JCSchoeman96/ticketing/pull/45).

## Ownership and current boundary

`Ticketing.Events` owns the merged Event resource and the current organizer-to-draft-Event creation effect.

The domain currently contains one resource:

- `Ticketing.Events.Event` — tenant-scoped PostgreSQL-backed Event state.

The current merged slice creates one draft Event. It does not implement Event publication, occurrence creation, sales, pricing, inventory, orders, payments, tickets, ledger behavior, outbox delivery, or background jobs.

## Production create interface

The domain exposes `Ticketing.Events.create_event/2` as the current production entry point for Event creation.

The caller supplies the Event-create attributes plus candidate `org_id` and a trusted actor through options. The domain starts one tenant-scoped `Ash.transact/3` and invokes the resource's sole create action, `create_event`, with authorization enabled.

There is no second Event persistence action. In particular, the vulnerable candidate's private `persist_draft` action and persona-bypass policy were removed before merge. No equivalent alternate write capability exists in the merged Event resource.

## Organizer proof and authorization order

The `create_event` resource change consumes Identity through governed Ash interfaces before protected Event identifiers are assigned:

```text
OrgMembership proof
→ User liveness
→ Session liveness
→ OrgRoleAssignment liveness
→ Identity authorize_event_create
→ protected Event identifiers assigned
→ Event insert
```

The Membership probe is first. The candidate organization is therefore only a selector until matching active/non-revoked Membership evidence is loaded.

The subsequent reads require the persisted User, Session and RoleAssignment state to match the trusted actor and selected organization/role. Session liveness uses PostgreSQL UTC `now()` in the Identity read, so an expired Session cannot reach the insert.

`Ticketing.Identity.Authorization.authorize_event_create` validates the persisted evidence and current human actor for the selected organization scope and role. The current accepted organizer roles are `org_owner` and `org_admin`; platform/support or fabricated role/persona state does not satisfy the merged path.

The IAM action returns only boolean success to the current orchestration. Events does not receive a reusable organizer persona, bearer token, signed capability, or other transferable authorization object.

## Event action boundary

`Ticketing.Events.Event` defines one create action:

- `create_event` — transactional, authorized, and restricted to the approved writable draft attributes.

The action accepts these caller-writable Event fields:

- `slug`;
- `visibility`;
- `default_locale`;
- `supported_locales`;
- `featured`;
- `taxonomy_refs`.

It also accepts orchestration arguments for selected scope/role plus request/trace identifiers.

Protected fields are not caller-writable through the action. The implementation forces `org_id` from the tenant transaction, generates `event_id` with `Ash.UUIDv7.generate/0`, derives `public_event_key` from that Event ID, and relies on governed defaults/database-owned values for lifecycle/version/timestamps.

The Event policy includes a preliminary trusted-session actor check. That check is not sufficient authority to insert a row: the action still performs the complete persisted Identity proof and IAM authorization sequence before the write.

## Current Event shape

The merged resource contains these persisted fields:

| Field | Current implementation posture |
| --- | --- |
| `org_id` | tenant component of composite primary key; protected/non-writable |
| `event_id` | UUIDv7 component of composite primary key; generated and protected |
| `public_event_key` | generated protected public key |
| `slug` | caller-writable; tenant-unique with `org_id` |
| `visibility` | caller-writable; one of `public`, `unlisted`, `private` |
| `status` | protected; defaults to `draft` |
| `default_locale` | caller-writable; current values `en` or `af` |
| `supported_locales` | caller-writable array |
| `featured` | caller-writable; defaults to `false` |
| `taxonomy_refs` | caller-writable array of maps; stored as JSONB; defaults to `[]` |
| `created_at_utc` | protected/generated; database-owned UTC default |
| `updated_at_utc` | protected/generated; database-owned UTC default |
| `archived_at_utc` | protected; nullable in current draft slice |
| `published_at_utc` | protected; nullable and `nil` for a newly created draft |
| `version` | protected; defaults to `1` |
| `lock_version` | protected; defaults to `1` |

The merged `create_event` slice does not expose arbitrary lifecycle/status mutation.

## Persistence and uniqueness

The `events` table uses composite physical primary key:

```text
(org_id, event_id)
```

The database also enforces tenant-scoped unique indexes for:

```text
(org_id, public_event_key)
(org_id, slug)
```

Those database constraints are authoritative for duplicate/concurrent uniqueness races. The implementation does not treat an application-side preflight as race-proof uniqueness authority.

## Tenant isolation and RLS

`Event` uses Ash attribute multitenancy on `org_id` and persists through `Ticketing.Repo` under the existing owner/runtime split.

The `events` table has PostgreSQL `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`. Its `tenant_context_isolation` policy requires row `org_id` to equal transaction-local `app.current_org_id` for both `USING` and `WITH CHECK`.

`Ticketing.Events.create_event/2` starts the tenant transaction with candidate `org_id`. The same transaction-local tenant UUID is retained through Membership proof, post-proof organizer evidence, IAM authorization and the Event insert. The merged flow does not perform a second tenant-context transition.

See [Tenancy and authorization](../../platform/tenancy-and-authorization.md) for the cross-cutting runtime-role, tenant-context and Identity authorization boundary.

## Transactions, rollback and side effects

The production create path is wrapped by one outer `Ash.transact/3`. The persisted organizer reads, IAM authorization and Event insert therefore participate in the same governed transaction/backend path verified by TICK-26 tests.

Failure before insertion leaves no Event row. The flow does not mutate Session state as part of Event creation.

Draft Event creation currently emits no publication event, outbox row or job. No generic idempotency/replay mechanism is introduced by TICK-26.

## Verification coverage

The merged TICK-26 tests cover the implemented boundary, including:

- `org_owner` and `org_admin` success;
- Membership proof before other organizer business-row reads;
- same PostgreSQL backend transaction through the Event insert;
- authoritative user/session/org/membership/role binding;
- active Session and DB-time expiry behavior;
- forged role denial;
- platform/support denial;
- invalid/mixed scope denial;
- cross-tenant information hiding;
- protected Event fields;
- initial draft values and database-owned timestamps;
- rollback with no Event and no Session mutation;
- database-enforced duplicate/concurrent uniqueness outcomes;
- regression proving the removed `persist_draft` action is unavailable;
- regression proving a fabricated human organizer map cannot directly invoke the remaining `create_event` action and insert an Event without persisted proof.

TICK-28 remains responsible for the supplemental integrated direct-SQL/RLS, pool-reuse, tenant-context-cleanup, telemetry and wider failure-path matrix. Those future tests do not change the Event semantics described here.

## Not implemented here

The current Events domain does not yet implement:

- Event publication transitions;
- occurrence creation or occurrence lifecycle;
- publication outbox/event delivery;
- pricing, offers or inventory;
- checkout, orders or payments;
- ticket issuance/admission/scan behavior;
- ledger behavior;
- UI or external API boundaries for Event creation.

Any later implementation must be documented only after it merges under its own approved governing work.
