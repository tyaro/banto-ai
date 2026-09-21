"""Small real snapshot/file IO; OS, source, native-process and science mocks explicit."""
import copy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_campaign_launcher as launcher
from banto_ai import anomaly_v03_engineering_inventory as snapshot
from banto_ai import _anomaly_v03_inventory as inventory
from banto_ai import _anomaly_v03_io as storage
from banto_ai import _anomaly_v03_engineering_runtime as resources
from tests.test_anomaly_v03_engineering import fixture_context
from tests import test_anomaly_v03_budgeted_run as budget_fixtures


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="bir-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.revision = "a" * 40
        self.observed = fixture_context()[1]
        self.paths = {}
        for name in ("runtime.py", "python.exe", "python314.dll"):
            path = self.root / name
            path.write_bytes(name.encode())
            self.paths[name] = path
        self.observed.update(python_exe_raw_sha256=storage.sha(b"python.exe"), python_dll_raw_sha256=storage.sha(b"python314.dll"))
        self.enterContext(patch.object(snapshot.engine, "_root", side_effect=lambda root: root))
        self.enterContext(patch.object(snapshot.policy, "validate_runtime"))
        self.enterContext(patch.object(resources, "probe_runtime", return_value=self.observed))
        self.enterContext(patch.object(resources, "require_start_resources", return_value={}))
        self.enterContext(patch.object(inventory, "_windows_cpu", return_value=("fixture", ["PF-001"])))
        self.enterContext(patch.object(inventory, "_startup", return_value={"bytecode_writes_disabled": True}))
        rows = sorted(({"path": name, "raw_sha256": "1" * 64, "byte_count": 1}
            for name in {*snapshot.acceptance.REQUIRED_PRODUCER_PATHS, snapshot.acceptance.WORKFLOW}), key=lambda row: row["path"])
        self.source = self.enterContext(patch.object(inventory, "capture_sources", return_value=rows))
        self.enterContext(patch.object(inventory, "stdlib_paths", return_value=[("stdlib/runtime.py", self.paths["runtime.py"])]))
        self.native = self.enterContext(patch.object(inventory, "native_paths", return_value=[
            ("native/" + name, self.paths[name]) for name in ("python.exe", "python314.dll")]))
        self.enterContext(patch.object(inventory, "extension_paths", return_value=set()))
        self.enterContext(patch.object(inventory, "_native_local"))
        self.enterContext(patch.object(snapshot, "sys", SimpleNamespace(executable=str(self.paths["python.exe"]))))

    def test_snapshot_reads_twice_and_does_not_claim_runtime_closure(self):
        with patch.object(inventory, "hash_file", wraps=inventory.hash_file) as standard, \
             patch.object(inventory, "hash_native", wraps=inventory.hash_native) as native, \
             patch.object(Path, "write_bytes", side_effect=AssertionError("unexpected write")):
            result = snapshot.collect(self.root, self.revision)
        self.assertEqual(standard.call_count, 2)
        self.assertEqual(native.call_count, 4)
        self.assertEqual(self.source.call_count, 2)
        self.assertFalse(result["formal_permission"])
        self.assertFalse(result["full_runtime_inventory_complete"])
        self.assertEqual(set(p.name for p in self.root.iterdir()), set(self.paths))

    def test_changed_native_list_stops_readback(self):
        self.native.side_effect = [self.native.return_value, []]
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            snapshot.collect(self.root, self.revision)

    def test_changed_stdlib_bytes_are_detected(self):
        original, calls = inventory.hash_file, []

        def changing(path, logical):
            row = original(path, logical)
            calls.append(logical)
            if len(calls) == 1:
                path.write_bytes(b"changed")
            return row
        with patch.object(inventory, "hash_file", side_effect=changing):
            with self.assertRaisesRegex(ValueError, "stdlib bytes changed"):
                snapshot.collect(self.root, self.revision)

    def test_actual_windows_update_value_is_recorded_but_change_during_inspection_stops(self):
        self.observed["os_ubr"] = 9457
        self.assertEqual(snapshot.collect(self.root, self.revision)["runtime"]["os_ubr"], 9457)
        with patch.object(resources, "probe_runtime", side_effect=[self.observed, {**self.observed, "os_ubr": 9999}]):
            with self.assertRaisesRegex(ValueError, "runtime changed"):
                snapshot.collect(self.root, self.revision)

    def test_missing_python_image_or_wrong_scope_is_rejected(self):
        original = snapshot.collect(self.root, self.revision)
        for field in ("loaded_native", "full_runtime_inventory_complete"):
            value = copy.deepcopy(original)
            value[field] = value[field][:1] if field == "loaded_native" else True
            with self.subTest(field=field), self.assertRaises(ValueError):
                snapshot.validate(value, self.root, self.revision)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        SnapshotTests.setUp(self)
        self.enterContext(patch.object(inventory, "_clean"))
        self.enterContext(patch.object(launcher.native, "_path_budget"))
        self.supervisor = self.enterContext(patch.object(launcher.processes, "supervise", side_effect=self.supervise))

    def supervise(self, argv, cwd, control, limits, *, boundary):
        boundary()
        control.mkdir()
        value = snapshot.collect(cwd, self.revision)
        raw = storage.json_bytes(value)
        storage._exclusive(control / "report.json", raw)
        storage._exclusive(control / "stderr.json", b"")
        return {"status": "complete", "exit_code": 0, "worker_exit_confirmed": True, "stop_reason": None,
            "worker_pid": value["pid"], "observation_errors": [], "runtime_before": self.observed,
            "runtime_after": self.observed, "output": {"bytes": len(raw), "sha256": storage.sha(raw)},
            "stderr": {"bytes": 0, "sha256": storage.sha(b"")}, "limits": limits, "argv": argv}

    def test_prepare_records_snapshot_and_empty_plan_without_computation(self):
        result = launcher.prepare(self.root, self.revision, "r")
        self.assertFalse(result["execution_started"])
        self.assertEqual(self.supervisor.call_count, 1)
        root, session = launcher.open_run(self.root, self.revision, "r", result["prepared"]["sha256"],
                                         result["state"]["path"], result["state"]["sha256"])
        self.assertEqual(root, self.root)
        self.assertEqual(session.session.state["next_unverified_chunk"], 0)
        self.assertFalse(session.session.records)
        with self.assertRaises(FileExistsError):
            launcher.prepare(self.root, self.revision, "r")
        self.assertEqual(self.supervisor.call_count, 1)

    def test_modified_preparation_and_snapshot_refuse_open(self):
        result = launcher.prepare(self.root, self.revision, "r")
        with self.assertRaisesRegex(ValueError, "external preparation hash"):
            launcher.open_run(self.root, self.revision, "r", "0" * 64, result["state"]["path"], result["state"]["sha256"])
        (self.root / launcher.PARENT / "r/inspection/report.json").write_bytes(b"{}\n")
        with self.assertRaisesRegex(ValueError, "prepared inspection changed"):
            launcher.open_run(self.root, self.revision, "r", result["prepared"]["sha256"], result["state"]["path"], result["state"]["sha256"])

    def test_dirty_source_is_rejected_before_directory_or_worker_creation(self):
        with patch.object(inventory, "_clean", side_effect=ValueError("tracked source dirty")):
            with self.assertRaisesRegex(ValueError, "source dirty"):
                launcher.prepare(self.root, self.revision, "r")
        self.supervisor.assert_not_called()
        self.assertFalse((self.root / launcher.PARENT).exists())

    def test_long_paths_are_rejected_before_directory_or_worker_creation(self):
        with patch.object(launcher.native, "_path_budget", side_effect=ValueError("output path too long")):
            with self.assertRaisesRegex(ValueError, "path too long"):
                launcher.prepare(self.root, self.revision, "r")
        self.supervisor.assert_not_called()
        self.assertFalse((self.root / launcher.PARENT).exists())

    def test_unreaped_inspector_returns_owner_without_reading_or_writing_outputs(self):
        owner = Mock(returncode=None, pid=1234)
        original = launcher.processes.UnreapedWorker(owner, {})
        self.supervisor.side_effect = original
        with patch.object(launcher.runs, "_write") as write, patch.object(launcher.journal, "read_metadata") as read:
            with self.assertRaises(launcher.processes.UnreapedWorker) as caught:
                launcher.inspect(self.root, self.revision, self.root / "inspection")
        self.assertIs(caught.exception.process, owner)
        write.assert_not_called()
        read.assert_not_called()

    def test_inspection_stop_is_preserved_when_monitor_write_fails(self):
        def failed(*args, **kwargs):
            value = self.supervise(*args, **kwargs)
            value.update(status="failed", stop_reason="memory_limit", exit_code=1)
            return value
        self.supervisor.side_effect = failed
        with patch.object(launcher.runs, "_write", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(resources.ResourceStop, "memory_limit"):
                launcher.inspect(self.root, self.revision, self.root / "inspection")

    def test_wrong_inspector_pid_is_rejected_before_preparation(self):
        def wrong_pid(*args, **kwargs):
            value = self.supervise(*args, **kwargs)
            value["worker_pid"] += 1
            return value
        self.supervisor.side_effect = wrong_pid
        with self.assertRaisesRegex(ValueError, "process binding"):
            launcher.prepare(self.root, self.revision, "r")
        self.assertFalse((self.root / launcher.PARENT / "r/prepared.json").exists())

    def test_cli_requires_explicit_chunk_count_without_starting(self):
        with patch.object(launcher, "open_run") as opening, patch.object(launcher.sys, "stderr", io.StringIO()):
            with self.assertRaises(SystemExit):
                launcher.main(["continue", "--root", str(self.root), "--expected-head", self.revision,
                    "--name", "r", "--prepared-sha256", "a" * 64, "--state-path", "closed.json", "--state-sha256", "b" * 64])
        opening.assert_not_called()

    def test_cli_keeps_unreaped_owner_when_stderr_fails(self):
        owner = Mock(returncode=None, pid=1234)
        owner.wait.side_effect = [KeyboardInterrupt(), None]

        def stop():
            if owner.kill.call_count == 2:
                owner.returncode = 1
        owner.kill.side_effect = stop
        original = launcher.processes.UnreapedWorker(owner, {})
        with patch.object(launcher, "prepare", side_effect=original), \
             patch.object(launcher.sys, "stderr", Mock(write=Mock(side_effect=OSError("closed stderr")))):
            self.assertEqual(launcher.main(["prepare", "--root", str(self.root), "--expected-head", self.revision, "--name", "r"]), 2)
        owner._handle.Close.assert_called_once()
        self.assertEqual(owner.kill.call_count, 2)


class ContinuationTests(unittest.TestCase):
    open = budget_fixtures.BudgetedRunTests.open
    supervise = budget_fixtures.BudgetedRunTests.supervise
    restore = budget_fixtures.BudgetedRunTests.restore

    def setUp(self):
        budget_fixtures.BudgetedRunTests.setUp(self)
        self.enterContext(patch.object(resources, "probe_runtime", return_value=self.observed))

    def test_fresh_inspection_precedes_native_data_work_and_retains_pin(self):
        constructor, events = launcher.native.NativeCallbacks, []

        def inspect(*args):
            events.append("inspection")
            self.now += 20
            return {"runtime": self.observed}, {"fixture": "externally retained inspection pin"}

        def callbacks(session):
            events.append("callbacks")
            self.session = session
            value = constructor(session)
            value.producer.revision, value.consumer.revision = "a" * 40, "b" * 40
            return value
        with patch.object(launcher, "inspect", side_effect=inspect), patch.object(launcher.native, "NativeCallbacks", side_effect=callbacks):
            result = launcher.continue_run(self.root, "b" * 40, self.run, 1)
        self.assertEqual(events, ["inspection", "callbacks"])
        self.assertEqual(result["next_unverified_chunk"], 1)
        self.assertEqual(result["elapsed_seconds_total"], 20)
        self.assertTrue((self.run_root / "control/000001/inspection-pin.json").is_file())

    def test_failed_inspection_never_constructs_native_data_callbacks(self):
        with patch.object(launcher, "inspect", side_effect=resources.ResourceStop("time_limit")), \
             patch.object(launcher.native, "NativeCallbacks") as callbacks:
            with self.assertRaises(resources.ResourceStop):
                launcher.continue_run(self.root, "b" * 40, self.run, 1)
        callbacks.assert_not_called()
        self.native.assert_not_called()
        self.assertFalse(self.run.session.records)
        self.assertIsNotNone(self.run.last_closed)


if __name__ == "__main__":
    unittest.main()
