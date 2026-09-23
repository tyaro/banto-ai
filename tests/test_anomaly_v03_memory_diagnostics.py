"""Small diagnostic failure cases; no numerical evaluation or allocation stress."""
import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.evaluator import anomaly_v03_memory_diagnostics as diagnostics
from tests import test_anomaly_v03_budgeted_run as budget_fixtures


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(temporary) / "events.jsonl"
        self.memory = {"commit_total_bytes": 1024, "commit_limit_bytes": 4096, "pagefiles": []}
        self.log = diagnostics.Diagnostics(self.path, sample_memory=lambda: self.memory)
        self.addCleanup(self.log.close)
        self.records = [{"chunk_index": 80, "attempt": 1, "sequence": 243, "status": "verified_complete"}]

    def rows(self):
        return [json.loads(line) for line in self.path.read_text().splitlines()]

    def test_error_identity_selection_frames_and_restore(self):
        primary = MemoryError("injected")

        class Controller:
            def _verify(self, records, pins, digest):
                raise primary

        original = Controller._verify
        with self.assertRaises(MemoryError) as caught:
            with self.log.observe_controller(Controller):
                Controller()._verify(self.records, {}, "digest")
        self.assertIs(caught.exception, primary)
        self.assertIs(Controller._verify, original)
        self.assertIsNone(self.log.active_chunk)
        rows = self.rows()
        self.assertEqual([row["event"] for row in rows], ["audit_begin", "exception", "exception_resources"])
        trace = rows[1]
        self.assertEqual(trace["chunk_at_failure"], self.records[0])
        frames = trace["exception_chain"][0]["frames"]
        self.assertEqual(frames[-1]["function"], "_verify")
        self.assertGreater(frames[-1]["line"], 0)
        self.assertEqual(set(frames[-1]), {"file", "function", "line"})
        self.assertEqual(rows[2]["memory"], self.memory)

    def test_replacement_instances_delegate_original_arguments_and_result(self):
        result, calls = object(), []

        class Controller:
            def _verify(controller, records, pins, digest):
                calls.append((controller, records, pins, digest))
                return result

        discarded = Controller()
        original, pins = Controller._verify, {"expected_record_count": 243}
        with self.log.observe_controller(Controller):
            fresh = Controller()
            self.assertIs(fresh._verify(self.records, pins, "digest"), result)
        self.assertIs(calls[0][0], fresh)
        self.assertIsNot(calls[0][0], discarded)
        self.assertIs(calls[0][1], self.records)
        self.assertIs(calls[0][2], pins)
        self.assertIs(Controller._verify, original)
        self.assertEqual([row["event"] for row in self.rows()], ["audit_begin", "audit_end"])

    def test_failed_memory_observation_preserves_trace_and_primary(self):
        self.log.sample_memory = Mock(side_effect=MemoryError("sampler allocation failed"))
        primary = RuntimeError("audit failed")

        class Controller:
            def _verify(self, *args):
                raise primary

        with self.log.observe_controller(Controller), self.assertRaises(RuntimeError) as caught:
            Controller()._verify(self.records, {}, "digest")
        self.assertIs(caught.exception, primary)
        self.assertEqual(self.log.errors, 2)
        self.assertEqual([row["event"] for row in self.rows()], ["observation_error", "exception", "observation_error"])

    def test_disk_write_failure_does_not_mask_error_or_retry_corrupt_stream(self):
        primary = MemoryError("original")

        class Controller:
            def _verify(self, *args):
                raise primary

        with patch.object(self.log._stream, "write", side_effect=OSError("disk full")) as write:
            with self.log.observe_controller(Controller), self.assertRaises(MemoryError) as caught:
                Controller()._verify(self.records, {}, "digest")
        self.assertIs(caught.exception, primary)
        self.assertEqual(write.call_count, 1)
        self.assertTrue(self.log.disabled)
        self.assertGreater(self.log.dropped, 0)

    def test_existing_file_is_not_reused(self):
        self.assertTrue(self.log.sample())
        raw = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            diagnostics.Diagnostics(self.path)
        self.assertEqual(self.path.read_bytes(), raw)

    def test_log_cap_is_visible_without_changing_operation_result(self):
        self.log.max_bytes = 1
        result = object()

        class Controller:
            def _verify(self, *args):
                return result

        with self.log.observe_controller(Controller):
            self.assertIs(Controller()._verify(self.records, {}, "digest"), result)
        self.assertEqual(self.path.stat().st_size, 0)
        self.assertEqual(self.log.dropped, 2)

    def test_chained_exceptions_keep_location_without_unbounded_chain(self):
        def fail():
            try:
                raise MemoryError("inner")
            except MemoryError as original:
                raise RuntimeError("outer") from original
        try:
            fail()
        except RuntimeError as error:
            chain = diagnostics.exception_details(error)
        self.assertEqual([item["type"] for item in chain], ["RuntimeError", "MemoryError"])
        self.assertTrue(all(len(item["frames"]) <= 32 for item in chain))

    def test_nested_installation_is_rejected_and_outer_hook_survives(self):
        class Controller:
            def _verify(self, *args):
                return None
        original = Controller._verify
        with self.log.observe_controller(Controller):
            installed = Controller._verify
            with self.assertRaisesRegex(RuntimeError, "already installed"):
                with self.log.observe_controller(Controller):
                    self.fail("nested observer entered")
            self.assertIs(Controller._verify, installed)
        self.assertIs(Controller._verify, original)

    def test_launcher_caught_failure_still_has_trace_and_methods_restore(self):
        from banto_ai import anomaly_v03_campaign_launcher as launcher
        primary = MemoryError("before audit")
        args = ["continue", "--root", str(self.path.parent), "--expected-head", "a" * 40,
                "--name", "fixture", "--prepared-sha256", "b" * 64,
                "--state-path", "fixture.json", "--state-sha256", "c" * 64, "--max-chunks", "1"]
        original_continuing = launcher.continue_run
        with patch.object(launcher, "open_run", side_effect=primary) as opening, \
             patch.object(launcher.sys, "stderr", io.StringIO()):
            with self.log.observe_launcher(launcher):
                self.assertEqual(launcher.main(args), 2)
            self.assertIs(launcher.open_run, opening)
        self.assertIs(launcher.continue_run, original_continuing)
        trace = next(row for row in self.rows() if row["event"] == "exception")
        self.assertEqual(trace["phase"], "open_run")
        self.assertEqual(trace["exception_chain"][0]["type"], "MemoryError")

    def test_unreaped_owner_bypasses_exception_observation(self):
        from banto_ai import anomaly_v03_campaign_launcher as launcher
        primary = launcher.processes.UnreapedWorker(Mock(pid=1234), {})
        with patch.object(launcher, "continue_run", side_effect=primary), \
             patch.object(self.log, "failure") as failure:
            with self.log.observe_launcher(launcher):
                with self.assertRaises(launcher.processes.UnreapedWorker) as caught:
                    launcher.continue_run(None, None, None, 1)
        self.assertIs(caught.exception, primary)
        failure.assert_not_called()
        self.assertEqual([row["event"] for row in self.rows()], ["phase_begin"])

    def test_pagefile_observation_error_is_not_a_healthy_start_sample(self):
        self.log.sample_memory = lambda: {**self.memory, "pagefiles_error": "winerror:5"}
        self.assertFalse(self.log.sample())
        self.assertEqual(self.log.errors, 1)
        self.assertEqual(self.rows()[0]["memory"]["pagefiles_error"], "winerror:5")


class ContinuationFailureTests(unittest.TestCase):
    # Reuse only the small real-IO fixture, not its entire test suite.
    setUp = budget_fixtures.BudgetedRunTests.setUp
    open = budget_fixtures.BudgetedRunTests.open
    supervise = budget_fixtures.BudgetedRunTests.supervise
    restore = budget_fixtures.BudgetedRunTests.restore
    factory = budget_fixtures.BudgetedRunTests.factory
    invoke = budget_fixtures.BudgetedRunTests.invoke

    def test_revalidation_failure_records_trace_and_closes_without_new_attempt(self):
        first = self.invoke(1)
        resumed = self.restore(first["state"])
        before = {path: path.read_bytes() for path in (self.tree / "chunks").rglob("*") if path.is_file()}
        commands_before = len(self.commands)
        original_session = resumed.session
        path = self.root / "diagnostics.jsonl"
        log = diagnostics.Diagnostics(path, sample_memory=lambda: {"pagefiles": []})
        primary = MemoryError("injected into saved-chunk revalidation")
        controller = budget_fixtures.runs.lifecycle.Controller

        def fail_verification(controller, records, pins, digest):
            raise primary

        try:
            with patch.object(controller, "_verify", new=fail_verification):
                with log.observe_controller(controller), self.assertRaises(MemoryError) as caught:
                    self.invoke(run=resumed)
        finally:
            log.close()
        self.assertIs(caught.exception, primary)
        self.assertIsNot(resumed.session, original_session)
        closed = json.loads(Path(resumed.last_closed["path"]).read_bytes())
        self.assertEqual((closed["status"], closed["stop_reason"]), ("failed", "exception"))
        self.assertEqual(resumed.session.state["next_unverified_chunk"], 1)
        self.assertEqual(len(resumed.session.records), 3)
        self.assertEqual(len(self.commands), commands_before)
        self.assertEqual(before, {p: p.read_bytes() for p in (self.tree / "chunks").rglob("*") if p.is_file()})
        trace = next(json.loads(line) for line in path.read_text().splitlines()
                     if json.loads(line)["event"] == "exception")
        self.assertEqual(trace["chunk_at_failure"]["chunk_index"], 0)
        self.assertEqual(trace["exception_chain"][0]["type"], "MemoryError")
        self.assertEqual(log.errors, 0)


if __name__ == "__main__":
    unittest.main()
