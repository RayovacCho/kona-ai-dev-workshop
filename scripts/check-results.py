#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Optional


ROOT = Path(__file__).resolve().parent.parent
RESULT_ROOT = ROOT / "results"
EXPECTED_CHECKSUM_FILES = {"jmh-result.json", "environment.txt"}
RESULT_DIRS = tuple(
    sorted(
        {
            path.parent
            for name in (*EXPECTED_CHECKSUM_FILES, "SHA256SUMS")
            for path in RESULT_ROOT.rglob(name)
        }
    )
)
REQUIRED_RESULT_DIRS = {
    RESULT_ROOT / "task-2.1-baseline",
    RESULT_ROOT / "task-2.3-round1",
    RESULT_ROOT / "task-2.3-round2",
    RESULT_ROOT / "task-2.3-round3",
    RESULT_ROOT / "task-2.3-final",
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_checksums(result_dir: Path) -> None:
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
    if set(entries) != EXPECTED_CHECKSUM_FILES:
        raise SystemExit(
            f"校验和清单文件集合不符合预期：{result_dir}；"
            f"实际 {sorted(entries)}，期望 {sorted(EXPECTED_CHECKSUM_FILES)}"
        )
    for name, expected in entries.items():
        path = result_dir / name
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"校验和不匹配：{path}")


def check_environment(result_dir: Path) -> Dict[str, str]:
    values = {}
    for line in (result_dir / "environment.txt").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    missing = REQUIRED_ENV - values.keys()
    if missing:
        raise SystemExit(f"缺少环境字段：{sorted(missing)}")
    if values["kona_worktree"] != "clean":
        raise SystemExit("正式基准并非由无未提交修改的 Kona 工作树生成")
    if not re.fullmatch(r"[0-9a-f]{40}", values["kona_commit"]):
        raise SystemExit("Kona commit 不是完整的 40 位 Git 对象编号")
    if values["jmh_version"] != "1.37":
        raise SystemExit(f"JMH 版本不符合预期：{values['jmh_version']}")
    if values["benchmark_source_sha256"] != sha256(BENCHMARK_SOURCE):
        raise SystemExit("基准源码与正式基准记录不一致")
    if values["dependency_lock_sha256"] != sha256(DEPENDENCY_LOCK):
        raise SystemExit("依赖锁定文件与正式基准记录不一致")
    schema = values.get("environment_schema")
    if schema is not None:
        if schema != "2":
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
    return values


def check_jmh(
    result_dir: Path,
    environment: Dict[str, str],
    report_path: Optional[Path] = None,
) -> None:
    with (result_dir / "jmh-result.json").open(encoding="utf-8") as stream:
        results = json.load(stream)
    expected = {
        (operation, payload)
        for operation in ("serialize", "deserialize", "roundTrip")
        for payload in ("SMALL", "GRAPH", "CUSTOM")
    }
    actual = {
        (entry["benchmark"].rsplit(".", 1)[-1], entry["params"]["payloadType"])
        for entry in results
    }
    if actual != expected or len(results) != len(expected):
        raise SystemExit(f"JMH 结果矩阵不符合预期：{sorted(actual)}")
    report = report_path.read_text(encoding="utf-8") if report_path else None
    for entry in results:
        if environment.get("environment_schema") == "2":
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
            "measurementIterations": 5,
            "measurementTime": "1 s",
        }
        for key, expected_value in expected_configuration.items():
            if entry.get(key) != expected_value:
                raise SystemExit(f"JMH 配置不符合预期 {key}：{entry.get(key)}")
        if entry["primaryMetric"].get("scoreUnit") != "us/op":
            raise SystemExit(f"分数单位不符合预期：{entry['benchmark']}")
        if entry["primaryMetric"]["score"] <= 0:
            raise SystemExit(f"主分数无效：{entry['benchmark']}")
        allocation = entry.get("secondaryMetrics", {}).get("gc.alloc.rate.norm", {})
        if allocation.get("score", 0) <= 0:
            raise SystemExit(f"缺少 GC 分配指标：{entry['benchmark']}")
        displayed_score = (
            f"{entry['primaryMetric']['score']:.3f} ± "
            f"{entry['primaryMetric']['scoreError']:.3f}"
        )
        displayed_allocation = f"{allocation['score']:,.0f}"
        if report is not None and displayed_score not in report:
            raise SystemExit(f"报告中缺少 JMH 分数：{displayed_score}")
        if report is not None and displayed_allocation not in report:
            raise SystemExit(f"报告中缺少分配量分数：{displayed_allocation}")


if __name__ == "__main__":
    reports = {
        "task-2.1-baseline": BASELINE_REPORT,
        "task-2.3-final": FINAL_REPORT,
    }
    missing_result_dirs = REQUIRED_RESULT_DIRS - set(RESULT_DIRS)
    if missing_result_dirs:
        raise SystemExit(f"缺少正式结果目录：{sorted(map(str, missing_result_dirs))}")
    for result_dir in RESULT_DIRS:
        check_checksums(result_dir)
        environment = check_environment(result_dir)
        check_jmh(result_dir, environment, reports.get(result_dir.name))
    print(f"正式基准产物：{len(RESULT_DIRS)} 组检查通过")
