"""Same-parent wire, ownership and refusal tests; no real DLL invocation."""
import ctypes as C
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_anomaly_v03_directory_rename as previous
from tests.fixtures import anomaly_v03_directory_rename as directory
from tests.fixtures import anomaly_v03_directory_rename_probe as probe
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_same_parent_rename as same


class SameParentTable(previous.DirectoryTable):
    def set_file_information_by_handle(self, handle, kind, raw):
        self.hit("rename", handle)
        assert set(self.table.live) == {101, 202} and handle == 202 and kind == 3
        assert raw[:16] == b"\0" * 16 and int.from_bytes(raw[16:20], "little") == 14
        assert raw[20:] == "payload".encode("utf-16-le") + b"\0\0"
        if "payload" in self.names or self.result == 0:
            return 0
        if type(self.result) is int and self.result == 1:
            self.names["payload"] = self.names.pop("stage")
        self.hit("after_effect", handle)
        return self.result


def setup():
    table, leases, group, files, _, old = previous.setup()
    backend = SameParentTable(table, leases)
    operation = same.SameParentDirectoryRename(backend, group=group, previous=old._previous, files=files)
    return table, leases, group, files, backend, operation


def native_backend(result=0, backend_type=same.WindowsNtSameParentBackend):
    calls = []
    class ApiFunction:
        def __call__(self, *args):
            calls.append(args)
            return result
    backend = backend_type(SimpleNamespace(_api=SimpleNamespace(n=SimpleNamespace(
        NtQueryObject=ApiFunction(), RtlNtStatusToDosError=ApiFunction(), NtSetInformationFile=ApiFunction()))))
    backend._map_status = lambda status: 5
    return backend, calls


class SameParentRenameTests(unittest.TestCase):
    def test_wire_uses_null_root_and_native_backend_keeps_exact_leaf(self):
        raw = same.same_parent_request()
        self.assertEqual(len(raw), 36)
        self.assertEqual(raw[:20], b"\0"*16 + b"\x0e\0\0\0")
        self.assertEqual(raw[20:], "payload".encode("utf-16-le") + b"\0\0")
        backend, calls = native_backend()
        self.assertEqual(backend.set_file_information_by_handle(202, 3, raw), 1)
        handle, iosb, buffer, length, kind = calls[0]
        self.assertEqual((handle, length, kind), (202, 40, 10))
        self.assertEqual(C.string_at(buffer, length), raw + b"\0"*4)
        self.assertEqual(backend.native_snapshot()["name_resolution"], "source_parent")

    def test_both_directories_stay_frozen_with_live_parent_and_closed_children(self):
        table, leases, group, files, backend, operation = setup()
        def save(directories, children):
            self.assertEqual(set(table.live), {101, 202})
            self.assertTrue(group.owner._busy)
            self.assertTrue(all(previous.json_sd(item)["aces"][0][2] == 0x10156 for item in directories))
        operation.run(save)
        self.assertEqual([row for row in table.calls if row[0] == "seal"], [("seal", 202), ("seal", 101)])
        snapshot = operation.snapshot()
        self.assertEqual(snapshot["parent_policy"], "frozen")
        self.assertEqual(snapshot["directory_states"], ["verified", "verified"])
        self.assertEqual(snapshot["rename"], "confirmed")
        self.assertTrue(snapshot["root_directory_is_null"])
        self.assertFalse(snapshot["native_publication_performed"])
        last = max(i for i, row in enumerate(table.calls) if row[0] == "rename")
        self.assertEqual(table.calls[last+1:], [("after_effect", 202)])
        group.finish()
        self.assertFalse(table.live)

    def test_held_root_and_same_parent_backends_reject_each_others_wire(self):
        backend, calls = native_backend()
        held = directory.rename.rename_request(101, "rename_payload")
        for raw in (held, bytearray(same.same_parent_request()), b"\x01" + same.same_parent_request()[1:],
                    same.same_parent_request()[:20] + "../evil".encode("utf-16-le") + b"\0\0"):
            with self.assertRaises((owned.OwnershipError, directory.rename.AdapterError)):
                backend.set_file_information_by_handle(202, 3, raw)
        self.assertFalse(calls)
        backend, calls = native_backend(backend_type=directory.WindowsNtDirectoryBackend)
        with self.assertRaises(directory.rename.AdapterError):
            backend.set_file_information_by_handle(202, 3, same.same_parent_request())
        self.assertFalse(calls)

    def test_source_parent_binding_is_not_removed_with_null_wire_root(self):
        table, leases, group, files, backend, operation = setup()
        group.owner._slots = tuple(replace(slot, parent=None) if i == 1 else slot for i, slot in enumerate(group.owner._slots))
        with self.assertRaises(owned.OwnershipError):
            same.SameParentDirectoryRename(backend, group=group, previous=operation._previous, files=files)
        self.assertFalse(table.calls)

    def test_parent_change_after_evidence_prevents_native_request(self):
        table, leases, group, files, backend, operation = setup()
        def replace_parent(*args):
            leases[0].observed.identity["file_id"] = "ab"*16
        with self.assertRaises(owned.OwnershipError):
            operation.run(replace_parent)
        self.assertFalse(any(row[0] == "rename" for row in table.calls))

    def test_unknown_child_close_prevents_directory_mutation(self):
        table, leases, group, files, backend, operation = setup()
        files._leases[0].close_state = "unknown"
        with self.assertRaises(owned.OwnershipError):
            operation.run(lambda *args: None)
        self.assertFalse(table.calls)

    def test_destination_collision_remains_failure_and_preserves_sentinel(self):
        table, leases, group, files, backend, operation = setup()
        backend.names["payload"] = "sentinel"
        with self.assertRaises(owned.OwnershipError) as caught:
            operation.run(lambda *args: None)
        self.assertEqual(caught.exception.winerror, 183)
        self.assertEqual(backend.names["payload"], "sentinel")
        self.assertIn("stage", backend.names)
        self.assertEqual(operation.snapshot()["rename"], "pending")

    def test_reply_loss_never_retries_or_switches_request_form(self):
        table, leases, group, files, backend, operation = setup()
        primary = RuntimeError("lost response")
        backend.hooks["after_effect"] = lambda h: (_ for _ in ()).throw(primary)
        with self.assertRaises(RuntimeError) as caught:
            operation.run(lambda *args: None)
        self.assertIs(caught.exception, primary)
        self.assertEqual(operation.snapshot()["rename"], "pending")
        before = table.calls[:]
        with self.assertRaises(owned.OwnershipError):
            operation.run(lambda *args: None)
        self.assertEqual(before, table.calls)

    def test_native_pending_or_interrupted_return_retains_buffers(self):
        for response in (0x103, "interrupted"):
            backend, calls = native_backend(0x103)
            if response == "interrupted":
                backend._set = lambda *args: (_ for _ in ()).throw(MemoryError())
            with self.assertRaises(MemoryError):
                backend.set_file_information_by_handle(202, 3, same.same_parent_request())
            self.assertTrue(backend.completion_unknown)
            self.assertIsNotNone(backend._buffer)
            self.assertIsNotNone(backend._io)

    def test_probe_rejects_second_attempt_and_combined_modes_before_start(self):
        with self.assertRaises(owned.OwnershipError):
            probe.main(same_parent=True, compare_parent_policy=True)
        with patch.object(probe.sys, "argv", ["probe", "--expected-head", "a"*40, "--attempt", "2"]), \
                patch.object(probe.subprocess, "check_output") as git, self.assertRaises(owned.OwnershipError):
            probe.main(same_parent=True)
        git.assert_not_called()
