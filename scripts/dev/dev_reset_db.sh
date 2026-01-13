#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_reset_db.sh
# Purpose: Safely reset dev/test DB using Ecto tasks.
# WARNING: This DROPS local databases.
# =========================

echo "⚠️  This will DROP and RECREATE local databases for this repo:"
echo "   - dev (mix ecto.drop/create/migrate)"
echo "   - test (MIX_ENV=test mix ecto.drop/create/migrate)"
echo ""
read -r -p "Type RESET to continue: " CONFIRM

if [[ "${CONFIRM}" != "RESET" ]]; then
  echo "[dev_reset_db] cancelled."
  exit 0
fi

echo "[dev_reset_db] ensuring DB container is running..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/dev_db_up.sh" >/dev/null

echo "[dev_reset_db] resetting dev DB..."
mix ecto.drop
mix ecto.create
mix ecto.migrate

echo "[dev_reset_db] resetting test DB..."
MIX_ENV=test mix ecto.drop
MIX_ENV=test mix ecto.create
MIX_ENV=test mix ecto.migrate

echo "[dev_reset_db] running ash codegen..."
mix ash.codegen

echo "[dev_reset_db] done."
