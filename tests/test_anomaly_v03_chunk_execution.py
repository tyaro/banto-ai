"""Native adapter contracts with real small files and explicit process/science mocks."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_chunk_execution as execution
from banto_ai import anomaly_v03_chunk_audit as audit
from banto_ai import _anomaly_v03_io as storage
from banto_ai import _anomaly_v03_engineering_runtime as resources
from tests import test_anomaly_v03_attempt_controller as controller_fixtures
from tests import test_anomaly_v03_chunk_producer as producer_fixtures
from tests.test_anomaly_v03_chunk_contract import envelope


class NativeCallbackTests(unittest.TestCase):
    open = controller_fixtures.ControllerTests.open

    def setUp(self):
        controller_fixtures.ControllerTests.setUp(self)
        self.session.verifier_revision = "b" * 40
        self.enterContext(patch.object(execution.engine, "_root", side_effect=lambda root: root))
        self.callbacks = execution.NativeCallbacks(self.session)
        self.callbacks.producer.revision = "a" * 40
        self.callbacks.consumer.revision = "b" * 40
        self.commands = []
        self.native = self.enterContext(patch.object(execution.processes, "supervise", side_effect=self.supervise))

    def supervise(self, argv, cwd, control, limits, *, stdout_name, boundary):
        boundary()
        control.mkdir()
        self.commands.append(argv)
        if stdout_name == "stdout.jsonl":
            row = self.session.records[-1]
            files, _ = envelope(self.plan, row["chunk_index"], row["attempt"])
            storage.publish_local_result(control.parent, "result", files, verify_semantics=lambda files: None)
            raw, runtime = b'{"fixture_worker":true}\n', self.observed
        else:
            args = dict(zip(argv[3::2], argv[4::2]))
            result = audit.audit_saved_chunk(Path(args["--input-root"]), args["--marker-sha256"],
                args["--supervision-sha256"], Path(args["--producer-root"]), args["--consumer-revision"],
                Path(args["--plan"]), args["--plan-sha256"], int(args["--chunk-index"]), int(args["--attempt"]))
            raw, runtime = storage.json_bytes(result), result["consumer_runtime"]
        storage._exclusive(control / stdout_name, raw)
        storage._exclusive(control / "stderr.json", b"")
        return {"format": "anomaly-v03-owned-process-monitor-v1", "status": "complete", "exit_code": 0,
            "worker_exit_confirmed": True, "worker_started": True, "worker_pid": 1234, "stop_reason": None,
            "observation_errors": [], "runtime_before": runtime, "runtime_after": copy.deepcopy(runtime),
            "formal_permission": False, "performance_status": "not_evaluated", "elapsed_seconds": 1.0,
            "peak_worker_private_bytes": 1000, "limits": limits, "argv": argv,
            "output": {"bytes": len(raw), "sha256": storage.sha(raw)}, "stderr": {"bytes": 0, "sha256": storage.sha(b"")}}

    def test_producer_and_auditor_callbacks_finalize_real_journal(self):
        receipts = []
        result = self.callbacks.run_next(self.observed, retain=receipts.append)
        self.assertEqual([r["receipt"]["journal"]["expected_record_count"] for r in receipts], [1, 2, 3])
        self.assertEqual(self.session.records[-1]["status"], "verified_complete")
        self.assertEqual(result["campaign_evaluations_credited"], 0)
        self.assertEqual(len(self.commands), 2)
        self.assertIn("_worker", self.commands[0])
        self.assertTrue(self.commands[1][2].endswith("audit_anomaly_v03_chunk.py"))
        self.assertEqual(self.commands[1][0:2], [sys.executable, "-B"])

    def test_changed_context_is_rejected_before_launch(self):
        context = self.session.start(self.observed)
        context["layout"]["result_root"] = "elsewhere/result"
        with self.assertRaisesRegex(ValueError, "layout"):
            self.callbacks.produce(context)
        self.native.assert_not_called()

    def test_changed_plan_is_rejected_before_start(self):
        (self.metadata / "plan.json").write_bytes(b"{}\n")
        with self.assertRaisesRegex(ValueError, "plan changed"):
            self.callbacks.run_next(self.observed)
        self.native.assert_not_called()
        self.assertFalse(self.session.records)

    def test_resource_stop_saves_monitor_and_retriable_failure(self):
        def failure(*args, **kwargs):
            report = self.supervise(*args, **kwargs)
            report.update(status="failed", stop_reason="memory_limit", exit_code=1)
            return report
        self.native.side_effect = failure
        with self.assertRaisesRegex(resources.ResourceStop, "memory_limit"):
            self.callbacks.run_next(self.observed)
        self.assertEqual(self.session.records[-1]["status"], "failed")
        self.assertEqual(len(self.commands), 1)
        monitor = json.loads((self.tree / "chunks/000/attempt-0001/producer-control/supervision.json").read_bytes())
        self.assertEqual(monitor["stop_reason"], "memory_limit")

    def test_audit_failure_retains_saved_producer(self):
        def failure(*args, **kwargs):
            report = self.supervise(*args, **kwargs)
            if kwargs["stdout_name"] == "report.json":
                report.update(status="failed", exit_code=2)
            return report
        self.native.side_effect = failure
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            self.callbacks.run_next(self.observed)
        self.assertEqual(self.session.records[-1]["status"], "failed")
        self.assertTrue((self.tree / "chunks/000/attempt-0001/result/.complete").exists())

    def test_monitor_write_failure_preserves_primary_resource_stop(self):
        def failure(*args, **kwargs):
            report = self.supervise(*args, **kwargs)
            report.update(status="failed", stop_reason="memory_limit", exit_code=1)
            return report
        self.native.side_effect = failure
        with patch.object(self.callbacks, "_write_monitor", side_effect=OSError("monitor disk full")):
            with self.assertRaises(resources.ResourceStop) as caught:
                self.callbacks.run_next(self.observed)
        self.assertEqual(caught.exception.reason, "memory_limit")
        self.assertIsInstance(caught.exception.__cause__, OSError)
        self.assertEqual(self.session.last_stop["reason"], "resource_limit")

    def test_unreaped_owner_survives_monitor_write_failure_without_failure_record(self):
        owner = Mock(returncode=None, pid=1234)
        error = execution.processes.UnreapedWorker(owner, {"runtime_before": self.observed})
        self.native.side_effect = error
        with patch.object(self.callbacks, "_write_monitor", side_effect=OSError("disk full")):
            with self.assertRaises(execution.processes.UnreapedWorker) as caught:
                self.callbacks.run_next(self.observed)
        self.assertIs(caught.exception, error)
        self.assertIs(caught.exception.process, owner)
        self.assertEqual([r["status"] for r in self.session.records], ["running"])

    def test_receipt_write_failure_does_not_launch_worker(self):
        with self.assertRaisesRegex(OSError, "receipt disk full"):
            self.callbacks.run_next(self.observed, retain=Mock(side_effect=OSError("receipt disk full")))
        self.native.assert_not_called()
        self.assertEqual(self.session.records[-1]["status"], "failed")

    def test_cli_retains_unreaped_worker_until_exit(self):
        owner = Mock(returncode=None, pid=1234)
        owner.wait.side_effect = [KeyboardInterrupt(), None]
        def stop():
            if owner.kill.call_count == 2:
                owner.returncode = 1
        owner.kill.side_effect = stop
        with patch.object(execution, "trial", side_effect=execution.processes.UnreapedWorker(owner, {})), \
             patch.object(sys, "stderr", Mock(write=Mock(side_effect=OSError("broken stderr")))):
            self.assertEqual(execution.main(["trial", "--root", str(self.root), "--expected-head", "a" * 40,
                                             "--name", "fixture"]), 2)
        self.assertEqual(owner.kill.call_count, 2)
        owner._handle.Close.assert_called_once()


class NativeWorkerTests(unittest.TestCase):
    def setUp(self):
        producer_fixtures.ChunkProducerTests.setUp(self)
        self.tree = self.root / "attempts"
        (self.tree / "chunks/096/attempt-0002").mkdir(parents=True)
        self.plan_path = self.root / "plan.json"
        self.plan_path.write_bytes(storage.json_bytes(self.plan))
        self.enterContext(patch.object(execution.engine, "_root", side_effect=lambda root: root))
        self.enterContext(patch.object(execution.rt, "capture_checkout", return_value=self.checkout))
        self.enterContext(patch.object(type(self.checkout), "recheck", return_value=None))
        self.enterContext(patch.object(resources, "probe_runtime", return_value=self.runtime))
        self.enterContext(patch.object(resources, "require_start_resources", return_value={"fixture": True}))
        self.enterContext(patch.object(resources, "memory_bytes", return_value={"peak_private_bytes": 1000}))

    def worker(self, digest=None):
        return execution._worker(self.root, "a" * 40, self.tree, self.plan_path,
            digest or execution.v.canonical_sha256(self.plan), 96, 2)

    def test_worker_publishes_and_replays_selected_smoke_chunk_after_close(self):
        report = self.worker()
        self.assertEqual(report["binding"]["chunk_index"], 96)
        self.assertEqual(report["binding"]["attempt"], 2)
        self.assertEqual(self.compute.call_count, 6)
        self.assertEqual(self.replay.call_count, 12)
        self.assertEqual(report["coverage"]["inconclusive"], 2)
        with self.assertRaises(FileExistsError):
            self.worker()

    def test_wrong_external_plan_hash_fails_before_generation_or_output(self):
        with self.assertRaisesRegex(ValueError, "plan hash"):
            self.worker("0" * 64)
        self.generate.assert_not_called()
        self.assertFalse((self.tree / "chunks/096/attempt-0002/result").exists())
