#!/usr/bin/env bash
set -euo pipefail

# =========================
# dev_format.sh
# Purpose: Run formatter + verify compilation.
# =========================

echo "[dev_format] mix format..."
mix format

echo "[dev_format] compile..."
mix compile --warnings-as-errors
echo "[dev_format] done."
