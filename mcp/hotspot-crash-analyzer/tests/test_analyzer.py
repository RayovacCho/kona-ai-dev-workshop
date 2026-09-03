import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(PROJECT))

from analyzer import (
    AnalysisError,
    analyze_file,
    build_jql,
    get_jbs_issue,
    parse_log_file,
    parse_log_text,
    search_jbs,
)


class AnalyzerTest(unittest.TestCase):
    def test_controlled_assertion(self):
        result = parse_log_file(str(FIXTURES / "hs_err_controlled_assert.log"))
        self.assertEqual("assertion", result["error"]["kind"])
        self.assertIn("test assert", result["error"]["message"])
        self.assertTrue(result["controlled_crash"])
        self.assertTrue(result["direct_cause"]["intentional"])
        self.assertEqual("high", result["direct_cause"]["confidence"])

    def test_controlled_sigsegv(self):
        result = parse_log_file(str(FIXTURES / "hs_err_controlled_sigsegv.log"))
        self.assertEqual("SIGSEGV", result["error"]["signal"])
        self.assertIn("VMError::controlled_crash", result["problematic_frame"]["symbol"])
        self.assertEqual("V", result["problematic_frame"]["kind"])

    def test_controlled_sigfpe_uses_exact_jbs_background_query(self):
        result = analyze_file(str(FIXTURES / "hs_err_controlled_sigfpe.log"))
        self.assertEqual("__pthread_kill+0x8", result["problematic_frame"]["symbol"])
        self.assertEqual(["VMError::controlled_crash"], result["jbs_search_terms"])
        self.assertIn("VMError%3A%3Acontrolled_crash", result["jbs_search_url"])
        self.assertNotIn("__pthread_kill", result["jbs_search_url"])
        self.assertFalse(result["jbs"]["searched"])
        self.assertEqual(result["jbs_search_url"], result["jbs"]["browse_url"])
        self.assertIn("历史背景", result["jbs"]["reason"])

    def test_rejects_non_hs_err(self):
        with self.assertRaises(AnalysisError):
            parse_log_text("ordinary Java exception\n")

    def test_non_controlled_native_crash_searches_jbs(self):
        candidate = {
            "query": "crash_in_native_library",
            "issues": [{"key": "JDK-1234567"}],
            "total": 1,
        }
        with mock.patch("analyzer.search_jbs", return_value=candidate) as search:
            result = analyze_file(str(FIXTURES / "hs_err_native_crash.log"))
        self.assertFalse(result["controlled_crash"])
        self.assertEqual("C", result["problematic_frame"]["kind"])
        self.assertIn("crash_in_native_library", result["direct_cause"]["summary"])
        self.assertTrue(result["jbs"]["searched"])
        self.assertEqual("JDK-1234567", result["jbs"]["issues"][0]["key"])
        search.assert_called_once()

    def test_jql_escapes_input(self):
        jql = build_jql('foo "bar" \\ baz')
        self.assertIn('foo \\"bar\\" \\\\ baz', jql)

    @staticmethod
    def _response(payload):
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
        return response

    @mock.patch("analyzer.urllib.request.urlopen")
    def test_search_jbs_parses_candidate(self, urlopen):
        urlopen.return_value = self._response(
            {
                "total": 1,
                "issues": [
                    {
                        "key": "JDK-1234567",
                        "fields": {
                            "summary": "Native crash",
                            "status": {"name": "Resolved"},
                            "resolution": {"name": "Fixed"},
                            "versions": [{"name": "25"}],
                            "fixVersions": [{"name": "25.0.1"}],
                            "components": [{"name": "hotspot"}],
                            "updated": "2026-08-30T00:00:00Z",
                        },
                    }
                ],
            }
        )
        result = search_jbs("crash_in_native_library", max_results=1)
        self.assertEqual(1, result["total"])
        self.assertEqual("JDK-1234567", result["issues"][0]["key"])
        self.assertEqual(["25.0.1"], result["issues"][0]["fix_versions"])

    @mock.patch("analyzer.urllib.request.urlopen")
    def test_get_jbs_issue_parses_metadata(self, urlopen):
        urlopen.return_value = self._response(
            {
                "fields": {
                    "summary": "Native crash",
                    "status": {"name": "Resolved"},
                    "resolution": {"name": "Fixed"},
                    "description": "Crash description",
                    "versions": [{"name": "25"}],
                    "fixVersions": [{"name": "25.0.1"}],
                    "components": [{"name": "hotspot"}],
                    "labels": ["crash"],
                    "issuelinks": [],
                    "updated": "2026-08-30T00:00:00Z",
                }
            }
        )
        issue = get_jbs_issue("jdk-1234567")
        self.assertEqual("JDK-1234567", issue["key"])
        self.assertEqual("Fixed", issue["resolution"])

    def test_mcp_stdio(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "analyze_hotspot_crash",
                    "arguments": {
                        "path": str(FIXTURES / "hs_err_controlled_sigfpe.log"),
                        "include_jbs": False,
                    },
                },
            },
        ]
        proc = subprocess.run(
            [sys.executable, str(PROJECT / "server.py")],
            input="".join(json.dumps(item) + "\n" for item in messages),
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        responses = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual("hotspot-crash-analyzer", responses[0]["result"]["serverInfo"]["name"])
        self.assertEqual(4, len(responses[1]["result"]["tools"]))
        analysis = responses[2]["result"]["structuredContent"]
        self.assertEqual("SIGFPE", analysis["error"]["signal"])
        self.assertTrue(analysis["direct_cause"]["intentional"])


if __name__ == "__main__":
    unittest.main()
