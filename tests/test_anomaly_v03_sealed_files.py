"""File sealing faults with an object table and fake Win32 calls only."""
import copy
import ctypes as C
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import _anomaly_v03_windows as win
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_sealed_files as seal
from tests import test_anomaly_v03_reader_reacquisition as readers
from tests import test_anomaly_v03_observed_evidence as observed


class SealTable(readers.ReaderTable):
    def granted_access(self, handle):
        self.hit("access", handle)
        return self.accesses[handle]

    def seal(self, handle, *, guard, reject):
        self.hit("seal", handle)
        guard()
        self.views[handle].sd["aces"] = win._dacl(observed.USER, "frozen", False)[1]
        self.hit("set_done", handle)
        return None


def setup(release=True):
    table, leases, group, original, reader = readers.setup(release)
    backend = SealTable(table, leases)
    backend.accesses = {404: seal.FILE_SEAL_ACCESS, 505: seal.MARKER_SEAL_ACCESS}
    generation = seal.SealedFiles(backend, group=group, root_index=0, plans=reader._plans, user=observed.USER)
    return table, leases, group, backend, generation


class SealedFileTests(unittest.TestCase):
    def test_sealed_handles_stay_live_through_continuation_then_close_under_parent(self):
        table, leases, group, backend, files = setup()
        closed_while_parent_held = []
        for handle in (404, 505):
            table.hooks[handle] = lambda: closed_while_parent_held.append(group.owner._busy)
        def continuation(pins):
            self.assertTrue(group.owner._busy)
            self.assertEqual(pins.parent.handle, 101)
            self.assertEqual(pins.marker_index, 1)
            self.assertEqual([o.pin.handle for o in pins.observations], [404, 505])
            self.assertEqual(set(table.live), {101, 404, 505})
            self.assertTrue(all(state == "verified" for state in files._seal_states))
            self.assertEqual(files._held_access, [0x160081, 0x170081])
        files.seal_and_use(continuation)
        self.assertEqual(files.snapshot()["continuation"], "returned")
        self.assertEqual(closed_while_parent_held, [True, True])
        self.assertEqual(set(table.live), {101})
        group.finish()
        self.assertFalse(table.live)

    def test_last_object_identity_and_rights_checked_before_first_mutation(self):
        for defect in ("identity", "access"):
            table, leases, group, backend, files = setup()
            if defect == "access":
                backend.accesses[505] |= 2
            else:
                backend.hooks["captured"] = lambda h: backend.views[h].identity.update(
                    file_id="ab" * 16) if h == 505 else None
            with self.assertRaises(owned.OwnershipError):
                files.seal_and_use(lambda pins: self.fail("continuation after invalid pin"))
            self.assertFalse(any(row[0] == "seal" for row in table.calls))
            self.assertEqual(set(table.live), {101})

    def test_unreleased_writer_prevents_all_new_acquisition(self):
        table, leases, group, backend, files = setup(False)
        with self.assertRaises(owned.OwnershipError):
            files.seal_and_use(lambda pins: None)
        self.assertFalse(table.calls)

    def test_preseal_descriptor_refresh_rejects_change_before_mutation(self):
        table, leases, group, backend, files = setup()
        def change(handle):
            if handle == 505:
                backend.views[404].sd["mandatory_policy"] = 0
        backend.hooks["captured"] = change
        with self.assertRaises(owned.OwnershipError):
            files.seal_and_use(lambda pins: None)
        self.assertFalse(any(row[0] == "seal" for row in table.calls))

    def test_set_reply_loss_or_bad_return_stops_without_retry_or_continuation(self):
        for failure in ("loss", "result"):
            table, leases, group, backend, files = setup()
            original = backend.seal
            primary = RuntimeError("reply lost")
            def invoke(*args, **kwargs):
                original(*args, **kwargs)
                if failure == "loss":
                    raise primary
                return True
            backend.seal = invoke
            with self.assertRaises((RuntimeError, owned.OwnershipError)) as caught:
                files.seal_and_use(lambda pins: self.fail("continuation after unknown mutation"))
            if failure == "loss":
                self.assertIs(caught.exception, primary)
            self.assertEqual([r for r in table.calls if r[0] == "seal"], [("seal", 404)])
            self.assertEqual(files._seal_states, ["set_pending", "not_started"])
            prior = table.calls[:]
            with self.assertRaises(BaseException):
                files.finish()
            self.assertEqual(table.calls, prior)

    def test_frozen_policy_identity_bytes_and_non_dacl_fields_read_back(self):
        for defect in ("aces", "owner", "group", "integrity", "policy", "identity", "bytes"):
            table, leases, group, backend, files = setup()
            def change(handle):
                view = backend.views[handle]
                if defect == "aces":
                    view.sd["aces"] = win._dacl(observed.USER, "private", False)[1]
                elif defect in ("owner", "group"):
                    view.sd[defect] = "S-1-5-18"
                elif defect == "integrity":
                    view.sd["integrity"] = "S-1-16-4096"
                elif defect == "policy":
                    view.sd["mandatory_policy"] = 0
                elif defect == "identity":
                    view.identity["file_id"] = "cd" * 16
                else:
                    view.raw = b"changed"
            backend.hooks["set_done"] = change
            with self.assertRaises((owned.OwnershipError, win._Failure)):
                files.seal_and_use(lambda pins: self.fail("continuation after wrong readback"))
            self.assertEqual([r for r in table.calls if r[0] == "seal"], [("seal", 404)])
            self.assertEqual(set(table.live), {101})

    def test_actual_retained_rights_must_match_after_seal(self):
        table, leases, group, backend, files = setup()
        backend.hooks["set_done"] = lambda handle: backend.accesses.update({handle: seal.FILE_SEAL_ACCESS | 2})
        with self.assertRaises(owned.OwnershipError):
            files.seal_and_use(lambda pins: None)
        self.assertEqual(files._seal_states, ["readback_pending", "not_started"])

    def test_stop_after_each_seal_boundary_allows_only_close(self):
        for kind in ("seal", "set_done", "check", "read", "sd", "access"):
            for stop in ("resource", "reentry"):
                table, leases, group, backend, files = setup()
                def interrupt(handle):
                    if files._seal_states[0] == "not_started":
                        return
                    if stop == "resource":
                        group.owner._journal.stop(resource=True)
                    else:
                        try:
                            files.seal_and_use(lambda pins: None)
                        except owned.OwnershipError:
                            pass
                backend.hooks[kind] = interrupt
                with self.assertRaises((owned.OwnershipError, MemoryError)):
                    files.seal_and_use(lambda pins: self.fail("continued after stop"))
                kinds = [r[0] for r in table.calls]
                last = max(i for i, value in enumerate(kinds) if value == kind)
                self.assertTrue(all(value == "close" for value in kinds[last + 1:]), kinds)
                self.assertEqual(set(table.live), {101})

    def test_continuation_stop_or_bad_return_and_failure_are_terminal(self):
        for kind in ("stop", "return", "exception", "finish"):
            table, leases, group, backend, files = setup()
            primary = RuntimeError("continuation failed")
            def continuation(pins):
                if kind == "stop":
                    group.owner._journal.stop(resource=True)
                elif kind == "return":
                    return True
                elif kind == "exception":
                    raise primary
                else:
                    try:
                        group.finish()
                    except owned.OwnershipError:
                        pass
            with self.assertRaises((MemoryError, RuntimeError, owned.OwnershipError)) as caught:
                files.seal_and_use(continuation)
            if kind == "exception":
                self.assertIs(caught.exception, primary)
            self.assertEqual(files._continuation, "pending")
            self.assertEqual(set(table.live), {101})

    def test_primary_survives_late_close_resource_stop(self):
        table, leases, group, backend, files = setup()
        primary = RuntimeError("primary")
        table.hooks[505] = lambda: (_ for _ in ()).throw(MemoryError())
        def continuation(pins):
            raise primary
        with self.assertRaises(RuntimeError) as caught:
            files.seal_and_use(continuation)
        self.assertIs(caught.exception, primary)
        self.assertTrue(files.snapshot()["resource_stop"])
        self.assertEqual(files._leases[1].close_state, "unknown")
        self.assertEqual(files._leases[0].close_state, "closed")

    def test_no_second_attempt_or_unscoped_acquire(self):
        for operation in ("repeat", "acquire"):
            table, leases, group, backend, files = setup()
            if operation == "repeat":
                files.seal_and_use(lambda pins: None)
            before = table.calls[:]
            with self.assertRaises(owned.OwnershipError):
                files.acquire() if operation == "acquire" else files.seal_and_use(lambda pins: None)
            self.assertEqual(table.calls, before)
            self.assertTrue(files.snapshot()["stopped"])

    def test_marker_name_count_and_journal_binding_required(self):
        table, leases, group, backend, files = setup()
        plans = files._plans
        for changed in ((plans[0],), (plans[0], replace(plans[1], name="another.json"))):
            with self.assertRaises(owned.OwnershipError):
                seal.SealedFiles(backend, group=group, root_index=0, plans=changed, user=observed.USER)
        group.owner._journal._marker_sha256 = "a" * 64
        with self.assertRaises(owned.OwnershipError):
            seal.SealedFiles(backend, group=group, root_index=0, plans=plans, user=observed.USER)
        self.assertFalse(table.calls)

    def test_native_open_uses_role_access_and_noninherit_no_create_flags(self):
        table, leases, group, backend, files = setup()
        calls = []
        fake = seal.WindowsSealBackend.__new__(seal.WindowsSealBackend)
        root = Path("C:/fixture")
        fake._source = SimpleNamespace(_root=root, _leases=[None] * len(root.parents) + [SimpleNamespace(handle=101)],
            _api=SimpleNamespace(k=SimpleNamespace(CreateFileW=lambda *args: calls.append(args) or 404)))
        for plan, access in zip(files._plans, (0x160081, 0x170081)):
            cell = SimpleNamespace(handle=None)
            fake.open_reader(cell, group.owner._slots[0].pin, plan)
            self.assertEqual(calls[-1][1:], (access, 1, None, 3, 0x00200000, None))


class SealWin32BoundaryTests(unittest.TestCase):
    def test_scenario_queries_writers_seals_and_releases_all_handles(self):
        from tests.fixtures import anomaly_v03_sealed_files_probe as probe
        for close_loss in (False, True):
            table, leases, observations, journal, group = observed.setup()
            journal.begin("prepare")
            record = observed.record(group)
            backend = SealTable(table, leases)
            backend.accesses = {202: 0x12019f, 303: 0x12019f, 404: 0x160081, 505: 0x170081}
            scenario = probe.SealingScenario()
            with patch.object(probe.seal, "WindowsSealBackend", return_value=backend):
                scenario.before_release(SimpleNamespace(_user=observed.USER), group, record)
            self.assertFalse(any(row[0] == "open" for row in table.calls))
            group.owner.release_before_publish("prepare", (1, 2))
            if close_loss:
                table.hooks[505] = lambda: (_ for _ in ()).throw(RuntimeError("close lost"))
                with self.assertRaises(RuntimeError):
                    scenario.after_release()
                self.assertEqual(scenario.snapshot()["file_sealing"], "not_completed")
                with self.assertRaises(RuntimeError):
                    group.finish()
            else:
                scenario.after_release()
                scenario.finish()
                group.finish()
                scenario.validate_terminal()
                self.assertEqual(scenario.snapshot()["file_sealing"], "pass")
                self.assertFalse(table.live)

    def backend(self):
        calls, errors, hooks = [], [], {}
        def hit(kind):
            calls.append(kind)
            if kind in hooks:
                return hooks[kind]()
        def dacl(desc, present, acl, defaulted):
            hit("dacl")
            present._obj.value, acl._obj.value, defaulted._obj.value = 1, 8, 0
            return 1
        def descriptor(sddl):
            hit("descriptor")
            self.assertEqual(sddl, win._dacl(observed.USER, "frozen", False)[0])
            return 9
        def set_info(*args):
            self.assertEqual(args[0:5], (404, 1, 0x80000004, None, None))
            self.assertEqual(args[5].value, 8)
            self.assertIsNone(args[6])
            result = hit("set")
            return 0 if result is None else result
        def free(desc):
            self.assertEqual(desc, 9)
            return hit("free")
        def call(ok, reason):
            if not ok:
                raise owned.OwnershipError(reason, 5)
        backend = seal.WindowsSealBackend.__new__(seal.WindowsSealBackend)
        backend._source = SimpleNamespace(_user=observed.USER, _win=win, _api=SimpleNamespace(
            descriptor=descriptor, call=call, a=SimpleNamespace(GetSecurityDescriptorDacl=dacl, SetSecurityInfo=set_info),
            k=SimpleNamespace(LocalFree=free)))
        return backend, calls, errors, hooks

    def test_only_protected_dacl_set_and_single_descriptor_free(self):
        backend, calls, errors, hooks = self.backend()
        backend.seal(404, guard=lambda: None, reject=errors.append)
        self.assertEqual(calls, ["descriptor", "dacl", "set", "free"])
        self.assertFalse(errors)

    def test_guard_stop_after_each_native_boundary_skips_later_io_but_frees_descriptor(self):
        for point in ("descriptor", "dacl", "set"):
            backend, calls, errors, hooks = self.backend()
            stopped = []
            hooks[point] = lambda: stopped.append(True) and None
            def guard():
                if stopped:
                    raise MemoryError()
            with self.assertRaises(MemoryError):
                backend.seal(404, guard=guard, reject=errors.append)
            self.assertEqual(calls[-1], "free")
            self.assertEqual(calls.count("free"), 1)
            self.assertEqual(calls[calls.index(point) + 1:], ["free"])

    def test_null_missing_or_default_acl_rejected_without_set(self):
        for present, pointer, defaulted in ((0, 8, 0), (1, 0, 0), (1, 8, 1)):
            backend, calls, errors, hooks = self.backend()
            def dacl(desc, p, acl, d):
                p._obj.value, acl._obj.value, d._obj.value = present, pointer, defaulted
                return 1
            backend._source._api.a.GetSecurityDescriptorDacl = dacl
            with self.assertRaises(owned.OwnershipError):
                backend.seal(404, guard=lambda: None, reject=errors.append)
            self.assertEqual(calls, ["descriptor", "free"])

    def test_error_dword_or_invalid_return_and_late_free_failure_keep_primary(self):
        for result in (5, 8, True, -1, None):
            backend, calls, errors, hooks = self.backend()
            if result is None:
                hooks["set"] = lambda: (_ for _ in ()).throw(RuntimeError("lost"))
            else:
                hooks["set"] = lambda: result
            hooks["free"] = lambda: (_ for _ in ()).throw(MemoryError())
            with self.assertRaises((owned.OwnershipError, RuntimeError)) as caught:
                backend.seal(404, guard=lambda: None, reject=errors.append)
            self.assertNotIsInstance(caught.exception, MemoryError)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], MemoryError)
            self.assertEqual(calls[-2:], ["set", "free"])

    def test_free_failure_after_acknowledged_set_stops_before_readback(self):
        backend, calls, errors, hooks = self.backend()
        hooks["free"] = lambda: 9
        with self.assertRaises(owned.OwnershipError):
            backend.seal(404, guard=lambda: None, reject=errors.append)
        self.assertEqual(len(errors), 1)
        self.assertEqual(calls, ["descriptor", "dacl", "set", "free"])
