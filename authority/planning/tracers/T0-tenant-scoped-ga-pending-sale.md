# T0: Tenant-scoped GA pending sale

- **Roadmap status:** NEXT
- **Contracts baseline:** `ea6ebbb84664aeb383d21ccbd92d30dd1a93939f`
- **Implementation baseline:** `9bbec7e5c926f8036ef32e261fbeb8ae9377e0ac`
- **Implementation repository:** `JCSchoeman96/ticketing`
- **Phoenix application directory:** `ticketing/`
- **Authority snapshot:** CANON-1 2.0.19, read from the active manifest and verified against installed CANON pins

## Scope

One authenticated organizer creates and publishes an Event and Occurrence, configures a fixed-price GA offer, and opens it for sale. A buyer retrieves the sellable offer, requests a quote, claims inventory atomically, creates an idempotent Order, and retrieves that Order in the same tenant. T0 ends at the persisted ORD-1 `draft` Order. T0 stops before provider payment confirmation, ORD finalization, seat or bucket allocation finalization, ticket issuance, and ledger work.

## B0 status

B0 is COMPLETE. The implementation repository is `JCSchoeman96/ticketing`; its Phoenix application lives in `ticketing/`. The Phoenix, Ash, and AshPostgres bootstrap exists. PostgreSQL and migration bootstrap exists. Contract-authority verification exists. B0 no longer blocks T0 and does not include product-domain work.

## Current authority snapshot

Versions come from `contracts/manifest.json`. CANON-1 2.0.19 pins 56 CANON members. EXT-1 is an accepted dependency-only record, not a CANON member.

| Authority | Version | Membership | T0 use |
|---|---:|---|---|
| CANON-1 | 2.0.19 | CANON_INDEX | Current suite membership and pins |
| V42-0 | 1.8.2 | CANON_MEMBER | Constitutional contract baseline |
| CS-0 | 3.0.1 | CANON_MEMBER | Contract and test-gate structure |
| BP-0 | 3.0.1 | CANON_MEMBER | Bundle posture |
| EVT-2 | 3.1.0 | CANON_MEMBER | Event/Occurrence authority and tenant-scoped Occurrence admission policy |
| TEN-1 | 2.0.1 | CANON_MEMBER | Membership proof before tenant context and hide-existence boundaries |
| IAM-1 | 4.2.0 | CANON_MEMBER | Trusted active Session, organizer persona, and org_owner/org_admin admission-policy capability |
| IAM-2 | 1.5.0 | CANON_MEMBER | Authorization policy posture where applicable |
| OFFER-1 | 2.0.0 | CANON_MEMBER | Offer, Product, ProductRevision, quote, and line claims |
| SEAT-1 | 4.1.0 | CANON_MEMBER | GA bucket inventory, holds, live proof validation, and replay proof possession |
| PRICE-1 | 4.0.0 | CANON_MEMBER | Reusable pricing program revision and signed quote snapshot |
| ORD-1 | 4.0.1 | CANON_MEMBER | Checkout, durable idempotency, draft Order, and retrieval tenancy |
| TAX-1 | 3.0.1 | CANON_MEMBER | Pinned tax profile resolution and tax context |
| PII-1 | 2.0.0 | CANON_MEMBER | Direct jurisdiction evidence ownership |
| API-0 | 1.2.0 | CANON_MEMBER | HTTP `Idempotency-Key` requirement |
| ERR-1 | 2.0.1 | CANON_MEMBER | Registered error codes and subcodes, including EVT admission-policy failures |
| OBS-1 | 2.9.1 | CANON_MEMBER | Required logs, spans, metrics, and alerts; stable policy-management operation ID |
| EVT-1 | 3.0.0 | CANON_MEMBER | Registered event vocabulary |
| LOCKS-1 | 3.0.0 | CANON_MEMBER | Durable idempotency identity, request hash, replay, and concurrency |
| EXT-1 | 2.1.7 | DEPENDENCY_ONLY | Accepted dependency only |

EXT-1 does not own T0 HTTP idempotency or durable idempotency semantics.

## End-to-end sequence

1. Resolve the organizer context before tenant-scoped Session or role reads:
   - Trusted authentication/session infrastructure authenticates the underlying session credential, then supplies authoritative `user_id` and authoritative `session_id`. The caller supplies candidate `org_id`, requested `active_scope = org`, and requested `active_role`; these selectors grant no tenant or role authority by themselves.
   - First, TEN-1 `org_membership_probe` uses its system-internal, transaction-local candidate-org scope to read only the matching `OrgMembership`. Require active, non-revoked membership for the authoritative user and retain its persisted `org_membership_id`. Failed proof discards candidate scope, does not establish tenant context, and preserves hide-existence behavior as external `ERR_NOT_FOUND`.
   - Only after proof, apply IAM-1 `t0_trusted_active_session` under the proven organization tenant. Require an active `User`; load the persisted Session by authoritative `session_id`; and require `Session.id = session_id`, `Session.user_id = user_id`, `Session.org_id = proven org_id`, `status = active`, `revoked_at_utc = null`, and `expires_at_utc > evaluated_at_utc` using authoritative database UTC time.
   - Require an active, non-revoked same-org `OrgRoleAssignment` for the authoritative user and requested role. Build the active organization persona from authoritative `user_id`, validated `session_id`, proven `org_id`, persisted `org_membership_id`, `active_scope = org`, and verified `active_role`. Evaluate T0 organizer capabilities against that persona only. After membership proof, invalid or mismatched Session state returns uniform `ERR_UNAUTHENTICATED`; a missing, inactive, revoked, or incapable requested role returns `ERR_FORBIDDEN`.
   - The application carries `request_id` and `trace_id` where the owning action requires them.
2. The organizer calls `EVT-2.create_event` for a tenant-owned Event.
3. The authorized `org_owner` or `org_admin` configures the organization's singleton policy with `EVT-2.set_occurrence_admission_policy`. The policy has no active/inactive state; it requires non-negative early/late seconds, and zero is valid. No platform default exists.
4. The organizer calls `EVT-2.create_occurrence` for a real Occurrence in that Event, supplying the actual check-in window. The action resolves the same-tenant policy inside its governed create transaction and rejects a missing policy or any window outside the policy bounds. A policy update does not alter existing Occurrence windows; admission uses each persisted Occurrence window.
5. The organizer calls `EVT-2.publish_event`, then `EVT-2.open_occurrence_sales` when the parent Event is published and database UTC is inside the configured sale window.
6. The organizer sets up a reusable PRICE-1 `PricingProgram` and `PricingProgramRevision`, configures its fixed-price phase and rules, and activates the revision.
7. The organizer uses `OFFER-1.create_offer`, `OFFER-1.create_product`, `OFFER-1.create_product_revision`, and `OFFER-1.create_offer_window`, then activates the Offer and Product after their guards pass.
8. ProductRevision binds to reusable pricing-program revision authority through `pricing_program_revision_id`. It does not bind directly to the transaction-specific PricingSnapshot.
9. ProductRevision immutably pins a T0-compatible pinned TaxProfile. The profile belongs to the same tenant, is active, and uses `default_tax_basis = org_location`.
10. The organizer calls `SEAT-1.create_inventory_bucket` for the GA Occurrence with fixed capacity, zero oversell allowance for this tracer, and the required shard configuration.
11. The buyer performs buyer sellability retrieval. The read checks tenant visibility, Event publication, the configured sale window, Offer eligibility, and parent sovereignty.
12. The buyer calls `OFFER-1.build_cart_quote` with the boundary `Idempotency-Key` and server-derived tenant and actor context.
13. Quote creation produces the transaction-specific signed PRICE-SIG-V4 PricingSnapshot from the reusable pricing revision and the resolved T0 tax context.
14. The buyer requests inventory through atomic `SEAT-1.claim_bucket_inventory` with quantity, `org_id`, actor context, governed TTL, and the boundary key.
15. The claim returns an `InventoryBucketHold` identity and signed bucket hold proof. The application does not fabricate a seat ID.
16. A normal first execution uses the full live verifier `SEAT-1.verify_bucket_hold_proofs`. If seat proofs are supplied, it uses `SEAT-1.verify_hold_proofs`. Both require current valid lifecycle state, including active and unexpired holds.
17. The buyer calls idempotent `ORD-1.create_checkout` with the exact quote snapshot and verified proof sets. ORD secures bounded grace for each bound hold and persists the Order.
18. The result is a persisted tenant-scoped `draft` Order for ORD-1 with immutable price and line snapshots, authoritative hold IDs, and bounded expiry.
19. The buyer retrieves the Order through same-tenant retrieval using explicit `org_id` and authorized actor context.
20. A completed-identical replay follows the separate proof-possession path below before ORD releases the stored original outcome.

### T0 Session boundary

T0 is a read-only consumer of an already-issued canonical Session. It does not issue a Session or implement `sign_in_with_org` issuance, receive a raw session credential or token, derive or verify `token_hash`, refresh Session expiry, rebind Session user or organization, revoke a Session, write `last_seen_at_utc`, or emit `ticketing.iam.session.created.v1` or `ticketing.iam.session.revoked.v1`.

## Buyer quote authorization and T0 eligibility

`OFFER-1.build_cart_quote` owns the buyer-facing quote boundary, authorized by `offer.quote.create`. `PRICE-1.create_snapshot` and `PRICE-1.activate_snapshot` are subordinate governed actions. They are not buyer-authorized endpoints. OFFER invokes them through scoped authenticated delegation and preserves originating actor attribution, `org_id`, `request_id`, `trace_id`, and the boundary `Idempotency-Key`. Generic authorization bypass, including `authorize?: false`, is forbidden.

OFFER owns eligibility, ProductRevision validation, tax/pricing binding, and quote invariants. PRICE owns snapshot construction, signature, activation, and pricing invariants. OFFER MUST NOT write PRICE resources directly.

T0 MUST use `public` eligibility. T0 `create_offer_window` MUST accept only `eligibility_policy.mode=public` and `prerequisite_policy.mode=none` or null. T0 does not support child occurrences or prerequisite claims; ProductRevision setup rejects child Occurrences. Do not implement entitlement or prerequisite eligibility machinery as part of T0. `build_cart_quote` MUST fail closed if it would require an `EligibilityIssuerKey`, a `SignedEligibilityClaim`, a claim nonce, signed-claim validation or consumption, or prerequisite proof. T0 MUST NOT validate or consume `SignedEligibilityClaim`. T0 also MUST NOT create, rotate, or revoke an `EligibilityIssuerKey`, create or revoke `SignedEligibilityClaim`, or consume a claim nonce. The ORD-1 canonical `entitlement_allocations` request-hash field remains unchanged; this boundary limits OFFER's T0 commercial eligibility path.

## Idempotency ownership and ORD-1 checkout

API-0 owns the required HTTP `Idempotency-Key` header. LOCKS-1 owns durable idempotency identity `(org_id, operation_id, key)` and a separately persisted canonical `request_hash`, plus replay, changed-hash conflict, concurrency, and one-effect behavior. EXT-1 remains dependency-only and does not own either layer.

For `ORD-1.create_checkout`, `operation_id` is `ORD-1.create_checkout`. The request hash is:

```text
lowercase_hex(SHA-256(UTF-8(RFC8785_JCS(normalized_request))))
```

The normalized fields are the installed ORD-1 fields:

- `org_id`
- `actor_id`
- `actor_type`
- `currency`
- `pricing_snapshot_id`
- `seat_hold_proofs[].hold_id`
- `bucket_hold_proofs[].hold_id`
- `entitlement_allocations[].hold_id`
- `entitlement_allocations[].line_key`
- `entitlement_allocations[].qty`
- `entitlement_allocations[].beneficiary_customer_id`
- `entitlement_allocations[].entitlement_kind`
- `entitlement_allocations[].entitlement_grant_id`
- `entitlement_allocations[].entitlement_tier_id`

Proof identity reduces to `hold_id`. `hold_signature` is excluded from request hashing, but every supplied signature remains mandatory security evidence and is verified separately. UUIDs use lowercase RFC-4122 form; currency uses uppercase ISO-4217 form. Seat and bucket proof collections sort by `hold_id`, duplicates across proof collections are rejected, and absent or empty optional collections normalize to `[]`. RFC8785_JCS canonicalizes object keys. Text is preserved without trimming, case folding, or extra Unicode normalization.

The durable identity and request hash are separate fields. Same identity and same hash replay the original result without another effect. Same identity and a changed hash returns `ERR_CONFLICT / LOCKS_IDEMPOTENCY_KEY_REUSE_MISMATCH`. Concurrent duplicate requests produce one effect and resolve to the same outcome. The quote action retains its contract-specific `ERR_CONFLICT / EXT_IDEMPOTENCY_REPLAY` behavior; do not replace it with the LOCKS-1 identifier.

## Completed-identical replay proof possession

This path runs only after LOCKS-1 establishes the same durable identity, the same canonical request hash, and an existing `COMPLETED` stored result.

1. Authenticate tenant context and actor context again. Preserve TEN-1 cross-tenant hiding.
2. For supplied SeatHold proofs, call `SEAT-1.verify_hold_proof_possession`. For supplied bucket proofs, call `SEAT-1.verify_bucket_hold_proof_possession`.
3. Cryptographically verify every supplied signature, verify that each signature binds to its referenced `hold_id`, and require the verified hold-ID sets to equal the normalized submitted proof-ID sets.
4. Do not check mutable hold status, expiry, inventory availability, or quantity as current checkout validity. Do not extend grace, rebind lines, or mutate hold, inventory, Order, allocation, or grace state.
5. Return only the stored original outcome. An invalid replacement signature prevents release of that response and must not execute checkout again.

These possession actions are narrow read-only checks for a completed identical replay. They do not authorize a first execution, an in-progress or incomplete execution, a changed-hash request, finalization, allocation, or any new effect. `finalize_checkout` does not use possession actions. Finalization remains bound to full live proof verification and current lifecycle guards, outside T0.

## Individual SeatHold signature

The individual SeatHold signature transcript is exactly:

```text
org_id|hold_id|occurrence_id|seat_id|actor_id|actor_type
```

The transcript does not include `expires_at_utc`. The signature is actor-bound and tenant-bound, and verification uses constant-time comparison. A governed grace extension does not rotate the individual signature. Live verification still requires current active and unexpired status, so an expired hold is not valid for a new checkout merely because its signature remains cryptographically valid.

`hold_signature_batch` remains deferred non-T0 legacy authority debt. No current governed domain action uses it. Its definition is not changed or promoted into T0.

## T0 tax authority

ProductRevision immutably pins `tax_profile_id`. Quote resolution uses that exact same-tenant, active TaxProfile and does not substitute another profile. T0 requires `default_tax_basis = org_location`. `event_location` and `customer_location` are unsupported. OFFER-1 MUST NOT infer jurisdiction from `Occurrence.venue`. No new raw PII storage is authorized.

General TAX-1 supports `half_even_minor_units` and `half_up_minor_units`. The general default is `half_even_minor_units`, and arithmetic follows the resolved TAXCTX-V2 `rounding_mode`. T0 is separately restricted by OFFER-1 to `half_even_minor_units`. The TAXCTX-V2 half-up conformance vector `TAXCTX-V2-0002` remains valid general TAX authority.

The TAXCTX-V2 field order is:

1. `org_id`
2. `jurisdiction_code`
3. `inclusion_mode`
4. `rounding_mode`
5. `tax_class`
6. `rate_basis_points`
7. `tax_scope`
8. `tax_basis`
9. `provider_mode`
10. `provider_name`
11. `tax_point_strategy`

Encode every field as `key=value`, join fields with `|`, and encode as UTF-8. Encode null or missing optional values as an empty value after `=`. Hash the bytes with SHA-256 and encode the digest as lowercase hexadecimal.

For a T0 single-context quote, `applicable_tax_rate_revision_refs = [TAX-1.tax_rate_id]`. For a T0 `org_location` draft quote, `opaque_pii_jurisdiction_evidence_ref = null` and `jurisdiction_evidence_sha256 = null`. PRICE-1 preserves both explicit nulls inside the signed PRICE-SIG-V4 snapshot. This T0 draft-quote rule does not define later payment or finalization evidence. TAX-1 remains eventless.

## Lifecycle tables

These tables record the T0-relevant lifecycle rules from the installed EVT-2 3.1.0, OFFER-1 2.0.0, SEAT-1 4.1.0, and ORD-1 4.0.1 authorities. They do not add states or transitions.

`OccurrenceAdmissionPolicy` is a tenant-scoped zero-or-one configured row per organization, keyed by `org_id`, with no active/inactive lifecycle. `EVT-2.set_occurrence_admission_policy` lets a human organization owner or admin create or replace its values using `evt.occurrence.admission_policy.manage`. Changes are prospective and leave persisted Occurrence windows unchanged.

### Event and occurrence sale lifecycle

| Transition | Initiator and action | Guards | Side effects and concurrency | Failure behavior |
|---|---|---|---|---|
| Event absent → `draft` | Authorized organizer, `EVT-2.create_event` | Valid tenant and Event input | Persist Event | Reject without write |
| Event `draft` → `published` | Authorized organizer, `EVT-2.publish_event` | Same-tenant Event is `draft` | Set status, database publication time, and version; enqueue registered `ticketing.event.published.v1` atomically | `ERR_PRECONDITION`; no status or event partial write |
| Event `draft` or `published` → `archived` | Authorized organizer, `EVT-2.archive_event` | Existing archive rules, including no delete when sales exist | Archive and preserve publication time and version | Existing canonical archive errors; no partial write |
| Occurrence absent → `scheduled` | Authorized organization organizer, `EVT-2.create_occurrence` | Authorized tenant and Event identity; explicit or canonical values for non-null T0 fields; root occurrence; configured same-tenant policy and check-in window within its bounds | Resolve policy and persist Occurrence with version and lock version 1; enqueue registered `ticketing.occurrence.created.v1` atomically | Missing policy: `ERR_PRECONDITION / EVT_ADMISSION_POLICY_MISSING`; out-of-policy window: `ERR_VALIDATION / EVT_CHECK_IN_WINDOW_OUT_OF_POLICY`; no write |
| `scheduled` → `sales_open` | Authorized organization organizer, `EVT-2.open_occurrence_sales` | Parent Event published; valid nonempty UTC window; database time inside the window | Compare-and-swap on lock version and current state; increment version and lock version atomically | `ERR_PRECONDITION`; no write |
| `sales_open` → `sales_closed` | Authorized organizer or authenticated system principal under separate policy, `EVT-2.close_occurrence_sales` | Current status and tenant/Event identity verified; system caller also requires database time at or after close time | Compare-and-swap on lock version and current state; increment version and lock version atomically | `ERR_PRECONDITION`; no write |

The sale lifecycle table covers only the T0 sale transitions. Other EVT-2 occurrence lifecycle behavior remains under its installed authority and is outside this T0 path.

### Offer lifecycle

| Transition | Initiator and action | Guards | Side effects | Failure behavior |
|---|---|---|---|---|
| Offer absent → `draft` | Authorized organizer, `OFFER-1.create_offer` | Same-tenant occurrence scope | Persist draft and database timestamps | `ERR_VALIDATION` or hidden `ERR_NOT_FOUND` |
| Product absent → `draft` | Authorized organizer, `OFFER-1.create_product` | Same-tenant non-archived Offer | Persist draft and database timestamps | `ERR_VALIDATION` or hidden `ERR_NOT_FOUND` |
| ProductRevision absent → immutable | Authorized organizer, `OFFER-1.create_product_revision` | Valid same-tenant Product and Occurrence; reusable PRICE-1 PricingProgramRevision | Persist immutable revision | Reject without write |
| OfferWindow absent → configured immutable window | Authorized organizer, `OFFER-1.create_offer_window` | Valid same-tenant Offer; `starts_at_utc < ends_at_utc` | Persist immutable window configuration | Reject without write |
| Offer `draft` → `active` | Authorized organizer, `OFFER-1.activate_offer` | Same-tenant draft Product, valid revision and OfferWindow, live occurrence scope | Persist active state and transition timestamp | `ERR_PRECONDITION`; no write |
| Product `draft` → `active` | Authorized organizer, `OFFER-1.activate_product` | Parent Offer active; valid immutable revision and pricing configuration | Persist active state and transition timestamp | `ERR_PRECONDITION`; no write |
| Offer or Product `draft` or `active` → `archived` | Authorized organizer, owning archive action | Same-tenant resource exists | Persist archived state and database timestamp; preserve history | `ERR_PRECONDITION`; no write |

Offer and Product states are `draft`, `active`, and `archived`. ProductRevision is immutable after creation. OfferWindow configuration is immutable; its time eligibility is checked at quote time.

### GA InventoryBucketHold lifecycle

| Transition | Initiator and action | Guards | Side effects and concurrency | Failure behavior |
|---|---|---|---|---|
| No hold → `active` | Buyer, `SEAT-1.claim_bucket_inventory` | Tenant-owned GA bucket; positive quantity; valid TTL; atomic shard capacity predicate | Increment the selected shard's `held_count`; persist signed hold and idempotency reservation in one transaction | `ERR_CONFLICT / SEAT_CAPACITY_EXHAUSTED` or fail-closed validation |
| `active` → `released` | Proof-bound hold actor, `SEAT-1.release_bucket_hold` | Valid tenant/actor proof; active status; CAS | Decrement `held_count` once under LOCKS-1 namespace 103 and SM-0 CAS | `ERR_PRECONDITION`; no partial write |
| `active` → `expired` | System/service, `SEAT-1.expire_bucket_holds` | Expiry at or before cutoff; CAS | Decrement `held_count` once under LOCKS-1 namespace 103 and SM-0 CAS | One CAS winner; no partial write |
| `active` → `active` | ORD checkout, `SEAT-1.extend_bucket_hold_grace` | Tenant/actor-bound proof; active unexpired hold; SEAT grace limits and total TTL; SM-0 CAS | Extend expiry and grace metadata when needed; counters remain unchanged; use LOCKS-1 namespace 103 and update the bucket cursor only when expiry changes | `ERR_PRECONDITION`; no partial update |
| `active` → `allocated` | ORD finalization, `SEAT-1.allocate_bucket_hold` | Verified current proof; unexpired hold; matching Order claim; CAS | Decrement `held_count`, increment `sold_count`, and create allocation atomically under LOCKS-1 namespace 103 and SM-0 CAS | `ERR_PRECONDITION`; rollback all effects |

InventoryBucketHold states are `active`, `released`, `expired`, and `allocated`. Release, expiry, grace, and allocation are fenced by the installed CAS rules; T0 performs no allocation.

### Order boundary

| Transition | Initiator and action | Guards | Side effects | Failure behavior |
|---|---|---|---|---|
| No Order → `draft` | Buyer, `ORD-1.create_checkout` | Same-tenant authenticated context; at least one full-live-verified hold proof; exact quote; tax context; lines match verified claims; durable idempotency is valid | Secure bounded hold grace; persist immutable Order, line and price snapshots, hold identities, and expiry in the owning transaction boundary | Existing ORD/SEAT errors; no partial Order or inventory effect |

T0 stops at the ORD-1 `draft` Order. `finalize_checkout` is a later boundary, outside T0. That boundary uses full live verification and the matching seat or bucket allocation actions under installed ORD/SEAT authority.

## Events, tenancy, and error boundaries

- The 53 deferred EVT registry-debt entries remain deferred. Do not repair them in T0.
- EVT-2 Event publication and Occurrence creation emit only their registered events under their contract transaction boundaries.
- TAX-1 remains eventless.
- Single-order `ORD-1.create_checkout` emits no event. Do not invent a checkout-created event from the separate checkout-group reference.
- Every tenant-scoped read and write carries explicit `org_id` and authenticated actor context. Do not infer tenant ownership from ambient process state or a globally looked-up identifier.
- Internal missing-tenant failures may use `ERR_FORBIDDEN / TEN_TENANT_CONTEXT_MISSING`. At a tenant-scoped HTTP/API boundary with hide-existence enabled, missing context, cross-tenant access, tenant mismatch, and RLS denial return the uniform HTTP 404 `ERR_NOT_FOUND` result. Do not leak internal tenant-context subcodes to callers; TEN-1 requires the hidden response to omit the optional subcode.
- Preserve registered quote replay, checkout idempotency, capacity, authorization, and proof errors. Do not rename or normalize contract-specific subcodes across boundaries.

## Required actions

- EVT-2: `create_event`, `set_occurrence_admission_policy`, `create_occurrence`, `publish_event`, `open_occurrence_sales`, and `close_occurrence_sales`.
- OFFER-1: `create_offer`, `create_product`, `create_product_revision`, `create_offer_window`, `activate_offer`, `activate_product`, `archive_offer`, `archive_product`, `build_cart_quote`, and `emit_ord_line_items`.
- PRICE-1: reusable program and revision setup, phase/rule setup, `create_snapshot`, and `activate_snapshot` as required by the fixed-price configuration. ProductRevision binds to reusable `PricingProgramRevision`; quote and Order bind to the transaction-specific `PricingSnapshot`.
- SEAT-1 new/effectful path: `create_inventory_bucket`, `claim_bucket_inventory`, `verify_hold_proofs`, `verify_bucket_hold_proofs`, `extend_hold_grace` for SeatHolds, and `extend_bucket_hold_grace` for bucket holds. Preserve `release_hold`, `expire_holds`, `allocate_hold`, `release_bucket_hold`, `expire_bucket_holds`, and `allocate_bucket_hold` for their governed lifecycle boundaries.
- SEAT-1 completed-identical replay only: `verify_hold_proof_possession` and `verify_bucket_hold_proof_possession`. These verify supplied signed proof possession for a completed replay. They do not replace either full live verifier.
- ORD-1: `create_checkout`. `finalize_checkout` appears only as the later full-verification and allocation boundary.
- TAX-1: `resolve_tax_context_for_event` and `compute_tax_for_price_line` as required by quote resolution.
- Buyer sellability and Order retrieval use current EVT-2/OFFER-1 and ORD-1 reads through the API-0 application boundary. The contracts do not define a route name; do not invent a canonical route or action identifier.

## T0 verification cases

Run implementation checks through the real Phoenix application boundary and PostgreSQL when T0 is authorized and implemented.

| Case | Expected result |
|---|---|
| Organizer creates and publishes a tenant Event and Occurrence | Rows preserve explicit `org_id`, governed states, versions, and registered events |
| Organization has no Occurrence admission policy | `create_occurrence` fails closed with `ERR_PRECONDITION / EVT_ADMISSION_POLICY_MISSING` |
| Owner/admin sets a policy and creates an Occurrence | Policy requires both non-negative second values (including explicit zero); create uses same-tenant policy and rejects each out-of-policy check-in bound with `ERR_VALIDATION / EVT_CHECK_IN_WINDOW_OUT_OF_POLICY` |
| Organization policy changes after Occurrences exist | Existing persisted check-in windows and their admission decisions remain unchanged |
| Organizer configures the GA offer | ProductRevision binds to reusable `pricing_program_revision_id` and the exact pinned `tax_profile_id` |
| Buyer retrieves a sellable offer | Event, sale-window, Offer, Product, tenant, and parent guards all pass |
| Buyer creates a quote | One transaction-specific signed PRICE-SIG-V4 PricingSnapshot uses the exact TaxProfile and T0 tax locks |
| Buyer claims the last unit concurrently | The SEAT atomic predicate permits at most one successful claim; exhaustion uses `ERR_CONFLICT / SEAT_CAPACITY_EXHAUSTED` |
| First checkout uses bucket proof | `verify_bucket_hold_proofs` verifies current active, unexpired hold state before the effect |
| Buyer repeats a completed identical checkout | Possession actions verify supplied signatures; ORD returns the stored original outcome with zero checkout effects |
| Completed replay supplies an invalid replacement signature | The stored response is withheld and checkout does not execute again |
| Same durable identity uses a different request hash | LOCKS returns `ERR_CONFLICT / LOCKS_IDEMPOTENCY_KEY_REUSE_MISMATCH`; no second effect occurs |
| Tenant-scoped request is cross-tenant or lacks visible context | Boundary returns uniform `ERR_NOT_FOUND` without a hidden-reason subcode |
| T0 quote pins event/customer location tax basis or another rounding mode | Quote fails closed before snapshot creation |
| T0 path reaches checkout event emission | No single-order checkout-created event is emitted |

## Definition of done

- B0 is recorded COMPLETE and T0 remains NEXT.
- The end-to-end T0 path uses installed resource, action, lifecycle, idempotency, tax, event, and error authority without fabricated identities or events.
- A successful T0 checkout persists and retrieves a tenant-scoped ORD-1 `draft` Order.
- New/effectful checkout and completed-identical replay use their separate SEAT-1 verification actions.
- T0 stops before payment confirmation, finalization, allocation, ticket issuance, and ledger work.
- The 53 deferred EVT registry-debt entries and `hold_signature_batch` remain deferred.
