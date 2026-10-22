# TICK-36 Trusted Session Consumption Authority Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- **Plan ID:** PLAN-AUTH-TICK-36
- **Version:** 0.1.0
- **Status:** APPROVED
- **Approved:** user instruction on 2026-10-22 — `Approve PLAN-AUTH-TICK-36 v0.1.0`
- **Execution baseline:** `d54696e15481ca14c91b70f9fa6a1ca648a28031`
- **Execution baseline tree:** `cc9ef915a7a251b06c0e048d9aecce7fefb0d6d3`
- **Execution baseline evidence:** PR #26 merge (TICK-38 `ubuntu-24.04` runner pin); Authority checks run `39794394538` SUCCESS and CI run `39794394459` SUCCESS on that exact SHA. The intervening delta from the plan-creation baseline is limited to `.github/workflows/authority.yml` and `.github/workflows/ci.yml` runner pins, reviewed and recorded as nonsemantic to TICK-36.
- **Plan-creation baseline (historical, preserved):** `c3068a7c3f5f7192d1bc354d8bd6f4f138b01540`
- **Plan-creation baseline tree (historical, preserved):** `843023aed0f56356dee877d4d1480afc28e88578`
- **Approved spec commit:** `7d7c214afd2f5f92394ff554f8d012c23eb6b482`
- **Working branch:** `authority/tick-36-session-consumption`

**Goal:** Resolve TICK-36 by releasing IAM-1 `4.1.3` with a narrow trusted active-Session consumption/liveness policy for T0 organizer authorization, selecting it through CANON-1 `2.0.18`, installing the exact deterministic artifacts, and opening a validated authority PR without resuming TICK-25.

**Architecture:** T0 remains a consumer of an already-issued canonical IAM Session, not a Session issuer. The trusted authentication/session boundary supplies authoritative `user_id + session_id`; TEN-1 `org_membership_probe` proves membership first; only then may T0 validate the persisted same-org Session and active persisted role/persona before Event capability evaluation. The repair is IAM-only plus the required CANON successor, preserves EVT-1's explicit T0 no-session-event quarantine, and does not change TEN-1, IAM-2, EVT-1, ERR-1, OBS-1, application code, or dependencies.

**Tech Stack:** Ticketing authority JSON contracts/test gates, Python release tooling under `authority/tools/`, deterministic ZIP construction, pytest authority verification, Git/GitHub CI.

**Spec:** `planning/specs/SPEC-AUTH-TICK-36_v0.1.0.md`

## Global Constraints

- Begin from freshly verified GitHub `main`; expected baseline is `c3068a7c3f5f7192d1bc354d8bd6f4f138b01540`, tree `843023aed0f56356dee877d4d1480afc28e88578`.
- The merged PR #25 tree is byte-identical to its final tested PR head, but baseline post-merge Authority/CI runs failed before executing any job step. **Do not begin IAM successor authoring until a fresh post-merge Authority run and CI run on current `main` actually execute and pass.** If they still fail pre-execution, record the external/platform blocker and STOP.
- Installed authority at spec approval: CANON-1 `2.0.17`, TEN-1 `2.0.1`, IAM-1 `4.1.2`, IAM-2 `1.5.0`, EVT-1 `3.0.0`.
- Intended successors: IAM-1 `4.1.3`, CANON-1 `2.0.18`. STOP if either identity is no longer free or governing authority moved materially.
- Accepted release bytes are immutable. Never mutate installed IAM-1 `4.1.2` or CANON-1 `2.0.17` bytes in place.
- TEN-1 `org_membership_probe` remains exactly selected and unchanged. Membership proof must precede Session and role reads.
- T0 receives authoritative `user_id + session_id` from trusted authentication/session infrastructure. T0 receives no raw Session token and does not derive/verify `token_hash`.
- T0 MUST NOT issue, refresh, rebind, revoke, mutate, or write `last_seen_at_utc` on Session and MUST NOT emit `ticketing.iam.session.created.v1` or `ticketing.iam.session.revoked.v1`.
- Session liveness is time-of-use and uses authoritative database UTC time: exact id/user/org match, `status=active`, `revoked_at_utc=nil`, `expires_at_utc > evaluated_at_utc`.
- Active persona is explicit: T0 tenant capabilities require `active_scope=org`; requested `active_role` is only a selector and must be backed by one active/non-revoked same-org persisted `OrgRoleAssignment`.
- Active User, active/non-revoked OrgMembership, active Session, and active role assignment remain required. Caller-supplied role lists never grant authority.
- Session validation failure is uniform `ERR_UNAUTHENTICATED` using the existing IAM session-invalid/expired posture; role/capability denial remains `ERR_FORBIDDEN` under ordinary same-tenant authorization semantics.
- No TEN-1, IAM-2, EVT-1, ERR-1, OBS-1, ROADMAP, tracer, JIP, application, migration, dependency, or frontend change is authorized by this plan.
- Store reference baseline refreshed during re-Grill: `aab23f6afb924828a6f3b3c43bf069b304b6585e`; current delta is `REFERENCE_ONLY` / not applicable to this narrow IAM authority repair.
- LiveFrames reference baseline refreshed during re-Grill: `3689b2e302cd5afe96430b72c127a3ffcec2ef98`; `NOT_APPLICABLE`.
- TICK-25 and TICK-26 remain non-READY throughout this authority plan.
- Follow root `AGENTS.md`, `authority/AGENTS.md`, and `authority/README.md` exactly. Never patch generated hashes or generated CANON selection data by hand.

## Review Focus

1. **Trusted-id confusion:** `session_id`, `user_id`, candidate `org_id`, or requested role must never independently grant tenant/persona authority.
2. **Ordering regression:** no Session or role lookup occurs before TEN-1 membership proof succeeds.
3. **Session issuer creep:** no raw token handling, Session mutation, refresh/rebind/revoke, or IAM Session event emission enters T0.
4. **Persona spoofing:** capability evaluation uses the verified persisted `active_role`, not a broader caller-provided or merely-present role set.
5. **Cross-contract drift:** EVT-1 T0 quarantine, TEN-1 probe, IAM-2 selection, and every unrelated CANON member remain unchanged.

---

### Task 1: Re-establish freshness and the authority execution gate

**Files:**
- Read: `AGENTS.md`
- Read: `authority/AGENTS.md`
- Read: `authority/README.md`
- Read: `planning/specs/SPEC-AUTH-TICK-36_v0.1.0.md`
- Read: `authority/contracts/manifest.json`
- Read: installed CANON-1/TEN-1/IAM-1/IAM-2/EVT-1 extracted artifacts
- Read: `authority/release-src/current/IAM-1/4.1.2/{contract.json,test-gates.json,release.json,provenance.json}`

**Interfaces:**
- Consumes: approved SPEC-AUTH-TICK-36 v0.1.0.
- Produces: verified fresh baseline and permission to begin semantic authority authoring.

- [ ] **Step 1: Load execution/process skills before repo work**

Use `superpowers:using-git-worktrees` before creating/reusing an isolated execution worktree. Authority semantics follow repository authority instructions; downstream application implementation skills do not override them.

- [ ] **Step 2: Fetch and verify `origin/main`**

Expected at plan creation:

```text
SHA  c3068a7c3f5f7192d1bc354d8bd6f4f138b01540
tree 843023aed0f56356dee877d4d1480afc28e88578
```

If `main` moved, inspect the complete delta. STOP on material changes to CANON, IAM-1, TEN-1, IAM-2, EVT-1, authority tooling, ROADMAP/tracer, TICK-36 prerequisites, or the approved spec.

- [ ] **Step 3: Clear the pre-execution CI blocker**

Obtain fresh runs for current `main` for both repository workflows that previously gated PR #25:

```text
Authority checks
CI
```

Required evidence: jobs actually start, execute steps, and finish SUCCESS. A zero-step cancellation/failure is not a passing gate even if the current tree equals a previously tested PR tree.

If GitHub still refuses to execute the jobs, record the run/job evidence in Plane and STOP. Do not author IAM-1 `4.1.3` while freshness execution remains unverified.

- [ ] **Step 4: Verify installed authority and successor identities**

Prove manifest/CANON select exactly:

```text
CANON-1 2.0.17
TEN-1   2.0.1
IAM-1   4.1.2
IAM-2   1.5.0
EVT-1   3.0.0
```

Confirm `authority/release-src/current/IAM-1/4.1.3/` and `authority/release-src/current/CANON-1/2.0.18/` do not already exist with another meaning.

- [ ] **Step 5: Verify Plane state and branch inventory**

TICK-36 remains In Progress; TICK-25 is blocked by TICK-36 and non-READY; TICK-26 remains non-READY. Before semantic work, the branch should contain only the approved TICK-36 spec and this plan relative to fresh main. Unexpected files are a STOP.

---

### Task 2: Write the focused canonical RED test

**Files:**
- Create: `authority/tests/test_iam_t0_trusted_session_policy.py`
- Reference: `authority/tests/test_iam_t0_authority_closure.py`
- Reference: `authority/tests/test_ten_membership_probe_policy.py`

**Interfaces:**
- Consumes: manifest-selected installed canonical bundles.
- Produces: permanent executable proof that IAM-1 `4.1.2` lacks the approved trusted-session policy/context shape and that the eventual selected successor preserves TEN/EVT/IAM cross-contract constraints.

- [ ] **Step 1: Reuse the manifest-selected bundle loader pattern**

Load `authority/contracts/manifest.json`, open the selected release ZIPs, and assert CANON pins the same version/path. Do not test `release-src` as though it were canonical.

- [ ] **Step 2: Add `test_selected_iam1_defines_t0_trusted_active_session_policy`**

Assert `authorization_model.t0_trusted_active_session` exists and equals the approved policy values defined in Task 3, including exact Python value types.

- [ ] **Step 3: Add `test_selected_iam1_auth_context_exposes_active_scope_and_role`**

Assert the selected IAM-1 `authorization_model.auth_context_shape` explicitly contains:

```text
active_scope = atom constrained to org|platform
active_role  = string
```

Also assert existing `active_persona_required`, active-persona rule, and T0 tenant capability org-persona requirements remain unchanged.

- [ ] **Step 4: Add `test_selected_iam1_gate_370_locks_trusted_session_policy`**

Assert exactly one paired gate exists with:

```text
id = IAM-1-GATE-370-T0-TRUSTED-SESSION-CONSUMPTION
level = P0
must = true
enforced_by = pytest
```

Require the gate to reference this focused pytest test and to pin the policy/context fields that are scalar/structurally stable.

- [ ] **Step 5: Add `test_t0_session_consumption_preserves_ten_and_evt_quarantine`**

Assert all of the following from manifest-selected installed bundles:

- TEN-1 still selects `org_membership_probe` with `role_lookup_before_proof_allowed=false` and `other_tenant_resource_access_before_proof_allowed=false`;
- IAM-2 selected version remains `1.5.0`;
- EVT-1 still marks `ticketing.iam.session.created.v1` and `ticketing.iam.session.revoked.v1` as T0 deferred/quarantined and explicitly non-emitted by T0;
- no tested assertion treats Session or OrgMembership as a global resource.

- [ ] **Step 6: Run focused RED and capture the expected failures**

From repository root:

```bash
PYTHONPATH=authority python3 -m pytest -q authority/tests/test_iam_t0_trusted_session_policy.py
```

Expected on IAM-1 `4.1.2`: policy/context/gate assertions fail because the successor semantics do not yet exist, while the preserved TEN/EVT/IAM-2 assertions should already pass.

If the whole file passes before successor authoring, STOP because the RED test does not prove the gap.

Suggested commit:

```text
test(TICK-36): lock trusted session consumption authority
```

---

### Task 3: Author IAM-1 `4.1.3` successor source

**Files:**
- Create: `authority/release-src/current/IAM-1/4.1.3/contract.json`
- Create: `authority/release-src/current/IAM-1/4.1.3/test-gates.json`
- Create: `authority/release-src/current/IAM-1/4.1.3/release.json`
- Create: `authority/release-src/current/IAM-1/4.1.3/provenance.json`

**Interfaces:**
- Consumes: exact editable IAM-1 `4.1.2` source and RED tests.
- Produces: IAM-1 `4.1.3` candidate source with only the approved trusted-session delta.

- [ ] **Step 1: Copy the immediate source baseline**

Copy all four source files from:

```text
authority/release-src/current/IAM-1/4.1.2/
```

to:

```text
authority/release-src/current/IAM-1/4.1.3/
```

Do not copy/edit installed ZIP or extracted canonical artifacts in place.

- [ ] **Step 2: Update successor identity/provenance mechanically**

Update contract version, paired gate `contract_ref`, the existing version-pin gate expectation, release metadata, and provenance from `4.1.2` to `4.1.3` using the exact current installed IAM-1 `4.1.2` ZIP hash/bytes as immediate source provenance. Use one explicit UTC generation timestamp consistently where tooling requires it.

`release.json` keeps `source_provenance.kind = "installed-canonical-successor"` and changes the release intent to this trusted-session consumption repair.

Append one new change-log entry. Do not rewrite historical entries.

- [ ] **Step 3: Add the canonical policy at `authorization_model.t0_trusted_active_session`**

The object must use these exact fields and values:

```text
enabled = true
policy_id = "t0_trusted_active_session"
caller_boundary = "trusted_authentication_session_infrastructure"
public_clients_allowed = false
authoritative_user_id_required = true
authoritative_session_id_required = true
raw_session_token_available_to_t0 = false
membership_probe_policy_id = "org_membership_probe"
membership_proof_required_before_session_read = true
membership_proof_required_before_role_read = true
session_resource = "IAM-1.Session"
session_read_only = true
session_match_fields = ["id", "user_id", "org_id"]
session_match_sources.id = "authoritative_session_id"
session_match_sources.user_id = "authoritative_user_id"
session_match_sources.org_id = "proven_org_id"
session_status_required = "active"
session_revoked_at_utc_required = null
session_expiry_rule = "expires_at_utc > database_evaluated_at_utc"
database_time_required = true
user_status_required = "active"
membership_status_required = "active"
membership_revoked_at_utc_required = null
active_scope_required_for_t0_tenant_capabilities = "org"
role_assignment_resource = "IAM-1.OrgRoleAssignment"
role_assignment_status_required = "active"
role_assignment_revoked_at_required = null
active_role_is_selector_only = true
active_role_must_match_persisted_assignment = true
capability_evaluated_against_active_role_only = true
platform_support_personas_allowed_for_t0_tenant_capabilities = false
caller_supplied_role_list_authoritative = false
session_mutations_allowed = false
session_events_emitted = []
session_failure_code = "ERR_UNAUTHENTICATED"
session_failure_subcode = "IAM_SESSION_EXPIRED"
role_failure_code = "ERR_FORBIDDEN"
```

Add concise normative notes only for the already-approved distinctions: the trusted IDs are authentication results rather than authorization grants; TEN membership proof comes first; T0 validates persisted state and does not issue/mutate Sessions.

Do not add Session token-generation, hashing, TTL issuance, refresh, revoke, `auth_strategy`, provider, AuthIdentity, or event-production semantics.

- [ ] **Step 4: Make active persona fields explicit in `auth_context_shape`**

Add:

```text
active_scope: atom constrained to [org, platform]
active_role: string
```

Do not change existing actor/user/org/session/assurance fields. The new policy still requires `active_scope=org` for the T0 tenant path.

- [ ] **Step 5: Add paired P0 gate `IAM-1-GATE-370-T0-TRUSTED-SESSION-CONSUMPTION`**

Requirements:

```text
id = "IAM-1-GATE-370-T0-TRUSTED-SESSION-CONSUMPTION"
level = "P0"
must = true
enforced_by = "pytest"
```

Use the established IAM property-test gate style to reference:

```text
authority/tests/test_iam_t0_trusted_session_policy.py
```

and its focused test functions. Add `json_pointer_equals` assertions where the current gate schema supports them cleanly for stable scalar/list values. Do not invent a new assertion type merely to encode nested negative semantics; the focused pytest is the executable cross-contract proof.

- [ ] **Step 6: Inspect the semantic source diff against 4.1.2**

Expected changes only:

1. successor version/timestamp/provenance/release metadata;
2. one new change-log entry;
3. `authorization_model.t0_trusted_active_session`;
4. explicit `active_scope` / `active_role` auth-context fields;
5. one new paired P0 gate plus mechanical version-pin updates.

Any unrelated IAM capability, role, Session schema, outbox-event, telemetry, AuthIdentity, token, invitation, or assurance change is a STOP.

Suggested commit:

```text
fix(TICK-36): define trusted active session consumption
```

---

### Task 4: Deterministically build and validate IAM-1 `4.1.3`

**Files:**
- Read/build: `authority/release-src/current/IAM-1/4.1.3/*`
- Temporary outputs only: `/tmp/tick36-iam-build-one`, `/tmp/tick36-iam-build-two`

**Interfaces:**
- Consumes: Task 3 candidate source.
- Produces: byte-identical validated IAM-1 `4.1.3` release candidates.

- [ ] **Step 1: Build twice from `authority/`**

```bash
python tools/build_contract_release.py \
  --source release-src/current/IAM-1/4.1.3/ \
  --output /tmp/tick36-iam-build-one \
  --allow-candidate

python tools/build_contract_release.py \
  --source release-src/current/IAM-1/4.1.3/ \
  --output /tmp/tick36-iam-build-two \
  --allow-candidate
```

- [ ] **Step 2: Byte-compare deterministic outputs**

Compare the two IAM ZIPs and every generated member (`contract`, `test gates`, `bundle.manifest.json`). Any byte difference is a STOP and must be explained before proceeding.

- [ ] **Step 3: Validate candidate and release closure**

```bash
python tools/validate_contract_release.py \
  /tmp/tick36-iam-build-one/IAM-1_bundle_v4.1.3.zip

python tools/validate_release_set.py \
  --candidate /tmp/tick36-iam-build-one/IAM-1_bundle_v4.1.3.zip \
  --root .
```

Expected: VALID with no unresolved/below-floor dependency errors.

- [ ] **Step 4: Inspect exact candidate semantics**

Open the built ZIP, not only source files. Confirm the built contract/gates contain exactly the approved policy/context/gate and preserve existing IAM Session event declarations unchanged.

---

### Task 5: Generate and validate CANON-1 `2.0.18`

**Files:**
- Create via tooling: `authority/release-src/current/CANON-1/2.0.18/*`
- Temporary outputs: `/tmp/tick36-canon-build-one`, `/tmp/tick36-canon-build-two`

**Interfaces:**
- Consumes: validated IAM-1 `4.1.3` candidate plus active CANON-1 `2.0.17` and manifest.
- Produces: deterministic CANON-1 `2.0.18` candidate selecting only IAM-1 `4.1.3` as the semantic member change.

- [ ] **Step 1: Generate successor through repository tooling only**

From `authority/`:

```bash
python tools/generate_canon.py successor \
  --root . \
  --candidate /tmp/tick36-iam-build-one/IAM-1_bundle_v4.1.3.zip \
  --version 2.0.18 \
  --output-dir release-src/current/CANON-1/2.0.18 \
  --generated-at-utc <same-approved-build-UTC>
```

Do not hand-edit generated CANON selection/hashes/provenance.

- [ ] **Step 2: Inspect CANON selection delta before building**

Required semantic selection delta:

```text
IAM-1 4.1.2 -> 4.1.3
```

Everything else—including TEN-1 `2.0.1`, IAM-2 `1.5.0`, EVT-1 `3.0.0`, membership/dependency-only statuses, and unrelated hashes/paths—must remain unchanged except generator-owned provenance fields.

- [ ] **Step 3: Build CANON twice**

```bash
python tools/build_contract_release.py \
  --source release-src/current/CANON-1/2.0.18/ \
  --output /tmp/tick36-canon-build-one \
  --allow-candidate

python tools/build_contract_release.py \
  --source release-src/current/CANON-1/2.0.18/ \
  --output /tmp/tick36-canon-build-two \
  --allow-candidate
```

Byte-compare ZIP and every generated member. Any difference is a STOP.

- [ ] **Step 4: Validate CANON and the combined release set**

Run candidate validation for CANON and release-set validation with both IAM and CANON candidates using the tool's supported repeated-candidate form. Expected: VALID with complete dependency closure and no unrelated selection drift.

Suggested commit after validated generated source:

```text
build(TICK-36): generate CANON 2.0.18
```

---

### Task 6: Install exact IAM/CANON bytes and turn RED to GREEN

**Files:**
- Replace active installed ZIP selection: `authority/contracts/IAM-1/IAM-1_bundle_v4.1.2.zip` -> exact validated `IAM-1_bundle_v4.1.3.zip`
- Replace active installed ZIP selection: `authority/contracts/CANON-1/CANON-1_bundle_v2.0.17.zip` -> exact validated `CANON-1_bundle_v2.0.18.zip`
- Regenerate: `authority/contracts/IAM-1/extracted/*`
- Regenerate: `authority/contracts/CANON-1/extracted/*`
- Regenerate: `authority/contracts/manifest.json`
- Test: `authority/tests/test_iam_t0_trusted_session_policy.py`

**Interfaces:**
- Consumes: exact build-one IAM and CANON ZIPs.
- Produces: installed canonical suite selecting IAM-1 `4.1.3` through CANON-1 `2.0.18`.

- [ ] **Step 1: Install only exact validated build-one ZIP bytes**

Follow the repository's current one-active-ZIP-per-doc installation convention. Preserve superseded accepted bytes through Git history; do not modify them in place or rebuild during install.

- [ ] **Step 2: Regenerate extracted copies and manifest**

From `authority/`:

```bash
python tools/contract_manifest.py extract IAM-1 --root .
python tools/contract_manifest.py extract CANON-1 --root .
python tools/contract_manifest.py generate --root .
```

- [ ] **Step 3: Run focused GREEN**

From repository root:

```bash
PYTHONPATH=authority python3 -m pytest -q authority/tests/test_iam_t0_trusted_session_policy.py
```

Expected: all focused tests PASS against manifest-selected installed canonical bundles.

- [ ] **Step 4: Verify manifest/CANON exact selection**

Confirm IAM-1 and CANON identities/hashes match the exact build-one ZIPs; TEN/IAM-2/EVT-1 remain unchanged.

Suggested commit:

```text
chore(TICK-36): install IAM 4.1.3 and CANON 2.0.18
```

---

### Task 7: Run full authority and application-side verification

**Files:**
- No new semantic files expected beyond Tasks 2-6.
- Temporary audit outputs only under `/tmp/`.

**Interfaces:**
- Consumes: installed candidate suite.
- Produces: fresh local verification evidence suitable for independent PR review.

- [ ] **Step 1: Run the documented full authority suite**

From repository root:

```bash
PYTHONPATH=authority python3 -m pytest -q authority/tests
python3 authority/tools/contract_manifest.py verify --root authority
python3 authority/tools/generate_canon.py verify --root authority
python3 authority/tools/reconcile_contracts.py audit --canonical --strict --root authority \
  --json-output /tmp/tick36-authority-audit.json \
  --markdown-output /tmp/tick36-authority-audit.md
```

Expected: all tests PASS, manifest VALID, CANON verification VALID, strict audit PASS with zero blocking dependency issues.

- [ ] **Step 2: Reproduce generated CANON files byte-for-byte**

Regenerate CANON-1 `2.0.18` from the same base manifest/CANON and exact IAM candidate into a separate temporary directory and compare every generator-owned file with tracked `release-src/current/CANON-1/2.0.18/` bytes. Any difference is a STOP.

- [ ] **Step 3: Run application-side authority verification without dependency movement**

Using the repository-pinned runtime and existing local ignored credentials without printing secrets:

```bash
cd ticketing
mix contract.authority
```

Do not change `mix.lock`, dependency versions, application source, DB schema, or credentials to make this pass.

- [ ] **Step 4: Inspect exact branch diff and repository cleanliness**

Required changed-file classes only:

```text
planning/specs/SPEC-AUTH-TICK-36_v0.1.0.md
planning/plans/2026-10-22-tick-36-trusted-session-consumption-authority-repair_v0.1.0.md
authority/tests/test_iam_t0_trusted_session_policy.py
authority/release-src/current/IAM-1/4.1.3/*
authority/release-src/current/CANON-1/2.0.18/*
authority/contracts/IAM-1/*
authority/contracts/CANON-1/*
authority/contracts/manifest.json
```

Mechanical authority tests may change only if the full suite exposes stale-version assumptions analogous to TICK-35; any such expansion requires explicit evidence and must not alter product semantics.

Run:

```bash
git diff --check
```

Expected: PASS; worktree clean after commits.

---

### Task 8: Open the authority PR and stop for independent review

**Files:**
- No additional product semantics.

**Interfaces:**
- Consumes: complete verified branch.
- Produces: open PR plus exact-head CI evidence and a `READY FOR REVIEW` handoff; never self-merges.

- [ ] **Step 1: Refresh `main` immediately before PR handoff**

If `main` moved, inspect the delta and STOP on material authority/prerequisite movement. Rebase/refresh only through a reviewed, non-semantic path.

- [ ] **Step 2: Push `authority/tick-36-session-consumption` and open one authority PR**

PR title should identify TICK-36 and the IAM trusted-session authority repair. The body must include:

- approved spec/plan links;
- baseline/current main SHA;
- IAM/CANON successor identities;
- RED evidence;
- double-build hashes/byte-equality evidence;
- candidate/release-set validation;
- focused GREEN/full authority verification;
- strict audit/CANON/manifest results;
- `mix contract.authority` result;
- explicit statement that T0 remains a Session consumer and emits no IAM Session events;
- explicit unchanged TEN-1/IAM-2/EVT-1 evidence;
- exact changed-file inventory;
- TICK-25/TICK-26 remain non-READY.

- [ ] **Step 3: Require exact-head GitHub CI**

Both Authority checks and repository CI for the exact PR head must actually execute and finish SUCCESS. Zero-step/pre-execution failures are not green.

- [ ] **Step 4: Update Plane and stop**

Set TICK-36 execution ledger to `READY FOR REVIEW` evidence only; do not mark Done, do not release TICK-25, do not merge. Return the PR number, exact head SHA/tree, validation evidence, and any residual risks for independent control-tower review.

---

## Post-merge control-tower handoff

This plan does not authorize the coding agent to self-merge. After independent review and explicit user merge:

1. verify signed merge SHA/tree and that merged tree equals the reviewed PR head tree;
2. require fresh post-merge Authority and CI runs that actually execute and pass;
3. run the targeted re-Grill against installed IAM-1 `4.1.3`, TEN-1 `2.0.1`, IAM-2 `1.5.0`, EVT-1 `3.0.0` and the current technical/reference baseline;
4. close TICK-36 only if no residual Session/persona authority gap remains;
5. reconcile TICK-35 closure evidence;
6. prepare JIP-T0-01 `0.1.3` and a corresponding SPEC-T0-01 successor for explicit user approval;
7. only after those approvals and fresh dependency checks may TICK-25 receive READY.

## Plan self-review result

- **Spec coverage:** every approved TICK-36 requirement maps to Tasks 2-7 or the post-merge handoff.
- **Scope:** one authority subsystem (IAM-1 trusted Session consumption) plus mechanically required CANON selection; no independent feature was mixed in.
- **Type/name consistency:** policy path is fixed as `authorization_model.t0_trusted_active_session`; gate ID fixed as `IAM-1-GATE-370-T0-TRUSTED-SESSION-CONSUMPTION`; successor versions fixed as IAM-1 `4.1.3` and CANON-1 `2.0.18` subject to freshness checks.
- **Review-focus coverage:** focused tests cover trusted-ID confusion, membership-before-Session ordering, read-only/no-event constraints, persisted active-role persona, and TEN/EVT/IAM-2 cross-contract preservation.
- **Proportion:** the plan specifies decisions, evidence, commands, and task boundaries without implementing contract bodies in advance.