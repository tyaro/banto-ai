"""Single-call directory acquisition experiment; no publisher or native entry.

The trusted caller retains this holder before acquire() and keeps all ancestors
guarded through finish(). Successful acquisition does not certify isolation.
Imports do not load a DLL. Tests inject the backend, including Windows bindings.
"""
import ctypes as C
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys

from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_prepublication as prep
from . import anomaly_v03_rename_adapter as rename
from .anomaly_v03_reader_reacquisition import WindowsReaderBackend
from .anomaly_v03_tracked_open import TrackedOpen

ROOT_ACCESS = 0x1600A7
SHARE_READ = 1
DISALLOW_REDIRECTS = 1


class DirectoryAcquisition:
    """One acquisition and one close authority; no retry, adoption or cleanup."""
    def __init__(self, backend, *, guard):
        owned._need(callable(guard), "directory_guard")
        self._backend, self._external_guard = backend, guard
        self._lease = TrackedOpen(backend)  # Reserved before preparation or creation.
        self._started = self._busy = self._done = self._resource = False
        self._error = None
        self._phase = "not_started"
        self._access = self._observation = None

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)

    def _guard(self):
        if self._error is not None:
            raise self._error
        owned._need(not self._done, "directory_finished")
        owned._need(self._external_guard() is None, "directory_guard_response")
        if self._error is not None:
            raise self._error

    def acquire(self):
        entered = False
        try:
            if self._error is not None:
                raise self._error
            owned._need(not self._started and not self._done and not self._busy, "directory_attempt_reused")
            self._started = self._busy = entered = True
            self._guard()
            self._phase = "preparing"
            owned._need(self._backend.prepare() is None, "directory_prepare_response")
            self._guard()

            def create(cell):
                try:
                    self._guard()
                    self._phase = "create_pending"
                    owned._need(self._backend.create(cell) is None and rename._handle(cell.handle),
                                "directory_create_response")
                except BaseException as error:
                    self._record(error)
                    raise self._error

            def inspect(handle):
                self._guard()
                self._phase = "inspect_pending"
                access = self._backend.granted_access(handle)
                self._guard()
                owned._need(type(access) is int and access == ROOT_ACCESS, "directory_granted_access")
                self._access = access
                observation = self._backend.inspect(handle, guard=self._guard)
                self._guard()
                owned._need(type(observation) is prep.Observation, "directory_observation")
                rename._pin(observation.pin)
                owned._need(observation.pin.handle == handle and observation.pin.directory
                            and type(observation.descriptor) is bytes
                            and 0 < len(observation.descriptor) <= prep.MAX_DESCRIPTOR_BYTES, "directory_observation")
                return observation

            def inspect_recorded(handle):
                try:
                    return inspect(handle)
                except BaseException as error:
                    self._record(error)
                    raise self._error

            observation = self._lease.acquire(create, inspect_recorded)
            self._guard()
            self._observation = observation
            self._phase = "verified"
            return observation
        except BaseException as error:
            self._record(error)
            if entered:
                self._busy = False
                self.finish()
            raise self._error
        finally:
            if entered:
                self._busy = False

    def finish(self, *, primary=None):
        owned._need(primary is None or isinstance(primary, BaseException), "primary_type")
        if primary is not None:
            self._record(primary)
        if self._busy:
            self._record(owned.OwnershipError("directory_operation_active"))
            raise self._error
        if not self._done:
            self._done = self._busy = True
            try:
                try:
                    self._lease.close()
                except BaseException as error:
                    self._record(error)
                self._resource = self._resource or self._lease.resource_stop
                try:
                    owned._need(self._backend.release() is None, "directory_release_response")
                except BaseException as error:
                    self._record(error)
            finally:
                self._busy = False
        if self._error is not None:
            raise self._error

    def snapshot(self):
        return {"phase": self._phase, "finished": self._done, "stopped": self._error is not None,
                "resource_stop": self._resource, "granted_access": self._access,
                "same_handle_observation_verified": self._observation is not None,
                "close": self._lease.snapshot(), "retry_permitted": False, "cleanup_permitted": False,
                "isolation_certified": False, "protected_commit_allowed": False,
                "native_publication_performed": False, "formal_permission": False,
                "execution_authenticated": False, "acceptance_status": "not_completed"}


def _path(path):
    owned._need(type(path) is str and 3 < len(path) <= 240, "directory_path")
    pure = PureWindowsPath(path)
    owned._need(re.fullmatch(r"[A-Za-z]:", pure.drive) is not None and pure.root == "\\"
                and str(pure) == path and 2 <= len(pure.parts) <= 17, "directory_path")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    for part in pure.parts[1:]:
        owned._need(not re.search(r'[<>:"/\\|?*\x00-\x1f]', part) and not part.endswith((".", " "))
                    and part.split(".")[0].upper() not in reserved, "directory_path")
    return Path(path)


class WindowsDirectoryBackend:
    """Prepared five-argument Win64 binding. Caller supplies existing API runtime.

    No ancestor ownership, child inventory or peer capability proof is supplied.
    prepare() must finish before create(). Keep the backend reachable even when
    creation loses its response: its descriptor may need to live until exit.
    """
    DIRECTORY = True

    def __init__(self, win, api, *, path, user):
        self._path = _path(path)
        owned._need(type(user) is str and len(user) <= 184
                    and re.fullmatch(r"S-1-(?:[0-9]+-)+[0-9]+", user) is not None, "directory_user")
        self._win, self._api, self._user = win, api, user
        self._prepared = self._preparing = self._called = self._returned = self._released = False
        self._descriptor = None
        self._descriptor_state = "not_started"
        self._arguments = self._create = self._reader = None

    def prepare(self):
        owned._need(not self._preparing and not self._released, "directory_backend_reused")
        self._preparing = True
        win, api = self._win, self._api
        owned._need(os.name == "nt" and sys.version_info[:3] == (3, 14, 0) and C.sizeof(C.c_void_p) == 8,
                    "directory_runtime")
        owned._need(C.sizeof(win._SA) == 24 and win._SA.descriptor.offset == 8
                    and win._SA.inherit.offset == 16 and C.sizeof(win.D) == 4, "directory_security_abi")
        create = api.k.CreateDirectory2W  # Missing symbol fails before descriptor allocation.
        create.restype = C.c_void_p
        create.argtypes = [C.c_wchar_p, C.c_uint32, C.c_uint32, C.c_uint32, C.POINTER(win._SA)]
        self._create = create
        self._reader = WindowsReaderBackend(self)
        sddl = self._sddl()
        self._descriptor_state = "allocating"
        self._descriptor = api.descriptor(sddl)
        owned._need(rename._handle(self._descriptor_address()), "directory_descriptor")
        self._descriptor_state = "owned"
        self._security = win._SA(C.sizeof(win._SA), self._descriptor, False)
        self._arguments = (str(self._path), ROOT_ACCESS, SHARE_READ, DISALLOW_REDIRECTS, C.byref(self._security))
        self._prepared = True

    def create(self, cell):
        owned._need(self._prepared and not self._called and not self._released
                    and type(cell) is TrackedOpen and cell.state == "opening" and cell.handle is None,
                    "directory_create_state")
        self._called = True  # Side effect may occur even if no handle reaches Python.
        cell.handle = self._create(*self._arguments)
        self._returned = True
        if cell.handle is None or type(cell.handle) is int and cell.handle in (0, -1, (1 << 64) - 1):
            code = C.get_last_error()
            owned._need(type(code) is int and 0 < code < 1 << 32, "directory_error_unavailable")
            raise owned.OwnershipError("directory_create_failed", code)
        owned._need(rename._handle(cell.handle), "directory_create_value")

    def granted_access(self, handle):
        return self._reader.granted_access(handle)

    def _sddl(self):
        return self._win._dacl(self._user, "private", self.DIRECTORY)[0]

    def _verify_policy(self, sd):
        self._win._verify_sd(sd, self._user, "private", self.DIRECTORY)

    def _content_hash(self, handle, *, guard):
        return None

    def inspect(self, handle, *, guard):
        # _Bound.check() reopens by name. Only observe() is used here: the
        # original returned handle is the sole directory handle acquired.
        view = self._win._Bound.__new__(self._win._Bound)
        view.api, view.path, view.directory, view.handle = self._api, self._path, self.DIRECTORY, handle
        guard()
        before = view.observe()
        guard()
        sd = self._api.security(handle)
        guard()
        self._verify_policy(sd)
        descriptor = json.dumps(sd, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
        owned._need(0 < len(descriptor) <= prep.MAX_DESCRIPTOR_BYTES, "directory_descriptor_budget")
        guard()
        after = view.observe()
        guard()
        owned._need(before == after, "directory_identity_changed")
        content_hash = self._content_hash(handle, guard=guard)
        guard()
        pin = rename.ObjectPin(handle, before["volume"], bytes.fromhex(before["file_id"]), before["directory"], content_hash)
        rename._pin(pin)
        return prep.Observation(pin, descriptor)

    def close_handle(self, handle):
        return self._api.k.CloseHandle(handle)

    def get_last_error(self):
        return C.get_last_error()

    def _descriptor_address(self):
        # Existing _Api.descriptor returns an H cell, not its integer value.
        return self._descriptor.value if type(self._descriptor) is C.c_void_p else self._descriptor

    def release(self):
        if self._released:
            return
        self._released = True
        if self._called and not self._returned:
            self._descriptor_state = "retained_unknown"  # Do not free possible in-flight input.
        elif rename._handle(self._descriptor_address()):
            self._descriptor_state = "free_unknown"  # No second LocalFree on reply loss.
            owned._need(not self._api.k.LocalFree(self._descriptor), "directory_descriptor_free")
            self._descriptor_state = "freed"
        elif self._descriptor_state == "allocating":
            self._descriptor_state = "unavailable"

    def snapshot(self):
        return {"prepared": self._prepared, "create_called": self._called, "create_returned": self._returned,
                "descriptor_state": self._descriptor_state,
                "worker_exit_required": self.requires_exit(),
                "retry_permitted": False, "cleanup_permitted": False, "isolation_certified": False}

    def requires_exit(self):
        # Teardown must not allocate a report just to decide input lifetime.
        return (self._called and not self._returned) or self._descriptor_state in (
            "allocating", "unavailable", "free_unknown", "retained_unknown")
