"""Fault tests for the held-directory operation; no native execution."""
import ctypes as C
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
import tempfile
from unittest.mock import patch

from banto_ai import _anomaly_v03_windows as win
from tests.fixtures import anomaly_v03_directory_rename as move
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_observed_evidence as bridge
from tests.fixtures import anomaly_v03_reader_reacquisition as reopen
from tests.fixtures import anomaly_v03_sealed_files as seal
from tests import test_anomaly_v03_observed_evidence as observed
from tests import test_anomaly_v03_sealed_files as sealed


class DirectoryTable:
    def __init__(self, table, leases):
        self.table, self.leases = table, leases
        self.hooks = {}
        self.rights = {101: move.ROOT_ACCESS, 202: move.STAGE_ACCESS}
        self.names = {"stage": leases[1].observed.identity["file_id"]}
        self.error, self.result = 183, 1

    def hit(self, kind, handle=0):
        self.table.calls.append((kind, handle))
        if kind in self.hooks:
            self.hooks[kind](handle)

    def granted_access(self, handle):
        self.hit("access", handle)
        return self.rights[handle]

    def seal_directory(self, handle, *, guard, reject):
        self.hit("seal", handle)
        guard()
        self.leases[0 if handle == 101 else 1].observed.sd["aces"] = win._dacl(observed.USER, "frozen", True)[1]
        self.hit("set_done", handle)

    def set_file_information_by_handle(self, handle, kind, raw):
        self.hit("rename", handle)
        assert set(self.table.live) == {101, 202}
        assert handle == 202 and kind == 3
        assert raw[:8] == b"\0" * 8 and int.from_bytes(raw[8:16], "little") == 101
        assert int.from_bytes(raw[16:20], "little") == 14 and raw[20:-2].decode("utf-16-le") == "payload"
        assert len(raw) == 36 and raw[-2:] == b"\0\0"
        if "payload" in self.names or self.result == 0:
            return 0
        if type(self.result) is int and self.result == 1:
            self.names["payload"] = self.names.pop("stage")
        self.hit("after_effect", handle)
        return self.result

    def get_last_error(self):
        self.hit("error")
        return self.error


def setup(seal_children=True):
    table, leases, _, journal, group = observed.setup(adopt=False)
    leases[1].observed.identity["directory"] = True
    leases[1].observed.raw = None
    leases[1].observed.sd["aces"] = win._dacl(observed.USER, "private", True)[1]
    leases[2].observed.raw = observed.FILES["facts.json"]
    observations = tuple(bridge.inspect_native(lease, expected=lease.observed.raw, private_user=observed.USER)
                         for lease in leases)
    group.adopt(leases=leases, observations=observations, journal=journal, parents=(None, 0, 1))
    plans = (reopen.ReadPlan(2, "facts.json", observed.FILES["facts.json"], observations[2]),)
    file_backend = sealed.SealTable(table, leases)
    file_backend.accesses = {505: seal.FILE_SEAL_ACCESS}
    files = seal.SealedFiles(file_backend, group=group, root_index=1, plans=plans,
                             user=observed.USER, require_marker=False)
    journal.begin("prepare")
    group.owner.release_before_publish("prepare", (2,))
    if seal_children:
        files.seal_and_use(lambda pins: None)
    backend = DirectoryTable(table, leases)
    operation = move.DirectoryRename(backend, group=group, previous=observations[:2], files=files)
    table.calls.clear()
    return table, leases, group, files, backend, operation


class DirectoryRenameTests(unittest.TestCase):
    def test_seal_save_relative_rename_then_owner_closes_without_observation(self):
        table, leases, group, files, backend, operation = setup()
        saved = []
        def persist(directories, children):
            saved.append((directories, children))
            self.assertTrue(group.owner._busy)
            self.assertEqual(set(table.live), {101, 202})
            self.assertTrue(all(json_sd(d)["aces"][0][2] == 0x10156 for d in directories))
            self.assertEqual(children[0].pin.content_sha256, hashlib.sha256(observed.FILES["facts.json"]).hexdigest())
        operation.run(persist)
        self.assertEqual(len(saved), 1)
        self.assertEqual(backend.names, {"payload": leases[1].observed.identity["file_id"]})
        self.assertEqual(operation.snapshot()["rename"], "confirmed")
        self.assertEqual(operation.snapshot()["rights_after"], [0x1600a7, 0x1700a1])
        last = max(i for i, row in enumerate(table.calls) if row[0] == "rename")
        self.assertEqual(table.calls[last + 1:], [("after_effect", 202)])
        group.finish()
        self.assertEqual(table.calls[-2:], [("close", 202), ("close", 101)])
        self.assertFalse(table.live)
        self.assertEqual(group.owner._journal.snapshot()["commit_observation"], "not_started")

    def test_unfinished_or_unknown_child_generation_prevents_directory_calls(self):
        for status in ("unfinished", "unknown", "writer_unknown"):
            table, leases, group, files, backend, operation = setup(status != "unfinished")
            if status == "unknown":
                files._leases[0].close_state = "unknown"
            elif status == "writer_unknown":
                group.owner._states[2] = "unknown"
            with self.assertRaises(owned.OwnershipError):
                operation.run(lambda *args: self.fail("saved"))
            self.assertFalse(table.calls)

    def test_bad_initial_identity_sd_or_access_blocks_all_mutation(self):
        for defect in ("id", "sd", "access"):
            table, leases, group, files, backend, operation = setup()
            if defect == "id":
                leases[1].observed.identity["file_id"] = "ef" * 16
            elif defect == "sd":
                leases[1].observed.sd["mandatory_policy"] = 0
            else:
                backend.rights[202] |= 2
            with self.assertRaises(owned.OwnershipError):
                operation.run(lambda *args: None)
            self.assertFalse(any(row[0] in ("seal", "rename") for row in table.calls))

    def test_directory_change_reply_loss_is_unknown_and_never_retried(self):
        table, leases, group, files, backend, operation = setup()
        primary = RuntimeError("reply lost")
        backend.hooks["set_done"] = lambda h: (_ for _ in ()).throw(primary)
        with self.assertRaises(RuntimeError) as caught:
            operation.run(lambda *args: None)
        self.assertIs(caught.exception, primary)
        self.assertEqual(operation.snapshot()["directory_states"], ["not_started", "set_pending"])
        self.assertEqual(operation.snapshot()["rename"], "not_started")
        prior = table.calls[:]
        with self.assertRaises(owned.OwnershipError):
            operation.run(lambda *args: None)
        self.assertEqual(table.calls, prior)

    def test_frozen_readback_and_retained_rights_reject_changes(self):
        for defect in ("aces", "group", "policy", "rights"):
            table, leases, group, files, backend, operation = setup()
            def change(h):
                view = leases[1].observed
                if defect == "aces":
                    view.sd["aces"] = win._dacl(observed.USER, "private", True)[1]
                elif defect == "group":
                    view.sd["group"] = "S-1-5-18"
                elif defect == "policy":
                    view.sd["mandatory_policy"] = 0
                else:
                    backend.rights[h] ^= 2
            backend.hooks["set_done"] = change
            with self.assertRaises((owned.OwnershipError, win._Failure)):
                operation.run(lambda *args: self.fail("saved"))
            self.assertEqual([r for r in table.calls if r[0] == "seal"], [("seal", 202)])
            self.assertFalse(any(r[0] == "rename" for r in table.calls))

    def test_lost_or_wrong_save_response_prevents_rename(self):
        for result in ("lost", True):
            table, leases, group, files, backend, operation = setup()
            def persist(*args):
                if result == "lost":
                    raise MemoryError()
                return result
            with self.assertRaises((MemoryError, owned.OwnershipError)):
                operation.run(persist)
            self.assertEqual(operation.snapshot()["evidence"], "save_pending")
            self.assertFalse(any(r[0] == "rename" for r in table.calls))

    def test_changed_sealed_directory_after_save_prevents_rename(self):
        table, leases, group, files, backend, operation = setup()
        def persist(*args):
            leases[0].observed.sd["mandatory_policy"] = 0
        with self.assertRaises(owned.OwnershipError):
            operation.run(persist)
        self.assertEqual(operation.snapshot()["evidence"], "saved")
        self.assertFalse(any(r[0] == "rename" for r in table.calls))

    def test_stops_or_swallowed_reentry_after_native_boundaries_stop_following_io(self):
        for boundary in ("access", "seal", "set_done"):
            for action in ("resource", "reentry", "finish"):
                table, leases, group, files, backend, operation = setup()
                def stop(handle):
                    if action == "resource":
                        group.owner._journal.stop(resource=True)
                    else:
                        try:
                            operation.run(lambda *args: None) if action == "reentry" else group.finish()
                        except owned.OwnershipError:
                            pass
                backend.hooks[boundary] = stop
                with self.assertRaises((MemoryError, owned.OwnershipError)):
                    operation.run(lambda *args: None)
                self.assertEqual(table.calls[-1][0], boundary)
                self.assertEqual(operation.snapshot()["rename"], "not_started")

    def test_parent_stop_during_persist_prevents_fresh_observation(self):
        table, leases, group, files, backend, operation = setup()
        before = []
        def persist(*args):
            before.extend(table.calls)
            group.owner._journal.stop(resource=True)
        with self.assertRaises(MemoryError):
            operation.run(persist)
        self.assertEqual(table.calls, before)

    def test_existing_destination_is_not_replaced(self):
        table, leases, group, files, backend, operation = setup()
        backend.names["payload"] = "sentinel"
        with self.assertRaises(owned.OwnershipError) as caught:
            operation.run(lambda *args: None)
        self.assertEqual(caught.exception.winerror, 183)
        self.assertEqual(backend.names["payload"], "sentinel")
        self.assertIn("stage", backend.names)
        self.assertEqual(table.calls[-2:], [("rename", 202), ("error", 0)])
        self.assertEqual(operation.snapshot()["rename"], "pending")

    def test_rename_reply_loss_and_invalid_responses_are_not_success_or_retried(self):
        for result in ("loss", True, None, 1 << 31):
            table, leases, group, files, backend, operation = setup()
            primary = RuntimeError("rename response lost")
            if result == "loss":
                backend.hooks["after_effect"] = lambda h: (_ for _ in ()).throw(primary)
            else:
                backend.result = result
            with self.assertRaises((RuntimeError, owned.OwnershipError)):
                operation.run(lambda *args: None)
            self.assertEqual(operation.snapshot()["rename"], "pending")
            prior = table.calls[:]
            with self.assertRaises(owned.OwnershipError):
                operation.run(lambda *args: None)
            self.assertEqual(table.calls, prior)

    def test_known_resource_error_and_missing_error_code_stop(self):
        for code in (8, 0, True):
            table, leases, group, files, backend, operation = setup()
            backend.result, backend.error = 0, code
            with self.assertRaises(owned.OwnershipError):
                operation.run(lambda *args: None)
            self.assertEqual(operation.snapshot()["resource_stop"], code == 8)
            self.assertEqual(table.calls[-1][0], "error")

    def test_confirmed_rename_survives_late_stop_without_postrename_io(self):
        table, leases, group, files, backend, operation = setup()
        backend.hooks["after_effect"] = lambda h: group.owner._journal.stop(resource=True)
        with self.assertRaises(MemoryError):
            operation.run(lambda *args: None)
        self.assertEqual(operation.snapshot()["rename"], "confirmed")
        self.assertEqual(table.calls[-1][0], "after_effect")

    def test_marker_mode_remains_explicit_and_preserves_default(self):
        table, leases, group, files, backend, operation = setup()
        self.assertIsNone(files.snapshot().get("marker_index"))
        self.assertIsNone(files._marker_index)
        plans = files._plans
        with self.assertRaises(owned.OwnershipError):
            seal.SealedFiles(backend, group=group, root_index=1, plans=plans, user=observed.USER)
        with self.assertRaises(owned.OwnershipError):
            seal.SealedFiles(backend, group=group, root_index=1, plans=plans, user=observed.USER, require_marker=0)

    def test_native_role_access_is_limited_to_new_root_and_stage(self):
        fixture = move.WindowsDirectoryFixture()
        fixture._root = Path("C:/fresh")
        self.assertEqual(fixture._open_access(fixture._root, directory=True, create=False), 0x1600a7)
        self.assertEqual(fixture._open_access(fixture._root / "stage", directory=True, create=False), 0x1700a1)
        self.assertEqual(fixture._open_access(fixture._root.parent, directory=True, create=False), 0x20081)
        self.assertEqual(fixture._open_access(fixture._root / "stage/facts.json", directory=False, create=True), 0xC0020000)

    def test_native_rename_uses_exact_class_buffer_and_size(self):
        backend = move.WindowsDirectoryBackend.__new__(move.WindowsDirectoryBackend)
        calls = []
        def invoke(handle, kind, buffer, size):
            calls.append((handle, kind, C.string_at(buffer, size), size))
            return -1
        backend._source = SimpleNamespace(_api=SimpleNamespace(k=SimpleNamespace(SetFileInformationByHandle=invoke)))
        raw = bytes(range(36))
        self.assertEqual(backend.set_file_information_by_handle(202, 3, raw), -1)
        self.assertEqual(calls, [(202, 3, raw, 36)])

    def test_native_stage_file_path_rights_and_binding(self):
        backend = move.WindowsStageFileBackend.__new__(move.WindowsStageFileBackend)
        root, calls = Path("C:/fresh"), []
        backend._source = SimpleNamespace(_root=root,
            _leases=[None] * (len(root.parents)+1) + [SimpleNamespace(handle=202)],
            _api=SimpleNamespace(k=SimpleNamespace(CreateFileW=lambda *args: calls.append(args) or 505)))
        cell = SimpleNamespace(handle=None)
        backend.open_reader(cell, SimpleNamespace(handle=202), SimpleNamespace(name="facts.json"))
        self.assertEqual(calls[0], (str(root / "stage/facts.json"), 0x160081, 1, None, 3, 0x00200000, None))
        with self.assertRaises(owned.OwnershipError):
            backend.open_reader(cell, SimpleNamespace(handle=101), SimpleNamespace(name="facts.json"))

    def test_native_directory_dacl_uses_directory_specific_deny(self):
        helper = sealed.SealWin32BoundaryTests()
        backend, calls, errors, hooks = helper.backend()
        sddls = []
        backend._source._api.descriptor = lambda text: sddls.append(text) or 9
        backend.seal_directory(404, guard=lambda: None, reject=errors.append)
        self.assertEqual(sddls, [win._dacl(observed.USER, "frozen", True)[0]])
        self.assertIn("0x10156", sddls[0])
        self.assertEqual(calls, ["dacl", "set", "free"])
        self.assertFalse(errors)

    def test_probe_resource_failure_skips_normal_report_and_verification(self):
        from tests.fixtures import anomaly_v03_directory_rename_probe as probe
        with tempfile.TemporaryDirectory() as directory:
            source = SimpleNamespace(_leases=[], _resource=False,
                connect=lambda path: (_ for _ in ()).throw(MemoryError()))
            sink = SimpleNamespace(_resource=False, finish=lambda **kwargs: None,
                                   snapshot=lambda: self.fail("resource snapshot"))
            with patch.object(probe, "BASE", Path(directory)), \
                 patch.object(probe.move, "WindowsDirectoryFixture", return_value=source), \
                 patch.object(probe, "WindowsPrivateSink", return_value=sink), \
                 patch.object(probe.subprocess, "check_output", side_effect=("a"*40, b"")), \
                 patch.object(probe.sys, "argv", ["probe", "--expected-head", "a"*40, "--attempt", "1"]), \
                 patch.object(probe.os, "chdir"), patch.object(probe.os, "write") as notice:
                self.assertEqual(probe.main(), 80)
            notice.assert_called_once()
            self.assertFalse((Path(directory) / "attempt-1/probe-result.json").exists())


def json_sd(observation):
    import json
    return json.loads(observation.descriptor)
