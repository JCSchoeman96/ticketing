# JIP-T0-SEC-02 — Restore secure Tidewave development-tooling baseline

**Version:** 0.1.0  
**Status:** APPROVED  
**Approval:** prior explicit user acceptance, carried forward and freshness-reverified 2026-10-29  
**Plane implementation item:** TICK-58  
**Blocks:** JIP-T0-SEC-01 closeout / PR #48 and TICK-26  
**Nature:** Development-tooling/security prerequisite; no product/domain semantics

## 1. Objective

Restore Ticketing's DEV-only Tidewave dependency to a release unaffected by `EEF-CVE-2026-109823` / `CVE-2026-109823`, while preserving the existing development-only boundary and preventing unrelated dependency, runtime, product, or domain drift.

The approved manifest requirement is:

```elixir
{:tidewave, ">= 0.9.2 and < 1.0.0", only: :dev}
```

The fixed security floor is Tidewave `0.9.2`.

This JIP does not authorize implementation until this approved planning artifact is persisted through the repository planning workflow, independently reviewed, explicitly merge-authorized by the user, merged to `main`, and post-merge freshness is reverified.

## 2. Fresh authority and repository baseline

Freshness was reverified immediately before persistence.

### Repository baseline

- GitHub `main`: `77ebe45e3d99789b279f7fb5f3b3b106fb660475`
- Baseline commit: `Merge PR #47: restore secure Bandit runtime baseline`
- Installed CANON: `CANON-1 2.0.18`
- CANON artifact blob SHA: `e6212a45f6c5499b081a9fe77101647cb098302c`
- Installed contract manifest blob SHA: `bd4e8c750ea8fd17e94a9e89557d6e2da5e35b47`
- ROADMAP: `B0 COMPLETE / T0 NEXT`
- Active tracer: `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`
- Root and applicable scoped `AGENTS.md` files re-read and unchanged for this planning scope.
- `planning/WORKFLOW.md` re-read and unchanged for this planning scope.

No canonical product-authority change is required by this prerequisite. The Tidewave change is below the product-semantic authority layer and must not alter any contract-defined behavior.

### Current technical baseline

- Elixir `1.20.4`
- Erlang/OTP `29.1.2`
- Phoenix `1.8.16`
- Phoenix LiveView `1.2.13`
- Ash `3.37.2`
- AshPhoenix `2.3.25`
- AshPostgres `2.15.2`
- Bandit `1.14.0`
- Tidewave `0.9.1` — security-blocked DEV-only baseline

Current manifest declaration:

```elixir
{:tidewave, "~> 0.9.1", only: :dev}
```

Current lock resolution is exactly Tidewave `0.9.1`.

The broader stack is not part of this prerequisite and MUST NOT be upgraded opportunistically.

## 3. Security evidence

The Erlang Ecosystem Foundation CNA published `CVE-2026-109823` on 2026-10-27.

Security boundary:

- EEF advisory ID: `EEF-CVE-2026-109823`
- CVE: `CVE-2026-109823`
- severity: LOW, CVSS 4.0 score `2.3`
- title: host filesystem path disclosure via DNS rebinding
- affected Tidewave range: `>= 0.8.0 and < 0.9.2`
- fixed version floor: `0.9.2`

The vulnerable behavior allows a malicious web page, through DNS rebinding against a developer's loopback-bound Tidewave-enabled application, to obtain local filesystem-path information exposed in Tidewave configuration metadata because affected responses do not adequately validate the `Host` boundary.

Primary advisory:

`https://cna.erlef.org/cves/CVE-2026-109823.html`

Machine-readable corroboration:

`https://osv.dev/vulnerability/EEF-CVE-2026-109823`

Upstream Tidewave Phoenix tag `v0.9.2` exists at commit:

`bf1f223f4897ada38ecc7e72c3f61bdcced4e46a`

The EEF/OSV record identifies the corresponding Git fixed boundary and the Hex fixed event as `0.9.2`.

### Package-resolution guard

Implementation MUST independently prove that a compliant Tidewave release satisfying `>= 0.9.2 and < 1.0.0` is resolvable from Ticketing's configured Hex source at implementation time.

If a compliant release cannot actually be resolved:

- do not suppress or bypass `mix hex.audit`;
- do not silently switch Tidewave to an ad-hoc Git dependency;
- do not broaden the resolver or upgrade unrelated packages;
- stop and return the prerequisite for targeted review.

This guard does not change the accepted security floor or manifest range.

## 4. Technology decision

### Decision: ADOPT Tidewave >= 0.9.2 and < 1.0.0

**Classification:** `IMPLEMENTATION_LOCKED` security prerequisite.

Ticketing MUST NOT resolve Tidewave below `0.9.2`.

Approved declaration:

```elixir
{:tidewave, ">= 0.9.2 and < 1.0.0", only: :dev}
```

The `only: :dev` boundary is locked. Tidewave MUST NOT become a TEST or production dependency as part of this work.

Rationale:

- records the known patched minimum explicitly;
- records the next incompatible major boundary explicitly;
- prevents future lock regeneration from silently selecting the advisory-affected 0.9.1 baseline;
- preserves the existing development-tooling role of Tidewave;
- restores compatibility with the repository's mandatory `mix hex.audit` security gate.

### Rejected alternatives

**Keep `~> 0.9.1` and update only `mix.lock`: REJECT.**

That would fail to encode the known security floor in the manifest and could permit future vulnerable resolution.

**Suppress or waive the Hex advisory: REJECT.**

The repository explicitly treats known applicable advisories as a blocking security condition.

**Move Tidewave out of DEV-only scope: REJECT.**

This JIP does not authorize broader runtime exposure.

**Bundle the Tidewave change into JIP-T0-SEC-01 closeout or TICK-26: REJECT.**

The newly discovered dependency vulnerability is a separate prerequisite with its own scope, evidence, resolver review, merge gate, and closeout.

## 5. Ash capability evaluation

No new Ash capability is relevant to this prerequisite.

- Ash core: unchanged
- AshPhoenix: unchanged
- AshPostgres: unchanged
- AshStateMachine: `NOT_APPLICABLE`
- AshOban: `NOT_APPLICABLE`
- Reactor adoption: `NOT_APPLICABLE`
- AshAuthentication: `NOT_APPLICABLE`
- other Ash extensions/capabilities: `NOT_APPLICABLE`

No Ash feature adoption, DSL change, transaction change, policy change, migration change, or dependency upgrade may be hidden in this work.

## 6. Reference evaluation

Required reference repositories were refreshed even though this slice is development-tool security rather than commerce/UI architecture.

### Store_Blueprint_Hardening

Fresh main commit:

`db14e3cadf7d60b1c5ca1add696e289cb7b5c7dc`

**Classification:** `NOT_APPLICABLE`

No Store commerce/provider/outbox/idempotency pattern materially constrains this DEV-only Tidewave security patch. The repository remains reference evidence only and is not Ticketing authority.

### LiveFrames

Fresh main commit:

`f43a3f44eb1b14b2b8c0300a4a5be6ebee5b63d2`

**Classification:** `NOT_APPLICABLE`

No LiveFrames UI pattern materially constrains this DEV-only dependency security patch. The repository remains reference evidence only and is not Ticketing authority.

Reference movement is nonmaterial to this JIP and does not stale the accepted packet.

## 7. Scope

Implementation scope is deliberately narrow:

- change Ticketing's direct Tidewave requirement to the approved security range;
- preserve `only: :dev` exactly;
- resolve Tidewave to `0.9.2` or a freshly reviewed later compatible secure 0.9.x release satisfying the approved range;
- inspect the complete `mix.lock` resolver diff;
- accept only Tidewave-related movement that is demonstrably required;
- prove Tidewave remains usable for the intended local development workflow;
- prove the vulnerable Host/origin security boundary is no longer present through the patched upstream behavior and appropriate application-level smoke evidence;
- run the complete applicable repository security/application gates;
- update the affected derived implementation documentation only after the implementation is merged.

Expected normal implementation diff:

- `ticketing/mix.exs`
- `ticketing/mix.lock`
- the smallest Tidewave-specific test/smoke evidence only if executable application-level evidence is required

Any additional dependency or application-source change requires explicit explanation. Material unrelated drift stops implementation.

## 8. Explicit non-goals

This JIP does NOT authorize:

- product/domain implementation;
- Event or Identity changes;
- TICK-26 implementation or PR #45 changes;
- tenancy, authorization, actor, Session, membership, role or RLS changes;
- database schema, migration, grant, role or generated-resource changes;
- Phoenix, LiveView, Bandit, Ash, AshPhoenix, AshPostgres, Elixir, Erlang/OTP or PostgreSQL upgrades;
- frontend/tooling upgrades unrelated to Tidewave;
- Tidewave production exposure;
- endpoint architecture redesign;
- new product HTTP routes or API behavior;
- new canonical errors, events, outbox records, jobs or telemetry schemas;
- refactoring encountered while updating the dependency;
- reproducing the upstream exploit suite inside Ticketing unless a Ticketing-specific regression requires it;
- merging or modifying PR #48 as part of the Tidewave implementation PR.

## 9. Domain ownership, resources, actions and lifecycles

### Domain ownership/resources/actions

`UNAFFECTED`.

No Ticketing domain, resource or Ash action is introduced or modified.

### Domain lifecycles

`UNAFFECTED`.

No domain lifecycle state, transition, initiator, guard, side effect or terminal state is introduced or changed.

The only relevant execution progression is repository/process state:

`approved planning packet → merged planning artifact → READY prerequisite → dependency update → reviewed implementation PR → merged secure baseline → closeout`

That process progression does not create product semantics.

## 10. Tenancy, actor, authorization and RLS

`UNAFFECTED`.

Existing tenant resolution, actors, Ash policies, PostgreSQL RLS, support-mode rules, membership proof ordering and information-hiding behavior remain unchanged.

A Tidewave dependency patch MUST NOT be used as a reason to alter these boundaries.

## 11. Persistence, transactions and concurrency

### Persistence / indexes / foreign keys / DB-owned time

`UNAFFECTED`.

No migration, resource snapshot or schema change is expected.

Any Ash code-generation drift is unexpected and must be investigated rather than committed blindly.

### Transactions / concurrency / CAS / locks

`UNAFFECTED`.

### Idempotency / replay

`UNAFFECTED`.

### Money / inventory / ticketing state

`UNAFFECTED`.

## 12. Errors, side effects, events and observability

### Canonical errors

`UNAFFECTED`.

### Events / outbox / jobs / audit

`UNAFFECTED`.

### Observability

No new product observability contract is introduced.

The implementation and review evidence should identify the resolved Tidewave version and security-audit outcome without logging or exposing local secrets, credentials or unnecessary developer filesystem paths.

## 13. Resolver invariant

The dependency resolution MUST be reviewed as data rather than assumed safe because a dependency command succeeds.

Expected result:

- Tidewave changes from `0.9.1` to `0.9.2` or an explicitly reviewed later secure compatible 0.9.x release.

If any other package changes:

1. determine exactly why the resolver changed it;
2. prove the movement is required by the Tidewave update;
3. verify security and compatibility;
4. stop for targeted review if the movement is material, unrelated or avoidable.

Unrelated opportunistic dependency refreshes are prohibited.

The implementation MUST preserve `only: :dev` in `mix.exs`.

## 14. Migration, rollout and rollback

No database migration exists.

Rollout is a development-tool dependency update.

Before accepting the implementation:

- a secure Tidewave release resolves from the configured package source;
- the application still boots in DEV;
- the intended local Tidewave MCP/development path remains functional;
- the security audit no longer reports `CVE-2026-109823` for the resolved Tidewave package;
- the patched Host/origin behavior is covered by upstream evidence and the smallest useful Ticketing smoke/regression evidence;
- production dependency posture remains unchanged.

Tidewave `0.9.1` and any other release below the approved security floor are NOT valid rollback targets.

If the secure 0.9.x release exposes a Ticketing incompatibility:

- stop rollout;
- diagnose the incompatibility;
- prefer another secure compatible release satisfying the approved range where justified;
- do not downgrade to an advisory-affected release;
- re-Grill/reapprove if resolution materially expands scope or changes a locked decision.

## 15. Required verification

The implementation must provide evidence for all applicable checks:

1. exact `ticketing/mix.exs` diff;
2. exact `ticketing/mix.lock` resolver diff;
3. Tidewave resolves at or above `0.9.2` and below `1.0.0`;
4. Tidewave remains `only: :dev`;
5. no unexplained unrelated dependency movement;
6. `mix hex.audit` reports no applicable Tidewave advisory;
7. DEV application boots with the secure Tidewave resolution;
8. intended local Tidewave MCP/development functionality remains available;
9. smallest useful Host/origin security regression/smoke evidence passes where application-level evidence is practical;
10. `mix ash.codegen --check`;
11. `mix contract.authority`;
12. full ExUnit suite;
13. Credo strict;
14. Sobelow configured blocking threshold;
15. DEV asset build where required by `mix check`;
16. `mix check`;
17. `mix check.types`;
18. `mix precommit`;
19. `git diff --check`;
20. exact-head CI, including PostgreSQL 18 partition verification and Dialyzer;
21. independent exact-diff review;
22. explicit user merge authorization;
23. merged-`main` verification.

Upstream owns protocol/security exploit-level regression coverage. Ticketing must prove safe package resolution, preserved DEV-only scope, application compatibility, and a clean repository security gate.

## 16. Documentation impact

Derived implementation documentation is updated only after the secure Tidewave implementation is merged and verified.

### UPDATE

`ticketing/docs/platform/runtime.md`

Replace the current DEV-tooling Tidewave `0.9.1` baseline with the merged secure resolution, retain its DEV-only role, and record the governing JIP/TICK and verified merged SHA.

### UPDATE

`ticketing/docs/platform/testing-and-quality-gates.md`

Record the restored clean `mix hex.audit` baseline for Tidewave and the relevant merged verification evidence.

### CREATE

`ticketing/docs/handoffs/JIP-T0-SEC-02.md`

Freeze the prerequisite closeout, exact merged SHA, exact dependency/resolver diff, advisory evidence, verification evidence, and downstream handoff back to JIP-T0-SEC-01 closeout / TICK-26 readiness progression.

### UNAFFECTED

- `ticketing/docs/platform/database.md`
- tenancy/authorization documentation
- domain documentation
- flow documentation
- canonical product contracts

## 17. Risks and stop conditions

### Resolver expansion

Risk: updating Tidewave could move unrelated dependencies.

Mitigation: exact full lock-diff review; unrelated/material movement is a blocker.

### False security closure

Risk: a lock-only update could leave the manifest capable of accepting a vulnerable release later.

Mitigation: encode the `0.9.2` security floor directly in `mix.exs`.

### Boundary expansion

Risk: Tidewave could accidentally become available outside DEV.

Mitigation: preserve and verify `only: :dev`; production exposure is explicitly prohibited.

### Package publication/index timing

Risk: the advisory/upstream fixed boundary may be visible before a configured package source can actually resolve the secure release.

Mitigation: prove package-source resolution before accepting implementation; never substitute a Git dependency or suppress the audit without targeted review.

### Unsafe rollback

Risk: operational convenience could tempt downgrade to `0.9.1`.

Mitigation: advisory-affected versions are explicitly invalid rollback targets.

### Scope contamination

Risk: the security prerequisite could become a vehicle for TICK-26, PR #48 or unrelated tooling changes.

Mitigation: keep SEC-02 as a narrow dependency/security PR and stop on material expansion.

## 18. Decision classification

### `CONTRACT_LOCKED`

Existing Ticketing product/domain semantics, tenancy, authorization, persistence, lifecycle, error, event, money, inventory and observable application contracts remain unchanged.

### `IMPLEMENTATION_LOCKED`

- Tidewave minimum accepted version is `0.9.2`.
- Approved range is `>= 0.9.2 and < 1.0.0`.
- Tidewave remains `only: :dev`.
- Advisory-affected versions are not rollback targets.
- `mix hex.audit` may not be suppressed or waived.
- No unrelated dependency churn.
- No silent switch to a Git dependency if Hex resolution is unavailable.
- SEC-02 remains separate from SEC-01 closeout and TICK-26.
- Complete applicable security/application verification is mandatory before merge.

### `IMPLEMENTATION_FREE`

- exact dependency-update command;
- exact minimal smoke/regression test mechanics;
- helper/test layout that cannot change external semantics;
- a later secure Tidewave 0.9.x resolution above `0.9.2` if freshly verified and still within the approved range.

### `AUTHORITY_GAP`

None identified.

If implementation discovers a need to change product semantics, production exposure, package source strategy, dependency architecture, a material locked decision, or another authority-controlled boundary, stop and return to targeted JIT review rather than inventing a solution.

## 19. Plane and downstream dependency posture

TICK-58 is the implementation child for this JIP.

Current native relations already make TICK-58 a blocker of:

- TICK-57 / JIP-T0-SEC-01 closeout;
- TICK-26 atomic organizer draft Event creation.

TICK-58 MUST remain non-READY until:

1. this approved JIP is persisted on `main` through a planning-only PR;
2. the planning PR receives independent exact-head control-tower review;
3. the user explicitly authorizes that planning PR merge;
4. the planning PR is merged;
5. merged `main` is reverified for authority/tracer/baseline freshness;
6. Plane dependencies remain correct and no new blocker or authority gap exists.

After the secure Tidewave implementation itself is independently reviewed, user-authorized, merged and reverified:

1. finish JIP-T0-SEC-02 derived docs/handoff;
2. return to the JIP-T0-SEC-01 closeout / PR #48 gate with fresh CI;
3. only after the security/closeout chain is complete, refresh TICK-26 against the accepted secure `main` baseline;
4. require fresh exact-head CI and independent review for any resumed TICK-26 PR.

No stale pre-security-upgrade CI result may be inherited as merge evidence.

## 20. Definition of Done

This JIP is complete only when:

- the approved Tidewave security floor is encoded in `ticketing/mix.exs`;
- the exact lock resolves a secure compatible Tidewave release;
- Tidewave remains DEV-only;
- `mix hex.audit` is clean for the Tidewave advisory;
- intended DEV Tidewave functionality is verified;
- no unexplained unrelated dependency drift exists;
- all applicable repository gates pass;
- exact-head CI is green, including PostgreSQL 18 partition verification and Dialyzer;
- the exact implementation diff receives independent review;
- explicit user merge authorization is obtained;
- merged `main` is reverified;
- required implementation docs and `JIP-T0-SEC-02` handoff are updated against the merged SHA;
- TICK-58 is closed only after all required evidence is recorded;
- JIP-T0-SEC-01 closeout / PR #48 is re-run from the restored secure baseline;
- TICK-26 remains blocked until the security prerequisite chain is genuinely complete.
