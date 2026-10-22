# TICK-35 Membership Bootstrap Authority Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- **Plan ID:** PLAN-AUTH-TICK-35
- **Version:** 0.1.0
- **Status:** APPROVED
- **Approved:** user instruction on 2026-10-22 — `Approve PLAN-AUTH-TICK-35 v0.1.0`
- **Baseline:** `71fe96e24f87f89418719e0f56252a633a8550e8`
- **Baseline tree:** `95e966a168205db06f9c6f7135be14e29366289a`

**Goal:** Resolve TICK-35 by releasing TEN-1 `2.0.1` with a narrowly bounded system-internal membership-probe policy, selecting it through CANON-1 `2.0.17`, installing the exact deterministic artifacts, and opening a validated authority PR without resuming TICK-25.

**Architecture:** Preserve TEN-1's ordinary membership-before-human-tenant invariant and add the one explicit exception already anticipated by TEN-1: a system-internal, transaction-local, FORCE-RLS-constrained probe that may read only `IAM-1.OrgMembership` for the authenticated user in one candidate organization. Lock the semantics in both the paired P0 gate and a focused canonical authority test, generate CANON only through repository tooling, and treat built ZIPs/hashes/extracted artifacts as immutable release evidence. No application implementation or downstream JIP correction occurs in this plan.

**Tech Stack:** Repository authority JSON contracts/test gates, Python release tooling under `authority/tools/`, deterministic ZIP generation, pytest authority verification, Git/GitHub CI.

**Spec:** `planning/specs/SPEC-AUTH-TICK-35_v0.1.0.md`

## Global Constraints

- Begin from freshly verified `main`; expected baseline is `71fe96e24f87f89418719e0f56252a633a8550e8`, tree `95e966a168205db06f9c6f7135be14e29366289a`.
- Installed authority at approval: CANON-1 `2.0.16`, TEN-1 `2.0.0`, IAM-1 `4.1.2`, IAM-2 `1.5.0`.
- Accepted release bytes are immutable. Never edit installed TEN-1 `2.0.0` or CANON-1 `2.0.16` artifacts in place.
- Intended successors: TEN-1 `2.0.1`, CANON-1 `2.0.17`. STOP if either identity is no longer free or governing authority moved materially.
- `TEN-1-GATE-140` remains P0/must and ordinary `/tenancy/tenant_resolution/membership_validation/enforced_before_setting_tenant` remains `true`.
- `IAM-1.OrgMembership` remains tenant-scoped and MUST NOT enter TEN-1's global-resource allowlist.
- Probe boundary: system-internal only; already-authenticated human `user_id`; one candidate `org_id`; read-only membership proof; no role read or other tenant business access before proof.
- Candidate DB scope: transaction-local, same backend transaction, constrained runtime role, FORCE RLS, non-superuser, non-BYPASSRLS, non-owner.
- Failure: no candidate-org persistence, persona/session promotion, role lookup, writes, or existence leakage.
- No IAM-1/IAM-2/EVT/ERR/OBS successor is authorized here. Any real dependency contradiction is a STOP and requires widening TICK-35 explicitly.
- No `ticketing/` code, dependencies, migrations, JIP, downstream T0 spec, ROADMAP, tracer, or READY-state change belongs in this authority PR.
- TICK-25 and TICK-26 remain non-READY throughout this plan.
- Follow root `AGENTS.md`, `authority/AGENTS.md`, and `authority/README.md` exactly. Never patch generated hashes merely to satisfy validation.

## Review Focus

1. **Candidate-org confusion:** candidate DB scope never means the human has an authorized/resolved tenant before proof.
2. **Probe widening:** machine evidence must constrain the pre-proof path to `IAM-1.OrgMembership` and read-only proof only.
3. **RLS bypass:** no semantics permit superuser, BYPASSRLS, table-owner, session-scoped GUC, or cross-connection tenant context.
4. **Existence leakage:** failed proof remains externally hidden and cannot create role/persona/session state.
5. **Planning half-fix:** authority merge alone never makes TICK-25 READY; IAM-1 Session/active-persona scope still requires the targeted re-Grill/JIP amendment.

---

### Task 1: Verify the authority execution gate and isolate the worktree

**Files:**
- Read: `AGENTS.md`
- Read: `authority/AGENTS.md`
- Read: `authority/README.md`
- Read: `planning/specs/SPEC-AUTH-TICK-35_v0.1.0.md`
- Read: `authority/contracts/manifest.json`
- Read: current CANON/TEN-1/IAM-1 installed extracted artifacts
- Read: `authority/release-src/current/TEN-1/2.0.0/{contract.json,test-gates.json,release.json,provenance.json}`

**Interfaces:**
- Consumes: approved SPEC-AUTH-TICK-35 v0.1.0.
- Produces: verified baseline and isolated authority branch/worktree.

- [ ] **Step 1: Load process skills before repo work**

Use `superpowers:using-git-worktrees` before creating/reusing an isolated worktree. Follow authority instructions, not the application implementation skill, for semantic/release behavior.

- [ ] **Step 2: Fetch and verify `origin/main`**

Expected:

```text
SHA  71fe96e24f87f89418719e0f56252a633a8550e8
tree 95e966a168205db06f9c6f7135be14e29366289a
```

If `main` moved, inspect the complete delta. STOP if it changes CANON, TEN-1, IAM-1, authority tooling, TICK-35 design, ROADMAP/tracer semantics, or TICK-35 prerequisites.

- [ ] **Step 3: Verify installed authority from CANON + manifest**

Prove current selection is:

```text
CANON-1 2.0.16
TEN-1   2.0.0
IAM-1   4.1.2
IAM-2   1.5.0
```

Confirm successor source identities `TEN-1/2.0.1` and `CANON-1/2.0.17` are unused.

- [ ] **Step 4: Verify Plane blocker state**

TICK-35 remains In Progress and blocks TICK-25. TICK-25 and TICK-26 must both be non-READY. Record no implementation-state promotion.

- [ ] **Step 5: Reuse/create the isolated branch**

Use:

```text
authority/tick-35-membership-bootstrap
```

The branch may contain only the approved TICK-35 spec and this plan before authority authoring begins. Unexpected files are a STOP.

---

### Task 2: Write the focused canonical RED test

**Files:**
- Create: `authority/tests/test_ten_membership_probe_policy.py`

**Interfaces:**
- Consumes: manifest-selected installed canonical artifacts.
- Produces: permanent test evidence that fails on TEN-1 `2.0.0` and passes only after the installed canonical suite contains the approved probe and gate.

- [ ] **Step 1: Follow the existing canonical-test loading pattern**

Use the same manifest-selected ZIP approach as `authority/tests/test_iam_t0_authority_closure.py`: load `authority/contracts/manifest.json`, open the selected TEN-1 bundle, and assert CANON pins the same version/path. Do not test `release-src` as though it were canonical.

- [ ] **Step 2: Add `test_selected_ten1_defines_system_internal_membership_probe_policy`**

Assert the manifest-selected TEN-1 contract has:

```text
/tenancy/tenant_resolution/system_internal_membership_probe/enabled = true
policy_id = "org_membership_probe"
caller_boundary = "system_internal_only"
public_clients_allowed = false
requires_authenticated_human = true
authoritative_user_id_required = true
candidate_org_authoritative_before_proof = false
preproof_candidate_scope_allowed = true
transaction_local_required = true
same_backend_transaction_required = true
constrained_runtime_role_required = true
force_rls_required = true
superuser_forbidden = true
bypassrls_forbidden = true
table_owner_execution_forbidden = true
allowed_resource = "IAM-1.OrgMembership"
allowed_operation = "read_membership_proof"
read_only = true
membership_match_fields = ["org_id", "user_id"]
active_membership_required = true
role_lookup_before_proof_allowed = false
other_tenant_resource_access_before_proof_allowed = false
writes_allowed = false
event_capability_authorization_allowed = false
persona_promotion_on_failure_allowed = false
session_promotion_on_failure_allowed = false
persist_candidate_org_on_failure_allowed = false
hide_existence_on_failure_required = true
org_membership_id_is_proof_output = true
role_resolution_after_success_allowed = true
```

- [ ] **Step 3: Add `test_selected_ten1_gate_145_locks_probe_and_preserves_gate_140`**

Assert selected paired gates contain exactly one `TEN-1-GATE-145`, with `level == "P0"` and `must is True`. Build a map of its automated `json_pointer_equals` assertions and prove every required scalar policy field above is locked to the same value.

Also assert selected `TEN-1-GATE-140` still exists exactly once, remains P0/must, and still locks:

```text
/tenancy/tenant_resolution/membership_validation/required = true
/tenancy/tenant_resolution/membership_validation/enforced_before_setting_tenant = true
```

- [ ] **Step 4: Add `test_org_membership_remains_tenant_scoped_not_global`**

Assert:

```text
"IAM-1.OrgMembership" not in contract["tenancy"]["global_resources"]["allowed_resources"]
```

This is the durable negative-membership proof; do not depend on a gate assertion type that the current generic release validator does not execute.

- [ ] **Step 5: Run the focused test and capture RED evidence**

From repo root:

```bash
PYTHONPATH=authority python3 -m pytest -q authority/tests/test_ten_membership_probe_policy.py
```

Expected on installed TEN-1 `2.0.0`: FAIL because the probe and Gate 145 do not yet exist.

If it passes before authority changes, STOP because the test is not proving the gap.

Commit the test only after observing the intended RED state.

Suggested commit:

```text
test(TICK-35): lock membership bootstrap authority
```

---

### Task 3: Author TEN-1 `2.0.1` successor source

**Files:**
- Create: `authority/release-src/current/TEN-1/2.0.1/contract.json`
- Create: `authority/release-src/current/TEN-1/2.0.1/test-gates.json`
- Create: `authority/release-src/current/TEN-1/2.0.1/release.json`
- Create: `authority/release-src/current/TEN-1/2.0.1/provenance.json`

**Interfaces:**
- Consumes: TEN-1 `2.0.0` editable source and the RED test.
- Produces: candidate source with only the approved TICK-35 semantic delta.

- [ ] **Step 1: Copy the immediate editable source baseline**

Copy the four files from:

```text
authority/release-src/current/TEN-1/2.0.0/
```

to:

```text
authority/release-src/current/TEN-1/2.0.1/
```

Never copy/edit installed ZIP or extracted canonical artifacts in place.

- [ ] **Step 2: Normalize successor identity metadata**

Set version/contract_ref/release identity to `2.0.1` wherever required by the current source schema. Use one explicit UTC generation timestamp consistently where the release tooling requires it.

Append one new change-log entry describing the TICK-35 membership-probe semantic addition. Do not rewrite historical entries.

- [ ] **Step 3: Rewrite provenance to the immediate installed 2.0.0 baseline**

`provenance.json` must identify the installed TEN-1 `2.0.0` ZIP as the immediate source baseline using the exact current manifest ZIP hash/byte count. Record the verified Git preparation base SHA and current source-member hashes/bytes for the new `contract.json` and `test-gates.json` as required by `build_contract_release.py`.

Do not retain the old 1.7.13/staging-bootstrap provenance statement as the provenance story for `2.0.1`.

Use a source-provenance kind accepted by current tooling that truthfully represents a semantic successor; do not claim `staging-bundle-bootstrap` unless the source actually meets that meaning.

- [ ] **Step 4: Add the exact canonical probe object**

Under:

```text
tenancy.tenant_resolution.system_internal_membership_probe
```

add exactly:

```json
{
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

Keep existing ordinary membership validation unchanged:

```text
required = true
enforced_before_setting_tenant = true
```

Do not change global resources, source precedence, public-surface semantics, Postgres RLS requirements, or hide-existence semantics.

- [ ] **Step 5: Add `TEN-1-GATE-145`**

Insert adjacent to the tenant-resolution gates. Requirements:

```text
id = "TEN-1-GATE-145"
level = "P0"
must = true
enforced_by = existing current strict gate identifier used by neighboring TEN-1 gates
```

Use automated `json_pointer_equals` assertions for each scalar field in the probe object and retain Gate 140 unchanged. It is acceptable for `membership_match_fields` and the negative global-resource assertion to be locked by the focused pytest test rather than inventing an unsupported gate assertion type.

- [ ] **Step 6: Inspect semantic diff against 2.0.0 source**

Expected semantic change only:

1. successor identity/timestamp/provenance metadata;
2. one new 2.0.1 change-log entry;
3. the `system_internal_membership_probe` object;
4. `TEN-1-GATE-145`.

Any unrelated tenancy semantic drift is a STOP.

- [ ] **Step 7: Build and schema-validate the candidate**

From `authority/`:

```bash
python tools/build_contract_release.py \
  --source release-src/current/TEN-1/2.0.1/ \
  --output /tmp/tick35-ten-candidate \
  --allow-candidate

python tools/validate_contract_release.py \
  /tmp/tick35-ten-candidate/TEN-1_bundle_v2.0.1.zip

python tools/validate_release_set.py \
  --candidate /tmp/tick35-ten-candidate/TEN-1_bundle_v2.0.1.zip \
  --root .
```

Expected: all candidate/schema/dependency validation passes. Note: these validators do not substitute for the focused semantic RED/GREEN authority test.

Suggested commit:

```text
authority(TICK-35): define membership bootstrap probe
```

---

### Task 4: Prove deterministic TEN-1 output and generate CANON-1 `2.0.17`

**Files:**
- Create generated source: `authority/release-src/current/CANON-1/2.0.17/`
- Temporary outputs: `/tmp/tick35-*`

**Interfaces:**
- Consumes: validated TEN-1 `2.0.1` source.
- Produces: byte-identical TEN-1 candidate builds and generated CANON successor selecting only the new TEN-1.

- [ ] **Step 1: Build TEN-1 twice from clean output directories**

```bash
rm -rf /tmp/tick35-ten-build-one /tmp/tick35-ten-build-two
python tools/build_contract_release.py --source release-src/current/TEN-1/2.0.1/ --output /tmp/tick35-ten-build-one --allow-candidate
python tools/build_contract_release.py --source release-src/current/TEN-1/2.0.1/ --output /tmp/tick35-ten-build-two --allow-candidate
```

- [ ] **Step 2: Byte-compare TEN-1 outputs**

Compare ZIP bytes and, by extracting or reading each archive, the contract, paired test gates and bundle manifest. Expected: byte-for-byte identical. Any difference is a STOP.

Record SHA-256 and byte counts for the accepted build-one ZIP/artifacts as evidence.

- [ ] **Step 3: Generate CANON successor through `generate_canon.py` only**

Use one explicit UTC timestamp:

```bash
python tools/generate_canon.py successor \
  --root . \
  --candidate /tmp/tick35-ten-build-one/TEN-1_bundle_v2.0.1.zip \
  --version 2.0.17 \
  --output-dir release-src/current/CANON-1/2.0.17 \
  --generated-at-utc <UTC-TIMESTAMP>
```

Do not hand-edit generated CANON selection/provenance/hash files.

- [ ] **Step 4: Inspect generated CANON selection**

Prove:

```text
base CANON = 2.0.16
TEN-1 pin  = 2.0.0 → 2.0.1
all unrelated CANON member versions unchanged
candidate hash = accepted TEN-1 build-one hash
```

Unexpected member drift is a STOP.

- [ ] **Step 5: Build CANON twice and byte-compare**

```bash
rm -rf /tmp/tick35-canon-build-one /tmp/tick35-canon-build-two
python tools/build_contract_release.py --source release-src/current/CANON-1/2.0.17/ --output /tmp/tick35-canon-build-one --allow-candidate
python tools/build_contract_release.py --source release-src/current/CANON-1/2.0.17/ --output /tmp/tick35-canon-build-two --allow-candidate
```

Compare ZIP, contract, paired gates and manifest bytes. Expected: byte-identical.

- [ ] **Step 6: Validate CANON candidate and release closure**

Run the repository-documented contract/release-set validation for CANON `2.0.17` and explicit candidate closure as required by tool help. Expected: PASS.

Suggested commit:

```text
authority(TICK-35): generate CANON 2.0.17 successor
```

---

### Task 5: Install the exact TEN-1 + CANON snapshot and turn focused tests GREEN

**Files:**
- Install: `authority/contracts/TEN-1/TEN-1_bundle_v2.0.1.zip`
- Regenerate: `authority/contracts/TEN-1/extracted/**`
- Install: `authority/contracts/CANON-1/CANON-1_bundle_v2.0.17.zip`
- Regenerate: `authority/contracts/CANON-1/extracted/**`
- Regenerate: `authority/contracts/manifest.json`
- Test: `authority/tests/test_ten_membership_probe_policy.py`

**Interfaces:**
- Consumes: exact byte-identical accepted build-one ZIPs.
- Produces: coherent installed canonical snapshot with focused semantic tests green.

- [ ] **Step 1: Re-read current install/extract tool help before writing canonical directories**

Follow `authority/README.md` and current CLI help exactly. Do not invent install layout or leave stale extracted members.

- [ ] **Step 2: Install the exact accepted TEN-1 and CANON ZIP bytes together**

Use the proven build-one bytes from Task 4. Do not rebuild between final hash evidence and installation unless rebuilt bytes are re-compared.

- [ ] **Step 3: Regenerate extracted inspection copies and manifest**

From `authority/`, run the documented equivalent of:

```bash
python tools/contract_manifest.py extract TEN-1 --root .
python tools/contract_manifest.py extract CANON-1 --root .
python tools/contract_manifest.py generate --root .
```

- [ ] **Step 4: Verify the installed snapshot from canonical files**

Prove:

```text
CANON-1 2.0.17
TEN-1   2.0.1
IAM-1   4.1.2 unchanged
IAM-2   1.5.0 unchanged
```

Verify manifest hashes match exact accepted candidate bytes.

- [ ] **Step 5: Run focused authority tests and capture GREEN evidence**

```bash
PYTHONPATH=authority python3 -m pytest -q authority/tests/test_ten_membership_probe_policy.py
```

Expected: PASS.

This GREEN result must prove:

- probe object exact values;
- Gate 145 exact machine locks;
- Gate 140 still P0/must and ordinary membership-before-setting remains true;
- `IAM-1.OrgMembership` remains absent from global resources.

Suggested commit:

```text
authority(TICK-35): install TEN-1 2.0.1 and CANON 2.0.17
```

---

### Task 6: Run full authority verification and exact-diff audit

**Files:**
- No new product files expected beyond approved authority artifacts/test.

**Interfaces:**
- Consumes: installed successor snapshot.
- Produces: fresh complete authority validation evidence.

- [ ] **Step 1: Run full authority pytest suite**

From repository root:

```bash
PYTHONPATH=authority python3 -m pytest -q authority/tests
```

Expected: PASS.

- [ ] **Step 2: Verify manifest and CANON generation**

```bash
python3 authority/tools/contract_manifest.py verify --root authority
python3 authority/tools/generate_canon.py verify --root authority
```

Expected: PASS.

- [ ] **Step 3: Run strict canonical reconciliation**

```bash
python3 authority/tools/reconcile_contracts.py audit --canonical --strict --root authority \
  --json-output /tmp/ticketing-authority-audit.json \
  --markdown-output /tmp/ticketing-authority-audit.md
```

Expected: PASS/no unresolved strict contradiction.

- [ ] **Step 4: Run application-side authority verifier**

From `ticketing/`:

```bash
mix contract.authority
```

Expected: PASS without changing application files/dependencies.

- [ ] **Step 5: Audit exact branch diff**

Allowed paths:

```text
planning/specs/SPEC-AUTH-TICK-35_v0.1.0.md
planning/plans/2026-10-22-tick-35-membership-bootstrap-authority-repair_v0.1.0.md
authority/tests/test_ten_membership_probe_policy.py
authority/release-src/current/TEN-1/2.0.1/**
authority/release-src/current/CANON-1/2.0.17/**
authority/contracts/TEN-1/TEN-1_bundle_v2.0.1.zip
authority/contracts/TEN-1/extracted/**
authority/contracts/CANON-1/CANON-1_bundle_v2.0.17.zip
authority/contracts/CANON-1/extracted/**
authority/contracts/manifest.json
```

No `ticketing/`, JIP-T0-01, SPEC-T0-01, ROADMAP/tracer, dependency, or unrelated contract edits are allowed.

- [ ] **Step 6: Hygiene checks**

Run `git diff --check`; inspect untracked files; ensure no temp build directories, local absolute paths, secrets, virtualenv/cache files, or generated audit files are committed.

---

### Task 7: Open the authority PR and stop for independent review

**Files:**
- No additional semantic files unless correcting a discovered blocker.

**Interfaces:**
- Consumes: clean fully validated authority branch.
- Produces: open authority PR with fresh exact-head CI; no merge.

- [ ] **Step 1: Push branch**

```text
authority/tick-35-membership-bootstrap
```

- [ ] **Step 2: Open one PR against current `main`**

Suggested title:

```text
[TICK-35] Define membership-before-tenant bootstrap authority
```

PR body must include:

- exact base/head SHA and base tree;
- TEN-1 `2.0.0 → 2.0.1`;
- CANON-1 `2.0.16 → 2.0.17`;
- exact authority gap and approved semantic repair;
- system-internal probe restrictions;
- Gate 140 preservation;
- Gate 145 evidence;
- OrgMembership non-global proof;
- focused RED then GREEN evidence;
- deterministic double-build hashes/results;
- release-set/full authority validation results;
- exact changed-file list;
- explicit no application/JIP/ROADMAP/tracer/dependency changes;
- TICK-25/TICK-26 remain blocked/non-READY.

- [ ] **Step 3: Require fresh exact-head CI**

All required authority-triggered workflows/checks must complete successfully on the exact PR head. Inspect any failing log; do not rerun blindly or weaken gates.

- [ ] **Step 4: Update TICK-35 ledger**

Record PR URL/head, deterministic ZIP hashes, focused RED/GREEN results, full authority validation, and CI run IDs. TICK-35 remains In Progress pending independent review/merge.

- [ ] **Step 5: Handoff and stop**

Return exactly:

```text
READY FOR AUTHORITY REVIEW
```

Include:

- verified base SHA/tree;
- branch/head;
- PR URL;
- exact changed files;
- TEN-1/CANON candidate and installed hashes;
- focused RED and GREEN evidence;
- Gate 140 unchanged proof;
- Gate 145 proof;
- OrgMembership non-global proof;
- deterministic double-build comparison results;
- all authority verification results;
- exact-head CI conclusions;
- any warning/discovery/blocker;
- confirmation no application code/downstream planning/dependency changes occurred;
- confirmation TICK-25/TICK-26 remain non-READY.

Do not merge. Do not mark TICK-35 Done. Do not start the downstream JIT re-Grill before independent authority review, merge, and post-merge verification.

---

## Control-tower continuation after authority merge

This is not executed by the authority authoring agent before merge.

After the user merges an independently approved authority PR, the control tower must:

1. verify actual merge SHA/tree/signature and post-merge authority/main CI;
2. verify installed CANON-1 `2.0.17` and TEN-1 `2.0.1` from current `main`;
3. record merged authority evidence on TICK-35;
4. treat JIP-T0-01 `0.1.2` as STALE for implementation;
5. run targeted JIT/`grill-with-docs` against new TEN-1, IAM-1 `4.1.2`, and merged TICK-23/TICK-24 substrate;
6. prepare JIP-T0-01 `0.1.3` plus reconciled downstream spec/Plane graph;
7. obtain explicit user approval of JIP `0.1.3`;
8. only then rerun TICK-25 dependency/freshness/READY gate.

TICK-35 closes only after merged authority evidence and the required downstream handoff are recorded. Authority merge alone does not make TICK-25 implementation-ready.
