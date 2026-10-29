# Identity domain

> Nature and status: Derived implementation documentation. This dossier describes the merged `Ticketing.Identity` implementation and does not define product semantics.
>
> Last verified main SHA: `25a6a0956d7bb81214e348c7511132f5297d0fc5`
>
> Governing JIP: JIP-T0-01 v0.1.6 / Plane TICK-25 and TICK-26.
>
> Relevant merged implementation PRs: [#40 (TICK-25)](https://github.com/JCSchoeman96/ticketing/pull/40), [#45 (TICK-26)](https://github.com/JCSchoeman96/ticketing/pull/45), and [#55 (TICK-28 verification)](https://github.com/JCSchoeman96/ticketing/pull/55).

## Ownership and boundary

`Ticketing.Identity` owns the merged non-credential organizer evidence and IAM authorization resources required by the current T0 flow:

| Resource | Scope | Current purpose |
| --- | --- | --- |
| `Ticketing.Identity.User` | global | trusted User liveness evidence |
| `Ticketing.Identity.OrgMembership` | tenant | active organization-membership proof |
| `Ticketing.Identity.Session` | tenant | read-only active Session liveness evidence |
| `Ticketing.Identity.OrgRoleAssignment` | tenant | persisted active organization-role evidence |
| `Ticketing.Identity.Authorization` | non-persistent | current-orchestration IAM authorization for Event creation |

The domain does not own authentication providers, credentials, login flows, Session issuance, or Event persistence. `Ticketing.Events` owns the Event resource and the complete Event-create effect while consuming Identity through governed interfaces.

## Governed interfaces

The merged Ash domain exposes these code interfaces for persisted evidence:

- `read_user_for_liveness(id)`;
- `probe_org_membership(user_id)`;
- `read_session_for_liveness(id)`;
- `read_active_role_assignment(user_id, role)`.

The domain also includes the private non-persistent `Authorization.authorize_event_create` Ash action used inside the merged Event-create orchestration. It is not a public domain code interface and does not return a reusable authorization object.

There are no generic production create/update/destroy interfaces for the tenant evidence resources in this T0 slice. Pre-existing test state is seeded only through the narrow owner/test fixture boundary.

## User liveness

`User.read_for_liveness` returns a User only when the requested ID matches the authenticated actor and the persisted User is active, not disabled, and not deleted.

User is global rather than tenant-scoped. It relates to the user's organization memberships, Sessions, and organization role assignments, but those tenant resources remain protected by their own tenant context, policies, and database RLS.

## Membership proof

`OrgMembership.read_membership_proof` is tenant-scoped and returns only an active, non-revoked membership for the requested user. Its Ash policy requires the row user to match the authenticated actor.

The merged TICK-26 Event-create flow invokes this Membership probe before any other organizer business-row evidence. Candidate `org_id` is therefore only a selector until this read succeeds.

## Session liveness

`Session` is read-only in the merged T0 boundary: its Ash action set contains only `read_for_liveness`.

The liveness read requires:

- the requested Session ID;
- `status == "active"`;
- no revocation timestamp;
- `expires_at_utc` later than PostgreSQL UTC `now()`;
- row `user_id` matching the authenticated actor.

The Session resource stores a sensitive, non-public `token_hash`, but the liveness read explicitly selects only `id`, `org_id`, `user_id`, status, timestamps, expiry, revocation, and last-seen fields. It therefore does not return the token hash through this interface.

TICK-25/TICK-26 add no Session issue, refresh, rebind, revoke, last-seen mutation, or Session lifecycle-event behavior.

## Role-assignment liveness

`OrgRoleAssignment.read_active_assignment` is tenant-scoped and requires the requested user and role to match an active, non-revoked persisted assignment. Its Ash policy also requires the row user to match the authenticated actor.

A role string supplied to this read is a selector for persisted evidence; it is not, by itself, authority. The Event-create flow passes the persisted assignment together with the other current-transaction evidence into the IAM authorization action.

## Event-create IAM authorization

`Ticketing.Identity.Authorization` uses `Ash.DataLayer.Simple` and has no persisted table. Its private `authorize_event_create` action returns a boolean and is governed by `Ticketing.Identity.Checks.CanCreateEvent`.

The check requires a human trusted actor and validates the current action arguments against the persisted evidence supplied by the Event-create orchestration:

- `active_scope == "org"`;
- selected role is `org_owner` or `org_admin`;
- User ID matches and User is active;
- Membership matches organization/user and remains active/non-revoked;
- Session matches organization/user/session and remains active/non-revoked;
- RoleAssignment matches organization/user/selected role and remains active/non-revoked.

Session expiry is already enforced by the preceding persisted Session liveness read using database time.

The authorization result is intentionally non-transferable in practice: the action returns only `true` to the current orchestration. It does not create or return an organizer persona, bearer token, signed capability, opaque credential, or other value that can independently authorize a later Event write.

## Persistence and tenant isolation

The tenant evidence resources use Ash attribute multitenancy on `org_id` and PostgreSQL `ENABLE ROW LEVEL SECURITY` plus `FORCE ROW LEVEL SECURITY`. Their database policy requires row `org_id` to match transaction-local `app.current_org_id`.

JIP-T0-01 v0.1.5 explicitly permits single-column database-generated UUIDv7 physical primary keys for exactly Membership, Session, and RoleAssignment. The merged database also preserves the required tenant identities/indexes:

- Membership `(org_id, org_membership_id)` and `(org_id, user_id)`;
- Session `(org_id, id)`;
- RoleAssignment `(org_id, user_id, role)`.

The constrained-runtime tests prove no-context and wrong-tenant denial and matching-tenant visibility. Session and RoleAssignment are also looked up by global physical UUID in that matrix, proving that the UUID alone is not an authorization path.

See [Tenancy and authorization](../../platform/tenancy-and-authorization.md) for the cross-cutting database-role, tenant-context, RLS and merged Event-create authorization boundary.

## Test-only fixture boundary

`Ticketing.Identity.OwnerFixtures` exists under test support to seed deterministic pre-existing Identity state through the owner/migration boundary. It is test-only infrastructure and is not a production application API. Its ability to inject deterministic identifiers for fixtures does not change the production rule that the excepted physical IDs are database-generated and non-writable through production interfaces.

## Current consumer

The merged `Ticketing.Events.create_event/2` flow consumes Identity in this order inside the Event transaction:

```text
Membership proof
→ User liveness
→ Session liveness
→ RoleAssignment liveness
→ authorize_event_create
→ Event insert
```

Identity never performs the Event insert itself. The authorization result is consumed by the Events orchestration before the single Event write.

## Not implemented here

Identity still does not implement:

- authentication providers, credentials, passwords, OAuth, magic links, or login UI;
- Session issuance, refresh, rebind, revoke, last-seen mutation, or lifecycle events;
- production organization-role grant/activation convenience APIs;
- occurrence creation, publication, sales, pricing, offers, inventory, orders, payments, tickets, or ledger behavior.

TICK-28 supplements the Membership, Session and RoleAssignment failure-path evidence and verifies direct-SQL tenant isolation, tenant-context lifecycle and observability privacy across the integrated Event-create boundary. It changes no Identity ownership, authorization semantics, or production behavior. See the [T0-01 implementation handoff](../../handoffs/T0-01.md).
