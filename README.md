# Ticketing

This repository contains both canonical Ticketing authority and its implementation. The authority files live in `authority/`. The Phoenix application lives in `ticketing/`. Physical co-location does not change the authority hierarchy: the application remains downstream of CANON, canonical contracts, the ROADMAP, and its active tracer.

Read the repository governance in [AGENTS.md](AGENTS.md), authority-specific rules in [authority/AGENTS.md](authority/AGENTS.md), and application rules in [ticketing/AGENTS.md](ticketing/AGENTS.md). Import provenance and source validation evidence are recorded in [authority/provenance/import.json](authority/provenance/import.json).

## Local setup

From the repository root:

1. Install the runtimes listed in `.tool-versions` with `mise install` or `asdf install`.
2. Install authority validation dependencies:

   ```sh
   python3 -m pip install -r authority/requirements-release.txt pytest==9.1.1
   ```

3. Start PostgreSQL with `docker compose up -d db`. Compose publishes it on `localhost:5433`.
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
   mix precommit
   mix phx.server
   ```

`mix contract.authority` validates the in-repository authority. CANON's current version comes from `authority/contracts/manifest.json`; application source does not pin a moving CANON version.
