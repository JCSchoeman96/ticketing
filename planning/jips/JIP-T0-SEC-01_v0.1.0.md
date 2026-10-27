# JIP-T0-SEC-01 — Restore secure Bandit runtime baseline

**Version:** 0.1.0  
**Status:** APPROVED  
**Approved:** 2026-10-27 by explicit user acceptance  
**Plane prerequisite:** TICK-56  
**Blocks:** TICK-26 / PR #45  
**Nature:** Runtime/security prerequisite; no product/domain semantics

## 1. Objective

Restore Ticketing's HTTP server dependency baseline to a release unaffected by the Bandit security advisories published on 26 October 2026, while preventing unrelated dependency drift or accidental product/domain change.

The implementation SHALL establish Bandit `1.14.0` as the minimum accepted runtime version and keep the dependency below the next incompatible major version.

Recommended direct dependency requirement:

```elixir
{:bandit, ">= 1.14.0 and < 2.0.0-0"}
```

The initial expected lock resolution is Bandit `1.14.0`.

## 2. Fresh baseline

### Canonical repository baseline

- GitHub `main`: `294e2050549d9765c8388380a82d26b5f467c847`
- CANON-1: `2.0.18`
- Installed contract manifest: unchanged from verified `main`
- ROADMAP: `B0 COMPLETE / T0 NEXT`
- Active tracer: T0 tenant-scoped GA pending-sale tracer
- TICK-56 is already a native `blocked_by` dependency of TICK-26.

No product-authority change is required by this prerequisite.

### Current technical baseline

- Elixir `1.20.4`
- Erlang/OTP `29.1.2`
- Phoenix `1.8.16`
- Phoenix LiveView `1.2.13`
- Ash `3.37.2`
- AshPhoenix `2.3.25`
- AshPostgres `2.15.2`
- Plug `1.20.3`
- Thousand Island `1.6.0`
- WebSock `0.5.3`
- websock_adapter `0.6.0`
- PostgreSQL `18.6`
- Bandit `1.13.1` — security-blocked baseline

The broader stack is already current and MUST NOT be upgraded as part of this JIP unless dependency resolution proves an unavoidable prerequisite, in which case implementation stops and the JIP is re-evaluated.

## 3. Security evidence

Bandit `1.13.1` falls inside multiple advisory-affected ranges published on 26 October 2026.

The advisories include remotely triggerable HTTP/1, HTTP/2 and WebSocket resource-exhaustion, parsing and protocol-handling vulnerabilities. Relevant affected ranges terminate before `1.14.0`.

Bandit tag `1.14.0` resolves to upstream commit:

`220b9dfd27f9a21305be2afc75cbe585ddc24e7a`

Bandit 1.14.0 contains the applicable fixes and introduces bounded/default handling for HTTP/2 stream counts, header-list sizes, receive windows, unread messages, SETTINGS frames, HPACK state, HTTP/1 parsing and WebSocket fragmentation/close behavior.

## 4. Technology decision

### Decision: ADOPT Bandit >= 1.14.0

**Classification:** `IMPLEMENTATION_LOCKED` security prerequisite.

Ticketing MUST NOT resolve Bandit below `1.14.0`.

### Manifest form

**Classification:** `IMPLEMENTATION_FREE`, locked by this JIP to the selected implementation:

```elixir
{:bandit, ">= 1.14.0 and < 2.0.0-0"}
```

Rationale:

- records the known patched minimum explicitly;
- records the next incompatible major boundary explicitly;
- satisfies repository version-range policy;
- prevents a future lock regeneration from silently reintroducing an advisory-affected Bandit 1.x release;
- remains compatible with Phoenix's Bandit 1.x requirement.

### Rejected alternatives

**Lock-only update while retaining `~> 1.5`: REJECT.**

It may produce a safe lock today, but the project manifest would fail to record the known security floor.

**Change the requirement to `~> 1.14`: ACCEPTABLE BUT NOT SELECTED.**

It provides substantially the same SemVer range, but the explicit lower/upper-bound form communicates the security-floor intent more clearly.

## 5. Ash capability evaluation

No new Ash capability is relevant to this prerequisite.

- Ash core: unchanged
- AshPhoenix: unchanged
- AshPostgres: unchanged
- AshStateMachine: NOT_APPLICABLE
- AshOban: NOT_APPLICABLE
- Reactor adoption: NOT_APPLICABLE
- AshAuthentication: NOT_APPLICABLE
- Signals/Temporal/PaperTrail/Archival/Storage/JSON: NOT_APPLICABLE

No Ash feature adoption or upgrade may be hidden in this change.

## 6. Reference evaluation

### Store_Blueprint_Hardening

Verified reference commit:

`327d8705f75f7a16677911bd6209531b910aef55`

**Classification:** `ADAPT`

Relevant pattern:

```elixir
{:bandit, ">= 1.14.0 and < 2.0.0-0"}
```

The reference resolves Bandit 1.14.0 and explicitly treats the requirement as a security floor.

This repository is reference evidence only and is not semantic authority.

### LiveFrames

Verified reference commit:

`04aff4dbc66cbbfd676a662b8b2d6645030ccd72`

Current preview application still declares Bandit `~> 1.12` and its lock resolves `1.12.5`.

**Classification:** `REFERENCE_ONLY`

It is useful as evidence of why permissive/stale runtime baselines must not be copied. It is not suitable as the Ticketing security baseline.

## 7. Scope

Implementation scope is deliberately narrow:

- change Ticketing's direct Bandit requirement to the approved security floor;
- resolve Bandit to `1.14.0` or another approved non-vulnerable 1.x version satisfying the floor;
- inspect the complete `mix.lock` resolver diff;
- accept only Bandit-related dependency movement that is demonstrably required;
- prove the HTTP endpoint still boots and serves a normal request;
- prove the LiveView/WebSocket path remains operational at an appropriate integration level;
- run the complete repository quality/security gates;
- update the affected derived implementation documentation after merge.

Expected normal source diff:

- `ticketing/mix.exs`
- `ticketing/mix.lock`
- the smallest test/smoke-test file only if new executable evidence is required
- post-merge derived documentation identified below

Any additional dependency or application-source change requires explicit explanation. Material unrelated drift stops implementation.

## 8. Explicit non-goals

This JIP does NOT authorize:

- Phoenix upgrade;
- LiveView upgrade;
- Elixir or Erlang/OTP upgrade;
- Ash/AshPhoenix/AshPostgres upgrade;
- PostgreSQL upgrade;
- frontend/tooling upgrade;
- endpoint redesign;
- new HTTP features;
- new Bandit tuning unrelated to the 1.14 secure defaults;
- changes to canonical API/domain behavior;
- Events/TICK-26 implementation changes;
- tenancy, authorization or RLS changes;
- database schema or migration changes;
- changes to canonical errors;
- new telemetry/event schemas;
- refactoring merely encountered during the upgrade.

## 9. Observable HTTP behavior

Bandit 1.14.0 changes network-facing behavior intentionally.

The upgrade adopts the upstream secure behavior for:

- HTTP/2 receive-window enforcement;
- bounded concurrent streams;
- bounded decoded header-list size;
- bounded HPACK encoder state;
- HTTP/2 frame/state error handling;
- HTTP/2 body-read deadlines;
- stricter HTTP/1 request-line parsing;
- stricter absolute-form target parsing;
- stricter HTTP/1 chunk-extension/trailer parsing;
- bounded parsing of oversized numeric values;
- bounded fragmented WebSocket memory use;
- correct server-initiated WebSocket close behavior.

Malformed, adversarial or previously over-permissive network input may therefore be rejected, reset, limited or closed differently after the upgrade.

This is an intended security correction, not a Ticketing product-semantic change.

Normal valid Ticketing HTTP and LiveView behavior MUST remain compatible.

## 10. Domain and persistence impact

### Domain ownership/resources/actions

UNAFFECTED.

### Lifecycles

No Ticketing domain lifecycle is introduced or modified.

### Tenancy / actor / authorization / RLS

UNAFFECTED.

Existing tenant resolution, Ash policies, actors, PostgreSQL RLS and support-mode rules remain unchanged.

### Persistence / indexes / foreign keys / DB-owned time

UNAFFECTED.

No migration or resource snapshot should be generated.

Any Ash code-generation drift is unexpected and must be investigated rather than committed blindly.

### Transactions / concurrency / CAS / locks

UNAFFECTED.

### Idempotency / replay

UNAFFECTED.

### Canonical errors

UNAFFECTED.

### Events / outbox / jobs / audit

UNAFFECTED.

### Money / inventory / ticketing state

UNAFFECTED.

## 11. Resolver invariant

The dependency resolution MUST be reviewed as data, not assumed safe because `mix deps.update bandit` succeeds.

Expected result:

- Bandit changes from `1.13.1` to `1.14.0` or an explicitly reviewed later compatible patched 1.x version.

If other packages change:

1. determine why the resolver changed them;
2. prove the movement is required by the Bandit upgrade;
3. verify security and compatibility;
4. stop for re-review if the movement is material or unrelated.

Unrelated opportunistic dependency refreshes are prohibited.

## 12. Migration and rollout

No database migration exists.

Rollout is an ordinary application dependency release.

Before production acceptance:

- application boots with the patched Bandit;
- ordinary HTTP traffic succeeds;
- LiveView/WebSocket connectivity succeeds;
- security and application gates pass.

No special data migration, dual-write, backfill or compatibility window is required.

## 13. Rollback

Bandit `1.13.1` and any other release below the approved security floor are NOT valid rollback targets.

If Bandit 1.14.0 exposes a Ticketing incompatibility:

- stop rollout;
- diagnose the incompatibility;
- prefer a newer patched Bandit 1.x satisfying the security floor;
- use operational traffic mitigation if required while a safe application fix is prepared;
- re-Grill/reapprove if the required solution materially expands scope.

Security regression is not an acceptable rollback strategy.

## 14. Required verification

The implementation must provide evidence for all applicable checks:

1. exact `mix.exs` diff;
2. exact `mix.lock` resolver diff;
3. Bandit resolves at or above 1.14.0 and below 2.0.0;
4. no unexplained unrelated dependency movement;
5. `mix hex.audit` reports no applicable Bandit advisory;
6. endpoint boots under the patched Bandit;
7. a real HTTP request through the network-facing endpoint succeeds;
8. LiveView/WebSocket compatibility is exercised by the smallest reliable existing or new integration smoke;
9. `mix ash.codegen --check`;
10. `mix contract.authority`;
11. full ExUnit suite;
12. Credo strict;
13. Sobelow configured blocking threshold;
14. asset build;
15. `mix check`;
16. `mix check.types`;
17. `mix precommit`;
18. exact-head CI, including PostgreSQL 18 partition verification;
19. independent exact-diff review;
20. merged `main` verification.

Reproduction of each upstream CVE exploit inside Ticketing is NOT required. Upstream fixes own the protocol-level exploit tests; Ticketing must prove safe resolution and application compatibility.

## 15. Documentation impact

### UPDATE

`ticketing/docs/platform/runtime.md`

Record the merged Bandit secure baseline, approved security floor, governing JIP/TICK and verified merged SHA.

### UPDATE

`ticketing/docs/platform/testing-and-quality-gates.md`

Record the restored clean `mix hex.audit` baseline and merged verification evidence.

### CREATE

`ticketing/docs/handoffs/JIP-T0-SEC-01.md`

Freeze the prerequisite closeout, exact merged SHA, dependency diff, security evidence, verification evidence and downstream handoff to TICK-26.

### UNAFFECTED

- domain documentation
- tenancy/authorization documentation
- database documentation
- flows
- product contracts

## 16. Risks

**Protocol strictness regression:** Valid application traffic could rely on behavior newly tightened by Bandit.

Mitigation: endpoint/LiveView smoke evidence and full application tests.

**Resolver expansion:** Updating Bandit could move unrelated dependencies.

Mitigation: exact resolver diff is a blocking review gate.

**False security closure:** Merely changing `mix.lock` could leave the manifest capable of accepting an advisory-affected version later.

Mitigation: encode the security floor in `mix.exs`.

**Unsafe rollback:** Operational pressure could tempt downgrade to 1.13.1.

Mitigation: explicitly prohibit advisory-affected rollback targets.

## 17. Decision classification

**CONTRACT_LOCKED**

Existing Ticketing product/domain semantics, tenancy, authorization, persistence and observable application contracts must remain unchanged.

**IMPLEMENTATION_LOCKED**

- Bandit minimum accepted version is 1.14.0.
- No advisory-affected rollback target.
- No unrelated dependency churn.
- Secure upstream HTTP/WebSocket behavior is accepted.
- Complete security/application verification is mandatory before merge.

**IMPLEMENTATION_FREE**

- exact smoke-test mechanics;
- exact safe later Bandit 1.x resolution if newer than 1.14.0 when implementation begins, subject to fresh review;
- mechanical form of resolver invocation.

**AUTHORITY_GAP**

None identified.

## 18. Downstream dependency

TICK-56 remains a prerequisite blocking TICK-26.

After TICK-56 is independently reviewed, explicitly merge-authorized, merged and reverified on `main`:

1. refresh TICK-26 against the new `main`;
2. re-check its approved JIP for staleness;
3. re-run PR #45 against fresh `main`;
4. require a new exact-head CI run;
5. independently review the rebased/updated exact diff before any merge recommendation.

TICK-26 must not inherit a stale pre-security-upgrade CI result.

## 19. Definition of Done

This JIP is complete only when:

- the approved Bandit security floor is encoded in the manifest;
- the exact lock resolves a non-vulnerable compatible Bandit;
- `mix hex.audit` is clean for Bandit;
- normal HTTP and LiveView/WebSocket compatibility is verified;
- no unexplained unrelated dependency drift exists;
- all applicable repository gates pass;
- exact-head CI is green;
- exact diff receives independent review;
- user merge authorization is obtained;
- merged `main` is reverified;
- required implementation docs/handoff are updated against the merged SHA;
- TICK-56 is closed only after all evidence is recorded;
- dependent TICK-26 is refreshed from the new accepted baseline.
