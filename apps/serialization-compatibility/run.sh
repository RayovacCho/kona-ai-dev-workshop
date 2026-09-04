#!/usr/bin/env bash
set -euo pipefail

: "${BASELINE_JAVA_HOME:?请设置 BASELINE_JAVA_HOME}"
: "${OPTIMIZED_JAVA_HOME:?请设置 OPTIMIZED_JAVA_HOME}"

root=$(cd "$(dirname "$0")" && pwd)
build="$root/build"
temporary=$(mktemp -d "${TMPDIR:-/tmp}/serialization-compatibility.XXXXXX")
trap 'rm -rf "$temporary"' EXIT

for java_home in "$BASELINE_JAVA_HOME" "$OPTIMIZED_JAVA_HOME"; do
  [[ -x "$java_home/bin/java" ]] || { echo "缺少 $java_home/bin/java" >&2; exit 2; }
done

rm -rf "$build"
mkdir -p "$build"
"$BASELINE_JAVA_HOME/bin/javac" -d "$build" "$root/SerializationCompatibility.java"

baseline_stream="$temporary/baseline.ser"
optimized_stream="$temporary/optimized.ser"
"$BASELINE_JAVA_HOME/bin/java" -cp "$build" SerializationCompatibility write "$baseline_stream"
"$OPTIMIZED_JAVA_HOME/bin/java" -cp "$build" SerializationCompatibility read "$baseline_stream"
"$OPTIMIZED_JAVA_HOME/bin/java" -cp "$build" SerializationCompatibility write "$optimized_stream"
"$BASELINE_JAVA_HOME/bin/java" -cp "$build" SerializationCompatibility read "$optimized_stream"

cmp "$baseline_stream" "$optimized_stream"
stream_size=$(wc -c < "$baseline_stream" | tr -d ' ')
echo "跨版本读取与字节流一致性检查通过（$stream_size 字节）"
