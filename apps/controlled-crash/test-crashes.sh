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
    echo "失败：编号 $how 的 JVM 意外成功返回" >&2
    failed=1
  else
    status=$?
    after=$(find "$log_dir" -maxdepth 1 -name 'hs_err_pid*.log' -type f 2>/dev/null | wc -l | tr -d ' ')
    if [[ $after -gt $before ]]; then
      echo "通过：编号 $how 已终止子 JVM（shell 状态码 $status）"
    else
      echo "失败：编号 $how 失败，但未生成 hs_err" >&2
      failed=1
    fi
  fi
done

echo "崩溃日志：${LOG_DIR:-$APP_DIR/crash-logs}"
exit "$failed"
