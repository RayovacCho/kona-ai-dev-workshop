#!/usr/bin/env bash
set -uo pipefail

APP_DIR=$(cd "$(dirname "$0")" && pwd)
CASES=(1 2 14 15 16 17 99)
log_dir=${LOG_DIR:-$APP_DIR/crash-logs}
snapshot_dir=$(mktemp -d "${TMPDIR:-/tmp}/controlled-crash-test.XXXXXX")
trap 'rm -rf "$snapshot_dir"' EXIT
failed=0

mkdir -p "$log_dir"

snapshot_logs() {
  find "$log_dir" -maxdepth 1 -name 'hs_err_pid*.log' -type f -print | LC_ALL=C sort
}

expected_pattern() {
  case "$1" in
    1) echo 'assert\(how == 0\) failed: test assert' ;;
    2) echo 'guarantee\(how == 0\) failed: test guarantee' ;;
    14) echo 'SIGSEGV|EXCEPTION_ACCESS_VIOLATION' ;;
    15) echo 'SIGFPE|EXCEPTION_INT_DIVIDE_BY_ZERO' ;;
    16) echo 'Force crash with an active ThreadsListHandle' ;;
    17) echo 'Force crash with a nested ThreadsListHandle' ;;
    99) echo 'Crashing with number 99' ;;
  esac
}

for how in "${CASES[@]}"; do
  echo "=== controlledCrash($how) ==="
  before="$snapshot_dir/before-$how"
  after="$snapshot_dir/after-$how"
  snapshot_logs > "$before"
  if "$APP_DIR/run-crash.sh" "$how"; then
    echo "失败：编号 $how 的 JVM 意外成功返回" >&2
    failed=1
  else
    status=$?
    snapshot_logs > "$after"
    new_logs=$(comm -13 "$before" "$after")
    new_count=$(printf '%s\n' "$new_logs" | sed '/^$/d' | wc -l | tr -d ' ')
    if [[ $new_count -ne 1 ]]; then
      echo "失败：编号 $how 应生成一份 hs_err，实际生成 $new_count 份" >&2
      failed=1
      continue
    fi
    new_log=$new_logs
    if ! grep -Eq "$(expected_pattern "$how")" "$new_log" ||
       ! grep -q 'WhiteBox.controlledCrash' "$new_log" ||
       ! grep -q 'WB_ControlledCrash' "$new_log"; then
      echo "失败：编号 $how 的 hs_err 内容与预期不符：$new_log" >&2
      failed=1
      continue
    fi
    echo "通过：编号 $how 已终止子 JVM 并生成匹配的 hs_err（shell 状态码 ${status}）"
  fi
done

echo "崩溃日志：$log_dir"
exit "$failed"
