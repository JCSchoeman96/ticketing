# Runtime baseline

> Nature and status: Derived implementation documentation. This document describes merged implementation state and does not define product semantics.
>
> Last verified implementation main SHA: `2bfb68d579d39f05cd626e8c36a365d588cb8cbc`
>
> Governing JIPs: JIP-T0-00 / Plane TICK-1, approved; JIP-T0-01 v0.1.5 / Plane TICK-25 for the merged Identity authorization substrate and TICK-54 for the secure Ash/AshPostgres baseline; JIP-T0-SEC-01 v0.1.0 / Plane TICK-57 as the historical Bandit security restoration; JIP-T0-SEC-03 v0.1.0 / Plane TICK-61 as the current Bandit + Tidewave security baseline.
>
> Plane work includes TICK-2, TICK-3, TICK-4, TICK-5, TICK-9, TICK-13, TICK-25, TICK-53, TICK-54, TICK-56, TICK-57, TICK-60, TICK-61, and TICK-62.
>
> Relevant merged PRs include [#40 (TICK-25)](https://github.com/JCSchoeman96/ticketing/pull/40), [#42 (TICK-54)](https://github.com/JCSchoeman96/ticketing/pull/42), [#47 (SEC-01)](https://github.com/JCSchoeman96/ticketing/pull/47), and [#51 (SEC-03)](https://github.com/JCSchoeman96/ticketing/pull/51).

## Runtime and application identity

| Component | Baseline |
| --- | --- |
| Elixir | 1.20.4 |
| Erlang/OTP | 29.1.2 |
| Phoenix | 1.8.16 |
| Phoenix LiveView | 1.2.13 |
| Ash | 3.37.2 |
| AshPhoenix | 2.3.25 |
| AshPostgres | 2.15.2 |
| ash_sql | 0.8.4 (transitive) |
| SimpleSat | 0.1.4 |
| Postgrex | 0.22.4 |
| Bandit | 1.14.1 |

The root application namespace is `Ticketing`. Its OTP application identity is `:ticketing`.

## Merged domain runtime

`Ticketing.Identity` is a merged Ash domain. Its current resource boundary is:

- global `Ticketing.Identity.User`;
- tenant `Ticketing.Identity.OrgMembership`;
- tenant read-only T0 `Ticketing.Identity.Session`;
- tenant `Ticketing.Identity.OrgRoleAssignment`.

The domain exposes only the governed reads needed by the T0 organizer flow: User liveness, matching membership proof, Session liveness, and active role-assignment reads. Session has no create, update, or destroy Ash action in this baseline, and its liveness read deliberately excludes the sensitive `token_hash` field.

`Ticketing.Events` and `create_event` are not part of the merged runtime yet. They remain downstream TICK-26 work.

## Ash capability posture

JIP-T0-00 records `ADOPT` for Ash core, AshPhoenix, and AshPostgres. JIP-T0-01 v0.1.5 updates the merged implementation baseline to Ash 3.37.2 and AshPostgres 2.15.2 as a security prerequisite; `ash_sql` 0.8.4 is the required transitive resolution. That prerequisite does not adopt new Ash 3.37 APIs, DSL constructs, authorization mechanisms, transaction mechanisms, or product/domain behavior.

SimpleSat 0.1.4 is a direct runtime dependency used as the approved Ash policy SAT backend. PicoSAT remains unselected. The merged dependency baseline must continue to satisfy the repository security gate; known-vulnerable Ash 3.36.1 / AshPostgres 2.15.1 are not an accepted rollback target.

The existing JIP posture still defers Ash Signals, Temporal Resources, AshStateMachine, AshOban, AshAuthentication, AshPaperTrail, Ash Storage, and Ash JSON:API unless a later approved JIP adopts them. Reactor is present transitively through Ash, but Ticketing has not adopted it as an architectural capability. AshArchival remains rejected as a substitute for canonical lifecycle transitions. These decisions do not add or change product semantics.

## HTTP server security baseline

Bandit is Ticketing's production/runtime HTTP server. The direct dependency requirement is:

```elixir
{:bandit, ">= 1.14.1 and < 2.0.0-0"}
```

The current lock resolves Bandit 1.14.1. JIP-T0-SEC-01 historically moved Bandit from 1.13.1 to 1.14.0 in PR #47. A newly published advisory then made 1.14.0 invalid as the current security baseline; JIP-T0-SEC-03 moved Bandit from 1.14.0 to 1.14.1 in PR #51. SEC-01 remains historical evidence and SEC-03 governs the current secure runtime baseline.

PR #51 changed only the Bandit and Tidewave declarations/resolutions. No Plug, Phoenix, LiveView, Thousand Island, WebSock, Ash, database, frontend, or product/domain dependency moved. Bandit 1.14.0 and earlier advisory-affected releases are not accepted rollback targets.

The permanent Bandit runtime smoke introduced under SEC-01 remains part of the application test suite and verifies real HTTP plus Phoenix LiveView WebSocket compatibility. SEC-03 additionally reviewed Bandit's upstream regression coverage for fragmented HTTP/2 DATA-frame bodies rather than adding an unbounded exploit harness to Ticketing.

## Development and agent tooling

Tidewave 0.9.2 is a DEV-only dependency with the direct requirement:

```elixir
{:tidewave, ">= 0.9.2 and < 1.0.0", only: :dev}
```

The development endpoint binds to `127.0.0.1` and uses `TICKETING_DEV_HTTP_PORT`, which defaults to `4200`. Tidewave is mounted at `/tidewave/mcp` on that endpoint. SEC-03 verification confirmed normal local development access still works after Tidewave's Host-validation change, a foreign Host without Origin is rejected without exposing local path/configuration metadata, and the production dependency listing excludes Tidewave.

UsageRules is available in DEV and TEST. It supplies version-matched package guidance and generates framework skills under the repository-root `.agents/skills/` directory. The repository `AGENTS.md` files remain the source of implementation governance. The Ash UsageRules material was mechanically resynced for the merged Ash 3.37.2 baseline in TICK-54.

## Frontend tooling

| Tool | Baseline |
| --- | --- |
| Phoenix LiveView | 1.2.13 |
| Phoenix HTML | 4.3.0 |
| Tailwind Elixir wrapper | 0.5.1 |
| Tailwind CSS binary | 4.3.3 |
| esbuild Elixir wrapper | 0.10.0 |
| esbuild binary | 0.28.2 |
| Heroicons | v2.2.0 |
| Vendored DaisyUI plugin | 5.0.35 |

`mix assets.build` builds development assets. `mix assets.deploy` minifies assets and digests the output for deployment.

## Deployment

The repository deployment [`compose.yaml`](../../../compose.yaml) defines one application service, `ticketing`. It has no database or Redis service. [`ticketing/Dockerfile`](../../Dockerfile) builds the production release image.

Redis is N/A for Ticketing. The current runtime has no Redis/Redix dependency.
