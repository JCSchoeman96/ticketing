#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_db_init.sh
# Purpose: Ensure expected dev/test databases exist (idempotent).
# =========================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/dev_db_up.sh" >/dev/null

HOST_PORT="${POSTGRES_HOST_PORT:-5433}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASS="${POSTGRES_PASSWORD:-postgres}"

DEV_DB="${DEV_DB_NAME:-ticketing_dev}"
TEST_DB="${TEST_DB_NAME:-ticketing_test}"

export PGPASSWORD="${DB_PASS}"

echo "[dev_db_init] ensuring databases exist: ${DEV_DB}, ${TEST_DB}"

psql "postgresql://${DB_USER}@localhost:${HOST_PORT}/postgres" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${DEV_DB}') THEN
    CREATE DATABASE ${DEV_DB};
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${TEST_DB}') THEN
    CREATE DATABASE ${TEST_DB};
  END IF;
END
\$\$;
SQL

echo "[dev_db_init] done."
