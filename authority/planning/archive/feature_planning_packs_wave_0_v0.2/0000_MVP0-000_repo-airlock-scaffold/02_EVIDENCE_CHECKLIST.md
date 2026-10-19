# Evidence Checklist — FP-MVP0-000-repo-airlock-scaffold

## Identity

| Field | Value |
|---|---|
| order | `0000` |
| folder | `0000_MVP0-000_repo-airlock-scaffold` |
| feature_pack_id | `FP-MVP0-000-repo-airlock-scaffold` |
| class | `MVP0` |
| source row | `A-to-Z §17 / §29, TB-000 preconditions` |
| release phase | `foundation` |
| MVP blocker | `yes` |
| next folder | `0010_TB-000_governance-tracer-bullet` |

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
