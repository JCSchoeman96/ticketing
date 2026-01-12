.PHONY: contracts-check contracts-lint

contracts-check:
	python3 contracts/tools/ci_contract_gate_strict_v2.7.0.py contracts/bundles

contracts-lint:
	python3 contracts/tools/ci_ash_governance_lint_v1.2.0.py contracts/bundles
