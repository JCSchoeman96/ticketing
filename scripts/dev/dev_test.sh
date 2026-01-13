#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_test.sh
# Purpose: Run tests with correct DB available.
# Flags:
#   --migrate   runs MIX_ENV=test migrations before test
# =========================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/dev_db_up.sh" >/dev/null

DO_MIGRATE="false"
if [[ "${1:-}" == "--migrate" ]]; then
  DO_MIGRATE="true"
fi

if [[ "${DO_MIGRATE}" == "true" ]]; then
  echo "[dev_test] running test migrations..."
  MIX_ENV=test mix ecto.create
  MIX_ENV=test mix ecto.migrate
fi

echo "[dev_test] running tests..."
exec mix test
