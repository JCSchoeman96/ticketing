# Ticketing canonical authority

`authority/` contains Ticketing's canonical contracts, CANON, release provenance, planning, tracers, and validation and release tools. The Phoenix/Ash implementation lives in `ticketing/` and remains downstream of this authority.

CANON selects the suite. `contracts/manifest.json` records its physical inventory, hashes, membership, and ZIP/extract mapping. The manifest does not select semantics. The exact release ZIP under `contracts/<DOC-ID>/<DOC-ID>_bundle_v<VERSION>.zip` is immutable; a semantic correction requires a successor version.

`provenance/import.json` records the source commits, source-tree identities, and import checks. The import keeps current release artifacts and release-authoring inputs. It does not copy the source repository's earlier Git history.

`authority-staging/` is retained because current T0 validation gates use those files as candidate fixtures. They remain noncanonical and do not select product semantics.

The original `governance/` documents are preserved as historical/supporting references. Some describe the former multi-repository layout; current repository responsibilities come from the root and nested `AGENTS.md` files.

## Validate from the repository root

Install the authority test dependencies and run the full authority checks:

```bash
python3 -m pip install -r authority/requirements-release.txt pytest==9.1.1
PYTHONPATH=authority python3 -m pytest -q authority/tests
python3 authority/tools/contract_manifest.py verify --root authority
python3 authority/tools/generate_canon.py verify --root authority
python3 authority/tools/reconcile_contracts.py audit --canonical --strict --root authority \
  --json-output /tmp/ticketing-authority-audit.json \
  --markdown-output /tmp/ticketing-authority-audit.md
```

The root `.github/workflows/authority.yml` runs these checks when authority files or their validation configuration change. `mix contract.authority` runs the manifest, CANON, and strict audit checks from the application.

## Create a successor release

Run the release-authoring commands from `authority/`; the paths below are relative to that directory.

1. Prepare successor source under `release-src/current/<DOC-ID>/<VERSION>/`. For a legacy release without editable source, bootstrap from its exact active ZIP and record its ZIP hash, byte count, and member hashes in `provenance.json`.
2. Build the source twice into separate temporary directories:

   ```bash
   python tools/build_contract_release.py --source release-src/current/<DOC-ID>/<VERSION>/ --output /tmp/build-one --allow-candidate
   python tools/build_contract_release.py --source release-src/current/<DOC-ID>/<VERSION>/ --output /tmp/build-two --allow-candidate
   ```

3. Compare both ZIPs, manifests, contract artifacts, and paired test gates. Validate the candidate and its dependency set:

   ```bash
   python tools/validate_contract_release.py /tmp/build-one/<DOC-ID>_bundle_v<VERSION>.zip
   python tools/validate_release_set.py --candidate /tmp/build-one/<DOC-ID>_bundle_v<VERSION>.zip --root .
   ```

4. When a CANON pin changes, generate its successor from the current CANON and manifest plus explicit candidate ZIPs:

   ```bash
   python tools/generate_canon.py successor \
     --root . \
     --candidate /tmp/build-one/<DOC-ID>_bundle_v<VERSION>.zip \
     --version <NEXT-CANON-VERSION> \
     --output-dir release-src/current/CANON-1/<NEXT-CANON-VERSION> \
     --generated-at-utc <UTC-TIMESTAMP>
   ```

   The generator preserves current membership, validates each candidate, checks dependency closure, and records hashes for the base CANON, active manifest, closure input, and candidates in `resolved-selection.json` and `generation-provenance.json`.
5. Build CANON twice and compare its ZIP, manifest, contract, and test-gates bytes. Validate the contract candidate and CANON candidate.
6. Install each accepted release ZIP and its matching CANON ZIP together. Regenerate extracted copies with `python tools/contract_manifest.py extract <DOC-ID> --root .`, then regenerate `contracts/manifest.json` with `python tools/contract_manifest.py generate --root .`.
7. Run the authority tests, manifest verification, CANON verification, strict audit, and CI checks before publishing the authority change.
