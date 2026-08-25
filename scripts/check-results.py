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
            raise SystemExit(f"checksum mismatch: {path}")


def check_environment() -> None:
    values = {}
    for line in (RESULT_DIR / "environment.txt").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    missing = REQUIRED_ENV - values.keys()
    if missing:
        raise SystemExit(f"environment fields missing: {sorted(missing)}")
    if values["kona_worktree"] != "clean":
        raise SystemExit("formal baseline was not produced from a clean Kona worktree")
    if values["benchmark_source_sha256"] != sha256(BENCHMARK_SOURCE):
        raise SystemExit("benchmark source differs from the formal baseline")
    if values["dependency_lock_sha256"] != sha256(DEPENDENCY_LOCK):
        raise SystemExit("dependency lock differs from the formal baseline")


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
        raise SystemExit(f"unexpected JMH result matrix: {sorted(actual)}")
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
                raise SystemExit(f"unexpected JMH configuration {key}: {entry.get(key)}")
        if entry["primaryMetric"].get("scoreUnit") != "us/op":
            raise SystemExit(f"unexpected score unit: {entry['benchmark']}")
        if entry["primaryMetric"]["score"] <= 0:
            raise SystemExit(f"invalid primary score: {entry['benchmark']}")
        allocation = entry.get("secondaryMetrics", {}).get("gc.alloc.rate.norm", {})
        if allocation.get("score", 0) <= 0:
            raise SystemExit(f"missing GC allocation metric: {entry['benchmark']}")
        displayed_score = (
            f"{entry['primaryMetric']['score']:.3f} ± "
            f"{entry['primaryMetric']['scoreError']:.3f}"
        )
        displayed_allocation = f"{allocation['score']:,.0f}"
        if displayed_score not in report:
            raise SystemExit(f"JMH score missing from report: {displayed_score}")
        if displayed_allocation not in report:
            raise SystemExit(f"allocation score missing from report: {displayed_allocation}")


if __name__ == "__main__":
    check_checksums()
    check_environment()
    check_jmh()
    print("Formal baseline artifacts: OK")
