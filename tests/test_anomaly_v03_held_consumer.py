"""Existing SealedFiles plus fake synchronous Win32 read/metadata calls."""
import copy
import ctypes as C
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace
import unittest

from tests.fixtures import anomaly_v03_held_consumer as held
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_prepublication as prep
from tests import test_anomaly_v03_sealed_files as sealing
from tests import test_anomaly_v03_observed_evidence as observed


class NativeSurface:
    def __init__(self):
        self.calls, self.hooks, self.read_values = [], {}, {}
        self.active = lambda: True

    def hit(self, kind, handle):
        if not self.active():
            return
        self.calls.append((kind, handle))
        if kind in self.hooks:
            self.hooks[kind](handle)

    def attach(self, view):
        security = view.api.security
        def observe():
            self.hit("observe", view.handle)
            return copy.deepcopy(view.identity)
        def sd(handle):
            self.hit("security", handle)
            return security(handle)
        def standard(handle, kind, pointer, size):
            assert kind == 1 and size == 24
            self.hit("standard", handle)
            pointer._obj.end = pointer._obj.allocation = len(view.raw)
            pointer._obj.links = 1
            if "standard_result" in self.hooks:
                self.hooks["standard_result"](pointer._obj)
            return 1
        def seek(handle, offset, out, method):
            assert offset == 0 and out is None and method == 0
            self.hit("seek", handle)
            return 1
        def read(handle, buffer, requested, count, overlapped):
            assert overlapped is None and requested == len(buffer)
            self.hit("read", handle)
            value = view.raw
            C.memmove(buffer, value, min(len(value), requested))
            count._obj.value = len(value)
            if "read_result" in self.hooks:
                return self.hooks["read_result"](count._obj, requested)
            return 1
        def checked(result, reason):
            if not result:
                raise owned.OwnershipError(reason, 5)
        view.observe = observe
        view.api = SimpleNamespace(security=sd, call=checked,
            k=SimpleNamespace(GetFileInformationByHandleEx=standard, SetFilePointerEx=seek, ReadFile=read))


def setup(*, guard=lambda: None):
    table, leases, group, backend, files = sealing.setup()
    root = prep.Observation(group.owner._slots[0].pin,
        json.dumps(leases[0].observed.sd, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii"))
    surface = NativeSurface()
    surface.attach(leases[0].observed)
    original = backend.view
    def view(handle, plan):
        value = original(handle, plan)
        surface.attach(value)
        return value
    backend.view = view
    reader = held.HeldConsumer(files, held.WindowsHeldReadBackend(files), root_observation=root,
                               source_revision="a"*40, guard=guard)
    surface.active = lambda: reader._pins is not None
    return reader, surface, table, leases, group, backend, files


class HeldConsumerTests(unittest.TestCase):
    def test_existing_generation_collects_exact_bytes_inside_borrow_and_confirms_child_closes(self):
        reader, api, table, leases, group, backend, files = setup()
        def inspect(handle):
            self.assertTrue(group.owner._busy and files._busy)
            self.assertEqual(set(table.live), {101, 404, 505})
        api.hooks["read"] = inspect
        reader.run()
        self.assertEqual(reader._captured, [observed.FILES["facts.json"], observed.MARKER])
        self.assertEqual([h for kind,h in api.calls if kind == "read"], [404, 505])
        self.assertEqual(set(table.live), {101})
        self.assertEqual(reader.snapshot()["collection"], "complete")
        self.assertFalse(reader.requires_exit())
        self.assertTrue(all(row["close_state"] == "closed" for row in reader.snapshot()["files"]))
        with self.assertRaises(owned.OwnershipError) as caught:
            reader.consumer_payload()
        self.assertEqual(caught.exception.reason, "held_consumer_isolation_unresolved")
        self.assertFalse(reader.snapshot()["consumer_payload_released"])
        group.finish()
        self.assertFalse(table.live)

    def test_consumer_never_uses_bound_check_read_or_named_reopen(self):
        reader, api, table, leases, group, backend, files = setup()
        def forbid(handle):
            def no_path():
                self.fail("consumer called path-based view.check/read")
            for lease in (leases[0], *files._leases):
                lease.observed.check = lease.observed.read = no_path
        api.hooks["observe"] = forbid
        reader.run()
        self.assertEqual(reader.snapshot()["consumer_handles_acquired"], 0)
        self.assertFalse(reader.snapshot()["consumer_path_reopened"])

    def test_last_child_metadata_and_access_are_checked_before_first_read(self):
        for fault in ("descriptor", "access", "length"):
            reader, api, table, leases, group, backend, files = setup()
            if fault == "descriptor":
                api.hooks["security"] = lambda h: backend.views[h].sd.update(owner="changed") if h == 505 else None
            elif fault == "access":
                backend.hooks["access"] = lambda h: backend.accesses.update({h: 1}) if reader._pins is not None and h == 505 else None
            else:
                api.hooks["standard_result"] = lambda info: setattr(info, "end", info.end + 1)
            with self.assertRaises(owned.OwnershipError):
                reader.run()
            self.assertFalse(any(kind == "read" for kind,h in api.calls))
            self.assertEqual(reader._captured, [None,None])
            self.assertEqual(set(table.live), {101})

    def test_unknown_child_close_requires_parent_retention_and_no_second_close(self):
        reader, api, table, leases, group, backend, files = setup()
        def lost(): raise ValueError("close lost")
        table.hooks[404] = lost
        with self.assertRaises(ValueError): reader.run()
        calls = list(table.calls)
        self.assertTrue(reader.requires_exit())
        self.assertEqual(set(table.live), {101,404})
        with self.assertRaises(ValueError): files.finish()
        self.assertEqual(table.calls, calls)

    def test_earlier_file_or_root_change_during_later_read_invalidates_entire_capture(self):
        for scope in ("file", "root"):
            reader, api, table, leases, group, backend, files = setup()
            def change(handle):
                if handle == 505:
                    target = backend.views[404] if scope == "file" else leases[0].observed
                    target.sd["owner"] = "changed"
            api.hooks["read"] = change
            with self.assertRaises(owned.OwnershipError):
                reader.run()
            self.assertEqual(reader._captured, [None,None])
            self.assertEqual(reader.snapshot()["collection"], "incomplete")

    def test_postread_access_change_is_rejected(self):
        reader, api, table, leases, group, backend, files = setup()
        api.hooks["read"] = lambda h: backend.accesses.update({404: 1}) if h == 505 else None
        with self.assertRaises(owned.OwnershipError):
            reader.run()

    def test_short_overlong_invalid_count_or_false_response_stops_without_retry(self):
        for kind in ("short", "long", "invalid", "false", "boolean"):
            reader, api, table, leases, group, backend, files = setup()
            def result(count, requested):
                if kind == "short": count.value -= 1
                if kind == "long": count.value = requested
                if kind == "invalid": count.value = 0xffffffff
                return 0 if kind == "false" else True if kind == "boolean" else 1
            api.hooks["read_result"] = result
            with self.assertRaises(owned.OwnershipError):
                reader.run()
            self.assertEqual([h for kind,h in api.calls if kind == "read"], [404])
            self.assertEqual(reader._captured, [None,None])
            self.assertEqual(set(table.live), {101})

    def test_same_length_wrong_bytes_are_rejected(self):
        reader, api, table, leases, group, backend, files = setup()
        api.hooks["read"] = lambda h: setattr(backend.views[h], "raw", b"x"*len(backend.views[h].raw))
        with self.assertRaises(owned.OwnershipError):
            reader.run()
        self.assertEqual(reader._captured, [None,None])

    def test_failure_at_each_read_boundary_stops_further_observations_and_preserves_first(self):
        for point in ("observe", "security", "standard", "seek", "read"):
            reader, api, table, leases, group, backend, files = setup()
            primary = ValueError(point)
            def fail(handle):
                raise primary
            api.hooks[point] = fail
            with self.assertRaises(ValueError) as caught:
                reader.run()
            self.assertIs(caught.exception, primary)
            self.assertEqual(api.calls[-1][0], point)
            self.assertEqual(set(table.live), {101})

    def test_close_failure_or_late_guard_failure_discards_successful_capture(self):
        for point in ("close", "guard"):
            reader, api, table, leases, group, backend, files = setup()
            primary = ValueError(point)
            def fail(): raise primary
            if point == "close":
                table.hooks[404] = fail
            else:
                def after():
                    if files._done: raise primary
                reader._external_guard = after
            with self.assertRaises(ValueError) as caught:
                reader.run()
            self.assertIs(caught.exception, primary)
            self.assertEqual(reader._captured, [None,None])

    def test_primary_read_error_survives_later_close_memory_error(self):
        reader, api, table, leases, group, backend, files = setup()
        primary = ValueError("read")
        def fail_read(h): raise primary
        def fail_close(): raise MemoryError()
        api.hooks["read"] = fail_read
        table.hooks[404] = fail_close
        with self.assertRaises(ValueError) as caught:
            reader.run()
        self.assertIs(caught.exception, primary)
        self.assertTrue(reader._resource)
        with self.assertRaises(owned.OwnershipError): reader.snapshot()

    def test_final_guard_latched_generation_or_owner_error_cannot_leave_complete_bytes(self):
        for target in ("generation", "owner"):
            for error in (ValueError("stopped"), MemoryError("stopped")):
                reader, api, table, leases, group, backend, files = setup()
                def final_guard():
                    if files._done:
                        if target == "generation": files._record(error)
                        else: group.reject(error)
                reader._external_guard = final_guard
                with self.assertRaises(type(error)) as caught:
                    reader.run()
                self.assertIs(caught.exception, error)
                self.assertEqual(reader._captured,[None,None])
                self.assertEqual(reader._resource,isinstance(error,MemoryError))
                if not reader._resource:
                    self.assertEqual(reader.snapshot()["collection"],"incomplete")

    def test_final_guard_journal_stop_without_exception_prevents_completion(self):
        for resource in (False,True):
            reader, api, table, leases, group, backend, files = setup()
            def final_guard():
                if files._done: group.owner._journal.stop(resource=resource)
            reader._external_guard=final_guard
            with self.assertRaises(MemoryError if resource else owned.OwnershipError):
                reader.run()
            self.assertEqual(reader._captured,[None,None])
            self.assertEqual(reader._resource,resource)

    def test_final_guard_primary_survives_secondary_journal_snapshot_failure(self):
        for secondary in (MemoryError("journal"), RuntimeError("journal")):
            reader, api, table, leases, group, backend, files = setup()
            primary=ValueError("first upstream error")
            def broken_snapshot(): raise secondary
            def final_guard():
                if files._done:
                    files._record(primary)
                    group.owner._journal.snapshot=broken_snapshot
            reader._external_guard=final_guard
            with self.assertRaises(ValueError) as caught: reader.run()
            self.assertIs(caught.exception,primary)
            self.assertEqual(reader._captured,[None,None])
            self.assertEqual(reader._resource,isinstance(secondary,MemoryError))

    def test_first_error_survives_late_journal_resource_stop_during_close(self):
        reader, api, table, leases, group, backend, files = setup()
        primary=ValueError("read")
        def fail(h): raise primary
        api.hooks["read"]=fail
        table.hooks[404]=lambda: group.owner._journal.stop(resource=True)
        with self.assertRaises(ValueError) as caught: reader.run()
        self.assertIs(caught.exception,primary)
        self.assertTrue(reader._resource)
        self.assertEqual(reader._captured,[None,None])

    def test_swallowed_reentry_cannot_resume_read_or_finish(self):
        for point in ("observe", "security", "standard", "seek", "read"):
            reader, api, table, leases, group, backend, files = setup()
            def reenter(h):
                try: reader.run()
                except owned.OwnershipError: pass
            api.hooks[point] = reenter
            with self.assertRaises(owned.OwnershipError): reader.run()
            self.assertEqual(api.calls[-1][0], point)
            self.assertEqual(reader._captured, [None,None])

    def test_any_child_closed_or_transferred_during_read_stops_whole_set(self):
        for action in ("close", "transfer", "view", "plans"):
            reader, api, table, leases, group, backend, files = setup()
            def change(h):
                if action == "close": files._leases[1].close()
                elif action == "transfer": files._leases[1]._custodian = SimpleNamespace(active=False)
                elif action == "view": files._leases[1].observed = copy.copy(files._leases[1].observed)
                else: files._plans = files._plans[:-1]
            api.hooks["read"] = change
            with self.assertRaises(owned.OwnershipError): reader.run()
            self.assertEqual(reader._captured, [None,None])

    def test_stop_before_sealing_does_not_open_any_new_file(self):
        def stopped(): raise MemoryError()
        reader, api, table, leases, group, backend, files = setup(guard=stopped)
        with self.assertRaises(MemoryError): reader.run()
        self.assertEqual(api.calls, [])
        self.assertEqual(table.calls, [])
        self.assertTrue(reader._resource)

    def test_guard_limit_and_bad_guard_response_are_terminal(self):
        for mode in ("budget", "result"):
            reader, api, table, leases, group, backend, files = setup()
            if mode == "budget": reader.MAX_GUARDS = 1
            else: reader._external_guard = lambda: True
            with self.assertRaises((MemoryError, owned.OwnershipError)): reader.run()
            self.assertEqual(reader._captured, [None,None])

    def test_constructor_rejects_changed_root_marker_or_revision_without_io(self):
        for mode in ("root", "revision", "marker"):
            reader, api, table, leases, group, backend, files = setup()
            root = replace(reader._root, pin=replace(reader._root.pin, file_id=b"x"*16)) if mode == "root" else reader._root
            if mode == "marker": files._marker_index = None
            with self.assertRaises((owned.OwnershipError, held.model.ModelError)):
                held.HeldConsumer(files, reader.backend, root_observation=root,
                                  source_revision="b"*40 if mode == "revision" else "a"*40, guard=lambda: None)
            self.assertEqual(api.calls, [])
            self.assertEqual(table.calls, [])

    def test_reuse_cannot_read_again_and_snapshot_cannot_modify_captured_data(self):
        reader, api, table, leases, group, backend, files = setup()
        reader.run(); count = len(api.calls)
        row = reader.snapshot(); row["files"][0]["captured_sha256"] = "bad"
        self.assertEqual(reader.snapshot()["files"][0]["captured_sha256"], hashlib.sha256(observed.FILES["facts.json"]).hexdigest())
        with self.assertRaises(owned.OwnershipError): reader.run()
        self.assertEqual(len(api.calls), count)


class NativeReadBoundsTests(unittest.TestCase):
    def test_seek_failure_consumes_attempt_and_prevents_repeated_native_io(self):
        surface = NativeSurface()
        view = SimpleNamespace(handle=404, raw=b"data", identity={}, api=SimpleNamespace(security=lambda h: {}))
        surface.attach(view)
        def fail(h): raise ValueError("seek")
        surface.hooks["seek"] = fail
        backend = held.WindowsHeldReadBackend(None)
        lease = SimpleNamespace(handle=404, observed=view)
        storage = held.ReadStorage(4)
        with self.assertRaises(ValueError): backend.read(lease,storage,guard=lambda:None)
        self.assertTrue(storage.attempted and not storage.called)
        with self.assertRaises(owned.OwnershipError): backend.read(lease,storage,guard=lambda:None)
        self.assertEqual(surface.calls,[("seek",404)])

    def test_single_read_requests_expected_length_plus_one_including_empty_and_maximum(self):
        for length in (0, 1, held.model.MAX_FILE_BYTES):
            surface = NativeSurface()
            view = SimpleNamespace(handle=404, raw=b"x"*length, identity={}, api=SimpleNamespace(security=lambda h: {}))
            surface.attach(view)
            lease = SimpleNamespace(handle=404, observed=view)
            backend = held.WindowsHeldReadBackend(None)
            storage = held.ReadStorage(length)
            self.assertEqual(backend.read(lease, storage, guard=lambda: None), view.raw)
            self.assertEqual(len(storage.buffer), length+1)
            self.assertTrue(storage.called and storage.returned)
            with self.assertRaises(owned.OwnershipError): backend.read(lease, storage, guard=lambda: None)
            self.assertEqual(surface.calls, [("seek",404),("read",404)])

    def test_read_storage_is_bounded_and_standard_abi_is_correct(self):
        for value in (True, -1, held.model.MAX_FILE_BYTES+1):
            with self.assertRaises(owned.OwnershipError): held.ReadStorage(value)
        self.assertEqual((C.sizeof(held._Standard), held._Standard.pending.offset, held._Standard.directory.offset), (24,20,21))

    def test_pending_links_directory_and_negative_size_are_rejected_before_data_read(self):
        for field,value in (("pending",1),("links",2),("directory",1),("end",-1),("allocation",0)):
            reader, api, table, leases, group, backend, files = setup()
            api.hooks["standard_result"] = lambda info: setattr(info,field,value)
            with self.assertRaises(owned.OwnershipError): reader.run()
            self.assertFalse(any(kind=="read" for kind,h in api.calls))


if __name__ == "__main__":
    unittest.main()
