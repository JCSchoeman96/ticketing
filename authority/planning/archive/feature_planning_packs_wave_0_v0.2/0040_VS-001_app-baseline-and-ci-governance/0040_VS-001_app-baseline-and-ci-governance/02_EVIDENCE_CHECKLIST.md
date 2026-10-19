# Evidence Checklist — FP-VS-001-app-baseline-and-ci-governance

## Identity

| Field | Value |
|---|---|
| order | `0040` |
| folder | `0040_VS-001_app-baseline-and-ci-governance` |
| feature_pack_id | `FP-VS-001-app-baseline-and-ci-governance` |
| class | `VS` |
| source row | `VS-001` |
| release phase | `foundation` |
| MVP blocker | `yes` |
| next folder | `0050_TB-001_tenant-context-rls-denial` |

## Required coding-agent evidence

The coding agent MUST report all of the following before the pack is accepted:

```text
- changed files
- commands added or preserved
- tests added
- tests run
- gates/checks run
- evidence report path
- pass/fail/pending status per gate
- unresolved blockers
- non-goals intentionally not touched
- confirmation that no product resources were introduced
- confirmation that root namespace remains Ticketing
- confirmation that OTP app atom remains :ticketing
- confirmation that no V42.* module prefix was introduced
```

## Minimum acceptance evidence

```text
- mix compile evidence
- mix test evidence
- mix check or equivalent evidence
- governance lint command/wrapper evidence or pending blocker
- contract strict gate command/wrapper evidence or pending blocker
- migration safety command/wrapper evidence or pending blocker
- UUID binary sort command/wrapper evidence or pending blocker
- reports/foundation/vs_001_foundation_report.md
```

## Rejection conditions

Reject this pack if the implementation:

```text
- creates product domain resources
- creates login/registration/org-switching flows
- creates order/payment/seat/ticket/refund/payout/scanning code
- silently skips governance gates
- claims CI success without evidence
- introduces V42.* module prefixes
- weakens Ticketing/:ticketing naming
```

## Acceptance rule

This folder is accepted only when `00_FEATURE_PLAN.md` and `01_CODING_AGENT_PROMPT.md` have both been satisfied and the evidence above is attached to the PR or implementation report.
