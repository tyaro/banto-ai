"""Reader generation faults and fixed Windows query ABI; never call native APIs."""
import copy
import ctypes as C
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest
import tempfile
from unittest.mock import patch

from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_reader_reacquisition as reopen
from tests.fixtures.anomaly_v03_tracked_open import TrackedOpen
from tests import test_anomaly_v03_observed_evidence as observed
from tests import test_anomaly_v03_handle_owner as owners


class ReaderTable:
    def __init__(self, table, original):
        self.table, self.original = table, original
        self.views, self.hooks = {}, {}
        self.numbers = (404, 505)
        self.access = reopen.READER_ACCESS

    def hit(self, kind, handle):
        self.table.calls.append((kind, handle))
        if kind in self.hooks:
            self.hooks[kind](handle)

    def open_reader(self, cell, root, plan):
        self.hit("open", plan.writer_index)
        cell.handle = self.numbers[plan.writer_index - 1]
        self.table.live[cell.handle] = "original"
        original = self.original[plan.writer_index].observed
        view = SimpleNamespace(handle=cell.handle, identity=copy.deepcopy(original.identity),
                               raw=original.raw, sd=copy.deepcopy(original.sd))
        def check():
            self.hit("check", view.handle)
            return dict(view.identity)
        def read():
            self.hit("read", view.handle)
            return view.raw
        def security(handle):
            self.hit("sd", handle)
            return dict(view.sd)
        view.check, view.read, view.api = check, read, SimpleNamespace(security=security)
        self.views[cell.handle] = view
        self.hit("captured", cell.handle)

    def view(self, handle, plan):
        self.hit("view", handle)
        return self.views[handle]

    def granted_access(self, handle):
        self.hit("access", handle)
        return self.access

    def close_handle(self, handle):
        return self.table.close_handle(handle)

    def get_last_error(self):
        return self.table.get_last_error()


def setup(release=True):
    table, leases, observations, journal, group = observed.setup()
    plans = (reopen.ReadPlan(1, "facts.json", observed.FILES["facts.json"], observations[1]),
             reopen.ReadPlan(2, "marker-pending.json", observed.MARKER, observations[2]))
    backend = ReaderTable(table, leases)
    readers = reopen.ReacquiredReaders(backend, group=group, root_index=0, plans=plans, user=observed.USER)
    journal.begin("prepare")
    if release:
        group.owner.release_before_publish("prepare", (1, 2))
    table.calls.clear()
    return table, leases, group, backend, readers


class ReaderReacquisitionTests(unittest.TestCase):
    def test_readers_match_and_close_before_root_borrow_ends(self):
        table, leases, group, backend, readers = setup()
        parent_busy = []
        table.hooks[404] = lambda: parent_busy.append(group.owner._busy)
        table.hooks[505] = lambda: parent_busy.append(group.owner._busy)
        readers.acquire()
        self.assertEqual(parent_busy, [True, True])
        self.assertEqual(table.live, {101: "original"})
        self.assertTrue(all(row["state"] == "verified" and row["close"]["close_state"] == "closed"
                            for row in readers.snapshot()["readers"]))
        readers.finish()
        group.finish()
        self.assertEqual(table.calls[-1], ("close", 101))

    def test_reader_may_reuse_closed_writer_number_without_reclosing_old_slot(self):
        table, leases, group, backend, readers = setup()
        backend.numbers = (202, 303)
        readers.acquire()
        group.finish()
        self.assertEqual([row for row in table.calls if row[0] == "close"],
                         [("close", 303), ("close", 202), ("close", 101)])
        self.assertFalse(table.live)

    def test_live_or_unknown_writer_blocks_all_opens(self):
        for state in ("owned", "unknown"):
            table, leases, group, backend, readers = setup(False)
            if state == "unknown":
                group.owner._states[1] = "unknown"
                leases[1].close_state = "unknown"
            with self.assertRaises(owned.OwnershipError):
                readers.acquire()
            self.assertFalse(any(row[0] == "open" for row in table.calls))

    def test_failure_at_open_capture_view_access_or_read_closes_only_acquired_generation(self):
        for point in ("open", "captured", "view", "access", "read"):
            table, leases, group, backend, readers = setup()
            primary = MemoryError()
            backend.hooks[point] = lambda handle: (_ for _ in ()).throw(primary)
            with self.assertRaises(MemoryError) as caught:
                readers.acquire()
            self.assertIs(caught.exception, primary)
            self.assertEqual(table.live, {101: "original"})
            self.assertTrue(readers.snapshot()["resource_stop"])
            with self.assertRaises(MemoryError):
                group.finish()
            self.assertFalse(table.live)

    def test_same_bytes_different_identity_or_changed_bytes_or_descriptor_are_rejected(self):
        for changed in ("identity", "bytes", "sd"):
            table, leases, group, backend, readers = setup()
            def change(handle):
                view = backend.views[handle]
                if changed == "identity":
                    view.identity["file_id"] = "ab" * 16
                elif changed == "bytes":
                    view.raw = b"changed"
                else:
                    view.sd["mandatory_policy"] = 0  # Valid private shape, but changed from writer.
            backend.hooks["captured"] = change
            with self.assertRaises(owned.OwnershipError):
                readers.acquire()
            self.assertEqual(table.live, {101: "original"})
            self.assertFalse(any(row == ("open", 2) for row in table.calls))

    def test_extra_write_delete_or_missing_read_rights_fail_before_bytes_read(self):
        for access in (reopen.WRITER_ACCESS, reopen.READER_ACCESS | 0x10000,
                       reopen.READER_ACCESS & ~1, True):
            table, leases, group, backend, readers = setup()
            backend.access = access
            with self.assertRaises(owned.OwnershipError):
                readers.acquire()
            self.assertFalse(any(row[0] == "read" for row in table.calls))
            self.assertEqual(table.live, {101: "original"})

    def test_parent_resource_stop_or_swallowed_finish_aborts_after_each_callback(self):
        for kind in ("captured", "view", "access", "check", "read", "sd"):
            for action in ("resource", "finish"):
                table, leases, group, backend, readers = setup()
                def stop(handle):
                    if action == "resource":
                        group.owner._journal.stop(resource=True)
                    else:
                        try:
                            readers.finish()
                        except owned.OwnershipError:
                            pass
                backend.hooks[kind] = stop
                with self.assertRaises((MemoryError, owned.OwnershipError)):
                    readers.acquire()
                kinds = [row[0] for row in table.calls]
                last = max(i for i, name in enumerate(kinds) if name == kind)
                self.assertTrue(all(name == "close" for name in kinds[last + 1:]))
                self.assertEqual(table.live, {101: "original"})

    def test_parent_cannot_finish_while_reader_is_being_closed(self):
        table, leases, group, backend, readers = setup()
        def stop_parent():
            try:
                group.finish()
            except owned.OwnershipError:
                pass
        table.hooks[505] = stop_parent
        with self.assertRaises(owned.OwnershipError):
            readers.acquire()
        self.assertEqual(table.live, {101: "original"})
        with self.assertRaises(owned.OwnershipError):
            group.finish()
        self.assertFalse(table.live)

    def test_lost_close_reply_is_never_retried_and_remaining_readers_are_closed(self):
        table, leases, group, backend, readers = setup()
        def lost():
            table.live[505] = "new-object"
            raise MemoryError()
        table.hooks[505] = lost
        with self.assertRaises(MemoryError):
            readers.acquire()
        with self.assertRaises(MemoryError):
            readers.finish()
        self.assertEqual(table.live, {101: "original", 505: "new-object"})
        self.assertEqual(table.calls.count(("close", 505)), 1)
        self.assertEqual(table.calls.count(("close", 404)), 1)

    def test_primary_is_preserved_when_later_close_runs_out_of_memory(self):
        table, leases, group, backend, readers = setup()
        primary = ValueError("read")
        backend.hooks["read"] = lambda handle: (_ for _ in ()).throw(primary)
        table.hooks[404] = owners.raising(MemoryError())
        with self.assertRaises(ValueError) as caught:
            readers.acquire()
        self.assertIs(caught.exception, primary)
        self.assertTrue(readers.snapshot()["resource_stop"])

    def test_repeated_acquire_stops_without_reopening(self):
        table, leases, group, backend, readers = setup()
        readers.acquire()
        count = len(table.calls)
        with self.assertRaises(owned.OwnershipError):
            readers.acquire()
        self.assertEqual(len(table.calls), count)
        self.assertEqual(group.owner._journal.snapshot()["model_status"], "stopped")

    def test_invalid_plan_is_rejected_before_any_open(self):
        table, leases, group, backend, readers = setup()
        for plan in (replace(readers._plans[0], writer_index=True),
                     replace(readers._plans[0], name="../outside"),
                     replace(readers._plans[0], raw=b"changed")):
            with self.assertRaises((owned.OwnershipError, ValueError)):
                reopen.ReacquiredReaders(backend, group=group, root_index=0, plans=(plan,), user=observed.USER)
        self.assertFalse(table.calls)


class WindowsReaderBindingTests(unittest.TestCase):
    def test_scenario_cleanup_resource_failure_skips_normal_report(self):
        from tests.fixtures import anomaly_v03_observed_evidence_probe as driver
        with tempfile.TemporaryDirectory() as directory:
            source = SimpleNamespace(_leases=[], _resource=False,
                                     connect=lambda path: (_ for _ in ()).throw(ValueError()))
            sink = SimpleNamespace(_resource=False, finish=lambda **kwargs: None,
                                   snapshot=lambda: self.fail("resource snapshot"))
            scenario = SimpleNamespace(base=Path(directory),
                                       finish=lambda **kwargs: (_ for _ in ()).throw(MemoryError()),
                                       snapshot=lambda: self.fail("scenario resource snapshot"))
            with patch.object(driver, "WindowsPrivateSink", side_effect=(source, sink)), \
                 patch.object(driver.subprocess, "check_output", side_effect=("a" * 40, b"")), \
                 patch.object(driver.sys, "argv", ["probe", "--expected-head", "a" * 40, "--attempt", "1"]), \
                 patch.object(driver.os, "write") as notice:
                self.assertEqual(driver.main(scenario=scenario), 80)
            notice.assert_called_once()
            self.assertFalse((Path(directory) / "attempt-1/probe-result.json").exists())

    def test_native_scenario_queries_writers_then_verifies_readers_after_release(self):
        from tests.fixtures import anomaly_v03_reader_reacquisition_probe as probe
        table, leases, observations, journal, group = observed.setup()
        journal.begin("prepare")
        record = observed.record(group)
        backend = ReaderTable(table, leases)
        backend.granted_access = lambda handle: reopen.WRITER_ACCESS if handle in (202, 303) else reopen.READER_ACCESS
        scenario = probe.ReaderScenario()
        with patch.object(probe.reopen, "WindowsReaderBackend", return_value=backend):
            scenario.before_release(SimpleNamespace(_user=observed.USER), group, record)
        self.assertFalse(any(row[0] == "open" for row in table.calls))
        group.owner.release_before_publish("prepare", (1, 2))
        scenario.after_release()
        scenario.finish()
        group.finish()
        scenario.validate_terminal()
        self.assertEqual(scenario.snapshot()["reader_reacquisition"], "pass")
        self.assertFalse(table.live)

    def test_fixed_open_existing_read_rights_share_and_flags(self):
        calls = []
        root = Path("toy-root")
        source = SimpleNamespace(_root=root, _leases=[None, SimpleNamespace(handle=101)],
                                 _api=SimpleNamespace(k=SimpleNamespace(CreateFileW=lambda *args: calls.append(args) or 202)))
        backend = reopen.WindowsReaderBackend.__new__(reopen.WindowsReaderBackend)
        backend._source = source
        cell = TrackedOpen(backend)
        backend.open_reader(cell, SimpleNamespace(handle=101), SimpleNamespace(name="facts.json"))
        self.assertEqual(cell.handle, 202)
        self.assertEqual(calls[0][1:], (0x120081, 1, None, 3, 0x00200000, None))

    def test_object_basic_abi_size_and_failure_resource_translation(self):
        self.assertEqual(C.sizeof(reopen._ObjectBasic), 56)
        self.assertEqual(reopen._ObjectBasic.access.offset, 4)
        backend = reopen.WindowsReaderBackend.__new__(reopen.WindowsReaderBackend)
        def query(handle, kind, buffer, size, length):
            buffer._obj.access = reopen.READER_ACCESS
            length._obj.value = 56
            return 0
        backend._query = query
        self.assertEqual(backend.granted_access(202), reopen.READER_ACCESS)
        backend._query = lambda *args: -1073741801
        backend._map_status = lambda status: 8
        with self.assertRaises(owned.OwnershipError) as caught:
            backend.granted_access(202)
        self.assertTrue(owned._resource(caught.exception))
        self.assertEqual(caught.exception.ntstatus, 0xC0000017)
        def short(handle, kind, buffer, size, length):
            length._obj.value = 4
            return 0
        backend._query = short
        with self.assertRaises(owned.OwnershipError):
            backend.granted_access(202)
