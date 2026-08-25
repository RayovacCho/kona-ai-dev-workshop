#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "用法：KONA_SRC=/path KONA_HOME=/path $0 <输出文件>" >&2
  exit 2
fi
: "${KONA_SRC:?请设置 KONA_SRC}"
: "${KONA_HOME:?请设置 KONA_HOME}"

output=$1
script_dir=$(cd "$(dirname "$0")" && pwd)
workshop_root=$(cd "$script_dir/.." && pwd)
mkdir -p "$(dirname "$output")"

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

if [[ -n "$(git -C "$KONA_SRC" status --porcelain)" ]]; then
  echo "拒绝记录含未提交修改的 Kona 工作树" >&2
  exit 2
fi

os_name=$(uname -s)
os_version=$(uname -r)
if command -v sw_vers >/dev/null 2>&1; then
  os_name=$(sw_vers -productName)
  os_version=$(sw_vers -productVersion)
fi

cpu=unknown
memory=unknown
if [[ $(uname -s) == Darwin ]]; then
  cpu=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)
  hardware=$(system_profiler SPHardwareDataType 2>/dev/null || true)
  [[ -n "$cpu" ]] || cpu=$(awk -F': ' '/Chip:/{print $2; exit}' <<< "$hardware")
  memory=$(sysctl -n hw.memsize 2>/dev/null || true)
  [[ -n "$memory" ]] || memory=$(awk -F': ' '/Memory:/{print $2; exit}' <<< "$hardware")
elif command -v lscpu >/dev/null 2>&1; then
  cpu=$(lscpu | awk -F: '/Model name/{sub(/^[ \t]+/, "", $2); print $2; exit}')
  memory=$(awk '/MemTotal/{print $2 * 1024; exit}' /proc/meminfo)
fi

{
  echo "captured_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "os=$os_name $os_version"
  echo "architecture=$(uname -m)"
  echo "cpu=$cpu"
  echo "memory=$memory"
  echo "kona_commit=$(git -C "$KONA_SRC" rev-parse HEAD)"
  echo "kona_worktree=clean"
  echo "jmh_version=1.37"
  echo "benchmark_source_sha256=$(sha256 "$workshop_root/apps/serialization-jmh/src/workshop/serialization/JavaSerializationBenchmark.java")"
  echo "dependency_lock_sha256=$(sha256 "$workshop_root/apps/serialization-jmh/dependencies.sha256")"
  echo "java_version=$($KONA_HOME/bin/java -version 2>&1 | paste -sd '|' -)"
} > "$output"

echo "已写入 $output"
