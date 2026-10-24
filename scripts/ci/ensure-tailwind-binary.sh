#!/usr/bin/env bash
set -euo pipefail

readonly tailwind_version='4.3.3'
readonly tailwind_target='linux-x64'
readonly tailwind_sha256='dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a'
readonly tailwind_url='https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-linux-x64'
readonly tailwind_relative_path='ticketing/_build/tailwind-linux-x64-4.3.3'

if (($# > 1)); then
  printf 'Usage: %s [repository-root]\n' "$0" >&2
  exit 64
fi

repo_root="$(cd "${1:-.}" && pwd)"
destination="$repo_root/$tailwind_relative_path"
destination_dir="$(dirname "$destination")"
mkdir -p "$destination_dir"

temporary_file="$(mktemp "$destination_dir/.tailwind-${tailwind_target}-${tailwind_version}.tmp.XXXXXX")"
cleanup() {
  rm -f -- "$temporary_file"
}
trap cleanup EXIT

curl \
  --fail \
  --location \
  --proto '=https' \
  --proto-redir '=https' \
  --retry 3 \
  --retry-all-errors \
  --retry-delay 2 \
  --retry-max-time 300 \
  --connect-timeout 10 \
  --max-time 180 \
  --remove-on-error \
  --silent \
  --show-error \
  --output "$temporary_file" \
  "$tailwind_url"

if ! printf '%s  %s\n' "$tailwind_sha256" "$temporary_file" | sha256sum --check --status; then
  printf 'Tailwind v%s checksum mismatch; refusing to install\n' "$tailwind_version" >&2
  exit 1
fi

chmod 0755 "$temporary_file"
mv -f -- "$temporary_file" "$destination"
trap - EXIT

printf 'Verified Tailwind v%s at %s\n' "$tailwind_version" "${destination#"$repo_root"/}"
