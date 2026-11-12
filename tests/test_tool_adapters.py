import json
from pathlib import Path
import tempfile
import unittest

from tools.adapters import pip_audit


ROOT = Path(__file__).resolve().parent.parent


class ToolAdapterTests(unittest.TestCase):
    def test_pip_audit_vulnerability_and_clean_dependency(self):
        findings = pip_audit(ROOT / "tests" / "fixtures" / "pip_audit.json")
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["id"], "pip_audit_PYSEC-2026-1")
        self.assertEqual(finding["severity"], "medium")
        self.assertIn("example-vulnerable 1.0.0", finding["detail"])
        self.assertEqual(
            set(finding),
            {"id", "severity", "layer", "title", "detail", "evidence_seq",
             "call_id", "source", "evidence_file"},
        )
        self.assertIn(finding["severity"], {"high", "medium", "low", "info"})
        self.assertEqual(finding["evidence_seq"], [])
        self.assertIsNone(finding["call_id"])

    def test_empty_and_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.json"
            empty.write_text("", encoding="utf-8")
            self.assertEqual(pip_audit(empty), [])
            self.assertEqual(pip_audit(Path(tmp) / "missing.json"), [])

    def test_malformed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{", encoding="utf-8")
            self.assertEqual(pip_audit(path), [])


if __name__ == "__main__":
    unittest.main()
