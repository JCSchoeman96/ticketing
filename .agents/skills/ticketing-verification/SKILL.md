---
name: ticketing-verification
description: Use before handing repository-changing Ticketing implementation to PR review. Verify the exact scope, generated outputs, dependencies, required checks, branch, and open PR.
---

# Ticketing verification workflow

Use this checklist with root `AGENTS.md`, the effective scoped `AGENTS.md`, `planning/WORKFLOW.md`, the current approved JIP/spec when applicable, and the assigned Plane item. Report `READY FOR REVIEW` or `NOT READY`. Never report `READY TO MERGE`; independent review and current CI own that decision.

## Review the worktree and scope

- Record `git status --short`, the base SHA, and the current head SHA.
- Review the exact final diff and list every changed file.
- Compare the diff with the Plane item and, when applicable, its JIP scope, non-goals, and locked decisions.
- Confirm `Documentation Impact` and update only its specified paths. If it is `UNAFFECTED`, verify that no implementation documentation changed.
- Review `mix.exs` and the exact `mix.lock` diff. Explain every added, removed, upgraded, or downgraded dependency. Reject unexplained resolver changes.
- Review all migrations and generated files. Confirm generated UsageRules skills are under repo-root `.agents/skills/`, and human-maintained Ticketing skills remain intact after sync.
- Check for temporary files, debug output, credentials, and user-specific MCP configuration.
- Verify material API assumptions against authoritative docs for the installed dependency versions.

## Run required verification

From `ticketing/`, run and record the applicable gates. `mix precommit` is the fast everyday gate, `mix check` is the full non-Dialyzer gate, and `mix check.types` is the dedicated Dialyzer gate.

```sh
mix deps.get
mix format --check-formatted
mix compile --warnings-as-errors
MIX_ENV=dev mix usage_rules.list
MIX_ENV=dev mix usage_rules.sync
MIX_ENV=dev mix usage_rules.sync --check
mix precommit
mix check
mix check.types
mix contract.authority
mix ash.codegen --check
git diff --check
```

`mix usage_rules.sync` writes generated output. Review its changes, then run `mix usage_rules.sync --check` to prove a fresh sync has no drift. Igniter's supported `--check` mode exits nonzero when generated changes are pending and halts before writing files; `mix check` uses this mode so verification never silently rewrites tracked output. The alias runs this drift check under DEV because the generated Phoenix skill includes the DEV-only `phoenix_live_reload` rules; format, compile, and tests run under TEST.

For Tidewave changes, verify the DEV endpoint is loopback-only, Tidewave is dev-only, and the MCP endpoint uses the same port as Phoenix. Check the default `4200` port and an explicit worktree port from `4201–4219`. Confirm Ticketing does not bind port `4000` and production configuration does not enable Tidewave or change.

## Prepare the review handoff

- Push the implementation branch and open a PR against current `main`.
- Link the PR to the assigned Plane item and, when applicable, its actual parent JIP. Include the current approved JIP and accepted spec, when applicable, in the handoff. Do not assume a fixed JIP identifier.
- Verify the PR base and head SHA, exact changed-file list, assigned Plane item, and governing JIP/spec when applicable, plus dependency and lock changes, checks, warnings, deferrals, and blockers.
- Hand the exact PR head and fresh CI evidence to ChatGPT acting as the independent control tower. Leave the PR open. A control-tower `PASS` is not merge authorization; merge only after explicit user authorization.

Return `READY FOR REVIEW` only when the branch is pushed, the PR is open, all applicable checks pass, and the handoff includes the required evidence. Otherwise return `NOT READY` with the failed checks or blockers.
