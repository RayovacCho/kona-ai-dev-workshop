import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "check-results.py"
SPEC = importlib.util.spec_from_file_location("check_results", SCRIPT)
check_results = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_results)


class ChecksumManifestTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.result_dir = Path(self.temporary.name)
        for name, content in {
            "jmh-result.json": b"[]\n",
            "environment.txt": b"os=test\n",
        }.items():
            (self.result_dir / name).write_bytes(content)

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(self, names):
        lines = []
        for name in names:
            digest = hashlib.sha256((self.result_dir / name).read_bytes()).hexdigest()
            lines.append(f"{digest}  {name}")
        (self.result_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    def test_accepts_exact_required_files(self):
        self.write_manifest(["jmh-result.json", "environment.txt"])
        check_results.check_checksums(self.result_dir)

    def test_rejects_empty_manifest(self):
        (self.result_dir / "SHA256SUMS").write_text("")
        with self.assertRaises(SystemExit):
            check_results.check_checksums(self.result_dir)

    def test_rejects_incomplete_manifest(self):
        self.write_manifest(["jmh-result.json"])
        with self.assertRaises(SystemExit):
            check_results.check_checksums(self.result_dir)

    def test_requires_schema_two_for_current_results_and_three_for_new_results(self):
        result_dirs = (
            check_results.RESULT_ROOT / "task-2.1-baseline",
            check_results.RESULT_ROOT / "task-2.3-final",
        )
        for result_dir in result_dirs:
            with self.subTest(result_dir=result_dir):
                with self.assertRaises(SystemExit):
                    check_results.check_required_provenance(result_dir, {})
                check_results.check_required_provenance(
                    result_dir, {"environment_schema": "2"}
                )
        new_result = check_results.RESULT_ROOT / "reproductions" / "new-run"
        with self.assertRaises(SystemExit):
            check_results.check_required_provenance(
                new_result, {"environment_schema": "2"}
            )
        check_results.check_required_provenance(
            new_result, {"environment_schema": "3"}
        )

    def test_allows_legacy_intermediate_results_without_schema_two(self):
        result_dir = check_results.RESULT_ROOT / "task-2.3-round1"
        check_results.check_required_provenance(result_dir, {})

    def test_rejects_duplicate_environment_fields(self):
        environment = self.result_dir / "environment.txt"
        environment.write_text("os=test\nos=changed\n")
        with self.assertRaises(SystemExit):
            check_results.read_environment(environment)

    def test_rejects_non_comparable_final_environment(self):
        baseline = check_results.RESULT_ROOT / "task-2.1-baseline"
        final = check_results.RESULT_ROOT / "task-2.3-final"
        environments = {
            baseline: {"os": "test", "architecture": "arm64", "cpu": "cpu", "memory": "16 GB"},
            final: {"os": "changed", "architecture": "arm64", "cpu": "cpu", "memory": "16 GB"},
        }
        with self.assertRaises(SystemExit):
            check_results.check_comparable_environments(environments)

    def test_accepts_complete_three_by_five_raw_data(self):
        metric = {"rawData": [[1.0] * 5 for _ in range(3)]}
        check_results.check_raw_data(metric, "benchmark")

    def test_rejects_incomplete_raw_data(self):
        metric = {"rawData": [[1.0] * 5 for _ in range(2)]}
        with self.assertRaises(SystemExit):
            check_results.check_raw_data(metric, "benchmark")

    def test_rejects_non_finite_raw_data(self):
        metric = {"rawData": [[1.0] * 5 for _ in range(3)]}
        metric["rawData"][1][2] = float("nan")
        with self.assertRaises(SystemExit):
            check_results.check_raw_data(metric, "benchmark")


if __name__ == "__main__":
    unittest.main()
