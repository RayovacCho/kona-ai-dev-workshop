import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "analyze-chinese-jmh.py"
SPEC = importlib.util.spec_from_file_location("analyze_chinese_jmh", SCRIPT)
analyzer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(analyzer)


class ChineseJmhAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "result.json"

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def entry(operation, payload, score=2.0, allocation=200.0):
        return {
            "benchmark": f"example.Benchmark.{operation}",
            "params": {"payloadType": payload},
            "primaryMetric": {"score": score, "scoreUnit": "us/op"},
            "secondaryMetrics": {
                "gc.alloc.rate.norm": {"score": allocation, "scoreUnit": "B/op"}
            },
        }

    def complete_results(self):
        entries = []
        for english, chinese, _ in analyzer.PAYLOAD_PAIRS:
            for operation in analyzer.OPERATION_LABELS:
                entries.append(self.entry(operation, english, 2.0, 200.0))
                entries.append(self.entry(operation, chinese, 2.2, 220.0))
        return entries

    def test_renders_chinese_comparison(self):
        self.path.write_text(json.dumps(self.complete_results()), encoding="utf-8")
        output = analyzer.render_section("测试", self.path)
        self.assertIn("中文耗时变化", output)
        self.assertIn("+10.00%", output)
        self.assertIn("100 元素对象图", output)

    def test_rejects_missing_pair(self):
        entries = self.complete_results()
        entries.pop()
        self.path.write_text(json.dumps(entries), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "缺少中文对照场景"):
            list(analyzer.comparisons(analyzer.load_results(self.path)))

    def test_rejects_wrong_unit(self):
        entries = self.complete_results()
        entries[0]["primaryMetric"]["scoreUnit"] = "ns/op"
        self.path.write_text(json.dumps(entries), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "指标单位"):
            analyzer.load_results(self.path)


if __name__ == "__main__":
    unittest.main()
