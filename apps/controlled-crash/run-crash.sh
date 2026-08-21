#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^-?[0-9]+$ ]]; then
  echo "Usage: $0 <crash-number>" >&2
  exit 2
fi

APP_DIR=$(cd "$(dirname "$0")" && pwd)
JAVA_HOME=${JAVA_HOME:-/Users/rayovac9/TencentKona-25/build/macosx-aarch64-server-fastdebug/images/jdk}
LOG_DIR=${LOG_DIR:-"$APP_DIR/crash-logs"}
JAR="$APP_DIR/build/controlled-crash.jar"

[[ -x "$JAVA_HOME/bin/java" ]] || { echo "Not executable: $JAVA_HOME/bin/java" >&2; exit 2; }
[[ -f "$JAR" ]] || { echo "Build the app first: $APP_DIR/build.sh" >&2; exit 2; }
mkdir -p "$LOG_DIR"

exec "$JAVA_HOME/bin/java" \
  -XX:+UnlockDiagnosticVMOptions \
  -XX:+WhiteBoxAPI \
  -XX:ErrorFile="$LOG_DIR/hs_err_pid%p.log" \
  -Xbootclasspath/a:"$JAR" \
  workshop.crash.ControlledCrash "$1"
