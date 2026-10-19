# Agent Handoff Rules — Wave 0


> Status: Draft implementation handoff pack.  
> Phase: Legislative Mode -> MVP-0 only.  
> Root namespace: `Ticketing`.  
> OTP app atom: `:ticketing`.  
> Ash posture: Ash 3.x only.  
> Product work: BLOCKED unless explicitly allowed by this pack.  
> Authority rule: contracts and gates win over this planning pack.


## Mandatory behaviour for every coding agent

1. Inspect the repository before editing.
2. Confirm current git branch and working tree status.
3. Read the relevant Feature Planning Pack and prompt.
4. Implement only the named pack scope.
5. Preserve `Ticketing` root namespace and `:ticketing` OTP app.
6. Use Ash 3.x only.
7. Do not add product resources or product workflows unless the pack explicitly allows them.
8. Do not call external providers.
9. Do not introduce direct `Repo` calls in governed flows unless explicitly allowed.
10. Do not add `V42.*`, `ORD.*`, `SEAT.*`, or contract-ID-prefixed module names.
11. Add tests/gates as required by the pack.
12. Produce an evidence summary at the end.

## Required final report from coding agent

```text
Pack implemented:
Changed files:
Tests added:
Tests run:
Gates run:
Evidence artifacts produced:
Known blockers:
Non-goals intentionally not touched:
Follow-up pack recommended:
```

## Stop conditions

The agent MUST stop and report a blocker if:

- a governing contract bundle is missing;
- a referenced gate is missing;
- repo layout differs materially from the pack assumptions;
- implementing the pack would require product behaviour;
- a migration would create tenant drift;
- a direct Repo call is needed in a governed flow;
- package/library versions contradict Ash 3.x posture;
- the pack conflicts with V42, CS-0, BP-0, GOV-0, LINT-0, TEN-1, or TB-000.
