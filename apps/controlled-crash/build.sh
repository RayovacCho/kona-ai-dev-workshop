#!/usr/bin/env bash
set -euo pipefail

: "${KONA_SRC:?请设置 KONA_SRC，指向 TencentKona-25 源码树}"
: "${JAVA_HOME:?请设置 JAVA_HOME，指向 Kona fastdebug JDK 镜像}"
APP_DIR=$(cd "$(dirname "$0")" && pwd)
OUT="$APP_DIR/build"
WHITEBOX_ROOT="$KONA_SRC/test/lib/jdk/test/whitebox"
JAVAC="$JAVA_HOME/bin/javac"
JAR_TOOL="$JAVA_HOME/bin/jar"

[[ -d "$WHITEBOX_ROOT" ]] || { echo "缺少 WhiteBox 源码目录：$WHITEBOX_ROOT" >&2; exit 2; }
[[ -x "$JAVAC" ]] || { echo "文件不可执行：$JAVAC" >&2; exit 2; }
[[ -x "$JAR_TOOL" ]] || { echo "文件不可执行：$JAR_TOOL" >&2; exit 2; }

whitebox_sources=()
while IFS= read -r source; do
  whitebox_sources+=("$source")
done < <(find "$WHITEBOX_ROOT" -name '*.java' -type f -print)
[[ ${#whitebox_sources[@]} -gt 0 ]] || { echo "未找到 WhiteBox Java 源码" >&2; exit 2; }

rm -rf "$OUT/classes"
mkdir -p "$OUT/classes"
"$JAVAC" -d "$OUT/classes" "${whitebox_sources[@]}" \
  "$APP_DIR/src/workshop/crash/ControlledCrash.java"
"$JAR_TOOL" --create --file "$OUT/controlled-crash.jar" -C "$OUT/classes" .
echo "已构建 $OUT/controlled-crash.jar"
