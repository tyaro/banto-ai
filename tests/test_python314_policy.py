"""New single-minor policy risks using synthetic journals; no native execution."""

import copy
import io
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from banto_ai import anomaly_v03_acceptance as acceptance
from banto_ai import _anomaly_v03_inventory as inventory
from banto_ai import _anomaly_v03_runtime as runtime
from tests.test_ci_shared_fixtures import SOURCE, journal
from tests.test_ci_verify_regression_journals import add_case, WINDOWS_NATIVE, WINDOWS_REASON
from tools import ci_compare_fixtures as comparison
from tools import ci_shared_fixtures as shared
from tools import ci_test_report as ci
from tools import ci_verify_python314_journal as gate

ROOT = Path(__file__).resolve().parents[1]


class Python314PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="banto-python314-policy-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.jsonl"

    def rows(self, minor="3.14"):
        rows = journal(minor)
        existing = {r["test_id"] for r in rows if r["event"] == "planned_test"}
        for test_id in sorted(gate.REQUIRED_TEST_IDS - existing):
            add_case(rows, test_id)
        return rows

    def check(self, rows, **overrides):
        self.path.write_bytes(b"".join(shared.canonical(row) + b"\n" for row in rows))
        values = {"expected_head": SOURCE["revision"],
                  "expected_workflow_sha256": SOURCE["workflow_sha256"],
                  "expected_run_id": SOURCE["github_run_id"],
                  "expected_run_attempt": SOURCE["github_run_attempt"], **overrides}
        return gate.verify(self.path, **values)

    def test_single_journal_keeps_all_required_tests_and_does_not_claim_comparison(self):
        rows = self.rows()
        add_case(rows, WINDOWS_NATIVE, "skip", WINDOWS_REASON)
        report = self.check(rows)
        self.assertEqual(report["verification_status"], "passed")
        self.assertEqual(report["required_tests_passed"], len(gate.REQUIRED_TEST_IDS))
        self.assertEqual(len(report["fixtures"]), len(shared.EXPECTED))
        self.assertEqual(report["windows_native_skips"], [WINDOWS_NATIVE])
        self.assertFalse(report["cross_python_comparison_performed"])
        self.assertFalse(report["execution_authenticated"])
        self.assertFalse(report["formal_permission"])
        self.assertEqual(report["acceptance_status"], "not_completed")
        self.assertEqual(report["raw_pin"]["bytes"], self.path.stat().st_size)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_old_or_future_minor_cannot_satisfy_new_single_journal_gate(self):
        for minor in ("3.12", "3.13", "3.15"):
            with self.subTest(minor=minor), self.assertRaisesRegex(comparison.EvidenceError, "python_mismatch"):
                self.check(self.rows(minor))

    def test_external_source_run_workflow_and_attempt_pins_remain_required(self):
        for key, value in (("expected_head", "c" * 40), ("expected_workflow_sha256", "d" * 64),
                           ("expected_run_id", "13"), ("expected_run_attempt", "2"),
                           ("expected_head", "short")):
            with self.subTest(key=key), self.assertRaises(comparison.EvidenceError):
                self.check(self.rows(), **{key: value})

    def test_missing_required_case_and_unreviewed_skip_still_fail(self):
        with self.assertRaisesRegex(comparison.EvidenceError, "required_test_missing"):
            self.check(journal("3.14"))
        rows = self.rows()
        add_case(rows, "tests.synthetic.Case.test_unreviewed", "skip", "not reviewed")
        with self.assertRaisesRegex(comparison.EvidenceError, "unexpected_linux_skip"):
            self.check(rows)

    def test_partial_duplicate_fixture_and_failure_cannot_be_completed(self):
        cases = []
        partial = self.rows(); partial.pop(); cases.append(partial)
        duplicate = self.rows()
        index = next(i for i, r in enumerate(duplicate) if r["event"] == "shared_fixture")
        duplicate.insert(index, copy.deepcopy(duplicate[index])); cases.append(duplicate)
        failed = self.rows()
        next(r for r in failed if r["event"] == "outcome")["status"] = "failure"; cases.append(failed)
        for rows in cases:
            with self.subTest(case=len(rows)), self.assertRaises(comparison.EvidenceError):
                self.check(rows)

    def test_cli_consumes_one_input_and_emits_new_verification_format(self):
        self.check(self.rows())
        args = ["--python314", str(self.path), "--expected-head", SOURCE["revision"],
                "--expected-workflow-sha256", SOURCE["workflow_sha256"],
                "--expected-run-id", SOURCE["github_run_id"],
                "--expected-run-attempt", SOURCE["github_run_attempt"]]
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(gate.main(args), 0)
        self.assertEqual(json.loads(output.getvalue())["verification_version"], "ci-python314-journal.1")
        with patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit) as raised:
            gate.main(args + ["--python312", str(self.path)])
        self.assertEqual(raised.exception.code, 2)

    def test_report_runtime_rejects_other_minors_before_discovery(self):
        for minor in (12, 14, 15):
            with self.subTest(minor=minor), \
                    patch.object(ci, "sys", SimpleNamespace(platform="linux", version_info=(3, minor, 7), version="stub")), \
                    patch.object(ci.platform, "freedesktop_os_release", return_value={"ID": "ubuntu", "VERSION_ID": "24.04"}), \
                    patch.object(ci.platform, "machine", return_value="x86_64"), \
                    patch.object(ci.platform, "python_implementation", return_value="CPython"), \
                    patch.object(ci.platform, "python_version", return_value="3.14.7"), \
                    patch.object(ci.sysconfig, "get_config_var", return_value=None), \
                    patch.dict(ci.os.environ, {"ImageOS": "ubuntu24", "ImageVersion": "stub-image"}, clear=True):
                if minor == 14:
                    self.assertEqual(ci.runtime_metadata()["python_version"], "3.14.7")
                else:
                    with self.assertRaisesRegex(RuntimeError, "CPython 3.14"):
                        ci.runtime_metadata()

    def test_minor_range_workflow_and_legacy_schema_are_consistent(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["requires-python"], ">=3.14,<3.15")
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertNotIn("3.12", workflow)
        self.assertNotIn("ci_compare_fixtures.py", workflow)
        self.assertIn("tools/ci_verify_python314_journal.py", workflow)
        legacy = json.loads((ROOT / acceptance.LEGACY_SCHEMA_PATH).read_text(encoding="utf-8"))
        self.assertEqual(legacy, acceptance.receipt_schema(version=acceptance.LEGACY_RECEIPT_VERSION))
        active = json.loads((ROOT / acceptance.SCHEMA_PATH).read_text(encoding="utf-8"))
        self.assertEqual(active, acceptance.receipt_schema())
        self.assertNotIn("linux-3.12", active["properties"]["requirements"]["properties"])

    def test_inspection_collector_rejects_python312_before_path_or_native_io(self):
        with patch.object(inventory, "sys", SimpleNamespace(dont_write_bytecode=True, version_info=(3, 12, 8))), \
                patch.object(inventory.platform, "python_implementation", return_value="CPython"), \
                patch.object(inventory.rt, "regular_path", side_effect=AssertionError("path IO reached")), \
                self.assertRaisesRegex(runtime.IntegrityError, "unsupported_runtime"):
            inventory.probe_host(ROOT)


if __name__ == "__main__":
    unittest.main()
