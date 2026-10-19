# Evidence Checklist — FP-CI-001-deterministic-uuid-binary-sort

## Identity

| Field | Value |
|---|---|
| order | `0020` |
| folder | `0020_CI-001_deterministic-uuid-binary-sort` |
| feature_pack_id | `FP-CI-001-deterministic-uuid-binary-sort` |
| class | `CI` |
| source row | `CI-001` |
| release phase | `foundation` |
| MVP blocker | `yes` |
| next folder | `0030_CI-002_migration-safety-baseline` |

## Required coding-agent evidence

The coding agent MUST report all of the following before the pack is accepted:

```text
- changed files
- tests run
- gates/checks run
- evidence produced
- unresolved blockers
- non-goals intentionally not touched
- confirmation that scope did not expand beyond this pack
```

## Acceptance rule

This folder is accepted only when `00_FEATURE_PLAN.md` and `01_CODING_AGENT_PROMPT.md` have both been satisfied and the evidence above is attached to the PR or implementation report.
