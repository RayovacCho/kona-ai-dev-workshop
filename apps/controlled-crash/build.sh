#!/usr/bin/env bash
set -euo pipefail

KONA_SRC=${KONA_SRC:-/Users/rayovac9/TencentKona-25}
APP_DIR=$(cd "$(dirname "$0")" && pwd)
OUT="$APP_DIR/build"

mkdir -p "$OUT/classes"
whitebox_sources=()
while IFS= read -r source; do
  whitebox_sources+=("$source")
done < <(find "$KONA_SRC/test/lib/jdk/test/whitebox" -name '*.java' -type f -print)

javac -d "$OUT/classes" "${whitebox_sources[@]}" \
  "$APP_DIR/src/workshop/crash/ControlledCrash.java"
jar --create --file "$OUT/controlled-crash.jar" -C "$OUT/classes" .
echo "已构建 $OUT/controlled-crash.jar"
