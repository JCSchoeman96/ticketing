# Identity domain

> Nature and status: Derived implementation documentation. This dossier describes the merged `Ticketing.Identity` implementation and does not define product semantics.
>
> Last verified main SHA: `c6979779a33ca2e4f84573bab7211bb800cf45cb`
>
> Governing JIP: JIP-T0-01 v0.1.5 / Plane TICK-25.
>
> Merged implementation PR: [#40](https://github.com/JCSchoeman96/ticketing/pull/40).

## Ownership and boundary

`Ticketing.Identity` owns the merged non-credential organizer evidence resources required by T0:

| Resource | Scope | Current purpose |
| --- | --- | --- |
| `Ticketing.Identity.User` | global | trusted User liveness evidence |
| `Ticketing.Identity.OrgMembership` | tenant | active organization-membership proof |
| `Ticketing.Identity.Session` | tenant | read-only active Session liveness evidence |
| `Ticketing.Identity.OrgRoleAssignment` | tenant | persisted active organization-role evidence |

The domain does not own authentication providers, credentials, login flows, Session issuance, or Event creation.

## Governed interfaces

The merged Ash domain exposes these code interfaces:

- `read_user_for_liveness(id)`;
- `probe_org_membership(user_id)`;
- `read_session_for_liveness(id)`;
- `read_active_role_assignment(user_id, role)`.

There are no generic production create/update/destroy interfaces for the tenant evidence resources in this T0 slice. Pre-existing test state is seeded only through the narrow owner/test fixture boundary.

## User liveness

`User.read_for_liveness` returns a User only when the requested ID matches the authenticated actor and the persisted User is active, not disabled, and not deleted.

User is global rather than tenant-scoped. It relates to the user's organization memberships, Sessions, and organization role assignments, but those tenant resources remain protected by their own tenant context, policies, and database RLS.

## Membership proof

`OrgMembership.read_membership_proof` is tenant-scoped and returns only an active, non-revoked membership for the requested user. Its Ash policy requires the row user to match the authenticated actor.

This interface is the merged evidence boundary intended for the candidate-organization membership proof in the downstream organizer flow. The downstream transaction that orders that proof before other organizer evidence is not implemented in TICK-25.

## Session liveness

`Session` is read-only in the merged T0 boundary: its Ash action set contains only `read_for_liveness`.

The liveness read requires:

- the requested Session ID;
- `status == "active"`;
- no revocation timestamp;
- `expires_at_utc` later than PostgreSQL UTC `now()`;
- row `user_id` matching the authenticated actor.

The Session resource stores a sensitive, non-public `token_hash`, but the liveness read explicitly selects only `id`, `org_id`, `user_id`, status, timestamps, expiry, revocation, and last-seen fields. It therefore does not return the token hash through this interface.

TICK-25 adds no Session issue, refresh, rebind, revoke, last-seen mutation, or Session lifecycle-event behavior.

## Role-assignment liveness

`OrgRoleAssignment.read_active_assignment` is tenant-scoped and requires the requested user and role to match an active, non-revoked persisted assignment. Its Ash policy also requires the row user to match the authenticated actor.

A role string supplied to this read is a selector for persisted evidence; it is not, by itself, authority. The later Event-create action must derive authorization from the verified persisted organizer state and the governing IAM capability rules.

## Persistence and tenant isolation

The tenant resources use Ash attribute multitenancy on `org_id` and PostgreSQL `ENABLE ROW LEVEL SECURITY` plus `FORCE ROW LEVEL SECURITY`. Their database policy requires row `org_id` to match transaction-local `app.current_org_id`.

JIP-T0-01 v0.1.5 explicitly permits single-column database-generated UUIDv7 physical primary keys for exactly Membership, Session, and RoleAssignment. The merged database also preserves the required tenant identities/indexes:

- Membership `(org_id, org_membership_id)` and `(org_id, user_id)`;
- Session `(org_id, id)`;
- RoleAssignment `(org_id, user_id, role)`.

The constrained-runtime tests prove no-context and wrong-tenant denial and matching-tenant visibility. Session and RoleAssignment are also looked up by global physical UUID in that matrix, proving that the UUID alone is not an authorization path.

See [Tenancy and authorization](../../platform/tenancy-and-authorization.md) for the cross-cutting database-role, tenant-context, and RLS implementation.

## Test-only fixture boundary

`Ticketing.Identity.OwnerFixtures` exists under test support to seed deterministic pre-existing Identity state through the owner/migration boundary. It is test-only infrastructure and is not a production application API. Its ability to inject deterministic identifiers for fixtures does not change the production rule that the excepted physical IDs are database-generated and non-writable through production interfaces.

## Not implemented here

TICK-25 does not implement:

- authentication providers, credentials, passwords, OAuth, magic links, or login UI;
- Session issuance, refresh, rebind, revoke, last-seen mutation, or lifecycle events;
- production organization-role grant/activation convenience APIs;
- `Ticketing.Events`, Event persistence, or `create_event`;
- occurrence creation, publication, sales, pricing, offers, inventory, orders, payments, tickets, or ledger behavior.

The next approved T0-01 implementation slice is the separately gated TICK-26 atomic organizer-to-draft-Event effect.
