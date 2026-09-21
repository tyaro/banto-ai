"""Real small journal/publication IO; native processes, science and clocks mocked."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_budgeted_run as runs
from banto_ai import anomaly_v03_chunk_execution as execution
from banto_ai import _anomaly_v03_io as storage
from banto_ai import _anomaly_v03_engineering_runtime as resources
from tests import test_anomaly_v03_chunk_execution as native_fixtures


class BudgetedRunTests(unittest.TestCase):
    open = native_fixtures.NativeCallbackTests.open
    supervise = native_fixtures.NativeCallbackTests.supervise

    def setUp(self):
        native_fixtures.NativeCallbackTests.setUp(self)
        # The separate path preflight test uses every real registered identity.
        with patch.object(execution, "_path_budget"):
            self.prepared = runs.prepare(self.root, "run", self.plan, self.observed)
        self.run_root = Path(self.prepared["root"])
        self.tree = self.run_root / "attempts"
        self.now, self.increment = 0, 100
        self.memory = Mock(return_value={"private_bytes": 1000})
        self.measure = Mock(wraps=runs.output_bytes)
        self.after_chunk = lambda: None
        self.run = self.restore(self.prepared["state"])

    def restore(self, pin):
        return runs.Run(self.run_root, self.prepared["request"]["sha256"], pin["path"], pin["sha256"],
            self.root / "producer", self.root / "consumer", "b" * 40,
            clock=lambda: self.now, measure=self.measure, sample_memory=self.memory)

    def factory(self, session):
        self.session = session
        callbacks = execution.NativeCallbacks(session)
        callbacks.producer.revision, callbacks.consumer.revision = "a" * 40, "b" * 40

        def next_chunk(observed, *, retain):
            result = callbacks.run_next(observed, retain=retain)
            self.now += self.increment
            self.after_chunk()
            return result
        return SimpleNamespace(run_next=next_chunk)

    def invoke(self, count=1, run=None):
        return (run or self.run).run(self.observed, max_chunks=count, callbacks_factory=self.factory)

    def test_sequential_chunks_then_restart_keep_pins_time_and_prefix(self):
        first = self.invoke(2)
        self.assertEqual(first["chunks_verified_in_invocation"], 2)
        self.assertEqual(first["elapsed_seconds_total"], 200)
        prefix = {p: p.read_bytes() for p in (self.tree / "chunks/000").rglob("*") if p.is_file()}
        resumed = self.restore(first["state"])
        second = self.invoke(run=resumed)
        self.assertEqual(second["next_unverified_chunk"], 3)
        self.assertEqual(second["elapsed_seconds_total"], 300)
        self.assertEqual(set(resumed.session.descriptor_pins), {"3", "6", "9"})
        self.assertEqual(prefix, {p: p.read_bytes() for p in (self.tree / "chunks/000").rglob("*") if p.is_file()})
        self.assertEqual(len(list((self.run_root / "control/000001/receipts").iterdir())), 6)
        self.assertEqual(len(list((self.run_root / "control/000002/receipts").iterdir())), 3)
        self.assertFalse(second["formal_permission"])
        self.assertEqual(second["campaign_evaluations_credited"], 0)
        with self.assertRaisesRegex(ValueError, "unclosed or unexpected"):
            self.invoke()

    def test_stop_request_finishes_current_chunk_and_resumes_next(self):
        self.after_chunk = lambda: (self.run_root / "control/000001/stop.request").write_bytes(b"")
        first = self.invoke(3)
        self.assertEqual((first["status"], first["stop_reason"], first["next_unverified_chunk"]),
                         ("stopped", "stop_requested", 1))
        self.after_chunk = lambda: None
        self.assertEqual(self.invoke(run=self.restore(first["state"]))["next_unverified_chunk"], 2)

    def test_time_budget_is_cumulative_and_refuses_next_chunk(self):
        self.increment = runs.budget()["wall_seconds"] - 1000
        first = self.invoke(3)
        self.assertEqual(first["stop_reason"], "time_budget")
        self.assertEqual(first["chunks_verified_in_invocation"], 1)
        calls = len(self.commands)
        second = self.invoke(run=self.restore(first["state"]))
        self.assertEqual(second["elapsed_seconds_total"], self.increment)
        self.assertEqual(second["stop_reason"], "time_budget")
        self.assertEqual(len(self.commands), calls)

    def test_output_reserve_stops_before_callbacks_are_constructed(self):
        self.measure.side_effect = None
        self.measure.return_value = runs.budget()["output_bytes"] - 2 * runs.budget()["control_reserve_bytes"]
        factory = Mock()
        result = self.run.run(self.observed, callbacks_factory=factory)
        self.assertEqual(result["stop_reason"], "output_budget")
        factory.assert_not_called()
        self.native.assert_not_called()

    def test_final_inventory_time_is_charged_and_stops_the_run(self):
        def measure(root):
            if self.measure.call_count == 3:
                self.now = runs.budget()["wall_seconds"] + 1
            return runs.output_bytes(root)
        self.measure.side_effect = measure
        result = self.invoke()
        self.assertEqual((result["status"], result["stop_reason"]), ("stopped", "time_budget"))
        self.assertEqual(result["elapsed_seconds_total"], runs.budget()["wall_seconds"] + 1)

    def test_last_chunk_time_overrun_has_priority_over_completed(self):
        # This scheduling-only stub represents the last chunk without fabricating
        # 119 prior publications or running hundreds of unrelated evaluations.
        def factory(session):
            session.state["next_unverified_chunk"] = 119

            def finish(*args, **kwargs):
                session.state["next_unverified_chunk"] = None
                session.records = [{"status": "verified_complete"}]
                self.now = runs.budget()["wall_seconds"] + 1
            return SimpleNamespace(run_next=finish)
        result = self.run.run(self.observed, max_chunks=1, callbacks_factory=factory)
        self.assertEqual((result["status"], result["stop_reason"]), ("stopped", "time_budget"))
        self.assertIsNone(result["next_unverified_chunk"])

    def test_memory_stop_after_verified_chunk_saves_closed_boundary(self):
        self.after_chunk = lambda: self.memory.configure_mock(return_value={"private_bytes": 3 * 1024**3})
        with self.assertRaisesRegex(resources.ResourceStop, "memory_limit"):
            self.invoke(3)
        closed = json.loads(Path(self.run.last_closed["path"]).read_bytes())
        self.assertEqual(closed["status"], "failed")
        self.assertEqual(closed["elapsed_seconds_total"], 100)
        self.assertEqual(self.restore(self.run.last_closed).session.state["next_unverified_chunk"], 1)
        self.assertEqual(len(self.commands), 2)

    def test_retriable_worker_failure_preserves_old_attempt_and_uses_new_attempt(self):
        def failure(*args, **kwargs):
            report = self.supervise(*args, **kwargs)
            report.update(status="failed", stop_reason="memory_limit", exit_code=1)
            return report
        self.native.side_effect = failure
        with self.assertRaises(resources.ResourceStop):
            self.invoke()
        old = self.tree / "chunks/000/attempt-0001"
        prefix = {p: p.read_bytes() for p in old.rglob("*") if p.is_file()}
        self.native.side_effect = self.supervise
        resumed = self.restore(self.run.last_closed)
        self.invoke(run=resumed)
        self.assertEqual(resumed.session.records[-1]["attempt"], 2)
        self.assertEqual(prefix, {p: p.read_bytes() for p in old.rglob("*") if p.is_file()})

    def test_unreaped_worker_is_not_measured_or_closed_and_keeps_owner(self):
        owner = Mock(returncode=None, pid=1234)
        original = execution.processes.UnreapedWorker(owner, {"runtime_before": self.observed})
        calls = []

        def failure(*args, **kwargs):
            calls.append(self.measure.call_count)
            raise original
        self.native.side_effect = failure
        with self.assertRaises(execution.processes.UnreapedWorker) as caught:
            self.invoke()
        self.assertIs(caught.exception, original)
        self.assertIs(caught.exception.process, owner)
        self.assertEqual(self.measure.call_count, calls[0])
        self.assertIsNone(self.run.last_closed)
        with self.assertRaisesRegex(ValueError, "unclosed or unexpected"):
            self.restore(self.prepared["state"])

    def test_unfinished_transition_never_closes_invocation(self):
        original = runs.lifecycle.TransitionIncomplete("intent retained")
        with self.assertRaises(runs.lifecycle.TransitionIncomplete) as caught:
            self.run.run(self.observed, callbacks_factory=lambda session: Mock(run_next=Mock(side_effect=original)))
        self.assertIs(caught.exception, original)
        self.assertIsNone(self.run.last_closed)

    def test_final_clock_failure_does_not_mask_original_exception(self):
        original = RuntimeError("primary failure")

        def failure(*args, **kwargs):
            self.run.clock = Mock(side_effect=OSError("clock failed"))
            raise original
        with self.assertRaises(RuntimeError) as caught:
            self.run.run(self.observed, callbacks_factory=lambda session: Mock(run_next=Mock(side_effect=failure)))
        self.assertIs(caught.exception, original)
        self.assertIsNone(self.run.last_closed)

    def test_closed_write_failure_does_not_mask_original_exception(self):
        original, real_write = RuntimeError("primary failure"), runs._write

        def write(path, value):
            if path.name == "closed.json":
                raise OSError("disk full")
            return real_write(path, value)
        with patch.object(runs, "_write", side_effect=write):
            with self.assertRaises(RuntimeError) as caught:
                self.run.run(self.observed, callbacks_factory=lambda session: Mock(run_next=Mock(side_effect=original)))
        self.assertIs(caught.exception, original)
        self.assertIsNone(self.run.last_closed)

    def test_request_tamper_after_last_chunk_prevents_closed_state(self):
        self.after_chunk = lambda: (self.run_root / "request.json").write_bytes(b"{}\n")
        with self.assertRaisesRegex(ValueError, "request changed"):
            self.invoke()
        self.assertIsNone(self.run.last_closed)

    def test_external_hashes_and_closed_state_chain_are_required(self):
        pin = {**self.prepared["state"], "sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "external closed-state hash"):
            self.restore(pin)
        first = self.invoke()
        Path(self.prepared["state"]["path"]).write_bytes(b"{}\n")
        with self.assertRaisesRegex(ValueError, "external closed-state hash"):
            self.restore(first["state"])

    def test_noop_callback_cannot_be_counted_as_a_verified_chunk(self):
        with self.assertRaisesRegex(ValueError, "exactly one chunk"):
            self.run.run(self.observed, callbacks_factory=lambda session: Mock())
        self.assertEqual(self.restore(self.run.last_closed).session.state["next_unverified_chunk"], 0)

    def test_prepare_checks_all_registered_paths_and_preserves_existing_root(self):
        with patch.object(execution, "_path_budget", wraps=execution._path_budget) as check:
            prepared = runs.prepare(self.root, "p", self.plan, self.observed)
        self.assertEqual([call.args[2] for call in check.call_args_list], list(range(120)))
        self.assertFalse(prepared["execution_started"])
        with patch.object(execution, "_path_budget"):
            with self.assertRaises(FileExistsError):
                runs.prepare(self.root, "p", self.plan, self.observed)
        with self.assertRaisesRegex(ValueError, "path too long"):
            runs.prepare(self.root, "x" * 64, self.plan, self.observed)
        self.assertFalse((self.root / ("x" * 64)).exists())

    def test_output_walk_counts_hardlinks_and_rejects_inventory_overflow(self):
        directory = self.root / "count"
        directory.mkdir()
        (directory / "one").write_bytes(b"123")
        os.link(directory / "one", directory / "two")
        self.assertEqual(runs.output_bytes(directory), 6)
        with patch.object(runs, "MAX_OUTPUT_ENTRIES", 1):
            with self.assertRaisesRegex(ValueError, "inventory limit"):
                runs.output_bytes(directory)


if __name__ == "__main__":
    unittest.main()
