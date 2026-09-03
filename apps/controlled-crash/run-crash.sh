#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^-?[0-9]+$ ]]; then
  echo "用法：$0 <崩溃编号>" >&2
  exit 2
fi

APP_DIR=$(cd "$(dirname "$0")" && pwd)
: "${JAVA_HOME:?请设置 JAVA_HOME，指向 Kona fastdebug JDK 镜像}"
LOG_DIR=${LOG_DIR:-"$APP_DIR/crash-logs"}
JAR="$APP_DIR/build/controlled-crash.jar"

[[ -x "$JAVA_HOME/bin/java" ]] || { echo "文件不可执行：$JAVA_HOME/bin/java" >&2; exit 2; }
[[ -f "$JAR" ]] || { echo "请先构建应用：$APP_DIR/build.sh" >&2; exit 2; }
java_version=$("$JAVA_HOME/bin/java" -version 2>&1)
[[ "$java_version" == *fastdebug* || "$java_version" == *slowdebug* ]] || {
  echo "受控崩溃只能使用 fastdebug/slowdebug JVM：$JAVA_HOME" >&2
  exit 2
}
mkdir -p "$LOG_DIR"

exec "$JAVA_HOME/bin/java" \
  -XX:+UnlockDiagnosticVMOptions \
  -XX:+WhiteBoxAPI \
  -XX:ErrorFile="$LOG_DIR/hs_err_pid%p.log" \
  -Xbootclasspath/a:"$JAR" \
  workshop.crash.ControlledCrash "$1"
