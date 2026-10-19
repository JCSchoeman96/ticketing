# Feature Planning Pack: FP-MVP0-000 — Repo and Airlock Scaffolding


> Status: Draft implementation handoff pack.  
> Phase: Legislative Mode -> MVP-0 only.  
> Root namespace: `Ticketing`.  
> OTP app atom: `:ticketing`.  
> Ash posture: Ash 3.x only.  
> Product work: BLOCKED unless explicitly allowed by this pack.  
> Authority rule: contracts and gates win over this planning pack.


## 1. Identity

| Field | Value |
|---|---|
| `feature_pack_id` | `FP-MVP0-000-repo-airlock-scaffold` |
| `source_row_ids` | A-to-Z §17 / §29, TB-000 preconditions, planning catalogue first-sequence row 1 |
| `classification` | `PP` — platform primitive / foundation scaffold |
| `FR_ref` | `FR-MVP0-000` — NEW: proposed planning handle until FR-1 exists |
| `release_phase` | `foundation` |
| `mvp_blocker` | `yes` |
| `coding_agent_safe` | Yes, after repository inspection and contract bundle availability check |

## 2. Goal

Create the minimum repo, Airlock, source-manifest, Domain Map, traceability, and CI scaffolding needed to implement TB-000 cleanly.

This pack MUST NOT implement product behaviour. It only prepares the governance and application skeleton.

## 3. Governing sources

| Source | Role |
|---|---|
| `V42_A_to_Z_Locked_Setup_and_Ultimate_Goal_v1.2.md` | MVP-0 and first legal build sequence |
| `TB-000_Governance_Tracer_Bullet_v1.0.md` | Upcoming proof target |
| `CANON-1` and `contracts/manifest.json` | Current membership, pins, paths, and hashes |
| `CS-0@3.0.0` | Contract artifact schema authority |
| `BP-0@3.0.0` | Bundle authoring blueprint |
| `GOV-0` | Ash 3.x governance |
| `LINT-0` | Static governance lint posture |
| `CG-0` | Strict CI contract-gate expectations |

## 4. Scope

### 4.1 Must create or verify

- Workspace/repo skeleton exists.
- Phoenix/Ash application is named `Ticketing` with OTP app `:ticketing`.
- Basic directories exist for:
  - `contracts/raw_bundles/`
  - `contracts/baselines/`
  - `vault/Raw/`
  - `vault/Data/`
  - `vault/Compiled/`
  - `vault/Control/`
  - `vault/Indexes/`
  - `docs/atlas/`
  - `docs/domain_map/`
  - `docs/feature_packs/`
  - `tools/airlock/`
  - `tools/trace/`
  - `ci/`
- Python v2 Airlock scripts are installed or copied into `tools/airlock/` if provided.
- Minimal `source_manifest` placeholder exists and is machine-readable.
- Minimal `contract_register` placeholder exists and is machine-readable.
- Minimal `00_DOMAIN_MAP.md` skeleton exists with required matrix headings only.
- Minimal trace validator placeholder exists, but product rules are not implemented yet.
- Basic CI placeholders exist for static Airlock, lint, tests, and trace validation.

### 4.2 Must not create

- No order, payment, seat, ticket, refund, payout, scanner, ledger, pricing, subscription, notification, or external-provider resources.
- No product migrations.
- No product routes.
- No buyer/admin UX beyond skeleton health/runtime visibility.
- No production LightRAG.
- No autonomous agent harness.

## 5. Candidate files

Exact repo paths may differ. The agent must inspect first.

```text
README.md
mix.exs
config/*.exs
lib/ticketing/application.ex
lib/ticketing_web/*
contracts/raw_bundles/.gitkeep
contracts/baselines/.gitkeep
vault/Raw/.gitkeep
vault/Data/.gitkeep
vault/Compiled/.gitkeep
vault/Control/.gitkeep
vault/Indexes/.gitkeep
docs/domain_map/00_DOMAIN_MAP.md
docs/atlas/README.md
tools/airlock/README.md
tools/trace/README.md
tools/trace/trace_validator.exs or equivalent
ci/README.md
.github/workflows/airlock.yml or equivalent CI placeholder
```

## 6. Definitely required resources

None. This pack is scaffolding only.

## 7. Definitely required actions

None in product/domain terms.

Allowed setup commands:

```text
mix deps.get
mix compile
mix test
```

If Phoenix/Ash skeleton is not yet initialized, the agent may initialize the project only with explicit human confirmation or if this pack is being executed in an empty repo created for this platform.

## 8. DB / migrations

No product migrations. If the framework creates baseline repo metadata, the agent must list it explicitly.

## 9. Policies

No runtime authorization policies yet. Governance policy is fail-closed: missing source, missing contract, missing generated artifact, or missing trace metadata must be treated as a blocker.

## 10. Telemetry / observability

Only skeleton compile/test evidence is required. No product telemetry.

## 11. Acceptance tests

- Repo compiles.
- Test suite boots.
- No product modules exist under ticketing domain namespaces.
- `Ticketing` namespace is used.
- OTP app is `:ticketing`.
- Required scaffold directories exist.
- Domain Map skeleton includes required matrix headings.
- Trace validator placeholder returns an explicit `not_implemented` or `pending` state, not a fake pass.

## 12. Must-have gates

```text
SCAFFOLD-001: repo compiles
SCAFFOLD-002: OTP app is :ticketing
SCAFFOLD-003: root namespace is Ticketing
SCAFFOLD-004: no product modules created
SCAFFOLD-005: no product migrations created
SCAFFOLD-006: required scaffold directories exist
SCAFFOLD-007: Domain Map skeleton exists
SCAFFOLD-008: trace validator placeholder exists and fails/pends honestly
```

## 13. Definition of done

The pack is accepted only when the agent provides:

```text
- changed file list
- compile/test output
- scaffold directory verification
- confirmation that no product resources/workflows were introduced
- explicit next pack recommendation: FP-TB-000-governance-tracer-bullet
```

## 14. Remaining risks

- FR-1 is not yet indexed; `FR-MVP0-000` is a temporary planning handle.
- This pack depends on actual repo state. If a repo already exists, the agent must patch rather than recreate.
