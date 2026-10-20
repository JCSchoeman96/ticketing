# Testing and quality gates

> Nature and status: Derived implementation documentation. This document records current verification mechanics and baseline evidence; it does not define product semantics.
>
> Last verified main SHA: `ebf0018d18fd4422707551a2b391d92f7ad52246`
>
> Governing JIP: JIP-T0-00 / Plane TICK-1, approved
>
> Plane work: TICK-6, TICK-7, TICK-8, TICK-9, TICK-13, TICK-14, TICK-17
>
> Merged PRs: [#10](https://github.com/JCSchoeman96/ticketing/pull/10), [#14](https://github.com/JCSchoeman96/ticketing/pull/14), [#15](https://github.com/JCSchoeman96/ticketing/pull/15)

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

## Reviewed baseline evidence

[CI run 39440841714](https://github.com/JCSchoeman96/ticketing/actions/runs/39440841714) completed successfully on main SHA `ebf0018d18fd4422707551a2b391d92f7ad52246`.

- Application ExUnit run: 24 passed.
- Partitioned PostgreSQL 18 Repo smoke: 12 passed.
- Dialyzer: Total errors 0, Skipped 0, Unnecessary Skips 0.

## Warning posture

Completed TICK-14 records the reviewed upstream and dependency warning families, including OTP `xmerl_ucs` missing-spec warnings during cold PLT construction and `yamerl` deprecated prefix-catch warnings. The review accepted those as upstream/toolchain observations without suppressions or dependency churn. Other cold dependency warnings are recorded there as well.

The low-confidence Sobelow findings are in the existing `contract_authority` tooling. TICK-17 did not introduce them. This documentation does not suppress or reclassify those findings.

## Applying these gates

These aliases describe the current baseline gates. A future change runs checks that apply to its scope under the repository instructions. This page does not require every application command to run for every documentation-only edit.
