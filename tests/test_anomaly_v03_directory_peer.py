"""Faults in same-token capability acquisition; no native API invocation."""
from dataclasses import replace
import ctypes as C
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_directory_peer as peer
from tests.fixtures import anomaly_v03_directory_acquisition as acq
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_prepublication as prep
from tests.fixtures import anomaly_v03_rename_adapter as rename
from tests.test_anomaly_v03_directory_driver import Context
from tests.test_anomaly_v03_directory_acquisition import Function, failing


ORIGINAL = prep.Observation(rename.ObjectPin(303, 7, b"\x01" * 16, True), b"private")


class Backend:
    def __init__(self, original=ORIGINAL, calls=None):
        self.original = original
        self.calls = [] if calls is None else calls
        self.hooks, self.live, self.opened = {}, set(), {}
        self.results = [601, peer.INVALID, peer.INVALID, 604]
        self.codes = [0, 32, 5, 0]
        self.index = -1
        self.access_delta = 0
        self.observation = None

    def hit(self, event):
        self.calls.append(event)
        if event in self.hooks:
            self.hooks[event]()

    def open_existing(self, mask):
        self.index += 1
        self.hit("peer_open")
        result = self.results[self.index]
        if rename._handle(result):
            self.live.add(result)
            self.opened[result] = mask
        self.hit("peer_return")
        return result

    def get_last_error(self):
        self.hit("peer_error")
        return self.codes[self.index]

    def granted_access(self, handle):
        self.hit("peer_access")
        return self.opened[handle] ^ self.access_delta

    def inspect(self, handle, *, guard):
        self.hit("peer_inspect")
        guard()
        return self.observation or replace(self.original, pin=replace(self.original.pin, handle=handle))

    def close_handle(self, handle):
        self.hit("peer_close")
        self.live.remove(handle)
        self.hit("peer_closed")
        return 1


def setup():
    backend = Backend()
    holder = peer.PeerAcquisitions(backend, ORIGINAL, guard=lambda: backend.hit("peer_guard"))
    return backend, holder


class PeerAcquisitionTests(unittest.TestCase):
    def test_mixed_matrix_verifies_grants_and_records_only_known_denials(self):
        backend, holder = setup()
        holder.run()
        report = holder.snapshot()
        self.assertTrue(report["matrix_complete"])
        self.assertEqual([row["state"] for row in report["cases"]], ["granted", "denied", "denied", "granted"])
        self.assertEqual(backend.calls.count("peer_open"), 4)
        self.assertEqual(backend.calls.count("peer_inspect"), 2)
        self.assertEqual(backend.calls.count("peer_close"), 2)
        self.assertFalse(backend.live)
        self.assertFalse(holder.requires_exit())
        self.assertFalse(report["isolation_certified"])
        self.assertFalse(report["namespace_mutation_performed"])
        holder.finish()
        self.assertEqual(backend.calls.count("peer_close"), 2)

    def test_all_granted_and_all_mutation_requests_denied_are_observations_not_isolation(self):
        for results in ([601, 602, 603, 604], [601, peer.INVALID, peer.INVALID, peer.INVALID]):
            backend, holder = setup()
            backend.results = results
            backend.codes = [0, 32, 32, 32]
            holder.run()
            self.assertTrue(holder.snapshot()["matrix_complete"])
            self.assertFalse(holder.snapshot()["isolation_certified"])

    def test_control_denial_aborts_remaining_matrix_without_unknown_handle(self):
        backend, holder = setup()
        backend.results[0], backend.codes[0] = peer.INVALID, 32
        with self.assertRaises(owned.OwnershipError) as caught:
            holder.run()
        self.assertEqual(caught.exception.reason, "peer_control_denied")
        self.assertEqual(backend.calls.count("peer_open"), 1)
        self.assertFalse(holder.requires_exit())
        self.assertFalse(holder.snapshot()["matrix_complete"])

    def test_error_is_captured_before_next_guard(self):
        backend, holder = setup()
        holder.run()
        for index, event in enumerate(backend.calls):
            if event == "peer_error":
                self.assertEqual(backend.calls[index - 1], "peer_return")

    def test_undocumented_invalid_replies_and_error_codes_do_not_become_known_denials(self):
        for value, code in ((None, 5), (0, 32), (True, 5), (1.5, 5),
                            (peer.INVALID, 0), (peer.INVALID, True), (peer.INVALID, 2), (peer.INVALID, 8)):
            backend, holder = setup()
            backend.results[0], backend.codes[0] = value, code
            with self.assertRaises(owned.OwnershipError):
                holder.run()
            self.assertFalse(holder._denied[0])
            self.assertEqual(backend.calls.count("peer_open"), 1)
            self.assertNotIn("peer_access", backend.calls)
            self.assertTrue(holder.requires_exit())
            self.assertEqual(holder._resource, value == peer.INVALID and type(code) is int and code == 8)

    def test_open_response_loss_retains_unknown_handle_and_stops(self):
        backend, holder = setup()
        primary = MemoryError()
        backend.hooks["peer_return"] = failing(primary)
        with self.assertRaises(MemoryError) as caught:
            holder.run()
        self.assertIs(caught.exception, primary)
        self.assertEqual(backend.live, {601})
        self.assertNotIn("peer_close", backend.calls)
        self.assertTrue(holder.requires_exit())
        with self.assertRaises(owned.OwnershipError):
            holder.snapshot()

    def test_wrong_access_or_original_identity_descriptor_fails_before_next_open(self):
        for changed in ("access", "id", "sd", "handle", "shape"):
            backend, holder = setup()
            if changed == "access":
                backend.access_delta = 2
            elif changed == "id":
                backend.observation = replace(ORIGINAL, pin=replace(ORIGINAL.pin, handle=601, file_id=b"\x02" * 16))
            elif changed == "sd":
                backend.observation = replace(ORIGINAL, pin=replace(ORIGINAL.pin, handle=601), descriptor=b"other")
            elif changed == "handle":
                backend.observation = ORIGINAL
            else:
                backend.observation = True
            with self.assertRaises((owned.OwnershipError, AttributeError)):
                holder.run()
            self.assertEqual(backend.calls.count("peer_open"), 1)
            self.assertEqual(backend.calls.count("peer_close"), 1)
            self.assertFalse(backend.live)

    def test_primary_inspection_error_survives_reentrant_resource_close_failure(self):
        backend, holder = setup()
        primary = ValueError("inspect")
        backend.hooks["peer_inspect"] = failing(primary)
        def close():
            try:
                holder.finish()
            except BaseException:
                pass
            raise MemoryError()
        backend.hooks["peer_close"] = close
        with self.assertRaises(ValueError) as caught:
            holder.run()
        self.assertIs(caught.exception, primary)
        self.assertTrue(holder._resource)
        self.assertTrue(holder.requires_exit())

    def test_close_reply_loss_is_not_retried(self):
        backend, holder = setup()
        primary = OSError("lost")
        backend.hooks["peer_closed"] = failing(primary)
        for method in (holder.run, holder.finish, holder.finish):
            with self.assertRaises(OSError) as caught:
                method()
            self.assertIs(caught.exception, primary)
        self.assertFalse(backend.live)
        self.assertEqual(backend.calls.count("peer_close"), 1)
        self.assertTrue(holder.requires_exit())

    def test_swallowed_reentry_stops_at_all_boundaries(self):
        for boundary in ("peer_guard", "peer_open", "peer_return", "peer_error", "peer_access", "peer_inspect", "peer_close"):
            for action in ("run", "finish"):
                backend, holder = setup()
                def reenter():
                    try:
                        getattr(holder, action)()
                    except owned.OwnershipError:
                        pass
                backend.hooks[boundary] = reenter
                with self.subTest(boundary=boundary, action=action), self.assertRaises(owned.OwnershipError):
                    holder.run()
                self.assertFalse(holder.snapshot()["matrix_complete"])
                self.assertLessEqual(backend.calls.count("peer_open"), 2)

    def test_guard_failure_and_finish_before_run_prevent_any_open(self):
        for action in ("guard", "finish"):
            backend, holder = setup()
            if action == "guard":
                backend.hooks["peer_guard"] = failing(MemoryError())
            else:
                holder.finish()
                self.assertFalse(holder.snapshot()["matrix_complete"])
            with self.assertRaises((MemoryError, owned.OwnershipError)):
                holder.run()
            self.assertNotIn("peer_open", backend.calls)

    def test_windows_adapter_uses_only_noncreating_noninheriting_open_with_share_all(self):
        arguments = []
        context = SimpleNamespace(source_path=r"C:\fresh\source-fixture",
            sink=SimpleNamespace(_api=SimpleNamespace(k=SimpleNamespace(CreateFileW=Function(lambda *args: arguments.append(args) or 601)))))
        backend = peer.WindowsPeerBackend(context)
        self.assertEqual(backend.open_existing(0x1200C0), 601)
        self.assertEqual(arguments, [(r"C:\fresh\source-fixture", 0x1200C0, 7, None, 3, 0x02200000, None)])


class PeerTestContext(Context):
    def __init__(self):
        super().__init__()
        self.peers = self.peer_backend = None
        self.peer_hook = lambda backend: None

    def persist(self, observation):
        self.peer_backend = Backend(observation, self.api.calls)
        self.peer_hook(self.peer_backend)
        self.peers = peer.PeerAcquisitions(self.peer_backend, observation, guard=self.guard)
        self.peers.run()
        super().persist(observation)

    def resource_stop(self):
        return super().resource_stop() or self.peers is not None and self.peers._resource

    def child_requires_exit(self):
        return super().child_requires_exit() or self.peers is not None and self.peers.requires_exit()


class PeerDriverTests(unittest.TestCase):
    def setUp(self):
        for target, attribute, value in ((acq.sys, "version_info", (3, 14, 0)),
                                         (acq.os, "name", "nt"), (acq, "Path", lambda value: value)):
            stub = patch.object(target, attribute, value)
            stub.start()
            self.addCleanup(stub.stop)

    def test_all_peer_handles_close_before_evidence_and_original_root_close(self):
        context = PeerTestContext()
        runner = peer.PeerDriver(context)
        runner.run()
        self.assertEqual(runner.exit_code(), 0)
        self.assertTrue(context.peers.snapshot()["matrix_complete"])
        calls = context.api.calls
        self.assertLess(len(calls) - 1 - calls[::-1].index("peer_close"), calls.index("persist"))
        self.assertEqual(calls[-3:], ["close", "free", "ancestors_close"])

    def test_unknown_peer_retains_original_root_descriptor_and_ancestors_for_exit(self):
        for boundary in ("peer_return", "peer_close"):
            context = PeerTestContext()
            context.peer_hook = lambda backend: backend.hooks.update({boundary: failing(OSError("unknown"))})
            runner = peer.PeerDriver(context)
            with self.assertRaises(OSError):
                runner.run()
            self.assertEqual(runner.exit_code(), 81)
            self.assertEqual(context.api.live, {303})
            self.assertNotIn("close", context.api.calls)
            self.assertNotIn("free", context.api.calls)
            self.assertFalse(context.finished)
            self.assertNotIn("persist", context.api.calls)

    def test_known_peer_inspection_failure_closes_original_and_preserves_primary(self):
        context = PeerTestContext()
        primary = ValueError("peer inspect")
        context.peer_hook = lambda backend: backend.hooks.update(peer_inspect=failing(primary))
        runner = peer.PeerDriver(context)
        with self.assertRaises(ValueError) as caught:
            runner.run()
        self.assertIs(caught.exception, primary)
        self.assertFalse(context.api.live)
        self.assertTrue(context.finished)
        self.assertEqual(runner.exit_code(), 1)

    def test_resource_stop_in_peer_suppresses_evidence_and_normal_snapshot(self):
        context = PeerTestContext()
        context.peer_hook = lambda backend: backend.hooks.update(peer_inspect=failing(MemoryError()))
        runner = peer.PeerDriver(context)
        with self.assertRaises(MemoryError):
            runner.run()
        self.assertNotIn("persist", context.api.calls)
        self.assertEqual(runner.exit_code(), 80)
        with self.assertRaises(owned.OwnershipError):
            runner.snapshot()


class TokenBasisTests(unittest.TestCase):
    def setup_sink(self, **changes):
        closed = []
        profile = {"user": ["S-1-5-21-1-2-3-1001", 0], "type": 1, "elevated": 0,
                   "integrity": "S-1-16-8192", "privileges": [["SeChangeNotifyPrivilege", 3]],
                   "token_id": "01", "modified_id": "02", "authentication_id": "03", **changes}
        def open_token(process, mask, pointer):
            self.assertEqual(mask, 8)
            pointer._obj.value = 707
            return 1
        sink = peer.ProfiledSink()
        sink._win = SimpleNamespace(H=C.c_void_p)
        sink._api = SimpleNamespace(a=SimpleNamespace(OpenProcessToken=open_token),
            k=SimpleNamespace(GetCurrentProcess=lambda: -1), profile=lambda handle: profile,
            call=lambda ok, reason: owned._need(ok, reason))
        sink._backend = SimpleNamespace(close_handle=lambda handle: closed.append(handle) or 1)
        return sink, closed

    def test_query_only_token_is_closed_and_initial_basis_recorded(self):
        sink, closed = self.setup_sink()
        self.assertEqual(sink._read_user(), "S-1-5-21-1-2-3-1001")
        self.assertEqual(closed, [707])
        self.assertEqual(sink.token_basis["enabled_privileges"], ["SeChangeNotifyPrivilege"])

    def test_elevation_integrity_and_enabled_backup_privileges_reject(self):
        for changes in ({"elevated": 1}, {"type": 2}, {"integrity": "S-1-16-12288"},
                        {"privileges": [["SeBackupPrivilege", 2]]}, {"privileges": [["SeRestorePrivilege", 2]]}):
            sink, closed = self.setup_sink(**changes)
            with self.assertRaises(owned.OwnershipError):
                sink._read_user()
            self.assertEqual(closed, [707])

    def test_token_close_resource_failure_is_propagated(self):
        sink, closed = self.setup_sink()
        sink._backend.close_handle = lambda handle: failing(MemoryError())()
        with self.assertRaises(MemoryError):
            sink._read_user()
        self.assertTrue(sink._resource)
        self.assertEqual(sink._token.close_state, "unknown")


if __name__ == "__main__":
    unittest.main()
