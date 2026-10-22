# TICK-35 Membership Bootstrap Authority Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve TICK-35 by releasing TEN-1 `2.0.1` with a narrowly bounded system-internal membership-probe policy, selecting it through CANON-1 `2.0.17`, installing the exact deterministic artifacts, and opening a validated authority PR without resuming TICK-25.

**Architecture:** Preserve TEN-1's ordinary membership-before-human-tenant invariant and add one explicit exception already anticipated by TEN-1: a system-internal, transaction-local, FORCE-RLS-constrained probe that may read only `IAM-1.OrgMembership` for the authenticated user in a candidate organization. Gate the new semantics directly in the paired TEN-1 P0 test gates, generate CANON through repository tooling, and treat every generated ZIP/hash/extracted artifact as immutable release output. No application implementation or downstream JIP correction occurs in this plan.

**Tech Stack:** Repository authority JSON contracts/test gates, Python release tooling under `authority/tools/`, deterministic ZIP generation, pytest authority verification, Git/GitHub CI.

**Spec:** `planning/specs/SPEC-AUTH-TICK-35_v0.1.0.md`

## Global Constraints

- Begin from verified GitHub `main` `71fe96e24f87f89418719e0f56252a633a8550e8`, tree `95e966a168205db06f9c6f7135be14e29366289a`, unless a fresh check proves `main` has moved only in a non-material way.
- Installed authority at plan approval is CANON-1 `2.0.16`, TEN-1 `2.0.0`, IAM-1 `4.1.2`, IAM-2 `1.5.0`.
- Accepted installed release bytes are immutable. Never edit TEN-1 `2.0.0` or CANON-1 `2.0.16` release ZIPs/extracted artifacts in place.
- Intended successors are TEN-1 `2.0.1` and CANON-1 `2.0.17`; stop if either identity is no longer free or the current installed selection changes.
- `TEN-1-GATE-140` remains P0/must and `/tenancy/tenant_resolution/membership_validation/enforced_before_setting_tenant` remains `true`.
- `IAM-1.OrgMembership` remains tenant-scoped and MUST NOT be added to TEN-1's global-resource allowlist.
- The new probe is system-internal only, read-only, scoped to the authenticated human user's membership in one candidate `org_id`, and MUST NOT read roles or other tenant business resources before membership proof.
- Candidate DB scope remains transaction-local, same-backend, ordinary constrained runtime, FORCE-RLS protected, non-superuser, non-BYPASSRLS, non-owner.
- Failure must not promote/persist candidate tenant, create persona/session state, perform role lookup, write data, or leak organization/membership existence.
- No IAM-1/IAM-2/EVT/ERR/OBS successor is authorized by this plan. If release validation exposes a real dependency contradiction, STOP and widen TICK-35 explicitly.
- No `ticketing/` application code, dependency, migration, JIP, downstream spec, or Plane READY state changes are allowed in the authority PR.
- TICK-25 and TICK-26 remain non-READY throughout this plan.
- Follow root `AGENTS.md`, `authority/AGENTS.md`, and `authority/README.md` exactly; generated hashes are evidence, never values to patch manually.

## Review Focus

1. **Candidate-org authorization confusion:** setting candidate DB scope for the probe must never mean the human now owns an active tenant/persona.
2. **Probe widening:** the canonical object must machine-lock `IAM-1.OrgMembership` as the only pre-proof tenant resource and read-only proof as the only operation.
3. **RLS bypass:** no wording or field may imply superuser, BYPASSRLS, table-owner, session-scoped tenant state, or cross-connection behavior.
4. **Existence leakage:** failed membership proof must preserve the existing TEN-1 hide-existence boundary and leave no role/persona/session promotion.
5. **Half-fix downstream:** the authority PR must explicitly leave the existing IAM-1 Session/active-persona mismatch for the post-merge targeted re-Grill; TICK-25 must not become READY merely because TEN-1 is repaired.

---

### Task 1: Verify the authority execution gate and isolate the branch

**Files:**
- Read: `AGENTS.md`
- Read: `authority/AGENTS.md`
- Read: `authority/README.md`
- Read: `planning/specs/SPEC-AUTH-TICK-35_v0.1.0.md`
- Read: `authority/contracts/manifest.json`
- Read: `authority/contracts/CANON-1/extracted/CANON-1_Contract_v2.0.16.json`
- Read: `authority/contracts/TEN-1/extracted/TEN-1_Contract_v2.0.0.json`
- Read: `authority/contracts/TEN-1/extracted/TEN-1_Test_Gates_v2.0.0.json`
- Read: `authority/contracts/IAM-1/extracted/IAM-1_Contract_v4.1.2.json`
- Read: `authority/release-src/current/TEN-1/2.0.0/{contract.json,test-gates.json,release.json,provenance.json}`

**Interfaces:**
- Consumes: approved SPEC-AUTH-TICK-35 v0.1.0 and installed canonical suite.
- Produces: a verified immutable baseline and an isolated authority worktree/branch safe for successor authoring.

- [ ] **Step 1: Load required execution skills before repo work**

Use `superpowers:using-git-worktrees` and the repository's authority instructions. Do not use the application implementation skill as authority semantics.

- [ ] **Step 2: Fetch and verify current `origin/main`**

Run the normal repository Git commands to prove the exact current `main` SHA/tree and compare to:

```text
71fe96e24f87f89418719e0f56252a633a8550e8
95e966a168205db06f9c6f7135be14e29366289a
```

Expected: either exact match, or a reviewed newer `main` whose delta does not touch/alter CANON, TEN-1, IAM-1, authority tooling, TICK-35 spec, ROADMAP/tracer semantics, or TICK-35 prerequisites. Any material movement is a STOP.

- [ ] **Step 3: Verify installed release identities from canonical files, not memory**

Confirm manifest/CANON select:

```text
CANON-1 2.0.16
TEN-1   2.0.0
IAM-1   4.1.2
IAM-2   1.5.0
```

Confirm `authority/release-src/current/TEN-1/2.0.1/` and `authority/release-src/current/CANON-1/2.0.17/` do not already exist.

- [ ] **Step 4: Verify TICK-35 remains the blocking authority gap**

Plane must show TICK-25 blocked/non-READY and TICK-26 Todo/non-READY. Do not alter their execution state in this authority plan.

- [ ] **Step 5: Create or reuse the isolated authority worktree/branch**

Use branch:

```text
authority/tick-35-membership-bootstrap
```

If the branch already contains only the approved spec + this execution plan on top of the verified base, continue there. Otherwise STOP and reconcile before authoring contract bytes.

---

### Task 2: Prepare TEN-1 `2.0.1` successor source and establish RED gate evidence

**Files:**
- Create directory: `authority/release-src/current/TEN-1/2.0.1/`
- Create from immediate source baseline: `contract.json`
- Create from immediate source baseline: `test-gates.json`
- Create/update successor metadata: `release.json`
- Create/update successor provenance: `provenance.json`

**Interfaces:**
- Consumes: installed TEN-1 `2.0.0` source and approved spec.
- Produces: a successor source candidate whose new paired gate initially fails until the contract contains the approved probe semantics.

- [ ] **Step 1: Copy the immediate TEN-1 source baseline**

Copy the four source files from:

```text
authority/release-src/current/TEN-1/2.0.0/
```

to:

```text
authority/release-src/current/TEN-1/2.0.1/
```

Do not copy or mutate installed ZIP/extracted artifacts under `authority/contracts/TEN-1/`.

- [ ] **Step 2: Normalize successor identity metadata only**

Set successor source identity consistently to `2.0.1` in `contract.json`, `test-gates.json`, and `release.json` wherever the current-source schema binds version/release identity. Use one execution timestamp consistently where release tooling expects generated timestamps.

Append a TEN-1 change-log entry that says, in substance and without broadening scope:

```text
Define the explicit system-internal org_membership_probe that may establish
transaction-local candidate-org scope solely to prove an already-authenticated
human's active IAM-1.OrgMembership, while preserving ordinary
membership-before-tenant, FORCE RLS, hide-existence, and tenant-scoped
OrgMembership semantics.
```

Do not rewrite historical change-log entries.

- [ ] **Step 3: Rewrite successor provenance against the installed TEN-1 `2.0.0` release**

`provenance.json` must identify the immediate accepted source baseline as the installed TEN-1 `2.0.0` ZIP and record its exact current manifest hash/byte evidence. Do not retain the old 1.7.13/staging-bootstrap statement as though it were the source of 2.0.1.

Record the verified repository preparation base SHA. Provenance must clearly say this is a semantic successor for TICK-35, not mechanical normalization of old staging material.

- [ ] **Step 4: Add the new P0 gate before adding the contract object**

Insert `TEN-1-GATE-145` adjacent to `TEN-1-GATE-140`/the next tenant-resolution gate. It must be `level: "P0"`, `must: true`, and use automated assertions against the contract JSON.

The gate must pin the following exact successor contract object at:

```text
/tenancy/tenant_resolution/system_internal_membership_probe
```

with these required values:

```text
enabled                                      = true
policy_id                                    = "org_membership_probe"
caller_boundary                              = "system_internal_only"
public_clients_allowed                       = false
requires_authenticated_human                = true
authoritative_user_id_required               = true
candidate_org_authoritative_before_proof     = false
preproof_candidate_scope_allowed             = true
transaction_local_required                   = true
same_backend_transaction_required            = true
constrained_runtime_role_required             = true
force_rls_required                            = true
superuser_forbidden                           = true
bypassrls_forbidden                           = true
table_owner_execution_forbidden               = true
allowed_resource                              = "IAM-1.OrgMembership"
allowed_operation                             = "read_membership_proof"
read_only                                     = true
active_membership_required                    = true
role_lookup_before_proof_allowed              = false
other_tenant_resource_access_before_proof_allowed = false
writes_allowed                                = false
event_capability_authorization_allowed        = false
persona_promotion_on_failure_allowed          = false
session_promotion_on_failure_allowed          = false
persist_candidate_org_on_failure_allowed      = false
hide_existence_on_failure_required            = true
org_membership_id_is_proof_output             = true
role_resolution_after_success_allowed         = true
```

The gate must also continue to assert, either directly in 145 or by retaining 140 plus a focused 145 assertion:

```text
/tenancy/tenant_resolution/membership_validation/enforced_before_setting_tenant = true
```

and prove `IAM-1.OrgMembership` is not added to `/tenancy/global_resources/allowed_resources`. If the generic gate schema lacks a negative-array-membership assertion, use an existing supported assertion type or add a narrow authority test at Task 4; do not weaken this requirement into prose-only evidence.

- [ ] **Step 5: Build/validate the gate-first candidate and capture expected RED evidence**

Run the documented contract build/validation path against `TEN-1/2.0.1` before adding the contract probe object.

Expected: candidate validation/test-gate evaluation fails specifically because the new `TEN-1-GATE-145` JSON pointers/values are absent from `contract.json`.

If it passes despite the object being absent, STOP: the gate is not proving what it claims.

Commit only after capturing the RED evidence in the execution notes; do not treat this intermediate source as a release candidate.

---

### Task 3: Add the minimal TEN-1 probe semantics and turn the gate GREEN

**Files:**
- Modify: `authority/release-src/current/TEN-1/2.0.1/contract.json`
- Modify if required by supported assertion shape only: `authority/release-src/current/TEN-1/2.0.1/test-gates.json`

**Interfaces:**
- Consumes: `TEN-1-GATE-145` from Task 2.
- Produces: a contract candidate whose explicit machine-readable policy satisfies the approved repair without altering ordinary membership-before-tenant semantics.

- [ ] **Step 1: Add `system_internal_membership_probe` under `tenancy.tenant_resolution`**

Create exactly one new object:

```json
"system_internal_membership_probe": {
  "enabled": true,
  "policy_id": "org_membership_probe",
  "caller_boundary": "system_internal_only",
  "public_clients_allowed": false,
  "requires_authenticated_human": true,
  "authoritative_user_id_required": true,
  "candidate_org_authoritative_before_proof": false,
  "preproof_candidate_scope_allowed": true,
  "transaction_local_required": true,
  "same_backend_transaction_required": true,
  "constrained_runtime_role_required": true,
  "force_rls_required": true,
  "superuser_forbidden": true,
  "bypassrls_forbidden": true,
  "table_owner_execution_forbidden": true,
  "allowed_resource": "IAM-1.OrgMembership",
  "allowed_operation": "read_membership_proof",
  "read_only": true,
  "membership_match_fields": ["org_id", "user_id"],
  "active_membership_required": true,
  "role_lookup_before_proof_allowed": false,
  "other_tenant_resource_access_before_proof_allowed": false,
  "writes_allowed": false,
  "event_capability_authorization_allowed": false,
  "persona_promotion_on_failure_allowed": false,
  "session_promotion_on_failure_allowed": false,
  "persist_candidate_org_on_failure_allowed": false,
  "hide_existence_on_failure_required": true,
  "org_membership_id_is_proof_output": true,
  "role_resolution_after_success_allowed": true,
  "notes": [
    "Candidate org scope exists only to prove the already-authenticated human's active membership and is not the human's resolved tenant or active persona.",
    "Successful membership proof permits downstream IAM-1 organization-persona/session establishment; the probe itself grants no role or tenant capability.",
    "Failure discards candidate scope and MUST preserve TEN-1 hide-existence behavior."
  ]
}
```

Do not alter the existing `membership_validation` object except where successor-version metadata requires no semantic change. In particular, keep:

```text
enforced_before_setting_tenant = true
required = true
```

- [ ] **Step 2: Verify no global-resource or unrelated tenancy drift**

Diff the successor contract against 2.0.0 after normalizing only expected version/timestamp/change-log fields.

Expected semantic delta: the one probe object plus its 2.0.1 change-log record. No global allowlist addition, no RLS weakening, no source-precedence changes, no public-surface changes.

- [ ] **Step 3: Rebuild and validate the TEN-1 candidate**

From `authority/`, run the documented build:

```bash
python tools/build_contract_release.py \
  --source release-src/current/TEN-1/2.0.1/ \
  --output /tmp/tick35-ten-one \
  --allow-candidate
```

Then:

```bash
python tools/validate_contract_release.py \
  /tmp/tick35-ten-one/TEN-1_bundle_v2.0.1.zip

python tools/validate_release_set.py \
  --candidate /tmp/tick35-ten-one/TEN-1_bundle_v2.0.1.zip \
  --root .
```

Expected: PASS. `TEN-1-GATE-145` is present and machine-locks the policy; `TEN-1-GATE-140` remains unchanged/P0/must.

- [ ] **Step 4: Add a narrow repository authority test only if the gate schema cannot prove negative global membership**

If existing gate assertion types cannot prove that `IAM-1.OrgMembership` is absent from the global allowlist, add one focused test under `authority/tests/` using the repository's existing test style. It must load the built/candidate or installed contract through the established authority helper and assert membership is not in `tenancy.global_resources.allowed_resources`.

Do not add a test if the paired gate already proves the condition.

- [ ] **Step 5: Commit the completed TEN-1 successor source**

Suggested commit:

```text
authority(TICK-35): define membership bootstrap probe
```

---

### Task 4: Prove deterministic TEN-1 release output

**Files:**
- No canonical install yet.
- Temporary outputs only under `/tmp`.

**Interfaces:**
- Consumes: validated TEN-1 `2.0.1` source.
- Produces: two byte-identical TEN-1 candidate builds and recorded hashes for later CANON generation/install verification.

- [ ] **Step 1: Build twice into clean independent directories**

From `authority/`:

```bash
rm -rf /tmp/tick35-ten-build-one /tmp/tick35-ten-build-two
python tools/build_contract_release.py --source release-src/current/TEN-1/2.0.1/ --output /tmp/tick35-ten-build-one --allow-candidate
python tools/build_contract_release.py --source release-src/current/TEN-1/2.0.1/ --output /tmp/tick35-ten-build-two --allow-candidate
```

- [ ] **Step 2: Byte-compare all deterministic artifacts**

Compare at minimum:

```text
TEN-1_bundle_v2.0.1.zip
TEN-1_Contract_v2.0.1.json
TEN-1_Test_Gates_v2.0.1.json
bundle.manifest.json
```

Expected: byte-for-byte identical. Any difference is a STOP; do not pick one build arbitrarily.

- [ ] **Step 3: Validate the accepted TEN-1 candidate build again**

Run both `validate_contract_release.py` and `validate_release_set.py` against the chosen byte-identical build-one ZIP. Record SHA-256 and byte counts in execution evidence; do not hand-enter them into generated artifacts unless the release source schema explicitly requires provenance values.

---

### Task 5: Generate and deterministically validate CANON-1 `2.0.17`

**Files:**
- Create generated source: `authority/release-src/current/CANON-1/2.0.17/`
- Temporary deterministic outputs under `/tmp`.

**Interfaces:**
- Consumes: accepted TEN-1 `2.0.1` candidate ZIP and current installed CANON/manifest.
- Produces: CANON successor selecting TEN-1 `2.0.1`, with all other suite membership preserved by the generator.

- [ ] **Step 1: Generate CANON successor only through repository tooling**

From `authority/`, use one explicit UTC timestamp for generation provenance:

```bash
python tools/generate_canon.py successor \
  --root . \
  --candidate /tmp/tick35-ten-build-one/TEN-1_bundle_v2.0.1.zip \
  --version 2.0.17 \
  --output-dir release-src/current/CANON-1/2.0.17 \
  --generated-at-utc <UTC-TIMESTAMP>
```

Do not hand-edit CANON contract selection, resolved-selection hashes, or generation provenance.

- [ ] **Step 2: Inspect generated CANON selection before building**

Prove:

```text
TEN-1 pin changes 2.0.0 → 2.0.1
all unrelated CANON members retain their current versions
base CANON identity = installed 2.0.16
active manifest input is the verified pre-install manifest
candidate hash matches deterministic TEN-1 build
```

Unexpected member drift is a STOP.

- [ ] **Step 3: Build CANON twice**

```bash
rm -rf /tmp/tick35-canon-build-one /tmp/tick35-canon-build-two
python tools/build_contract_release.py --source release-src/current/CANON-1/2.0.17/ --output /tmp/tick35-canon-build-one --allow-candidate
python tools/build_contract_release.py --source release-src/current/CANON-1/2.0.17/ --output /tmp/tick35-canon-build-two --allow-candidate
```

- [ ] **Step 4: Byte-compare CANON deterministic artifacts**

Compare the CANON ZIP, contract, test gates and bundle manifest from both builds. Expected: byte-identical.

- [ ] **Step 5: Validate CANON candidate/release set**

Run the documented contract and release-set validators for CANON `2.0.17`, including the TEN-1 candidate where the tool requires explicit candidate closure inputs.

Expected: PASS with dependency closure intact.

Suggested commit after source generation is stable:

```text
authority(TICK-35): generate CANON 2.0.17 successor
```

---

### Task 6: Install the exact TEN-1 + CANON releases and regenerate canonical inventory

**Files:**
- Create/replace current installed TEN-1 release selection under `authority/contracts/TEN-1/` according to `contract_manifest.py` workflow
- Create/install `authority/contracts/CANON-1/CANON-1_bundle_v2.0.17.zip`
- Regenerate extracted copies under `authority/contracts/TEN-1/extracted/`
- Regenerate extracted copies under `authority/contracts/CANON-1/extracted/`
- Modify generated `authority/contracts/manifest.json`

**Interfaces:**
- Consumes: byte-identical validated TEN-1 and CANON build-one ZIPs.
- Produces: one coherent installed canonical snapshot selecting TEN-1 `2.0.1` through CANON-1 `2.0.17`.

- [ ] **Step 1: Re-read the current install commands from `authority/README.md` and tool help**

Use the repository's actual install/extract interface. Do not invent a copy layout or leave two releases simultaneously selected in `extracted/`.

- [ ] **Step 2: Install TEN-1 `2.0.1` and CANON-1 `2.0.17` together**

Use exactly the deterministic build-one ZIP bytes proven in Tasks 4–5.

Do not rebuild between validation and install unless the rebuilt bytes are re-compared to the accepted candidates.

- [ ] **Step 3: Regenerate extracted inspection copies**

Run:

```bash
python tools/contract_manifest.py extract TEN-1 --root .
python tools/contract_manifest.py extract CANON-1 --root .
```

or the exact current equivalent confirmed by tool help.

- [ ] **Step 4: Regenerate the manifest**

```bash
python tools/contract_manifest.py generate --root .
```

- [ ] **Step 5: Inspect the installed snapshot**

Prove from installed canonical files, not release-src:

```text
CANON-1 = 2.0.17
TEN-1   = 2.0.1
IAM-1   = 4.1.2 unchanged
IAM-2   = 1.5.0 unchanged
```

Verify installed TEN-1 contains `system_internal_membership_probe` and `TEN-1-GATE-145`; Gate 140 remains P0/must; OrgMembership is still absent from global resources.

Verify manifest ZIP/artifact hashes match the exact accepted candidate bytes.

- [ ] **Step 6: Commit installed artifacts/inventory**

Suggested commit:

```text
authority(TICK-35): install TEN-1 2.0.1 and CANON 2.0.17
```

---

### Task 7: Run full authority validation and exact-diff review

**Files:**
- Potential test file only if Task 3 required a negative-membership helper assertion.
- No downstream planning/application edits.

**Interfaces:**
- Consumes: installed successor snapshot.
- Produces: fresh local authority evidence that the repository is coherent before PR handoff.

- [ ] **Step 1: Install/use the authority validation environment without changing project dependencies**

From repository root, use the documented authority Python environment and pinned requirements. Do not commit local virtualenv/cache files.

- [ ] **Step 2: Run full authority tests**

```bash
PYTHONPATH=authority python3 -m pytest -q authority/tests
```

Expected: PASS.

- [ ] **Step 3: Verify manifest and CANON generation state**

```bash
python3 authority/tools/contract_manifest.py verify --root authority
python3 authority/tools/generate_canon.py verify --root authority
```

Expected: PASS.

- [ ] **Step 4: Run strict canonical reconciliation**

```bash
python3 authority/tools/reconcile_contracts.py audit --canonical --strict --root authority \
  --json-output /tmp/ticketing-authority-audit.json \
  --markdown-output /tmp/ticketing-authority-audit.md
```

Expected: PASS/no unresolved strict authority contradiction.

- [ ] **Step 5: Run application-side authority verification without changing application code**

From `ticketing/` run:

```bash
mix contract.authority
```

Expected: PASS.

- [ ] **Step 6: Review the exact branch diff against the execution baseline**

Allowed changes are limited to:

```text
planning/specs/SPEC-AUTH-TICK-35_v0.1.0.md
planning/plans/2026-10-22-tick-35-membership-bootstrap-authority-repair.md
authority/release-src/current/TEN-1/2.0.1/**
authority/release-src/current/CANON-1/2.0.17/**
authority/contracts/TEN-1/TEN-1_bundle_v2.0.1.zip
authority/contracts/TEN-1/extracted/**
authority/contracts/CANON-1/CANON-1_bundle_v2.0.17.zip
authority/contracts/CANON-1/extracted/**
authority/contracts/manifest.json
```

plus at most one focused `authority/tests/**` file if needed to prove negative global-resource membership.

There must be no `ticketing/`, JIP-T0-01, SPEC-T0-01, ROADMAP/tracer, dependency, Plane-export, or unrelated contract edits.

- [ ] **Step 7: Verify no stale/generated junk or secret material**

Run `git diff --check`, inspect untracked files, and confirm no temp outputs, local paths, credentials or virtualenv artifacts enter the commit.

---

### Task 8: Open the authority PR and stop for independent review

**Files:**
- No new product files unless required to correct review findings.

**Interfaces:**
- Consumes: validated clean authority branch.
- Produces: one open authority PR with exact-head CI, ready for independent control-tower review but not merged.

- [ ] **Step 1: Push the authority branch**

Branch:

```text
authority/tick-35-membership-bootstrap
```

- [ ] **Step 2: Open one PR against current `main`**

Suggested title:

```text
[TICK-35] Define membership-before-tenant bootstrap authority
```

PR body must state:

- exact base/head SHAs;
- TEN-1 2.0.0 → 2.0.1;
- CANON-1 2.0.16 → 2.0.17;
- canonical problem being repaired;
- system-internal probe restrictions;
- Gate 140 preserved;
- new Gate 145 evidence;
- OrgMembership remains tenant-scoped/non-global;
- deterministic double-build hashes/results;
- release-set/full authority validation results;
- exact changed-file list;
- no application/downstream JIP changes;
- TICK-25/TICK-26 remain blocked/non-READY.

- [ ] **Step 3: Obtain fresh exact-head CI**

Require every authority-triggered required workflow/check to complete successfully on the exact PR head. Inspect failed logs rather than rerunning blindly.

- [ ] **Step 4: Update TICK-35 with PR/evidence**

Record exact PR URL/head, successor hashes, deterministic-build result, authority validation result, and CI run IDs. Keep TICK-35 In Progress pending independent review/merge.

- [ ] **Step 5: Return handoff and stop**

Return exactly:

```text
READY FOR AUTHORITY REVIEW
```

Include:

- verified base SHA/tree;
- branch/head;
- PR URL;
- exact changed files;
- exact TEN-1/CANON candidate and installed hashes;
- RED Gate-145 evidence;
- GREEN Gate-145 evidence;
- proof Gate 140 remains unchanged;
- proof OrgMembership remains non-global;
- deterministic double-build comparisons;
- validation command results;
- exact-head CI conclusions;
- explicit statement that no application code/JIP/ROADMAP/tracer/dependency changes occurred;
- confirmation TICK-25 and TICK-26 remain non-READY;
- any blocker/discovery.

Do not merge the PR. Do not mark TICK-35 Done. Do not begin the downstream targeted re-Grill until the authority PR is independently approved, merged, and post-merge verified.

---

## Control-tower continuation after authority merge

This section is not executed by the authority authoring agent before PR merge.

After the user merges the independently approved authority PR, the control tower must:

1. verify actual merge SHA/tree/signature and exact post-merge authority/main CI;
2. verify installed CANON-1 `2.0.17` / TEN-1 `2.0.1` from current `main`;
3. record merged evidence on TICK-35;
4. treat JIP-T0-01 `0.1.2` as STALE for implementation because its Session non-goal and resolver ordering no longer align with the governing authority set;
5. run targeted `grill-with-docs`/JIT re-Grill against the new TEN-1 plus IAM-1 4.1.2 and the merged TICK-23/TICK-24 substrate;
6. prepare JIP-T0-01 `0.1.3` and a reconciled downstream spec/Plane graph;
7. obtain explicit user approval of JIP v0.1.3;
8. only then rerun the TICK-25 freshness/dependency gate and decide READY status.

TICK-35 closes only after its authority repair merge evidence and required downstream handoff are recorded; the authority merge itself does not make TICK-25 implementation-ready.
