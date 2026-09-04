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
output_tmp=$(mktemp "${output}.tmp.XXXXXX")
trap 'rm -f "$output_tmp"' EXIT

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
if [[ -n "$(git -C "$workshop_root" status --porcelain --untracked-files=no)" ]]; then
  echo "拒绝记录含未提交修改的 workshop 工作树" >&2
  exit 2
fi

kona_root=$(cd "$KONA_SRC" && pwd -P)
kona_home=$(cd "$KONA_HOME" && pwd -P)
expected_home="$kona_root/build/${KONA_CONF:-macosx-aarch64-server-release}/images/jdk"
if [[ "$kona_home" != "$expected_home" ]]; then
  echo "正式基准必须使用当前 KONA_SRC 的 images/jdk" >&2
  echo "期望：$expected_home" >&2
  echo "实际：$kona_home" >&2
  exit 2
fi

kona_commit=$(git -C "$KONA_SRC" rev-parse HEAD)
kona_revision=${kona_commit:0:12}
release_file="$kona_home/release"
modules_file="$kona_home/lib/modules"
benchmark_jar="$workshop_root/apps/serialization-jmh/build/serialization-jmh.jar"
[[ -x "$kona_home/bin/java" ]] || { echo "缺少 $kona_home/bin/java" >&2; exit 2; }
[[ -f "$release_file" ]] || { echo "缺少 $release_file" >&2; exit 2; }
[[ -f "$modules_file" ]] || { echo "缺少 $modules_file" >&2; exit 2; }
[[ -f "$benchmark_jar" ]] || { echo "缺少 $benchmark_jar；请先运行 make jmh-build" >&2; exit 2; }
jdk_source=$(sed -n 's/^SOURCE="\(.*\)"$/\1/p' "$release_file")
if [[ "$jdk_source" != *"git:$kona_revision"* ]]; then
  echo "JDK release 中的源码修订与 Kona HEAD 不一致" >&2
  echo "Kona HEAD：$kona_revision" >&2
  echo "JDK SOURCE：$jdk_source" >&2
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
  echo "environment_schema=3"
  echo "captured_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "os=$os_name $os_version"
  echo "architecture=$(uname -m)"
  echo "cpu=$cpu"
  echo "memory=$memory"
  echo "kona_commit=$kona_commit"
  echo "kona_worktree=clean"
  echo "workshop_commit=$(git -C "$workshop_root" rev-parse HEAD)"
  echo "workshop_worktree=clean"
  echo "kona_home=$kona_home"
  echo "jdk_source_revision=$kona_revision"
  echo "jdk_release_sha256=$(sha256 "$release_file")"
  echo "java_executable_sha256=$(sha256 "$kona_home/bin/java")"
  echo "modules_sha256=$(sha256 "$modules_file")"
  echo "jmh_version=1.37"
  echo "benchmark_source_sha256=$(sha256 "$workshop_root/apps/serialization-jmh/src/workshop/serialization/JavaSerializationBenchmark.java")"
  echo "focused_benchmark_source_sha256=$(sha256 "$workshop_root/apps/serialization-jmh/src/workshop/serialization/SerializationFocusedBenchmark.java")"
  echo "dependency_lock_sha256=$(sha256 "$workshop_root/apps/serialization-jmh/dependencies.sha256")"
  echo "benchmark_build_sha256=$(sha256 "$workshop_root/apps/serialization-jmh/build.sh")"
  echo "benchmark_run_sha256=$(sha256 "$workshop_root/apps/serialization-jmh/run.sh")"
  echo "capture_environment_sha256=$(sha256 "$workshop_root/scripts/capture-environment.sh")"
  echo "benchmark_jar_sha256=$(sha256 "$benchmark_jar")"
  echo "java_version=$("$kona_home/bin/java" -version 2>&1 | paste -sd '|' -)"
} > "$output_tmp"

mv "$output_tmp" "$output"
trap - EXIT

echo "已写入 $output"
