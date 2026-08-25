#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = ROOT / "results" / "task-2.1-baseline"
REQUIRED_ENV = {
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_checksums() -> None:
    checksum_file = RESULT_DIR / "SHA256SUMS"
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        expected, name = line.split(maxsplit=1)
        path = RESULT_DIR / name.lstrip("*")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"校验和不匹配：{path}")


def check_environment() -> None:
    values = {}
    for line in (RESULT_DIR / "environment.txt").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    missing = REQUIRED_ENV - values.keys()
    if missing:
        raise SystemExit(f"缺少环境字段：{sorted(missing)}")
    if values["kona_worktree"] != "clean":
        raise SystemExit("正式基准并非由无未提交修改的 Kona 工作树生成")
    if values["benchmark_source_sha256"] != sha256(BENCHMARK_SOURCE):
        raise SystemExit("基准源码与正式基准记录不一致")
    if values["dependency_lock_sha256"] != sha256(DEPENDENCY_LOCK):
        raise SystemExit("依赖锁定文件与正式基准记录不一致")


def check_jmh() -> None:
    with (RESULT_DIR / "jmh-result.json").open(encoding="utf-8") as stream:
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
    report = BASELINE_REPORT.read_text(encoding="utf-8")
    for entry in results:
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
        if displayed_score not in report:
            raise SystemExit(f"报告中缺少 JMH 分数：{displayed_score}")
        if displayed_allocation not in report:
            raise SystemExit(f"报告中缺少分配量分数：{displayed_allocation}")


if __name__ == "__main__":
    check_checksums()
    check_environment()
    check_jmh()
    print("正式基准产物：检查通过")
