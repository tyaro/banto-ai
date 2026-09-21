"""Owned process lifecycle fixtures plus one tiny Windows print-only child."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_process_supervisor as monitor
from tests.test_anomaly_v03_engineering import fixture_context


class FakeProcess:
    def __init__(self, *, exit_code=0, running=False):
        self.pid, self.returncode, self.running = 123, None, running
        self.final_exit = exit_code
        self._handle = Mock()
        self.kills, self.waits = 0, 0

    def poll(self):
        if not self.running and self.returncode is None:
            self.returncode = self.final_exit
        return self.returncode

    def kill(self):
        self.kills += 1
        self.running, self.returncode = False, -9

    def wait(self, timeout):
        self.waits += 1
        return self.poll()


class ProcessSupervisorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="banto-process-monitor-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.runtime = fixture_context()[1]
        self.limits = {"wall_seconds": 60, "private_bytes": 1024**3, "output_bytes": 1024**2}
        self.enterContext(patch.object(monitor.subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True))

    def run_fake(self, *, process=None, stdout=b'{}\n', stderr=b'', limits=None, memory=None, probe=None, boundary=lambda: None):
        process = process or FakeProcess()
        def launch(argv, **kwargs):
            kwargs["stdout"].write(stdout)
            kwargs["stdout"].flush()
            kwargs["stderr"].write(stderr)
            kwargs["stderr"].flush()
            self.assertEqual(kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)
            return process
        with patch.object(monitor.subprocess, "Popen", side_effect=launch), \
             patch.object(monitor.resources, "memory_bytes", side_effect=memory or (lambda handle: {"peak_private_bytes": 1000})), \
             patch.object(monitor.resources, "require_start_resources", return_value={}), \
             patch.object(monitor.resources, "free_resources", return_value={}), \
             patch.object(monitor.time, "sleep"):
            result = monitor.supervise([sys.executable, "-B", "fixture-only"], self.root, self.root / "control",
                limits or self.limits, runtime_probe=probe or (lambda: copy.deepcopy(self.runtime)), boundary=boundary)
        return result, process

    def test_normal_exit_records_output_runtime_and_closes_owned_handle(self):
        report, process = self.run_fake()
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["output"]["bytes"], 3)
        self.assertTrue(report["worker_exit_confirmed"])
        self.assertFalse(report["formal_permission"])
        self.assertEqual((process.kills, process.waits), (0, 1))
        process._handle.Close.assert_called_once()

    def test_memory_limit_kills_only_owned_worker_and_reaps(self):
        report, process = self.run_fake(process=FakeProcess(running=True), memory=lambda handle: {"peak_private_bytes": 1024**3 + 1})
        self.assertEqual(report["stop_reason"], "memory_limit")
        self.assertEqual((process.kills, process.waits), (1, 1))
        self.assertTrue(report["worker_exit_confirmed"])

    def test_time_limit_kills_and_reaps(self):
        times = iter([0, 0, 2, 2, 2])
        with patch.object(monitor.time, "monotonic", side_effect=lambda: next(times, 2)):
            report, process = self.run_fake(process=FakeProcess(running=True), limits=self.limits | {"wall_seconds": 1})
        self.assertEqual(report["stop_reason"], "time_limit")
        self.assertEqual(process.kills, 1)

    def test_combined_logs_and_post_exit_burst_are_limited(self):
        report, _ = self.run_fake(stdout=b'1234', stderr=b'5678', limits=self.limits | {"output_bytes": 7})
        self.assertEqual(report["stop_reason"], "output_limit")
        self.assertEqual(report["status"], "failed")

    def test_memory_observation_failure_still_reaps_and_is_not_success(self):
        def fail(handle):
            raise OSError("fixture memory observation")
        report, process = self.run_fake(process=FakeProcess(running=True), memory=fail)
        self.assertEqual(report["status"], "failed")
        self.assertEqual((process.kills, process.waits), (1, 1))
        self.assertEqual([e["stage"] for e in report["observation_errors"]], ["supervision", "final_worker_memory"])

    def test_runtime_change_is_preserved(self):
        probes = iter([self.runtime, self.runtime | {"os_ubr": 9999}])
        report, _ = self.run_fake(probe=lambda: next(probes))
        self.assertEqual((report["status"], report["stop_reason"]), ("failed", "runtime_changed"))

    def test_launch_failure_keeps_partial_logs_and_no_confirmed_worker(self):
        with patch.object(monitor.subprocess, "Popen", side_effect=OSError("launch fixture")), \
             patch.object(monitor.resources, "require_start_resources", return_value={}):
            report = monitor.supervise([sys.executable], self.root, self.root / "control", self.limits,
                runtime_probe=lambda: self.runtime)
        self.assertFalse(report["worker_started"] or report["worker_exit_confirmed"])
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["output"]["bytes"], 0)

    def test_invalid_limits_and_existing_control_never_launch(self):
        with patch.object(monitor.subprocess, "Popen") as launch:
            for limits in (self.limits | {"wall_seconds": float("inf")}, self.limits | {"private_bytes": True}):
                with self.assertRaises(ValueError):
                    monitor.supervise([sys.executable], self.root, self.root / "invalid", limits)
            control = self.root / "control"
            control.mkdir()
            (control / "keep").write_bytes(b"retained")
            with self.assertRaises(FileExistsError):
                monitor.supervise([sys.executable], self.root, control, self.limits)
            self.assertEqual((control / "keep").read_bytes(), b"retained")
        launch.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "real child uses Windows process observation")
    def test_tiny_real_windows_child_exits_and_output_is_hashed(self):
        report = monitor.supervise([sys.executable, "-B", "-c", "print('fixture')"], self.root,
            self.root / "real", self.limits, runtime_probe=lambda: self.runtime)
        self.assertEqual(report["status"], "complete", report)
        self.assertTrue(report["worker_exit_confirmed"])
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual((self.root / "real/report.json").read_bytes().strip(), b"fixture")
        self.assertGreater(report["peak_worker_private_bytes"], 0)

    def test_interrupt_still_returns_reaped_observations(self):
        calls = 0
        def memory(handle):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise KeyboardInterrupt()
            return {"peak_private_bytes": 1000}
        report, process = self.run_fake(process=FakeProcess(running=True), memory=memory)
        self.assertEqual(report["stop_reason"], "interrupted")
        self.assertTrue(report["worker_exit_confirmed"])
        self.assertEqual(process.kills, 1)

    def test_unreaped_worker_retains_original_handle_and_failure_report(self):
        process = FakeProcess(running=True)
        process.kill = Mock(side_effect=OSError("injected stop failure"))
        process.wait = Mock(side_effect=subprocess.TimeoutExpired("fixture", 30))
        with patch.object(monitor, "_file_pin") as read_logs, self.assertRaises(monitor.UnreapedWorker) as caught:
            self.run_fake(process=process, memory=lambda handle: {"peak_private_bytes": 1024**3 + 1})
        read_logs.assert_not_called()
        self.assertIs(caught.exception.process, process)
        self.assertFalse(caught.exception.report["worker_exit_confirmed"])
        self.assertEqual(caught.exception.report["status"], "failed")
        process._handle.Close.assert_not_called()

    def test_interrupt_during_cleanup_retains_unreaped_owner(self):
        process = FakeProcess(running=True)
        process.kill = Mock(side_effect=KeyboardInterrupt())
        process.wait = Mock(side_effect=KeyboardInterrupt())
        with self.assertRaises(monitor.UnreapedWorker) as caught:
            self.run_fake(process=process, memory=lambda handle: {"peak_private_bytes": 1024**3 + 1})
        self.assertIs(caught.exception.process, process)
        self.assertFalse(caught.exception.report["worker_exit_confirmed"])

    def test_oversized_finished_log_is_rejected_before_read(self):
        path = self.root / "large.log"
        path.write_bytes(b"12345678")
        with patch.object(Path, "open", side_effect=AssertionError("oversized log read")), self.assertRaisesRegex(monitor.resources.ResourceStop, "output_limit"):
            monitor._file_pin(path, 7)


if __name__ == "__main__":
    unittest.main()
