#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
JDK_HOME="${KONA_HOME:-}"
JMH_VERSION=1.37

: "${JDK_HOME:?请设置 KONA_HOME，指向用于运行基准的 release JDK}"

SOURCE="$ROOT/src/workshop/serialization/JavaSerializationBenchmark.java"
FOCUSED_SOURCE="$ROOT/src/workshop/serialization/SerializationFocusedBenchmark.java"
JAR="$ROOT/build/serialization-jmh.jar"
if [[ ! -f "$JAR" || "$SOURCE" -nt "$JAR" || "$FOCUSED_SOURCE" -nt "$JAR" || \
      "$ROOT/build.sh" -nt "$JAR" || \
      "$ROOT/dependencies.sha256" -nt "$JAR" ]]; then
  "$ROOT/build.sh"
fi

mkdir -p "$ROOT/results"
STAMP="$(date +%Y%m%d-%H%M%S)"
RESULT_FILE="${JMH_RESULT_FILE:-$ROOT/results/baseline-$STAMP.json}"
mkdir -p "$(dirname "$RESULT_FILE")"
CP="$JAR:$ROOT/lib/jmh-core-$JMH_VERSION.jar:$ROOT/lib/jopt-simple-5.0.4.jar:$ROOT/lib/commons-math3-3.6.1.jar"

exec "$JDK_HOME/bin/java" -cp "$CP" org.openjdk.jmh.Main \
  "${JMH_INCLUDE:-workshop.serialization.JavaSerializationBenchmark}" \
  -rf json -rff "$RESULT_FILE" "$@"
