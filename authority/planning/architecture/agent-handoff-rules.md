# Agent handoff rules

Before editing:

- Inspect the repository, current branch, and worktree.
- Find the current governing contracts and gates for the requested behavior.
- Treat current canonical contracts as authority. Report any unresolved conflict instead of resolving it by assumption.

While editing:

- Carry `org_id` and the authorized actor explicitly through governed actions.
- Use governed domain actions for domain state changes. Do not bypass them with direct persistence calls unless current authority allows it.
- Keep tests tied to observable behavior and the real application boundary where that boundary carries the risk.
- Do not weaken or remove a test just to make CI green.
- Preserve evidence for meaningful behavior, including relevant test results and known limits.

At handoff, report changed files, checks run, evidence, and unresolved authority questions. Do not maintain archived pack manifests, indexes, pointers, or sequencing.
