# Contracts

This repo is contract-first.

## Source of truth
- `contracts/bundles/` contains JSON-only contract bundles (`*_bundle_v*.zip`).
- Bundles are immutable artifacts. Update by regenerating a new bundle version.

## Tooling
- `make contracts-check` runs CI strict contract gate validation.
- `make contracts-lint` runs governance lint.

## Working area
- `contracts/working/` is for extracted bundles during audit/regeneration only.
- Do not treat `working/` as canonical.
