"""Synthetic saved-journal attacks; no suite discovery or native execution."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_ci_shared_fixtures import SOURCE, journal, payload
from tools import ci_compare_fixtures as comparison
from tools import ci_shared_fixtures as shared
from tools import ci_verify_regression_journals as verify


REQUIRED_INVENTORY = verify.REQUIRED_TEST_IDS
MANDATORY = "tests.test_contract.CommonTests.test_required"
WINDOWS_NATIVE = "tests.test_anomaly_v03_windows.NativeWindowsControls.test_held_identity_protected_acl_and_success_cleanup"
WINDOWS_REASON = "Windows-only native control; NOT acceptance on Linux"
NEW_WINDOWS_NATIVE = (
    "tests.test_anomaly_v03_preformal_five_role_job_owner.FiveRoleJobNativeProbeTests."
    "test_six_job_members_complete_and_owner_accepts"
)
OPTIONAL_CAPSTONE = (
    "tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests."
    "test_instruction_operands_are_not_published"
)
OPTIONAL_TOTO = (
    "tests.test_toto2_docs.Toto2DocumentationTests."
    "test_controlled_artifacts_are_verified_when_available"
)


def add_case(rows, test_id, status="pass", reason=None):
    planned_end = next(i for i, row in enumerate(rows) if row["event"] == "test_started")
    rows.insert(planned_end, {"event": "planned_test", "test_id": test_id})
    outcome = {"event": "outcome", "test_id": test_id, "status": status}
    if status == "skip":
        outcome.update(reason=reason, subtest=False)
    rows[-1:-1] = [
        {"event": "test_started", "test_id": test_id},
        outcome,
        {"event": "test_finished", "test_id": test_id, "outcomes": [status], "elapsed_seconds": 0.0},
    ]
    rows[-1]["discovered"] += 1
    rows[-1]["tests_run"] += 1
    if status == "skip":
        rows[-1]["skipped"] += 1


class RegressionJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="banto-ci-verify-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        required = patch.object(verify, "REQUIRED_TEST_IDS", frozenset({MANDATORY}))
        required.start()
        self.addCleanup(required.stop)

    def rows(self, mandatory_status="pass"):
        result = {minor: journal(minor) for minor in comparison.MINORS}
        for rows in result.values():
            add_case(rows, MANDATORY, mandatory_status,
                     "not a native test" if mandatory_status == "skip" else None)
        return result

    def pair(self, rows):
        paths = {}
        for minor in comparison.MINORS:
            path = self.root / ("python" + minor + ".jsonl")
            path.write_bytes(b"".join(shared.canonical(row) + b"\n" for row in rows[minor]))
            paths[minor] = path
        return paths

    def check(self, rows, head=SOURCE["revision"], workflow=SOURCE["workflow_sha256"],
              run_id=SOURCE["github_run_id"], attempt=SOURCE["github_run_attempt"]):
        return verify.verify(self.pair(rows), head, workflow, run_id, attempt)

    def test_matching_journals_pass_as_read_only_regression_evidence(self):
        rows = self.rows()
        for item in rows.values():
            add_case(item, WINDOWS_NATIVE, "skip", WINDOWS_REASON)
            add_case(item, NEW_WINDOWS_NATIVE, "skip", "Windows native Job probe")
        paths = self.pair(rows)
        before = {path: path.read_bytes() for path in paths.values()}
        result = verify.verify(paths, SOURCE["revision"], SOURCE["workflow_sha256"],
                               SOURCE["github_run_id"], SOURCE["github_run_attempt"])
        self.assertEqual(result["verification_status"], "passed")
        self.assertEqual(result["shared_fixture_comparison"], "matched")
        self.assertEqual(result["acceptance_status"], "not_completed")
        self.assertFalse(result["formal_permission"])
        self.assertEqual(result["runner_image_digest_status"], "not_collected")
        self.assertFalse(result["execution_authenticated"])
        self.assertIn("saved Ubuntu unittest journals only", result["scope"])
        self.assertEqual(result["jobs"]["3.12"]["windows_native_skips"],
                         sorted([WINDOWS_NATIVE, NEW_WINDOWS_NATIVE]))
        self.assertEqual(result["jobs"]["3.12"]["non_s4_optional_skips"], [])
        self.assertEqual({path: path.read_bytes() for path in paths.values()}, before)
        self.assertEqual(set(self.root.iterdir()), set(paths.values()))

    def test_missing_or_identically_skipped_required_test_fails(self):
        with self.subTest(case="missing"), self.assertRaisesRegex(comparison.EvidenceError, "required_test_missing"):
            self.check({minor: journal(minor) for minor in comparison.MINORS})
        with self.subTest(case="both_skip"), self.assertRaisesRegex(comparison.EvidenceError, "required_test_not_passed"):
            self.check(self.rows("skip"))

    def test_required_windows_allowlist_id_still_cannot_skip(self):
        rows = self.rows()
        for item in rows.values():
            add_case(item, WINDOWS_NATIVE, "skip", WINDOWS_REASON)
        with patch.object(verify, "REQUIRED_TEST_IDS", frozenset({MANDATORY, WINDOWS_NATIVE})), \
                self.assertRaisesRegex(comparison.EvidenceError, "required_test_not_passed"):
            self.check(rows)

    def test_identical_unrelated_skip_and_wrong_native_reason_fail(self):
        for test_id, reason in (
            ("tests.test_other.OtherTests.test_optional", "optional artifact missing"),
            (WINDOWS_NATIVE, "optional artifact missing"),
            ("tests.test_anomaly_v03_windows.NativeWindowsControls.test_future", WINDOWS_REASON),
        ):
            rows = self.rows()
            for item in rows.values():
                add_case(item, test_id, "skip", reason)
            with self.subTest(test_id=test_id, reason=reason), \
                    self.assertRaisesRegex(comparison.EvidenceError, "unexpected_linux_skip"):
                self.check(rows)

    def test_known_non_s4_optional_skips_are_separate_and_exact(self):
        rows = self.rows()
        for item in rows.values():
            add_case(item, OPTIONAL_CAPSTONE, "skip",
                     "optional offline-analysis extra is not installed; not native acceptance")
            add_case(item, OPTIONAL_TOTO, "skip", "controlled Toto artifact unavailable")
        result = self.check(rows)
        self.assertEqual(result["jobs"]["3.12"]["windows_native_skips"], [])
        self.assertEqual(result["jobs"]["3.12"]["non_s4_optional_skips"],
                         sorted([OPTIONAL_CAPSTONE, OPTIONAL_TOTO]))
        for test_id, reason in ((OPTIONAL_CAPSTONE, "wrong optional reason"),
                                ("tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_future",
                                 "optional offline-analysis extra is not installed; not native acceptance")):
            rows = self.rows()
            for item in rows.values():
                add_case(item, test_id, "skip", reason)
            with self.subTest(test_id=test_id), \
                    self.assertRaisesRegex(comparison.EvidenceError, "unexpected_linux_skip"):
                self.check(rows)
        with patch.object(verify, "REQUIRED_TEST_IDS", frozenset({MANDATORY, OPTIONAL_TOTO})), \
                self.assertRaisesRegex(comparison.EvidenceError, "required_test_not_passed"):
            self.check(self.rows_with_skip(OPTIONAL_TOTO, "controlled Toto artifact unavailable"))

    def rows_with_skip(self, test_id, reason):
        rows = self.rows()
        for item in rows.values():
            add_case(item, test_id, "skip", reason)
        return rows

    def test_required_ids_exist_as_exact_unittest_cases(self):
        def cases(suite):
            for item in suite:
                if isinstance(item, unittest.TestSuite):
                    yield from cases(item)
                else:
                    yield item
        suite = unittest.defaultTestLoader.loadTestsFromNames(sorted(REQUIRED_INVENTORY))
        self.assertEqual([case.id() for case in cases(suite)], sorted(REQUIRED_INVENTORY))
        optional = verify.OPTIONAL_SKIP_IDS | verify.OPTIONAL_SKIP_TESTS.keys()
        suite = unittest.defaultTestLoader.loadTestsFromNames(sorted(optional))
        self.assertEqual([case.id() for case in cases(suite)], sorted(optional))
        self.assertFalse(REQUIRED_INVENTORY & optional)

    def test_external_head_workflow_and_shared_fixture_mismatch_fail(self):
        for field, value in (("head", "c" * 40), ("workflow", "d" * 64),
                             ("run_id", "13"), ("attempt", "2")):
            with self.subTest(field=field), self.assertRaisesRegex(comparison.EvidenceError, "external_source_pin_mismatch"):
                self.check(self.rows(), **{field: value})
        for field, value in (("run_id", "0"), ("attempt", "bad")):
            with self.subTest(field=field), self.assertRaisesRegex(comparison.EvidenceError,
                                                                   "expected_run_identity_format"):
                self.check(self.rows(), **{field: value})
        rows = self.rows()
        fixture = next(row for row in rows["3.14"] if row.get("fixture_id") == "Q1")
        payload(fixture, {"different": True})
        with self.assertRaisesRegex(comparison.EvidenceError, "shared_fixture_mismatch"):
            self.check(rows)

    def test_failure_partial_report_and_cross_job_source_drift_fail(self):
        rows = self.rows()
        outcome = next(row for row in rows["3.14"] if row.get("test_id") == MANDATORY and row["event"] == "outcome")
        outcome["status"] = "failure"
        with self.assertRaisesRegex(comparison.EvidenceError, "test_not_successful"):
            self.check(rows)
        rows = self.rows()
        rows["3.14"].pop()
        with self.assertRaises(comparison.EvidenceError):
            self.check(rows)
        rows = self.rows()
        rows["3.14"][0]["source"]["revision"] = "c" * 40
        with self.assertRaisesRegex(comparison.EvidenceError, "source_mismatch"):
            self.check(rows)

    def test_cli_returns_failure_without_creating_artifact(self):
        paths = self.pair(self.rows())
        args = ["--python312", str(paths["3.12"]), "--python314", str(paths["3.14"]),
                "--expected-head", SOURCE["revision"],
                "--expected-workflow-sha256", SOURCE["workflow_sha256"],
                "--expected-run-id", SOURCE["github_run_id"],
                "--expected-run-attempt", SOURCE["github_run_attempt"]]
        with patch.object(verify.sys, "stdout", io.StringIO()) as stdout:
            self.assertEqual(verify.main(args), 0)
        self.assertEqual(json.loads(stdout.getvalue())["verification_status"], "passed")
        with patch.object(verify.sys, "stderr", io.StringIO()) as stderr:
            self.assertEqual(verify.main(args[:-1] + ["2"]), 1)
        self.assertIn("external_source_pin_mismatch", stderr.getvalue())
        self.assertEqual(set(self.root.iterdir()), set(paths.values()))


if __name__ == "__main__":
    unittest.main()
