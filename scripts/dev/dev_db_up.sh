#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_db_up.sh
# Purpose: Ensure dev Postgres container is running and reachable.
# =========================

CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-dev-postgres}"
HOST_PORT="${POSTGRES_HOST_PORT:-5433}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASS="${POSTGRES_PASSWORD:-postgres}"
DB_DEFAULT="${POSTGRES_DEFAULT_DB:-postgres}"
IMAGE="${POSTGRES_IMAGE:-postgres:18-alpine}"

echo "[dev_db_up] container=${CONTAINER_NAME} host_port=${HOST_PORT}"

if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  echo "[dev_db_up] ${CONTAINER_NAME} already running."
else
  if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    echo "[dev_db_up] starting existing container..."
    docker start "${CONTAINER_NAME}" >/dev/null
  else
    echo "[dev_db_up] creating + starting new container..."
    docker run -d \
      --name "${CONTAINER_NAME}" \
      -e POSTGRES_PASSWORD="${DB_PASS}" \
      -p "${HOST_PORT}:5432" \
      -v "${CONTAINER_NAME}-data:/var/lib/postgresql/data" \
      "${IMAGE}" >/dev/null
  fi
fi

# Verify connectivity
export PGPASSWORD="${DB_PASS}"
psql "postgresql://${DB_USER}@localhost:${HOST_PORT}/${DB_DEFAULT}" -c "SELECT 1;" >/dev/null
echo "[dev_db_up] DB ok."
