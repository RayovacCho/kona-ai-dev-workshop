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

    def test_requires_schema_two_for_current_formal_results(self):
        result_dir = next(iter(check_results.CURRENT_PROVENANCE_RESULT_DIRS))
        with self.assertRaises(SystemExit):
            check_results.check_required_provenance(result_dir, {})
        check_results.check_required_provenance(
            result_dir, {"environment_schema": "2"}
        )

    def test_allows_legacy_intermediate_results_without_schema_two(self):
        result_dir = check_results.RESULT_ROOT / "task-2.3-round1"
        check_results.check_required_provenance(result_dir, {})


if __name__ == "__main__":
    unittest.main()
