SHELL := /bin/bash

KONA_CONF ?= macosx-aarch64-server-release
KONA_HOME ?= $(if $(KONA_SRC),$(KONA_SRC)/build/$(KONA_CONF)/images/jdk,)
JTREG_TESTS := test/jdk/java/io/Serializable test/jdk/java/io/ObjectInputStream test/jdk/java/io/ObjectStreamClass
RESULT_DIR ?= results/task-2.1-baseline
BASELINE_DIR := $(abspath $(RESULT_DIR))

.NOTPARALLEL: benchmark

.PHONY: check test-mcp check-results jmh-build verify-clean-kona configure-kona \
        jdk-images jtreg-baseline jmh-baseline capture-environment \
        baseline-checksums benchmark

check: test-mcp check-results
	@bash -n apps/controlled-crash/build.sh apps/controlled-crash/run-crash.sh \
	  apps/controlled-crash/test-crashes.sh apps/serialization-jmh/build.sh \
	  apps/serialization-jmh/run.sh scripts/capture-environment.sh
	@git diff --check

test-mcp:
	@python3 -m unittest discover -s mcp/hotspot-crash-analyzer/tests -v

check-results:
	@python3 scripts/check-results.py

jmh-build:
	@test -n "$(KONA_HOME)" || { echo "请设置 KONA_HOME" >&2; exit 2; }
	@KONA_HOME="$(KONA_HOME)" apps/serialization-jmh/build.sh

verify-clean-kona:
	@test -n "$(KONA_SRC)" || { echo "请设置 KONA_SRC" >&2; exit 2; }
	@test "$$(git -C "$(KONA_SRC)" rev-parse --is-inside-work-tree 2>/dev/null)" = true || { \
	  echo "KONA_SRC 不是 Git 工作树：$(KONA_SRC)" >&2; exit 2; }
	@test -z "$$(git -C "$(KONA_SRC)" status --porcelain)" || { \
	  echo "拒绝在含未提交修改的 Kona 工作树上生成正式基准：$(KONA_SRC)" >&2; \
	  git -C "$(KONA_SRC)" status --short >&2; exit 2; }

configure-kona: verify-clean-kona
	@test -n "$(BOOT_JDK)" || { echo "请设置 BOOT_JDK" >&2; exit 2; }
	@test -n "$(JT_HOME)" || { echo "请设置 JT_HOME" >&2; exit 2; }
	@cd "$(KONA_SRC)" && bash configure --with-boot-jdk="$(BOOT_JDK)" \
	  --with-jtreg="$(JT_HOME)" --disable-warnings-as-errors

jdk-images: verify-clean-kona
	@env -u MAKEFLAGS -u MFLAGS -u MAKELEVEL make -C "$(KONA_SRC)" CONF="$(KONA_CONF)" images

jtreg-baseline: verify-clean-kona
	@env -u MAKEFLAGS -u MFLAGS -u MAKELEVEL make -C "$(KONA_SRC)" \
	  CONF="$(KONA_CONF)" build-test-lib
	@env -u MAKEFLAGS -u MFLAGS -u MAKELEVEL make -C "$(KONA_SRC)" \
	  CONF="$(KONA_CONF)" test-image-jdk-jtreg-native
	@env -u MAKEFLAGS -u MFLAGS -u MAKELEVEL make -C "$(KONA_SRC)" \
	  CONF="$(KONA_CONF)" test-only \
	  TEST="$(JTREG_TESTS)" JTREG='JOBS=4;TIMEOUT_FACTOR=4'

jmh-baseline: verify-clean-kona jmh-build
	@test ! -e "$(BASELINE_DIR)/jmh-result.json" || \
	  test "$(ALLOW_BASELINE_OVERWRITE)" = 1 || { \
	  echo "正式结果已存在：$(BASELINE_DIR)/jmh-result.json" >&2; \
	  echo "请设置新的 RESULT_DIR；确需覆盖时显式传 ALLOW_BASELINE_OVERWRITE=1" >&2; exit 2; }
	@mkdir -p "$(BASELINE_DIR)"
	@KONA_HOME="$(KONA_HOME)" \
	  JMH_RESULT_FILE="$(BASELINE_DIR)/jmh-result.json" \
	  apps/serialization-jmh/run.sh -prof gc

capture-environment: verify-clean-kona
	@test ! -e "$(BASELINE_DIR)/environment.txt" || \
	  test "$(ALLOW_BASELINE_OVERWRITE)" = 1 || { \
	  echo "正式环境清单已存在：$(BASELINE_DIR)/environment.txt" >&2; \
	  echo "请设置新的 RESULT_DIR；确需覆盖时显式传 ALLOW_BASELINE_OVERWRITE=1" >&2; exit 2; }
	@mkdir -p "$(BASELINE_DIR)"
	@KONA_SRC="$(KONA_SRC)" KONA_HOME="$(KONA_HOME)" \
	  scripts/capture-environment.sh "$(BASELINE_DIR)/environment.txt"
	@$(MAKE) --no-print-directory baseline-checksums RESULT_DIR="$(RESULT_DIR)"

baseline-checksums:
	@test -f "$(BASELINE_DIR)/jmh-result.json" || { echo "缺少 jmh-result.json" >&2; exit 2; }
	@test -f "$(BASELINE_DIR)/environment.txt" || { echo "缺少 environment.txt" >&2; exit 2; }
	@cd "$(BASELINE_DIR)" && if command -v sha256sum >/dev/null 2>&1; then \
	  sha256sum jmh-result.json environment.txt > SHA256SUMS; \
	else \
	  shasum -a 256 jmh-result.json environment.txt > SHA256SUMS; \
	fi

benchmark: verify-clean-kona jdk-images jtreg-baseline jmh-baseline capture-environment
