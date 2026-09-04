import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "check-crash-logs.py"
SPEC = importlib.util.spec_from_file_location("check_crash_logs", SCRIPT)
check_crash_logs = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_crash_logs)


class CrashLogManifestTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temporary.name)
        self.log = self.log_dir / "sample.log"
        self.log.write_bytes(b"sample\n")
        self.expected = {"sample.log": {}}

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(self, lines):
        (self.log_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    def test_accepts_exact_manifest(self):
        digest = hashlib.sha256(self.log.read_bytes()).hexdigest()
        self.write_manifest([f"{digest}  sample.log"])
        check_crash_logs.check_manifest(self.log_dir, self.expected)

    def test_rejects_unexpected_file(self):
        digest = hashlib.sha256(self.log.read_bytes()).hexdigest()
        self.write_manifest([f"{digest}  sample.log", f"{digest}  duplicate.log"])
        with self.assertRaises(SystemExit):
            check_crash_logs.check_manifest(self.log_dir, self.expected)

    def test_rejects_changed_log(self):
        self.write_manifest([f"{'0' * 64}  sample.log"])
        with self.assertRaises(SystemExit):
            check_crash_logs.check_manifest(self.log_dir, self.expected)

    def test_rejects_path_traversal(self):
        self.write_manifest([f"{'0' * 64}  ../sample.log"])
        with self.assertRaises(SystemExit):
            check_crash_logs.check_manifest(self.log_dir, self.expected)

    def test_accepts_non_sensitive_environment_names(self):
        text = "Environment Variables:\nPATH=/usr/bin\nLANG=zh_CN.UTF-8\n\nSystem:\n"
        check_crash_logs.check_environment_privacy(text, self.log)

    def test_rejects_sensitive_environment_name_without_exposing_value(self):
        text = "Environment Variables:\nSERVICE_TOKEN=do-not-print\n\nSystem:\n"
        with self.assertRaises(SystemExit) as raised:
            check_crash_logs.check_environment_privacy(text, self.log)
        self.assertNotIn("do-not-print", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
