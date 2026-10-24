#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
installer="$repo_root/scripts/ci/ensure-tailwind-binary.sh"
workflow="$repo_root/.github/workflows/ci.yml"
expected_url='https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-linux-x64'
expected_sha256='dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a'

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

[[ -f "$installer" ]] || fail "Tailwind acquisition helper is missing"
[[ -f "$workflow" ]] || fail "CI workflow is missing"

grep -Fq "$expected_url" "$installer" || fail "Tailwind v4.3.3 URL is not pinned"
grep -Fq "$expected_sha256" "$installer" || fail "Tailwind SHA-256 is not pinned"
if grep -Eiq 'latest|tailwindcss/releases/latest' "$installer"; then
  fail "Tailwind acquisition must not resolve a moving latest version"
fi

test_line="$(grep -nF 'test-tailwind-acquisition.sh' "$workflow" | head -n 1 | cut -d: -f1 || true)"
helper_line="$(grep -nF 'ensure-tailwind-binary.sh' "$workflow" | head -n 1 | cut -d: -f1 || true)"
setup_line="$(grep -nE 'run: mix setup$' "$workflow" | head -n 1 | cut -d: -f1 || true)"
[[ -n "$test_line" && -n "$helper_line" && -n "$setup_line" ]] || fail "CI must test and acquire Tailwind before mix setup"
((test_line < helper_line && helper_line < setup_line)) || fail "Tailwind checks and acquisition must precede mix setup"
grep -Fq "readonly tailwind_relative_path='ticketing/_build/tailwind-linux-x64-4.3.3'" "$installer" ||
  fail "Tailwind destination path is not pinned to the wrapper's expected path"

test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT
fake_bin="$test_root/fake-bin"
mkdir -p "$fake_bin"

cat > "$fake_bin/curl" <<'CURL'
#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$@" > "$CURL_ARGS_LOG"
output=''
while (($#)); do
  if [[ "$1" == '--output' ]]; then
    shift
    output="${1:-}"
  fi
  shift
done

[[ -n "$output" ]] || exit 64
case "$CURL_MODE" in
  checksum-mismatch)
    printf '#!/usr/bin/env bash\nprintf executed > "%s"\n' "$CURL_EXEC_MARKER" > "$output"
    ;;
  partial-download)
    printf '#!/usr/bin/env bash\nprintf executed > "%s"\n' "$CURL_EXEC_MARKER" > "$output"
    exit 23
    ;;
  *)
    exit 64
    ;;
esac
CURL

cat > "$fake_bin/chmod" <<'CHMOD'
#!/usr/bin/env bash
set -euo pipefail
printf 'called\n' > "$CHMOD_MARKER"
CHMOD

chmod 0755 "$fake_bin/curl" "$fake_bin/chmod"

check_failed_download() {
  local mode="$1"
  local case_root="$test_root/$mode"
  local args_log="$test_root/$mode.curl-args"
  local chmod_marker="$test_root/$mode.chmod-called"
  local exec_marker="$test_root/$mode.binary-executed"
  local error_log="$test_root/$mode.stderr"
  local exit_code=0
  local destination="$case_root/ticketing/_build/tailwind-linux-x64-4.3.3"
  local previous_target="$test_root/$mode.previous-target"

  mkdir -p "$case_root/ticketing"
  if [[ "$mode" == 'checksum-mismatch' ]]; then
    mkdir -p "$(dirname "$destination")"
    printf 'previous verified binary sentinel\n' > "$previous_target"
    cp "$previous_target" "$destination"
  fi
  if PATH="$fake_bin:$PATH" \
    CURL_MODE="$mode" \
    CURL_ARGS_LOG="$args_log" \
    CHMOD_MARKER="$chmod_marker" \
    CURL_EXEC_MARKER="$exec_marker" \
    bash "$installer" "$case_root" > /dev/null 2> "$error_log"; then
    fail "$mode unexpectedly succeeded"
  else
    exit_code=$?
  fi

  ((exit_code != 0)) || fail "$mode did not propagate a failure"
  [[ ! -e "$exec_marker" ]] || fail "$mode executed the unverified download"
  if [[ "$mode" == 'checksum-mismatch' ]]; then
    cmp -s "$previous_target" "$destination" || fail "checksum mismatch changed the prior installed binary"
  else
    [[ ! -e "$destination" ]] || fail "$mode left an installable Tailwind binary"
  fi
  [[ ! -e "$chmod_marker" ]] || fail "$mode reached chmod before verification"
  if compgen -G "$case_root/ticketing/_build/.tailwind-linux-x64-4.3.3.tmp.*" > /dev/null; then
    fail "$mode left a temporary download behind"
  fi

  for required_arg in \
    '--fail' '--location' '--proto' '=https' '--proto-redir' \
    '--retry' '3' '--retry-all-errors' '--connect-timeout' '10' \
    '--max-time' '180' '--remove-on-error' '--output' "$expected_url"; do
    grep -Fxq -- "$required_arg" "$args_log" || fail "curl is missing required option $required_arg"
  done

  if grep -Fxq -- '-k' "$args_log" || grep -Fxq -- '--insecure' "$args_log"; then
    fail "curl TLS verification must remain enabled"
  fi

  if [[ "$mode" == 'checksum-mismatch' ]]; then
    grep -Fq 'checksum mismatch' "$error_log" || fail "checksum mismatch did not produce a clear failure"
  fi
}

check_failed_download checksum-mismatch
printf 'PASS: checksum mismatch fails before chmod or installation\n'
check_failed_download partial-download
printf 'PASS: partial downloader failure propagates and is cleaned up\n'
