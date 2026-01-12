.RECIPEPREFIX := >
.PHONY: help contracts-check contracts-check-core contracts-check-optional contracts-check-all suite-all-clean clean

PY ?= python3
CI_GATE ?= contracts/tools/ci_contract_gate_strict_v2.7.0.py

# Keep "core" green by default
CONTRACTS_CORE_DIR ?= contracts/bundles_core
CONTRACTS_OPTIONAL_DIR ?= contracts/bundles_optional

# Default suite dir
CONTRACTS_DIR ?= $(CONTRACTS_CORE_DIR)

CANON_ZIP ?= $(CONTRACTS_CORE_DIR)/CANON-1_bundle_v0.9.41_JSON_ONLY.zip
CS_ZIP ?= $(CONTRACTS_CORE_DIR)/CS-0_bundle_v2.2.0_JSON_ONLY.zip

SUITE_ALL_DIR ?= .suite/all

help:
>@echo "Targets:"
>@echo "  make contracts-check-core      # Validate core suite only (should stay green)"
>@echo "  make contracts-check-optional  # Validate optional dir only (may fail until deps exist)"
>@echo "  make contracts-check-all       # Validate core+optional combined via symlink suite"
>@echo "  make suite-all-clean           # Remove combined suite dir"

contracts-check:
>$(PY) $(CI_GATE) \
>  --root "." \
>  --contracts-dir "$(CONTRACTS_DIR)" \
>  --canon "$(CANON_ZIP)" \
>  --cs "$(CS_ZIP)"

contracts-check-core:
>$(MAKE) contracts-check CONTRACTS_DIR=$(CONTRACTS_CORE_DIR)

contracts-check-optional:
>$(MAKE) contracts-check CONTRACTS_DIR=$(CONTRACTS_OPTIONAL_DIR)

# Build a combined suite dir with symlinks to both core + optional
$(SUITE_ALL_DIR):
>mkdir -p "$(SUITE_ALL_DIR)"
>for f in $(CONTRACTS_CORE_DIR)/*.zip; do ln -sfn "../../$$f" "$(SUITE_ALL_DIR)/$$(basename $$f)"; done
>for f in $(CONTRACTS_OPTIONAL_DIR)/*.zip; do ln -sfn "../../$$f" "$(SUITE_ALL_DIR)/$$(basename $$f)"; done

contracts-check-all: $(SUITE_ALL_DIR)
>$(MAKE) contracts-check CONTRACTS_DIR=$(SUITE_ALL_DIR)

suite-all-clean:
>rm -rf "$(SUITE_ALL_DIR)"

clean: suite-all-clean
