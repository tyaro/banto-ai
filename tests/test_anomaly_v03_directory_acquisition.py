"""Acquisition and Win64-call faults via fake APIs; no native DLL or fixture."""
import copy
import ctypes as C
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import _anomaly_v03_windows as win
from tests.fixtures import anomaly_v03_directory_acquisition as acq
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_rename_adapter as rename

USER = "S-1-5-21-1-2-3-1001"
PATH = r"C:\isolated\new-root"


class Function:
    def __init__(self, operation):
        self.operation = operation

    def __call__(self, *args):
        return self.operation(*args)


class BorrowedView:
    def observe(self):
        self.api.hit("observe")
        return copy.deepcopy(self.api.identity)

    def check(self):
        raise AssertionError("Must not reopen the path")


class FakeApi:
    def __init__(self):
        self.calls, self.hooks, self.live = [], {}, set()
        self.value, self.access, self.query_status, self.query_length = 303, acq.ROOT_ACCESS, 0, 56
        self.arguments = None
        self.identity = {"volume": 7, "file_id": "01" * 16, "directory": True}
        self.sd = {"protected": True, "owner": USER, "group": USER,
                   "aces": win._dacl(USER, "private", True)[1],
                   "integrity": "S-1-16-8192", "mandatory_policy": 1}
        self.k = SimpleNamespace(CreateDirectory2W=Function(self.create),
                                 CloseHandle=Function(self.close), LocalFree=Function(self.free))
        self.n = SimpleNamespace(NtQueryObject=Function(self.query), RtlNtStatusToDosError=Function(lambda status: 5))

    def hit(self, event):
        self.calls.append(event)
        if event in self.hooks:
            self.hooks[event]()

    def descriptor(self, sddl):
        self.hit("descriptor")
        assert sddl == win._dacl(USER, "private", True)[0]
        return C.c_void_p(808)

    def create(self, *args):
        self.arguments = args
        self.hit("create")
        if rename._handle(self.value):
            self.live.add(self.value)
        self.hit("created")
        return self.value

    def query(self, handle, kind, info, size, length):
        self.hit("access")
        assert handle == self.value and kind == 0 and size == 56
        info._obj.access, length._obj.value = self.access, self.query_length
        return self.query_status

    def security(self, handle):
        self.hit("security")
        return copy.deepcopy(self.sd)

    def close(self, handle):
        self.hit("close")
        self.live.remove(handle)
        return 1

    def free(self, pointer):
        self.hit("free")
        assert type(pointer) is C.c_void_p and pointer.value == 808
        return None


def failing(error):
    def fail():
        raise error
    return fail


def setup():
    api = FakeApi()
    surface = SimpleNamespace(_SA=win._SA, D=win.D, _dacl=win._dacl,
                              _verify_sd=win._verify_sd, _Bound=BorrowedView)
    backend = acq.WindowsDirectoryBackend(surface, api, path=PATH, user=USER)
    holder = acq.DirectoryAcquisition(backend, guard=lambda: api.hit("guard"))
    return api, backend, holder


class DirectoryAcquisitionTests(unittest.TestCase):
    def setUp(self):
        # Pure native-shaped tests also run on a 64-bit non-Windows host.
        self.runtime = patch.object(acq.sys, "version_info", (3, 14, 0))
        self.runtime.start()
        self.addCleanup(self.runtime.stop)
        self.platform = patch.object(acq.os, "name", "nt")
        self.platform.start()
        self.addCleanup(self.platform.stop)
        # Path() must remain host-native despite the synthetic runtime check.
        self.path = patch.object(acq, "Path", lambda value: value)
        self.path.start()
        self.addCleanup(self.path.stop)

    def test_single_five_argument_call_retains_original_handle_until_finish(self):
        api, backend, holder = setup()
        api.hooks["access"] = lambda: self.assertEqual(holder._lease.handle, 303)
        observation = holder.acquire()
        self.assertEqual(observation.pin.handle, 303)
        self.assertEqual(api.live, {303})
        self.assertEqual(api.calls.count("create"), 1)
        self.assertEqual(api.calls.count("observe"), 2)
        self.assertEqual(api.arguments[:4], (PATH, acq.ROOT_ACCESS, 1, 1))
        self.assertEqual(len(api.arguments), 5)
        security = api.arguments[4]._obj
        self.assertEqual((security.length, security.descriptor, security.inherit), (24, 808, 0))
        self.assertEqual(api.k.CreateDirectory2W.restype, C.c_void_p)
        self.assertEqual(api.k.CreateDirectory2W.argtypes,
                         [C.c_wchar_p, C.c_uint32, C.c_uint32, C.c_uint32, C.POINTER(win._SA)])
        holder.finish()
        holder.finish()
        self.assertEqual(api.calls[-2:], ["close", "free"])
        self.assertFalse(api.live)
        self.assertEqual(backend.snapshot()["descriptor_state"], "freed")
        self.assertEqual(holder.snapshot()["close"]["close_state"], "closed")
        self.assertFalse(holder.snapshot()["isolation_certified"])

    def test_invalid_handles_including_both_documented_failure_forms_never_close(self):
        for value in (None, 0, -1, (1 << 64) - 1, True, 1.5, (1 << 64) - 2):
            with self.subTest(value=value):
                api, backend, holder = setup()
                api.value = value
                with patch.object(C, "get_last_error", return_value=183, create=True), self.assertRaises(owned.OwnershipError):
                    holder.acquire()
                self.assertNotIn("close", api.calls)
                self.assertNotIn("access", api.calls)
                self.assertEqual(api.calls.count("free"), 1)
                self.assertEqual(holder.snapshot()["close"]["close_state"], "unavailable")

    def test_collision_preserves_error_and_never_falls_back(self):
        api, backend, holder = setup()
        api.value = None
        with patch.object(C, "get_last_error", return_value=183, create=True):
            with self.assertRaises(owned.OwnershipError) as first:
                holder.acquire()
        self.assertEqual(first.exception.winerror, 183)
        for method in (holder.acquire, holder.finish):
            with self.assertRaises(owned.OwnershipError) as later:
                method()
            self.assertIs(later.exception, first.exception)
        self.assertEqual(api.calls.count("create"), 1)

    def test_creation_resource_error_and_unavailable_error_code_never_become_success(self):
        for code in (8, 112, 0, True, -1):
            api, backend, holder = setup()
            api.value = None
            with patch.object(C, "get_last_error", return_value=code, create=True), self.assertRaises(owned.OwnershipError):
                holder.acquire()
            self.assertTrue(holder.snapshot()["stopped"])
            self.assertEqual(holder.snapshot()["resource_stop"], type(code) is int and code in (8, 112))
            self.assertNotIn("close", api.calls)

    def test_creation_response_loss_retains_input_and_requires_worker_exit(self):
        api, backend, holder = setup()
        error = MemoryError()
        api.hooks["created"] = failing(error)
        with self.assertRaises(MemoryError) as caught:
            holder.acquire()
        self.assertIs(caught.exception, error)
        self.assertEqual(api.live, {303})  # The effect happened, no number was captured.
        self.assertNotIn("close", api.calls)
        self.assertNotIn("free", api.calls)
        self.assertTrue(backend.snapshot()["worker_exit_required"])
        self.assertEqual(backend.snapshot()["descriptor_state"], "retained_unknown")

    def test_preparation_failures_never_create(self):
        for boundary in ("symbol", "descriptor", "arguments"):
            api, backend, holder = setup()
            if boundary == "symbol":
                del api.k.CreateDirectory2W
            elif boundary == "descriptor":
                api.hooks["descriptor"] = failing(MemoryError())
            else:
                backend._win._SA = type("BadSA", (), {})
            with self.assertRaises((AttributeError, TypeError, MemoryError)):
                holder.acquire()
            self.assertNotIn("create", api.calls)
            if boundary == "descriptor":
                self.assertTrue(backend.snapshot()["worker_exit_required"])

    def test_argument_preparation_failure_frees_known_descriptor_without_creation(self):
        api, backend, holder = setup()
        primary = MemoryError()
        with patch.object(C, "byref", side_effect=primary), self.assertRaises(MemoryError) as caught:
            holder.acquire()
        self.assertIs(caught.exception, primary)
        self.assertNotIn("create", api.calls)
        self.assertEqual(api.calls.count("free"), 1)
        self.assertEqual(backend.snapshot()["descriptor_state"], "freed")

    def test_prepare_response_and_captured_response_failure_stop_before_inspection(self):
        for boundary in ("prepare", "create"):
            api, backend, holder = setup()
            original = getattr(backend, boundary)
            def wrong(*args):
                original(*args)
                return True
            setattr(backend, boundary, wrong)
            with self.assertRaises(owned.OwnershipError):
                holder.acquire()
            self.assertNotIn("access", api.calls)
            self.assertEqual(api.calls.count("close"), int(boundary == "create"))
            self.assertEqual(api.calls.count("free"), 1)

    def test_wrong_granted_rights_and_query_failures_close_before_returning(self):
        for changes in ({"access": acq.ROOT_ACCESS | 0x10000}, {"access": acq.ROOT_ACCESS & ~1},
                        {"query_status": -1073741790}, {"query_length": 0}):
            api, backend, holder = setup()
            for key, value in changes.items():
                setattr(api, key, value)
            with self.assertRaises(owned.OwnershipError):
                holder.acquire()
            self.assertNotIn("observe", api.calls)
            self.assertFalse(api.live)
            self.assertEqual(api.calls.count("close"), 1)

    def test_same_handle_identity_and_private_descriptor_must_match(self):
        for changed in ("identity", "security", "type"):
            api, backend, holder = setup()
            if changed == "identity":
                api.hooks["security"] = lambda: api.identity.update(file_id="02" * 16)
            elif changed == "security":
                api.sd["aces"] = []
            else:
                api.identity["directory"] = False
            with self.assertRaises((owned.OwnershipError, rename.AdapterError, win._Failure)):
                holder.acquire()
            self.assertFalse(api.live)

    def test_native_observation_failures_and_malformed_backend_observations_close(self):
        for reason in ("object_reparse_or_type", "handle_inheritable", "object_path_changed"):
            api, backend, holder = setup()
            api.hooks["observe"] = failing(win._Failure(reason))
            with self.assertRaises(win._Failure):
                holder.acquire()
            self.assertFalse(api.live)
        api, backend, holder = setup()
        backend.inspect = lambda handle, guard: True
        with self.assertRaises(owned.OwnershipError):
            holder.acquire()
        self.assertFalse(api.live)

    def test_non_integer_granted_access_and_bad_guard_response_reject(self):
        for mode in ("access", "guard"):
            api, backend, holder = setup()
            if mode == "access":
                backend.granted_access = lambda handle: True
            else:
                holder._external_guard = lambda: True
            with self.assertRaises(owned.OwnershipError):
                holder.acquire()
            self.assertNotIn("observe", api.calls)
            self.assertFalse(api.live)

    def test_inspection_failure_remains_primary_during_reentrant_and_resource_close_failure(self):
        api, backend, holder = setup()
        primary = ValueError("inspect")
        api.hooks["observe"] = failing(primary)
        def close_failure():
            try:
                holder.finish()
            except BaseException:
                pass
            raise MemoryError()
        api.hooks["close"] = close_failure
        with self.assertRaises(ValueError) as caught:
            holder.acquire()
        self.assertIs(caught.exception, primary)
        self.assertTrue(holder.snapshot()["resource_stop"])
        self.assertEqual(holder.snapshot()["close"]["close_state"], "unknown")
        self.assertEqual(api.calls.count("free"), 1)

    def test_swallowed_reentry_stops_at_all_callback_boundaries(self):
        for boundary in ("descriptor", "create", "access", "observe", "security"):
            for action in ("acquire", "finish"):
                api, backend, holder = setup()
                def reenter():
                    try:
                        getattr(holder, action)()
                    except owned.OwnershipError:
                        pass
                api.hooks[boundary] = reenter
                with self.assertRaises(owned.OwnershipError):
                    holder.acquire()
                self.assertFalse(holder.snapshot()["same_handle_observation_verified"])
                self.assertEqual(api.calls.count("create"), int(boundary != "descriptor"))
                self.assertFalse(api.live)

    def test_parent_guard_failure_prevents_acquisition(self):
        api, backend, holder = setup()
        primary = ValueError("parent")
        api.hooks["guard"] = failing(primary)
        with self.assertRaises(ValueError) as caught:
            holder.acquire()
        self.assertIs(caught.exception, primary)
        self.assertNotIn("create", api.calls)
        self.assertNotIn("descriptor", api.calls)

    def test_close_response_loss_never_recloses_reused_number(self):
        api, backend, holder = setup()
        holder.acquire()
        def lost():
            api.live.remove(303)
            api.live.add(909)
            raise MemoryError()
        api.hooks["close"] = lost
        for _ in range(2):
            with self.assertRaises(MemoryError):
                holder.finish()
        self.assertEqual(api.live, {909})
        self.assertEqual(api.calls.count("close"), 1)
        self.assertEqual(api.calls.count("free"), 1)

    def test_descriptor_free_failure_is_not_retried_and_preserves_primary(self):
        api, backend, holder = setup()
        holder.acquire()
        primary = ValueError("caller")
        api.hooks["free"] = failing(MemoryError())
        for _ in range(2):
            with self.assertRaises(ValueError) as caught:
                holder.finish(primary=primary)
            self.assertIs(caught.exception, primary)
        self.assertEqual(api.calls.count("free"), 1)
        self.assertTrue(backend.snapshot()["worker_exit_required"])
        self.assertTrue(holder.snapshot()["resource_stop"])

    def test_finish_before_acquire_and_backend_reuse_never_create(self):
        api, backend, holder = setup()
        holder.finish()
        with self.assertRaises(owned.OwnershipError):
            holder.acquire()
        with self.assertRaises(owned.OwnershipError):
            backend.prepare()
        self.assertNotIn("create", api.calls)

    def test_path_and_user_validation_is_pure_and_bounded(self):
        api, backend, holder = setup()
        for path in ("relative", r"C:relative", r"\\server\share\new", r"C:\a\..\b", r"C:\a\.",
                     r"C:\a\new ", r"C:\a\x:y", r"C:\a\CON.txt", "C:\\" + "x" * 241, "C:\\a\x00b"):
            with self.subTest(path=path), self.assertRaises(owned.OwnershipError):
                acq.WindowsDirectoryBackend(backend._win, api, path=path, user=USER)
        for user in (None, "", USER + ";", "x" * 185):
            with self.assertRaises(owned.OwnershipError):
                acq.WindowsDirectoryBackend(backend._win, api, path=PATH, user=user)
        self.assertFalse(api.calls)


if __name__ == "__main__":
    unittest.main()
