#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
JDK_HOME="${KONA_HOME:-/Users/rayovac9/TencentKona-25/build/macosx-aarch64-server-release/images/jdk}"
JMH_VERSION=1.37

if [[ ! -f "$ROOT/build/serialization-jmh.jar" ]]; then
  "$ROOT/build.sh"
fi

mkdir -p "$ROOT/results"
STAMP="$(date +%Y%m%d-%H%M%S)"
CP="$ROOT/build/serialization-jmh.jar:$ROOT/lib/jmh-core-$JMH_VERSION.jar:$ROOT/lib/jopt-simple-5.0.4.jar:$ROOT/lib/commons-math3-3.6.1.jar"

exec "$JDK_HOME/bin/java" -cp "$CP" org.openjdk.jmh.Main \
  'workshop.serialization.JavaSerializationBenchmark' \
  -rf json -rff "$ROOT/results/baseline-$STAMP.json" "$@"

