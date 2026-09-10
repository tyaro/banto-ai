"""Small synthetic unittest suites; no repository discovery or native controls."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools import ci_test_report as ci


class CiTestReportTests(unittest.TestCase):
    def run_sample(self, case):
        output, console = io.BytesIO(), io.StringIO()
        summary = ci.run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(case), ci.Journal(output).emit, console)
        return summary, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_all_unittest_outcomes_and_subtest_failures_are_preserved(self):
        class Sample(unittest.TestCase):
            def test_pass(self): pass
            def test_fail(self): self.fail("DUMMY_PRIVATE exception details")
            def test_error(self): raise ValueError("DUMMY_PRIVATE exception details")
            @unittest.skip("synthetic skip")
            def test_skip(self): pass
            @unittest.expectedFailure
            def test_expected(self): self.fail()
            @unittest.expectedFailure
            def test_unexpected(self): pass
            def test_subtest_fail(self):
                with self.subTest(data="DUMMY_PRIVATE parameters"): self.fail("DUMMY_PRIVATE message")
            def test_subtest_skip(self):
                with self.subTest(data="DUMMY_PRIVATE parameters"): self.skipTest("synthetic subtest skip")
        summary, rows = self.run_sample(Sample)
        self.assertEqual(summary, dict(discovered=8, tests_run=8, failures=2, errors=1, skipped=2,
                                       expected_failures=1, unexpected_successes=1, stopped=False, unittest_success=False))
        planned = {r["test_id"] for r in rows if r["event"] == "planned_test"}
        finished = [r for r in rows if r["event"] == "test_finished"]
        self.assertEqual({r["test_id"] for r in finished}, planned)
        self.assertEqual(len(finished), 8)
        self.assertTrue(all(r["outcomes"] for r in finished))
        self.assertNotIn("DUMMY_PRIVATE", json.dumps(rows))
        self.assertEqual([r["subtest_ordinal"] for r in rows if "subtest_ordinal" in r], [1])

    def test_class_setup_error_keeps_planned_tests_and_fixture_error(self):
        class Sample(unittest.TestCase):
            @classmethod
            def setUpClass(cls): raise RuntimeError("fixture failed")
            def test_one(self): pass
            def test_two(self): pass
        summary, rows = self.run_sample(Sample)
        self.assertEqual((summary["discovered"], summary["tests_run"], summary["errors"]), (2, 0, 1))
        self.assertFalse(summary["unittest_success"])
        error = next(r for r in rows if r["event"] == "outcome")
        self.assertEqual(error["status"], "error")
        self.assertIn("setUpClass", error["test_id"])
        self.assertFalse(any(r["event"] == "test_finished" for r in rows))

    def test_teardown_failure_never_becomes_a_pass(self):
        class Sample(unittest.TestCase):
            def test_one(self): pass
            def tearDown(self): raise OSError("teardown")
        summary, rows = self.run_sample(Sample)
        self.assertFalse(summary["unittest_success"])
        self.assertEqual(rows[-1]["outcomes"], ["error"])

    def test_empty_and_duplicate_suites_are_rejected_before_execution(self):
        calls = []
        class Sample(unittest.TestCase):
            def test_one(self): calls.append(1)
        for suite in (unittest.TestSuite(), unittest.TestSuite([Sample("test_one"), Sample("test_one")])):
            with self.subTest(count=suite.countTestCases()), self.assertRaises(RuntimeError):
                ci.run_suite(suite, lambda *args, **kwargs: None, io.StringIO())
        self.assertEqual(calls, [])

    def test_report_limit_preserves_only_complete_lines(self):
        output = io.BytesIO()
        journal = ci.Journal(output)
        journal.emit("first")
        first = output.getvalue()
        with patch.object(ci, "MAX_REPORT_BYTES", len(first) + 1), self.assertRaises(RuntimeError):
            journal.emit("second")
        self.assertEqual(output.getvalue(), first)
        self.assertEqual(journal.bytes_written, len(first))

    def test_windows_rejected_before_filesystem_or_test_discovery(self):
        with patch.object(ci, "sys", SimpleNamespace(platform="win32")), \
                patch.object(ci, "source_identity", side_effect=AssertionError("source inspected")), \
                patch.object(Path, "mkdir", side_effect=AssertionError("directory created")), \
                patch.object(unittest.TestLoader, "discover", side_effect=AssertionError("tests imported")), \
                self.assertRaisesRegex(RuntimeError, "Linux CI only"):
            ci.main()

    def test_linux_runtime_metadata_keeps_actual_patch_and_missing_image_digest(self):
        for minor in (12, 14):
            version = f"3.{minor}.7"
            with self.subTest(minor=minor), patch.object(ci, "sys", SimpleNamespace(
                    platform="linux", version_info=(3, minor, 7), version="CPython build details")), \
                    patch.object(ci.platform, "freedesktop_os_release", return_value={"ID": "ubuntu", "VERSION_ID": "24.04"}), \
                    patch.object(ci.platform, "machine", return_value="x86_64"), \
                    patch.object(ci.platform, "python_implementation", return_value="CPython"), \
                    patch.object(ci.platform, "python_version", return_value=version), \
                    patch.object(ci.sysconfig, "get_config_var", return_value=None), \
                    patch.dict(ci.os.environ, {"ImageOS": "ubuntu24", "ImageVersion": "hand-image", "DUMMY_PRIVATE": "never export"}, clear=True):
                result = ci.runtime_metadata()
            self.assertEqual(result["python_version"], version)
            self.assertEqual(result["runner_image_version"], "hand-image")
            self.assertIsNone(result["runner_image_digest"])
            self.assertEqual(result["runner_image_digest_status"], "not_collected")
            self.assertNotIn("DUMMY_PRIVATE", json.dumps(result))

    def test_other_linux_release_architecture_minor_and_gil_are_rejected(self):
        cases = [("26.04", "x86_64", (3, 14), 0), ("24.04", "aarch64", (3, 14), 0),
                 ("24.04", "x86_64", (3, 13), 0), ("24.04", "x86_64", (3, 14), 1)]
        for release, arch, version, gil in cases:
            with self.subTest(release=release, arch=arch, version=version, gil=gil), \
                    patch.object(ci, "sys", SimpleNamespace(platform="linux", version_info=version)), \
                    patch.object(ci.platform, "freedesktop_os_release", return_value={"ID": "ubuntu", "VERSION_ID": release}), \
                    patch.object(ci.platform, "machine", return_value=arch), \
                    patch.object(ci.platform, "python_implementation", return_value="CPython"), \
                    patch.object(ci.sysconfig, "get_config_var", return_value=gil), self.assertRaises(RuntimeError):
                ci.runtime_metadata()

    def test_source_identity_uses_clean_actual_head_and_checks_workflow_sha(self):
        with tempfile.TemporaryDirectory(prefix="banto-ci-report-test-") as temp:
            root = Path(temp)
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/ci.yml").write_text("hand workflow", encoding="utf-8")
            head = "a" * 40
            with patch.dict(ci.os.environ, {"GITHUB_SHA": head}, clear=True), \
                    patch.object(ci.subprocess, "check_output", side_effect=[(head + "\n").encode(), b""]) as git:
                result = ci.source_identity(root)
            self.assertEqual(result["revision"], head)
            self.assertEqual(len(result["workflow_sha256"]), 64)
            self.assertTrue(all(call.kwargs["env"]["GIT_NO_LAZY_FETCH"] == "1" for call in git.call_args_list))
            for dirty, github_sha in ((b" M changed.py\n", head), (b"", "b" * 40)):
                with self.subTest(dirty=bool(dirty)), patch.dict(ci.os.environ, {"GITHUB_SHA": github_sha}, clear=True), \
                        patch.object(ci.subprocess, "check_output", side_effect=[head.encode(), dirty]), self.assertRaises(RuntimeError):
                    ci.source_identity(root)

    def invoke_main(self, root, suite, identities):
        with patch.object(ci, "ROOT", root), patch.object(ci, "runtime_metadata", return_value={"fixture": True}), \
                patch.object(ci, "source_identity", side_effect=identities), \
                patch.object(unittest.TestLoader, "discover", return_value=suite), patch.object(ci.sys, "stderr", io.StringIO()):
            return ci.main()

    def test_main_success_is_unaccepted_and_report_is_never_overwritten(self):
        class Sample(unittest.TestCase):
            def test_one(self): pass
        with tempfile.TemporaryDirectory(prefix="banto-ci-report-test-") as temp:
            root = Path(temp)
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(Sample)
            self.assertEqual(self.invoke_main(root, suite, [{"revision": "a"}, {"revision": "a"}]), 0)
            raw = (root / ci.REPORT).read_bytes()
            rows = [json.loads(line) for line in raw.splitlines()]
            self.assertEqual(rows[-1]["event"], "run_finished")
            self.assertTrue(rows[-1]["unittest_success"])
            self.assertFalse(rows[-1]["formal_permission"])
            self.assertEqual(rows[-1]["acceptance_status"], "not_completed")
            with self.assertRaises(FileExistsError): self.invoke_main(root, suite, [{"revision": "a"}])
            self.assertEqual((root / ci.REPORT).read_bytes(), raw)

    def test_source_drift_returns_failure_even_after_passing_tests(self):
        class Sample(unittest.TestCase):
            def test_one(self): pass
        with tempfile.TemporaryDirectory(prefix="banto-ci-report-test-") as temp:
            root = Path(temp)
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(Sample)
            self.assertEqual(self.invoke_main(root, suite, [{"revision": "a"}, {"revision": "b"}]), 1)
            last = json.loads((root / ci.REPORT).read_bytes().splitlines()[-1])
            self.assertFalse(last["source_unchanged"])

    def test_requested_stop_with_unexecuted_tests_is_failure(self):
        calls = []
        class Sample(unittest.TestCase):
            def test_a_stop(self): self._outcome.result.stop()
            def test_b_not_run(self): calls.append(1)
        with tempfile.TemporaryDirectory(prefix="banto-ci-report-test-") as temp:
            root = Path(temp)
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(Sample)
            self.assertEqual(self.invoke_main(root, suite, [{"revision": "a"}, {"revision": "a"}]), 1)
            rows = [json.loads(line) for line in (root / ci.REPORT).read_bytes().splitlines()]
            self.assertEqual((rows[-1]["discovered"], rows[-1]["tests_run"]), (2, 1))
            self.assertTrue(rows[-1]["stopped"])
            self.assertFalse(rows[-1]["unittest_success"])
            self.assertEqual(sum(r["event"] == "planned_test" for r in rows), 2)
            self.assertEqual(calls, [])

    def test_test_failure_returns_nonzero_with_complete_failure_summary(self):
        class Sample(unittest.TestCase):
            def test_one(self): self.fail("synthetic")
        with tempfile.TemporaryDirectory(prefix="banto-ci-report-test-") as temp:
            root = Path(temp)
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(Sample)
            self.assertEqual(self.invoke_main(root, suite, [{"revision": "a"}, {"revision": "a"}]), 1)
            last = json.loads((root / ci.REPORT).read_bytes().splitlines()[-1])
            self.assertEqual((last["event"], last["failures"]), ("run_finished", 1))
            self.assertFalse(last["unittest_success"])

    def test_interruption_leaves_no_completed_summary(self):
        class Sample(unittest.TestCase):
            def test_one(self): raise KeyboardInterrupt()
        with tempfile.TemporaryDirectory(prefix="banto-ci-report-test-") as temp:
            root = Path(temp)
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(Sample)
            with self.assertRaises(KeyboardInterrupt): self.invoke_main(root, suite, [{"revision": "a"}])
            rows = [json.loads(line) for line in (root / ci.REPORT).read_bytes().splitlines()]
            self.assertEqual(rows[0]["event"], "run_started")
            self.assertFalse(any(r["event"] == "run_finished" for r in rows))


if __name__ == "__main__":
    unittest.main()
