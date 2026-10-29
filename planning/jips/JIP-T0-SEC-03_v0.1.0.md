# JIP-T0-SEC-03 v0.1.0

**Status:** APPROVED  
**Approval:** Explicit user acceptance on 2026-10-29 after independent control-tower PASS  
**Type:** Atomic dependency-security restoration prerequisite  
**Proposed Plane structure:** New SEC-03 parent with one atomic implementation child

## 1. Objective

Atomically restore Ticketing’s dependency-security baseline after the newly coupled Bandit and Tidewave advisories, while preserving the production and DEV dependency boundaries, preventing unrelated resolver drift, and restoring the repository’s globally clean security gate.

This packet is planning only. It does not authorize implementation until the JIP is explicitly accepted, persisted through the planning workflow, independently reviewed, decomposed in Plane, and the atomic child is approved as READY.

## 2. Exact baseline and authority

- Verified GitHub `main`: `77ebe45e3d99789b279f7fb5f3b3b106fb660475`
- CANON-1: 2.0.18
- Installed contract manifest blob: `bd4e8c750ea8fd17e94a9e89557d6e2da5e35b47`
- CANON artifact blob: `e6212a45f6c5499b081a9fe77101647cb098302c`
- ROADMAP: `B0 COMPLETE / T0 NEXT`, blob `3b5794e53bf66501eb2128d46f8ea2c666bcd59e`
- Active tracer: `authority/planning/tracers/T0-tenant-scoped-ga-pending-sale.md`, blob `ec9275c1e4534cd029235a4609c5874e6e36a663`
- Root and scoped governance and `planning/WORKFLOW.md`: verified against this `main`.
- Historical security packet: `planning/jips/JIP-T0-SEC-01_v0.1.0.md`, blob `9e1c21d77fa9e58cb7a795a534defa974bae5733`, approved and preserved as the October 26 decision.
- SEC-02 v0.1.0 exists on PR #49 head `332f9192786c432da0ee8fe01d8ea287baa334c6`; it records the Tidewave decision but is stale and superseded for execution if this atomic model is accepted.

No canonical product authority, roadmap, or tracer amendment is required. This is a runtime dependency-security prerequisite.

## 3. Security evidence

### Bandit

- Advisory: `EEF-CVE-2026-116078` / `CVE-2026-116078` / `GHSA-pxjf-g536-7r93`
- Published: 2026-10-28 13:26:25 UTC; modified: 13:41:02 UTC.
- Severity: High, CVSS 4.0 8.7, vector `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N`.
- Affected range: `>= 0.3.1 and < 1.14.1`.
- Fixed floor: 1.14.1.
- Attack: unauthenticated remote HTTP/2 request using many one-byte DATA frames to a body-reading Plug path. `Plug.Parsers` routes are affected. Impact is memory amplification and availability loss.
- Upstream fix: `327bb02ff84171237e1aeff787930debd16155ee`.
- Upstream tag commit: `710614b1c2eb526422c8cdb040bdd4f12b464015`.
- Hex 1.14.1 was published and resolved from the configured Hex source in this simulation.

### Tidewave

- Advisory: `EEF-CVE-2026-109823` / `CVE-2026-109823`.
- Published: 2026-10-27 15:47:36 UTC; modified: 16:01:15 UTC.
- Severity: Low, CVSS 4.0 2.3, vector `CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:P/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N`.
- Affected range: `>= 0.8.0 and < 0.9.2`.
- Fixed floor: 0.9.2.
- Attack: a developer visits a malicious DNS-rebinding page while the loopback development server is running. A same-origin request with no Origin header can expose local filesystem path metadata through `/tidewave/connect` or the toolbar.
- Upstream fix: `80159536f752dc4d34797934d1516f29cea12b50`.
- Upstream tag commit: `bf1f223f4897ada38ecc7e72c3f61bdcced4e46a`.
- Hex 0.9.2 was published and resolved from the configured Hex source in this simulation.

## 4. Technical baseline and dependency decisions

Current declarations are in [ticketing/mix.exs](/home/jcschoeman96/projects/current/ticketing/ticketing/mix.exs:50); current resolutions are in [ticketing/mix.lock](/home/jcschoeman96/projects/current/ticketing/ticketing/mix.lock:6).

**Bandit decision, `IMPLEMENTATION_LOCKED`:**

```elixir
{:bandit, ">= 1.14.1 and < 2.0.0-0"}
```

Bandit remains Ticketing’s production/runtime HTTP server and also serves the development endpoint.

**Tidewave decision, `IMPLEMENTATION_LOCKED`:**

```elixir
{:tidewave, ">= 0.9.2 and < 1.0.0", only: :dev}
```

Tidewave remains DEV-only. It must not become a test or production dependency.

The combined target lock resolves Bandit 1.14.1 and Tidewave 0.9.2. The targeted simulation changed no other lock entry. The full `mix.lock` diff is:

```diff
-  "bandit": {:hex, :bandit, "1.14.0", "555af34f126edb98d8b6b95bbeba4d5f4c3af21e37535d791f32db2365c532fb", [:mix], [{:hpax, "~> 1.1", [hex: :hpax, repo: "hexpm", optional: false]}, {:plug, "~> 1.18", [hex: :plug, repo: "hexpm", optional: false]}, {:telemetry, "~> 0.4 or ~> 1.0", [hex: :telemetry, repo: "hexpm", optional: false]}, {:thousand_island, "~> 1.6", [hex: :thousand_island, repo: "hexpm", optional: false]}, {:websock, "~> 0.5", [hex: :websock, repo: "hexpm", optional: false]}], "hexpm", "2d07630e4bf77b55240881386f7629bcc2f87426a299860b2d31c4ad77a48746"},
+  "bandit": {:hex, :bandit, "1.14.1", "5fb450e2360faf03d9b9fb45cfe52e14197f62d376c34781219bec0f9bc7ca06", [:mix], [{:hpax, "~> 1.1", [hex: :hpax, repo: "hexpm", optional: false]}, {:plug, "~> 1.18", [hex: :plug, repo: "hexpm", optional: false]}, {:telemetry, "~> 0.4 or ~> 1.0", [hex: :telemetry, repo: "hexpm", optional: false]}, {:thousand_island, "~> 1.6", [hex: :thousand_island, repo: "hexpm", optional: false]}, {:websock, "~> 0.5", [hex: :websock, repo: "hexpm", optional: false]}], "hexpm", "87c7ee5e08fb5f22d4e072e681e1101266a21432889b08ef8d0cb0c1450f8bba"},
-  "tidewave": {:hex, :tidewave, "0.9.1", "28bc14d3af0169f07c88ffd97004f344180a9cd2316d345f472bd22092cccd22", [:mix], [{:circular_buffer, "~> 0.4 or ~> 1.0", [hex: :circular_buffer, repo: "hexpm", optional: false]}, {:igniter, "~> 0.6", [hex: :igniter, repo: "hexpm", optional: true]}, {:jason, "~> 1.4", [hex: :jason, repo: "hexpm", optional: false]}, {:phoenix_live_reload, ">= 1.6.1", [hex: :phoenix_live_reload, repo: "hexpm", optional: true]}, {:plug, "~> 1.18", [hex: :plug, repo: "hexpm", optional: false]}, {:plug_cowboy, "~> 2.9", [hex: :plug_cowboy, repo: "hexpm", optional: true]}, {:websock_adapter, "~> 0.5", [hex: :websock_adapter, repo: "hexpm", optional: false]}], "hexpm", "dc8db03332b35084fd5b5fbe4fcb196c077bbe9cfdf883dcf6a5750a9bc19bb2"},
+  "tidewave": {:hex, :tidewave, "0.9.2", "a523b6af9a11a06807dbe09f645187dfdb2873603a169fb2274da46db54dbc1d", [:mix], [{:circular_buffer, "~> 0.4 or ~> 1.0", [hex: :circular_buffer, repo: "hexpm", optional: false]}, {:igniter, "~> 0.6", [hex: :igniter, repo: "hexpm", optional: true]}, {:jason, "~> 1.4", [hex: :jason, repo: "hexpm", optional: false]}, {:phoenix_live_reload, ">= 1.6.1", [hex: :phoenix_live_reload, repo: "hexpm", optional: true]}, {:plug, "~> 1.18", [hex: :plug, repo: "hexpm", optional: false]}, {:plug_cowboy, "~> 2.9", [hex: :plug_cowboy, repo: "hexpm", optional: true]}, {:websock_adapter, "~> 0.5", [hex: :websock_adapter, repo: "hexpm", optional: false]}], "hexpm", "66cba92861fa17cef3920caa9419bb001b81474dba0df3567f5b782675459879"},
```

A plain resolver run also selected Igniter 0.8.5, Phoenix Live Reload 1.7.0, Sourceror 1.13.0, Spitfire 0.4.3, and `websock_adapter` 0.7.0. None is required by the two security fixes. The tested targeted resolution preserved all five at their existing locked versions. Implementation must inspect the exact lock diff and stop if any other package moves.

The combined target’s `mix hex.audit` result was `No retired or security advisory packages found`.

## 5. Runtime compatibility and ownership

The endpoint uses `Bandit.PhoenixAdapter`, mounts Tidewave only when `Mix.env() == :dev`, and places `Plug.Parsers` before the router. The LiveView socket is `/live`. [Endpoint]( /home/jcschoeman96/projects/current/ticketing/ticketing/lib/ticketing_web/endpoint.ex:14) [Endpoint configuration](/home/jcschoeman96/projects/current/ticketing/ticketing/config/config.exs:52) [DEV endpoint](/home/jcschoeman96/projects/current/ticketing/ticketing/config/dev.exs:48) [runtime configuration](/home/jcschoeman96/projects/current/ticketing/ticketing/config/runtime.exs:85)

Bandit owns HTTP and HTTP/2 ingress parsing beneath Plug. Tidewave owns development tooling routes and toolbar metadata within the DEV endpoint. No Ticketing Ash Domain, Resource, action, or public domain interface is introduced or changed.

## 6. Ash capability evaluation

The installed baseline is Ash 3.37.2, AshPhoenix 2.3.25, and AshPostgres 2.15.2. None provides a mechanism relevant to the Bandit HTTP/2 body parser or Tidewave Host validation. No Ash upgrade or capability adoption is part of this JIP.

The existing posture remains: Ash core, AshPhoenix, and AshPostgres are adopted; Reactor remains present transitively but is not an adopted architecture; Ash Signals, Temporal Resources, Ash Storage, AshStateMachine, AshOban, AshPaperTrail/AshArchival, and AshAuthentication remain deferred or not applicable. No policy, actor, tenancy, RLS, transaction, persistence, or lifecycle behavior changes.

## 7. Reference evaluation

- Store Blueprint Hardening `d0e704ef6f2c83158149d2ecc5301c6ff864177f`: `NOT_APPLICABLE`. Commerce patterns do not govern this dependency-security work.
- LiveFrames `d03f635c779e86af907d9c1225b0bcba846bae62`: `NOT_APPLICABLE`. No frontend or design implementation is in scope.

Neither reference is semantic authority.

## 8. Scope and non-goals

Implementation scope is limited to:

- changing the Bandit and Tidewave manifest constraints to the locked ranges above;
- resolving and locking Bandit 1.14.1 and Tidewave 0.9.2, with no other package movement;
- adding only genuinely necessary runtime smoke or regression evidence;
- running the required repository verification;
- updating derived implementation documentation after the implementation merges.

Expected implementation files are `ticketing/mix.exs`, `ticketing/mix.lock`, and, only if required, the smallest focused runtime test or smoke file. Post-merge derived documentation is listed in Section 17.

This JIP does not authorize Phoenix, LiveView, Ash, Elixir, OTP, PostgreSQL, frontend, or other package upgrades; Git dependencies; security advisory suppressions; endpoint redesign; domain or product changes; TICK-26 implementation; Tidewave production exposure; migrations; or unrelated refactoring.

## 9. Decision classifications

**`CONTRACT_LOCKED`**

All existing Ticketing product and domain contracts remain unchanged. No lifecycle, tenancy, authorization, persistence, concurrency, error, event, money, or inventory semantics may change.

**`IMPLEMENTATION_LOCKED`**

- Bandit requirement: `>= 1.14.1 and < 2.0.0-0`.
- Tidewave requirement: `>= 0.9.2 and < 1.0.0`, `only: :dev`.
- The implementation is atomic across both advisories.
- The global security audit must not be suppressed or waived.
- Only Bandit and Tidewave lock entries may change.
- No Git dependency or unrelated dependency movement is permitted.
- Advisory-affected Bandit and Tidewave versions are not valid rollback targets.

**`IMPLEMENTATION_FREE`**

The test layout and resolver invocation may vary if the final result preserves the exact constraints and changes no unrelated lock entries. A later secure compatible resolution within the ranges can be considered only with fresh evidence and no scope expansion.

**`AUTHORITY_GAP`**

None identified.

## 10. Lifecycle, tenancy, persistence, and side effects

- Domain resources, actions, ownership, lifecycle states, transitions, and guards: `UNAFFECTED`.
- Tenancy, actors, authentication, authorization, capabilities, and RLS: `UNAFFECTED`.
- Persistence, schema, migrations, indexes, foreign keys, and database time: `UNAFFECTED`.
- Transactions, concurrency, locks, CAS/version fences, and idempotency/replay: `UNAFFECTED`.
- Canonical errors: `UNAFFECTED`. Upstream HTTP protocol rejections remain outside Ticketing domain error semantics.
- Events, outbox, jobs, and product audit records: `UNAFFECTED`.
- Money, inventory, orders, and ticketing behavior: `UNAFFECTED`.

Any unexpected change in these areas is a stop condition.

## 11. Observability

No product observability contract or telemetry schema is added. Verification should record resolved package versions, audit output, and runtime smoke results. Runtime review should watch for unexpected request failures or memory behavior. Development Host rejection must not log or expose filesystem paths or secrets.

## 12. Resolver invariant

The implementation must preserve all lock entries except Bandit and Tidewave. The disposable simulation used the targeted update path `mix deps.unlock bandit tidewave` followed by `mix deps.get`; it resolved both packages without transitive movement.

The lock diff must be reviewed as data. If either release is unavailable from the configured Hex source, the audit remains unclean, or another package must move, stop and return for review. Do not suppress advisories, change the package source, or use a Git dependency.

## 13. Rollout and rollback

No database migration or product rollout is required. The production release receives Bandit 1.14.1. Development receives Tidewave 0.9.2 and keeps Tidewave only in `:dev`. No feature flag or traffic migration is introduced.

Bandit 1.14.0 and Tidewave 0.9.1 are not valid rollback targets. If a runtime regression appears, roll back application code while retaining the secure dependencies, or evaluate another secure compatible release under a fresh review. A downgrade below either security floor is prohibited.

## 14. Required runtime and security evidence

Positive evidence must cover:

- ordinary HTTP through `TicketingWeb.Endpoint`;
- a body-reading request through `Plug.Parsers`;
- the existing LiveView `/live` WebSocket path;
- local DEV Tidewave access using `localhost`, including its intended connection route;
- the DEV-only dependency boundary.

Negative/security evidence must cover:

- review of Bandit 1.14.1’s upstream HTTP/2 fragmented DATA-frame regression tests; do not duplicate a high-memory exploit harness in Ticketing;
- Tidewave rejection of a foreign Host without Origin, with no Tidewave configuration/path metadata returned;
- the local Host path still working after Tidewave’s new Host check;
- a clean global `mix hex.audit`.

If a deterministic Ticketing HTTP/2 body smoke is practical, keep it bounded and focused. Otherwise, rely on Bandit’s upstream protocol regression coverage plus Ticketing’s endpoint/body-parsing smoke. Do not create an unbounded load test.

## 15. Repository verification and merge gates

The implementation must pass the exact applicable repository checks:

- `mix hex.audit`
- `mix check`
- `mix check.types`
- `mix precommit`
- `git diff --check`
- CI application bootstrap and PostgreSQL 18.6 partition smoke
- CI Dialyzer job
- all applicable runtime smoke and focused security evidence

**Planning-artifact review gate:** The planning PR must contain only the reviewed planning artifact, pass applicable planning/authority checks, and have fresh exact-head CI evidence. If application CI fails solely because the unchanged baseline still contains Bandit 1.14.0 and Tidewave 0.9.1, record that as a pre-existing security blocker. Do not call the run green, hide the failure, or suppress the advisories. The control tower reviews the exact planning diff and the documented CI result before the user authorizes a planning merge.

**Implementation merge gate:** Both advisories must be absent from the global `mix hex.audit`; all applicable checks must pass; exact-head CI must be green; the exact diff must receive independent review; and the user must explicitly authorize the merge. The implementation gate is not weakened by the planning-artifact exception.

## 16. Risks and stop conditions

Stop implementation if:

- Bandit 1.14.1 or Tidewave 0.9.2 cannot resolve from Hex;
- `mix hex.audit` reports any applicable advisory;
- any lock entry other than Bandit and Tidewave changes;
- framework, toolchain, database, or frontend versions move;
- Tidewave’s Host check breaks the configured local `localhost` flow and resolution requires broader endpoint exposure or unrelated changes;
- Bandit compatibility requires a Plug, Phoenix, LiveView, WebSocket, or Thousand Island upgrade;
- any domain, product, tenancy, authorization, RLS, persistence, transaction, concurrency, idempotency, error, event, or ticketing behavior changes;
- CI fails for a reason beyond the documented pre-existing advisories on a planning-only diff.

No new authority gap was found.

## 17. Documentation impact

Do not update implementation documentation during planning. After the implementation merges and exact `main` is verified:

- **UPDATE** `ticketing/docs/platform/runtime.md` with the new current Bandit and Tidewave baselines, preserving the Tidewave DEV-only boundary.
- **UPDATE** `ticketing/docs/platform/testing-and-quality-gates.md` with the restored global audit evidence and exact merged verification.
- **CREATE** `ticketing/docs/handoffs/JIP-T0-SEC-03.md` with the exact merge SHA, dependency diff, advisory evidence, verification, and downstream handoff.
- **UNAFFECTED** the historical SEC-01 handoff facts, assuming they remain recorded against their exact historical baseline. Reconcile PR #48’s current-state documentation against the SEC-03 merge before that PR proceeds.

The current docs are [runtime.md](/home/jcschoeman96/projects/current/ticketing/ticketing/docs/platform/runtime.md) and [testing-and-quality-gates.md](/home/jcschoeman96/projects/current/ticketing/ticketing/docs/platform/testing-and-quality-gates.md).

## 18. Proposed Plane and PR posture

Create a new SEC-03 parent with exactly one atomic dependency-security implementation child.

- Link TICK-60 to the child as the Bandit blocker it resolves. Do not set the child as blocked by TICK-60.
- Keep TICK-60’s existing block on TICK-57 and TICK-26 until the atomic child is complete and the merged `main` is verified.
- Mark TICK-58 and TICK-59 superseded for execution after the replacement path is accepted. Preserve their evidence and links; do not mark TICK-58 Done as a separately executed Tidewave change. Remove TICK-58’s obsolete blocking edges when adopting the new graph.
- Keep TICK-57 / SEC-01 closeout and TICK-26 blocked until SEC-03 merges, actual `main` and applicable CI are verified, and each downstream increment is refreshed for staleness.
- Keep PR #49 open, draft, and unmerged until the SEC-03 replacement/supersession path is approved. Then close it as superseded while retaining its branch and PR history.
- Keep PR #48 open and draft. After SEC-03 merges, refresh its current-state docs, preserve its SEC-01 historical record, and rerun exact-head CI and review.

## 19. Definition of Done

SEC-03 is complete only when:

- the user explicitly accepts this JIP and it is persisted through the approved planning path;
- Plane has one parent and one atomic implementation child, with dependencies reviewed;
- both exact manifest constraints are in place and Tidewave remains `only: :dev`;
- Bandit resolves to 1.14.1 and Tidewave to 0.9.2 from Hex;
- only the Bandit and Tidewave lock entries change;
- the global `mix hex.audit` is clean;
- runtime and security evidence in Section 14 passes;
- all required repository checks and exact-head CI pass;
- an independent reviewer approves the exact implementation diff;
- the user explicitly authorizes the implementation merge;
- merged `main` and its CI are verified;
- the documentation in Section 17 is checked against that merged SHA;
- TICK-60 is resolved only after the secure merged baseline is verified;
- TICK-57 and TICK-26 remain blocked until their freshness and dependency state are rechecked.

## SEC-02 and PR closeout note

SEC-02 should **not** become v0.2.0 if SEC-03 is accepted. Keep v0.1.0 unchanged as historical evidence and mark its Plane execution path superseded. The separate Tidewave implementation it planned is absorbed by SEC-03.

If a separate SEC-02 execution path is required because SEC-03 is rejected, it needs a versioned amendment that refreshes its baseline SHA, records Bandit 1.14.1 as the prerequisite baseline, replaces the old dependency graph and TICK-60 sequencing, updates CI expectations to account for the global audit cycle, and revises its DoD to require the globally clean audit after both advisories are fixed. Its Tidewave range and `only: :dev` decision remain unchanged. That is not the recommended path.

## Completion statement

The disposable worktree was removed. The original checkout has no tracked changes from this work; its pre-existing untracked files remain untouched. **No implementation, Plane mutation, PR mutation, merge, or READY transition was performed.**