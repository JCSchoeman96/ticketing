.PHONY: contracts-check contracts-lint contracts-manifest

# Root that contains your bundle zips
CONTRACTS_ROOT := contracts/bundles

# These will be set after extraction (we’ll fill them in once we see the filenames)
CANON_JSON := contracts/bundles/CANON-1_bundle_v0.9.41_JSON_ONLY.zip
CS_JSON := contracts/bundles/CS-0_bundle_v2.2.0_JSON_ONLY.zip
LINT_RULES_JSON := contracts/suite/LINT-0/LINT-0_bundle_v2.0.11/LINT-0_Contract_v2.0.11.json

contracts-check:
	python3 contracts/tools/ci_contract_gate_strict_v2.7.0.py \
		--root "$(CONTRACTS_ROOT)" \
		--canon "$(CANON_JSON)" \
		--cs "$(CS_JSON)"

contracts-lint:
	python3 contracts/tools/ci_ash_governance_lint_v1.2.0.py \
		--root "$(CONTRACTS_ROOT)" \
		--rules "$(LINT_RULES_JSON)"

contracts-manifest:
	python3 contracts/tools/tools_regen_bundle_manifest_v1.0.0.py "$(CONTRACTS_ROOT)"
