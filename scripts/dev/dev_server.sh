#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_server.sh
# Purpose: Start Phoenix server after ensuring DB is reachable.
# =========================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/dev_db_up.sh" >/dev/null

echo "[dev_server] starting Phoenix..."
exec mix phx.server
