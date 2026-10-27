# Testing and quality gates

> Nature and status: Derived implementation documentation. This document records current verification mechanics and merged baseline evidence; it does not define product semantics.
>
> Last verified main SHA: `77ebe45e3d99789b279f7fb5f3b3b106fb660475`
>
> Governing JIPs: JIP-T0-00 / Plane TICK-1, approved; JIP-T0-01 v0.1.5 / Plane TICK-25 and TICK-54; JIP-T0-SEC-01 v0.1.0 / Plane TICK-57 and TICK-56.
>
> Plane work includes TICK-6, TICK-7, TICK-8, TICK-9, TICK-13, TICK-14, TICK-17, TICK-53, TICK-54, TICK-25, TICK-56, TICK-57.
>
> Merged PRs include [#39 (TICK-53)](https://github.com/JCSchoeman96/ticketing/pull/39), [#42 (TICK-54)](https://github.com/JCSchoeman96/ticketing/pull/42), [#40 (TICK-25)](https://github.com/JCSchoeman96/ticketing/pull/40), and [#47 (TICK-56)](https://github.com/JCSchoeman96/ticketing/pull/47).

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

JIP-T0-01 v0.1.5 established Ash 3.37.2, AshPostgres 2.15.2, and required transitive `ash_sql` 0.8.4 as the merged secure baseline. Downgrading to the advisory-affected Ash 3.36.1 / AshPostgres 2.15.1 combination is not an accepted rollback path.

JIP-T0-SEC-01 v0.1.0 establishes Bandit 1.14.0 as the merged secure HTTP server baseline and requires the manifest floor `>= 1.14.0 and < 2.0.0-0`. Bandit 1.13.1 and other advisory-affected versions below 1.14.0 are not accepted rollback targets. The TICK-56 resolver diff moved only Bandit 1.13.1 -> 1.14.0; the only other `mix.lock` textual change was final-newline normalization.

The permanent Bandit runtime smoke asserts the approved version floor, sends a real TCP HTTP request through `TicketingWeb.Endpoint`, and performs a real WebSocket upgrade against the Phoenix LiveView `/live` socket. The application owns compatibility smoke; upstream Bandit owns protocol-level exploit regression coverage for the published advisories.

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

## Reviewed merged baseline evidence

[CI run 40313655766](https://github.com/JCSchoeman96/ticketing/actions/runs/40313655766) completed successfully on merged main SHA `c6979779a33ca2e4f84573bab7211bb800cf45cb` after PR #40.

- Toolchain: Elixir 1.20.4 / Erlang/OTP 29.1.2.
- PostgreSQL service: 18.6.
- `mix hex.audit`: no retired or security-advisory packages found.
- UsageRules sync, formatting, warnings-as-errors compilation, and `mix ash.codegen --check`: passed.
- Canonical authority verification: passed with CANON-1 2.0.18 and the active T0 tracer.
- Application ExUnit run: 77 passed.
- Credo strict: no issues found across 168 modules/functions.
- Sobelow medium-or-higher threshold: passed; the existing low-confidence tooling findings remain observations rather than suppressions.
- DEV asset build: passed.
- Partitioned PostgreSQL 18 Repo smoke: 18 passed.
- Dialyzer: Total errors 0, Skipped 0, Unnecessary Skips 0.

The bootstrap run also applied the merged TICK-25 migrations and runtime grants successfully before exercising the application and constrained-runtime database tests.

### Bandit security prerequisite evidence

PR #47 merged the reviewed TICK-56 implementation to `main` as `77ebe45e3d99789b279f7fb5f3b3b106fb660475`. The exact merge delta from its base contains only `ticketing/mix.exs`, `ticketing/mix.lock`, and `ticketing/test/ticketing_web/bandit_runtime_smoke_test.exs`.

[CI run 40514946850](https://github.com/JCSchoeman96/ticketing/actions/runs/40514946850) completed successfully on the exact cleaned PR head `b128626fb050805d7d2ae80cdb57575a5feb0ac4` before merge. Its `bootstrap` job passed application verification and PostgreSQL 18 partition verification, and its `check_types` job passed Dialyzer.

Merged-main [CI run 40535358726](https://github.com/JCSchoeman96/ticketing/actions/runs/40535358726) completed successfully on `77ebe45e3d99789b279f7fb5f3b3b106fb660475`. Its `bootstrap` job passed the full application verification and PostgreSQL 18 partition verification, and its `check_types` job passed Dialyzer. This is the required post-merge verification for the TICK-56 implementation baseline.

## Warning posture

Completed TICK-14 records reviewed upstream/dependency warning families, including OTP `xmerl_ucs` missing-spec warnings during cold PLT construction and `yamerl` deprecated prefix-catch warnings. Current CI also reports the existing Mix `xref: [exclude: ...]` deprecation and several upstream dependency compiler/type warnings. They do not change the green application gate and have not been suppressed by TICK-25.

The low-confidence Sobelow findings remain in existing infrastructure/tooling code. No Medium-or-higher finding failed the configured security check.

## Applying these gates

These aliases and evidence describe the current merged baseline. Future changes run the checks applicable to their scope under repository instructions. Documentation-only maintenance does not create an exception to semantic or implementation verification when code, schema, dependencies, security, or observable behavior also change.
