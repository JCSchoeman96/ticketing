# JIP-T0-SEC-01 implementation handoff

> Nature and status: Historical derived implementation change record for the first Bandit security prerequisite. It records the exact SEC-01 implementation and does not define or override product semantics. The current HTTP/development-tooling security baseline is governed by JIP-T0-SEC-03.
>
> Governing JIP: `planning/jips/JIP-T0-SEC-01_v0.1.0.md`, approved
>
> Plane: TICK-57 parent JIP; TICK-56 implementation prerequisite
>
> SEC-01 implementation baseline verified at: `77ebe45e3d99789b279f7fb5f3b3b106fb660475`
>
> Implementation PR: [#47](https://github.com/JCSchoeman96/ticketing/pull/47)
>
> Current superseding implementation baseline: `2bfb68d579d39f05cd626e8c36a365d588cb8cbc` under JIP-T0-SEC-03 / PR #51.

## Scope and authority

JIP-T0-SEC-01 was a narrow security prerequisite blocking downstream TICK-26. It changed only the Ticketing HTTP server dependency baseline and added the smallest permanent runtime compatibility smoke required by that JIP.

Canonical product/domain authority remained upstream in `authority/`. This prerequisite created no product/domain semantics and did not change tenancy, authorization, RLS, persistence, lifecycle, money, inventory, events, outbox, jobs, or downstream Event behavior.

## SEC-01 merged implementation outcome

PR #47 merged to `main` as `77ebe45e3d99789b279f7fb5f3b3b106fb660475` with parents:

- previous `main`: `dc9cc444229c2cab1704a297519a94d2317c6103`;
- reviewed implementation head: `b128626fb050805d7d2ae80cdb57575a5feb0ac4`.

The exact merge delta contained only:

1. `ticketing/mix.exs`;
2. `ticketing/mix.lock`;
3. `ticketing/test/ticketing_web/bandit_runtime_smoke_test.exs`.

No authority, domain implementation, migration, generated Ash resource, endpoint-design, frontend, tenancy/RLS/auth, or TICK-26 file changed in the implementation merge.

## Historical dependency decision

SEC-01 changed the Bandit direct dependency requirement to:

```elixir
{:bandit, ">= 1.14.0 and < 2.0.0-0"}
```

The lock moved Bandit only:

- before: Bandit 1.13.1;
- after: Bandit 1.14.0.

The only additional textual `mix.lock` change was normalization of the pre-existing missing final newline. No other package version moved.

This was the correct secure floor for the advisory set known when SEC-01 was approved. It is retained here as historical evidence only. A later advisory published on October 28 affected Bandit 1.14.0, so 1.14.0 is no longer a valid current or rollback baseline.

## Runtime compatibility evidence

The permanent `TicketingWeb.BanditRuntimeSmokeTest` introduced by SEC-01 verifies:

- the resolved Bandit version satisfies the governed secure range in force for the current implementation;
- a real TCP HTTP request through `TicketingWeb.Endpoint` returns a successful response;
- a real WebSocket upgrade through the Phoenix LiveView `/live` socket succeeds.

The smoke is application compatibility evidence, not a local reimplementation of upstream Bandit CVE exploit tests. Upstream protocol fixes remain owned by Bandit.

## SEC-01 verification evidence

TDD evidence was captured before the dependency change: on Bandit 1.13.1 the real HTTP and WebSocket paths passed while the SEC-01 security-floor assertion failed. After the manifest change, Mix resolved only Bandit to 1.14.0.

[CI run 40514946850](https://github.com/JCSchoeman96/ticketing/actions/runs/40514946850) completed successfully on the exact cleaned PR head `b128626fb050805d7d2ae80cdb57575a5feb0ac4`.

That run verified the restored standard workflow after temporary implementation-only CI helpers had been removed. Its evidence included application setup and `mix check`, `mix hex.audit`, formatting, warnings-as-errors compilation, `mix ash.codegen --check`, `mix contract.authority`, ExUnit, Credo strict, Sobelow, DEV asset build, PostgreSQL 18 partition verification, and `mix check.types` / Dialyzer.

Merged-main [CI run 40535358726](https://github.com/JCSchoeman96/ticketing/actions/runs/40535358726) then completed successfully on exact SEC-01 merge SHA `77ebe45e3d99789b279f7fb5f3b3b106fb660475`. That satisfied SEC-01's implementation verification gate at the time.

## Relationship to SEC-03

SEC-03 does not rewrite SEC-01 history. It records a newly discovered security state and supersedes only the current dependency baseline.

JIP-T0-SEC-03 v0.1.0 / PR #51 atomically changed:

- Bandit 1.14.0 → 1.14.1, with current requirement `>= 1.14.1 and < 2.0.0-0`;
- Tidewave 0.9.1 → 0.9.2, with current requirement `>= 0.9.2 and < 1.0.0`, still DEV-only.

PR #51 merged as `2bfb68d579d39f05cd626e8c36a365d588cb8cbc`, and merged-main CI run 40856980337 passed on that exact SHA. Current platform documentation therefore points to SEC-03 for the secure HTTP/development-tooling baseline while this handoff remains the historical SEC-01 record.

## Review and authorization

The exact SEC-01 three-file candidate was reviewed against JIP-T0-SEC-01 and no defect was identified. The repository owner explicitly approved the exact candidate and authorized PR #47's merge before it was merged with an expected-head lease on `b128626fb050805d7d2ae80cdb57575a5feb0ac4`.

## Rollback posture

Security regression is not an acceptable rollback strategy. Do not restore Bandit 1.13.1 or 1.14.0. The current minimum is governed by SEC-03. If a valid-traffic regression is discovered, prefer a newer patched compatible Bandit 1.x release or an operational mitigation while a reviewed safe application fix is prepared. Material scope expansion requires targeted re-Grill/reapproval.

## Downstream handoff

TICK-56 and parent TICK-57 may close only after this historical handoff and the current SEC-03 platform documentation are merged through the governed documentation closeout. TICK-26 remains blocked until that closeout is complete and its authority/JIP/baseline/dependency freshness is rechecked against current `main`.

The pre-security-upgrade TICK-26 CI result must not be reused as merge evidence.

## Closeout state

SEC-01 implementation and its historical merged-main verification are complete. The original draft documentation PR #48 became stale as current-state documentation after SEC-03 changed the dependency baseline. This historical record is therefore preserved through the combined SEC-01/SEC-03 documentation closeout rather than by merging stale current-state edits from PR #48.

The documentation closeout itself still requires exact-head review/CI, explicit user merge authorization, and merged-main verification before the SEC-01 parent can close.
