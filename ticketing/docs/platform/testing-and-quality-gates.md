# Testing and quality gates

> Nature and status: Derived implementation documentation. This document records current verification mechanics and baseline evidence; it does not define product semantics.
>
> Last verified main SHA: `342e2c1af89296753a31e70056dcf5d6c466ac3a`
>
> Governing JIPs: JIP-T0-00 / Plane TICK-1, approved; JIP-T0-01 v0.1.5 / Plane TICK-54 for the secure Ash/AshPostgres baseline.
>
> Plane work: TICK-6, TICK-7, TICK-8, TICK-9, TICK-13, TICK-14, TICK-17, TICK-53, TICK-54
>
> Merged PRs: [#10](https://github.com/JCSchoeman96/ticketing/pull/10), [#14](https://github.com/JCSchoeman96/ticketing/pull/14), [#15](https://github.com/JCSchoeman96/ticketing/pull/15), [#39 (TICK-53)](https://github.com/JCSchoeman96/ticketing/pull/39), [#42 (TICK-54)](https://github.com/JCSchoeman96/ticketing/pull/42)

## Mix aliases

The aliases below are defined in `ticketing/mix.exs`.

| Command | Current coverage |
| --- | --- |
| `mix precommit` | Checks UsageRules sync drift, formatting, compilation with warnings as errors, and ExUnit. |
| `mix check` | Checks UsageRules sync drift, `mix hex.audit`, formatting, compilation with warnings as errors, `mix ash.codegen --check`, `mix contract.authority`, ExUnit, Credo strict, Sobelow with `--private --exit Medium`, and a DEV asset build. |
| `mix check.types` | Runs Dialyzer with short output. |

## CI workflows

The application workflow in [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml) has two jobs. `bootstrap` starts a job-owned `postgres:18.6-alpine` service, runs `mix setup` and `mix check`, then runs the partitioned Repo smoke test with `MIX_TEST_PARTITION=1`. `check_types` runs `mix check.types` as a separate Dialyzer job.

The path-filtered [authority workflow](../../../.github/workflows/authority.yml) runs for changes under `authority/` and selected governance files. It runs authority tests, contract manifest verification, CANON pin verification, and a strict canonical audit. Application CI also invokes `mix contract.authority` through `mix check`.

## Security dependency gate

`mix hex.audit` is part of the ordinary `mix check` gate and therefore part of application CI. A dependency baseline that is subject to a known Hex security advisory is not an acceptable green baseline. Security-driven dependency movement still follows the repository's JIT/JIP prerequisite discipline; the audit gate does not authorize unrelated upgrades or feature adoption.

JIP-T0-01 v0.1.5 established Ash 3.37.2, AshPostgres 2.15.2, and required transitive `ash_sql` 0.8.4 as the merged secure baseline. A rollback must preserve a security-clean dependency set; downgrading to the advisory-affected Ash 3.36.1 / AshPostgres 2.15.1 baseline is not an accepted rollback path.

## Reviewed baseline evidence

[CI run 40295722833](https://github.com/JCSchoeman96/ticketing/actions/runs/40295722833) completed successfully on merged main SHA `342e2c1af89296753a31e70056dcf5d6c466ac3a` after PR #42.

- `mix hex.audit`: no retired or security-advisory packages found.
- UsageRules sync and `mix ash.codegen --check`: passed with no generated migration/schema drift.
- Canonical authority verification: passed with CANON-1 2.0.18 and the active T0 tracer.
- Application ExUnit run: 52 passed.
- Credo strict: no issues found across 139 modules/functions.
- Sobelow medium-or-higher threshold: passed; the pre-existing low-confidence tooling findings remain observations rather than suppressions.
- DEV asset build: passed.
- Partitioned PostgreSQL 18 Repo smoke: 18 passed.
- Dialyzer: Total errors 0, Skipped 0, Unnecessary Skips 0.

## Warning posture

Completed TICK-14 records the reviewed upstream and dependency warning families, including OTP `xmerl_ucs` missing-spec warnings during cold PLT construction and `yamerl` deprecated prefix-catch warnings. The review accepted those as upstream/toolchain observations without suppressions or dependency churn. Other cold dependency warnings are recorded there as well.

The low-confidence Sobelow findings are in the existing `contract_authority` tooling. TICK-17 did not introduce them, and TICK-54 did not change or suppress them. This documentation does not suppress or reclassify those findings.

## Applying these gates

These aliases describe the current baseline gates. A future change runs checks that apply to its scope under the repository instructions. This page does not require every application command to run for every documentation-only edit.
