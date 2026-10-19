# Evidence Checklist — FP-CI-002-migration-safety-baseline

## Identity

| Field | Value |
|---|---|
| order | `0030` |
| folder | `0030_CI-002_migration-safety-baseline` |
| feature_pack_id | `FP-CI-002-migration-safety-baseline` |
| class | `CI` |
| source row | `CI-002` |
| release phase | `foundation` |
| MVP blocker | `yes` |
| next folder | `TBD after Wave 0 execution evidence` |

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
