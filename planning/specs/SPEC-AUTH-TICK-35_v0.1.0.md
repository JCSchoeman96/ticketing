# SPEC-AUTH-TICK-35 v0.1.0 — Membership-before-tenant bootstrap authority repair

- **ID:** SPEC-AUTH-TICK-35
- **Version:** 0.1.0
- **Status:** DRAFT — in-chat architecture approved by the user on 2026-10-22; this written artifact is pending user review
- **Nature:** noncanonical authority-repair design record; this document does not itself create Ticketing semantics
- **Plane:** TICK-35 — `[AUTHORITY GAP] TICK-25 organizer membership proof precedes tenant context`
- **Affected implementation work:** TICK-25 and downstream TICK-26+
- **Repository baseline:** `71fe96e24f87f89418719e0f56252a633a8550e8`
- **Baseline tree:** `95e966a168205db06f9c6f7135be14e29366289a`
- **Installed CANON:** CANON-1 `2.0.16`
- **Installed governing contracts:** TEN-1 `2.0.0`, IAM-1 `4.1.2`, IAM-2 `1.5.0`
- **Current downstream packet:** JIP-T0-01 `0.1.2` / SPEC-T0-01 `0.1.1`

This spec is deliberately downstream and noncanonical. Installed canonical authority remains higher authority. The authority gap is resolved only when successor contract release(s), paired test gates, CANON selection, installed artifacts, manifest and strict validation are completed and merged.

## 1. Problem statement

TICK-25 cannot safely implement organizer resolution from the currently installed authority and approved downstream packet.

TEN-1 `2.0.0` requires membership validation before tenant context is established:

- `/tenancy/tenant_resolution/membership_validation/required = true`;
- `/tenancy/tenant_resolution/membership_validation/enforced_before_setting_tenant = true`;
- the contract note says tenant MUST NOT be set until the actor is proven to be a member of the organization, except for a system-internal caller explicitly permitted by policy;
- `TEN-1-GATE-140` is P0/must and locks this ordering.

At the same time, `OrgMembership` is tenant-scoped under IAM-1 and is not in TEN-1's global-resource allowlist. Reading it through the normal runtime boundary therefore requires tenant-scoped database access.

The current downstream spec reverses the required order: it receives authenticated `user_id` + explicit `org_id`, establishes that tenant in Ash/PostgreSQL, then reads `OrgMembership` to prove membership.

That creates a circular bootstrap requirement:

```text
membership proof required before human tenant selection
        ↓
OrgMembership is tenant-scoped
        ↓
tenant-scoped read requires database tenant context
        ↓
current downstream spec sets tenant before proof
```

No installed contract currently names the system-internal policy required to break that cycle.

## 2. Secondary planning inconsistency exposed by the same gap

IAM-1 `4.1.2` already establishes additional canonical requirements that JIP-T0-01 `0.1.2` excluded from implementation scope:

- T0 tenant capabilities require an active organization persona;
- `aal1` represents an authenticated session;
- authorization liveness requires active User, active OrgMembership and active Session;
- organization selection states that Sessions bind `org_id` through `sign_in_with_org` after active OrgMembership validation;
- active `org_membership_id` identifies the selected organization persona.

JIP-T0-01 `0.1.2` instead accepts only an already-authenticated `user_id` + explicit `org_id` and explicitly lists Session persistence/login semantics as a non-goal.

This is downstream planning drift against already-installed IAM authority. It does not require weakening IAM-1. After the canonical tenant-bootstrap gap is repaired, JIP-T0-01 must be treated as stale and re-Grilled so that the minimum canonical Session / active-org-persona substrate is brought into scope without pulling authentication-provider implementation into the increment.

## 3. Approved repair objective

Preserve the existing human-facing invariant:

> A human/request tenant MUST NOT become the resolved tenant until active membership in that organization has been proven.

Define the missing narrow policy anticipated by TEN-1's existing exception:

> A named system-internal membership probe MAY establish transaction-local candidate-organization database scope solely to prove whether an already-authenticated human principal has an active OrgMembership in that candidate organization. Candidate scope is not the human's resolved tenant or active persona. Successful proof permits normal organization-persona/session establishment under IAM-1. Failed proof must not promote, persist or leak the candidate organization.

The repair must keep `membership_validation.enforced_before_setting_tenant = true` for ordinary human/request tenant resolution. It must not turn the exception into a general bypass.

## 4. Required canonical semantics for TEN-1 successor

The successor TEN-1 release must add an explicit policy under the tenant-resolution authority for the membership bootstrap probe. The exact JSON property name may follow existing schema conventions, but the resulting canonical fields must make all of the following machine-testable.

### 4.1 Policy identity and caller boundary

The policy has one stable named purpose: `org_membership_probe` or an equivalently unambiguous canonical identifier.

It MUST state:

- caller boundary is `system_internal_only`;
- the probe acts only on behalf of an already-authenticated human principal whose authoritative `user_id` came from a trusted authentication boundary;
- the candidate `org_id` remains untrusted for authorization until membership proof succeeds;
- the probe does not create a human active persona merely by accepting the candidate `org_id`;
- the probe is not a platform/support impersonation or break-glass path;
- no public client may invoke the probe directly.

### 4.2 Candidate database scope

The policy MAY permit setting `app.current_org_id` before human membership proof only inside this named system-internal probe.

That candidate scope MUST:

- be transaction-local;
- use the ordinary constrained runtime database identity;
- remain subject to ENABLE + FORCE RLS;
- use the same backend transaction/connection as the membership read;
- clear automatically on commit/rollback/pool reuse;
- not weaken `default_deny_when_unset`;
- not grant superuser/BYPASSRLS/owner privileges;
- not change the canonical meaning of normal resolved tenant context outside the probe.

The contract must distinguish candidate probe scope from a successfully resolved human tenant/persona even though both may use the same transaction-local PostgreSQL tenant variable at implementation time.

### 4.3 Allowed resource and operation

The probe is read-only and narrowly bound to `IAM-1.OrgMembership`.

It MUST allow only the minimum membership lookup needed to establish the current principal's relationship to the candidate organization. The authoritative matching input is the already-authenticated `user_id` within the candidate `org_id`.

Before proof succeeds, the probe MUST NOT:

- read `OrgRoleAssignment`;
- read or write Event or any other tenant business resource;
- create/update/revoke OrgMembership;
- create/update/revoke roles;
- create an active organization persona;
- authorize an Event capability;
- convert candidate `org_id` into an authoritative actor claim;
- perform generic arbitrary tenant reads;
- expose a general system actor capable of tenant-domain actions.

### 4.4 Membership proof result

Success requires the canonical IAM-1 membership conditions, including active/non-revoked membership for the authenticated human principal in the candidate organization.

On success:

1. the persisted `org_membership_id` becomes the membership proof for subsequent IAM-1 organization-persona/session construction;
2. subsequent organization role resolution occurs only under the now-proven organization boundary;
3. later tenant actions still require the normal explicit tenant, active persona, role/capability and liveness checks.

The probe itself does not grant `org_owner`, `org_admin` or any other role.

### 4.5 Failure behavior and information hiding

On missing, inactive, revoked or mismatched membership:

- no human tenant/persona/session promotion occurs;
- no candidate organization state is persisted into authorization context;
- no role lookup occurs;
- transaction-local candidate scope is discarded;
- no writes occur;
- boundary behavior follows existing TEN-1 hide-existence requirements and must not reveal whether the organization exists, whether another user belongs to it, or why proof failed;
- internal stable diagnostics may retain the governing tenancy/IAM reason only where already permitted by canonical logging/error policy.

### 4.6 No global-resource reclassification

The repair MUST NOT add `IAM-1.OrgMembership` to TEN-1's global-resource allowlist.

The existing global-resource constraints remain unchanged. The membership probe is a controlled system-internal tenant-resolution exception, not a declaration that membership is global data.

## 5. Paired TEN-1 test-gate requirements

The TEN-1 successor must add a new P0/must gate in the unused ordering slot adjacent to the existing tenant-resolution gate; `TEN-1-GATE-145` is the intended stable ID unless the release tooling reveals a repository rule requiring another unused ID.

The paired gate must machine-check the canonical policy rather than relying only on prose. At minimum it must pin:

1. probe policy enabled and named;
2. caller boundary = system-internal only;
3. authenticated human principal required;
4. candidate organization remains untrusted before proof;
5. candidate scope may be set before proof only for this named probe;
6. candidate scope is transaction-local;
7. FORCE-RLS / non-bypass posture remains required;
8. allowed resource = `IAM-1.OrgMembership` only;
9. operation = read-only membership proof;
10. active membership required for success;
11. role lookup forbidden before proof;
12. other tenant-resource access forbidden before proof;
13. writes forbidden;
14. persona/session promotion forbidden on failure;
15. hide-existence failure behavior required;
16. OrgMembership remains absent from the global-resource allowlist;
17. `membership_validation.enforced_before_setting_tenant` remains `true` for ordinary human tenant resolution.

The successor must retain all existing P0 gates, including `TEN-1-GATE-140`; do not weaken, remove or invert the original invariant.

## 6. Successor release identities

Subject to repository tooling confirming that these successor identities are free and valid, the intended release identities are:

- TEN-1 `2.0.1` succeeding installed TEN-1 `2.0.0`;
- CANON-1 `2.0.17` succeeding installed CANON-1 `2.0.16`.

Accepted release bytes are immutable. Do not modify installed `2.0.0` or `2.0.16` artifacts in place.

The TEN-1 source successor should be prepared under:

`authority/release-src/current/TEN-1/2.0.1/`

using the existing TEN-1 `2.0.0` editable source as the immediate source baseline, with normal provenance/release metadata updated according to repository tooling.

CANON-1 `2.0.17` must be generated from the accepted current CANON + active manifest + explicit TEN-1 `2.0.1` candidate through `authority/tools/generate_canon.py successor`; do not hand-edit CANON selection data.

## 7. Release and installation requirements

Follow `authority/README.md` and `authority/AGENTS.md` exactly.

Required release evidence includes:

- build TEN-1 candidate twice into independent temporary output directories;
- byte-compare ZIP, contract, paired gates and bundle manifest;
- `validate_contract_release.py` success;
- `validate_release_set.py` success against the repository dependency set;
- generate CANON successor deterministically;
- build CANON twice and byte-compare outputs;
- validate CANON candidate and release set;
- install TEN-1 + matching CANON successor together;
- regenerate extracted inspection copies;
- regenerate `authority/contracts/manifest.json`;
- verify installed versions/hashes/dependency closure;
- run full authority tests, manifest verification, CANON verification and strict reconciliation audit;
- run repository CI on the exact PR head.

Do not manually patch generated hashes to force validation success.

## 8. Contracts intentionally unchanged by this authority repair

No successor is required merely to restate already-existing semantics in:

- IAM-1 `4.1.2` — active membership, active persona, Session binding/liveness and Event role capability rules remain governing authority;
- IAM-2 `1.5.0` — authentication/invite/consumer flows are not changed by this repair;
- EVT-1 / EVT-2 — Event semantics are unchanged;
- ERR-1 — existing error taxonomy remains controlling;
- OBS-1 — existing observability/redaction semantics remain controlling.

If release-set validation or targeted review finds an actual dependency contradiction rather than a planning mismatch, stop and widen TICK-35 explicitly instead of silently altering another contract.

## 9. Downstream planning consequence after authority merge

Merging the authority repair does not automatically resume TICK-25.

Because tenant/auth semantics materially change relative to the approved downstream packet:

1. JIP-T0-01 `0.1.2` becomes stale for implementation;
2. run a targeted JIT re-Grill against the newly installed CANON/TEN-1 and current IAM-1;
3. produce JIP-T0-01 `0.1.3` as an explicit amendment;
4. remove `Session persistence` from the blanket non-goals only to the minimum extent required for canonical active Session / active organization persona construction and liveness;
5. keep AuthIdentity/provider authentication/password/magic-link/OAuth/service-token implementation outside T0-01 unless canonical review independently requires otherwise;
6. reconcile SPEC-T0-01 with the corrected bootstrap sequence and Session/persona boundary;
7. require explicit user approval of the amended JIP before execution work resumes;
8. update Plane dependencies/READY state only after the authority and planning freshness gates pass.

## 10. Expected corrected organizer sequence downstream

The intended downstream sequence after the authority repair and JIP reconciliation is:

```text
trusted authentication boundary supplies authoritative human user_id
        ↓
caller supplies candidate org_id
        ↓
system-internal membership probe begins transaction
        ↓
transaction-local candidate org scope installed under named TEN-1 probe policy
        ↓
read only candidate user's OrgMembership
        ↓
active membership proven?
   ┌───────────────┴───────────────┐
   no                              yes
   ↓                               ↓
fail closed / hide existence       persisted org_membership_id established
no roles                           ↓
no persona/session promotion       establish minimum IAM-1 active org Session/persona
candidate scope discarded          ↓
                                   load active OrgRoleAssignment under proven tenant
                                   ↓
                                   evaluate Event capability
```

Events receives a resolved, canonical active organizer persona. Events does not own membership bootstrap logic.

## 11. Explicit non-goals

This authority repair does not authorize or implement:

- application code changes;
- TICK-25 IAM resources/actions;
- TICK-26 Event code;
- a generic tenant bypass;
- a global membership index;
- global/ungenanted OrgMembership reads;
- `authorize?: false` organizer access;
- privileged runtime DB roles;
- direct Repo domain APIs;
- support impersonation/break-glass semantics;
- authentication-provider integration;
- AuthIdentity implementation in T0-01;
- password/magic-link/OAuth/service-token flows;
- UI/login/session-management screens;
- dependency upgrades;
- changes to Event lifecycle, errors or publication events.

## 12. Review focus

Independent review of the authority successor must specifically try to falsify these properties:

1. **Candidate-org confusion:** no caller can treat candidate `org_id` as an authorized human tenant before membership proof.
2. **Probe widening:** the exception cannot become a general system-internal arbitrary tenant read or write channel.
3. **RLS weakening:** probe semantics do not require or permit superuser/BYPASSRLS/owner execution or session-scoped GUC leakage.
4. **Existence leakage:** failed proof is externally indistinguishable from other hidden-not-found tenant boundary failures.
5. **Planning half-fix:** downstream work does not resume with a sessionless organizer actor that still violates installed IAM-1 liveness/persona authority.

## 13. Definition of done for TICK-35 authority phase

The authority phase is complete only when all of the following are true:

- successor TEN-1 and CANON releases are deterministically built and validated;
- exact successor ZIPs and extracted artifacts are installed;
- manifest and CANON selection are coherent;
- full authority validation and exact-head CI pass;
- authority PR exact diff receives independent review;
- the authority PR is merged;
- post-merge current `main` and required CI are verified;
- Plane TICK-35 records the merged authority evidence;
- targeted JIT re-Grill identifies the exact JIP/spec amendments required before TICK-25;
- TICK-25 and TICK-26 remain non-READY until that downstream planning work is explicitly approved and freshness-checked.

This document itself never closes TICK-35 and never grants implementation READY status.
