import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from csvguard.cli import main
from csvguard.core import load_contract, validate


class CsvGuardTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        self.contract = load_contract(self.root / "sample/orders.schema.json")

    def test_valid_jsonl_passes(self):
        report = validate(self.root / "sample/orders.jsonl", self.contract, "jsonl")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["input"]["rows"], 2)

    def test_csv_reports_multiple_contract_violations(self):
        report = validate(self.root / "sample/orders.csv", self.contract)
        codes = {item["code"] for item in report["violations"]}
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["input"]["rows"], 4)
        self.assertGreaterEqual(report["summary"]["errors"], 4)
        self.assertTrue({"DUPLICATE_VALUE", "MIN_VALUE", "ENUM_VALUE", "TYPE_MISMATCH"}.issubset(codes))

    def test_unknown_fields_are_rejected(self):
        contract = {"fields": [{"name": "id", "type": "string", "required": True}]}
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data.csv"
            data.write_text("id,extra\nA,1\n", encoding="utf-8")
            report = validate(data, contract)
        self.assertEqual(report["violations"][0]["code"], "UNKNOWN_FIELD")

    def test_json_report_and_exit_code_are_cli_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            code = main([str(self.root / "sample/orders.csv"), "--contract", str(self.root / "sample/orders.schema.json"), "--report", "json", "--output", str(output)])
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(payload["tool"], "csvguard")
        self.assertEqual(payload["status"], "fail")
        self.assertIn("violations", payload)

    def test_limit_preserves_total_count(self):
        report = validate(self.root / "sample/orders.csv", self.contract, limit=1)
        self.assertEqual(len(report["violations"]), 1)
        self.assertGreater(report["summary"]["errors"], 1)
        self.assertTrue(report["summary"]["truncated"])

    def test_invalid_contract_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            contract_path = Path(directory) / "bad.json"
            contract_path.write_text('{"fields": [{"name": "id", "type": "made-up"}]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_contract(contract_path)


if __name__ == "__main__":
    unittest.main()
