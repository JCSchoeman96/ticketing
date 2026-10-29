# JIP-T0-SEC-03 implementation handoff

> Nature and status: Derived implementation change record for the current Bandit + Tidewave dependency-security restoration. This document records merged implementation state and does not define or override product semantics.
>
> Governing JIP: `planning/jips/JIP-T0-SEC-03_v0.1.0.md`, approved 2026-10-29
>
> Plane: TICK-61 parent JIP; TICK-62 atomic implementation; TICK-60 Bandit blocker resolved by the implementation
>
> Implementation baseline verified at: `2bfb68d579d39f05cd626e8c36a365d588cb8cbc`
>
> Implementation PR: [#51](https://github.com/JCSchoeman96/ticketing/pull/51)

## Scope and authority

JIP-T0-SEC-03 was a narrow atomic dependency-security prerequisite. It restored the global Hex security gate after Bandit 1.14.0 and Tidewave 0.9.1 became advisory-affected, while preserving the production/DEV dependency boundary and preventing unrelated resolver drift.

Canonical product/domain authority remained unchanged. The implementation introduced no domain resource, action, lifecycle, tenancy, actor, authorization, RLS, persistence, migration, transaction, concurrency, idempotency, error, event, outbox, job, money, inventory, or ticketing semantics.

## Merged implementation outcome

PR #51 was reviewed at exact implementation head `4a84e8aff17abbdd1815a4ed18b97097085c35cd` against dispatch/base SHA `5f6832e1ef4dd4cbaf49db1a719c8f9923568a79`.

After explicit user merge authorization, PR #51 merged as signed GitHub merge commit `2bfb68d579d39f05cd626e8c36a365d588cb8cbc` with parents:

- previous `main`: `5f6832e1ef4dd4cbaf49db1a719c8f9923568a79`;
- reviewed implementation head: `4a84e8aff17abbdd1815a4ed18b97097085c35cd`.

The exact base-to-merge delta contains only:

1. `ticketing/mix.exs`;
2. `ticketing/mix.lock`.

No test, application, authority, migration, generated resource, endpoint, frontend, or product/domain file changed in the SEC-03 implementation merge.

## Dependency baseline

The current direct requirements are:

```elixir
{:bandit, ">= 1.14.1 and < 2.0.0-0"}
{:tidewave, ">= 0.9.2 and < 1.0.0", only: :dev}
```

The lock moved exactly two packages:

- Bandit 1.14.0 → 1.14.1;
- Tidewave 0.9.1 → 0.9.2.

No unrelated package moved. In particular, the resolver did not move Phoenix, LiveView, Plug, Thousand Island, WebSock, `websock_adapter`, Ash, AshPhoenix, AshPostgres, Igniter, Phoenix Live Reload, Sourceror, or Spitfire. Tidewave remains DEV-only and the production dependency listing excludes it.

Bandit 1.14.0 and Tidewave 0.9.1 are advisory-affected and are not accepted rollback targets.

## Security evidence

### Bandit

The governing advisory was EEF-CVE-2026-116078 / CVE-2026-116078 / GHSA-pxjf-g536-7r93. Bandit versions below 1.14.1 in the affected range could amplify memory use when an HTTP/2 request body was fragmented into many one-byte DATA frames.

Upstream fix commit `327bb02ff84171237e1aeff787930debd16155ee` was independently reviewed. It accumulates HTTP/2 body DATA payloads into a binary instead of retaining one list cell/binary term per frame and adds a regression test that interleaves one-byte DATA frames across 16 heap-limited streams. Ticketing did not add an unbounded/high-memory exploit harness.

### Tidewave

The governing Tidewave advisory was EEF-CVE-2026-109823 / CVE-2026-109823. Tidewave 0.9.2 includes the Host-validation fix from upstream commit `80159536f752dc4d34797934d1516f29cea12b50`, preventing disallowed Host requests from receiving project metadata and checking Host alongside Origin policy.

## Runtime compatibility evidence

Focused SEC-03 verification covered:

- ordinary HTTP through `TicketingWeb.Endpoint`;
- JSON body parsing through `Plug.Parsers`, including malformed JSON rejection;
- the existing Phoenix LiveView `/live` WebSocket upgrade;
- normal localhost DEV Tidewave access;
- foreign Host without Origin returning 403 without local path/configuration metadata;
- Tidewave remaining absent from the production dependency set.

A separate Ticketing HTTP/2 fragmentation harness was not added. The approved JIP allowed reliance on the reviewed upstream bounded protocol regression together with Ticketing's endpoint/body-parsing compatibility evidence.

## Verification evidence

Before merge, local implementation verification passed:

- `mix hex.audit` — no retired or security-advisory packages found;
- `mix check` — including 80 ExUnit tests, Credo, Sobelow, authority checks, and asset build;
- `mix check.types` — zero Dialyzer errors;
- `mix precommit` — 80 tests;
- `git diff --check`;
- the focused runtime/security smokes above.

Exact-head [CI run 40854236375](https://github.com/JCSchoeman96/ticketing/actions/runs/40854236375) passed on reviewed head `4a84e8aff17abbdd1815a4ed18b97097085c35cd`, including application bootstrap, PostgreSQL 18.6 partition smoke, and Dialyzer.

Merged-main [CI run 40856980337](https://github.com/JCSchoeman96/ticketing/actions/runs/40856980337) then completed successfully on exact merge SHA `2bfb68d579d39f05cd626e8c36a365d588cb8cbc`. It recorded:

- clean global `mix hex.audit`;
- CANON-1 2.0.18 and active T0 tracer verification;
- 80 application ExUnit tests passed;
- Credo strict passed;
- Sobelow completed at the configured Medium-or-higher failure threshold;
- DEV asset build passed;
- PostgreSQL 18.6 partition smoke: 18 passed;
- Dialyzer: `Total errors: 0, Skipped: 0, Unnecessary Skips: 0`.

This satisfies the SEC-03 implementation and merged-main verification gates.

## Review and authorization

The control tower independently reviewed the exact two-file implementation diff, upstream security evidence, Plane dependency state, and exact-head CI. No scope expansion, resolver drift, authority gap, or merge-gate exception was found.

GitHub does not permit the connected repository-owner identity to formally APPROVE its own PR, so the control-tower PASS was recorded as commit-anchored COMMENT review `5696120834`. The user then explicitly authorized the exact reviewed implementation head and merged PR #51.

## Relationship to SEC-01 and SEC-02

SEC-01 remains valid historical evidence for the earlier Bandit 1.13.1 → 1.14.0 restoration and the permanent HTTP/WebSocket runtime smoke. SEC-03 does not rewrite those facts; it supersedes Bandit 1.14.0 as current state because of the newly published advisory.

SEC-02's separate Tidewave execution path was superseded before implementation. Its historical planning evidence remains preserved, while SEC-03 is the executed atomic restoration for both current advisories.

## Rollback posture

Do not roll back to Bandit 1.14.0 or Tidewave 0.9.1. If a runtime regression appears, retain secure dependency floors and evaluate a compatible secure release or an application-level mitigation under fresh review. Any material scope expansion or dependency movement requires the applicable JIT/Grill/JIP process.

## Downstream handoff

TICK-62 and TICK-60 may close after the successful merged-main verification recorded above. Parent TICK-61 remains open until the required derived documentation closeout is reviewed, merged, and checked against the implementation merge.

The SEC-01 parent TICK-57 is intended to close alongside this documentation so its historical record is preserved without reintroducing stale current-state documentation from draft PR #48.

TICK-26 remains blocked until the documentation closeout is complete and a fresh readiness check re-verifies current main, authority/CANON/manifest/ROADMAP/tracer, governing JIP, dependencies, and prior implementation candidate staleness. Pre-SEC-03 CI evidence must not be reused as current merge evidence.

## Documentation impact and closeout state

This closeout updates:

- `ticketing/docs/platform/runtime.md`;
- `ticketing/docs/platform/testing-and-quality-gates.md`;
- historical `ticketing/docs/handoffs/JIP-T0-SEC-01.md`;
- this `ticketing/docs/handoffs/JIP-T0-SEC-03.md`.

The implementation itself is verified complete at `2bfb68d579d39f05cd626e8c36a365d588cb8cbc`. The documentation closeout remains subject to exact-head CI/review, explicit user merge authorization, and post-merge verification before TICK-61/TICK-57 are closed and TICK-26 readiness is reconsidered.
