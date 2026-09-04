#!/usr/bin/env python3
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


ROOT = Path(__file__).resolve().parent.parent
RESULT_ROOT = ROOT / "results"
EXPECTED_CHECKSUM_FILES = {"jmh-result.json", "environment.txt"}
RESULT_DIRS = tuple(
    sorted(
        {
            path.parent
            for name in EXPECTED_CHECKSUM_FILES
            for path in RESULT_ROOT.rglob(name)
        }
    )
)
REPEAT_DIR = RESULT_ROOT / "task-2.3-repeat"
REPEAT_CHECKSUM_FILES = {"baseline.json", "optimized.json"}
REQUIRED_RESULT_DIRS = {
    RESULT_ROOT / "task-2.1-baseline",
    RESULT_ROOT / "task-2.3-round1",
    RESULT_ROOT / "task-2.3-round2",
    RESULT_ROOT / "task-2.3-round3",
    RESULT_ROOT / "task-2.3-final",
}
LEGACY_RESULT_DIRS = {
    RESULT_ROOT / "task-2.3-round1",
    RESULT_ROOT / "task-2.3-round2",
    RESULT_ROOT / "task-2.3-round3",
}
REQUIRED_ENV = {
    "captured_at_utc",
    "os",
    "architecture",
    "cpu",
    "memory",
    "kona_commit",
    "kona_worktree",
    "jmh_version",
    "benchmark_source_sha256",
    "dependency_lock_sha256",
    "java_version",
}
PROVENANCE_ENV = {
    "environment_schema",
    "kona_home",
    "jdk_source_revision",
    "jdk_release_sha256",
    "java_executable_sha256",
    "modules_sha256",
}
PROVENANCE_ENV_V3 = {
    "workshop_commit",
    "workshop_worktree",
    "benchmark_build_sha256",
    "benchmark_run_sha256",
    "capture_environment_sha256",
    "benchmark_jar_sha256",
}
BENCHMARK_SOURCE = (
    ROOT
    / "apps"
    / "serialization-jmh"
    / "src"
    / "workshop"
    / "serialization"
    / "JavaSerializationBenchmark.java"
)
DEPENDENCY_LOCK = ROOT / "apps" / "serialization-jmh" / "dependencies.sha256"
BASELINE_REPORT = ROOT / "docs" / "reports" / "task-2.1-serialization-baseline.md"
FINAL_REPORT = ROOT / "docs" / "reports" / "task-2.3-serialization-followup.md"
COMPARABLE_ENV = ("os", "architecture", "cpu", "memory")
HISTORICAL_BENCHMARK_SOURCE_SHA256 = (
    "c92bdf5086d89410e8856f494a60f412c5d399199207509cd5ed9196be104079"
)
HISTORICAL_BENCHMARK_RESULT_DIRS = {
    RESULT_ROOT / "task-2.3-round1",
    RESULT_ROOT / "task-2.3-round2",
    RESULT_ROOT / "task-2.3-round3",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_checksums(
    result_dir: Path, expected_files=EXPECTED_CHECKSUM_FILES
) -> None:
    checksum_file = result_dir / "SHA256SUMS"
    entries = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise SystemExit(f"校验和清单行格式无效：{checksum_file}：{line!r}")
        expected, name = parts
        name = name.lstrip("*")
        if name in entries:
            raise SystemExit(f"校验和清单包含重复文件：{result_dir / name}")
        if Path(name).name != name:
            raise SystemExit(f"校验和清单包含非法路径：{name}")
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected.lower()):
            raise SystemExit(f"校验和格式无效：{result_dir / name}")
        entries[name] = expected.lower()
    if set(entries) != expected_files:
        raise SystemExit(
            f"校验和清单文件集合不符合预期：{result_dir}；"
            f"实际 {sorted(entries)}，期望 {sorted(expected_files)}"
        )
    for name, expected in entries.items():
        path = result_dir / name
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"校验和不匹配：{path}")


def read_environment(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or not value:
            raise SystemExit(f"环境清单第 {line_number} 行格式无效：{path}")
        if key in values:
            raise SystemExit(f"环境清单包含重复字段 {key}：{path}")
        values[key] = value
    return values


def check_environment(result_dir: Path) -> Dict[str, str]:
    values = read_environment(result_dir / "environment.txt")
    missing = REQUIRED_ENV - values.keys()
    if missing:
        raise SystemExit(f"缺少环境字段：{sorted(missing)}")
    if values["kona_worktree"] != "clean":
        raise SystemExit("正式基准并非由无未提交修改的 Kona 工作树生成")
    if not re.fullmatch(r"[0-9a-f]{40}", values["kona_commit"]):
        raise SystemExit("Kona commit 不是完整的 40 位 Git 对象编号")
    if values["jmh_version"] != "1.37":
        raise SystemExit(f"JMH 版本不符合预期：{values['jmh_version']}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", values["captured_at_utc"]):
        raise SystemExit("环境采集时间不是 UTC ISO-8601 格式")
    benchmark_hash = values["benchmark_source_sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", benchmark_hash):
        raise SystemExit("基准源码哈希格式无效")
    expected_benchmark_hash = (
        HISTORICAL_BENCHMARK_SOURCE_SHA256
        if result_dir in HISTORICAL_BENCHMARK_RESULT_DIRS
        else sha256(BENCHMARK_SOURCE)
    )
    if benchmark_hash != expected_benchmark_hash:
        raise SystemExit("基准源码与正式基准记录不一致")
    if values["dependency_lock_sha256"] != sha256(DEPENDENCY_LOCK):
        raise SystemExit("依赖锁定文件与正式基准记录不一致")
    schema = values.get("environment_schema")
    if schema is not None:
        if schema not in {"2", "3"}:
            raise SystemExit(f"不支持的环境清单版本：{schema}")
        missing_provenance = PROVENANCE_ENV - values.keys()
        if missing_provenance:
            raise SystemExit(f"缺少 JDK 产物来源字段：{sorted(missing_provenance)}")
        if values["jdk_source_revision"] != values["kona_commit"][:12]:
            raise SystemExit("JDK SOURCE 修订与 Kona commit 不一致")
        if not values["kona_home"].endswith("/images/jdk"):
            raise SystemExit("正式基准没有使用 images/jdk")
        for key in ("jdk_release_sha256", "java_executable_sha256", "modules_sha256"):
            value = values[key]
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
                raise SystemExit(f"JDK 产物哈希无效：{key}")
        if schema == "3":
            missing_v3 = PROVENANCE_ENV_V3 - values.keys()
            if missing_v3:
                raise SystemExit(f"缺少基准执行来源字段：{sorted(missing_v3)}")
            if values["workshop_worktree"] != "clean":
                raise SystemExit("正式基准并非由无未提交修改的 workshop 工作树生成")
            if not re.fullmatch(r"[0-9a-f]{40}", values["workshop_commit"]):
                raise SystemExit("workshop commit 不是完整的 40 位 Git 对象编号")
            for key in PROVENANCE_ENV_V3 - {"workshop_commit", "workshop_worktree"}:
                if not re.fullmatch(r"[0-9a-f]{64}", values[key]):
                    raise SystemExit(f"基准执行产物哈希无效：{key}")
    return values


def check_comparable_environments(environments: Mapping[Path, Dict[str, str]]) -> None:
    pairs = ((RESULT_ROOT / "task-2.1-baseline", RESULT_ROOT / "task-2.3-final"),)
    for baseline_dir, final_dir in pairs:
        baseline = environments.get(baseline_dir)
        final = environments.get(final_dir)
        if baseline is None or final is None:
            continue
        differences = {
            key: (baseline.get(key), final.get(key))
            for key in COMPARABLE_ENV
            if baseline.get(key) != final.get(key)
        }
        if differences:
            raise SystemExit(
                f"基线与最终结果的测试环境不一致：{baseline_dir.name} / "
                f"{final_dir.name}：{differences}"
            )


def check_required_provenance(result_dir: Path, environment: Dict[str, str]) -> None:
    if result_dir in LEGACY_RESULT_DIRS:
        return
    if result_dir in REQUIRED_RESULT_DIRS:
        if environment.get("environment_schema") != "2":
            raise SystemExit(f"当前已归档正式结果必须使用 environment_schema=2：{result_dir}")
    elif environment.get("environment_schema") != "3":
        raise SystemExit(f"新正式结果必须使用 environment_schema=3：{result_dir}")


def check_jmh(
    result_dir: Path,
    environment: Dict[str, str],
    report_path: Optional[Path] = None,
) -> None:
    with (result_dir / "jmh-result.json").open(encoding="utf-8") as stream:
        results = json.load(stream)
    payloads = {"SMALL", "GRAPH", "CUSTOM"}
    if environment["benchmark_source_sha256"] != HISTORICAL_BENCHMARK_SOURCE_SHA256:
        payloads.update({"SMALL_CHINESE", "GRAPH_CHINESE", "LARGE_OBJECT_ARRAY"})
    expected = {
        (operation, payload)
        for operation in ("serialize", "deserialize", "roundTrip")
        for payload in payloads
    }
    actual = {
        (entry["benchmark"].rsplit(".", 1)[-1], entry["params"]["payloadType"])
        for entry in results
    }
    if actual != expected or len(results) != len(expected):
        raise SystemExit(f"JMH 结果矩阵不符合预期：{sorted(actual)}")
    report = report_path.read_text(encoding="utf-8") if report_path else None
    for entry in results:
        if environment.get("environment_schema") in {"2", "3"}:
            expected_java = str(Path(environment["kona_home"]) / "bin" / "java")
            if entry.get("jvm") != expected_java:
                raise SystemExit(
                    f"JMH JVM 与环境清单不一致：{entry.get('jvm')} != {expected_java}"
                )
        expected_configuration = {
            "mode": "avgt",
            "threads": 1,
            "forks": 3,
            "warmupIterations": 5,
            "warmupTime": "1 s",
            "warmupBatchSize": 1,
            "measurementIterations": 5,
            "measurementTime": "1 s",
            "measurementBatchSize": 1,
        }
        for key, expected_value in expected_configuration.items():
            if entry.get(key) != expected_value:
                raise SystemExit(f"JMH 配置不符合预期 {key}：{entry.get(key)}")
        if entry["primaryMetric"].get("scoreUnit") != "us/op":
            raise SystemExit(f"分数单位不符合预期：{entry['benchmark']}")
        check_raw_data(entry["primaryMetric"], entry["benchmark"])
        score = entry["primaryMetric"].get("score")
        score_error = entry["primaryMetric"].get("scoreError")
        if not isinstance(score, (int, float)) or not math.isfinite(score) or score <= 0:
            raise SystemExit(f"主分数无效：{entry['benchmark']}")
        if (
            not isinstance(score_error, (int, float))
            or not math.isfinite(score_error)
            or score_error < 0
        ):
            raise SystemExit(f"主分数误差无效：{entry['benchmark']}")
        allocation = entry.get("secondaryMetrics", {}).get("gc.alloc.rate.norm", {})
        if allocation.get("scoreUnit") != "B/op":
            raise SystemExit(f"分配量单位不符合预期：{entry['benchmark']}")
        check_raw_data(allocation, entry["benchmark"] + " gc.alloc.rate.norm")
        allocation_score = allocation.get("score")
        if (
            not isinstance(allocation_score, (int, float))
            or not math.isfinite(allocation_score)
            or allocation_score <= 0
        ):
            raise SystemExit(f"缺少 GC 分配指标：{entry['benchmark']}")
        displayed_score = (
            f"{score:.3f} ± "
            f"{score_error:.3f}"
        )
        displayed_allocation = f"{allocation_score:,.0f}"
        if report is not None:
            operation = entry["benchmark"].rsplit(".", 1)[-1]
            payload = entry["params"]["payloadType"]
            prefix = f"| `{operation}` | {payload} |"
            rows = [line for line in report.splitlines() if line.startswith(prefix)]
            if len(rows) != 1:
                raise SystemExit(f"报告中缺少唯一结果行：{operation}/{payload}")
            if displayed_score not in rows[0]:
                raise SystemExit(f"报告对应行缺少 JMH 分数：{displayed_score}")
            if displayed_allocation not in rows[0]:
                raise SystemExit(f"报告对应行缺少分配量分数：{displayed_allocation}")


def check_raw_data(metric: Dict[str, Any], benchmark: str) -> None:
    raw_data = metric.get("rawData")
    if (
        not isinstance(raw_data, list)
        or len(raw_data) != 3
        or any(not isinstance(fork, list) or len(fork) != 5 for fork in raw_data)
    ):
        raise SystemExit(f"JMH 原始样本不是 3 forks × 5 iterations：{benchmark}")
    if any(
        not isinstance(value, (int, float)) or not math.isfinite(value)
        for fork in raw_data
        for value in fork
    ):
        raise SystemExit(f"JMH 原始样本包含非有限数值：{benchmark}")


def check_repeat_results() -> None:
    check_checksums(REPEAT_DIR, REPEAT_CHECKSUM_FILES)
    report = FINAL_REPORT.read_text(encoding="utf-8")
    expected_jvms = {
        "baseline.json": read_environment(
            RESULT_ROOT / "task-2.1-baseline" / "environment.txt"
        )["kona_home"] + "/bin/java",
        "optimized.json": read_environment(
            RESULT_ROOT / "task-2.3-final" / "environment.txt"
        )["kona_home"] + "/bin/java",
    }
    for name, expected_jvm in expected_jvms.items():
        results = json.loads((REPEAT_DIR / name).read_text(encoding="utf-8"))
        operations = {"serialize", "deserialize", "roundTrip"}
        actual = {entry["benchmark"].rsplit(".", 1)[-1] for entry in results}
        if len(results) != 3 or actual != operations:
            raise SystemExit(f"反向复测操作矩阵不符合预期：{name}")
        for entry in results:
            if entry.get("params", {}).get("payloadType") != "GRAPH":
                raise SystemExit(f"反向复测包含非 GRAPH 载荷：{name}")
            if entry.get("jvm") != expected_jvm:
                raise SystemExit(f"反向复测 JVM 与正式环境不一致：{name}")
            for key, expected_value in {
                "mode": "avgt", "threads": 1, "forks": 3,
                "warmupIterations": 5, "warmupTime": "1 s", "warmupBatchSize": 1,
                "measurementIterations": 5, "measurementTime": "1 s",
                "measurementBatchSize": 1,
            }.items():
                if entry.get(key) != expected_value:
                    raise SystemExit(f"反向复测配置不符合预期 {key}：{name}")
            check_raw_data(entry["primaryMetric"], entry["benchmark"])
            allocation = entry.get("secondaryMetrics", {}).get("gc.alloc.rate.norm", {})
            if allocation.get("scoreUnit") != "B/op":
                raise SystemExit(f"反向复测缺少 B/op 指标：{name}")
            check_raw_data(allocation, entry["benchmark"] + " gc.alloc.rate.norm")
    for value in (
        "11.568 ± 0.422", "11.460 ± 0.117", "34,021", "32,944",
        "18.020 ± 0.306", "17.690 ± 0.304", "54,824", "52,496",
        "5.942 ± 0.156", "5.889 ± 0.162", "18,664", "16,320",
    ):
        if value not in report:
            raise SystemExit(f"最终报告缺少反向复测结果：{value}")


if __name__ == "__main__":
    reports = {
        "task-2.1-baseline": BASELINE_REPORT,
        "task-2.3-final": FINAL_REPORT,
    }
    missing_result_dirs = REQUIRED_RESULT_DIRS - set(RESULT_DIRS)
    if missing_result_dirs:
        raise SystemExit(f"缺少基准结果目录：{sorted(map(str, missing_result_dirs))}")
    environments = {}
    for result_dir in RESULT_DIRS:
        check_checksums(result_dir)
        environment = check_environment(result_dir)
        environments[result_dir] = environment
        check_required_provenance(result_dir, environment)
        check_jmh(result_dir, environment, reports.get(result_dir.name))
    check_comparable_environments(environments)
    check_repeat_results()
    print(f"基准产物：{len(RESULT_DIRS)} 组正式结果及 1 组反向复测检查通过")
