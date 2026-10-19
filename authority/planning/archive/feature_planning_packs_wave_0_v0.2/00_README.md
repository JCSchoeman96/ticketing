# Feature Planning Packs — Wave 0 v0.2

This bundle reorganizes Wave 0 so each Feature Planning Pack lives in its own chronological numbered folder.

## Folder naming rule

```text
<ORDER>_<CLASS-OR-SOURCE-ID>_<short-slug>/
```

Examples:

```text
0000_MVP0-000_repo-airlock-scaffold/
0010_TB-000_governance-tracer-bullet/
0020_CI-001_deterministic-uuid-binary-sort/
0030_CI-002_migration-safety-baseline/
```

The numeric prefix is the chronological implementation order. The class/source ID is descriptive only. This allows the real sequence to mix MVP, TB, CI, VS, PP, and OPS items without relying on alphabetical order or ID-prefix assumptions.

The sequence uses gaps of 10 so future packs can be inserted without renumbering every existing folder. For example, a new pack between `0010` and `0020` can use `0015_...`.

## Standard files inside every pack folder

```text
00_FEATURE_PLAN.md
01_CODING_AGENT_PROMPT.md
02_EVIDENCE_CHECKLIST.md
pack.json
```

## Shared files

```text
_shared/AGENT_HANDOFF_RULES.md
```

## Current Wave 0 order

| Order | Folder | Pack | Class |
|---:|---|---|---|
| 0000 | `0000_MVP0-000_repo-airlock-scaffold` | `FP-MVP0-000-repo-airlock-scaffold` | MVP0 |
| 0010 | `0010_TB-000_governance-tracer-bullet` | `FP-TB-000-governance-tracer-bullet` | TB |
| 0020 | `0020_CI-001_deterministic-uuid-binary-sort` | `FP-CI-001-deterministic-uuid-binary-sort` | CI |
| 0030 | `0030_CI-002_migration-safety-baseline` | `FP-CI-002-migration-safety-baseline` | CI |

## Important use rule

Give a coding agent exactly one numbered pack folder at a time, plus the shared handoff rules. Do not give the full CAI or full slice catalogue as an implementation instruction. Those are planning and authority-navigation inputs, not direct coding instructions.
