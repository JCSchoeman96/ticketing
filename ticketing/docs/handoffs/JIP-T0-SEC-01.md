# JIP-T0-SEC-01 implementation handoff

> Nature and status: Derived implementation change record for the Bandit security prerequisite. This document records merged implementation state and does not define or override product semantics.
>
> Governing JIP: `planning/jips/JIP-T0-SEC-01_v0.1.0.md`, approved
>
> Plane: TICK-57 parent JIP; TICK-56 implementation prerequisite
>
> Implementation baseline verified at: `77ebe45e3d99789b279f7fb5f3b3b106fb660475`
>
> Implementation PR: [#47](https://github.com/JCSchoeman96/ticketing/pull/47)
>
> Documentation impact: UPDATE `ticketing/docs/platform/runtime.md`; UPDATE `ticketing/docs/platform/testing-and-quality-gates.md`; CREATE `ticketing/docs/handoffs/JIP-T0-SEC-01.md`.

## Scope and authority

JIP-T0-SEC-01 was a narrow security prerequisite blocking downstream TICK-26. It changed only the Ticketing HTTP server dependency baseline and added the smallest permanent runtime compatibility smoke required by the JIP.

Canonical product/domain authority remains upstream in `authority/`. This prerequisite created no product/domain semantics and did not change tenancy, authorization, RLS, persistence, lifecycle, money, inventory, events, outbox, jobs, or downstream Event behavior.

## Merged implementation outcome

PR #47 merged to `main` as `77ebe45e3d99789b279f7fb5f3b3b106fb660475` with parents:

- previous `main`: `dc9cc444229c2cab1704a297519a94d2317c6103`;
- reviewed implementation head: `b128626fb050805d7d2ae80cdb57575a5feb0ac4`.

The exact merge delta contains only:

1. `ticketing/mix.exs`;
2. `ticketing/mix.lock`;
3. `ticketing/test/ticketing_web/bandit_runtime_smoke_test.exs`.

No authority, domain implementation, migration, generated Ash resource, endpoint-design, frontend, tenancy/RLS/auth, or TICK-26 file changed in the implementation merge.

## Dependency baseline

The direct dependency requirement is now:

```elixir
{:bandit, ">= 1.14.0 and < 2.0.0-0"}
```

The lock moved Bandit only:

- before: Bandit 1.13.1;
- after: Bandit 1.14.0.

The only additional textual `mix.lock` change was normalization of the pre-existing missing final newline. No other package version moved.

Bandit versions below 1.14.0 are not an accepted rollback target for this baseline. A later safe Bandit 1.x release may resolve under the manifest range only through ordinary dependency/security review.

## Runtime compatibility evidence

The permanent `TicketingWeb.BanditRuntimeSmokeTest` verifies:

- the resolved Bandit version satisfies the approved secure range;
- a real TCP HTTP request through `TicketingWeb.Endpoint` returns a successful response;
- a real WebSocket upgrade through the Phoenix LiveView `/live` socket succeeds.

The smoke is application compatibility evidence, not a local reimplementation of upstream Bandit CVE exploit tests. Upstream protocol fixes remain owned by Bandit.

## Verification evidence

TDD evidence was captured before the dependency change: on Bandit 1.13.1 the real HTTP and WebSocket paths passed while the approved security-floor assertion failed. After the manifest change, Mix resolved only Bandit to 1.14.0.

[CI run #188](https://github.com/JCSchoeman96/ticketing/actions/runs/40514946850) completed successfully on the exact cleaned PR head `b128626fb050805d7d2ae80cdb57575a5feb0ac4`.

That run verified the restored standard workflow after temporary implementation-only CI helpers had been removed. Its evidence includes:

- application setup and verification through `mix check`;
- `mix hex.audit` through the ordinary gate;
- formatting and warnings-as-errors compilation;
- `mix ash.codegen --check`;
- `mix contract.authority`;
- ExUnit, Credo strict, Sobelow, and DEV asset build through `mix check`;
- PostgreSQL 18 partition verification;
- `mix check.types` / Dialyzer.

The merged implementation commit is the signed GitHub merge `77ebe45e3d99789b279f7fb5f3b3b106fb660475`. Merged-main [CI run #189](https://github.com/JCSchoeman96/ticketing/actions/runs/40535358726) completed successfully on that exact SHA: the `bootstrap` job passed application verification and PostgreSQL 18 partition verification, and `check_types` passed Dialyzer. This satisfies the JIP's merged-main implementation verification gate.

## Review and authorization

The exact three-file candidate was reviewed against JIP-T0-SEC-01 and no defect was identified. The repository owner explicitly approved the exact candidate and authorized the merge before PR #47 was merged with an expected-head lease on `b128626fb050805d7d2ae80cdb57575a5feb0ac4`.

## Rollback posture

Security regression is not an acceptable rollback strategy. Do not restore Bandit 1.13.1 or another advisory-affected version below the approved floor. If a valid-traffic regression is discovered, prefer a newer patched compatible Bandit 1.x release or an operational mitigation while a reviewed safe application fix is prepared. Material scope expansion requires targeted re-Grill/reapproval.

## Downstream handoff to TICK-26

TICK-56 remains the native prerequisite blocking TICK-26 until this closeout is complete. After the required documentation closeout is reviewed and merged:

1. close TICK-56 only after its evidence is recorded;
2. close parent TICK-57 only after the JIP closeout evidence is complete;
3. refresh TICK-26 / PR #45 from the new secure `main` baseline;
4. re-check JIP-T0-01 v0.1.5 for staleness against the refreshed baseline;
5. require a fresh exact-head CI run for the refreshed PR #45, including PostgreSQL 18 partition verification;
6. independently review the refreshed exact diff before any TICK-26 merge recommendation.

The pre-security-upgrade TICK-26 CI result must not be reused as merge evidence.

## Closeout state

Implementation merge and merged-main verification are complete at `77ebe45e3d99789b279f7fb5f3b3b106fb660475`.

PR #48's documentation closeout must receive exact-head CI, review, and explicit merge authorization before it may merge. Exact CI run identifiers are execution evidence in GitHub/Plane and are intentionally not embedded as self-referential closeout requirements in this handoff.

Plane must record final execution evidence before TICK-56/TICK-57 are closed.
