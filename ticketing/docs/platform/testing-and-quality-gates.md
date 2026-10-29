# Testing and quality gates

> Nature and status: Derived implementation documentation. This document records current verification mechanics and merged baseline evidence; it does not define product semantics.
>
> Last verified implementation main SHA: `2bfb68d579d39f05cd626e8c36a365d588cb8cbc`
>
> Governing JIPs: JIP-T0-00 / Plane TICK-1, approved; JIP-T0-01 v0.1.5 / Plane TICK-25 and TICK-54; JIP-T0-SEC-01 v0.1.0 / Plane TICK-57 as historical security evidence; JIP-T0-SEC-03 v0.1.0 / Plane TICK-61 as the current dependency-security restoration.
>
> Plane work includes TICK-6, TICK-7, TICK-8, TICK-9, TICK-13, TICK-14, TICK-17, TICK-25, TICK-53, TICK-54, TICK-56, TICK-57, TICK-60, TICK-61, and TICK-62.
>
> Relevant merged PRs include [#40 (TICK-25)](https://github.com/JCSchoeman96/ticketing/pull/40), [#42 (TICK-54)](https://github.com/JCSchoeman96/ticketing/pull/42), [#47 (SEC-01)](https://github.com/JCSchoeman96/ticketing/pull/47), and [#51 (SEC-03)](https://github.com/JCSchoeman96/ticketing/pull/51).

## Mix aliases

The aliases below are defined in `ticketing/mix.exs`.

| Command | Current coverage |
| --- | --- |
| `mix precommit` | Checks UsageRules sync drift, formatting, compilation with warnings as errors, and ExUnit. |
| `mix check` | Checks UsageRules sync drift, `mix hex.audit`, formatting, compilation with warnings as errors, `mix ash.codegen --check`, `mix contract.authority`, ExUnit, Credo strict, Sobelow with `--private --exit Medium`, and a DEV asset build. |
| `mix check.types` | Runs Dialyzer with short output. |

## CI workflows

The application workflow in [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml) has two jobs. `bootstrap` starts a job-owned `postgres:18.6-alpine` service, runs application setup and `mix check`, then runs the partitioned Repo smoke test with `MIX_TEST_PARTITION=1`. `check_types` runs `mix check.types` as a separate Dialyzer job.

The path-filtered [authority workflow](../../../.github/workflows/authority.yml) runs for changes under `authority/` and selected governance files. It runs authority tests, contract manifest verification, CANON pin verification, and a strict canonical audit. Application CI also invokes `mix contract.authority` through `mix check`.

## Security dependency gate

`mix hex.audit` is part of the ordinary `mix check` gate and therefore part of application CI. A dependency baseline subject to a known Hex security advisory is not an acceptable green baseline. Security-driven dependency movement still follows the repository's JIT/JIP prerequisite discipline; the audit gate does not authorize unrelated upgrades or feature adoption.

JIP-T0-01 v0.1.5 established Ash 3.37.2, AshPostgres 2.15.2, and required transitive `ash_sql` 0.8.4 as the merged secure Ash baseline. Downgrading to the advisory-affected Ash 3.36.1 / AshPostgres 2.15.1 combination is not an accepted rollback path.

JIP-T0-SEC-01 v0.1.0 historically established Bandit 1.14.0 after the October 26 advisory set. JIP-T0-SEC-03 v0.1.0 supersedes that version as current runtime state after the October 28 Bandit advisory and the Tidewave advisory. The current requirements/resolutions are:

- Bandit requirement `>= 1.14.1 and < 2.0.0-0`, locked 1.14.1;
- Tidewave requirement `>= 0.9.2 and < 1.0.0`, locked 0.9.2 and `only: :dev`.

The SEC-03 implementation changed exactly those two dependency declarations and exactly those two lock entries. No unrelated dependency moved and the global audit is clean. Bandit 1.14.0 and Tidewave 0.9.1 are not accepted rollback targets.

## Security runtime evidence

SEC-03 verified the dependency changes without adding a high-memory exploit harness to Ticketing:

- ordinary HTTP through `TicketingWeb.Endpoint` returned successfully;
- a JSON body reached `Plug.Parsers`, and malformed JSON was rejected with 400;
- the existing `/live` WebSocket path completed a 101 upgrade;
- local DEV Tidewave access succeeded;
- a foreign Host without Origin was rejected with 403 and did not expose local path/configuration metadata;
- production dependency listing excluded Tidewave;
- Bandit upstream fix commit `327bb02ff84171237e1aeff787930debd16155ee` was reviewed, including its heap-limited regression test that interleaves one-byte HTTP/2 DATA frames across 16 streams.

The approved JIP treated a separate bounded Ticketing HTTP/2 body smoke as optional when upstream protocol regression coverage plus Ticketing endpoint/body-parsing compatibility evidence were sufficient. No unbounded load or exploit test was introduced.

## Identity verification coverage

The merged TICK-25 test suite covers the implemented Identity boundary, including:

- canonical resource shapes, nullability, identities and relationships;
- governed liveness/probe interface scope;
- active/non-revoked Membership and RoleAssignment reads;
- active, non-revoked, unexpired Session liveness;
- Session read-only posture and exclusion of sensitive `token_hash` from the liveness read;
- test-only owner fixture boundary;
- generated migration and resource-snapshot inspection;
- exact PostgreSQL catalog order of all four required org-first tenant indexes;
- constrained-runtime RLS behavior for Membership, Session and RoleAssignment;
- no-tenant, wrong-tenant and correct-tenant visibility cases;
- global physical UUID lookup not bypassing tenant RLS for Session and RoleAssignment.

These tests verify the merged Identity substrate only. They do not claim that the downstream organizer-to-Event transaction has been implemented; that remains TICK-26.

## Reviewed SEC-03 implementation evidence

PR #51 was reviewed at exact head `4a84e8aff17abbdd1815a4ed18b97097085c35cd` against base `5f6832e1ef4dd4cbaf49db1a719c8f9923568a79`. Exact-head [CI run 40854236375](https://github.com/JCSchoeman96/ticketing/actions/runs/40854236375) passed before merge. Local implementation verification also passed `mix hex.audit`, `mix check`, `mix check.types`, `mix precommit`, and `git diff --check`, together with the focused HTTP/body/WebSocket/Tidewave security smokes described above.

PR #51 then merged as signed main commit `2bfb68d579d39f05cd626e8c36a365d588cb8cbc`. Merged-main [CI run 40856980337](https://github.com/JCSchoeman96/ticketing/actions/runs/40856980337) completed successfully on that exact SHA.

The merged-main run verified:

- Toolchain: Elixir 1.20.4 / Erlang/OTP 29.1.2.
- PostgreSQL service: 18.6.
- `mix hex.audit`: no retired or security-advisory packages found.
- UsageRules sync, formatting, warnings-as-errors compilation, `mix ash.codegen --check`, and `mix contract.authority`: passed through `mix check`.
- Canonical authority verification: CANON-1 2.0.18 and active tracer `planning/tracers/T0-tenant-scoped-ga-pending-sale.md`.
- Application ExUnit: 80 passed.
- Credo strict: no issues found across 171 modules/functions.
- Sobelow: completed at the configured Medium-or-higher failure threshold; existing low-confidence tooling findings remain observations, not suppressions.
- DEV asset build: passed.
- Partitioned PostgreSQL 18 Repo smoke: 18 passed.
- Dialyzer: `Total errors: 0, Skipped: 0, Unnecessary Skips: 0`.

This is the current reviewed merged implementation baseline for the dependency-security gate.

## Historical SEC-01 evidence

SEC-01 remains a historical implementation record rather than the current dependency baseline. PR #47 merged Bandit 1.13.1 → 1.14.0 at main SHA `77ebe45e3d99789b279f7fb5f3b3b106fb660475`, added the permanent HTTP/LiveView WebSocket Bandit runtime smoke, and passed exact-head CI run 40514946850 plus merged-main CI run 40535358726. The later SEC-03 advisory did not invalidate those historical facts; it invalidated Bandit 1.14.0 as an acceptable current or rollback baseline.

## Warning posture

Completed TICK-14 records reviewed upstream/dependency warning families, including OTP `xmerl_ucs` missing-spec warnings during cold PLT construction and `yamerl` deprecated prefix-catch warnings. Current CI also reports the existing Mix `xref: [exclude: ...]` deprecation and several upstream dependency compiler/type warnings. They do not change the green application gate and were not suppressed by SEC-03.

The low-confidence Sobelow findings remain in existing infrastructure/tooling code. No Medium-or-higher finding failed the configured security check.

## Applying these gates

These aliases and evidence describe the current merged implementation baseline. Future changes run the checks applicable to their scope under repository instructions. Documentation-only maintenance does not create an exception to semantic or implementation verification when code, schema, dependencies, security, or observable behavior also change.
