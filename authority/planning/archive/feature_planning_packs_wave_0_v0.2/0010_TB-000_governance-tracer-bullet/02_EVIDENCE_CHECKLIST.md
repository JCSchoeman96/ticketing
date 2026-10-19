# Evidence Checklist — FP-TB-000-governance-tracer-bullet

## Identity

| Field | Value |
|---|---|
| order | `0010` |
| folder | `0010_TB-000_governance-tracer-bullet` |
| feature_pack_id | `FP-TB-000-governance-tracer-bullet` |
| class | `TB` |
| source row | `TB-000` |
| release phase | `foundation` |
| MVP blocker | `yes` |
| next folder | `0020_CI-001_deterministic-uuid-binary-sort` |

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
