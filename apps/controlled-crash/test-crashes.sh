#!/usr/bin/env bash
set -uo pipefail

APP_DIR=$(cd "$(dirname "$0")" && pwd)
CASES=(1 2 14 15 16 17 99)
failed=0

for how in "${CASES[@]}"; do
  echo "=== controlledCrash($how) ==="
  log_dir=${LOG_DIR:-$APP_DIR/crash-logs}
  before=$(find "$log_dir" -maxdepth 1 -name 'hs_err_pid*.log' -type f 2>/dev/null | wc -l | tr -d ' ')
  if "$APP_DIR/run-crash.sh" "$how"; then
    echo "FAIL: JVM returned success for case $how" >&2
    failed=1
  else
    status=$?
    after=$(find "$log_dir" -maxdepth 1 -name 'hs_err_pid*.log' -type f 2>/dev/null | wc -l | tr -d ' ')
    if [[ $after -gt $before ]]; then
      echo "PASS: case $how terminated the child JVM (shell status $status)"
    else
      echo "FAIL: case $how failed without producing hs_err" >&2
      failed=1
    fi
  fi
done

echo "Crash logs: ${LOG_DIR:-$APP_DIR/crash-logs}"
exit "$failed"
