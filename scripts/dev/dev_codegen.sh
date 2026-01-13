#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_codegen.sh
# Purpose: Run Ash codegen after ensuring DB is reachable.
# =========================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/dev_db_up.sh" >/dev/null

echo "[dev_codegen] running ash.codegen..."
mix ash.codegen

echo "[dev_codegen] done."
