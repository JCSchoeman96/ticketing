#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_db_psql.sh
# Purpose: Open psql shell into dev/test/postgres DB quickly.
# Usage:
#   scripts/dev/dev_db_psql.sh dev
#   scripts/dev/dev_db_psql.sh test
#   scripts/dev/dev_db_psql.sh postgres
# =========================

TARGET="${1:-dev}"

HOST_PORT="${POSTGRES_HOST_PORT:-5433}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASS="${POSTGRES_PASSWORD:-postgres}"

DEV_DB="${DEV_DB_NAME:-ticketing_dev}"
TEST_DB="${TEST_DB_NAME:-ticketing_test}"

case "${TARGET}" in
  dev) DB_NAME="${DEV_DB}" ;;
  test) DB_NAME="${TEST_DB}" ;;
  postgres) DB_NAME="postgres" ;;
  *)
    echo "[dev_db_psql] invalid target '${TARGET}'. Use: dev | test | postgres"
    exit 2
    ;;
esac

export PGPASSWORD="${DB_PASS}"
echo "[dev_db_psql] connecting to ${DB_NAME} on localhost:${HOST_PORT}..."
exec psql "postgresql://${DB_USER}@localhost:${HOST_PORT}/${DB_NAME}"
