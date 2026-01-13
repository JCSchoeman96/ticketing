#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_migrate.sh
# Purpose: Run dev migrations (idempotent).
# =========================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/dev_db_up.sh" >/dev/null

echo "[dev_migrate] ecto.create..."
mix ecto.create

echo "[dev_migrate] ecto.migrate..."
mix ecto.migrate

echo "[dev_migrate] done."
