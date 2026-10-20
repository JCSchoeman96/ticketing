# Ticketing

This repository contains both canonical Ticketing authority and its implementation. The authority files live in `authority/`. The Phoenix application lives in `ticketing/`. Physical co-location does not change the authority hierarchy: the application remains downstream of CANON, canonical contracts, the ROADMAP, and its active tracer.

Read the repository governance in [AGENTS.md](AGENTS.md), authority-specific rules in [authority/AGENTS.md](authority/AGENTS.md), and application rules in [ticketing/AGENTS.md](ticketing/AGENTS.md). Import provenance and source validation evidence are recorded in [authority/provenance/import.json](authority/provenance/import.json).

## Local setup

Ticketing DEV and TEST use the workstation-owned `dev-core` PostgreSQL allocation. The repository does not run local PostgreSQL or Redis services.

1. Install the runtimes listed in `.tool-versions` with `mise install` or `asdf install`.
2. Install authority validation dependencies:

   ```sh
   python3 -m pip install -r authority/requirements-release.txt pytest==9.1.1
   ```

3. Confirm the workstation `dev-core` allocation is provisioned. From the repository root, render and check its ignored environment:

   ```sh
   devcore-project render
   devcore-project doctor
   direnv allow
   ```

   The root `.envrc` loads the ignored `.envrc.private`. Without direnv, source `.envrc.private` from the repository root.

4. Run authority checks:

   ```sh
   PYTHONPATH=authority python3 -m pytest -q authority/tests
   python3 authority/tools/contract_manifest.py verify --root authority
   python3 authority/tools/generate_canon.py verify --root authority
   python3 authority/tools/reconcile_contracts.py audit --canonical --strict --root authority \
     --json-output /tmp/ticketing-authority-audit.json \
     --markdown-output /tmp/ticketing-authority-audit.md
   ```

5. Run application commands from `ticketing/`:

   ```sh
   cd ticketing
   mix setup
   mix contract.authority
   mix ash.codegen --check
   mix precommit
   mix phx.server
   ```

`mix setup` fetches dependencies, migrates the already-provisioned DEV database, runs seeds, and builds assets. It does not create the database. CANON's current version comes from `authority/contracts/manifest.json`; application source does not pin a moving CANON version.

Local ports:

| Purpose | Host and port | Database |
| --- | --- | --- |
| DEV | `127.0.0.1:55432` | `ticketing_dev` |
| TEST | `127.0.0.1:55433` | `ticketing_test` plus `MIX_TEST_PARTITION` |
| Ticketing HTTP | `127.0.0.1:4200` | Phoenix and Tidewave |
| Worktree HTTP | `127.0.0.1:4201` to `4219` | Use one available port per worktree |

Redis is N/A for Ticketing. Do not start a repository-local database or Redis service for application development.
