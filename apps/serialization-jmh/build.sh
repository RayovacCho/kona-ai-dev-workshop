#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
JDK_HOME="${KONA_HOME:-/Users/rayovac9/TencentKona-25/build/macosx-aarch64-server-release/images/jdk}"
JMH_VERSION=1.37
LIB="$ROOT/lib"
CLASSES="$ROOT/build/classes"

if [[ ! -x "$JDK_HOME/bin/javac" ]]; then
  echo "Kona javac not found at $JDK_HOME/bin/javac" >&2
  echo "Set KONA_HOME to the release JDK image." >&2
  exit 1
fi

mkdir -p "$LIB" "$CLASSES"

download() {
  local artifact="$1"
  local version="$2"
  local path="$3"
  local target="$LIB/$artifact-$version.jar"
  if [[ ! -f "$target" ]]; then
    curl --fail --location --retry 3 \
      "https://repo.maven.apache.org/maven2/$path/$artifact/$version/$artifact-$version.jar" \
      --output "$target"
  fi
}

download jmh-core "$JMH_VERSION" org/openjdk/jmh
download jmh-generator-annprocess "$JMH_VERSION" org/openjdk/jmh
download jopt-simple 5.0.4 net/sf/jopt-simple
download commons-math3 3.6.1 org/apache/commons

rm -rf "$CLASSES"
mkdir -p "$CLASSES"
CP="$LIB/jmh-core-$JMH_VERSION.jar:$LIB/jopt-simple-5.0.4.jar:$LIB/commons-math3-3.6.1.jar"
"$JDK_HOME/bin/javac" \
  -cp "$CP" \
  -processorpath "$LIB/jmh-generator-annprocess-$JMH_VERSION.jar:$LIB/jmh-core-$JMH_VERSION.jar" \
  -d "$CLASSES" \
  "$ROOT/src/workshop/serialization/JavaSerializationBenchmark.java"
"$JDK_HOME/bin/jar" --create --file "$ROOT/build/serialization-jmh.jar" -C "$CLASSES" .

echo "Built $ROOT/build/serialization-jmh.jar"

