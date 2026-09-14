"""Pure acquisition and sink fault tests; no Windows DLL loaded here."""
import ctypes
from pathlib import Path
from types import SimpleNamespace
import hashlib
import unittest

from tests.fixtures.anomaly_v03_tracked_open import TrackedOpen
from tests.fixtures.anomaly_v03_private_sink import WindowsPrivateSink
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests import test_anomaly_v03_handle_owner as owner_tests


class TrackedOpenTests(unittest.TestCase):
    def setup_lease(self):
        backend = owner_tests.ClosingTable((303,))
        lease = TrackedOpen(backend)
        def opener(cell):
            cell.handle = 303
        return backend, lease, opener

    def test_capture_precedes_inspection_and_close_is_confirmed_once(self):
        backend, lease, opener = self.setup_lease()
        observation = object()
        self.assertIs(lease.acquire(opener, lambda value: observation), observation)
        self.assertEqual(lease.handle, 303)
        lease.close()
        lease.close()
        self.assertEqual(backend.calls, [("close", 303)])
        self.assertEqual(lease.snapshot()["close_state"], "closed")

    def test_failure_after_raw_capture_and_during_inspection_releases_handle(self):
        for boundary in ("open", "inspect"):
            with self.subTest(boundary=boundary):
                backend, lease, opener = self.setup_lease()
                primary = MemoryError()
                def fail_open(cell):
                    opener(cell)
                    raise primary
                def fail_inspect(value):
                    raise primary
                with self.assertRaises(MemoryError) as caught:
                    lease.acquire(fail_open if boundary == "open" else opener,
                                  fail_inspect if boundary == "inspect" else lambda value: object())
                self.assertIs(caught.exception, primary)
                self.assertEqual(backend.live, {})
                self.assertEqual(backend.calls, [("close", 303)])
                self.assertTrue(lease.snapshot()["resource_stop"])

    def test_unavailable_raw_handle_is_never_guessed_or_closed(self):
        for value in (None, 0, True, -1, (1 << 64) - 1):
            with self.subTest(value=value):
                backend, lease, _ = self.setup_lease()
                with self.assertRaises(owned.OwnershipError):
                    lease.acquire(lambda cell: setattr(cell, "handle", value), lambda handle: self.fail("inspect"))
                self.assertEqual(backend.calls, [])
                self.assertEqual(lease.snapshot()["close_state"], "unavailable")

    def test_primary_is_preserved_when_close_also_fails(self):
        backend, lease, opener = self.setup_lease()
        primary = ValueError("probe")
        backend.hooks[303] = owner_tests.raising(MemoryError())
        def inspect(value):
            raise primary
        with self.assertRaises(ValueError) as caught:
            lease.acquire(opener, inspect)
        self.assertIs(caught.exception, primary)
        self.assertEqual(lease.snapshot()["close_state"], "unknown")
        self.assertTrue(lease.snapshot()["resource_stop"])
        with self.assertRaises(ValueError):
            lease.close()
        self.assertEqual(backend.calls, [("close", 303)])

    def test_swallowed_close_or_reacquire_during_open_is_rejected(self):
        for action in ("close", "open"):
            with self.subTest(action=action):
                backend, lease, opener = self.setup_lease()
                def reenter(value):
                    try:
                        lease.close() if action == "close" else lease.acquire(opener, lambda handle: object())
                    except owned.OwnershipError:
                        pass
                    return object()
                with self.assertRaises(owned.OwnershipError):
                    lease.acquire(opener, reenter)
                self.assertEqual(backend.calls, [("close", 303)])
                self.assertNotEqual(lease.state, "ready")

    def test_lost_close_reply_cannot_close_reused_number(self):
        backend, lease, opener = self.setup_lease()
        lease.acquire(opener, lambda value: object())
        def lost():
            backend.live[303] = "new-object"
            raise MemoryError()
        backend.hooks[303] = lost
        for _ in range(2):
            with self.assertRaises(MemoryError):
                lease.close()
        self.assertEqual(backend.calls, [("close", 303)])
        self.assertEqual(backend.live[303], "new-object")


class FakeNative:
    def __init__(self):
        self.calls, self.faults, self.files, self.live = [], {}, {}, {}
        self.current = None
        self.short = self.changed = False
        self.security_count = 0

    def hit(self, name):
        self.calls.append(name)
        if name in self.faults:
            self.faults[name]()

    def WriteFile(self, handle, buffer, count, written, unused):
        self.hit("write")
        self.files[self.current] = buffer.raw[:count]
        written._obj.value = count - 1 if self.short else count
        return 1

    def FlushFileBuffers(self, handle):
        self.hit("flush")
        return 1

    def close_handle(self, handle):
        self.hit("close")
        del self.live[handle]
        return 1

    def get_last_error(self):
        return 5

    def security(self, handle):
        self.security_count += 1
        self.hit("security")
        return {"private": True}

    def read(self):
        self.hit("read")
        return b"changed" if self.changed else self.files[self.current]

    def call(self, result, reason):
        if not result:
            raise owned.OwnershipError(reason, 5)


def make_sink():
    native = FakeNative()
    sink = WindowsPrivateSink()
    sink._started = sink._connected = True
    sink._root, sink._user = Path("toy-root"), "toy-user"
    sink._api = SimpleNamespace(k=native, call=native.call, security=native.security)
    sink._win = SimpleNamespace(D=ctypes.c_uint32, _verify_sd=lambda *args: None)
    sink._check = lambda: owned._need(sink._connected and not sink._finished and not sink._failed)
    def open_file(path, *, directory, create):
        native.hit("create")
        if path.name in native.files:
            raise FileExistsError("exists")
        native.current = path.name
        native.files[path.name] = b""
        lease = TrackedOpen(native)
        sink._leases.append(lease)
        def acquire(cell):
            cell.handle = 303
            native.live[303] = "owned"
        lease.acquire(acquire, lambda handle: SimpleNamespace(read=native.read))
        return lease
    sink._open = open_file
    return sink, native


class PrivateSinkProtocolTests(unittest.TestCase):
    raw = b'{"toy":true}\n'

    def save(self, sink, step="prepare"):
        sink.persist_evidence(step, self.raw, hashlib.sha256(self.raw).hexdigest())

    def test_save_requires_write_flush_readback_policy_and_close_before_success(self):
        sink, native = make_sink()
        self.save(sink)
        self.assertEqual(native.calls, ["create", "security", "write", "flush", "read", "security", "close"])
        self.assertEqual(native.live, {})
        self.assertEqual(sink.snapshot()["files"][0]["state"], "saved")
        sink.finish()
        self.assertEqual(native.calls.count("close"), 1)

    def test_failure_at_each_io_boundary_stops_and_closes_once_without_retry(self):
        for boundary in ("create", "security", "write", "flush", "read", "close"):
            with self.subTest(boundary=boundary):
                sink, native = make_sink()
                primary = MemoryError()
                native.faults[boundary] = owner_tests.raising(primary)
                with self.assertRaises(MemoryError) as caught:
                    self.save(sink)
                self.assertIs(caught.exception, primary)
                self.assertTrue(sink.snapshot()["resource_stop"])
                self.assertNotEqual(sink.snapshot()["files"][0]["state"], "saved")
                before = native.calls[:]
                with self.assertRaises(ValueError):
                    self.save(sink)
                self.assertEqual(native.calls, before)
                try:
                    sink.finish()
                except MemoryError:
                    pass
                self.assertLessEqual(native.calls.count("close"), 1)

    def test_short_write_and_changed_readback_stop(self):
        for kind in ("short", "changed"):
            with self.subTest(kind=kind):
                sink, native = make_sink()
                setattr(native, kind, True)
                with self.assertRaises(owned.OwnershipError):
                    self.save(sink)
                self.assertEqual(native.calls.count("close"), 1)
                if kind == "short":
                    self.assertNotIn("flush", native.calls)

    def test_existing_file_is_preserved_and_duplicate_phase_never_reopens(self):
        sink, native = make_sink()
        native.files["prepare.json"] = b"previous"
        with self.assertRaises(FileExistsError):
            self.save(sink)
        self.assertEqual(native.files["prepare.json"], b"previous")
        sink, native = make_sink()
        self.save(sink)
        before = native.calls[:]
        with self.assertRaises(owned.OwnershipError):
            self.save(sink)
        self.assertEqual(native.calls, before)
        self.assertEqual(native.files["prepare.json"], self.raw)

    def test_bad_input_stops_before_file_creation(self):
        for step, raw, digest in (("../bad", self.raw, "a" * 64), ("prepare", b"", "a" * 64),
                                  ("prepare", b"x" * (512 * 1024 + 1), "a" * 64),
                                  ("prepare", self.raw, "a" * 64)):
            sink, native = make_sink()
            with self.assertRaises(owned.OwnershipError):
                sink.persist_evidence(step, raw, digest)
            self.assertEqual(native.calls, [])

    def test_swallowed_reentry_or_finish_inside_write_stops_before_flush(self):
        for kind in ("save", "finish"):
            with self.subTest(kind=kind):
                sink, native = make_sink()
                def reenter():
                    try:
                        self.save(sink) if kind == "save" else sink.finish()
                    except owned.OwnershipError:
                        pass
                native.faults["write"] = reenter
                with self.assertRaises(owned.OwnershipError):
                    self.save(sink)
                self.assertNotIn("flush", native.calls)
                self.assertEqual(native.calls.count("close"), 1)

    def test_descriptor_free_secondary_failure_preserves_primary(self):
        sink, native = make_sink()
        sink._win._dacl = lambda *args: ("toy", [])
        sink._api.descriptor = lambda sddl: 100
        native.LocalFree = lambda pointer: 100
        primary = ValueError("create")
        with self.assertRaises(ValueError) as caught:
            with sink._descriptor(False):
                raise primary
        self.assertIs(caught.exception, primary)
        self.assertTrue(sink.snapshot()["stopped"])

    def test_actual_core_failures_and_nested_resource_codes_are_classified(self):
        from banto_ai import _anomaly_v03_windows as win
        for code in (5, 8, 14, 39, 112, 1450, 1451, 1452, 1453, 1454, 1455, 1816):
            for nested in (False, True):
                with self.subTest(code=code, nested=nested):
                    sink, native = make_sink()
                    error = win._Failure("sink_write", code)
                    if nested:
                        outer = RuntimeError("wrapped")
                        outer.__cause__ = error
                        error = outer
                    native.faults["write"] = owner_tests.raising(error)
                    with self.assertRaises(type(error)) as caught:
                        self.save(sink)
                    self.assertIs(caught.exception, error)
                    self.assertEqual(sink.snapshot()["resource_stop"], code != 5)
                    self.assertEqual(native.calls.count("close"), 1)

    def test_failed_token_call_never_adopts_nonzero_output(self):
        sink, native = make_sink()
        sink._backend = native
        sink._win.H = ctypes.c_void_p
        sink._api.k.GetCurrentProcess = lambda: -1
        def false_output(process, access, output):
            output._obj.value = 303
            return 0
        sink._api.a = SimpleNamespace(OpenProcessToken=false_output)
        sink._api.profile = lambda value: self.fail("failed token inspected")
        with self.assertRaises(owned.OwnershipError):
            sink._read_user()
        self.assertEqual(native.calls, [])
        self.assertIsNone(sink._token.handle)
        self.assertEqual(sink._token.snapshot()["close_state"], "unavailable")

    def test_swallowed_finish_from_close_cannot_report_save_success(self):
        sink, native = make_sink()
        def reenter():
            try:
                sink.finish()
            except owned.OwnershipError:
                pass
        native.faults["close"] = reenter
        with self.assertRaises(owned.OwnershipError):
            self.save(sink)
        self.assertNotEqual(sink.snapshot()["files"][0]["state"], "saved")
        self.assertTrue(sink.snapshot()["stopped"])
        self.assertEqual(native.calls.count("close"), 1)

    def test_probe_resource_stop_skips_snapshot_and_normal_report(self):
        import tempfile
        from unittest.mock import patch
        from tests.fixtures import anomaly_v03_private_sink_probe as probe
        class StoppedSink:
            _resource = False
            def __init__(self):
                self.finished = False
            def connect(self, root):
                raise MemoryError()
            def finish(self, *, primary=None):
                self.finished = True
                if primary:
                    raise primary
            def snapshot(self):
                raise AssertionError("snapshot after resource stop")
        fake = StoppedSink()
        def git_output(command, **kwargs):
            return "a" * 40 + "\n" if "rev-parse" in command else b""
        with tempfile.TemporaryDirectory(prefix="banto-b2-probe-test-") as directory:
            base = Path(directory)
            with patch.object(probe, "BASE", base), patch.object(probe, "WindowsPrivateSink", return_value=fake), \
                 patch.object(probe.subprocess, "check_output", side_effect=git_output), \
                 patch.object(probe.sys, "argv", ["probe", "--expected-head", "a" * 40, "--attempt", "1"]), \
                 patch.object(probe.os, "write") as notice:
                self.assertEqual(probe.main(), 80)
            self.assertTrue(fake.finished)
            notice.assert_called_once_with(1, b'{"storage_smoke":"resource_stop","resource_stop":true}\n')
            self.assertFalse((base / "attempt-1/probe-result.json").exists())

    def test_three_records_finish_closes_once_and_never_deletes_files(self):
        sink, native = make_sink()
        for step in owned.RELEASE_STEPS:
            self.save(sink, step)
        sink.finish()
        self.assertEqual(native.calls.count("close"), 3)
        self.assertEqual(set(native.files), {"prepare.json", "seal_payload.json", "verify_final.json"})
        self.assertEqual(sink.snapshot()["reserved_bytes"], 3 * len(self.raw))
        before = native.calls[:]
        with self.assertRaises(owned.OwnershipError):
            self.save(sink)
        self.assertEqual(native.calls, before)
        self.assertFalse(sink.snapshot()["formal_permission"])


if __name__ == "__main__":
    unittest.main()
