# Runtime baseline

> Nature and status: Derived implementation documentation. This document describes merged implementation state and does not define product semantics.
>
> Last verified main SHA: `ebf0018d18fd4422707551a2b391d92f7ad52246`
>
> Governing JIP: JIP-T0-00 / Plane TICK-1, approved
>
> Plane work: TICK-2, TICK-3, TICK-5, TICK-9, TICK-13
>
> Merged PRs: [#8](https://github.com/JCSchoeman96/ticketing/pull/8), [#10](https://github.com/JCSchoeman96/ticketing/pull/10), [#11](https://github.com/JCSchoeman96/ticketing/pull/11), [#13](https://github.com/JCSchoeman96/ticketing/pull/13)

## Runtime and application identity

| Component | Baseline |
| --- | --- |
| Elixir | 1.20.4 |
| Erlang/OTP | 29.1.2 |
| Phoenix | 1.8.15 |
| Phoenix LiveView | 1.2.12 |
| Ash | 3.36.1 |
| AshPhoenix | 2.3.25 |
| AshPostgres | 2.15.1 |
| Postgrex | 0.22.4 |

The root application namespace is `Ticketing`. Its OTP application identity is `:ticketing`.

## Ash capability posture

JIP-T0-00 records `ADOPT` for Ash core, AshPhoenix, and AshPostgres. The merged application pins those packages at the versions above. This does not imply that every Ash extension or product-domain resource is implemented.

The JIP defers Ash Signals, Temporal Resources, AshStateMachine, AshOban, AshAuthentication, AshPaperTrail, Ash Storage, and Ash JSON:API. Reactor is present transitively through Ash, but Ticketing has not adopted it as an architectural capability. The JIP rejects AshArchival as a substitute for canonical lifecycle transitions. These decisions do not add or change product semantics.

## Development and agent tooling

Tidewave 0.9.1 is a DEV-only dependency. The development endpoint binds to `127.0.0.1` and uses `TICKETING_DEV_HTTP_PORT`, which defaults to `4200`. Tidewave is mounted at `/tidewave/mcp` on that endpoint.

UsageRules is available in DEV and TEST. It supplies version-matched package guidance and generates framework skills under the repository-root `.agents/skills/` directory. The repository `AGENTS.md` files remain the source of implementation governance.

## Frontend tooling

| Tool | Baseline |
| --- | --- |
| Phoenix LiveView | 1.2.12 |
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
