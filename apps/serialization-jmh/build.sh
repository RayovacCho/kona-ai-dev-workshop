#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
JDK_HOME="${KONA_HOME:-}"
JMH_VERSION=1.37
LIB="$ROOT/lib"
CLASSES="$ROOT/build/classes"

: "${JDK_HOME:?请设置 KONA_HOME，指向用于编译和测试的 JDK}"
if [[ ! -x "$JDK_HOME/bin/javac" ]]; then
  echo "未找到可执行的 Kona javac：$JDK_HOME/bin/javac" >&2
  echo "请将 KONA_HOME 设置为发布版 JDK 镜像目录。" >&2
  exit 1
fi

mkdir -p "$LIB" "$CLASSES"

download() {
  local artifact="$1"
  local version="$2"
  local path="$3"
  local target="$LIB/$artifact-$version.jar"
  local temporary="$target.tmp.$$"
  if [[ ! -f "$target" ]]; then
    if ! curl --fail --location --retry 3 \
      "https://repo.maven.apache.org/maven2/$path/$artifact/$version/$artifact-$version.jar" \
      --output "$temporary"; then
      rm -f "$temporary"
      return 1
    fi
    mv "$temporary" "$target"
  fi
}

download jmh-core "$JMH_VERSION" org/openjdk/jmh
download jmh-generator-annprocess "$JMH_VERSION" org/openjdk/jmh
download jopt-simple 5.0.4 net/sf/jopt-simple
download commons-math3 3.6.1 org/apache/commons

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$LIB" && sha256sum --check "$ROOT/dependencies.sha256")
else
  (cd "$LIB" && shasum -a 256 --check "$ROOT/dependencies.sha256")
fi

rm -rf "$CLASSES"
mkdir -p "$CLASSES"
CP="$LIB/jmh-core-$JMH_VERSION.jar:$LIB/jopt-simple-5.0.4.jar:$LIB/commons-math3-3.6.1.jar"
"$JDK_HOME/bin/javac" \
  -cp "$CP" \
  -processorpath "$LIB/jmh-generator-annprocess-$JMH_VERSION.jar:$LIB/jmh-core-$JMH_VERSION.jar" \
  -d "$CLASSES" \
  "$ROOT/src/workshop/serialization/JavaSerializationBenchmark.java" \
  "$ROOT/src/workshop/serialization/SerializationFocusedBenchmark.java"
"$JDK_HOME/bin/jar" --create --file "$ROOT/build/serialization-jmh.jar" -C "$CLASSES" .

echo "已构建 $ROOT/build/serialization-jmh.jar"
